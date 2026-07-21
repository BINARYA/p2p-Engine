from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Mapping, Sequence


MUTATION_PREVIEW_POLICY_VERSION = 1


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
        default=_json_default,
    ).encode("utf-8")


def _json_default(value: object) -> object:
    if isinstance(value, (date, datetime)):
        return value.isoformat().replace("+00:00", "Z")
    raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")


def semantic_sha256(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


@dataclass(frozen=True)
class SourcePrecondition:
    path: str
    exists: bool
    physical_sha256: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "exists": self.exists,
            "physical_sha256": self.physical_sha256,
        }


@dataclass(frozen=True)
class MutationPreview:
    operation_id: str
    targets: tuple[str, ...]
    actor: str
    authority: str
    confirmation_required: bool
    source_preconditions: tuple[SourcePrecondition, ...]
    semantic_diff: Mapping[str, object]
    candidate_semantic_hashes: Mapping[str, str]
    preview_token: str
    policy_version: int = MUTATION_PREVIEW_POLICY_VERSION
    apply_allowed: bool = True
    blockers: tuple[str, ...] = ()
    token_context: Mapping[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        payload = {
            "operation_id": self.operation_id,
            "targets": list(self.targets),
            "actor": self.actor,
            "authority": self.authority,
            "confirmation_required": self.confirmation_required,
            "source_preconditions": [item.to_dict() for item in self.source_preconditions],
            "semantic_diff": dict(self.semantic_diff),
            "candidate_semantic_hashes": dict(self.candidate_semantic_hashes),
            "preview_token": self.preview_token,
            "policy_version": self.policy_version,
            "apply_allowed": self.apply_allowed,
            "blockers": list(self.blockers),
        }
        if self.token_context:
            payload["token_context"] = dict(self.token_context)
        return payload


@dataclass(frozen=True)
class MutationResult:
    status: str
    operation_id: str
    changed_paths: tuple[str, ...] = ()
    restored_paths: tuple[str, ...] = ()
    final_physical_hashes: Mapping[str, str] = field(default_factory=dict)
    preview_token: str = ""
    actor: str = ""
    message: str = ""
    recovery_required: bool = False
    derived_updates: Mapping[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "status": self.status,
            "operation_id": self.operation_id,
            "changed_paths": list(self.changed_paths),
            "restored_paths": list(self.restored_paths),
            "final_physical_hashes": dict(self.final_physical_hashes),
            "preview_token": self.preview_token,
            "actor": self.actor,
            "message": self.message,
            "recovery_required": self.recovery_required,
        }
        if self.derived_updates:
            payload["derived_updates"] = dict(self.derived_updates)
        return payload


class MutationPreviewService:
    @staticmethod
    def token(
        *,
        operation_id: str,
        targets: Sequence[str],
        sources: Sequence[SourcePrecondition],
        candidate_semantics: Mapping[str, object],
        token_context: Mapping[str, object] | None = None,
        policy_version: int = MUTATION_PREVIEW_POLICY_VERSION,
    ) -> str:
        payload = {
            "operation_id": operation_id,
            "targets": sorted(str(target) for target in targets),
            "sources": [
                item.to_dict()
                for item in sorted(sources, key=lambda source: source.path)
            ],
            "candidate_semantics": {
                key: candidate_semantics[key] for key in sorted(candidate_semantics)
            },
            "policy_version": policy_version,
        }
        if token_context is not None:
            payload["token_context"] = {
                key: token_context[key] for key in sorted(token_context)
            }
        return semantic_sha256(payload)

    @staticmethod
    def build(
        *,
        operation_id: str,
        targets: Sequence[str],
        actor: str,
        authority: str,
        sources: Sequence[SourcePrecondition],
        candidate_semantics: Mapping[str, object],
        semantic_diff: Mapping[str, object],
        token_context: Mapping[str, object] | None = None,
        confirmation_required: bool = True,
        blockers: Sequence[str] = (),
        policy_version: int = MUTATION_PREVIEW_POLICY_VERSION,
    ) -> MutationPreview:
        normalized_targets = tuple(sorted(str(target) for target in targets))
        normalized_sources = tuple(sorted(sources, key=lambda source: source.path))
        candidate_hashes = {
            key: semantic_sha256(candidate_semantics[key])
            for key in sorted(candidate_semantics)
        }
        token = MutationPreviewService.token(
            operation_id=operation_id,
            targets=normalized_targets,
            sources=normalized_sources,
            candidate_semantics=candidate_semantics,
            token_context=token_context,
            policy_version=policy_version,
        )
        normalized_blockers = tuple(str(item) for item in blockers)
        return MutationPreview(
            operation_id=operation_id,
            targets=normalized_targets,
            actor=actor,
            authority=authority,
            confirmation_required=confirmation_required,
            source_preconditions=normalized_sources,
            semantic_diff=dict(semantic_diff),
            candidate_semantic_hashes=candidate_hashes,
            preview_token=token,
            policy_version=policy_version,
            apply_allowed=not normalized_blockers,
            blockers=normalized_blockers,
            token_context=dict(token_context or {}),
        )


def source_precondition(path: str, content: bytes | None) -> SourcePrecondition:
    return SourcePrecondition(
        path=path,
        exists=content is not None,
        physical_sha256=hashlib.sha256(content).hexdigest() if content is not None else None,
    )
