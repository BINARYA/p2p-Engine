from __future__ import annotations

from dataclasses import dataclass, field
import re
from collections.abc import Sequence
from typing import Mapping


PROJECT_DOMAIN_CONTRACT = "p2p-project-domain/v1"
STRUCTURE_SOURCE_CONTRACT = "p2p-structure-source/v1"
PROJECT_DOMAIN_MAX_KEY_BYTES = 64
PROJECT_DOMAIN_MAX_NAME_BYTES = 160
PROJECT_DOMAIN_MAX_EXTERNAL_REF_BYTES = 512
PROJECT_DOMAIN_SOURCES = frozenset({"local", "external", "imported", "system"})
PROJECT_STARTERS = frozenset({"generic", "empty"})
VERTICAL_DOMAIN_TAG_LIMIT = 16

_KEY = re.compile(r"^[a-z0-9](?:[a-z0-9._-]{0,62}[a-z0-9])?$")
_CHECKSUM = re.compile(r"^(?:sha256:)?[0-9a-f]{64}$")
_VERTICAL_COORDINATE = re.compile(
    r"^[a-z0-9](?:[a-z0-9._-]{0,62}[a-z0-9])?/"
    r"[a-z0-9](?:[a-z0-9_-]{0,62}[a-z0-9])?@"
    r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def normalize_domain_key(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("P2P_PROJECT_DOMAIN_INVALID: domain key must be text")
    key = value.strip().lower()
    if (
        not key
        or len(key.encode("utf-8")) > PROJECT_DOMAIN_MAX_KEY_BYTES
        or not _KEY.fullmatch(key)
        or "/" in key
        or "\\" in key
        or key in {".", ".."}
    ):
        raise ValueError(
            "P2P_PROJECT_DOMAIN_INVALID: domain key must be a bounded lower-case identifier"
        )
    return key


def normalize_domain_name(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("P2P_PROJECT_DOMAIN_INVALID: domain name must be text")
    name = " ".join(value.strip().split())
    if (
        not name
        or len(name.encode("utf-8")) > PROJECT_DOMAIN_MAX_NAME_BYTES
        or _CONTROL.search(name)
    ):
        raise ValueError("P2P_PROJECT_DOMAIN_INVALID: domain name is empty or unsafe")
    return name


def normalize_domain_source(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("P2P_PROJECT_DOMAIN_INVALID: domain source must be text")
    source = value.strip().lower()
    if source not in PROJECT_DOMAIN_SOURCES:
        raise ValueError(
            "P2P_PROJECT_DOMAIN_INVALID: domain source must be local, external, imported, or system"
        )
    return source


def normalize_external_ref(value: object | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("P2P_PROJECT_DOMAIN_INVALID: external_ref must be text or null")
    external_ref = value.strip()
    if (
        not external_ref
        or len(external_ref.encode("utf-8")) > PROJECT_DOMAIN_MAX_EXTERNAL_REF_BYTES
        or _CONTROL.search(external_ref)
    ):
        raise ValueError("P2P_PROJECT_DOMAIN_INVALID: external_ref is empty or unsafe")
    return external_ref


def normalize_domain_tags(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError("P2P_VERTICAL_DOMAIN_METADATA_INVALID: domain_tags must be a list")
    if len(value) > VERTICAL_DOMAIN_TAG_LIMIT:
        raise ValueError(
            f"P2P_VERTICAL_DOMAIN_METADATA_INVALID: at most {VERTICAL_DOMAIN_TAG_LIMIT} domain tags are allowed"
        )
    normalized = tuple(sorted({normalize_domain_key(item) for item in value}))
    if len(normalized) != len(value):
        raise ValueError(
            "P2P_VERTICAL_DOMAIN_METADATA_INVALID: domain_tags must be unique"
        )
    return normalized


@dataclass(frozen=True)
class ProjectDomainRef:
    key: str
    name: str
    source: str = "local"
    external_ref: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "key", normalize_domain_key(self.key))
        object.__setattr__(self, "name", normalize_domain_name(self.name))
        object.__setattr__(self, "source", normalize_domain_source(self.source))
        object.__setattr__(self, "external_ref", normalize_external_ref(self.external_ref))
        if self.source == "external" and self.external_ref is None:
            raise ValueError(
                "P2P_PROJECT_DOMAIN_INVALID: external domain source requires external_ref"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "name": self.name,
            "source": self.source,
            "external_ref": self.external_ref,
        }

    @classmethod
    def from_mapping(cls, value: object) -> "ProjectDomainRef":
        if not isinstance(value, Mapping):
            raise ValueError("P2P_PROJECT_DOMAIN_INVALID: domain descriptor must be a mapping")
        unknown = sorted(set(value) - {"key", "name", "source", "external_ref"})
        if unknown:
            raise ValueError(
                "P2P_PROJECT_DOMAIN_INVALID: unsupported domain fields: "
                + ", ".join(str(item) for item in unknown)
            )
        return cls(
            key=value.get("key"),  # type: ignore[arg-type]
            name=value.get("name"),  # type: ignore[arg-type]
            source=value.get("source", "local"),  # type: ignore[arg-type]
            external_ref=value.get("external_ref"),
        )


@dataclass(frozen=True)
class StructureSource:
    kind: str
    starter_id: str | None = None
    coordinate: str | None = None
    checksum: str | None = None

    def __post_init__(self) -> None:
        kind = str(self.kind).strip().lower()
        object.__setattr__(self, "kind", kind)
        if kind == "starter":
            starter = str(self.starter_id or "").strip().lower()
            if starter not in PROJECT_STARTERS:
                raise ValueError(
                    "P2P_STRUCTURE_SOURCE_INVALID: starter must be generic or empty"
                )
            if self.coordinate is not None or self.checksum is not None:
                raise ValueError(
                    "P2P_STRUCTURE_SOURCE_INVALID: starter forbids vertical release fields"
                )
            object.__setattr__(self, "starter_id", starter)
            return
        if kind == "vertical_release":
            coordinate = str(self.coordinate or "").strip()
            checksum = str(self.checksum or "").strip().lower()
            if not _VERTICAL_COORDINATE.fullmatch(coordinate):
                raise ValueError(
                    "P2P_STRUCTURE_SOURCE_INVALID: vertical release requires an exact coordinate"
                )
            if not _CHECKSUM.fullmatch(checksum):
                raise ValueError(
                    "P2P_STRUCTURE_SOURCE_INVALID: vertical release requires a SHA-256 checksum"
                )
            if self.starter_id is not None:
                raise ValueError(
                    "P2P_STRUCTURE_SOURCE_INVALID: vertical release forbids starter_id"
                )
            object.__setattr__(self, "coordinate", coordinate)
            object.__setattr__(self, "checksum", checksum.removeprefix("sha256:"))
            return
        raise ValueError(
            "P2P_STRUCTURE_SOURCE_INVALID: source kind must be starter or vertical_release"
        )

    @classmethod
    def starter(cls, starter_id: str) -> "StructureSource":
        return cls(kind="starter", starter_id=starter_id)

    @classmethod
    def vertical_release(cls, coordinate: str, checksum: str) -> "StructureSource":
        return cls(kind="vertical_release", coordinate=coordinate, checksum=checksum)

    def to_dict(self) -> dict[str, object]:
        if self.kind == "starter":
            return {"kind": self.kind, "starter_id": self.starter_id}
        return {
            "kind": self.kind,
            "coordinate": self.coordinate,
            "checksum": self.checksum,
        }

    @classmethod
    def from_mapping(cls, value: object) -> "StructureSource":
        if not isinstance(value, Mapping):
            raise ValueError("P2P_STRUCTURE_SOURCE_INVALID: source must be a mapping")
        unknown = sorted(set(value) - {"kind", "starter_id", "coordinate", "checksum"})
        if unknown:
            raise ValueError(
                "P2P_STRUCTURE_SOURCE_INVALID: unsupported source fields: "
                + ", ".join(str(item) for item in unknown)
            )
        return cls(
            kind=str(value.get("kind") or ""),
            starter_id=value.get("starter_id"),  # type: ignore[arg-type]
            coordinate=value.get("coordinate"),  # type: ignore[arg-type]
            checksum=value.get("checksum"),  # type: ignore[arg-type]
        )


@dataclass(frozen=True)
class ProjectDomainState:
    revision: int
    descriptor: ProjectDomainRef | None
    updated_at: str
    updated_by: str
    project_memory_revision: str
    contract: str = PROJECT_DOMAIN_CONTRACT

    def __post_init__(self) -> None:
        if self.revision < 1:
            raise ValueError("P2P_PROJECT_DOMAIN_INVALID: revision must be positive")
        if self.contract != PROJECT_DOMAIN_CONTRACT:
            raise ValueError("P2P_PROJECT_DOMAIN_UNSUPPORTED: domain contract is unsupported")

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": self.contract,
            "revision": self.revision,
            "descriptor": self.descriptor.to_dict() if self.descriptor else None,
            "updated_at": self.updated_at,
            "updated_by": self.updated_by,
            "project_memory_revision": self.project_memory_revision,
        }


@dataclass(frozen=True)
class ProjectDomainMutationPlan:
    operation: str
    previous: ProjectDomainState
    next: ProjectDomainState
    operation_key_sha256: str
    request_fingerprint_sha256: str
    preview_token: str
    source_preconditions: tuple[object, ...] = field(repr=False)
    candidate_bytes: Mapping[str, bytes] = field(repr=False)
    authority: object = field(repr=False)


@dataclass(frozen=True)
class ProjectDomainMutationResult:
    status: str
    operation: str
    previous: ProjectDomainState
    current: ProjectDomainState
    actor: str
    changed_paths: tuple[str, ...] = ()
    message: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": PROJECT_DOMAIN_CONTRACT,
            "operation": self.operation,
            "status": self.status,
            "previous": self.previous.to_dict(),
            "current": self.current.to_dict(),
            "actor": self.actor,
            "changed_paths": list(self.changed_paths),
            "message": self.message,
        }
