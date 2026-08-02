from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re

from p2p_engine.core.mutation_preview import MutationPreview, MutationResult
from p2p_engine.core.project_verticals import VerticalPack, VerticalValidationIssue


PORTABLE_VERTICAL_SCHEMA_VERSION = 2
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
    impact: dict[str, object]
    blockers: tuple[str, ...] = ()
    candidate_files: dict[str, bytes] = field(default_factory=dict, repr=False)

    @property
    def apply_allowed(self) -> bool:
        return self.preview is not None and not self.blockers

    def to_dict(self) -> dict[str, object]:
        return {
            "operation": self.operation,
            "coordinate": self.coordinate,
            "apply_allowed": self.apply_allowed,
            "impact": self.impact,
            "blockers": list(self.blockers),
            "preview": self.preview.to_dict() if self.preview else None,
        }


@dataclass(frozen=True)
class VerticalLifecycleResult:
    operation: str
    coordinate: str
    mutation: MutationResult

    def to_dict(self) -> dict[str, object]:
        return {
            "operation": self.operation,
            "coordinate": self.coordinate,
            "mutation": self.mutation.to_dict(),
        }
