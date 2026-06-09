from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from p2p_engine.core.proposal_artifact_state import (
    ProposalArtifactConfirmation,
    ProposalArtifactExpectation,
    ProposalArtifactOperation,
    ProposalArtifactRecord,
    ProposalArtifactRiskFlag,
    ProposalArtifactStateView,
    ProposalArtifactStatus,
)
from p2p_engine.foundation.files import read_yaml_mapping as _read_yaml_mapping
from p2p_engine.foundation.files import relative_to_root as _relative_to_root
from p2p_engine.foundation.files import yaml_dump as _yaml_dump

ARTIFACT_STATE_FILENAME = "artifact-state.yml"
ARTIFACT_STATE_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ArtifactDefinition:
    artifact_id: str
    filename: str
    default_expectation: ProposalArtifactExpectation


ARTIFACT_DEFINITIONS: tuple[ArtifactDefinition, ...] = (
    ArtifactDefinition("proposal", "proposal.md", ProposalArtifactExpectation.required),
    ArtifactDefinition("readiness", "readiness.yml", ProposalArtifactExpectation.required),
    ArtifactDefinition("open_questions", "open-questions.md", ProposalArtifactExpectation.required),
    ArtifactDefinition("clarifications", "clarifications.md", ProposalArtifactExpectation.required_when_applicable),
    ArtifactDefinition("findings", "findings.md", ProposalArtifactExpectation.required_when_applicable),
    ArtifactDefinition("exploration", "exploration.md", ProposalArtifactExpectation.required_when_applicable),
    ArtifactDefinition("impact_map", "impact-map.yml", ProposalArtifactExpectation.required_when_applicable),
)
ARTIFACTS_BY_ID = {definition.artifact_id: definition for definition in ARTIFACT_DEFINITIONS}
ARTIFACTS_BY_FILENAME = {definition.filename: definition for definition in ARTIFACT_DEFINITIONS}
AUTO_REQUIRED_ARTIFACTS = {"findings", "impact_map"}
ALWAYS_REQUIRED_ARTIFACTS = {"proposal", "readiness", "open_questions"}

RISK_KEYWORDS: tuple[tuple[ProposalArtifactRiskFlag, tuple[str, ...]], ...] = (
    (ProposalArtifactRiskFlag.governance_policy, ("governance", "policy", "owner-controlled", "decision", "consent")),
    (ProposalArtifactRiskFlag.public_interface, ("cli", "mcp", "api", "command", "tool", "public interface")),
    (ProposalArtifactRiskFlag.persistent_state, ("storage", "schema", "registry", "registries", "layout", "persistent", ".p2p")),
    (ProposalArtifactRiskFlag.compatibility_migration, ("compatibility", "migration", "backward", "legacy", "breaking")),
    (ProposalArtifactRiskFlag.cross_module, ("cross-module", "shared service", "facade", "workflow", "core workflow")),
    (ProposalArtifactRiskFlag.permission_security_sync, ("permission", "security", "sync", "remote", "provider", "destructive")),
    (ProposalArtifactRiskFlag.source_of_truth_memory, ("source of truth", "memory", "agent instruction", "artifact-writing", "write interface")),
    (ProposalArtifactRiskFlag.user_workflow_docs_release, ("docs", "install", "release", "user-visible", "setup")),
    (ProposalArtifactRiskFlag.dependency_runtime_infra, ("dependency", "runtime", "infrastructure", "environment")),
    (ProposalArtifactRiskFlag.high_uncertainty_evidence, ("uncertainty", "evidence", "technical claim", "investigation")),
    (ProposalArtifactRiskFlag.alternatives, ("alternative", "tradeoff", "options", "multiple credible")),
    (ProposalArtifactRiskFlag.owner_clarification, ("clarification", "owner answer", "assumption")),
)


class ProposalArtifactStateService:
    def __init__(
        self,
        *,
        root: Path,
        find_proposal_dir: Callable[[str], Path],
    ) -> None:
        self.root = root
        self.find_proposal_dir = find_proposal_dir

    def read(self, proposal_id: str) -> ProposalArtifactStateView:
        proposal_dir = self.find_proposal_dir(proposal_id)
        path = proposal_dir / ARTIFACT_STATE_FILENAME
        if not path.exists():
            return _legacy_view(proposal_id, path, self.root)
        data = _read_yaml_mapping(path, default={})
        validate_proposal_artifact_state_payload(data)
        return _view_from_payload(proposal_id, path, data, self.root)

    def initialize(self, proposal_id: str, *, actor: str = "local") -> ProposalArtifactStateView:
        proposal_dir = self.find_proposal_dir(proposal_id)
        path = proposal_dir / ARTIFACT_STATE_FILENAME
        existing = _read_yaml_mapping(path, default={}) if path.exists() else {}
        text = _proposal_text(proposal_dir)
        risk_flags = detect_risk_flags(text)
        records = _initial_records(
            proposal_dir=proposal_dir,
            existing=existing,
            risk_flags=risk_flags,
            actor=actor,
        )
        now = _now()
        payload = {
            "proposal_artifacts": {
                "schema_version": ARTIFACT_STATE_SCHEMA_VERSION,
                "proposal_id": proposal_id,
                "initialized_at": _existing_initialized_at(existing) or now,
                "updated_at": now,
                "status": "active",
                "legacy": {"state": "", "reason": ""},
                "artifacts": records,
            }
        }
        validate_proposal_artifact_state_payload(payload)
        _atomic_write(path, _yaml_dump(payload))
        return self.read(proposal_id)

    def set_artifact(
        self,
        proposal_id: str,
        artifact_id: str,
        *,
        expectation: ProposalArtifactExpectation | None = None,
        status: ProposalArtifactStatus | None = None,
        reason: str = "",
        actor: str = "local",
        source: str = "agent",
        risk_flags: list[ProposalArtifactRiskFlag] | None = None,
    ) -> ProposalArtifactOperation:
        data, path = self._existing_payload(proposal_id)
        artifact_key = _normalize_artifact_id(artifact_id)
        artifacts = _artifact_payloads(data)
        item = _find_artifact_payload(artifacts, artifact_key)
        old_item = dict(item)
        if status in {ProposalArtifactStatus.not_applicable, ProposalArtifactStatus.deferred} and not reason.strip():
            raise ValueError(f"Artifact {artifact_key} status {status.value} requires a non-empty reason.")
        if expectation is not None:
            item["expectation"] = expectation.value
        if status is not None:
            item["status"] = status.value
        if reason:
            item["reason"] = reason.strip()
        if risk_flags is not None:
            item["risk_flags"] = [flag.value for flag in risk_flags]
        item["actor"] = actor
        item["source"] = source
        if item.get("confirmation") == ProposalArtifactConfirmation.owner_confirmed.value:
            item["confirmation"] = ProposalArtifactConfirmation.owner_confirmed.value
        elif source == "system":
            item["confirmation"] = ProposalArtifactConfirmation.system.value
        else:
            item["confirmation"] = ProposalArtifactConfirmation.agent_proposed.value
        item["updated_at"] = _now()
        item.setdefault("history", [])
        history = item["history"]
        if isinstance(history, list):
            history.append(_history_entry(old_item, actor=actor, source=source, reason=str(item.get("reason") or "")))
        _touch(data)
        validate_proposal_artifact_state_payload(data)
        _atomic_write(path, _yaml_dump(data))
        view = self.read(proposal_id)
        record = _find_record(view.artifacts, artifact_key)
        return ProposalArtifactOperation(
            proposal_id=proposal_id,
            path=_relative_to_root(path, self.root),
            artifact=record,
            view=view,
            message=f"Artifact state updated: {record.artifact_id}",
        )

    def confirm(
        self,
        proposal_id: str,
        artifact_id: str,
        *,
        actor: str = "owner",
    ) -> ProposalArtifactOperation:
        data, path = self._existing_payload(proposal_id)
        artifact_key = _normalize_artifact_id(artifact_id)
        item = _find_artifact_payload(_artifact_payloads(data), artifact_key)
        old_item = dict(item)
        item["confirmation"] = ProposalArtifactConfirmation.owner_confirmed.value
        item["confirmed_by"] = actor
        item["updated_at"] = _now()
        history = item.setdefault("history", [])
        if isinstance(history, list):
            history.append(_history_entry(old_item, actor=actor, source="owner", reason="Owner confirmed artifact state."))
        _touch(data)
        validate_proposal_artifact_state_payload(data)
        _atomic_write(path, _yaml_dump(data))
        view = self.read(proposal_id)
        record = _find_record(view.artifacts, artifact_key)
        return ProposalArtifactOperation(
            proposal_id=proposal_id,
            path=_relative_to_root(path, self.root),
            artifact=record,
            view=view,
            message=f"Artifact state owner-confirmed: {record.artifact_id}",
        )

    def mark_legacy(
        self,
        proposal_id: str,
        *,
        reason: str = "Proposal predates artifact-aware state.",
        actor: str = "local",
    ) -> ProposalArtifactStateView:
        proposal_dir = self.find_proposal_dir(proposal_id)
        path = proposal_dir / ARTIFACT_STATE_FILENAME
        now = _now()
        payload = {
            "proposal_artifacts": {
                "schema_version": ARTIFACT_STATE_SCHEMA_VERSION,
                "proposal_id": proposal_id,
                "initialized_at": now,
                "updated_at": now,
                "status": "legacy",
                "legacy": {
                    "state": ProposalArtifactStatus.absent_legacy.value,
                    "reason": reason.strip() or "Proposal predates artifact-aware state.",
                    "actor": actor,
                },
                "artifacts": [],
            }
        }
        validate_proposal_artifact_state_payload(payload)
        _atomic_write(path, _yaml_dump(payload))
        return self.read(proposal_id)

    def _existing_payload(self, proposal_id: str) -> tuple[dict[str, object], Path]:
        proposal_dir = self.find_proposal_dir(proposal_id)
        path = proposal_dir / ARTIFACT_STATE_FILENAME
        if not path.exists():
            raise ValueError(
                f"No artifact state exists for proposal {proposal_id}. "
                f"Run `p2p proposal artifact init {proposal_id}` or `p2p proposal artifact mark-legacy {proposal_id}`."
            )
        data = _read_yaml_mapping(path, default={})
        validate_proposal_artifact_state_payload(data)
        return data, path


def detect_risk_flags(text: str) -> list[ProposalArtifactRiskFlag]:
    lowered = text.lower()
    flags: list[ProposalArtifactRiskFlag] = []
    for flag, keywords in RISK_KEYWORDS:
        if any(keyword in lowered for keyword in keywords):
            flags.append(flag)
    return flags


def validate_proposal_artifact_state_payload(data: dict[str, object]) -> None:
    state = data.get("proposal_artifacts")
    if not isinstance(state, dict):
        raise ValueError("Artifact state must define top-level `proposal_artifacts` mapping.")
    schema_version = state.get("schema_version")
    if schema_version != ARTIFACT_STATE_SCHEMA_VERSION:
        raise ValueError(f"Unsupported proposal artifact state schema_version: {schema_version}")
    proposal_id = str(state.get("proposal_id") or "").strip()
    if not proposal_id:
        raise ValueError("Artifact state missing proposal_id.")
    status = str(state.get("status") or "active")
    if status not in {"active", "legacy"}:
        raise ValueError(f"Invalid artifact state status: {status}")
    legacy = state.get("legacy") or {}
    if legacy and not isinstance(legacy, dict):
        raise ValueError("Artifact state legacy field must be a mapping.")
    legacy_state = str(dict(legacy).get("state") or "")
    if legacy_state and legacy_state != ProposalArtifactStatus.absent_legacy.value:
        raise ValueError(f"Invalid artifact legacy state: {legacy_state}")
    artifacts = state.get("artifacts") or []
    if not isinstance(artifacts, list):
        raise ValueError("Artifact state artifacts field must be a list.")
    seen: set[str] = set()
    for item in artifacts:
        if not isinstance(item, dict):
            raise ValueError("Artifact record must be a mapping.")
        artifact_id = _normalize_artifact_id(str(item.get("id") or ""))
        if artifact_id not in ARTIFACTS_BY_ID:
            allowed = ", ".join(sorted(ARTIFACTS_BY_ID))
            raise ValueError(f"Invalid artifact id: {artifact_id}. Allowed: {allowed}")
        if artifact_id in seen:
            raise ValueError(f"Duplicate artifact id: {artifact_id}")
        seen.add(artifact_id)
        filename = str(item.get("filename") or "")
        if filename != ARTIFACTS_BY_ID[artifact_id].filename:
            raise ValueError(f"Invalid filename for artifact {artifact_id}: {filename}")
        _parse_expectation(item.get("expectation"), field=f"{artifact_id}.expectation")
        status_value = _parse_status(item.get("status"), field=f"{artifact_id}.status")
        _parse_confirmation(item.get("confirmation"), field=f"{artifact_id}.confirmation")
        reason = str(item.get("reason") or "").strip()
        if status_value in {ProposalArtifactStatus.not_applicable, ProposalArtifactStatus.deferred} and not reason:
            raise ValueError(f"Artifact {artifact_id} status {status_value.value} requires a non-empty reason.")
        risk_flags = item.get("risk_flags") or []
        if not isinstance(risk_flags, list):
            raise ValueError(f"Artifact {artifact_id} risk_flags must be a list.")
        for flag in risk_flags:
            _parse_risk_flag(flag, field=f"{artifact_id}.risk_flags")
        history = item.get("history") or []
        if not isinstance(history, list):
            raise ValueError(f"Artifact {artifact_id} history must be a list.")


def _initial_records(
    *,
    proposal_dir: Path,
    existing: dict[str, object],
    risk_flags: list[ProposalArtifactRiskFlag],
    actor: str,
) -> list[dict[str, object]]:
    existing_items = {
        _normalize_artifact_id(str(item.get("id") or "")): item
        for item in _artifact_payloads(existing)
        if isinstance(item, dict)
    }
    now = _now()
    records: list[dict[str, object]] = []
    for definition in ARTIFACT_DEFINITIONS:
        previous = dict(existing_items.get(definition.artifact_id) or {})
        expectation = _expectation_for(definition, risk_flags)
        status = _initial_status(
            proposal_dir / definition.filename,
            expectation=expectation,
            previous=previous,
        )
        flags = _risk_flags_for_artifact(definition.artifact_id, risk_flags)
        records.append(
            {
                "id": definition.artifact_id,
                "filename": definition.filename,
                "expectation": expectation.value,
                "status": status.value,
                "reason": str(previous.get("reason") or _default_reason(definition, expectation, status)),
                "source": str(previous.get("source") or "system"),
                "actor": actor,
                "confirmation": str(previous.get("confirmation") or ProposalArtifactConfirmation.system.value),
                "confirmed_by": str(previous.get("confirmed_by") or ""),
                "risk_flags": [flag.value for flag in flags],
                "created_at": str(previous.get("created_at") or now),
                "updated_at": now,
                "history": list(previous.get("history") or []),
            }
        )
    return records


def _initial_status(path: Path, *, expectation: ProposalArtifactExpectation, previous: dict[str, object]) -> ProposalArtifactStatus:
    previous_status = str(previous.get("status") or "")
    if previous_status in {item.value for item in ProposalArtifactStatus} and previous_status != ProposalArtifactStatus.absent_legacy.value:
        return ProposalArtifactStatus(previous_status)
    if expectation == ProposalArtifactExpectation.optional_memory:
        return ProposalArtifactStatus.unknown
    if not path.exists():
        return ProposalArtifactStatus.missing
    text = path.read_text(encoding="utf-8")
    quality = _artifact_quality(text)
    if quality == "missing":
        return ProposalArtifactStatus.missing
    if quality == "weak":
        return ProposalArtifactStatus.weak
    return ProposalArtifactStatus.satisfied


def _artifact_quality(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return "missing"
    lowered = stripped.lower()
    placeholders = (
        "pending.",
        "not explored yet.",
        "none identified yet.",
        "none recorded yet.",
        "not generated yet.",
        "findings: []",
    )
    if any(placeholder in lowered for placeholder in placeholders):
        return "weak"
    content = " ".join(line.strip() for line in stripped.splitlines() if line.strip() and not line.lstrip().startswith("#"))
    if len(content) < 40:
        return "weak"
    return "satisfied"


def _expectation_for(definition: ArtifactDefinition, risk_flags: list[ProposalArtifactRiskFlag]) -> ProposalArtifactExpectation:
    if definition.artifact_id in ALWAYS_REQUIRED_ARTIFACTS:
        return ProposalArtifactExpectation.required
    if definition.artifact_id in AUTO_REQUIRED_ARTIFACTS and _auto_required(risk_flags):
        return ProposalArtifactExpectation.required
    if definition.artifact_id == "exploration" and (
        ProposalArtifactRiskFlag.alternatives in risk_flags
        or ProposalArtifactRiskFlag.high_uncertainty_evidence in risk_flags
    ):
        return ProposalArtifactExpectation.required
    if definition.artifact_id == "clarifications" and ProposalArtifactRiskFlag.owner_clarification in risk_flags:
        return ProposalArtifactExpectation.required
    return definition.default_expectation


def _auto_required(risk_flags: list[ProposalArtifactRiskFlag]) -> bool:
    auto_flags = set(ProposalArtifactRiskFlag) - {
        ProposalArtifactRiskFlag.alternatives,
        ProposalArtifactRiskFlag.owner_clarification,
    }
    return bool(set(risk_flags) & auto_flags)


def _risk_flags_for_artifact(artifact_id: str, risk_flags: list[ProposalArtifactRiskFlag]) -> list[ProposalArtifactRiskFlag]:
    if artifact_id in AUTO_REQUIRED_ARTIFACTS:
        return list(risk_flags)
    if artifact_id == "exploration":
        return [flag for flag in risk_flags if flag in {ProposalArtifactRiskFlag.alternatives, ProposalArtifactRiskFlag.high_uncertainty_evidence}]
    if artifact_id == "clarifications":
        return [flag for flag in risk_flags if flag == ProposalArtifactRiskFlag.owner_clarification]
    return []


def _default_reason(
    definition: ArtifactDefinition,
    expectation: ProposalArtifactExpectation,
    status: ProposalArtifactStatus,
) -> str:
    if status == ProposalArtifactStatus.satisfied:
        return "Artifact content is present."
    if status == ProposalArtifactStatus.weak:
        return "Artifact exists but appears placeholder or thin."
    if status == ProposalArtifactStatus.missing:
        return "Artifact is expected but missing."
    if expectation == ProposalArtifactExpectation.required:
        return "Artifact is required by the graduated-by-risk policy."
    return ""


def _view_from_payload(
    proposal_id: str,
    path: Path,
    data: dict[str, object],
    root: Path,
) -> ProposalArtifactStateView:
    state = data["proposal_artifacts"]
    assert isinstance(state, dict)
    legacy = state.get("legacy") or {}
    legacy_state = None
    legacy_reason = ""
    if isinstance(legacy, dict):
        raw_state = str(legacy.get("state") or "")
        legacy_state = ProposalArtifactStatus(raw_state) if raw_state else None
        legacy_reason = str(legacy.get("reason") or "")
    records = [_record_from_payload(item) for item in _artifact_payloads(data)]
    return ProposalArtifactStateView(
        proposal_id=proposal_id,
        status=str(state.get("status") or "active"),
        path=_relative_to_root(path, root),
        schema_version=int(state.get("schema_version") or ARTIFACT_STATE_SCHEMA_VERSION),
        legacy_state=legacy_state,
        legacy_reason=legacy_reason,
        artifacts=records,
        suggested_next=_suggested_next(proposal_id, records, legacy_state),
    )


def _legacy_view(proposal_id: str, path: Path, root: Path) -> ProposalArtifactStateView:
    return ProposalArtifactStateView(
        proposal_id=proposal_id,
        status="legacy_absent",
        path=_relative_to_root(path, root),
        schema_version=None,
        legacy_state=ProposalArtifactStatus.absent_legacy,
        legacy_reason="Artifact-aware state is absent for this proposal.",
        artifacts=[],
        suggested_next=[f"p2p proposal artifact init {proposal_id}", f"p2p proposal artifact mark-legacy {proposal_id}"],
    )


def _record_from_payload(item: dict[str, object]) -> ProposalArtifactRecord:
    return ProposalArtifactRecord(
        artifact_id=_normalize_artifact_id(str(item.get("id") or "")),
        filename=str(item.get("filename") or ""),
        expectation=_parse_expectation(item.get("expectation"), field="expectation"),
        status=_parse_status(item.get("status"), field="status"),
        reason=str(item.get("reason") or ""),
        source=str(item.get("source") or ""),
        actor=str(item.get("actor") or ""),
        confirmation=_parse_confirmation(item.get("confirmation"), field="confirmation"),
        confirmed_by=str(item.get("confirmed_by") or ""),
        risk_flags=[_parse_risk_flag(flag, field="risk_flags") for flag in item.get("risk_flags") or []],
        created_at=str(item.get("created_at") or ""),
        updated_at=str(item.get("updated_at") or ""),
        history=list(item.get("history") or []),
    )


def _find_record(records: list[ProposalArtifactRecord], artifact_id: str) -> ProposalArtifactRecord:
    for record in records:
        if record.artifact_id == artifact_id:
            return record
    raise ValueError(f"Artifact not found in state: {artifact_id}")


def _find_artifact_payload(artifacts: list[dict[str, object]], artifact_id: str) -> dict[str, object]:
    if artifact_id not in ARTIFACTS_BY_ID:
        allowed = ", ".join(sorted(ARTIFACTS_BY_ID))
        raise ValueError(f"Unknown proposal artifact: {artifact_id}. Allowed artifacts: {allowed}")
    for item in artifacts:
        if _normalize_artifact_id(str(item.get("id") or "")) == artifact_id:
            return item
    raise ValueError(f"Artifact state missing record for {artifact_id}. Run `p2p proposal artifact init` to refresh records.")


def _artifact_payloads(data: dict[str, object]) -> list[dict[str, object]]:
    state = data.get("proposal_artifacts") if isinstance(data, dict) else {}
    if not isinstance(state, dict):
        return []
    artifacts = state.get("artifacts") or []
    return [item for item in artifacts if isinstance(item, dict)] if isinstance(artifacts, list) else []


def _suggested_next(
    proposal_id: str,
    records: list[ProposalArtifactRecord],
    legacy_state: ProposalArtifactStatus | None,
) -> list[str]:
    if legacy_state == ProposalArtifactStatus.absent_legacy:
        return [f"p2p proposal artifact init {proposal_id}"]
    suggested: list[str] = []
    for record in records:
        if record.status in {
            ProposalArtifactStatus.unknown,
            ProposalArtifactStatus.missing,
            ProposalArtifactStatus.weak,
            ProposalArtifactStatus.deferred,
        } and record.expectation in {
            ProposalArtifactExpectation.required,
            ProposalArtifactExpectation.required_when_applicable,
        }:
            suggested.append(f"p2p proposal artifact set {proposal_id} {record.artifact_id} --status satisfied --reason \"...\"")
    return suggested


def _parse_expectation(value: object, *, field: str) -> ProposalArtifactExpectation:
    try:
        return ProposalArtifactExpectation(str(value or ProposalArtifactExpectation.required_when_applicable.value))
    except ValueError as exc:
        allowed = ", ".join(item.value for item in ProposalArtifactExpectation)
        raise ValueError(f"Invalid proposal artifact expectation for {field}: {value}. Allowed: {allowed}") from exc


def _parse_status(value: object, *, field: str) -> ProposalArtifactStatus:
    try:
        return ProposalArtifactStatus(str(value or ProposalArtifactStatus.unknown.value))
    except ValueError as exc:
        allowed = ", ".join(item.value for item in ProposalArtifactStatus)
        raise ValueError(f"Invalid proposal artifact status for {field}: {value}. Allowed: {allowed}") from exc


def _parse_confirmation(value: object, *, field: str) -> ProposalArtifactConfirmation:
    try:
        return ProposalArtifactConfirmation(str(value or ProposalArtifactConfirmation.unconfirmed.value))
    except ValueError as exc:
        allowed = ", ".join(item.value for item in ProposalArtifactConfirmation)
        raise ValueError(f"Invalid proposal artifact confirmation for {field}: {value}. Allowed: {allowed}") from exc


def _parse_risk_flag(value: object, *, field: str) -> ProposalArtifactRiskFlag:
    try:
        return ProposalArtifactRiskFlag(str(value or ""))
    except ValueError as exc:
        allowed = ", ".join(item.value for item in ProposalArtifactRiskFlag)
        raise ValueError(f"Invalid proposal artifact risk flag for {field}: {value}. Allowed: {allowed}") from exc


def _proposal_text(proposal_dir: Path) -> str:
    parts: list[str] = []
    for filename in ("proposal.md", "clarifications.md", "alternatives.md", "findings.md", "risks.md", "assumptions.md"):
        path = proposal_dir / filename
        if path.exists():
            parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


def _normalize_artifact_id(value: str) -> str:
    raw = value.strip().lower()
    if raw in ARTIFACTS_BY_FILENAME:
        return ARTIFACTS_BY_FILENAME[raw].artifact_id
    normalized = re.sub(r"[^a-z0-9]+", "_", raw).strip("_")
    for definition in ARTIFACT_DEFINITIONS:
        filename_key = definition.filename.removesuffix(".md").removesuffix(".yml").replace("-", "_")
        if normalized == filename_key:
            return definition.artifact_id
    return normalized


def _existing_initialized_at(existing: dict[str, object]) -> str:
    state = existing.get("proposal_artifacts") if isinstance(existing, dict) else {}
    return str(state.get("initialized_at") or "") if isinstance(state, dict) else ""


def _touch(data: dict[str, object]) -> None:
    state = data.get("proposal_artifacts")
    if isinstance(state, dict):
        state["updated_at"] = _now()


def _history_entry(old_item: dict[str, object], *, actor: str, source: str, reason: str) -> dict[str, object]:
    return {
        "at": _now(),
        "actor": actor,
        "source": source,
        "previous_status": old_item.get("status", ""),
        "previous_expectation": old_item.get("expectation", ""),
        "previous_confirmation": old_item.get("confirmation", ""),
        "reason": reason,
    }


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.tmp")
    temp_path.write_text(content, encoding="utf-8")
    temp_path.replace(path)
