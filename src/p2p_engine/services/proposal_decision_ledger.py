from __future__ import annotations

import hashlib
import re
from datetime import date
from pathlib import Path
from typing import Mapping

import yaml

from p2p_engine.foundation.yaml_loaders import DuplicateYamlKeyError, load_yaml

from p2p_engine.core.mutation_preview import semantic_sha256
from p2p_engine.core.proposal_decision_events import (
    ProposalDecisionAffectedDecision,
    ProposalDecisionAuthorityEvidence,
    ProposalDecisionAuthorityResolution,
    ProposalDecisionBindingStatus,
    ProposalDecisionCondition,
    ProposalDecisionEffectiveState,
    ProposalDecisionEvent,
    ProposalDecisionEventType,
    ProposalDecisionImpactBinding,
    ProposalDecisionLedger,
    ProposalDecisionLegacyEvidence,
    ProposalDecisionLineage,
    ProposalDecisionLineageKind,
    ProposalDecisionMigrationProvenance,
    ProposalDecisionMutationBinding,
    ProposalDecisionPredecessor,
    ProposalDecisionReadinessBinding,
)
from p2p_engine.foundation.files import yaml_dump
from p2p_engine.foundation.markdown import read_markdown_section, read_title, replace_section


LEDGER_CONTRACT_VERSION = 1
EVENT_SCHEMA_VERSION = 1
EVENT_INTEGRITY_POLICY_VERSION = 1
PROPOSAL_SEMANTICS_POLICY_VERSION = 1
DECISION_SEMANTICS_POLICY_VERSION = 1
EVENT_ID_PREFIX = "PDE-"
OPERATION_KEY_PREFIX = "P2POP-"
MAX_LEDGER_BYTES = 32 * 1024 * 1024
MAX_RATIONALE_BYTES = 64 * 1024
MAX_CONDITION_BYTES = 8 * 1024
MAX_CONDITIONS_BYTES = 64 * 1024
MAX_CONDITIONS = 64
MAX_LINEAGE_TARGETS = 100
MAX_LEGACY_SCALAR_BYTES = 4 * 1024

_ROOT_KEYS = frozenset({"proposal_decision_ledger"})
_LEDGER_KEYS = frozenset(
    {
        "contract_version",
        "proposal_id",
        "authority_resolution",
        "effective_state",
        "head_event_id",
        "events",
        "legacy_evidence",
    }
)
_EVENT_KEYS = frozenset(
    {
        "event_schema_version",
        "event_id",
        "operation_key",
        "proposal_id",
        "event_type",
        "effective_state",
        "rationale",
        "conditions",
        "decided_on",
        "authority",
        "predecessor",
        "proposal_semantic_sha256",
        "decision_semantic_sha256",
        "affected_decision",
        "lineage",
        "impact",
        "readiness",
        "mutation",
        "migration",
        "event_sha256",
    }
)
_AUTHORITY_KEYS = frozenset(
    {
        "owner_id",
        "owner_role",
        "executor_actor_id",
        "executor_kind",
        "channel",
        "permission_policy_sha256",
        "consent_id",
        "consent_sha256",
    }
)
_PREDECESSOR_KEYS = frozenset({"event_id", "event_sha256"})
_AFFECTED_KEYS = frozenset(
    {"event_id", "decision_semantic_sha256", "revocation_event_id"}
)
_LINEAGE_KEYS = frozenset({"kind", "targets"})
_IMPACT_KEYS = frozenset(
    {"required", "preview_token", "source_fingerprint_sha256", "total_count"}
)
_READINESS_KEYS = frozenset({"source_fingerprint_sha256", "owner_override"})
_MUTATION_KEYS = frozenset({"preview_token", "request_fingerprint_sha256"})
_MIGRATION_KEYS = frozenset(
    {"migration_id", "source_paths", "source_sha256", "preserved_values"}
)
_LEGACY_KEYS = frozenset(
    {
        "migration_id",
        "source_paths",
        "source_sha256",
        "values",
        "diagnostics",
        "truncated_fields",
    }
)
_CONDITION_KEYS = frozenset({"id", "text"})
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_EVENT_ID = re.compile(r"^PDE-[0-9a-f]{24}$")
_OPERATION_KEY = re.compile(r"^P2POP-[0-9a-f]{24}$")
_PROPOSAL_ID = re.compile(r"^PROP-\d{3,}$")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def strict_yaml_load(content: bytes) -> object:
    if len(content) > MAX_LEDGER_BYTES:
        raise ValueError(
            "P2P361_DECISION_LEDGER_INVALID: ledger exceeds "
            f"{MAX_LEDGER_BYTES} bytes"
        )
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("P2P361_DECISION_LEDGER_INVALID: ledger is not UTF-8") from exc
    try:
        return load_yaml(text, loader_contract="unique-v1")
    except DuplicateYamlKeyError as exc:
        raise ValueError(
            f"P2P361_DECISION_LEDGER_INVALID: duplicate YAML key `{exc.key}`"
        ) from exc
    except ValueError:
        raise
    except yaml.YAMLError as exc:
        raise ValueError(f"P2P361_DECISION_LEDGER_INVALID: invalid YAML: {exc}") from exc


class ProposalDecisionLedgerCodec:
    def empty(self, proposal_id: str) -> ProposalDecisionLedger:
        _validate_proposal_id(proposal_id)
        return ProposalDecisionLedger(
            contract_version=LEDGER_CONTRACT_VERSION,
            proposal_id=proposal_id,
            authority_resolution=ProposalDecisionAuthorityResolution.resolved,
            effective_state=ProposalDecisionEffectiveState.undecided,
            head_event_id=None,
        )

    def dumps(self, ledger: ProposalDecisionLedger) -> bytes:
        self.validate(ledger)
        return yaml_dump(ledger.to_dict()).encode("ascii")

    def loads(self, content: bytes, *, expected_proposal_id: str | None = None) -> ProposalDecisionLedger:
        return self.loads_mapping(
            strict_yaml_load(content),
            expected_proposal_id=expected_proposal_id,
        )

    def loads_mapping(
        self,
        payload: object,
        *,
        expected_proposal_id: str | None = None,
    ) -> ProposalDecisionLedger:
        """Decode an already parsed strict YAML mapping without reparsing bytes."""
        if not isinstance(payload, Mapping):
            raise _invalid("ledger root must be a mapping")
        _closed_keys(payload, _ROOT_KEYS, "ledger root")
        raw = payload.get("proposal_decision_ledger")
        if not isinstance(raw, Mapping):
            raise _invalid("proposal_decision_ledger mapping is required")
        _closed_keys(raw, _LEDGER_KEYS, "proposal_decision_ledger")
        contract_version = _required_int(raw, "contract_version")
        if contract_version != LEDGER_CONTRACT_VERSION:
            code = (
                "P2P376_DECISION_FUTURE_CONTRACT"
                if contract_version > LEDGER_CONTRACT_VERSION
                else "P2P361_DECISION_LEDGER_INVALID"
            )
            raise ValueError(f"{code}: unsupported ledger contract version {contract_version}")
        proposal_id = _required_text(raw, "proposal_id")
        _validate_proposal_id(proposal_id)
        if expected_proposal_id and proposal_id != expected_proposal_id:
            raise _invalid(
                f"ledger proposal `{proposal_id}` does not match `{expected_proposal_id}`"
            )
        events_raw = _required_list(raw, "events")
        legacy_raw = _required_list(raw, "legacy_evidence")
        ledger = ProposalDecisionLedger(
            contract_version=contract_version,
            proposal_id=proposal_id,
            authority_resolution=_enum(
                ProposalDecisionAuthorityResolution,
                raw.get("authority_resolution"),
                "authority_resolution",
            ),
            effective_state=_enum(
                ProposalDecisionEffectiveState,
                raw.get("effective_state"),
                "effective_state",
            ),
            head_event_id=_optional_text(raw.get("head_event_id"), "head_event_id"),
            events=tuple(self._parse_event(item, proposal_id) for item in events_raw),
            legacy_evidence=tuple(self._parse_legacy(item) for item in legacy_raw),
        )
        self.validate(ledger)
        return ledger

    def recover_valid_event_prefix(
        self,
        content: bytes,
        *,
        expected_proposal_id: str,
    ) -> tuple[ProposalDecisionEvent, ...]:
        payload = strict_yaml_load(content)
        if not isinstance(payload, dict):
            raise ValueError(
                "P2P372_DECISION_REPAIR_UNSAFE: ledger root is not recoverable"
            )
        raw = payload.get("proposal_decision_ledger")
        if not isinstance(raw, dict):
            raise ValueError(
                "P2P372_DECISION_REPAIR_UNSAFE: ledger mapping is not recoverable"
            )
        proposal_id = str(raw.get("proposal_id") or "")
        if proposal_id != expected_proposal_id:
            raise ValueError(
                "P2P372_DECISION_REPAIR_UNSAFE: proposal identity differs"
            )
        events_raw = raw.get("events")
        if not isinstance(events_raw, list):
            raise ValueError(
                "P2P372_DECISION_REPAIR_UNSAFE: event sequence is not recoverable"
            )
        recovered: list[ProposalDecisionEvent] = []
        for item in events_raw:
            try:
                event = self._parse_event(item, expected_proposal_id)
                candidate = ProposalDecisionLedger(
                    contract_version=LEDGER_CONTRACT_VERSION,
                    proposal_id=expected_proposal_id,
                    authority_resolution=ProposalDecisionAuthorityResolution.resolved,
                    effective_state=event.effective_state,
                    head_event_id=event.event_id,
                    events=(*recovered, event),
                )
                self.validate(candidate)
            except ValueError:
                break
            recovered.append(event)
        return tuple(recovered)

    def validate(self, ledger: ProposalDecisionLedger) -> None:
        if ledger.contract_version != LEDGER_CONTRACT_VERSION:
            raise _invalid("unsupported ledger contract version")
        _validate_proposal_id(ledger.proposal_id)
        event_ids: set[str] = set()
        operation_keys: set[str] = set()
        predecessor: ProposalDecisionEvent | None = None
        for event in ledger.events:
            self._validate_event(event, ledger.proposal_id, predecessor)
            if event.event_id in event_ids:
                raise _invalid(f"duplicate event ID `{event.event_id}`")
            if event.operation_key in operation_keys:
                raise _invalid(f"duplicate operation key `{event.operation_key}`")
            event_ids.add(event.event_id)
            operation_keys.add(event.operation_key)
            predecessor = event
        self._validate_chain_semantics(ledger.events)
        expected_head = ledger.events[-1].event_id if ledger.events else None
        if ledger.head_event_id != expected_head:
            raise _invalid("head_event_id does not match the final event")
        expected_state = (
            ledger.events[-1].effective_state
            if ledger.events
            else (
                ProposalDecisionEffectiveState.unknown_legacy
                if ledger.authority_resolution
                == ProposalDecisionAuthorityResolution.unknown_legacy
                else ProposalDecisionEffectiveState.undecided
            )
        )
        if ledger.effective_state != expected_state:
            raise _invalid("effective_state does not match the event head")
        if (
            ledger.authority_resolution
            == ProposalDecisionAuthorityResolution.unknown_legacy
            and ledger.events
        ):
            raise _invalid("unknown legacy authority cannot contain resolved events")

    @staticmethod
    def _validate_chain_semantics(
        events: tuple[ProposalDecisionEvent, ...],
    ) -> None:
        from p2p_engine.services.lifecycle_authority import (
            effective_state_for_event,
            require_transition,
        )

        state = ProposalDecisionEffectiveState.undecided
        active_decision: ProposalDecisionEvent | None = None
        events_by_id: dict[str, ProposalDecisionEvent] = {}
        active_to_inactive = {
            ProposalDecisionEventType.revoked,
            ProposalDecisionEventType.superseded,
            ProposalDecisionEventType.split,
            ProposalDecisionEventType.merged_into_other,
        }
        for event in events:
            require_transition(state, event.event_type)
            affected = event.affected_decision
            if event.event_type == ProposalDecisionEventType.reinstated:
                restored = events_by_id.get(affected.event_id or "")
                revocation = events_by_id.get(affected.revocation_event_id or "")
                if (
                    restored is None
                    or restored.event_type
                    not in {
                        ProposalDecisionEventType.accepted,
                        ProposalDecisionEventType.accepted_with_changes,
                    }
                    or affected.decision_semantic_sha256
                    != restored.decision_semantic_sha256
                    or event.decision_semantic_sha256
                    != restored.decision_semantic_sha256
                    or revocation is None
                    or revocation.event_type != ProposalDecisionEventType.revoked
                    or revocation.event_id != event.predecessor.event_id
                    or revocation.affected_decision.event_id != restored.event_id
                ):
                    raise ValueError(
                        "P2P368_DECISION_REINSTATEMENT_MISMATCH: reinstatement "
                        "references do not match the prior active decision and revocation"
                    )
                expected_state = effective_state_for_event(
                    event.event_type,
                    restored_state=restored.effective_state,
                )
                active_decision = restored
            else:
                expected_state = effective_state_for_event(event.event_type)
                if event.event_type in active_to_inactive and active_decision is not None:
                    if (
                        affected.event_id != active_decision.event_id
                        or affected.decision_semantic_sha256
                        != active_decision.decision_semantic_sha256
                        or affected.revocation_event_id is not None
                        or event.decision_semantic_sha256
                        != active_decision.decision_semantic_sha256
                    ):
                        raise _invalid(
                            "inactive transition does not bind the current active decision"
                        )
                    active_decision = None
                elif (
                    affected.event_id is not None
                    or affected.decision_semantic_sha256 is not None
                    or affected.revocation_event_id is not None
                ):
                    raise _invalid(
                        f"`{event.event_type.value}` has unexpected affected-decision references"
                    )
                if event.event_type in {
                    ProposalDecisionEventType.accepted,
                    ProposalDecisionEventType.accepted_with_changes,
                }:
                    active_decision = event
            if event.effective_state != expected_state:
                raise _invalid(
                    f"`{event.event_type.value}` has incompatible effective state "
                    f"`{event.effective_state.value}`"
                )
            state = event.effective_state
            events_by_id[event.event_id] = event

    def append(
        self,
        ledger: ProposalDecisionLedger,
        event: ProposalDecisionEvent,
    ) -> ProposalDecisionLedger:
        candidate = ProposalDecisionLedger(
            contract_version=ledger.contract_version,
            proposal_id=ledger.proposal_id,
            authority_resolution=ProposalDecisionAuthorityResolution.resolved,
            effective_state=event.effective_state,
            head_event_id=event.event_id,
            events=(*ledger.events, event),
            legacy_evidence=ledger.legacy_evidence,
        )
        self.validate(candidate)
        return candidate

    def build_event(
        self,
        *,
        proposal_id: str,
        event_type: ProposalDecisionEventType,
        effective_state: ProposalDecisionEffectiveState,
        rationale: str,
        conditions: tuple[ProposalDecisionCondition, ...],
        decided_on: str,
        authority: ProposalDecisionAuthorityEvidence,
        predecessor: ProposalDecisionEvent | None,
        proposal_semantic_sha256: str,
        decision_semantic_sha256: str,
        affected_decision: ProposalDecisionAffectedDecision,
        lineage: ProposalDecisionLineage,
        impact: ProposalDecisionImpactBinding,
        readiness: ProposalDecisionReadinessBinding,
        preview_token: str,
        request_fingerprint_sha256: str,
        operation_key: str,
        migration: ProposalDecisionMigrationProvenance | None = None,
    ) -> ProposalDecisionEvent:
        rationale = normalize_scalar(rationale, "rationale", MAX_RATIONALE_BYTES)
        _validate_date(decided_on)
        validate_conditions(conditions, required=event_type == ProposalDecisionEventType.accepted_with_changes)
        validate_lineage(lineage, proposal_id=proposal_id, event_type=event_type)
        if not _OPERATION_KEY.fullmatch(operation_key):
            raise _invalid("operation_key must use P2POP- plus 24 lowercase hex characters")
        _validate_sha256(proposal_semantic_sha256, "proposal_semantic_sha256")
        _validate_sha256(decision_semantic_sha256, "decision_semantic_sha256")
        _validate_sha256(preview_token, "mutation.preview_token")
        _validate_sha256(request_fingerprint_sha256, "mutation.request_fingerprint_sha256")
        predecessor_value = ProposalDecisionPredecessor(
            event_id=predecessor.event_id if predecessor else None,
            event_sha256=predecessor.event_sha256 if predecessor else None,
        )
        identity_payload = {
            "event_integrity_policy_version": EVENT_INTEGRITY_POLICY_VERSION,
            "event_schema_version": EVENT_SCHEMA_VERSION,
            "operation_key": operation_key,
            "proposal_id": proposal_id,
            "event_type": event_type.value,
            "effective_state": effective_state.value,
            "rationale": rationale,
            "conditions": [item.to_dict() for item in conditions],
            "decided_on": decided_on,
            "authority": authority.to_dict(),
            "predecessor": predecessor_value.to_dict(),
            "proposal_semantic_sha256": proposal_semantic_sha256,
            "decision_semantic_sha256": decision_semantic_sha256,
            "affected_decision": affected_decision.to_dict(),
            "lineage": lineage.to_dict(),
            "impact": impact.to_dict(),
            "readiness": readiness.to_dict(),
            "mutation": {
                "preview_token": preview_token,
                "request_fingerprint_sha256": request_fingerprint_sha256,
            },
            "migration": migration.to_dict() if migration else None,
        }
        event_id = EVENT_ID_PREFIX + semantic_sha256(identity_payload)[:24]
        provisional = ProposalDecisionEvent(
            event_schema_version=EVENT_SCHEMA_VERSION,
            event_id=event_id,
            operation_key=operation_key,
            proposal_id=proposal_id,
            event_type=event_type,
            effective_state=effective_state,
            rationale=rationale,
            conditions=conditions,
            decided_on=decided_on,
            authority=authority,
            predecessor=predecessor_value,
            proposal_semantic_sha256=proposal_semantic_sha256,
            decision_semantic_sha256=decision_semantic_sha256,
            affected_decision=affected_decision,
            lineage=lineage,
            impact=impact,
            readiness=readiness,
            mutation=ProposalDecisionMutationBinding(
                preview_token=preview_token,
                request_fingerprint_sha256=request_fingerprint_sha256,
            ),
            migration=migration,
            event_sha256="",
        )
        return ProposalDecisionEvent(
            **{
                **provisional.__dict__,
                "event_sha256": semantic_sha256(provisional.to_dict(include_hash=False)),
            }
        )

    def _parse_event(self, raw: object, proposal_id: str) -> ProposalDecisionEvent:
        if not isinstance(raw, dict):
            raise _invalid("event must be a mapping")
        _closed_keys(raw, _EVENT_KEYS, "event")
        authority_raw = _required_mapping(raw, "authority")
        predecessor_raw = _required_mapping(raw, "predecessor")
        affected_raw = _required_mapping(raw, "affected_decision")
        lineage_raw = _required_mapping(raw, "lineage")
        impact_raw = _required_mapping(raw, "impact")
        readiness_raw = _required_mapping(raw, "readiness")
        mutation_raw = _required_mapping(raw, "mutation")
        _closed_keys(authority_raw, _AUTHORITY_KEYS, "authority")
        _closed_keys(predecessor_raw, _PREDECESSOR_KEYS, "predecessor")
        _closed_keys(affected_raw, _AFFECTED_KEYS, "affected_decision")
        _closed_keys(lineage_raw, _LINEAGE_KEYS, "lineage")
        _closed_keys(impact_raw, _IMPACT_KEYS, "impact")
        _closed_keys(readiness_raw, _READINESS_KEYS, "readiness")
        _closed_keys(mutation_raw, _MUTATION_KEYS, "mutation")
        conditions = tuple(self._parse_condition(item) for item in _required_list(raw, "conditions"))
        migration_raw = raw.get("migration")
        migration = None
        if migration_raw is not None:
            if not isinstance(migration_raw, dict):
                raise _invalid("migration must be a mapping or null")
            _closed_keys(migration_raw, _MIGRATION_KEYS, "migration")
            migration = ProposalDecisionMigrationProvenance(
                migration_id=_required_text(migration_raw, "migration_id"),
                source_paths=_text_tuple(migration_raw.get("source_paths"), "migration.source_paths"),
                source_sha256=_string_mapping(
                    migration_raw.get("source_sha256"),
                    "migration.source_sha256",
                ),
                preserved_values=_mapping(
                    migration_raw.get("preserved_values"),
                    "migration.preserved_values",
                ),
            )
        lineage_kind_raw = lineage_raw.get("kind")
        lineage_kind = (
            None
            if lineage_kind_raw is None
            else _enum(ProposalDecisionLineageKind, lineage_kind_raw, "lineage.kind")
        )
        return ProposalDecisionEvent(
            event_schema_version=_required_int(raw, "event_schema_version"),
            event_id=_required_text(raw, "event_id"),
            operation_key=_required_text(raw, "operation_key"),
            proposal_id=_required_text(raw, "proposal_id"),
            event_type=_enum(ProposalDecisionEventType, raw.get("event_type"), "event_type"),
            effective_state=_enum(
                ProposalDecisionEffectiveState,
                raw.get("effective_state"),
                "effective_state",
            ),
            rationale=_required_text(raw, "rationale"),
            conditions=conditions,
            decided_on=_required_text(raw, "decided_on"),
            authority=ProposalDecisionAuthorityEvidence(
                owner_id=_required_text(authority_raw, "owner_id"),
                owner_role=_required_text(authority_raw, "owner_role"),
                executor_actor_id=_required_text(authority_raw, "executor_actor_id"),
                executor_kind=_required_text(authority_raw, "executor_kind"),
                channel=_required_text(authority_raw, "channel"),
                permission_policy_sha256=_required_text(
                    authority_raw,
                    "permission_policy_sha256",
                ),
                consent_id=_optional_text(authority_raw.get("consent_id"), "authority.consent_id"),
                consent_sha256=_optional_text(
                    authority_raw.get("consent_sha256"),
                    "authority.consent_sha256",
                ),
            ),
            predecessor=ProposalDecisionPredecessor(
                event_id=_optional_text(predecessor_raw.get("event_id"), "predecessor.event_id"),
                event_sha256=_optional_text(
                    predecessor_raw.get("event_sha256"),
                    "predecessor.event_sha256",
                ),
            ),
            proposal_semantic_sha256=_required_text(raw, "proposal_semantic_sha256"),
            decision_semantic_sha256=_required_text(raw, "decision_semantic_sha256"),
            affected_decision=ProposalDecisionAffectedDecision(
                event_id=_optional_text(affected_raw.get("event_id"), "affected_decision.event_id"),
                decision_semantic_sha256=_optional_text(
                    affected_raw.get("decision_semantic_sha256"),
                    "affected_decision.decision_semantic_sha256",
                ),
                revocation_event_id=_optional_text(
                    affected_raw.get("revocation_event_id"),
                    "affected_decision.revocation_event_id",
                ),
            ),
            lineage=ProposalDecisionLineage(
                kind=lineage_kind,
                targets=_text_tuple(lineage_raw.get("targets"), "lineage.targets"),
            ),
            impact=ProposalDecisionImpactBinding(
                required=_required_bool(impact_raw, "required"),
                preview_token=_optional_text(impact_raw.get("preview_token"), "impact.preview_token"),
                source_fingerprint_sha256=_optional_text(
                    impact_raw.get("source_fingerprint_sha256"),
                    "impact.source_fingerprint_sha256",
                ),
                total_count=_required_int(impact_raw, "total_count"),
            ),
            readiness=ProposalDecisionReadinessBinding(
                source_fingerprint_sha256=_optional_text(
                    readiness_raw.get("source_fingerprint_sha256"),
                    "readiness.source_fingerprint_sha256",
                ),
                owner_override=_required_bool(readiness_raw, "owner_override"),
            ),
            mutation=ProposalDecisionMutationBinding(
                preview_token=_required_text(mutation_raw, "preview_token"),
                request_fingerprint_sha256=_required_text(
                    mutation_raw,
                    "request_fingerprint_sha256",
                ),
            ),
            migration=migration,
            event_sha256=_required_text(raw, "event_sha256"),
        )

    def _parse_condition(self, raw: object) -> ProposalDecisionCondition:
        if not isinstance(raw, dict):
            raise _invalid("condition must be a mapping")
        _closed_keys(raw, _CONDITION_KEYS, "condition")
        return ProposalDecisionCondition(
            condition_id=_required_text(raw, "id"),
            text=_required_text(raw, "text"),
        )

    def _parse_legacy(self, raw: object) -> ProposalDecisionLegacyEvidence:
        if not isinstance(raw, dict):
            raise _invalid("legacy evidence must be a mapping")
        _closed_keys(raw, _LEGACY_KEYS, "legacy evidence")
        return ProposalDecisionLegacyEvidence(
            migration_id=_required_text(raw, "migration_id"),
            source_paths=_text_tuple(raw.get("source_paths"), "legacy.source_paths"),
            source_sha256=_string_mapping(raw.get("source_sha256"), "legacy.source_sha256"),
            values=_mapping(raw.get("values"), "legacy.values"),
            diagnostics=_text_tuple(raw.get("diagnostics"), "legacy.diagnostics"),
            truncated_fields=_text_tuple(
                raw.get("truncated_fields"),
                "legacy.truncated_fields",
            ),
        )

    def _validate_event(
        self,
        event: ProposalDecisionEvent,
        proposal_id: str,
        predecessor: ProposalDecisionEvent | None,
    ) -> None:
        if event.event_schema_version != EVENT_SCHEMA_VERSION:
            code = (
                "P2P376_DECISION_FUTURE_CONTRACT"
                if event.event_schema_version > EVENT_SCHEMA_VERSION
                else "P2P361_DECISION_LEDGER_INVALID"
            )
            raise ValueError(
                f"{code}: unsupported event schema version {event.event_schema_version}"
            )
        if event.proposal_id != proposal_id:
            raise _invalid("event proposal_id does not match ledger")
        if not _EVENT_ID.fullmatch(event.event_id):
            raise _invalid(f"invalid event ID `{event.event_id}`")
        if not _OPERATION_KEY.fullmatch(event.operation_key):
            raise _invalid(f"invalid operation key `{event.operation_key}`")
        normalize_scalar(event.rationale, "rationale", MAX_RATIONALE_BYTES)
        validate_conditions(
            event.conditions,
            required=event.event_type == ProposalDecisionEventType.accepted_with_changes,
        )
        _validate_date(event.decided_on)
        if predecessor is None:
            if event.predecessor.event_id is not None or event.predecessor.event_sha256 is not None:
                raise _invalid("first event must have an empty predecessor")
        else:
            if event.predecessor.event_id != predecessor.event_id:
                raise _invalid("predecessor event ID does not match prior event")
            if event.predecessor.event_sha256 != predecessor.event_sha256:
                raise _invalid("predecessor hash does not match prior event")
            if event.decided_on < predecessor.decided_on:
                raise _invalid("event dates must be non-decreasing")
        for value, field in (
            (event.proposal_semantic_sha256, "proposal_semantic_sha256"),
            (event.decision_semantic_sha256, "decision_semantic_sha256"),
            (event.authority.permission_policy_sha256, "permission_policy_sha256"),
            (event.mutation.preview_token, "preview_token"),
            (event.mutation.request_fingerprint_sha256, "request_fingerprint_sha256"),
            (event.event_sha256, "event_sha256"),
        ):
            _validate_sha256(value, field)
        if event.authority.owner_role != "owner":
            raise _invalid("event authority owner_role must be owner")
        validate_lineage(event.lineage, proposal_id=proposal_id, event_type=event.event_type)
        expected_hash = semantic_sha256(event.to_dict(include_hash=False))
        if event.event_sha256 != expected_hash:
            raise _invalid(f"event hash mismatch for `{event.event_id}`")
        identity_payload = {
            "event_integrity_policy_version": EVENT_INTEGRITY_POLICY_VERSION,
            **event.to_dict(include_hash=False),
        }
        identity_payload.pop("event_id")
        expected_id = EVENT_ID_PREFIX + semantic_sha256(identity_payload)[:24]
        if event.event_id != expected_id:
            raise _invalid(f"event ID mismatch for `{event.event_id}`")


def normalize_scalar(value: str, field: str, maximum_bytes: int) -> str:
    normalized = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        raise _invalid(f"{field} must be non-empty")
    if _CONTROL.search(normalized):
        raise _invalid(f"{field} contains unsupported control characters")
    size = len(normalized.encode("utf-8"))
    if size > maximum_bytes:
        raise _invalid(f"{field} is {size} bytes; maximum is {maximum_bytes}")
    return normalized


def proposal_semantic_payload(proposal_id: str, proposal_text: str) -> dict[str, object]:
    _validate_proposal_id(proposal_id)
    normalized = proposal_text.replace("\r\n", "\n").replace("\r", "\n")
    sections = ("Problem", "Context", "Goals", "Non-Goals", "Proposal", "Acceptance Criteria")
    for section in sections:
        if len(re.findall(rf"^## {re.escape(section)}\s*$", normalized, flags=re.MULTILINE)) > 1:
            raise _invalid(f"proposal contains duplicate semantic section `{section}`")
    title = read_title(normalized)
    if not title:
        raise _invalid("proposal title is missing")
    payload: dict[str, object] = {
        "policy_version": PROPOSAL_SEMANTICS_POLICY_VERSION,
        "proposal_id": proposal_id,
        "title": _normalize_markdown_value(title),
    }
    for section in sections:
        value = read_markdown_section(normalized, section) or ""
        payload[_semantic_key(section)] = _normalize_markdown_value(value)
    return payload


def proposal_semantic_sha256(proposal_id: str, proposal_text: str) -> str:
    return semantic_sha256(proposal_semantic_payload(proposal_id, proposal_text))


def decision_semantic_sha256(
    *,
    proposal_sha256: str,
    outcome: ProposalDecisionEffectiveState,
    rationale: str,
    conditions: tuple[ProposalDecisionCondition, ...] = (),
) -> str:
    _validate_sha256(proposal_sha256, "proposal_sha256")
    normalized_rationale = normalize_scalar(rationale, "rationale", MAX_RATIONALE_BYTES)
    validate_conditions(
        conditions,
        required=outcome == ProposalDecisionEffectiveState.accepted_with_changes,
    )
    return semantic_sha256(
        {
            "policy_version": DECISION_SEMANTICS_POLICY_VERSION,
            "proposal_semantic_sha256": proposal_sha256,
            "outcome": outcome.value,
            "rationale": normalized_rationale,
            "conditions": [item.to_dict() for item in conditions],
        }
    )


def operation_key(request_semantics: Mapping[str, object], source_head_event_id: str | None) -> str:
    return OPERATION_KEY_PREFIX + semantic_sha256(
        {
            "request": dict(request_semantics),
            "source_head_event_id": source_head_event_id,
        }
    )[:24]


def validate_conditions(
    conditions: tuple[ProposalDecisionCondition, ...],
    *,
    required: bool,
) -> None:
    if required and not conditions:
        raise _invalid("accepted_with_changes requires at least one structured condition")
    if len(conditions) > MAX_CONDITIONS:
        raise _invalid(f"conditions exceed maximum count {MAX_CONDITIONS}")
    seen: set[str] = set()
    total = 0
    for item in conditions:
        condition_id = normalize_scalar(item.condition_id, "condition.id", 256)
        if condition_id in seen:
            raise _invalid(f"duplicate condition ID `{condition_id}`")
        seen.add(condition_id)
        text = normalize_scalar(item.text, "condition.text", MAX_CONDITION_BYTES)
        total += len(text.encode("utf-8"))
    if total > MAX_CONDITIONS_BYTES:
        raise _invalid(
            f"condition text is {total} bytes; maximum is {MAX_CONDITIONS_BYTES}"
        )


def validate_lineage(
    lineage: ProposalDecisionLineage,
    *,
    proposal_id: str,
    event_type: ProposalDecisionEventType,
) -> None:
    targets = tuple(str(item).strip() for item in lineage.targets)
    if len(targets) > MAX_LINEAGE_TARGETS:
        raise _invalid(f"lineage targets exceed maximum count {MAX_LINEAGE_TARGETS}")
    if any(not item for item in targets):
        raise ValueError("P2P369_DECISION_LINEAGE_INVALID: empty lineage target")
    if proposal_id in targets:
        raise ValueError("P2P369_DECISION_LINEAGE_INVALID: proposal cannot target itself")
    if len(set(targets)) != len(targets):
        raise ValueError("P2P369_DECISION_LINEAGE_INVALID: duplicate lineage target")
    for target in targets:
        _validate_proposal_id(target)
    requirements = {
        ProposalDecisionEventType.superseded: (ProposalDecisionLineageKind.supersedes, 1, 1),
        ProposalDecisionEventType.split: (ProposalDecisionLineageKind.split, 2, MAX_LINEAGE_TARGETS),
        ProposalDecisionEventType.merged_into_other: (
            ProposalDecisionLineageKind.merged_into,
            1,
            1,
        ),
    }
    requirement = requirements.get(event_type)
    if requirement is None:
        if lineage.kind is not None or targets:
            raise ValueError(
                f"P2P369_DECISION_LINEAGE_INVALID: `{event_type.value}` does not accept lineage"
            )
        return
    expected_kind, minimum, maximum = requirement
    if lineage.kind != expected_kind or not minimum <= len(targets) <= maximum:
        raise ValueError(
            f"P2P369_DECISION_LINEAGE_INVALID: `{event_type.value}` requires "
            f"{expected_kind.value} lineage with {minimum}..{maximum} targets"
        )


def render_proposal_projection(proposal_text: str, state: ProposalDecisionEffectiveState) -> str:
    if not re.search(r"^## Status\s*$", proposal_text, flags=re.MULTILINE):
        raise _invalid("proposal projection is missing Status section")
    projected = "draft" if state == ProposalDecisionEffectiveState.undecided else state.value
    return replace_section(proposal_text, "Status", f"`{projected}`")


def render_decision_projection(
    proposal_id: str,
    event: ProposalDecisionEvent | None,
    *,
    ledger_filename: str = "decision-events.yml",
    empty_state: ProposalDecisionEffectiveState = ProposalDecisionEffectiveState.undecided,
) -> str:
    if event is None:
        if empty_state == ProposalDecisionEffectiveState.undecided:
            return f"# Decision - {proposal_id}\n\n## Status\n\n`pending`\n"
        return (
            f"# Decision - {proposal_id}\n\n"
            "## Status\n\n"
            f"`{empty_state.value}`\n\n"
            "## Outcome\n\n"
            f"{empty_state.value}\n\n"
            "## Effective State\n\n"
            f"{empty_state.value}\n\n"
            "## Reason\n\n"
            "Legacy authority requires owner resolution.\n\n"
            "## Canonical Source\n\n"
            f"{ledger_filename}\n"
        )
    lineage = (
        "None."
        if event.lineage.kind is None
        else f"{event.lineage.kind.value}: {', '.join(event.lineage.targets)}"
    )
    return (
        f"# Decision - {proposal_id}\n\n"
        "## Status\n\n"
        f"`{event.effective_state.value}`\n\n"
        "## Outcome\n\n"
        f"{event.effective_state.value}\n\n"
        "## Event Type\n\n"
        f"{event.event_type.value}\n\n"
        "## Effective State\n\n"
        f"{event.effective_state.value}\n\n"
        "## Reason\n\n"
        f"{event.rationale}\n\n"
        "## Date\n\n"
        f"{event.decided_on}\n\n"
        "## Approver\n\n"
        f"{event.authority.owner_id}\n\n"
        "## Owner\n\n"
        f"{event.authority.owner_id}\n\n"
        "## Ledger Head\n\n"
        f"{event.event_id}\n\n"
        "## Decision Fingerprint\n\n"
        f"{event.decision_semantic_sha256}\n\n"
        "## Lineage\n\n"
        f"{lineage}\n\n"
        "## Canonical Source\n\n"
        f"{ledger_filename}\n"
    )


def projection_binding_status(
    proposal_id: str,
    proposal_text: str,
    event: ProposalDecisionEvent | None,
) -> ProposalDecisionBindingStatus:
    if event is None:
        return ProposalDecisionBindingStatus.current
    try:
        current = proposal_semantic_sha256(proposal_id, proposal_text)
    except ValueError:
        return ProposalDecisionBindingStatus.unavailable
    return (
        ProposalDecisionBindingStatus.current
        if current == event.proposal_semantic_sha256
        else ProposalDecisionBindingStatus.diverged
    )


def legacy_scalar(value: object) -> tuple[object, bool]:
    if not isinstance(value, str):
        return value, False
    encoded = value.encode("utf-8", errors="replace")
    if len(encoded) <= MAX_LEGACY_SCALAR_BYTES:
        return value, False
    prefix = encoded[:MAX_LEGACY_SCALAR_BYTES].decode("utf-8", errors="ignore")
    return {
        "inline_prefix": prefix,
        "original_size": len(encoded),
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "truncated": True,
    }, True


def _normalize_markdown_value(value: str) -> object:
    normalized = "\n".join(line.rstrip() for line in value.strip().splitlines())
    lines = [line.strip() for line in normalized.splitlines()]
    if lines and all(not line or line.startswith(("- ", "* ")) for line in lines):
        return [
            re.sub(r"^[-*]\s+", "", line).strip()
            for line in lines
            if line
        ]
    return normalized


def _semantic_key(section: str) -> str:
    return section.lower().replace("-", "_").replace(" ", "_")


def _invalid(message: str) -> ValueError:
    return ValueError(f"P2P361_DECISION_LEDGER_INVALID: {message}")


def _closed_keys(value: Mapping[object, object], allowed: frozenset[str], field: str) -> None:
    unknown = {str(key) for key in value if key not in allowed}
    if unknown:
        raise _invalid(f"{field} has unknown fields: {', '.join(sorted(unknown))}")


def _required_mapping(value: Mapping[str, object], key: str) -> dict[str, object]:
    raw = value.get(key)
    if not isinstance(raw, dict):
        raise _invalid(f"{key} must be a mapping")
    return raw


def _mapping(value: object, field: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise _invalid(f"{field} must be a mapping")
    return {str(key): item for key, item in value.items()}


def _string_mapping(value: object, field: str) -> dict[str, str]:
    raw = _mapping(value, field)
    result: dict[str, str] = {}
    for key, item in raw.items():
        text = str(item or "").strip()
        _validate_sha256(text, f"{field}.{key}")
        result[key] = text
    return result


def _required_list(value: Mapping[str, object], key: str) -> list[object]:
    raw = value.get(key)
    if not isinstance(raw, list):
        raise _invalid(f"{key} must be a sequence")
    return raw


def _required_text(value: Mapping[str, object], key: str) -> str:
    raw = value.get(key)
    if not isinstance(raw, str) or not raw.strip():
        raise _invalid(f"{key} must be a non-empty string")
    return raw.strip()


def _optional_text(value: object, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise _invalid(f"{field} must be a non-empty string or null")
    return value.strip()


def _required_int(value: Mapping[str, object], key: str) -> int:
    raw = value.get(key)
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise _invalid(f"{key} must be an integer")
    return raw


def _required_bool(value: Mapping[str, object], key: str) -> bool:
    raw = value.get(key)
    if not isinstance(raw, bool):
        raise _invalid(f"{key} must be a boolean")
    return raw


def _text_tuple(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise _invalid(f"{field} must be a sequence")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise _invalid(f"{field} must contain non-empty strings")
        result.append(item.strip())
    return tuple(result)


def _enum(enum_type, value: object, field: str):
    try:
        return enum_type(value)
    except (TypeError, ValueError) as exc:
        raise _invalid(f"invalid {field}: {value}") from exc


def _validate_date(value: str) -> None:
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise _invalid(f"invalid canonical decision date `{value}`") from exc
    if parsed.isoformat() != value:
        raise _invalid(f"decision date must be canonical ISO date: `{value}`")


def _validate_sha256(value: str, field: str) -> None:
    if not _SHA256.fullmatch(str(value or "")):
        raise _invalid(f"{field} must be 64 lowercase hex characters")


def _validate_proposal_id(value: str) -> None:
    if not _PROPOSAL_ID.fullmatch(str(value or "")):
        raise _invalid(f"invalid proposal ID `{value}`")
