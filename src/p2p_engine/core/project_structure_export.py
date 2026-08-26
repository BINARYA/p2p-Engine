from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from p2p_engine.core.authority import AuthorityEvidence
from p2p_engine.core.mutation_preview import MutationPreview, MutationResult


PROJECT_STRUCTURE_EXPORT_PREVIEW_CONTRACT = "p2p-project-structure-export-preview/v1"
PROJECT_STRUCTURE_EXPORT_RESULT_CONTRACT = "p2p-project-structure-export-result/v1"
PROJECT_STRUCTURE_EXPORT_MARKER_CONTRACT = "p2p-project-structure-export-marker/v1"
PROJECT_STRUCTURE_EXPORT_OPERATION = "project_structure_export"
PROJECT_STRUCTURE_EXPORT_OPERATION_ID = "project.structure.export.apply"
PROJECT_STRUCTURE_EXPORT_CAPABILITY = "project.vertical.export"


@dataclass(frozen=True)
class ProjectStructureExportSource:
    structure_id: str
    revision: int
    checksum: str
    active_semantic_hash: str
    origin: Mapping[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "structure_id": self.structure_id,
            "revision": self.revision,
            "checksum": self.checksum,
            "active_semantic_hash": self.active_semantic_hash,
            "origin": dict(self.origin),
        }


@dataclass(frozen=True)
class ProjectStructureExportCounts:
    active: Mapping[str, int]
    excluded_retired: Mapping[str, int]
    excluded_disabled: Mapping[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "active": dict(self.active),
            "excluded_retired": dict(self.excluded_retired),
            "excluded_disabled": dict(self.excluded_disabled),
        }


@dataclass(frozen=True)
class ProjectStructureExportEligibility:
    eligible: bool
    source: ProjectStructureExportSource
    counts: ProjectStructureExportCounts
    blockers: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": PROJECT_STRUCTURE_EXPORT_PREVIEW_CONTRACT,
            "eligible": self.eligible,
            "source": self.source.to_dict(),
            "counts": self.counts.to_dict(),
            "blockers": list(self.blockers),
            "mutation_performed": False,
        }


@dataclass(frozen=True)
class ProjectStructureExportPreview:
    source: ProjectStructureExportSource
    counts: ProjectStructureExportCounts
    coordinate: str
    lineage: Mapping[str, object]
    domain_metadata: Mapping[str, object]
    draft_document_hash: str
    draft_document: Mapping[str, object]
    preview: MutationPreview
    blockers: tuple[str, ...] = ()

    @property
    def apply_allowed(self) -> bool:
        return self.preview.apply_allowed and not self.blockers

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": PROJECT_STRUCTURE_EXPORT_PREVIEW_CONTRACT,
            "source": self.source.to_dict(),
            "counts": self.counts.to_dict(),
            "coordinate": self.coordinate,
            "lineage": dict(self.lineage),
            "domain_metadata": dict(self.domain_metadata),
            "draft_document_hash": self.draft_document_hash,
            "draft_document": dict(self.draft_document),
            "preview": self.preview.to_dict(),
            "apply_allowed": self.apply_allowed,
            "blockers": list(self.blockers),
            "mutation_performed": False,
        }


@dataclass(frozen=True)
class ProjectStructureExportResult:
    status: str
    coordinate: str
    source: ProjectStructureExportSource
    lineage: Mapping[str, object]
    domain_metadata: Mapping[str, object]
    draft_id: str
    draft_revision: int
    draft_document_hash: str
    semantic_checksum: str
    artifact_checksum: str
    artifact_size: int
    artifact_entries: tuple[str, ...]
    marker_path: str
    operation_key_sha256: str
    mutation: MutationResult
    authority: AuthorityEvidence
    materialization_target: Path | None = None
    package_output: Path | None = None

    def to_dict(self, *, include_local_paths: bool = False) -> dict[str, object]:
        payload: dict[str, object] = {
            "contract": PROJECT_STRUCTURE_EXPORT_RESULT_CONTRACT,
            "status": self.status,
            "operation": PROJECT_STRUCTURE_EXPORT_OPERATION,
            "operation_id": PROJECT_STRUCTURE_EXPORT_OPERATION_ID,
            "coordinate": self.coordinate,
            "source": self.source.to_dict(),
            "lineage": dict(self.lineage),
            "domain_metadata": dict(self.domain_metadata),
            "draft": {
                "draft_id": self.draft_id,
                "revision": self.draft_revision,
                "document_hash": self.draft_document_hash,
            },
            "package": {
                "coordinate": self.coordinate,
                "semantic_checksum": self.semantic_checksum,
                "artifact_checksum": self.artifact_checksum,
                "size": self.artifact_size,
                "entries": list(self.artifact_entries),
            },
            "receipt": {
                "operation_key_sha256": self.operation_key_sha256,
                "marker_path": self.marker_path,
                "capability": PROJECT_STRUCTURE_EXPORT_CAPABILITY,
                "authority_context_sha256": self.authority.authority_context_sha256,
            },
            "authority": self.authority.to_dict(),
            "mutation": self.mutation.to_dict(),
            "remote_publication": False,
            "publisher_ownership_granted": False,
        }
        if include_local_paths:
            payload["local_paths"] = {
                "materialization_target": (
                    str(self.materialization_target)
                    if self.materialization_target is not None
                    else ""
                ),
                "package_output": (
                    str(self.package_output) if self.package_output is not None else ""
                ),
            }
        return payload
