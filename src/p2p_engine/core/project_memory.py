from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import re
from collections.abc import Mapping, Sequence

from p2p_engine.core.mutation_preview import semantic_sha256
from p2p_engine.core.project_structure import normalize_structure_id


PROJECT_MEMORY_SCOPE_CONTRACT = "p2p-project-memory-scope/v1"
PROJECT_MEMORY_SCOPE_EVENTS_CONTRACT = "p2p-project-memory-scope-events/v1"
MEMORY_CLASSIFICATION_CONTRACT = "p2p-memory-classification/v1"
PROJECT_MEMORY_SCOPE_MUTATION_CONTRACT = "p2p-project-memory-scope-mutation/v1"
PROJECT_MEMORY_SCOPE_KINDS = frozenset({"sections", "project_global", "unassigned"})
MEMORY_CLASSIFICATION_STATUSES = frozenset(
    {"complete", "incomplete", "not_applicable", "unknown", "stale"}
)
MEMORY_CLASSIFICATION_ITEM_STATES = frozenset(
    {
        "section_classified",
        "project_global",
        "unassigned",
        "requires_reassignment",
        "historical",
        "unknown",
    }
)
PROJECT_MEMORY_OBJECT_LIMIT = 4096
PROJECT_MEMORY_PUBLIC_ITEM_LIMIT = 100
PROJECT_MEMORY_SCOPE_EVENT_LIMIT = 1024

_PROPOSAL_ID = re.compile(r"^PROP-\d{3,}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ProjectMemoryScopeKind(StrEnum):
    sections = "sections"
    project_global = "project_global"
    unassigned = "unassigned"


@dataclass(frozen=True)
class ProjectMemoryScope:
    object_type: str
    object_id: str
    revision: int
    kind: ProjectMemoryScopeKind
    section_ids: tuple[str, ...] = ()
    structure_id: str = ""
    structure_revision: int = 0
    structure_checksum: str = ""
    updated_at: str = ""
    updated_by: str = ""
    authority: Mapping[str, object] = field(default_factory=dict)
    contract: str = PROJECT_MEMORY_SCOPE_CONTRACT

    def __post_init__(self) -> None:
        if self.contract != PROJECT_MEMORY_SCOPE_CONTRACT:
            raise ValueError("P2P_PROJECT_MEMORY_SCOPE_UNSUPPORTED: scope contract is unsupported")
        if self.object_type != "proposal" or not _PROPOSAL_ID.fullmatch(self.object_id):
            raise ValueError("P2P_PROJECT_MEMORY_SCOPE_INVALID: only canonical proposal IDs are supported")
        if isinstance(self.revision, bool) or not isinstance(self.revision, int) or self.revision < 1:
            raise ValueError("P2P_PROJECT_MEMORY_SCOPE_INVALID: revision must be positive")
        try:
            normalized_kind = ProjectMemoryScopeKind(str(self.kind))
        except ValueError as exc:
            raise ValueError("P2P_PROJECT_MEMORY_SCOPE_INVALID: unsupported scope kind") from exc
        normalized_sections = tuple(
            normalize_structure_id(item, field_name="scope.section_id")
            for item in self.section_ids
        )
        if len(normalized_sections) != len(set(normalized_sections)):
            raise ValueError("P2P_PROJECT_MEMORY_SCOPE_INVALID: section IDs must be unique")
        if normalized_kind == ProjectMemoryScopeKind.sections and not normalized_sections:
            raise ValueError("P2P_PROJECT_MEMORY_SCOPE_INVALID: sections scope requires targets")
        if normalized_kind != ProjectMemoryScopeKind.sections and normalized_sections:
            raise ValueError("P2P_PROJECT_MEMORY_SCOPE_INVALID: non-section scope forbids section IDs")
        has_binding = bool(self.structure_id or self.structure_revision or self.structure_checksum)
        if has_binding:
            normalize_structure_id(self.structure_id, field_name="scope.structure_id")
            if (
                isinstance(self.structure_revision, bool)
                or not isinstance(self.structure_revision, int)
                or self.structure_revision < 1
                or not _SHA256.fullmatch(self.structure_checksum)
            ):
                raise ValueError("P2P_PROJECT_MEMORY_SCOPE_INVALID: structure binding is incomplete")
        if not has_binding:
            raise ValueError(
                "P2P_PROJECT_MEMORY_SCOPE_INVALID: scope requires structure binding"
            )
        if not isinstance(self.authority, Mapping):
            raise ValueError("P2P_PROJECT_MEMORY_SCOPE_INVALID: authority must be a mapping")
        object.__setattr__(self, "kind", normalized_kind)
        object.__setattr__(self, "section_ids", normalized_sections)

    def semantic_payload(self) -> dict[str, object]:
        return {
            "object_type": self.object_type,
            "object_id": self.object_id,
            "revision": self.revision,
            "kind": self.kind.value,
            "section_ids": list(self.section_ids),
            "structure": {
                "id": self.structure_id or None,
                "revision": self.structure_revision or None,
                "checksum": self.structure_checksum or None,
            },
        }

    @property
    def semantic_sha256(self) -> str:
        return semantic_sha256(self.semantic_payload())

    def to_dict(self, *, include_authority: bool = True) -> dict[str, object]:
        result = {
            "contract": self.contract,
            **self.semantic_payload(),
            "semantic_sha256": self.semantic_sha256,
            "updated_at": self.updated_at,
            "updated_by": self.updated_by,
        }
        if include_authority:
            result["authority"] = dict(self.authority)
        return result


@dataclass(frozen=True)
class ProjectMemoryScopeEvent:
    event_id: str
    scope_revision: int
    scope_sha256: str
    occurred_at: str
    subject_id: str
    executor_id: str
    authority: Mapping[str, object]
    previous_kind: str | None
    current_kind: str
    section_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if (
            not self.event_id
            or isinstance(self.scope_revision, bool)
            or not isinstance(self.scope_revision, int)
            or self.scope_revision < 1
            or not _SHA256.fullmatch(self.scope_sha256)
        ):
            raise ValueError("P2P_PROJECT_MEMORY_SCOPE_INVALID: scope event identity is invalid")
        if self.current_kind not in PROJECT_MEMORY_SCOPE_KINDS:
            raise ValueError("P2P_PROJECT_MEMORY_SCOPE_INVALID: scope event kind is invalid")
        if self.previous_kind is not None and self.previous_kind not in PROJECT_MEMORY_SCOPE_KINDS:
            raise ValueError("P2P_PROJECT_MEMORY_SCOPE_INVALID: previous scope event kind is invalid")
        if not isinstance(self.authority, Mapping):
            raise ValueError("P2P_PROJECT_MEMORY_SCOPE_INVALID: event authority must be a mapping")
        normalized_sections = tuple(
            normalize_structure_id(item, field_name="scope_event.section_id")
            for item in self.section_ids
        )
        if len(normalized_sections) != len(set(normalized_sections)):
            raise ValueError(
                "P2P_PROJECT_MEMORY_SCOPE_INVALID: event section IDs must be unique"
            )
        if self.current_kind == ProjectMemoryScopeKind.sections.value:
            if not normalized_sections:
                raise ValueError(
                    "P2P_PROJECT_MEMORY_SCOPE_INVALID: sections event requires targets"
                )
        elif normalized_sections:
            raise ValueError(
                "P2P_PROJECT_MEMORY_SCOPE_INVALID: non-section event forbids targets"
            )
        object.__setattr__(self, "section_ids", normalized_sections)

    def to_dict(self) -> dict[str, object]:
        return {
            "event_id": self.event_id,
            "scope_revision": self.scope_revision,
            "scope_sha256": self.scope_sha256,
            "occurred_at": self.occurred_at,
            "subject_id": self.subject_id,
            "executor_id": self.executor_id,
            "authority": dict(self.authority),
            "previous_kind": self.previous_kind,
            "current_kind": self.current_kind,
            "section_ids": list(self.section_ids),
        }


@dataclass(frozen=True)
class MemoryClassificationItem:
    object_type: str
    object_id: str
    lifecycle: str
    state: str
    scope_kind: str
    section_ids: tuple[str, ...] = ()
    active_section_ids: tuple[str, ...] = ()
    retired_section_ids: tuple[str, ...] = ()
    unknown_section_ids: tuple[str, ...] = ()
    decision_blocking: bool = False
    message: str = ""

    def __post_init__(self) -> None:
        if self.state not in MEMORY_CLASSIFICATION_ITEM_STATES:
            raise ValueError("P2P_MEMORY_CLASSIFICATION_INVALID: item state is invalid")

    def to_dict(self) -> dict[str, object]:
        return {
            "object_type": self.object_type,
            "object_id": self.object_id,
            "lifecycle": self.lifecycle,
            "state": self.state,
            "scope_kind": self.scope_kind,
            "section_ids": list(self.section_ids),
            "active_section_ids": list(self.active_section_ids),
            "retired_section_ids": list(self.retired_section_ids),
            "unknown_section_ids": list(self.unknown_section_ids),
            "decision_blocking": self.decision_blocking,
            "message": self.message,
        }


@dataclass(frozen=True)
class MemoryClassificationSnapshot:
    status: str
    structure_id: str
    structure_revision: int
    structure_checksum: str
    memory_revision: str
    counts: Mapping[str, int]
    per_type: Mapping[str, Mapping[str, int]]
    items: tuple[MemoryClassificationItem, ...]
    truncated: bool = False
    diagnostics: tuple[Mapping[str, object], ...] = ()
    contract: str = MEMORY_CLASSIFICATION_CONTRACT

    def __post_init__(self) -> None:
        if self.contract != MEMORY_CLASSIFICATION_CONTRACT or self.status not in MEMORY_CLASSIFICATION_STATUSES:
            raise ValueError("P2P_MEMORY_CLASSIFICATION_INVALID: snapshot contract or status is invalid")
        if not _SHA256.fullmatch(self.structure_checksum) or not _SHA256.fullmatch(self.memory_revision):
            raise ValueError("P2P_MEMORY_CLASSIFICATION_INVALID: snapshot identity is invalid")

    def to_dict(self, *, limit: int = PROJECT_MEMORY_PUBLIC_ITEM_LIMIT) -> dict[str, object]:
        if isinstance(limit, bool) or limit < 1 or limit > PROJECT_MEMORY_OBJECT_LIMIT:
            raise ValueError("P2P_MEMORY_CLASSIFICATION_INVALID: item limit is out of bounds")
        collections: dict[str, list[dict[str, object]]] = {
            state: [] for state in MEMORY_CLASSIFICATION_ITEM_STATES
        }
        for item in self.items:
            collections[item.state].append(item.to_dict())
        public_collections: dict[str, object] = {}
        for state in sorted(collections):
            values = sorted(
                collections[state],
                key=lambda item: (str(item["object_type"]), str(item["object_id"])),
            )
            public_collections[state] = {
                "items": values[:limit],
                "total": len(values),
                "returned": min(len(values), limit),
                "truncated": len(values) > limit,
            }
        return {
            "contract": self.contract,
            "status": self.status,
            "structure": {
                "id": self.structure_id,
                "revision": self.structure_revision,
                "checksum": self.structure_checksum,
            },
            "memory_revision": self.memory_revision,
            "counts": dict(self.counts),
            "per_type": {key: dict(value) for key, value in sorted(self.per_type.items())},
            "collections": public_collections,
            "truncated": self.truncated or any(
                bool(value["truncated"]) for value in public_collections.values()  # type: ignore[index]
            ),
            "diagnostics": [dict(item) for item in self.diagnostics],
            "readiness_effect": "none",
        }


@dataclass(frozen=True)
class ProjectMemoryScopeMutationResult:
    status: str
    previous: ProjectMemoryScope
    current: ProjectMemoryScope
    previous_memory_revision: str
    current_memory_revision: str
    event: ProjectMemoryScopeEvent
    actor: str
    message: str
    contract: str = PROJECT_MEMORY_SCOPE_MUTATION_CONTRACT

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": self.contract,
            "status": self.status,
            "object_type": self.current.object_type,
            "object_id": self.current.object_id,
            "previous_scope": self.previous.to_dict(include_authority=False),
            "current_scope": self.current.to_dict(),
            "previous_memory_revision": self.previous_memory_revision,
            "current_memory_revision": self.current_memory_revision,
            "structure_revision": self.current.structure_revision,
            "structure_checksum": self.current.structure_checksum,
            "event": self.event.to_dict(),
            "actor": self.actor,
            "message": self.message,
        }


def project_memory_scope_from_mapping(value: object) -> ProjectMemoryScope:
    if not isinstance(value, Mapping):
        raise ValueError("P2P_PROJECT_MEMORY_SCOPE_INVALID: scope must be a mapping")
    allowed = {
        "contract", "object_type", "object_id", "revision", "kind", "section_ids",
        "structure", "updated_at", "updated_by", "authority", "semantic_sha256",
    }
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ValueError(
            "P2P_PROJECT_MEMORY_SCOPE_INVALID: unsupported fields: "
            + ", ".join(str(item) for item in unknown)
        )
    structure = value.get("structure") or {}
    if not isinstance(structure, Mapping):
        raise ValueError("P2P_PROJECT_MEMORY_SCOPE_INVALID: structure must be a mapping")
    section_ids = value.get("section_ids") or ()
    if isinstance(section_ids, (str, bytes)) or not isinstance(section_ids, Sequence):
        raise ValueError("P2P_PROJECT_MEMORY_SCOPE_INVALID: section_ids must be a list")
    authority = value.get("authority") or {}
    if not isinstance(authority, Mapping):
        raise ValueError("P2P_PROJECT_MEMORY_SCOPE_INVALID: authority must be a mapping")
    scope = ProjectMemoryScope(
        contract=str(value.get("contract") or ""),
        object_type=str(value.get("object_type") or ""),
        object_id=str(value.get("object_id") or ""),
        revision=value.get("revision"),  # type: ignore[arg-type]
        kind=ProjectMemoryScopeKind(str(value.get("kind") or "")),
        section_ids=tuple(str(item) for item in section_ids),
        structure_id=str(structure.get("id") or ""),
        structure_revision=int(structure.get("revision") or 0),
        structure_checksum=str(structure.get("checksum") or ""),
        updated_at=str(value.get("updated_at") or ""),
        updated_by=str(value.get("updated_by") or ""),
        authority=dict(authority),
    )
    recorded = value.get("semantic_sha256")
    if recorded is not None and str(recorded) != scope.semantic_sha256:
        raise ValueError("P2P_PROJECT_MEMORY_SCOPE_CHECKSUM_MISMATCH: scope semantics drifted")
    return scope
