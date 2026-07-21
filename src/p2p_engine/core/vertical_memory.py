from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
import re
from typing import Mapping


VERTICAL_MEMORY_MANIFEST_VERSION = 1
VERTICAL_MEMORY_PROJECT_VERSION = 1
VERTICAL_MEMORY_SECTION_VERSION = 1
VERTICAL_MEMORY_GENERATOR_CONTRACT = "vertical-project-memory-v1"
VERTICAL_MEMORY_SOURCE_POLICY = "vertical-memory-sources-v1"
VERTICAL_MEMORY_IDENTITY_POLICY = "vertical-memory-identity-v1"
VERTICAL_MEMORY_CURSOR_POLICY_VERSION = 1
VERTICAL_MEMORY_ROOT = ".p2p/project/vertical-memory"
_ID = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def vertical_memory_section_path(section_id: str) -> str:
    if not _ID.fullmatch(section_id):
        raise ValueError(f"Unsafe vertical-memory section ID: {section_id}")
    return f"{VERTICAL_MEMORY_ROOT}/sections/{section_id}.yml"


def validate_vertical_memory_owned_path(path: str) -> None:
    pure = PurePosixPath(path)
    if pure.is_absolute() or ".." in pure.parts:
        raise ValueError(f"Unsafe vertical-memory owned path: {path}")
    if not pure.as_posix().startswith(f"{VERTICAL_MEMORY_ROOT}/"):
        raise ValueError(f"Vertical-memory path escapes owned root: {path}")


@dataclass(frozen=True)
class VerticalMemoryEvidence:
    evidence_id: str
    source_path: str
    source_sha256: str
    fragment: str
    fragment_kind: str
    truncated: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.evidence_id,
            "source_path": self.source_path,
            "source_sha256": self.source_sha256,
            "fragment": self.fragment,
            "fragment_kind": self.fragment_kind,
            "truncated": self.truncated,
        }


@dataclass(frozen=True)
class VerticalMemoryContribution:
    contribution_id: str
    proposal_id: str
    title: str
    section_id: str
    authority: str
    activation: str
    effective_state: str
    head_event_id: str
    head_event_type: str
    rationale: str
    constraints: tuple[str, ...]
    applicability: str
    coverage_rationale: str
    source_path: str
    proposal_semantic_sha256: str
    decision_semantic_sha256: str
    lineage: Mapping[str, object] = field(default_factory=dict)
    evidence: tuple[VerticalMemoryEvidence, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.contribution_id,
            "proposal_id": self.proposal_id,
            "title": self.title,
            "section_id": self.section_id,
            "authority": self.authority,
            "activation": self.activation,
            "effective_state": self.effective_state,
            "head_event_id": self.head_event_id or None,
            "head_event_type": self.head_event_type or None,
            "rationale": self.rationale,
            "constraints": list(self.constraints),
            "applicability": self.applicability,
            "coverage_rationale": self.coverage_rationale,
            "source_path": self.source_path,
            "proposal_semantic_sha256": self.proposal_semantic_sha256 or None,
            "decision_semantic_sha256": self.decision_semantic_sha256 or None,
            "lineage": dict(self.lineage),
            "evidence": [item.to_dict() for item in self.evidence],
        }


@dataclass(frozen=True)
class VerticalMemorySection:
    section_id: str
    title: str
    purpose: str
    required: bool
    priority: int
    definition: Mapping[str, object]
    questions: tuple[Mapping[str, object], ...]
    active_contributions: tuple[VerticalMemoryContribution, ...]
    historical_contributions: tuple[VerticalMemoryContribution, ...]
    declared_questions: tuple[str, ...] = ()
    heuristic_suggestions: tuple[Mapping[str, object], ...] = ()
    conflicts: tuple[Mapping[str, object], ...] = ()
    diagnostics: tuple[Mapping[str, object], ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "vertical_memory_section": {
                "schema_version": VERTICAL_MEMORY_SECTION_VERSION,
                "section": {
                    "id": self.section_id,
                    "title": self.title,
                    "purpose": self.purpose,
                    "required": self.required,
                    "priority": self.priority,
                },
                "definition": dict(self.definition),
                "questions": [dict(item) for item in self.questions],
                "declared_questions": list(self.declared_questions),
                "heuristic_suggestions": [dict(item) for item in self.heuristic_suggestions],
                "active_contributions": [item.to_dict() for item in self.active_contributions],
                "historical_contributions": [item.to_dict() for item in self.historical_contributions],
                "conflicts": [dict(item) for item in self.conflicts],
                "diagnostics": [dict(item) for item in self.diagnostics],
            }
        }


@dataclass(frozen=True)
class VerticalProjectMemoryView:
    vertical_id: str
    vertical_version: str
    vertical_checksum: str
    sections: tuple[VerticalMemorySection, ...]
    unmapped_active_proposals: tuple[Mapping[str, object], ...]
    diagnostics: tuple[Mapping[str, object], ...]
    source_fingerprint_sha256: str
    profile: str = "default"
    modules: tuple[str, ...] = ()
    fallback_used: bool = False
    vertical_source: str = ""
    vertical_lock_checksum: str = ""
    definition_exists: bool = False
    definition_valid: bool = False
    source: str = "candidate"

    def to_dict(self) -> dict[str, object]:
        return {
            "vertical_id": self.vertical_id,
            "vertical_version": self.vertical_version,
            "vertical_checksum": self.vertical_checksum,
            "source_fingerprint_sha256": self.source_fingerprint_sha256,
            "source": self.source,
            "profile": self.profile,
            "modules": list(self.modules),
            "fallback_used": self.fallback_used,
            "vertical_source": self.vertical_source,
            "vertical_lock_checksum": self.vertical_lock_checksum,
            "definition_exists": self.definition_exists,
            "definition_valid": self.definition_valid,
            "sections": [item.to_dict()["vertical_memory_section"] for item in self.sections],
            "unmapped_active_proposals": [dict(item) for item in self.unmapped_active_proposals],
            "diagnostics": [dict(item) for item in self.diagnostics],
        }


@dataclass(frozen=True)
class VerticalMemoryCandidate:
    view: VerticalProjectMemoryView
    candidates: Mapping[str, bytes]
    source_preconditions: tuple[object, ...]
    owned_paths: tuple[str, ...]
    source_scopes: Mapping[str, str]


@dataclass(frozen=True)
class VerticalMemoryStatus:
    state: str
    reason: str
    manifest_path: Path
    vertical_id: str = ""
    vertical_version: str = ""
    source_fingerprint_sha256: str = ""
    current_source_fingerprint_sha256: str = ""
    changed_scopes: tuple[str, ...] = ()
    changed_paths: tuple[str, ...] = ()
    section_count: int = 0
    output_count: int = 0
    refresh_command: str = "p2p project refresh"

    @property
    def current(self) -> bool:
        return self.state == "current"

    def to_dict(self) -> dict[str, object]:
        return {
            "state": self.state,
            "reason": self.reason,
            "manifest_path": str(self.manifest_path),
            "vertical_id": self.vertical_id,
            "vertical_version": self.vertical_version,
            "source_fingerprint_sha256": self.source_fingerprint_sha256,
            "current_source_fingerprint_sha256": self.current_source_fingerprint_sha256,
            "changed_scopes": list(self.changed_scopes),
            "changed_paths": list(self.changed_paths),
            "section_count": self.section_count,
            "output_count": self.output_count,
            "refresh_command": self.refresh_command,
        }


@dataclass(frozen=True)
class VerticalMemoryImpact:
    scopes: tuple[str, ...]
    section_ids: tuple[str, ...]
    aggregate_changed: bool
    full_rebuild: bool
    reasons: tuple[str, ...]
    proposal_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class VerticalMemoryOperationResult:
    status: str
    mode: str
    changed_paths: tuple[str, ...]
    source_fingerprint_sha256: str
    reason: str = ""
    affected_sections: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "mode": self.mode,
            "changed_paths": list(self.changed_paths),
            "source_fingerprint_sha256": self.source_fingerprint_sha256,
            "reason": self.reason,
            "affected_sections": list(self.affected_sections),
        }


@dataclass(frozen=True)
class VerticalMemoryPage:
    section_id: str
    items: tuple[Mapping[str, object], ...]
    total: int
    returned: int
    truncated: bool
    next_cursor: str


@dataclass(frozen=True)
class VerticalMemoryAggregate:
    vertical_id: str
    vertical_version: str
    source: str
    source_fingerprint_sha256: str
    sections: tuple[Mapping[str, object], ...]
    unmapped_active_proposals: tuple[Mapping[str, object], ...]
    total: int
    returned: int
    truncated: bool
    next_cursor: str = ""
    diagnostics_count: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "vertical_id": self.vertical_id,
            "vertical_version": self.vertical_version,
            "source": self.source,
            "source_fingerprint_sha256": self.source_fingerprint_sha256,
            "sections": [dict(item) for item in self.sections],
            "unmapped_active_proposals": [
                dict(item) for item in self.unmapped_active_proposals
            ],
            "total": self.total,
            "returned": self.returned,
            "truncated": self.truncated,
            "next_cursor": self.next_cursor,
            "diagnostics_count": self.diagnostics_count,
        }


@dataclass(frozen=True)
class DerivedUpdateResult:
    state: str
    target: str
    changed_paths: tuple[str, ...] = ()
    reason: str = ""
    refresh_command: str = "p2p project refresh"
    affected_sections: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "state": self.state,
            "target": self.target,
            "changed_paths": list(self.changed_paths),
            "reason": self.reason,
            "refresh_command": self.refresh_command,
            "affected_sections": list(self.affected_sections),
        }


def vertical_memory_derived_updates(
    result: DerivedUpdateResult,
) -> dict[str, object]:
    """Adapt one derived refresh result to the additive public response shape."""
    return {"vertical_project_memory": result.to_dict()}


def validate_vertical_memory_view(view: VerticalProjectMemoryView) -> None:
    if not _ID.fullmatch(view.vertical_id):
        raise ValueError(f"Invalid vertical-memory vertical ID: {view.vertical_id}")
    if not _SHA256.fullmatch(view.source_fingerprint_sha256):
        raise ValueError("Invalid vertical-memory source fingerprint")
    section_ids = [item.section_id for item in view.sections]
    if len(section_ids) != len(set(section_ids)):
        raise ValueError("Duplicate vertical-memory section ID")
    for section in view.sections:
        vertical_memory_section_path(section.section_id)
        contribution_ids: set[str] = set()
        for contribution in (*section.active_contributions, *section.historical_contributions):
            if contribution.contribution_id in contribution_ids:
                raise ValueError("Duplicate vertical-memory contribution ID")
            contribution_ids.add(contribution.contribution_id)
            validate_vertical_memory_owned_source(contribution.source_path)


def validate_vertical_memory_owned_source(path: str) -> None:
    pure = PurePosixPath(path)
    if pure.is_absolute() or ".." in pure.parts or not pure.parts:
        raise ValueError(f"Unsafe vertical-memory source path: {path}")
