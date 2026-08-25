from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping

import yaml

from p2p_engine.core.authority import (
    LOCAL_AUTHORITY_POLICY_VERSION,
    AuthorityBasis,
    AuthorityContext,
    AuthorityEvidence,
    AuthorityMode,
    AuthorityRotationPreview,
    AuthorityRotationResult,
    ProjectAuthorityDescriptor,
)
from p2p_engine.core.mutation_preview import (
    MutationPreviewService,
    MutationResult,
    semantic_sha256,
    source_precondition,
)
from p2p_engine.foundation.files import yaml_dump
from p2p_engine.foundation.yaml_loaders import UNIQUE_LOADER_CONTRACT, load_yaml
from p2p_engine.services.authority import AuthorityContractCodec, ProjectAuthorityService
from p2p_engine.services.mutation_receipts import (
    MutationReceiptService,
    idempotency_key_sha256,
    validate_idempotency_key,
)
from p2p_engine.services.workspace_transactions import AtomicMutationWriter


AUTHORITY_EVENTS_PATH = ".p2p/project/authority-events.yml"
AUTHORITY_EVENTS_SCHEMA = "p2p-project-authority-events/v1"
AUTHORITY_ROTATION_OPERATION = "project-authority-rotate"
AUTHORITY_ROTATION_POLICY_VERSION = 1
AUTHORITY_EVENTS_MAX_BYTES = 4 * 1024 * 1024

_EVENT_ROOT_KEYS = frozenset({"authority_events"})
_EVENT_LEDGER_KEYS = frozenset({"schema", "events"})
_EVENT_KEYS = frozenset(
    {
        "event_id",
        "operation_key_sha256",
        "rotated_at",
        "previous_descriptor",
        "new_descriptor",
        "rotation_request",
        "authority",
        "request_fingerprint_sha256",
        "preview_token",
        "event_sha256",
    }
)


class ProjectAuthorityRotationService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        authority: ProjectAuthorityService | None = None,
        receipts: MutationReceiptService | None = None,
        atomic_writer: AtomicMutationWriter | None = None,
        clock: Callable[[], str] | None = None,
    ) -> None:
        self.root = root.resolve()
        self.p2p_dir = p2p_dir.resolve()
        self.authority = authority or ProjectAuthorityService(
            root=self.root,
            p2p_dir=self.p2p_dir,
        )
        self.receipts = receipts or MutationReceiptService(
            root=self.root,
            p2p_dir=self.p2p_dir,
        )
        self.atomic_writer = atomic_writer or AtomicMutationWriter(
            root=self.root,
            p2p_dir=self.p2p_dir,
        )
        self.codec = AuthorityContractCodec()
        self.events_path = self.root / AUTHORITY_EVENTS_PATH
        self.clock = clock or _utc_now_iso

    def validate_event_ledger(self) -> int:
        descriptor = self.authority.read_descriptor()
        _content, events = self._read_events()
        if not events:
            if descriptor.generation != 1:
                raise ValueError(
                    "P2P_AUTHORITY_CONTEXT_INVALID: rotated authority has no event history"
                )
            return 0
        target = self.codec.descriptor_from_mapping(
            _required_result_mapping(events[-1], "new_descriptor")
        )
        if target != descriptor:
            raise ValueError(
                "P2P_AUTHORITY_CONTEXT_INVALID: authority descriptor diverges "
                "from the rotation event head"
            )
        return len(events)

    def preview(
        self,
        *,
        operation_key: str,
        actor_id: str,
        executor_id: str,
        executor_kind: str,
        target_mode: str = "",
        replacement_authority_id: str = "",
        provider_id: str = "",
        provider_policy_version: str = "",
        display_name: str = "",
        rotated_at: str = "",
        authority_context: AuthorityContext | None = None,
        channel: str = "cli",
    ) -> AuthorityRotationPreview:
        validate_idempotency_key(operation_key)
        previous = self.authority.read_descriptor()
        rotation_request = self._rotation_request(
            previous,
            target_mode=target_mode,
            replacement_authority_id=replacement_authority_id,
            provider_id=provider_id,
            provider_policy_version=provider_policy_version,
            display_name=display_name,
            rotated_at=rotated_at or self.clock(),
        )
        context, evidence = self.authority.resolve(
            supplied_context=authority_context,
            subject_id=actor_id,
            executor_id=executor_id,
            executor_kind=executor_kind,
            required_capabilities=("project.authority.rotate",),
            channel=channel,
        )
        claim = context.claim_for("project.authority.rotate")
        if claim is None or claim.basis != AuthorityBasis.root_authority:
            raise ValueError(
                "P2P_AUTHORIZATION_DENIED: project authority rotation requires "
                "root-authority basis"
            )
        target = self._target_descriptor(previous, rotation_request)
        authority_bytes = self.authority.descriptor_bytes(previous)
        events_bytes, events = self._read_events()
        request_fingerprint = semantic_sha256(
            {
                "policy_version": AUTHORITY_ROTATION_POLICY_VERSION,
                "operation": "project.authority.rotate",
                "operation_key_sha256": idempotency_key_sha256(operation_key),
                "previous_descriptor": previous.to_dict(),
                "new_descriptor": target.to_dict(),
                "rotation_request": rotation_request,
                "authority_context_sha256": context.digest_sha256,
            }
        )
        event_without_preview = self._event_payload(
            operation_key=operation_key,
            rotated_at=str(rotation_request["rotated_at"]),
            previous=previous,
            target=target,
            rotation_request=rotation_request,
            authority=evidence,
            request_fingerprint=request_fingerprint,
            preview_token="0" * 64,
        )
        receipt_path = self.receipts.relative_path(operation_key)
        sources = (
            source_precondition(".p2p/project/authority.yml", authority_bytes),
            source_precondition(AUTHORITY_EVENTS_PATH, events_bytes),
            source_precondition(receipt_path, None),
        )
        mutation = MutationPreviewService.build(
            operation_id=AUTHORITY_ROTATION_OPERATION,
            targets=(
                ".p2p/project/authority.yml",
                AUTHORITY_EVENTS_PATH,
                receipt_path,
            ),
            actor=evidence.executor.identity_id,
            authority="root_authority",
            sources=sources,
            candidate_semantics={
                "previous_descriptor": previous.to_dict(),
                "new_descriptor": target.to_dict(),
                "event": {
                    key: value
                    for key, value in event_without_preview.items()
                    if key not in {"event_id", "event_sha256", "preview_token"}
                },
            },
            semantic_diff={
                "authority_id_before": previous.authority_id,
                "authority_id_after": target.authority_id,
                "mode_before": previous.mode.value,
                "mode_after": target.mode.value,
                "generation_before": previous.generation,
                "generation_after": target.generation,
            },
            token_context={
                "request_fingerprint_sha256": request_fingerprint,
                "authority_context_sha256": context.digest_sha256,
                "operation_key_sha256": idempotency_key_sha256(operation_key),
            },
            policy_version=AUTHORITY_ROTATION_POLICY_VERSION,
        )
        event = self._event_payload(
            operation_key=operation_key,
            rotated_at=str(rotation_request["rotated_at"]),
            previous=previous,
            target=target,
            rotation_request=rotation_request,
            authority=evidence,
            request_fingerprint=request_fingerprint,
            preview_token=mutation.preview_token,
        )
        candidates = {
            ".p2p/project/authority.yml": self.authority.descriptor_bytes(target),
            AUTHORITY_EVENTS_PATH: self._events_bytes([*events, event]),
        }
        self._validate_candidates(candidates, expected_previous=previous)
        return AuthorityRotationPreview(
            previous_descriptor=previous,
            new_descriptor=target,
            authority=evidence,
            mutation=mutation,
            rotation_request=rotation_request,
            candidate_bytes=candidates,
        )

    def apply(
        self,
        *,
        operation_key: str,
        actor_id: str,
        executor_id: str,
        executor_kind: str,
        preview_token: str,
        confirm: bool,
        target_mode: str = "",
        replacement_authority_id: str = "",
        provider_id: str = "",
        provider_policy_version: str = "",
        display_name: str = "",
        rotated_at: str = "",
        authority_context: AuthorityContext | None = None,
        channel: str = "cli",
    ) -> AuthorityRotationResult:
        replay = self._exact_replay(
            operation_key=operation_key,
            actor_id=actor_id,
            executor_id=executor_id,
            executor_kind=executor_kind,
            target_mode=target_mode,
            replacement_authority_id=replacement_authority_id,
            provider_id=provider_id,
            provider_policy_version=provider_policy_version,
            display_name=display_name,
            rotated_at=rotated_at,
            authority_context=authority_context,
        )
        if replay is not None:
            return replay
        preview = self.preview(
            operation_key=operation_key,
            actor_id=actor_id,
            executor_id=executor_id,
            executor_kind=executor_kind,
            target_mode=target_mode,
            replacement_authority_id=replacement_authority_id,
            provider_id=provider_id,
            provider_policy_version=provider_policy_version,
            display_name=display_name,
            rotated_at=rotated_at,
            authority_context=authority_context,
            channel=channel,
        )
        if not confirm:
            return AuthorityRotationResult(
                status="blocked",
                previous_descriptor=preview.previous_descriptor,
                new_descriptor=preview.new_descriptor,
                authority=preview.authority,
                event_id=self._candidate_event_id(preview.candidate_bytes),
                mutation=MutationResult(
                    status="blocked",
                    operation_id=AUTHORITY_ROTATION_OPERATION,
                    preview_token=preview.mutation.preview_token,
                    actor=preview.authority.executor.identity_id,
                    message="Explicit confirmation is required.",
                ),
                message="Explicit confirmation is required.",
            )
        if preview.mutation.preview_token != preview_token:
            return AuthorityRotationResult(
                status="stale_preview",
                previous_descriptor=preview.previous_descriptor,
                new_descriptor=preview.new_descriptor,
                authority=preview.authority,
                event_id=self._candidate_event_id(preview.candidate_bytes),
                mutation=MutationResult(
                    status="stale_preview",
                    operation_id=AUTHORITY_ROTATION_OPERATION,
                    preview_token=preview.mutation.preview_token,
                    actor=preview.authority.executor.identity_id,
                    message="P2P_AUTHORITY_GENERATION_STALE: rotation preview changed.",
                ),
                message="Rotation preview changed.",
            )
        event_id = self._candidate_event_id(preview.candidate_bytes)
        summary = {
            "operation": "project_authority_rotate",
            "operation_id": "project.authority.rotate",
            "previous_descriptor": preview.previous_descriptor.to_dict(),
            "new_descriptor": preview.new_descriptor.to_dict(),
            "rotation_request": dict(preview.rotation_request),
            "event_id": event_id,
            "event_path": AUTHORITY_EVENTS_PATH,
            "changed_paths": [
                AUTHORITY_EVENTS_PATH,
                ".p2p/project/authority.yml",
            ],
        }
        request_fingerprint = self._candidate_request_fingerprint(
            preview.candidate_bytes
        )
        receipt_path, receipt_content, _receipt = self.receipts.prepare(
            idempotency_key=operation_key,
            operation="project_authority_rotate",
            actor=preview.authority.executor.identity_id,
            request_fingerprint_sha256=request_fingerprint,
            preview_token=preview.mutation.preview_token,
            result=summary,
            candidates=preview.candidate_bytes,
            authority=preview.authority,
        )
        mutation = self.atomic_writer.apply(
            operation_id=AUTHORITY_ROTATION_OPERATION,
            candidates={**preview.candidate_bytes, receipt_path: receipt_content},
            sources=preview.mutation.source_preconditions,
            preview_token=preview.mutation.preview_token,
            actor=preview.authority.executor.identity_id,
            candidate_validator=lambda view: self._validate_candidates(
                {
                    path: view.read_bytes(path)
                    for path in preview.candidate_bytes
                },
                expected_previous=preview.previous_descriptor,
            ),
        )
        if mutation.status != "applied":
            replay = self._exact_replay(
                operation_key=operation_key,
                actor_id=actor_id,
                executor_id=executor_id,
                executor_kind=executor_kind,
                target_mode=target_mode,
                replacement_authority_id=replacement_authority_id,
                provider_id=provider_id,
                provider_policy_version=provider_policy_version,
                display_name=display_name,
                rotated_at=rotated_at,
                authority_context=authority_context,
            )
            if replay is not None:
                return replay
            return AuthorityRotationResult(
                status=mutation.status,
                previous_descriptor=preview.previous_descriptor,
                new_descriptor=preview.new_descriptor,
                authority=preview.authority,
                event_id=event_id,
                mutation=mutation,
                message=mutation.message,
            )
        return AuthorityRotationResult(
            status="applied",
            previous_descriptor=preview.previous_descriptor,
            new_descriptor=preview.new_descriptor,
            authority=preview.authority,
            event_id=event_id,
            mutation=mutation,
            message="Project authority rotation committed atomically.",
        )

    def _exact_replay(
        self,
        *,
        operation_key: str,
        actor_id: str,
        executor_id: str,
        executor_kind: str,
        target_mode: str,
        replacement_authority_id: str,
        provider_id: str,
        provider_policy_version: str,
        display_name: str,
        rotated_at: str,
        authority_context: AuthorityContext | None,
    ) -> AuthorityRotationResult | None:
        receipt = self.receipts.read(idempotency_key=operation_key)
        if receipt is None:
            return None
        if receipt.operation != "project_authority_rotate" or receipt.authority is None:
            raise ValueError(
                "P2P_IDEMPOTENCY_CONFLICT: operation key belongs to another mutation"
            )
        result = receipt.result
        request = result.get("rotation_request")
        if not isinstance(request, Mapping):
            raise ValueError("P2P_IDEMPOTENCY_RECEIPT_CORRUPT: rotation request is missing")
        expected_input = {
            "target_mode": target_mode or str(request.get("target_mode") or ""),
            "replacement_authority_id": replacement_authority_id,
            "provider_id": provider_id,
            "provider_policy_version": provider_policy_version,
            "display_name": display_name,
            "rotated_at": rotated_at,
        }
        if any(
            expected_input[key] and expected_input[key] != request.get(key)
            for key in expected_input
        ):
            raise ValueError(
                "P2P_IDEMPOTENCY_CONFLICT: operation key is bound to different rotation inputs"
            )
        evidence = self.codec.evidence_from_mapping(receipt.authority)
        if authority_context is not None and authority_context.digest_sha256 != evidence.authority_context_sha256:
            raise ValueError(
                "P2P_IDEMPOTENCY_CONFLICT: operation key is bound to different authority evidence"
            )
        if authority_context is None and (
            actor_id != evidence.subject.identity_id
            or executor_id != evidence.executor.identity_id
            or executor_kind != evidence.executor.kind.value
        ):
            raise ValueError(
                "P2P_IDEMPOTENCY_CONFLICT: operation key is bound to different subject or executor"
            )
        previous = self.codec.descriptor_from_mapping(
            _required_result_mapping(result, "previous_descriptor")
        )
        target = self.codec.descriptor_from_mapping(
            _required_result_mapping(result, "new_descriptor")
        )
        return AuthorityRotationResult(
            status="already_applied",
            previous_descriptor=previous,
            new_descriptor=target,
            authority=evidence,
            event_id=str(result.get("event_id") or ""),
            mutation=MutationResult(
                status="already_applied",
                operation_id=AUTHORITY_ROTATION_OPERATION,
                preview_token="",
                actor=evidence.executor.identity_id,
                message="Exact project authority rotation was already committed.",
            ),
            message="Exact project authority rotation was already committed.",
        )

    def _rotation_request(
        self,
        previous: ProjectAuthorityDescriptor,
        *,
        target_mode: str,
        replacement_authority_id: str,
        provider_id: str,
        provider_policy_version: str,
        display_name: str,
        rotated_at: str,
    ) -> dict[str, object]:
        try:
            mode = AuthorityMode(target_mode or previous.mode.value)
        except ValueError as exc:
            raise ValueError("P2P_AUTHORITY_CONTEXT_INVALID: target mode is unsupported") from exc
        timestamp = _normalize_timestamp(rotated_at)
        selected_provider = provider_id or (
            previous.provider_id if mode == AuthorityMode.external_attestation else ""
        )
        selected_policy = provider_policy_version or (
            previous.provider_policy_version
            if mode == AuthorityMode.external_attestation
            else ""
        )
        if mode == AuthorityMode.external_attestation and (
            not selected_provider or not selected_policy
        ):
            raise ValueError(
                "P2P_AUTHORITY_CONTEXT_INVALID: external target requires provider and policy version"
            )
        provider_changed = (
            mode != previous.mode
            or (
                mode == AuthorityMode.external_attestation
                and selected_provider != previous.provider_id
            )
        )
        if provider_changed and not replacement_authority_id:
            raise ValueError(
                "P2P_AUTHORITY_CONTEXT_INVALID: mode/provider replacement requires "
                "a replacement authority ID"
            )
        return {
            "target_mode": mode.value,
            "replacement_authority_id": replacement_authority_id,
            "provider_id": selected_provider,
            "provider_policy_version": selected_policy,
            "display_name": display_name,
            "rotated_at": timestamp,
        }

    def _target_descriptor(
        self,
        previous: ProjectAuthorityDescriptor,
        request: Mapping[str, object],
    ) -> ProjectAuthorityDescriptor:
        mode = AuthorityMode(str(request["target_mode"]))
        replacement_id = str(request["replacement_authority_id"] or "")
        target = ProjectAuthorityDescriptor(
            authority_id=replacement_id or previous.authority_id,
            mode=mode,
            generation=previous.generation + 1,
            display_name=str(request["display_name"] or previous.display_name),
            local_policy_version=(
                LOCAL_AUTHORITY_POLICY_VERSION
                if mode == AuthorityMode.local_policy
                else None
            ),
            provider_id=(
                str(request["provider_id"])
                if mode == AuthorityMode.external_attestation
                else None
            ),
            provider_policy_version=(
                str(request["provider_policy_version"])
                if mode == AuthorityMode.external_attestation
                else None
            ),
        )
        return self.codec.descriptor_from_mapping(target.to_payload())

    def _event_payload(
        self,
        *,
        operation_key: str,
        rotated_at: str,
        previous: ProjectAuthorityDescriptor,
        target: ProjectAuthorityDescriptor,
        rotation_request: Mapping[str, object],
        authority: AuthorityEvidence,
        request_fingerprint: str,
        preview_token: str,
    ) -> dict[str, object]:
        semantic = {
            "operation_key_sha256": idempotency_key_sha256(operation_key),
            "rotated_at": rotated_at,
            "previous_descriptor": previous.to_dict(),
            "new_descriptor": target.to_dict(),
            "rotation_request": dict(rotation_request),
            "authority": authority.to_dict(),
            "request_fingerprint_sha256": request_fingerprint,
        }
        event_id = "PAE-" + semantic_sha256(semantic)[:24]
        payload = {
            "event_id": event_id,
            **semantic,
            "preview_token": preview_token,
        }
        return {**payload, "event_sha256": semantic_sha256(payload)}

    def _read_events(self) -> tuple[bytes | None, list[dict[str, object]]]:
        if not self.events_path.exists():
            return None, []
        if self.events_path.is_symlink() or not self.events_path.is_file():
            raise ValueError("P2P_AUTHORITY_CONTEXT_INVALID: authority event path is unsafe")
        content = self.events_path.read_bytes()
        return content, self._parse_events(content)

    def _parse_events(self, content: bytes) -> list[dict[str, object]]:
        if len(content) > AUTHORITY_EVENTS_MAX_BYTES:
            raise ValueError("P2P_AUTHORITY_CONTEXT_INVALID: authority events exceed size limit")
        try:
            payload = load_yaml(content, loader_contract=UNIQUE_LOADER_CONTRACT)
        except (UnicodeDecodeError, ValueError, yaml.YAMLError) as exc:
            raise ValueError(f"P2P_AUTHORITY_CONTEXT_INVALID: invalid authority events: {exc}") from exc
        if not isinstance(payload, Mapping) or set(payload) != _EVENT_ROOT_KEYS:
            raise ValueError("P2P_AUTHORITY_CONTEXT_INVALID: invalid authority events root")
        ledger = payload.get("authority_events")
        if not isinstance(ledger, Mapping) or set(ledger) != _EVENT_LEDGER_KEYS:
            raise ValueError("P2P_AUTHORITY_CONTEXT_INVALID: invalid authority events ledger")
        if ledger.get("schema") != AUTHORITY_EVENTS_SCHEMA:
            raise ValueError("P2P_AUTHORITY_CONTEXT_INVALID: unsupported authority events schema")
        raw_events = ledger.get("events")
        if not isinstance(raw_events, list):
            raise ValueError("P2P_AUTHORITY_CONTEXT_INVALID: authority events must be a sequence")
        events: list[dict[str, object]] = []
        previous_target: ProjectAuthorityDescriptor | None = None
        ids: set[str] = set()
        for raw in raw_events:
            if not isinstance(raw, Mapping) or set(raw) != _EVENT_KEYS:
                raise ValueError("P2P_AUTHORITY_CONTEXT_INVALID: authority event has invalid fields")
            event = dict(raw)
            event_id = str(event.get("event_id") or "")
            if not event_id.startswith("PAE-") or event_id in ids:
                raise ValueError("P2P_AUTHORITY_CONTEXT_INVALID: invalid or duplicate authority event ID")
            ids.add(event_id)
            previous = self.codec.descriptor_from_mapping(
                _required_result_mapping(event, "previous_descriptor")
            )
            target = self.codec.descriptor_from_mapping(
                _required_result_mapping(event, "new_descriptor")
            )
            evidence = self.codec.evidence_from_mapping(
                _required_result_mapping(event, "authority")
            )
            if target.generation != previous.generation + 1:
                raise ValueError("P2P_AUTHORITY_CONTEXT_INVALID: invalid authority event generation")
            if previous_target is not None and previous != previous_target:
                raise ValueError("P2P_AUTHORITY_CONTEXT_INVALID: authority event chain diverges")
            if (
                evidence.authority_id != previous.authority_id
                or evidence.authority_generation != previous.generation
            ):
                raise ValueError("P2P_AUTHORITY_CONTEXT_INVALID: event authority evidence is stale")
            event_hash = str(event.get("event_sha256") or "")
            hash_payload = dict(event)
            hash_payload.pop("event_sha256", None)
            if event_hash != semantic_sha256(hash_payload):
                raise ValueError("P2P_AUTHORITY_CONTEXT_INVALID: authority event hash mismatch")
            identity_payload = {
                key: value
                for key, value in hash_payload.items()
                if key not in {"event_id", "preview_token"}
            }
            if event_id != "PAE-" + semantic_sha256(identity_payload)[:24]:
                raise ValueError("P2P_AUTHORITY_CONTEXT_INVALID: authority event ID mismatch")
            previous_target = target
            events.append(event)
        return events

    def _events_bytes(self, events: list[dict[str, object]]) -> bytes:
        content = yaml_dump(
            {
                "authority_events": {
                    "schema": AUTHORITY_EVENTS_SCHEMA,
                    "events": events,
                }
            }
        ).encode("ascii")
        self._parse_events(content)
        return content

    def _validate_candidates(
        self,
        candidates: Mapping[str, bytes],
        *,
        expected_previous: ProjectAuthorityDescriptor,
    ) -> None:
        target = self.codec.descriptor_from_bytes(
            candidates[".p2p/project/authority.yml"]
        )
        events = self._parse_events(candidates[AUTHORITY_EVENTS_PATH])
        if not events:
            raise ValueError("P2P_AUTHORITY_CONTEXT_INVALID: rotation event is missing")
        final = self.codec.descriptor_from_mapping(
            _required_result_mapping(events[-1], "new_descriptor")
        )
        previous = self.codec.descriptor_from_mapping(
            _required_result_mapping(events[-1], "previous_descriptor")
        )
        if previous != expected_previous or final != target:
            raise ValueError("P2P_AUTHORITY_CONTEXT_INVALID: rotation candidate is inconsistent")

    def _candidate_event_id(self, candidates: Mapping[str, bytes]) -> str:
        return str(self._parse_events(candidates[AUTHORITY_EVENTS_PATH])[-1]["event_id"])

    def _candidate_request_fingerprint(self, candidates: Mapping[str, bytes]) -> str:
        return str(
            self._parse_events(candidates[AUTHORITY_EVENTS_PATH])[-1][
                "request_fingerprint_sha256"
            ]
        )


def _required_result_mapping(
    value: Mapping[str, object],
    field: str,
) -> Mapping[str, object]:
    raw = value.get(field)
    if not isinstance(raw, Mapping):
        raise ValueError(f"P2P_AUTHORITY_CONTEXT_INVALID: {field} must be a mapping")
    return raw


def _normalize_timestamp(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("P2P_AUTHORITY_CONTEXT_INVALID: rotated_at must be ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("P2P_AUTHORITY_CONTEXT_INVALID: rotated_at requires timezone")
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )
