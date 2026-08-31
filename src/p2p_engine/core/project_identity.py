from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping
from uuid import UUID, uuid4, uuid5

from p2p_engine.core.mutation_preview import MutationPreview, MutationResult

PROJECT_IDENTITY_CONTRACT = "p2p-project-identity/v1"
PROJECT_REPLICA_CONTRACT = "p2p-project-replica/v1"
PROJECT_IDENTITY_POLICY_VERSION = 1
PROJECT_IDENTITY_MAX_LINEAGE = 32
PROJECT_DERIVATION_NAMESPACE = UUID("4bb15e8e-1066-4e40-a099-f167552107cc")

_OPAQUE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/+-]{0,255}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _identity_error(code: str, message: str) -> ValueError:
    return ValueError(f"{code}: {message}")


def _canonical_uuid(value: object, *, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise _identity_error("P2P_PROJECT_IDENTITY_INVALID", f"{field_name} is required")
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError) as exc:
        raise _identity_error(
            "P2P_PROJECT_IDENTITY_INVALID", f"{field_name} must be a UUID"
        ) from exc
    if parsed.int == 0 or str(parsed) != value:
        raise _identity_error(
            "P2P_PROJECT_IDENTITY_INVALID",
            f"{field_name} must be a canonical non-nil UUID",
        )
    return value


def _opaque_id(value: object, *, field_name: str) -> str:
    if not isinstance(value, str) or not _OPAQUE_ID.fullmatch(value):
        raise _identity_error(
            "P2P_PROJECT_IDENTITY_INVALID",
            f"{field_name} must be a bounded opaque identifier",
        )
    return value


def _display_name(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _identity_error("P2P_PROJECT_IDENTITY_INVALID", "display_name is required")
    normalized = value.strip()
    if len(normalized.encode("utf-8")) > 512 or "\x00" in normalized:
        raise _identity_error("P2P_PROJECT_IDENTITY_INVALID", "display_name exceeds its safe bound")
    return normalized


@dataclass(frozen=True, order=True)
class ProjectUuid:
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _canonical_uuid(self.value, field_name="project_uuid"))

    @classmethod
    def new(cls) -> ProjectUuid:
        return cls(str(uuid4()))

    @classmethod
    def for_operation(cls, source: ProjectUuid | None, operation_key: str) -> ProjectUuid:
        if not isinstance(operation_key, str) or not operation_key.strip():
            raise _identity_error(
                "P2P_IDEMPOTENCY_KEY_REQUIRED", "identity operation key is required"
            )
        seed = f"{source.value if source is not None else 'adoption'}:{operation_key}"
        return cls(str(uuid5(PROJECT_DERIVATION_NAMESPACE, seed)))

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, order=True)
class ReplicaId:
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _canonical_uuid(self.value, field_name="replica_id"))

    @classmethod
    def new(cls) -> ReplicaId:
        return cls(str(uuid4()))

    @classmethod
    def for_project_operation(cls, project_uuid: ProjectUuid, operation_key: str) -> ReplicaId:
        return cls(
            str(
                uuid5(
                    PROJECT_DERIVATION_NAMESPACE,
                    f"replica:{project_uuid.value}:{operation_key}",
                )
            )
        )

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, order=True)
class RemoteProjectId:
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "value",
            _opaque_id(self.value, field_name="remote_project_id"),
        )

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, order=True)
class ServerInstanceId:
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "value",
            _opaque_id(self.value, field_name="server_instance_id"),
        )

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class SourceMemoryRevision:
    sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.sha256, str) or not _SHA256.fullmatch(self.sha256):
            raise _identity_error(
                "P2P_PROJECT_REVISION_INVALID",
                "source-memory revision must be a lowercase SHA-256",
            )

    def compare(self, other: object) -> int:
        if not isinstance(other, SourceMemoryRevision):
            raise _identity_error(
                "P2P_PROJECT_REVISION_NAMESPACE_MISMATCH",
                "source-memory revisions cannot be compared with another namespace",
            )
        return (self.sha256 > other.sha256) - (self.sha256 < other.sha256)

    def to_dict(self) -> dict[str, object]:
        return {"namespace": "source_memory", "sha256": self.sha256}


@dataclass(frozen=True)
class _IntegerRevision:
    value: int
    namespace: str = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if isinstance(self.value, bool) or not isinstance(self.value, int) or self.value < 1:
            raise _identity_error(
                "P2P_PROJECT_REVISION_INVALID",
                f"{self.namespace} revision must be a positive integer",
            )

    def compare(self, other: object) -> int:
        if type(other) is not type(self):
            raise _identity_error(
                "P2P_PROJECT_REVISION_NAMESPACE_MISMATCH",
                f"{self.namespace} revisions cannot be compared with another namespace",
            )
        assert isinstance(other, _IntegerRevision)
        return (self.value > other.value) - (self.value < other.value)

    def to_dict(self) -> dict[str, object]:
        return {"namespace": self.namespace, "value": self.value}


@dataclass(frozen=True)
class RemoteProjectRevision(_IntegerRevision):
    namespace: str = field(init=False, default="remote_project", repr=False, compare=False)


@dataclass(frozen=True)
class EntityVersion(_IntegerRevision):
    namespace: str = field(init=False, default="entity", repr=False, compare=False)


@dataclass(frozen=True)
class AuthorityEpoch(_IntegerRevision):
    namespace: str = field(init=False, default="authority", repr=False, compare=False)


class ProjectMode(str, Enum):
    standalone = "standalone"
    linked = "linked"
    remote_only = "remote-only"
    link_suspended = "link-suspended"
    detached = "detached"


class LineageRelation(str, Enum):
    derived_from = "derived_from"
    detached_from = "detached_from"
    restored_from_bundle = "restored_from_bundle"


class LineageVisibility(str, Enum):
    preserved = "preserved"
    private = "private"


class CopyIntent(str, Enum):
    same_instance = "same-instance"
    new_replica = "new-replica"
    read_only = "read-only"
    derive = "derive"


@dataclass(frozen=True)
class RemoteBinding:
    server_instance_id: ServerInstanceId
    remote_project_id: RemoteProjectId

    def to_dict(self) -> dict[str, str]:
        return {
            "server_instance_id": self.server_instance_id.value,
            "remote_project_id": self.remote_project_id.value,
        }


@dataclass(frozen=True)
class ProjectLineage:
    relation: LineageRelation
    source_project_uuid: ProjectUuid
    source_revision: SourceMemoryRevision
    visibility: LineageVisibility = LineageVisibility.preserved

    def to_dict(self) -> dict[str, object]:
        return {
            "relation": self.relation.value,
            "source_project_uuid": self.source_project_uuid.value,
            "source_revision": self.source_revision.to_dict(),
            "visibility": self.visibility.value,
        }


@dataclass(frozen=True)
class ProjectIdentity:
    project_uuid: ProjectUuid
    display_name: str
    mode: ProjectMode
    replica_id: ReplicaId | None
    remote_binding: RemoteBinding | None = None
    lineage: tuple[ProjectLineage, ...] = ()
    policy_version: int = PROJECT_IDENTITY_POLICY_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "display_name", _display_name(self.display_name))
        if self.policy_version != PROJECT_IDENTITY_POLICY_VERSION:
            raise _identity_error(
                "P2P_PROJECT_IDENTITY_INVALID", "unsupported identity policy version"
            )
        if len(self.lineage) > PROJECT_IDENTITY_MAX_LINEAGE:
            raise _identity_error(
                "P2P_PROJECT_LINEAGE_INVALID", "lineage exceeds its bounded history"
            )
        sources: set[tuple[str, str, str]] = set()
        for item in self.lineage:
            if item.source_project_uuid == self.project_uuid:
                raise _identity_error(
                    "P2P_PROJECT_LINEAGE_CYCLE", "project lineage cannot reference itself"
                )
            key = (
                item.relation.value,
                item.source_project_uuid.value,
                item.source_revision.sha256,
            )
            if key in sources:
                raise _identity_error("P2P_PROJECT_LINEAGE_INVALID", "duplicate lineage entry")
            sources.add(key)
        bound = self.mode in {
            ProjectMode.linked,
            ProjectMode.remote_only,
            ProjectMode.link_suspended,
        }
        if bound != (self.remote_binding is not None):
            raise _identity_error(
                "P2P_PROJECT_IDENTITY_CONTRADICTORY",
                "mode and remote binding do not agree",
            )
        if self.mode == ProjectMode.remote_only:
            if self.replica_id is not None:
                raise _identity_error(
                    "P2P_PROJECT_IDENTITY_CONTRADICTORY",
                    "remote-only identity cannot claim a local replica",
                )
        elif self.replica_id is None:
            raise _identity_error(
                "P2P_PROJECT_IDENTITY_CONTRADICTORY",
                "an operational local identity requires replica_id",
            )

    @classmethod
    def new(cls, display_name: str) -> ProjectIdentity:
        return cls(
            project_uuid=ProjectUuid.new(),
            display_name=display_name,
            mode=ProjectMode.standalone,
            replica_id=ReplicaId.new(),
        )

    def with_display_name(self, display_name: str) -> ProjectIdentity:
        return ProjectIdentity(
            project_uuid=self.project_uuid,
            display_name=display_name,
            mode=self.mode,
            replica_id=self.replica_id,
            remote_binding=self.remote_binding,
            lineage=self.lineage,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": PROJECT_IDENTITY_CONTRACT,
            "policy_version": self.policy_version,
            "project_uuid": self.project_uuid.value,
            "display_name": self.display_name,
            "mode": self.mode.value,
            "remote_binding": (
                self.remote_binding.to_dict() if self.remote_binding is not None else None
            ),
            "replica_id": self.replica_id.value if self.replica_id is not None else None,
            "lineage": [item.to_dict() for item in self.lineage],
        }

    def canonical_project_dict(self) -> dict[str, object]:
        return {
            "contract": PROJECT_IDENTITY_CONTRACT,
            "policy_version": self.policy_version,
            "project_uuid": self.project_uuid.value,
            "display_name": self.display_name,
            "lineage": [item.to_dict() for item in self.lineage],
        }

    def local_replica_dict(self) -> dict[str, object]:
        return {
            "contract": PROJECT_REPLICA_CONTRACT,
            "project_uuid": self.project_uuid.value,
            "mode": self.mode.value,
            "replica_id": self.replica_id.value if self.replica_id is not None else None,
            "remote_binding": (
                self.remote_binding.to_dict() if self.remote_binding is not None else None
            ),
        }


@dataclass(frozen=True)
class IdentityTransitionRule:
    operation: str
    project_uuid_behavior: str
    replica_id_behavior: str
    binding_behavior: str
    explicit_owner_choice: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "operation": self.operation,
            "project_uuid": self.project_uuid_behavior,
            "replica_id": self.replica_id_behavior,
            "remote_binding": self.binding_behavior,
            "explicit_owner_choice": self.explicit_owner_choice,
        }


IDENTITY_TRANSITION_MATRIX: tuple[IdentityTransitionRule, ...] = (
    IdentityTransitionRule("init", "new", "new", "absent", False),
    IdentityTransitionRule("rename", "preserve", "preserve", "preserve", False),
    IdentityTransitionRule("move", "preserve", "preserve-if-source-retired", "preserve", True),
    IdentityTransitionRule("backup", "preserve", "non-operational-copy", "preserve", False),
    IdentityTransitionRule("restore", "preserve", "preserve-or-register", "preserve", True),
    IdentityTransitionRule(
        "share", "preserve", "register-if-materialized", "assign-or-preserve", True
    ),
    IdentityTransitionRule("clone", "preserve", "new", "preserve", True),
    IdentityTransitionRule("copy", "owner-choice", "owner-choice", "owner-choice", True),
    IdentityTransitionRule("derive", "new", "new", "remove", True),
    IdentityTransitionRule("suspend", "preserve", "preserve", "preserve", True),
    IdentityTransitionRule("detach", "new", "new", "remove", True),
)


@dataclass(frozen=True)
class TransferIdentityContract:
    project_uuid: ProjectUuid
    server_instance_id: ServerInstanceId
    remote_project_id: RemoteProjectId | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "project_uuid": self.project_uuid.value,
            "server_instance_id": self.server_instance_id.value,
            "remote_project_id": (
                self.remote_project_id.value if self.remote_project_id is not None else None
            ),
        }


@dataclass(frozen=True)
class ReplicaIdentityContract:
    project_uuid: ProjectUuid
    source_replica_id: ReplicaId | None
    target_replica_id: ReplicaId
    move: bool

    def __post_init__(self) -> None:
        if not self.move and self.source_replica_id == self.target_replica_id:
            raise _identity_error(
                "P2P_PROJECT_REPLICA_COLLISION",
                "a copied operational replica requires a new replica_id",
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "project_uuid": self.project_uuid.value,
            "source_replica_id": (
                self.source_replica_id.value if self.source_replica_id is not None else None
            ),
            "target_replica_id": self.target_replica_id.value,
            "move": self.move,
        }


@dataclass(frozen=True)
class DetachIdentityContract:
    source_project_uuid: ProjectUuid
    detached_project_uuid: ProjectUuid
    detached_replica_id: ReplicaId
    source_revision: SourceMemoryRevision
    retain_lineage: bool = True

    def __post_init__(self) -> None:
        if self.source_project_uuid == self.detached_project_uuid:
            raise _identity_error(
                "P2P_PROJECT_IDENTITY_CONTRADICTORY",
                "detach requires a new project_uuid",
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "source_project_uuid": self.source_project_uuid.value,
            "detached_project_uuid": self.detached_project_uuid.value,
            "detached_replica_id": self.detached_replica_id.value,
            "source_revision": self.source_revision.to_dict(),
            "retain_lineage": self.retain_lineage,
        }


@dataclass(frozen=True)
class CopyCollisionAssessment:
    state: str
    project_uuid: ProjectUuid
    local_replica_id: ReplicaId | None
    observed_replica_id: ReplicaId | None
    selected_intent: CopyIntent | None
    allowed: bool
    next_actions: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "state": self.state,
            "project_uuid": self.project_uuid.value,
            "local_replica_id": (
                self.local_replica_id.value if self.local_replica_id is not None else None
            ),
            "observed_replica_id": (
                self.observed_replica_id.value if self.observed_replica_id is not None else None
            ),
            "selected_intent": (
                self.selected_intent.value if self.selected_intent is not None else None
            ),
            "allowed": self.allowed,
            "next_actions": list(self.next_actions),
        }


@dataclass(frozen=True)
class ProjectIdentityStatus:
    state: str
    identity: ProjectIdentity | None
    blockers: tuple[str, ...] = ()
    suggested_command: str = ""

    @property
    def mutable(self) -> bool:
        return self.state == "valid" and not self.blockers

    def to_dict(self) -> dict[str, object]:
        return {
            "state": self.state,
            "mutable": self.mutable,
            "identity": self.identity.to_dict() if self.identity is not None else None,
            "blockers": list(self.blockers),
            "suggested_command": self.suggested_command,
        }


@dataclass(frozen=True)
class ProjectIdentityMutationPreview:
    kind: str
    previous: ProjectIdentity | None
    candidate: ProjectIdentity
    source_revision: SourceMemoryRevision
    mutation: MutationPreview
    backup_path: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "previous": self.previous.to_dict() if self.previous is not None else None,
            "candidate": self.candidate.to_dict(),
            "source_revision": self.source_revision.to_dict(),
            "backup_path": self.backup_path or None,
            "mutation": self.mutation.to_dict(),
        }


@dataclass(frozen=True)
class ProjectIdentityMutationResult:
    status: str
    kind: str
    previous: ProjectIdentity | None
    current: ProjectIdentity
    source_revision: SourceMemoryRevision
    mutation: MutationResult
    message: str

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "kind": self.kind,
            "previous": self.previous.to_dict() if self.previous is not None else None,
            "current": self.current.to_dict(),
            "source_revision": self.source_revision.to_dict(),
            "mutation": self.mutation.to_dict(),
            "message": self.message,
        }


def lineage_from_mapping(raw: Mapping[str, object]) -> ProjectLineage:
    allowed = {"relation", "source_project_uuid", "source_revision", "visibility"}
    if set(raw) != allowed:
        raise _identity_error("P2P_PROJECT_LINEAGE_INVALID", "lineage fields are not canonical")
    revision = raw.get("source_revision")
    if not isinstance(revision, Mapping) or set(revision) != {"namespace", "sha256"}:
        raise _identity_error("P2P_PROJECT_REVISION_INVALID", "lineage source revision is invalid")
    if revision.get("namespace") != "source_memory":
        raise _identity_error(
            "P2P_PROJECT_REVISION_NAMESPACE_MISMATCH",
            "lineage requires a source-memory revision",
        )
    try:
        relation = LineageRelation(str(raw.get("relation") or ""))
        visibility = LineageVisibility(str(raw.get("visibility") or ""))
    except ValueError as exc:
        raise _identity_error(
            "P2P_PROJECT_LINEAGE_INVALID", "lineage relation or visibility is invalid"
        ) from exc
    return ProjectLineage(
        relation=relation,
        source_project_uuid=ProjectUuid(str(raw.get("source_project_uuid") or "")),
        source_revision=SourceMemoryRevision(str(revision.get("sha256") or "")),
        visibility=visibility,
    )


def remote_binding_from_mapping(raw: object) -> RemoteBinding | None:
    if raw is None:
        return None
    if not isinstance(raw, Mapping) or set(raw) != {
        "server_instance_id",
        "remote_project_id",
    }:
        raise _identity_error("P2P_PROJECT_IDENTITY_INVALID", "remote binding fields are invalid")
    return RemoteBinding(
        server_instance_id=ServerInstanceId(str(raw.get("server_instance_id") or "")),
        remote_project_id=RemoteProjectId(str(raw.get("remote_project_id") or "")),
    )


def project_identity_from_mapping(raw: object) -> ProjectIdentity:
    if not isinstance(raw, Mapping):
        raise _identity_error("P2P_PROJECT_IDENTITY_INVALID", "identity must be a mapping")
    expected = {
        "contract",
        "policy_version",
        "project_uuid",
        "display_name",
        "mode",
        "remote_binding",
        "replica_id",
        "lineage",
    }
    if set(raw) != expected or raw.get("contract") != PROJECT_IDENTITY_CONTRACT:
        raise _identity_error(
            "P2P_PROJECT_IDENTITY_INVALID", "identity fields or contract are invalid"
        )
    raw_lineage = raw.get("lineage")
    if not isinstance(raw_lineage, list):
        raise _identity_error("P2P_PROJECT_LINEAGE_INVALID", "lineage must be a sequence")
    try:
        mode = ProjectMode(str(raw.get("mode") or ""))
    except ValueError as exc:
        raise _identity_error(
            "P2P_PROJECT_IDENTITY_INVALID", "project mode is unsupported"
        ) from exc
    raw_replica = raw.get("replica_id")
    policy_version = raw.get("policy_version")
    if isinstance(policy_version, bool) or not isinstance(policy_version, int):
        raise _identity_error(
            "P2P_PROJECT_IDENTITY_INVALID", "identity policy_version must be an integer"
        )
    return ProjectIdentity(
        project_uuid=ProjectUuid(str(raw.get("project_uuid") or "")),
        display_name=str(raw.get("display_name") or ""),
        mode=mode,
        replica_id=ReplicaId(str(raw_replica)) if raw_replica is not None else None,
        remote_binding=remote_binding_from_mapping(raw.get("remote_binding")),
        lineage=tuple(
            lineage_from_mapping(item) if isinstance(item, Mapping) else _raise_invalid_lineage()
            for item in raw_lineage
        ),
        policy_version=policy_version,
    )


def _raise_invalid_lineage():
    raise _identity_error("P2P_PROJECT_LINEAGE_INVALID", "lineage entry must be a mapping")
