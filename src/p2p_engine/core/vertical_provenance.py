from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Iterable, Mapping

from p2p_engine.core.vertical_semantic_identity import (
    VerticalSemanticIdentity,
    verify_vertical_semantic_identity,
)

PORTABLE_VERTICAL_PROVENANCE_CONTRACT = "p2p-vertical-portable-provenance/v1"

PROVENANCE_STATUS_CALCULATED = "calculated"
PROVENANCE_STATUS_VERIFIED_AGAINST_REFERENCE = "verified_against_reference"
PROVENANCE_STATUS_VERIFIABLE_WHEN_AVAILABLE = "verifiable_when_available"
PROVENANCE_STATUS_DECLARATIVE_UNVERIFIED = "declarative_unverified"
PROVENANCE_STATUS_UNAVAILABLE = "unavailable"

PORTABLE_PROVENANCE_STATUSES = frozenset(
    {
        PROVENANCE_STATUS_CALCULATED,
        PROVENANCE_STATUS_VERIFIED_AGAINST_REFERENCE,
        PROVENANCE_STATUS_VERIFIABLE_WHEN_AVAILABLE,
        PROVENANCE_STATUS_DECLARATIVE_UNVERIFIED,
        PROVENANCE_STATUS_UNAVAILABLE,
    }
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_LINEAGE_RELATIONS = frozenset({"forked_from", "previous_release"})


def _status(value: str) -> str:
    status = str(value or "").strip()
    if status not in PORTABLE_PROVENANCE_STATUSES:
        raise ValueError(
            "P2P_VERTICAL_PROVENANCE_INVALID: unsupported provenance status"
        )
    return status


@dataclass(frozen=True)
class PortableArtifactIdentity:
    algorithm: str
    digest: str

    def __post_init__(self) -> None:
        if self.algorithm != "sha256" or not _SHA256.fullmatch(self.digest):
            raise ValueError(
                "P2P_VERTICAL_PROVENANCE_INVALID: artifact identity must be a lowercase SHA-256 digest"
            )

    def to_dict(self) -> dict[str, str]:
        return {"algorithm": self.algorithm, "digest": self.digest}


@dataclass(frozen=True)
class PortableCalculatedIdentity:
    identity: PortableArtifactIdentity | VerticalSemanticIdentity | None
    status: str

    def __post_init__(self) -> None:
        status = _status(self.status)
        if status not in {PROVENANCE_STATUS_CALCULATED, PROVENANCE_STATUS_UNAVAILABLE}:
            raise ValueError(
                "P2P_VERTICAL_PROVENANCE_INVALID: subject identity status must be calculated or unavailable"
            )
        if status == PROVENANCE_STATUS_CALCULATED and self.identity is None:
            raise ValueError(
                "P2P_VERTICAL_PROVENANCE_INVALID: calculated identity requires a value"
            )
        if status == PROVENANCE_STATUS_UNAVAILABLE and self.identity is not None:
            raise ValueError(
                "P2P_VERTICAL_PROVENANCE_INVALID: unavailable identity cannot contain a value"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "identity": self.identity.to_dict() if self.identity is not None else None,
            "status": self.status,
        }


@dataclass(frozen=True)
class PortableProvenanceClaim:
    value: str
    status: str = PROVENANCE_STATUS_DECLARATIVE_UNVERIFIED

    def __post_init__(self) -> None:
        if _status(self.status) != PROVENANCE_STATUS_DECLARATIVE_UNVERIFIED:
            raise ValueError(
                "P2P_VERTICAL_PROVENANCE_INVALID: portable claims are declarative"
            )

    def to_dict(self) -> dict[str, str]:
        return {"value": self.value, "status": self.status}


@dataclass(frozen=True)
class PortableLineageRelation:
    relation: str
    coordinate: str
    status: str = PROVENANCE_STATUS_DECLARATIVE_UNVERIFIED

    def __post_init__(self) -> None:
        if self.relation not in _LINEAGE_RELATIONS:
            raise ValueError(
                "P2P_VERTICAL_PROVENANCE_INVALID: unsupported lineage relation"
            )
        if _status(self.status) != PROVENANCE_STATUS_DECLARATIVE_UNVERIFIED:
            raise ValueError(
                "P2P_VERTICAL_PROVENANCE_INVALID: portable lineage is declarative"
            )

    def to_dict(self) -> dict[str, str]:
        return {
            "relation": self.relation,
            "coordinate": self.coordinate,
            "status": self.status,
        }


@dataclass(frozen=True)
class PortableDependencyProvenance:
    coordinate: str
    relation_status: str
    target_semantic_identity: VerticalSemanticIdentity
    target_identity_status: str

    def __post_init__(self) -> None:
        if _status(self.relation_status) != PROVENANCE_STATUS_DECLARATIVE_UNVERIFIED:
            raise ValueError(
                "P2P_VERTICAL_PROVENANCE_INVALID: dependency relation is always declarative"
            )
        target_status = _status(self.target_identity_status)
        if target_status not in {
            PROVENANCE_STATUS_VERIFIABLE_WHEN_AVAILABLE,
            PROVENANCE_STATUS_VERIFIED_AGAINST_REFERENCE,
        }:
            raise ValueError(
                "P2P_VERTICAL_PROVENANCE_INVALID: invalid dependency target identity status"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "relation": {
                "coordinate": self.coordinate,
                "status": self.relation_status,
            },
            "target_semantic_identity": {
                "identity": self.target_semantic_identity.to_dict(),
                "status": self.target_identity_status,
            },
        }


@dataclass(frozen=True)
class PortableProvenanceSubject:
    coordinate: str
    schema_version: int
    package_version: int
    artifact: PortableCalculatedIdentity
    semantic: PortableCalculatedIdentity

    def to_dict(self) -> dict[str, object]:
        return {
            "coordinate": self.coordinate,
            "schema_version": self.schema_version,
            "package_version": self.package_version,
            "artifact": self.artifact.to_dict(),
            "semantic": self.semantic.to_dict(),
        }


@dataclass(frozen=True)
class PortableVerticalProvenance:
    subject: PortableProvenanceSubject
    publisher: PortableProvenanceClaim
    license: PortableProvenanceClaim
    construction_source: PortableProvenanceClaim
    lineage: tuple[PortableLineageRelation, ...] = ()
    dependencies: tuple[PortableDependencyProvenance, ...] = ()
    contract_version: str = PORTABLE_VERTICAL_PROVENANCE_CONTRACT

    def __post_init__(self) -> None:
        if self.contract_version != PORTABLE_VERTICAL_PROVENANCE_CONTRACT:
            raise ValueError(
                "P2P_VERTICAL_PROVENANCE_INVALID: unsupported portable provenance contract"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "contract_version": self.contract_version,
            "subject": self.subject.to_dict(),
            "claims": {
                "publisher": self.publisher.to_dict(),
                "license": self.license.to_dict(),
                "construction_source": self.construction_source.to_dict(),
            },
            "lineage": [item.to_dict() for item in self.lineage],
            "dependencies": [item.to_dict() for item in self.dependencies],
        }


def build_portable_vertical_provenance(
    *,
    coordinate: str,
    schema_version: int,
    package_version: int,
    artifact_checksum: str,
    semantic_identity: VerticalSemanticIdentity,
    publisher: str,
    license_id: str,
    construction_source: str,
    lineage: Mapping[str, str],
    dependencies: Iterable[object],
) -> PortableVerticalProvenance:
    artifact = (
        PortableCalculatedIdentity(
            identity=PortableArtifactIdentity("sha256", artifact_checksum),
            status=PROVENANCE_STATUS_CALCULATED,
        )
        if artifact_checksum
        else PortableCalculatedIdentity(
            identity=None,
            status=PROVENANCE_STATUS_UNAVAILABLE,
        )
    )
    lineage_relations = tuple(
        PortableLineageRelation(relation=relation, coordinate=str(lineage[relation]))
        for relation in ("forked_from", "previous_release")
        if lineage.get(relation)
    )
    dependency_relations = tuple(
        PortableDependencyProvenance(
            coordinate=str(getattr(item, "coordinate")),
            relation_status=PROVENANCE_STATUS_DECLARATIVE_UNVERIFIED,
            target_semantic_identity=getattr(item, "semantic_identity"),
            target_identity_status=PROVENANCE_STATUS_VERIFIABLE_WHEN_AVAILABLE,
        )
        for item in dependencies
    )
    return PortableVerticalProvenance(
        subject=PortableProvenanceSubject(
            coordinate=coordinate,
            schema_version=schema_version,
            package_version=package_version,
            artifact=artifact,
            semantic=PortableCalculatedIdentity(
                identity=semantic_identity,
                status=PROVENANCE_STATUS_CALCULATED,
            ),
        ),
        publisher=PortableProvenanceClaim(publisher),
        license=PortableProvenanceClaim(license_id),
        construction_source=PortableProvenanceClaim(construction_source),
        lineage=lineage_relations,
        dependencies=dependency_relations,
    )


def verify_dependency_target_identity(
    dependency: PortableDependencyProvenance,
    actual: VerticalSemanticIdentity,
) -> PortableDependencyProvenance:
    """Compare target content identity without upgrading the declared edge."""
    verify_vertical_semantic_identity(actual, dependency.target_semantic_identity)
    return replace(
        dependency,
        target_identity_status=PROVENANCE_STATUS_VERIFIED_AGAINST_REFERENCE,
    )
