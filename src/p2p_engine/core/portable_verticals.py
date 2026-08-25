from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re

from p2p_engine.core.mutation_preview import MutationPreview, MutationResult
from p2p_engine.core.project_verticals import VerticalPack, VerticalValidationIssue
from p2p_engine.core.vertical_transition_impact import (
    VERTICAL_TRANSITION_IMPACT_CONTRACT,
    VerticalTransitionImpact,
)


PORTABLE_VERTICAL_SCHEMA_VERSION = 3
PORTABLE_VERTICAL_PACKAGE_VERSION = 1
PORTABLE_VERTICAL_MAX_ENTRIES = 256
PORTABLE_VERTICAL_MAX_FILE_BYTES = 1_048_576
PORTABLE_VERTICAL_MAX_TOTAL_BYTES = 8_388_608
PORTABLE_VERTICAL_MAX_COMPRESSION_RATIO = 200

_SEMVER_PATTERN = (
    r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)"
    r"(?:-(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*)?"
    r"(?:\+[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*)?"
)
_COORDINATE_RE = re.compile(
    r"^(?P<publisher>[a-z0-9](?:[a-z0-9._-]{0,62}[a-z0-9])?)/"
    r"(?P<vertical>[a-z0-9](?:[a-z0-9_-]{0,62}[a-z0-9])?)@"
    rf"(?P<version>{_SEMVER_PATTERN})$"
)
_SEMVER_RE = re.compile(rf"^{_SEMVER_PATTERN}$")


@dataclass(frozen=True)
class VerticalCoordinate:
    publisher: str
    vertical_id: str
    version: str

    @classmethod
    def parse(cls, value: str) -> "VerticalCoordinate":
        text = str(value).strip()
        match = _COORDINATE_RE.fullmatch(text)
        if match is None:
            raise ValueError(
                "P2P_VERTICAL_INVALID_COORDINATE: expected publisher/vertical-id@MAJOR.MINOR.PATCH"
            )
        return cls(
            publisher=match.group("publisher"),
            vertical_id=match.group("vertical"),
            version=match.group("version"),
        )

    def __str__(self) -> str:
        return f"{self.publisher}/{self.vertical_id}@{self.version}"


def is_semantic_version(value: str) -> bool:
    return _SEMVER_RE.fullmatch(str(value).strip()) is not None


@dataclass(frozen=True)
class PortableVerticalInspection:
    target: str
    pack: VerticalPack
    declared_payload: dict[str, object]
    effective_payload: dict[str, object]
    artifact_checksum: str = ""
    semantic_checksum: str = ""
    entries: tuple[str, ...] = ()
    issues: tuple[VerticalValidationIssue, ...] = ()

    @property
    def valid(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)


@dataclass(frozen=True)
class PortableVerticalPackageResult:
    path: Path
    coordinate: str
    artifact_checksum: str
    semantic_checksum: str
    size: int
    entries: tuple[str, ...]


@dataclass(frozen=True)
class VerticalLifecyclePreview:
    operation: str
    coordinate: str
    preview: MutationPreview | None
    impact: VerticalTransitionImpact
    blockers: tuple[str, ...] = ()
    candidate_files: dict[str, bytes] = field(default_factory=dict, repr=False)
    decision_summary: tuple[dict[str, object], ...] = field(default_factory=tuple, repr=False)

    @property
    def apply_allowed(self) -> bool:
        return self.preview is not None and not self.blockers

    def to_dict(self) -> dict[str, object]:
        public_preview = None
        if self.preview is not None:
            public_preview = {
                "operation_id": self.preview.operation_id,
                "actor": self.preview.actor,
                "authority": self.preview.authority,
                "confirmation_required": self.preview.confirmation_required,
                "policy_version": self.preview.policy_version,
                "apply_allowed": self.preview.apply_allowed,
                "preview_token": self.preview.preview_token,
            }
        return {
            "operation": self.operation,
            "coordinate": self.coordinate,
            "apply_allowed": self.apply_allowed,
            "impact": self.impact.to_dict(),
            "blockers": list(self.blockers),
            "preview": public_preview,
        }


@dataclass(frozen=True)
class VerticalLifecycleResult:
    operation: str
    coordinate: str
    mutation: MutationResult
    analysis_fingerprint_sha256: str
    plan_fingerprint_sha256: str | None = None
    postconditions: dict[str, str | None] = field(default_factory=dict)
    impact_contract: str = VERTICAL_TRANSITION_IMPACT_CONTRACT

    def to_dict(self) -> dict[str, object]:
        return {
            "impact_contract": self.impact_contract,
            "operation": self.operation,
            "coordinate": self.coordinate,
            "analysis_fingerprint_sha256": self.analysis_fingerprint_sha256,
            "plan_fingerprint_sha256": self.plan_fingerprint_sha256,
            "postconditions": dict(self.postconditions),
            "mutation": {
                "status": self.mutation.status,
                "operation_id": self.mutation.operation_id,
                "actor": self.mutation.actor,
                "recovery_required": self.mutation.recovery_required,
            },
        }
