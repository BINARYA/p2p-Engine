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


STRUCTURE_RETIREMENT_IMPACT_CONTRACT = "p2p-structure-retirement-impact/v1"
STRUCTURE_RETIREMENT_PLAN_CONTRACT = "p2p-structure-retirement-plan/v1"
STRUCTURE_RETIREMENT_RESULT_CONTRACT = "p2p-structure-retirement-result/v1"
STRUCTURE_RETIREMENT_ACTIONS = frozenset(
    {
        "reassign_sections",
        "project_global",
        "unassigned",
        "retire",
        "remove_sections",
    }
)


@dataclass(frozen=True)
class StructureRetirementTarget:
    kind: str
    element_id: str
    section_id: str | None = None

    def __post_init__(self) -> None:
        kind = str(self.kind).strip().lower()
        if kind not in PROJECT_STRUCTURE_ELEMENT_KINDS:
            raise ValueError("P2P_STRUCTURE_RETIREMENT_TARGET_INVALID: unsupported target kind")
        element_id = normalize_structure_id(self.element_id, field_name="target.id")
        section_id = (
            normalize_structure_id(self.section_id, field_name="target.section_id")
            if self.section_id is not None
            else None
        )
        if section_id is not None and kind != "field":
            raise ValueError("P2P_STRUCTURE_RETIREMENT_TARGET_INVALID: section_id only disambiguates fields")
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "element_id", element_id)
        object.__setattr__(self, "section_id", section_id)

    @property
    def identity(self) -> str:
        if self.section_id is None:
            return f"{self.kind}:{self.element_id}"
        return f"{self.kind}:{self.section_id}/{self.element_id}"

    def to_dict(self) -> dict[str, object]:
        payload = {"kind": self.kind, "id": self.element_id}
        if self.section_id is not None:
            payload["section_id"] = self.section_id
        return payload


@dataclass(frozen=True)
class StructureRetirementDisposition:
    disposition_id: str
    action: str
    section_ids: tuple[str, ...] = ()
    reason: str = ""

    def __post_init__(self) -> None:
        disposition_id = normalize_structure_text(
            self.disposition_id,
            field_name="disposition.id",
            maximum_bytes=256,
        )
        action = str(self.action).strip().lower()
        if action not in STRUCTURE_RETIREMENT_ACTIONS:
            raise ValueError("P2P_STRUCTURE_RETIREMENT_DISPOSITION_INVALID: unsupported action")
        section_ids = tuple(
            normalize_structure_id(item, field_name="disposition.section_id")
            for item in self.section_ids
        )
        if len(section_ids) != len(set(section_ids)):
            raise ValueError("P2P_STRUCTURE_RETIREMENT_DISPOSITION_INVALID: section IDs must be unique")
        if action == "reassign_sections" and not section_ids:
            raise ValueError("P2P_STRUCTURE_RETIREMENT_DISPOSITION_INVALID: reassign_sections requires section_ids")
        if action != "reassign_sections" and section_ids:
            raise ValueError("P2P_STRUCTURE_RETIREMENT_DISPOSITION_INVALID: only reassign_sections accepts section_ids")
        object.__setattr__(self, "disposition_id", disposition_id)
        object.__setattr__(self, "action", action)
        object.__setattr__(self, "section_ids", section_ids)
        object.__setattr__(
            self,
            "reason",
            normalize_structure_text(
                self.reason,
                field_name="disposition.reason",
                maximum_bytes=1000,
                required=False,
            ),
        )

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "id": self.disposition_id,
            "action": self.action,
            "reason": self.reason,
        }
        if self.section_ids:
            payload["section_ids"] = list(self.section_ids)
        return payload


@dataclass(frozen=True)
class StructureRetirementImpact:
    impact_id: str
    object_type: str
    object_id: str
    path: str
    lifecycle: str
    state: str
    active: bool
    section_ids: tuple[str, ...] = ()
    retiring_section_ids: tuple[str, ...] = ()
    required_disposition: bool = False
    allowed_actions: tuple[str, ...] = ()
    default_action: str | None = None
    message: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "impact_id",
            normalize_structure_text(
                self.impact_id,
                field_name="impact.id",
                maximum_bytes=256,
            ),
        )
        object.__setattr__(
            self,
            "object_type",
            normalize_structure_text(
                self.object_type,
                field_name="impact.object_type",
                maximum_bytes=64,
            ),
        )
        object.__setattr__(
            self,
            "object_id",
            normalize_structure_text(
                self.object_id,
                field_name="impact.object_id",
                maximum_bytes=128,
            ),
        )
        object.__setattr__(
            self,
            "path",
            normalize_structure_text(
                self.path,
                field_name="impact.path",
                maximum_bytes=512,
                required=False,
            ),
        )
        object.__setattr__(
            self,
            "section_ids",
            tuple(normalize_structure_id(item, field_name="impact.section_id") for item in self.section_ids),
        )
        object.__setattr__(
            self,
            "retiring_section_ids",
            tuple(
                normalize_structure_id(item, field_name="impact.retiring_section_id")
                for item in self.retiring_section_ids
            ),
        )
        actions = tuple(str(item).strip().lower() for item in self.allowed_actions)
        if any(action not in STRUCTURE_RETIREMENT_ACTIONS for action in actions):
            raise ValueError("P2P_STRUCTURE_RETIREMENT_IMPACT_INVALID: unsupported allowed action")
        if self.default_action is not None and self.default_action not in actions:
            raise ValueError("P2P_STRUCTURE_RETIREMENT_IMPACT_INVALID: default action must be allowed")
        object.__setattr__(self, "allowed_actions", actions)
        object.__setattr__(
            self,
            "message",
            normalize_structure_text(
                self.message,
                field_name="impact.message",
                maximum_bytes=1000,
                required=False,
            ),
        )

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "id": self.impact_id,
            "object_type": self.object_type,
            "object_id": self.object_id,
            "path": self.path,
            "lifecycle": self.lifecycle,
            "state": self.state,
            "active": self.active,
            "section_ids": list(self.section_ids),
            "retiring_section_ids": list(self.retiring_section_ids),
            "required_disposition": self.required_disposition,
            "allowed_actions": list(self.allowed_actions),
            "message": self.message,
        }
        if self.default_action is not None:
            payload["default_action"] = self.default_action
        return payload


@dataclass(frozen=True)
class StructureRetirementPlan:
    dispositions: tuple[StructureRetirementDisposition, ...] = ()
    contract: str = STRUCTURE_RETIREMENT_PLAN_CONTRACT

    def __post_init__(self) -> None:
        if self.contract != STRUCTURE_RETIREMENT_PLAN_CONTRACT:
            raise ValueError("P2P_STRUCTURE_RETIREMENT_PLAN_UNSUPPORTED: unsupported plan contract")
        ids = [item.disposition_id for item in self.dispositions]
        if len(ids) != len(set(ids)):
            raise ValueError("P2P_STRUCTURE_RETIREMENT_DISPOSITION_INVALID: duplicate disposition id")

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": self.contract,
            "dispositions": [item.to_dict() for item in self.dispositions],
        }

    @property
    def by_id(self) -> dict[str, StructureRetirementDisposition]:
        return {item.disposition_id: item for item in self.dispositions}


@dataclass(frozen=True)
class ProjectStructureRetirementPreview:
    targets: tuple[StructureRetirementTarget, ...]
    current: ProjectStructure
    previous_memory_revision: str
    candidate: ProjectStructure | None
    candidate_memory_revision: str | None
    impacts: tuple[StructureRetirementImpact, ...]
    required_dispositions: tuple[StructureRetirementImpact, ...]
    applied_dispositions: tuple[StructureRetirementDisposition, ...]
    preview: MutationPreview
    classification_projection: Mapping[str, object] = field(default_factory=dict)
    readiness_projection: Mapping[str, object] = field(default_factory=dict)
    message: str = ""
    contract: str = STRUCTURE_RETIREMENT_IMPACT_CONTRACT

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": self.contract,
            "targets": [item.to_dict() for item in self.targets],
            "current": _structure_summary(self.current),
            "previous_memory_revision": self.previous_memory_revision,
            "candidate": (
                _structure_summary(self.candidate)
                if self.candidate is not None
                else None
            ),
            "candidate_memory_revision": self.candidate_memory_revision,
            "impacts": [item.to_dict() for item in self.impacts],
            "required_dispositions": [
                item.to_dict() for item in self.required_dispositions
            ],
            "applied_dispositions": [
                item.to_dict() for item in self.applied_dispositions
            ],
            "classification_projection": dict(self.classification_projection),
            "readiness_projection": dict(self.readiness_projection),
            "preview": self.preview.to_dict(),
            "message": self.message,
        }


@dataclass(frozen=True)
class ProjectStructureRetirementResult:
    status: str
    previous: ProjectStructure
    current: ProjectStructure
    previous_memory_revision: str
    current_memory_revision: str
    event: ProjectStructureEvent
    actor: str
    targets: tuple[StructureRetirementTarget, ...]
    dispositions: tuple[StructureRetirementDisposition, ...]
    changed_paths: tuple[str, ...] = ()
    message: str = ""
    contract: str = STRUCTURE_RETIREMENT_RESULT_CONTRACT

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": self.contract,
            "status": self.status,
            "previous_revision": self.previous.revision,
            "previous_checksum": self.previous.checksum,
            "current": self.current.to_dict(),
            "previous_memory_revision": self.previous_memory_revision,
            "current_memory_revision": self.current_memory_revision,
            "event": self.event.to_dict(),
            "actor": self.actor,
            "targets": [item.to_dict() for item in self.targets],
            "dispositions": [item.to_dict() for item in self.dispositions],
            "changed_paths": list(self.changed_paths),
            "message": self.message,
        }


def structure_retirement_plan_from_mapping(value: object | None) -> StructureRetirementPlan:
    if value is None:
        return StructureRetirementPlan()
    if not isinstance(value, Mapping):
        raise ValueError("P2P_STRUCTURE_RETIREMENT_PLAN_INVALID: plan must be a mapping")
    raw: Mapping[str, object]
    if set(value) == {"project_structure_retirement_plan"}:
        nested = value.get("project_structure_retirement_plan")
        if not isinstance(nested, Mapping):
            raise ValueError("P2P_STRUCTURE_RETIREMENT_PLAN_INVALID: root must contain a mapping")
        raw = nested
    else:
        raw = value
    unknown = sorted(set(raw) - {"contract", "dispositions"})
    if unknown:
        raise ValueError(
            "P2P_STRUCTURE_RETIREMENT_PLAN_INVALID: unsupported fields: "
            + ", ".join(str(item) for item in unknown)
        )
    if raw.get("contract") != STRUCTURE_RETIREMENT_PLAN_CONTRACT:
        raise ValueError("P2P_STRUCTURE_RETIREMENT_PLAN_UNSUPPORTED: unsupported plan contract")
    return StructureRetirementPlan(
        dispositions=tuple(
            structure_retirement_disposition_from_mapping(item)
            for item in _sequence(raw.get("dispositions"), "dispositions")
        )
    )


def structure_retirement_disposition_from_mapping(
    value: object,
) -> StructureRetirementDisposition:
    if not isinstance(value, Mapping):
        raise ValueError("P2P_STRUCTURE_RETIREMENT_DISPOSITION_INVALID: disposition must be a mapping")
    unknown = sorted(set(value) - {"id", "action", "section_ids", "reason"})
    if unknown:
        raise ValueError(
            "P2P_STRUCTURE_RETIREMENT_DISPOSITION_INVALID: unsupported fields: "
            + ", ".join(str(item) for item in unknown)
        )
    return StructureRetirementDisposition(
        disposition_id=value.get("id"),  # type: ignore[arg-type]
        action=str(value.get("action") or ""),
        section_ids=tuple(
            str(item)
            for item in _sequence(value.get("section_ids"), "disposition.section_ids")
        ),
        reason=str(value.get("reason") or ""),
    )


def structure_retirement_target_from_mapping(value: object) -> StructureRetirementTarget:
    if not isinstance(value, Mapping):
        raise ValueError("P2P_STRUCTURE_RETIREMENT_TARGET_INVALID: target must be a mapping")
    unknown = sorted(set(value) - {"kind", "id", "section_id"})
    if unknown:
        raise ValueError(
            "P2P_STRUCTURE_RETIREMENT_TARGET_INVALID: unsupported fields: "
            + ", ".join(str(item) for item in unknown)
        )
    return StructureRetirementTarget(
        kind=str(value.get("kind") or ""),
        element_id=value.get("id"),  # type: ignore[arg-type]
        section_id=(
            str(value.get("section_id"))
            if value.get("section_id") is not None
            else None
        ),
    )


def structure_retirement_target_from_text(value: str) -> StructureRetirementTarget:
    raw = normalize_structure_text(
        value,
        field_name="target",
        maximum_bytes=160,
    )
    if ":" not in raw:
        raise ValueError("P2P_STRUCTURE_RETIREMENT_TARGET_INVALID: target must use kind:id")
    kind, identity = raw.split(":", 1)
    section_id: str | None = None
    element_id = identity
    if kind.strip().lower() == "field" and "/" in identity:
        section_id, element_id = identity.split("/", 1)
    return StructureRetirementTarget(
        kind=kind,
        element_id=element_id,
        section_id=section_id,
    )


def _sequence(value: object, name: str) -> Sequence[object]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError(f"P2P_STRUCTURE_RETIREMENT_PLAN_INVALID: {name} must be a list")
    return value


def _structure_summary(structure: ProjectStructure) -> dict[str, object]:
    return {
        "contract": structure.contract,
        "structure_id": structure.structure_id,
        "revision": structure.revision,
        "checksum": structure.checksum,
    }
