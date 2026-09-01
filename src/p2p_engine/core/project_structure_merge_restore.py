from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from p2p_engine.core.project_structure import (
    PROJECT_STRUCTURE_ELEMENT_KINDS,
    ProjectStructure,
    normalize_structure_id,
    normalize_structure_text,
    project_structure_from_mapping,
)
from p2p_engine.core.project_structure_retirement import (
    StructureRetirementDisposition,
    structure_retirement_disposition_from_mapping,
)

STRUCTURE_SNAPSHOT_CONTRACT = "p2p-project-structure-snapshot/v1"
STRUCTURE_SNAPSHOT_LEDGER_CONTRACT = "p2p-project-structure-snapshots/v1"
STRUCTURE_MERGE_PLAN_CONTRACT = "p2p-structure-merge-plan/v1"
STRUCTURE_RESTORE_PLAN_CONTRACT = "p2p-structure-restore-plan/v1"
STRUCTURE_MERGE_PREVIEW_CONTRACT = "p2p-structure-merge-preview/v1"
STRUCTURE_RESTORE_PREVIEW_CONTRACT = "p2p-structure-restore-preview/v1"
STRUCTURE_TRANSITION_RESULT_CONTRACT = "p2p-structure-transition-result/v1"
STRUCTURE_COMPARISON_CONTRACT = "p2p-structure-comparison/v1"

PROJECT_STRUCTURE_MERGE_OPERATION = "project_structure_merge"
PROJECT_STRUCTURE_RESTORE_OPERATION = "project_structure_restore"
PROJECT_STRUCTURE_MERGE_CAPABILITY = "project.structure.merge"
PROJECT_STRUCTURE_RESTORE_CAPABILITY = "project.structure.restore"

STRUCTURE_SNAPSHOT_RETENTION_LIMIT = 100
STRUCTURE_TRANSITION_LIMIT = 1000
COLLISION_ACTIONS = frozenset({"keep-current", "replace-with-impact", "import-as-new-id"})


@dataclass(frozen=True)
class StructureElementRef:
    kind: str
    element_id: str
    section_id: str | None = None

    def __post_init__(self) -> None:
        kind = str(self.kind).strip().lower()
        if kind not in PROJECT_STRUCTURE_ELEMENT_KINDS:
            raise ValueError("P2P_STRUCTURE_ELEMENT_REF_INVALID: unsupported kind")
        element_id = normalize_structure_id(self.element_id, field_name="element_ref.id")
        section_id = (
            normalize_structure_id(self.section_id, field_name="element_ref.section_id")
            if self.section_id is not None
            else None
        )
        if kind == "field" and section_id is None:
            raise ValueError(
                "P2P_STRUCTURE_ELEMENT_REF_INVALID: field reference requires section_id"
            )
        if kind != "field" and section_id is not None:
            raise ValueError(
                "P2P_STRUCTURE_ELEMENT_REF_INVALID: section_id only disambiguates fields"
            )
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "element_id", element_id)
        object.__setattr__(self, "section_id", section_id)

    @property
    def identity(self) -> str:
        if self.kind == "field":
            return f"field:{self.section_id}/{self.element_id}"
        return f"{self.kind}:{self.element_id}"

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {"kind": self.kind, "id": self.element_id}
        if self.section_id is not None:
            payload["section_id"] = self.section_id
        return payload


@dataclass(frozen=True)
class StructurePlacement:
    identity: str
    parent_id: str
    order: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "identity",
            normalize_structure_text(
                self.identity,
                field_name="placement.identity",
                maximum_bytes=256,
            ),
        )
        parent = str(self.parent_id or "root").strip().lower()
        if parent != "root":
            parent = normalize_structure_id(parent, field_name="placement.parent_id")
        object.__setattr__(self, "parent_id", parent)
        if isinstance(self.order, bool) or not isinstance(self.order, int) or self.order < 0:
            raise ValueError("P2P_STRUCTURE_PLACEMENT_INVALID: order must be non-negative")

    def to_dict(self) -> dict[str, object]:
        return {
            "identity": self.identity,
            "parent_id": self.parent_id,
            "order": self.order,
        }


@dataclass(frozen=True)
class StructureCollisionDecision:
    identity: str
    action: str
    new_id: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "identity",
            normalize_structure_text(
                self.identity,
                field_name="collision.identity",
                maximum_bytes=256,
            ),
        )
        action = str(self.action).strip().lower()
        if action not in COLLISION_ACTIONS:
            raise ValueError("P2P_STRUCTURE_COLLISION_INVALID: unsupported action")
        object.__setattr__(self, "action", action)
        if action == "import-as-new-id":
            object.__setattr__(
                self,
                "new_id",
                normalize_structure_id(self.new_id, field_name="collision.new_id"),
            )
        elif self.new_id:
            raise ValueError(
                "P2P_STRUCTURE_COLLISION_INVALID: new_id is only valid for import-as-new-id"
            )

    def to_dict(self) -> dict[str, object]:
        payload = {"identity": self.identity, "action": self.action}
        if self.new_id:
            payload["new_id"] = self.new_id
        return payload


@dataclass(frozen=True)
class StructureSourceIdentity:
    kind: str
    identity: str
    digest: str
    schema_version: int

    def __post_init__(self) -> None:
        kind = str(self.kind).strip().lower()
        if kind not in {"release", "bundle", "retained_revision"}:
            raise ValueError("P2P_STRUCTURE_SOURCE_INVALID: unsupported source kind")
        object.__setattr__(self, "kind", kind)
        object.__setattr__(
            self,
            "identity",
            normalize_structure_text(
                self.identity,
                field_name="source.identity",
                maximum_bytes=256,
            ),
        )
        digest = str(self.digest or "").removeprefix("sha256:")
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise ValueError("P2P_STRUCTURE_SOURCE_INVALID: digest must be SHA-256")
        object.__setattr__(self, "digest", digest)
        if (
            isinstance(self.schema_version, bool)
            or not isinstance(self.schema_version, int)
            or self.schema_version < 1
        ):
            raise ValueError("P2P_STRUCTURE_SOURCE_INVALID: schema version is invalid")

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "identity": self.identity,
            "digest": self.digest,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class RetainedStructureSnapshot:
    structure: ProjectStructure
    retained_at: str
    retained_by: str
    reason: str
    contract: str = STRUCTURE_SNAPSHOT_CONTRACT

    def __post_init__(self) -> None:
        if self.contract != STRUCTURE_SNAPSHOT_CONTRACT:
            raise ValueError("P2P_STRUCTURE_SNAPSHOT_UNSUPPORTED: unsupported contract")
        for value, field_name, maximum in (
            (self.retained_at, "retained_at", 64),
            (self.retained_by, "retained_by", 128),
            (self.reason, "reason", 128),
        ):
            normalize_structure_text(
                value, field_name=f"snapshot.{field_name}", maximum_bytes=maximum
            )

    @property
    def revision(self) -> int:
        return self.structure.revision

    @property
    def checksum(self) -> str:
        return self.structure.checksum

    def to_storage_dict(self) -> dict[str, object]:
        return {
            "contract": self.contract,
            "retained_at": self.retained_at,
            "retained_by": self.retained_by,
            "reason": self.reason,
            "structure": self.structure.to_storage_dict(),
        }

    def to_dict(self, *, include_structure: bool = False) -> dict[str, object]:
        payload: dict[str, object] = {
            "contract": self.contract,
            "structure_id": self.structure.structure_id,
            "revision": self.revision,
            "checksum": self.checksum,
            "retained_at": self.retained_at,
            "retained_by": self.retained_by,
            "reason": self.reason,
        }
        if include_structure:
            payload["structure"] = self.structure.to_dict(include_retired=True)
        return payload


@dataclass(frozen=True)
class RetainedStructureLedger:
    structure_id: str
    snapshots: tuple[RetainedStructureSnapshot, ...] = ()
    retention_limit: int = STRUCTURE_SNAPSHOT_RETENTION_LIMIT
    contract: str = STRUCTURE_SNAPSHOT_LEDGER_CONTRACT

    def __post_init__(self) -> None:
        if self.contract != STRUCTURE_SNAPSHOT_LEDGER_CONTRACT:
            raise ValueError("P2P_STRUCTURE_SNAPSHOT_LEDGER_UNSUPPORTED: unsupported contract")
        normalize_structure_id(self.structure_id, field_name="snapshot_ledger.structure_id")
        if self.retention_limit != STRUCTURE_SNAPSHOT_RETENTION_LIMIT:
            raise ValueError("P2P_STRUCTURE_SNAPSHOT_RETENTION_INVALID: unsupported policy")
        revisions = [item.revision for item in self.snapshots]
        if revisions != sorted(set(revisions)):
            raise ValueError(
                "P2P_STRUCTURE_SNAPSHOT_LEDGER_INVALID: revisions must be unique and sorted"
            )
        if len(revisions) > self.retention_limit:
            raise ValueError("P2P_STRUCTURE_SNAPSHOT_LEDGER_INVALID: retention limit exceeded")
        if any(item.structure.structure_id != self.structure_id for item in self.snapshots):
            raise ValueError("P2P_STRUCTURE_SNAPSHOT_LEDGER_INVALID: structure identity mismatch")

    def to_storage_dict(self) -> dict[str, object]:
        return {
            "contract": self.contract,
            "structure_id": self.structure_id,
            "retention": {
                "mode": "newest-revisions",
                "limit": self.retention_limit,
                "automatic_pruning": True,
            },
            "snapshots": [item.to_storage_dict() for item in self.snapshots],
        }

    def retain(self, snapshot: RetainedStructureSnapshot) -> "RetainedStructureLedger":
        by_revision = {item.revision: item for item in self.snapshots}
        existing = by_revision.get(snapshot.revision)
        if existing is not None and existing.checksum != snapshot.checksum:
            raise ValueError("P2P_STRUCTURE_SNAPSHOT_COLLISION: revision checksum differs")
        by_revision[snapshot.revision] = existing or snapshot
        retained = tuple(by_revision[key] for key in sorted(by_revision))
        if len(retained) > self.retention_limit:
            retained = retained[-self.retention_limit :]
        return RetainedStructureLedger(
            structure_id=self.structure_id,
            snapshots=retained,
            retention_limit=self.retention_limit,
        )

    def resolve(self, revision: int) -> RetainedStructureSnapshot:
        match = next((item for item in self.snapshots if item.revision == revision), None)
        if match is None:
            raise ValueError(
                "P2P_STRUCTURE_SNAPSHOT_UNAVAILABLE: revision is unavailable or has been pruned"
            )
        return match


@dataclass(frozen=True)
class StructureMergePlan:
    source: StructureSourceIdentity
    expected_target_revision: int
    expected_target_checksum: str
    expected_memory_revision: str
    selected: tuple[StructureElementRef, ...]
    dependency_closure: tuple[StructureElementRef, ...]
    placements: tuple[StructurePlacement, ...]
    collisions: tuple[StructureCollisionDecision, ...]
    dispositions: tuple[StructureRetirementDisposition, ...] = ()
    contract: str = STRUCTURE_MERGE_PLAN_CONTRACT

    def __post_init__(self) -> None:
        if self.contract != STRUCTURE_MERGE_PLAN_CONTRACT:
            raise ValueError("P2P_STRUCTURE_MERGE_PLAN_UNSUPPORTED: unsupported contract")
        _positive_revision(self.expected_target_revision, "expected_target_revision")
        _sha256(self.expected_target_checksum, "expected_target_checksum")
        _sha256(self.expected_memory_revision, "expected_memory_revision")
        _unique_identities(self.selected, "selected")
        _unique_identities(self.dependency_closure, "dependency_closure")
        _unique_text([item.identity for item in self.placements], "placements")
        _unique_text([item.identity for item in self.collisions], "collisions")
        _unique_text([item.disposition_id for item in self.dispositions], "dispositions")
        if not self.selected:
            raise ValueError("P2P_STRUCTURE_MERGE_PLAN_INVALID: selected cannot be empty")
        if len(self.selected) + len(self.dependency_closure) > STRUCTURE_TRANSITION_LIMIT:
            raise ValueError("P2P_STRUCTURE_MERGE_PLAN_INVALID: selection limit exceeded")

    @property
    def selected_identities(self) -> tuple[str, ...]:
        return tuple(item.identity for item in self.selected)

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": self.contract,
            "source": self.source.to_dict(),
            "target": {
                "revision": self.expected_target_revision,
                "checksum": self.expected_target_checksum,
                "memory_revision": self.expected_memory_revision,
            },
            "selected": [item.to_dict() for item in self.selected],
            "dependency_closure": [item.to_dict() for item in self.dependency_closure],
            "placements": [item.to_dict() for item in self.placements],
            "collisions": [item.to_dict() for item in self.collisions],
            "dispositions": [item.to_dict() for item in self.dispositions],
        }


@dataclass(frozen=True)
class StructureRestorePlan:
    source_revision: int
    source_checksum: str
    expected_target_revision: int
    expected_target_checksum: str
    expected_memory_revision: str
    dispositions: tuple[StructureRetirementDisposition, ...] = ()
    contract: str = STRUCTURE_RESTORE_PLAN_CONTRACT

    def __post_init__(self) -> None:
        if self.contract != STRUCTURE_RESTORE_PLAN_CONTRACT:
            raise ValueError("P2P_STRUCTURE_RESTORE_PLAN_UNSUPPORTED: unsupported contract")
        _positive_revision(self.source_revision, "source_revision")
        _positive_revision(self.expected_target_revision, "expected_target_revision")
        _sha256(self.source_checksum, "source_checksum")
        _sha256(self.expected_target_checksum, "expected_target_checksum")
        _sha256(self.expected_memory_revision, "expected_memory_revision")
        _unique_text([item.disposition_id for item in self.dispositions], "dispositions")

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": self.contract,
            "source": {
                "kind": "retained_revision",
                "revision": self.source_revision,
                "checksum": self.source_checksum,
            },
            "target": {
                "revision": self.expected_target_revision,
                "checksum": self.expected_target_checksum,
                "memory_revision": self.expected_memory_revision,
            },
            "dispositions": [item.to_dict() for item in self.dispositions],
        }


@dataclass(frozen=True)
class StructureComparison:
    source: StructureSourceIdentity
    current: ProjectStructure
    elements: tuple[Mapping[str, object], ...]
    selected: tuple[StructureElementRef, ...] = ()
    dependency_closure: tuple[StructureElementRef, ...] = ()
    collisions: tuple[Mapping[str, object], ...] = ()
    blockers: tuple[str, ...] = ()
    truncated: bool = False
    contract: str = STRUCTURE_COMPARISON_CONTRACT

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": self.contract,
            "source": self.source.to_dict(),
            "current": structure_summary(self.current),
            "selected": [item.to_dict() for item in self.selected],
            "dependency_closure": [item.to_dict() for item in self.dependency_closure],
            "elements": [dict(item) for item in self.elements],
            "collisions": [dict(item) for item in self.collisions],
            "blockers": list(self.blockers),
            "truncated": self.truncated,
            "mutation_performed": False,
        }


@dataclass(frozen=True)
class StructureTransitionPreview:
    operation: str
    source: StructureSourceIdentity
    current: ProjectStructure
    candidate: ProjectStructure | None
    expected_memory_revision: str
    selected: tuple[StructureElementRef, ...] = ()
    dependency_closure: tuple[StructureElementRef, ...] = ()
    elements: tuple[Mapping[str, object], ...] = ()
    collisions: tuple[Mapping[str, object], ...] = ()
    impacts: tuple[Mapping[str, object], ...] = ()
    required_dispositions: tuple[Mapping[str, object], ...] = ()
    applied_dispositions: tuple[StructureRetirementDisposition, ...] = ()
    readiness_projection: Mapping[str, object] = field(default_factory=dict)
    classification_projection: Mapping[str, object] = field(default_factory=dict)
    blockers: tuple[str, ...] = ()
    preview_token: str = ""
    plan_digest: str = ""
    contract: str = ""

    @property
    def apply_allowed(self) -> bool:
        return self.candidate is not None and not self.blockers and bool(self.preview_token)

    def to_dict(self) -> dict[str, object]:
        contract = self.contract or (
            STRUCTURE_MERGE_PREVIEW_CONTRACT
            if self.operation == "merge"
            else STRUCTURE_RESTORE_PREVIEW_CONTRACT
        )
        return {
            "contract": contract,
            "operation": self.operation,
            "source": self.source.to_dict(),
            "current": structure_summary(self.current),
            "candidate": structure_summary(self.candidate) if self.candidate else None,
            "expected_memory_revision": self.expected_memory_revision,
            "selected": [item.to_dict() for item in self.selected],
            "dependency_closure": [item.to_dict() for item in self.dependency_closure],
            "elements": [dict(item) for item in self.elements],
            "collisions": [dict(item) for item in self.collisions],
            "impacts": [dict(item) for item in self.impacts],
            "required_dispositions": [dict(item) for item in self.required_dispositions],
            "applied_dispositions": [item.to_dict() for item in self.applied_dispositions],
            "readiness_projection": dict(self.readiness_projection),
            "classification_projection": dict(self.classification_projection),
            "blockers": list(self.blockers),
            "complete": not self.blockers,
            "apply_allowed": self.apply_allowed,
            "preview_token": self.preview_token if self.apply_allowed else None,
            "plan_digest": self.plan_digest,
            "forward_revision": self.candidate.revision if self.candidate else None,
            "detached_copy": True,
            "active_release_subscription": False,
            "second_authority_created": False,
            "mutation_performed": False,
        }


@dataclass(frozen=True)
class StructureTransitionResult:
    operation: str
    status: str
    source: StructureSourceIdentity
    previous: ProjectStructure
    current: ProjectStructure
    previous_memory_revision: str
    current_memory_revision: str
    event: Mapping[str, object]
    actor: str
    receipt_key_sha256: str
    changed_entities: tuple[str, ...]
    message: str
    contract: str = STRUCTURE_TRANSITION_RESULT_CONTRACT

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": self.contract,
            "operation": self.operation,
            "status": self.status,
            "source": self.source.to_dict(),
            "previous": structure_summary(self.previous),
            "current": structure_summary(self.current),
            "previous_memory_revision": self.previous_memory_revision,
            "current_memory_revision": self.current_memory_revision,
            "event": dict(self.event),
            "actor": self.actor,
            "receipt": {"key_sha256": self.receipt_key_sha256},
            "changed_entities": list(self.changed_entities),
            "detached_copy": True,
            "active_release_subscription": False,
            "second_authority_created": False,
            "message": self.message,
        }


def structure_summary(structure: ProjectStructure | None) -> dict[str, object] | None:
    if structure is None:
        return None
    return {
        "contract": structure.contract,
        "structure_id": structure.structure_id,
        "revision": structure.revision,
        "checksum": structure.checksum,
        "origin": structure.origin.to_dict(),
    }


def structure_element_ref_from_mapping(value: object) -> StructureElementRef:
    raw = _mapping(value, "element reference")
    _closed(raw, {"kind", "id", "section_id"}, "element reference")
    return StructureElementRef(
        kind=str(raw.get("kind") or ""),
        element_id=str(raw.get("id") or ""),
        section_id=(str(raw["section_id"]) if raw.get("section_id") is not None else None),
    )


def structure_merge_plan_from_mapping(value: object) -> StructureMergePlan:
    raw = _unwrap(value, "project_structure_merge_plan", STRUCTURE_MERGE_PLAN_CONTRACT)
    _closed(
        raw,
        {
            "contract",
            "source",
            "target",
            "selected",
            "dependency_closure",
            "placements",
            "collisions",
            "dispositions",
        },
        "merge plan",
    )
    source = _mapping(raw.get("source"), "source")
    _closed(source, {"kind", "identity", "digest", "schema_version"}, "source")
    target = _mapping(raw.get("target"), "target")
    _closed(target, {"revision", "checksum", "memory_revision"}, "target")
    return StructureMergePlan(
        source=StructureSourceIdentity(
            kind=str(source.get("kind") or ""),
            identity=str(source.get("identity") or ""),
            digest=str(source.get("digest") or ""),
            schema_version=_integer(source.get("schema_version"), "source.schema_version"),
        ),
        expected_target_revision=_integer(target.get("revision"), "target.revision"),
        expected_target_checksum=str(target.get("checksum") or ""),
        expected_memory_revision=str(target.get("memory_revision") or ""),
        selected=tuple(
            structure_element_ref_from_mapping(item)
            for item in _sequence(raw.get("selected"), "selected")
        ),
        dependency_closure=tuple(
            structure_element_ref_from_mapping(item)
            for item in _sequence(raw.get("dependency_closure"), "dependency_closure")
        ),
        placements=tuple(
            _placement(item) for item in _sequence(raw.get("placements"), "placements")
        ),
        collisions=tuple(
            _collision(item) for item in _sequence(raw.get("collisions"), "collisions")
        ),
        dispositions=tuple(
            structure_retirement_disposition_from_mapping(item)
            for item in _sequence(raw.get("dispositions"), "dispositions")
        ),
    )


def structure_restore_plan_from_mapping(value: object) -> StructureRestorePlan:
    raw = _unwrap(value, "project_structure_restore_plan", STRUCTURE_RESTORE_PLAN_CONTRACT)
    _closed(raw, {"contract", "source", "target", "dispositions"}, "restore plan")
    source = _mapping(raw.get("source"), "source")
    _closed(source, {"kind", "revision", "checksum"}, "source")
    if source.get("kind") != "retained_revision":
        raise ValueError("P2P_STRUCTURE_RESTORE_PLAN_INVALID: source kind is invalid")
    target = _mapping(raw.get("target"), "target")
    _closed(target, {"revision", "checksum", "memory_revision"}, "target")
    return StructureRestorePlan(
        source_revision=_integer(source.get("revision"), "source.revision"),
        source_checksum=str(source.get("checksum") or ""),
        expected_target_revision=_integer(target.get("revision"), "target.revision"),
        expected_target_checksum=str(target.get("checksum") or ""),
        expected_memory_revision=str(target.get("memory_revision") or ""),
        dispositions=tuple(
            structure_retirement_disposition_from_mapping(item)
            for item in _sequence(raw.get("dispositions"), "dispositions")
        ),
    )


def retained_snapshot_from_mapping(value: object) -> RetainedStructureSnapshot:
    raw = _mapping(value, "retained snapshot")
    _closed(
        raw, {"contract", "retained_at", "retained_by", "reason", "structure"}, "retained snapshot"
    )
    return RetainedStructureSnapshot(
        contract=str(raw.get("contract") or ""),
        retained_at=str(raw.get("retained_at") or ""),
        retained_by=str(raw.get("retained_by") or ""),
        reason=str(raw.get("reason") or ""),
        structure=project_structure_from_mapping(raw.get("structure")),
    )


def _placement(value: object) -> StructurePlacement:
    raw = _mapping(value, "placement")
    _closed(raw, {"identity", "parent_id", "order"}, "placement")
    return StructurePlacement(
        identity=str(raw.get("identity") or ""),
        parent_id=str(raw.get("parent_id") or ""),
        order=_integer(raw.get("order"), "placement.order"),
    )


def _collision(value: object) -> StructureCollisionDecision:
    raw = _mapping(value, "collision")
    _closed(raw, {"identity", "action", "new_id"}, "collision")
    return StructureCollisionDecision(
        identity=str(raw.get("identity") or ""),
        action=str(raw.get("action") or ""),
        new_id=str(raw.get("new_id") or ""),
    )


def _unwrap(value: object, root: str, contract: str) -> Mapping[str, object]:
    raw = _mapping(value, "plan")
    if set(raw) == {root}:
        raw = _mapping(raw.get(root), root)
    if raw.get("contract") != contract:
        raise ValueError("P2P_STRUCTURE_PLAN_UNSUPPORTED: unsupported plan contract")
    return raw


def _mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"P2P_STRUCTURE_PLAN_INVALID: {name} must be a mapping")
    return value


def _sequence(value: object, name: str) -> Sequence[object]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError(f"P2P_STRUCTURE_PLAN_INVALID: {name} must be a list")
    return value


def _closed(value: Mapping[str, object], allowed: set[str], name: str) -> None:
    unknown = sorted(str(key) for key in set(value) - allowed)
    if unknown:
        raise ValueError(
            f"P2P_STRUCTURE_PLAN_INVALID: unsupported {name} fields: {', '.join(unknown)}"
        )


def _integer(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"P2P_STRUCTURE_PLAN_INVALID: {name} must be an integer")
    return value


def _positive_revision(value: int, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"P2P_STRUCTURE_PLAN_INVALID: {name} must be positive")


def _sha256(value: str, name: str) -> None:
    digest = str(value or "").removeprefix("sha256:")
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise ValueError(f"P2P_STRUCTURE_PLAN_INVALID: {name} must be SHA-256")


def _unique_identities(values: Sequence[StructureElementRef], name: str) -> None:
    _unique_text([item.identity for item in values], name)


def _unique_text(values: Sequence[str], name: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"P2P_STRUCTURE_PLAN_INVALID: {name} contains duplicates")
