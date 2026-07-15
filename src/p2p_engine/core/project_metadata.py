from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


PROJECT_METADATA_POLICY_VERSION = 1
PROJECT_METADATA_ALLOWED_FIELDS = ("status", "workflow_phase", "current_objective")


@dataclass(frozen=True)
class CanonicalArtifactCandidate:
    path: str
    owner: str
    payload: Mapping[str, object]
    provenance: Mapping[str, object]


@dataclass(frozen=True)
class ProjectMetadataPatch:
    actor: str
    values: Mapping[str, str]
    policy_version: int = PROJECT_METADATA_POLICY_VERSION


@dataclass(frozen=True)
class ProjectMetadataView:
    path: str
    values: Mapping[str, str]
    preserved_hashes: Mapping[str, str]
