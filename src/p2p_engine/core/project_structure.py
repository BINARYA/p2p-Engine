from __future__ import annotations

from dataclasses import dataclass, field, replace
import re
from collections.abc import Mapping, Sequence

from p2p_engine.core.mutation_preview import semantic_sha256


PROJECT_STRUCTURE_CONTRACT = "p2p-project-structure/v1"
PROJECT_STRUCTURE_EVENTS_CONTRACT = "p2p-project-structure-events/v1"
PROJECT_STRUCTURE_MUTATION_CONTRACT = "p2p-project-structure-mutation/v1"
PROJECT_STRUCTURE_LIFECYCLES = frozenset({"active", "retired"})
PROJECT_STRUCTURE_ELEMENT_KINDS = frozenset(
    {"section", "field", "question", "criterion", "artifact"}
)
PROJECT_STRUCTURE_SECTION_LIMIT = 256
PROJECT_STRUCTURE_ELEMENT_LIMIT = 2048
PROJECT_STRUCTURE_EVENT_LIMIT = 4096
PROJECT_STRUCTURE_PUBLIC_HISTORY_LIMIT = 100
PROJECT_STRUCTURE_PUBLIC_ELEMENT_LIMIT = 250

_ID = re.compile(r"^[a-z0-9](?:[a-z0-9_-]{0,62}[a-z0-9])?$")
_CHECKSUM = re.compile(r"^[0-9a-f]{64}$")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def normalize_structure_id(value: object, *, field_name: str = "id") -> str:
    if not isinstance(value, str):
        raise ValueError(f"P2P_PROJECT_STRUCTURE_INVALID: {field_name} must be text")
    normalized = value.strip().lower()
    if not normalized or not _ID.fullmatch(normalized) or normalized in {".", ".."}:
        raise ValueError(
            f"P2P_PROJECT_STRUCTURE_INVALID: {field_name} must be a bounded lower-case identifier"
        )
    return normalized


def normalize_structure_text(
    value: object,
    *,
    field_name: str,
    maximum_bytes: int,
    required: bool = True,
) -> str:
    if not isinstance(value, str):
        raise ValueError(f"P2P_PROJECT_STRUCTURE_INVALID: {field_name} must be text")
    normalized = " ".join(value.strip().split())
    if (
        (required and not normalized)
        or len(normalized.encode("utf-8")) > maximum_bytes
        or _CONTROL.search(normalized)
    ):
        raise ValueError(
            f"P2P_PROJECT_STRUCTURE_INVALID: {field_name} is empty, oversized, or unsafe"
        )
    return normalized


def normalize_lifecycle(value: object) -> str:
    lifecycle = str(value or "active").strip().lower()
    if lifecycle not in PROJECT_STRUCTURE_LIFECYCLES:
        raise ValueError(
            "P2P_PROJECT_STRUCTURE_INVALID: lifecycle must be active or retired"
        )
    return lifecycle


@dataclass(frozen=True)
class StructureOrigin:
    kind: str
    identity: str
    checksum: str | None
    applied_at: str
    applied_by: str
    external_ref: str | None = None

    def __post_init__(self) -> None:
        kind = str(self.kind).strip().lower()
        if kind not in {"starter", "vertical_release"}:
            raise ValueError(
                "P2P_PROJECT_STRUCTURE_INVALID: origin kind must be starter or vertical_release"
            )
        identity = normalize_structure_text(
            self.identity,
            field_name="origin.identity",
            maximum_bytes=256,
        )
        checksum = None if self.checksum is None else str(self.checksum).strip().lower()
        if checksum is not None and not _CHECKSUM.fullmatch(checksum.removeprefix("sha256:")):
            raise ValueError(
                "P2P_PROJECT_STRUCTURE_INVALID: origin checksum must be SHA-256 or null"
            )
        if kind == "vertical_release" and checksum is None:
            raise ValueError(
                "P2P_PROJECT_STRUCTURE_INVALID: vertical release origin requires checksum"
            )
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "identity", identity)
        object.__setattr__(self, "checksum", checksum.removeprefix("sha256:") if checksum else None)
        object.__setattr__(
            self,
            "applied_at",
            normalize_structure_text(
                self.applied_at,
                field_name="origin.applied_at",
                maximum_bytes=64,
            ),
        )
        object.__setattr__(
            self,
            "applied_by",
            normalize_structure_text(
                self.applied_by,
                field_name="origin.applied_by",
                maximum_bytes=128,
            ),
        )
        if self.external_ref is not None:
            object.__setattr__(
                self,
                "external_ref",
                normalize_structure_text(
                    self.external_ref,
                    field_name="origin.external_ref",
                    maximum_bytes=512,
                ),
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "identity": self.identity,
            "checksum": self.checksum,
            "external_ref": self.external_ref,
            "applied_at": self.applied_at,
            "applied_by": self.applied_by,
        }

    @classmethod
    def from_mapping(cls, value: object) -> "StructureOrigin":
        raw = _strict_mapping(
            value,
            name="origin",
            allowed={"kind", "identity", "checksum", "external_ref", "applied_at", "applied_by"},
        )
        return cls(
            kind=raw.get("kind"),  # type: ignore[arg-type]
            identity=raw.get("identity"),  # type: ignore[arg-type]
            checksum=raw.get("checksum"),  # type: ignore[arg-type]
            external_ref=raw.get("external_ref"),  # type: ignore[arg-type]
            applied_at=raw.get("applied_at"),  # type: ignore[arg-type]
            applied_by=raw.get("applied_by"),  # type: ignore[arg-type]
        )


@dataclass(frozen=True)
class StructureSection:
    section_id: str
    title: str
    description: str = ""
    required: bool = True
    order: int = 0
    lifecycle: str = "active"

    def __post_init__(self) -> None:
        object.__setattr__(self, "section_id", normalize_structure_id(self.section_id, field_name="section.id"))
        object.__setattr__(self, "title", normalize_structure_text(self.title, field_name="section.title", maximum_bytes=200))
        object.__setattr__(self, "description", normalize_structure_text(self.description, field_name="section.description", maximum_bytes=2000, required=False))
        object.__setattr__(self, "lifecycle", normalize_lifecycle(self.lifecycle))
        _require_bool(self.required, "section.required")
        if isinstance(self.order, bool) or not isinstance(self.order, int) or self.order < 0:
            raise ValueError("P2P_PROJECT_STRUCTURE_INVALID: section order must be non-negative")

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.section_id,
            "title": self.title,
            "description": self.description,
            "required": self.required,
            "order": self.order,
            "lifecycle": self.lifecycle,
        }


@dataclass(frozen=True)
class StructureField:
    field_id: str
    section_id: str
    label: str
    description: str = ""
    required: bool = True
    order: int = 0
    lifecycle: str = "active"

    def __post_init__(self) -> None:
        object.__setattr__(self, "field_id", normalize_structure_id(self.field_id, field_name="field.id"))
        object.__setattr__(self, "section_id", normalize_structure_id(self.section_id, field_name="field.section_id"))
        object.__setattr__(self, "label", normalize_structure_text(self.label, field_name="field.label", maximum_bytes=200))
        object.__setattr__(self, "description", normalize_structure_text(self.description, field_name="field.description", maximum_bytes=2000, required=False))
        object.__setattr__(self, "lifecycle", normalize_lifecycle(self.lifecycle))
        _require_bool(self.required, "field.required")
        if isinstance(self.order, bool) or not isinstance(self.order, int) or self.order < 0:
            raise ValueError("P2P_PROJECT_STRUCTURE_INVALID: field order must be non-negative")

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.field_id,
            "section_id": self.section_id,
            "label": self.label,
            "description": self.description,
            "required": self.required,
            "order": self.order,
            "lifecycle": self.lifecycle,
        }


@dataclass(frozen=True)
class StructureQuestion:
    question_id: str
    section_id: str
    prompt: str
    priority: str = "medium"
    rationale: str = ""
    order: int = 0
    lifecycle: str = "active"

    def __post_init__(self) -> None:
        object.__setattr__(self, "question_id", normalize_structure_id(self.question_id, field_name="question.id"))
        object.__setattr__(self, "section_id", normalize_structure_id(self.section_id, field_name="question.section_id"))
        object.__setattr__(self, "prompt", normalize_structure_text(self.prompt, field_name="question.prompt", maximum_bytes=2000))
        priority = str(self.priority).strip().lower()
        if priority not in {"high", "medium", "low"}:
            raise ValueError("P2P_PROJECT_STRUCTURE_INVALID: question priority is invalid")
        object.__setattr__(self, "priority", priority)
        object.__setattr__(self, "rationale", normalize_structure_text(self.rationale, field_name="question.rationale", maximum_bytes=2000, required=False))
        object.__setattr__(self, "lifecycle", normalize_lifecycle(self.lifecycle))
        if isinstance(self.order, bool) or not isinstance(self.order, int) or self.order < 0:
            raise ValueError("P2P_PROJECT_STRUCTURE_INVALID: question order must be non-negative")

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.question_id,
            "section_id": self.section_id,
            "prompt": self.prompt,
            "priority": self.priority,
            "rationale": self.rationale,
            "order": self.order,
            "lifecycle": self.lifecycle,
        }


@dataclass(frozen=True)
class StructureCriterion:
    criterion_id: str
    section_id: str
    title: str
    required: bool = True
    enabled: bool = True
    keywords: tuple[str, ...] = ()
    order: int = 0
    lifecycle: str = "active"

    def __post_init__(self) -> None:
        object.__setattr__(self, "criterion_id", normalize_structure_id(self.criterion_id, field_name="criterion.id"))
        object.__setattr__(self, "section_id", normalize_structure_id(self.section_id, field_name="criterion.section_id"))
        object.__setattr__(self, "title", normalize_structure_text(self.title, field_name="criterion.title", maximum_bytes=200))
        object.__setattr__(self, "keywords", tuple(normalize_structure_text(item, field_name="criterion.keyword", maximum_bytes=100) for item in self.keywords))
        object.__setattr__(self, "lifecycle", normalize_lifecycle(self.lifecycle))
        _require_bool(self.required, "criterion.required")
        _require_bool(self.enabled, "criterion.enabled")
        if len(set(self.keywords)) != len(self.keywords):
            raise ValueError("P2P_PROJECT_STRUCTURE_INVALID: criterion keywords must be unique")
        if isinstance(self.order, bool) or not isinstance(self.order, int) or self.order < 0:
            raise ValueError("P2P_PROJECT_STRUCTURE_INVALID: criterion order must be non-negative")

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.criterion_id,
            "section_id": self.section_id,
            "title": self.title,
            "required": self.required,
            "enabled": self.enabled,
            "keywords": list(self.keywords),
            "order": self.order,
            "lifecycle": self.lifecycle,
        }


@dataclass(frozen=True)
class StructureArtifact:
    artifact_id: str
    title: str
    section_ids: tuple[str, ...] = ()
    required: bool = False
    order: int = 0
    lifecycle: str = "active"

    def __post_init__(self) -> None:
        object.__setattr__(self, "artifact_id", normalize_structure_id(self.artifact_id, field_name="artifact.id"))
        object.__setattr__(self, "title", normalize_structure_text(self.title, field_name="artifact.title", maximum_bytes=200))
        section_ids = tuple(normalize_structure_id(item, field_name="artifact.section_id") for item in self.section_ids)
        if len(section_ids) != len(set(section_ids)):
            raise ValueError("P2P_PROJECT_STRUCTURE_INVALID: artifact section IDs must be unique")
        object.__setattr__(self, "section_ids", section_ids)
        object.__setattr__(self, "lifecycle", normalize_lifecycle(self.lifecycle))
        _require_bool(self.required, "artifact.required")
        if isinstance(self.order, bool) or not isinstance(self.order, int) or self.order < 0:
            raise ValueError("P2P_PROJECT_STRUCTURE_INVALID: artifact order must be non-negative")

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.artifact_id,
            "title": self.title,
            "section_ids": list(self.section_ids),
            "required": self.required,
            "order": self.order,
            "lifecycle": self.lifecycle,
        }


@dataclass(frozen=True)
class ProjectStructure:
    structure_id: str
    revision: int
    checksum: str
    origin: StructureOrigin
    sections: tuple[StructureSection, ...] = ()
    fields: tuple[StructureField, ...] = ()
    questions: tuple[StructureQuestion, ...] = ()
    criteria: tuple[StructureCriterion, ...] = ()
    artifacts: tuple[StructureArtifact, ...] = ()
    contract: str = PROJECT_STRUCTURE_CONTRACT

    def __post_init__(self) -> None:
        if self.contract != PROJECT_STRUCTURE_CONTRACT:
            raise ValueError("P2P_PROJECT_STRUCTURE_UNSUPPORTED: structure contract is unsupported")
        object.__setattr__(self, "structure_id", normalize_structure_id(self.structure_id, field_name="structure_id"))
        if isinstance(self.revision, bool) or not isinstance(self.revision, int) or self.revision < 1:
            raise ValueError("P2P_PROJECT_STRUCTURE_INVALID: revision must be positive")
        if not _CHECKSUM.fullmatch(str(self.checksum)):
            raise ValueError("P2P_PROJECT_STRUCTURE_INVALID: checksum must be SHA-256")
        validate_project_structure(self, verify_checksum=False)

    def semantic_payload(self) -> dict[str, object]:
        return {
            "structure_id": self.structure_id,
            "sections": [item.to_dict() for item in self.sections],
            "fields": [item.to_dict() for item in self.fields],
            "questions": [item.to_dict() for item in self.questions],
            "criteria": [item.to_dict() for item in self.criteria],
            "artifacts": [item.to_dict() for item in self.artifacts],
        }

    def to_dict(
        self,
        *,
        include_retired: bool = True,
        element_limit: int = PROJECT_STRUCTURE_PUBLIC_ELEMENT_LIMIT,
    ) -> dict[str, object]:
        if isinstance(element_limit, bool) or not 1 <= element_limit <= PROJECT_STRUCTURE_ELEMENT_LIMIT:
            raise ValueError(
                "P2P_PROJECT_STRUCTURE_INVALID: public element limit is out of bounds"
            )

        def visible(items: Sequence[object]) -> tuple[list[dict[str, object]], dict[str, object]]:
            selected = [
                item.to_dict()  # type: ignore[attr-defined]
                for item in items
                if include_retired or getattr(item, "lifecycle", "active") == "active"
            ]
            returned = selected[:element_limit]
            return returned, {
                "total": len(selected),
                "returned": len(returned),
                "truncated": len(returned) < len(selected),
            }

        sections, section_page = visible(self.sections)
        fields, field_page = visible(self.fields)
        questions, question_page = visible(self.questions)
        criteria, criterion_page = visible(self.criteria)
        artifacts, artifact_page = visible(self.artifacts)

        return {
            "contract": self.contract,
            "structure_id": self.structure_id,
            "revision": self.revision,
            "checksum": self.checksum,
            "origin": self.origin.to_dict(),
            "sections": sections,
            "fields": fields,
            "questions": questions,
            "criteria": criteria,
            "artifacts": artifacts,
            "collections": {
                "sections": section_page,
                "fields": field_page,
                "questions": question_page,
                "criteria": criterion_page,
                "artifacts": artifact_page,
            },
        }

    def to_storage_dict(self) -> dict[str, object]:
        return {
            "contract": self.contract,
            "structure_id": self.structure_id,
            "revision": self.revision,
            "checksum": self.checksum,
            "origin": self.origin.to_dict(),
            "sections": [item.to_dict() for item in self.sections],
            "fields": [item.to_dict() for item in self.fields],
            "questions": [item.to_dict() for item in self.questions],
            "criteria": [item.to_dict() for item in self.criteria],
            "artifacts": [item.to_dict() for item in self.artifacts],
        }

    def active_section_ids(self) -> tuple[str, ...]:
        return tuple(item.section_id for item in self.sections if item.lifecycle == "active")


@dataclass(frozen=True)
class ProjectStructureEvent:
    event_id: str
    event_type: str
    revision: int
    checksum: str
    occurred_at: str
    subject_id: str
    executor_id: str
    authority: Mapping[str, object] = field(default_factory=dict)
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_id", normalize_structure_id(self.event_id, field_name="event.id"))
        if self.event_type not in {"initialized", "section_added", "metadata_updated", "sections_reordered"}:
            raise ValueError("P2P_PROJECT_STRUCTURE_INVALID: structure event type is unsupported")
        if isinstance(self.revision, bool) or not isinstance(self.revision, int) or self.revision < 1:
            raise ValueError("P2P_PROJECT_STRUCTURE_INVALID: structure event revision is invalid")
        if not _CHECKSUM.fullmatch(self.checksum):
            raise ValueError("P2P_PROJECT_STRUCTURE_INVALID: structure event revision or checksum is invalid")
        object.__setattr__(
            self,
            "occurred_at",
            normalize_structure_text(
                self.occurred_at,
                field_name="event.occurred_at",
                maximum_bytes=64,
            ),
        )
        object.__setattr__(
            self,
            "subject_id",
            normalize_structure_text(
                self.subject_id,
                field_name="event.subject_id",
                maximum_bytes=128,
            ),
        )
        object.__setattr__(
            self,
            "executor_id",
            normalize_structure_text(
                self.executor_id,
                field_name="event.executor_id",
                maximum_bytes=128,
            ),
        )
        if not isinstance(self.authority, Mapping) or not isinstance(self.details, Mapping):
            raise ValueError(
                "P2P_PROJECT_STRUCTURE_INVALID: event authority and details must be mappings"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "revision": self.revision,
            "checksum": self.checksum,
            "occurred_at": self.occurred_at,
            "subject_id": self.subject_id,
            "executor_id": self.executor_id,
            "authority": dict(self.authority),
            "details": dict(self.details),
        }


@dataclass(frozen=True)
class ProjectStructureHistory:
    structure_id: str
    events: tuple[ProjectStructureEvent, ...]
    total: int
    returned: int
    truncated: bool
    contract: str = PROJECT_STRUCTURE_EVENTS_CONTRACT

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": self.contract,
            "structure_id": self.structure_id,
            "events": [item.to_dict() for item in self.events],
            "total": self.total,
            "returned": self.returned,
            "truncated": self.truncated,
        }


@dataclass(frozen=True)
class ProjectStructureMutationPlan:
    operation: str
    request: Mapping[str, object]
    previous: ProjectStructure
    next: ProjectStructure
    event: ProjectStructureEvent
    operation_key_sha256: str
    request_fingerprint_sha256: str
    preview_token: str
    source_preconditions: tuple[object, ...] = field(repr=False)
    candidate_bytes: Mapping[str, bytes] = field(repr=False)
    authority: object = field(repr=False)


@dataclass(frozen=True)
class ProjectStructureMutationResult:
    status: str
    operation: str
    previous: ProjectStructure
    current: ProjectStructure
    event: ProjectStructureEvent
    actor: str
    changed_paths: tuple[str, ...] = ()
    message: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": PROJECT_STRUCTURE_MUTATION_CONTRACT,
            "operation": self.operation,
            "status": self.status,
            "previous_revision": self.previous.revision,
            "previous_checksum": self.previous.checksum,
            "current": self.current.to_dict(),
            "event": self.event.to_dict(),
            "actor": self.actor,
            "changed_paths": list(self.changed_paths),
            "message": self.message,
        }


def project_structure_checksum(structure: ProjectStructure) -> str:
    return semantic_sha256(structure.semantic_payload())


def with_project_structure_checksum(structure: ProjectStructure) -> ProjectStructure:
    return replace(structure, checksum=project_structure_checksum(structure))


def validate_project_structure(
    structure: ProjectStructure,
    *,
    verify_checksum: bool = True,
) -> None:
    collections = {
        "section": structure.sections,
        "field": structure.fields,
        "question": structure.questions,
        "criterion": structure.criteria,
        "artifact": structure.artifacts,
    }
    if len(structure.sections) > PROJECT_STRUCTURE_SECTION_LIMIT:
        raise ValueError("P2P_PROJECT_STRUCTURE_INVALID: section limit exceeded")
    for kind, items in collections.items():
        if len(items) > PROJECT_STRUCTURE_ELEMENT_LIMIT:
            raise ValueError(f"P2P_PROJECT_STRUCTURE_INVALID: {kind} limit exceeded")
        identifiers = [_element_identity(kind, item) for item in items]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError(f"P2P_PROJECT_STRUCTURE_INVALID: duplicate {kind} IDs")
    section_ids = {item.section_id for item in structure.sections}
    for item in (*structure.fields, *structure.questions, *structure.criteria):
        if item.section_id not in section_ids:
            raise ValueError(
                f"P2P_PROJECT_STRUCTURE_INVALID: broken section reference `{item.section_id}`"
            )
    for item in structure.artifacts:
        unknown = sorted(set(item.section_ids) - section_ids)
        if unknown:
            raise ValueError(
                "P2P_PROJECT_STRUCTURE_INVALID: artifact has broken section references: "
                + ", ".join(unknown)
            )
    active_orders = [item.order for item in structure.sections if item.lifecycle == "active"]
    if active_orders != list(range(len(active_orders))):
        raise ValueError(
            "P2P_PROJECT_STRUCTURE_INVALID: active section order must be contiguous and canonical"
        )
    if verify_checksum and project_structure_checksum(structure) != structure.checksum:
        raise ValueError("P2P_PROJECT_STRUCTURE_CHECKSUM_MISMATCH: semantic checksum drift")


def project_structure_from_mapping(value: object) -> ProjectStructure:
    raw = _strict_mapping(
        value,
        name="project_structure",
        allowed={"contract", "structure_id", "revision", "checksum", "origin", "sections", "fields", "questions", "criteria", "artifacts"},
    )
    structure = ProjectStructure(
        contract=str(raw.get("contract") or ""),
        structure_id=raw.get("structure_id"),  # type: ignore[arg-type]
        revision=raw.get("revision"),  # type: ignore[arg-type]
        checksum=str(raw.get("checksum") or ""),
        origin=StructureOrigin.from_mapping(raw.get("origin")),
        sections=tuple(_section_from_mapping(item) for item in _sequence(raw.get("sections"), "sections")),
        fields=tuple(_field_from_mapping(item) for item in _sequence(raw.get("fields"), "fields")),
        questions=tuple(_question_from_mapping(item) for item in _sequence(raw.get("questions"), "questions")),
        criteria=tuple(_criterion_from_mapping(item) for item in _sequence(raw.get("criteria"), "criteria")),
        artifacts=tuple(_artifact_from_mapping(item) for item in _sequence(raw.get("artifacts"), "artifacts")),
    )
    validate_project_structure(structure)
    return structure


def project_structure_event_from_mapping(value: object) -> ProjectStructureEvent:
    raw = _strict_mapping(
        value,
        name="event",
        allowed={"event_id", "event_type", "revision", "checksum", "occurred_at", "subject_id", "executor_id", "authority", "details"},
    )
    authority = raw.get("authority") or {}
    details = raw.get("details") or {}
    if not isinstance(authority, Mapping) or not isinstance(details, Mapping):
        raise ValueError("P2P_PROJECT_STRUCTURE_INVALID: event authority and details must be mappings")
    return ProjectStructureEvent(
        event_id=raw.get("event_id"),  # type: ignore[arg-type]
        event_type=str(raw.get("event_type") or ""),
        revision=raw.get("revision"),  # type: ignore[arg-type]
        checksum=str(raw.get("checksum") or ""),
        occurred_at=str(raw.get("occurred_at") or ""),
        subject_id=str(raw.get("subject_id") or ""),
        executor_id=str(raw.get("executor_id") or ""),
        authority=dict(authority),
        details=dict(details),
    )


def _section_from_mapping(value: object) -> StructureSection:
    raw = _strict_mapping(value, name="section", allowed={"id", "title", "description", "required", "order", "lifecycle"})
    return StructureSection(str(raw.get("id") or ""), str(raw.get("title") or ""), str(raw.get("description") or ""), _mapping_bool(raw, "required", True), raw.get("order", 0), str(raw.get("lifecycle") or "active"))  # type: ignore[arg-type]


def _field_from_mapping(value: object) -> StructureField:
    raw = _strict_mapping(value, name="field", allowed={"id", "section_id", "label", "description", "required", "order", "lifecycle"})
    return StructureField(str(raw.get("id") or ""), str(raw.get("section_id") or ""), str(raw.get("label") or ""), str(raw.get("description") or ""), _mapping_bool(raw, "required", True), raw.get("order", 0), str(raw.get("lifecycle") or "active"))  # type: ignore[arg-type]


def _question_from_mapping(value: object) -> StructureQuestion:
    raw = _strict_mapping(value, name="question", allowed={"id", "section_id", "prompt", "priority", "rationale", "order", "lifecycle"})
    return StructureQuestion(str(raw.get("id") or ""), str(raw.get("section_id") or ""), str(raw.get("prompt") or ""), str(raw.get("priority") or "medium"), str(raw.get("rationale") or ""), raw.get("order", 0), str(raw.get("lifecycle") or "active"))  # type: ignore[arg-type]


def _criterion_from_mapping(value: object) -> StructureCriterion:
    raw = _strict_mapping(value, name="criterion", allowed={"id", "section_id", "title", "required", "enabled", "keywords", "order", "lifecycle"})
    return StructureCriterion(str(raw.get("id") or ""), str(raw.get("section_id") or ""), str(raw.get("title") or ""), _mapping_bool(raw, "required", True), _mapping_bool(raw, "enabled", True), tuple(str(item) for item in _sequence(raw.get("keywords"), "criterion.keywords")), raw.get("order", 0), str(raw.get("lifecycle") or "active"))  # type: ignore[arg-type]


def _artifact_from_mapping(value: object) -> StructureArtifact:
    raw = _strict_mapping(value, name="artifact", allowed={"id", "title", "section_ids", "required", "order", "lifecycle"})
    return StructureArtifact(str(raw.get("id") or ""), str(raw.get("title") or ""), tuple(str(item) for item in _sequence(raw.get("section_ids"), "artifact.section_ids")), _mapping_bool(raw, "required", False), raw.get("order", 0), str(raw.get("lifecycle") or "active"))  # type: ignore[arg-type]


def _strict_mapping(value: object, *, name: str, allowed: set[str]) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"P2P_PROJECT_STRUCTURE_INVALID: {name} must be a mapping")
    unknown = sorted(str(item) for item in set(value) - allowed)
    if unknown:
        raise ValueError(
            f"P2P_PROJECT_STRUCTURE_INVALID: unsupported {name} fields: {', '.join(unknown)}"
        )
    return value


def _sequence(value: object, name: str) -> Sequence[object]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError(f"P2P_PROJECT_STRUCTURE_INVALID: {name} must be a list")
    return value


def _element_identity(kind: str, item: object) -> object:
    if kind == "field":
        return (str(getattr(item, "section_id")), str(getattr(item, "field_id")))
    return str(getattr(item, f"{kind}_id"))


def _require_bool(value: object, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"P2P_PROJECT_STRUCTURE_INVALID: {field_name} must be boolean")
    return value


def _mapping_bool(raw: Mapping[str, object], key: str, default: bool) -> bool:
    return _require_bool(raw.get(key, default), key)
