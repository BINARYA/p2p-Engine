from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Mapping, Sequence

from p2p_engine.core.mutation_preview import MutationPreview
from p2p_engine.core.project_structure import (
    PROJECT_STRUCTURE_ELEMENT_KINDS,
    ProjectStructure,
    ProjectStructureEvent,
    normalize_structure_id,
    normalize_structure_text,
)
from p2p_engine.core.project_structure_retirement import (
    StructureRetirementDisposition,
    StructureRetirementImpact,
    structure_retirement_disposition_from_mapping,
)


STRUCTURE_REPLACEMENT_IMPACT_CONTRACT = "p2p-structure-replacement-impact/v1"
STRUCTURE_REPLACEMENT_PLAN_CONTRACT = "p2p-structure-replacement-plan/v1"
STRUCTURE_REPLACEMENT_RESULT_CONTRACT = "p2p-structure-replacement-result/v1"
PROJECT_STRUCTURE_REPLACEMENT_OPERATION = "project_structure_replacement"
PROJECT_STRUCTURE_REPLACEMENT_OPERATION_ID = "project.structure.replace.apply"
PROJECT_STRUCTURE_REPLACEMENT_CAPABILITY = "project.structure.replace"


@dataclass(frozen=True)
class StructureReplacementRelease:
    reference: str
    coordinate: str
    semantic_checksum: str
    schema_version: int
    source_type: str
    resolved_from: str
    artifact_checksum: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "reference",
            normalize_structure_text(
                self.reference,
                field_name="replacement.reference",
                maximum_bytes=512,
            ),
        )
        object.__setattr__(
            self,
            "coordinate",
            normalize_structure_text(
                self.coordinate,
                field_name="replacement.coordinate",
                maximum_bytes=256,
            ),
        )
        checksum = str(self.semantic_checksum or "").removeprefix("sha256:")
        if len(checksum) != 64 or any(char not in "0123456789abcdef" for char in checksum):
            raise ValueError("P2P_STRUCTURE_REPLACEMENT_TARGET_INVALID: semantic checksum must be SHA-256")
        object.__setattr__(self, "semantic_checksum", checksum)
        if isinstance(self.schema_version, bool) or not isinstance(self.schema_version, int):
            raise ValueError("P2P_STRUCTURE_REPLACEMENT_TARGET_INVALID: schema_version is invalid")
        object.__setattr__(
            self,
            "source_type",
            normalize_structure_text(
                self.source_type,
                field_name="replacement.source_type",
                maximum_bytes=64,
                required=False,
            ),
        )
        object.__setattr__(
            self,
            "resolved_from",
            normalize_structure_text(
                self.resolved_from,
                field_name="replacement.resolved_from",
                maximum_bytes=512,
                required=False,
            ),
        )
        artifact_checksum = str(self.artifact_checksum or "").removeprefix("sha256:")
        if artifact_checksum and (
            len(artifact_checksum) != 64
            or any(char not in "0123456789abcdef" for char in artifact_checksum)
        ):
            raise ValueError("P2P_STRUCTURE_REPLACEMENT_TARGET_INVALID: artifact checksum must be SHA-256")
        object.__setattr__(self, "artifact_checksum", artifact_checksum)

    def to_dict(self) -> dict[str, object]:
        payload = {
            "reference": self.reference,
            "coordinate": self.coordinate,
            "semantic_checksum": self.semantic_checksum,
            "schema_version": self.schema_version,
            "source_type": self.source_type,
            "resolved_from": self.resolved_from,
        }
        if self.artifact_checksum:
            payload["artifact_checksum"] = self.artifact_checksum
        return payload


@dataclass(frozen=True)
class StructureReplacementElement:
    kind: str
    identity: str
    state: str
    current_hash: str = ""
    target_hash: str = ""
    message: str = ""

    def __post_init__(self) -> None:
        kind = str(self.kind).strip().lower()
        if kind not in PROJECT_STRUCTURE_ELEMENT_KINDS:
            raise ValueError("P2P_STRUCTURE_REPLACEMENT_ELEMENT_INVALID: unsupported kind")
        if self.state not in {"preserved", "added", "retired", "conflicting"}:
            raise ValueError("P2P_STRUCTURE_REPLACEMENT_ELEMENT_INVALID: unsupported state")
        object.__setattr__(self, "kind", kind)
        object.__setattr__(
            self,
            "identity",
            normalize_structure_text(
                self.identity,
                field_name="replacement.element.identity",
                maximum_bytes=256,
            ),
        )
        for value, field_name in (
            (self.current_hash, "current_hash"),
            (self.target_hash, "target_hash"),
        ):
            if value and (len(value) != 64 or any(char not in "0123456789abcdef" for char in value)):
                raise ValueError(f"P2P_STRUCTURE_REPLACEMENT_ELEMENT_INVALID: {field_name} must be SHA-256")
        object.__setattr__(
            self,
            "message",
            normalize_structure_text(
                self.message,
                field_name="replacement.element.message",
                maximum_bytes=1000,
                required=False,
            ),
        )

    def to_dict(self) -> dict[str, object]:
        payload = {
            "kind": self.kind,
            "identity": self.identity,
            "state": self.state,
        }
        if self.current_hash:
            payload["current_hash"] = self.current_hash
        if self.target_hash:
            payload["target_hash"] = self.target_hash
        if self.message:
            payload["message"] = self.message
        return payload


@dataclass(frozen=True)
class StructureReplacementPlan:
    target_coordinate: str
    target_semantic_checksum: str
    dispositions: tuple[StructureRetirementDisposition, ...] = ()
    contract: str = STRUCTURE_REPLACEMENT_PLAN_CONTRACT

    def __post_init__(self) -> None:
        if self.contract != STRUCTURE_REPLACEMENT_PLAN_CONTRACT:
            raise ValueError("P2P_STRUCTURE_REPLACEMENT_PLAN_UNSUPPORTED: unsupported plan contract")
        object.__setattr__(
            self,
            "target_coordinate",
            normalize_structure_text(
                self.target_coordinate,
                field_name="replacement.plan.target.coordinate",
                maximum_bytes=256,
            ),
        )
        checksum = str(self.target_semantic_checksum or "").removeprefix("sha256:")
        if len(checksum) != 64 or any(char not in "0123456789abcdef" for char in checksum):
            raise ValueError("P2P_STRUCTURE_REPLACEMENT_PLAN_INVALID: target semantic checksum must be SHA-256")
        object.__setattr__(self, "target_semantic_checksum", checksum)
        ids = [item.disposition_id for item in self.dispositions]
        if len(ids) != len(set(ids)):
            raise ValueError("P2P_STRUCTURE_REPLACEMENT_DISPOSITION_INVALID: duplicate disposition id")

    @property
    def by_id(self) -> dict[str, StructureRetirementDisposition]:
        return {item.disposition_id: item for item in self.dispositions}

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": self.contract,
            "target": {
                "coordinate": self.target_coordinate,
                "semantic_checksum": self.target_semantic_checksum,
            },
            "dispositions": [item.to_dict() for item in self.dispositions],
        }


@dataclass(frozen=True)
class ProjectStructureReplacementInspection:
    target: StructureReplacementRelease
    candidate: ProjectStructure | None
    active_counts: Mapping[str, int]
    blockers: tuple[str, ...] = ()
    contract: str = STRUCTURE_REPLACEMENT_IMPACT_CONTRACT

    @property
    def valid(self) -> bool:
        return not self.blockers

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": self.contract,
            "target": self.target.to_dict(),
            "valid": self.valid,
            "active_counts": dict(self.active_counts),
            "candidate": (
                _structure_summary(self.candidate)
                if self.candidate is not None
                else None
            ),
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class ProjectStructureReplacementPreview:
    target: StructureReplacementRelease
    current: ProjectStructure
    previous_memory_revision: str
    candidate: ProjectStructure | None
    candidate_memory_revision: str | None
    elements: tuple[StructureReplacementElement, ...]
    impacts: tuple[StructureRetirementImpact, ...]
    required_dispositions: tuple[StructureRetirementImpact, ...]
    applied_dispositions: tuple[StructureRetirementDisposition, ...]
    preview: MutationPreview
    plan_complete: bool
    classification_projection: Mapping[str, object] = field(default_factory=dict)
    readiness_projection: Mapping[str, object] = field(default_factory=dict)
    blockers: tuple[str, ...] = ()
    message: str = ""
    contract: str = STRUCTURE_REPLACEMENT_IMPACT_CONTRACT

    @property
    def apply_token(self) -> str | None:
        if not self.plan_complete or self.blockers or not self.preview.apply_allowed:
            return None
        return self.preview.preview_token or None

    def to_dict(self) -> dict[str, object]:
        preview = self.preview.to_dict()
        if self.apply_token is None:
            preview["preview_token"] = None
            preview["apply_allowed"] = False
        return {
            "contract": self.contract,
            "target": self.target.to_dict(),
            "current": _structure_summary(self.current),
            "previous_memory_revision": self.previous_memory_revision,
            "candidate": (
                _structure_summary(self.candidate)
                if self.candidate is not None
                else None
            ),
            "candidate_memory_revision": self.candidate_memory_revision,
            "elements": [item.to_dict() for item in self.elements],
            "impacts": [item.to_dict() for item in self.impacts],
            "required_dispositions": [
                item.to_dict() for item in self.required_dispositions
            ],
            "applied_dispositions": [
                item.to_dict() for item in self.applied_dispositions
            ],
            "plan_complete": self.plan_complete,
            "classification_projection": dict(self.classification_projection),
            "readiness_projection": dict(self.readiness_projection),
            "blockers": list(self.blockers),
            "preview": preview,
            "apply_token": self.apply_token,
            "message": self.message,
        }


@dataclass(frozen=True)
class ProjectStructureReplacementResult:
    status: str
    previous: ProjectStructure
    current: ProjectStructure
    target: StructureReplacementRelease
    previous_memory_revision: str
    current_memory_revision: str
    event: ProjectStructureEvent
    actor: str
    dispositions: tuple[StructureRetirementDisposition, ...]
    readiness_identity: Mapping[str, object]
    classification_identity: Mapping[str, object]
    changed_paths: tuple[str, ...] = ()
    message: str = ""
    contract: str = STRUCTURE_REPLACEMENT_RESULT_CONTRACT

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": self.contract,
            "status": self.status,
            "operation": PROJECT_STRUCTURE_REPLACEMENT_OPERATION,
            "operation_id": PROJECT_STRUCTURE_REPLACEMENT_OPERATION_ID,
            "target": self.target.to_dict(),
            "previous_revision": self.previous.revision,
            "previous_checksum": self.previous.checksum,
            "current": self.current.to_dict(),
            "previous_memory_revision": self.previous_memory_revision,
            "current_memory_revision": self.current_memory_revision,
            "event": self.event.to_dict(),
            "actor": self.actor,
            "dispositions": [item.to_dict() for item in self.dispositions],
            "readiness_identity": dict(self.readiness_identity),
            "classification_identity": dict(self.classification_identity),
            "detached_copy": True,
            "active_release_subscription": False,
            "remote_publication": False,
            "publisher_ownership_granted": False,
            "moderation_rights_granted": False,
            "changed_paths": list(self.changed_paths),
            "message": self.message,
        }


def structure_replacement_plan_from_mapping(value: object | None) -> StructureReplacementPlan | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError("P2P_STRUCTURE_REPLACEMENT_PLAN_INVALID: plan must be a mapping")
    raw: Mapping[str, object]
    if set(value) == {"project_structure_replacement_plan"}:
        nested = value.get("project_structure_replacement_plan")
        if not isinstance(nested, Mapping):
            raise ValueError("P2P_STRUCTURE_REPLACEMENT_PLAN_INVALID: root must contain a mapping")
        raw = nested
    else:
        raw = value
    unknown = sorted(set(raw) - {"contract", "target", "dispositions"})
    if unknown:
        raise ValueError(
            "P2P_STRUCTURE_REPLACEMENT_PLAN_INVALID: unsupported fields: "
            + ", ".join(str(item) for item in unknown)
        )
    if raw.get("contract") != STRUCTURE_REPLACEMENT_PLAN_CONTRACT:
        raise ValueError("P2P_STRUCTURE_REPLACEMENT_PLAN_UNSUPPORTED: unsupported plan contract")
    target = raw.get("target")
    if not isinstance(target, Mapping):
        raise ValueError("P2P_STRUCTURE_REPLACEMENT_PLAN_INVALID: target must be a mapping")
    target_unknown = sorted(set(target) - {"coordinate", "semantic_checksum"})
    if target_unknown:
        raise ValueError(
            "P2P_STRUCTURE_REPLACEMENT_PLAN_INVALID: unsupported target fields: "
            + ", ".join(str(item) for item in target_unknown)
        )
    dispositions = raw.get("dispositions")
    if dispositions is None:
        dispositions = ()
    if isinstance(dispositions, (str, bytes)) or not isinstance(dispositions, Sequence):
        raise ValueError("P2P_STRUCTURE_REPLACEMENT_PLAN_INVALID: dispositions must be a list")
    return StructureReplacementPlan(
        target_coordinate=str(target.get("coordinate") or ""),
        target_semantic_checksum=str(target.get("semantic_checksum") or ""),
        dispositions=tuple(
            structure_retirement_disposition_from_mapping(item)
            for item in dispositions
        ),
    )


def structure_replacement_empty_plan(
    *,
    target_coordinate: str,
    target_semantic_checksum: str,
) -> StructureReplacementPlan:
    return StructureReplacementPlan(
        target_coordinate=target_coordinate,
        target_semantic_checksum=target_semantic_checksum,
    )


def _structure_summary(structure: ProjectStructure) -> dict[str, object]:
    return {
        "contract": structure.contract,
        "structure_id": structure.structure_id,
        "revision": structure.revision,
        "checksum": structure.checksum,
        "origin": structure.origin.to_dict(),
    }
