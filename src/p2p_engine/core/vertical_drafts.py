from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


VERTICAL_DRAFT_DOCUMENT_VERSION = "p2p-vertical-draft/v1"
VERTICAL_DRAFT_STATE_VERSION = "p2p-vertical-draft-state/v1"
VERTICAL_DRAFT_EVIDENCE_VERSION = "p2p-vertical-draft-evidence/v1"
VERTICAL_DRAFT_MAX_DOCUMENT_BYTES = 1_048_576
VERTICAL_DRAFT_MAX_SECTIONS = 128
VERTICAL_DRAFT_MAX_FIELDS = 1_024
VERTICAL_DRAFT_MAX_TEXT_BYTES = 32_768


@dataclass(frozen=True)
class VerticalDraftOrigin:
    kind: str
    coordinate: str = ""
    semantic_checksum: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "kind": self.kind,
            "coordinate": self.coordinate,
            "semantic_checksum": self.semantic_checksum,
        }


@dataclass(frozen=True)
class VerticalDraftDiagnostic:
    code: str
    field: str
    message: str
    severity: str = "error"

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "field": self.field,
            "message": self.message,
            "severity": self.severity,
        }


@dataclass(frozen=True)
class VerticalDraftAssessment:
    revision: int
    document_hash: str
    readiness: int
    structurally_valid: bool
    publishable: bool
    diagnostics: tuple[VerticalDraftDiagnostic, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "revision": self.revision,
            "document_hash": self.document_hash,
            "readiness": self.readiness,
            "structurally_valid": self.structurally_valid,
            "publishable": self.publishable,
            "diagnostics": [item.to_dict() for item in self.diagnostics],
        }


@dataclass(frozen=True)
class VerticalDraftEvidence:
    revision: int
    document_hash: str
    materialization: dict[str, object] | None = None
    validation: dict[str, object] | None = None
    package: dict[str, object] | None = None
    local_adds: tuple[dict[str, object], ...] = ()
    publications: tuple[dict[str, object], ...] = ()
    last_publication_failure: dict[str, object] | None = None

    @classmethod
    def empty(cls, revision: int, document_hash: str) -> "VerticalDraftEvidence":
        return cls(revision=revision, document_hash=document_hash)

    def to_dict(self) -> dict[str, object]:
        return {
            "contract_version": VERTICAL_DRAFT_EVIDENCE_VERSION,
            "revision": self.revision,
            "document_hash": self.document_hash,
            "materialization": self.materialization,
            "validation": self.validation,
            "package": self.package,
            "local_adds": list(self.local_adds),
            "publications": list(self.publications),
            "last_publication_failure": self.last_publication_failure,
        }


@dataclass(frozen=True)
class VerticalDraftState:
    draft_id: str
    revision: int
    document_hash: str
    status: str
    origin: VerticalDraftOrigin
    document: dict[str, object]
    path: Path

    def to_dict(self) -> dict[str, object]:
        return {
            "contract_version": VERTICAL_DRAFT_STATE_VERSION,
            "draft_id": self.draft_id,
            "revision": self.revision,
            "document_hash": self.document_hash,
            "status": self.status,
            "origin": self.origin.to_dict(),
            "document": self.document,
            "path": str(self.path),
        }


@dataclass(frozen=True)
class VerticalDraftView:
    state: VerticalDraftState
    evidence: VerticalDraftEvidence
    assessment: VerticalDraftAssessment

    def to_dict(self) -> dict[str, object]:
        return {
            "draft": self.state.to_dict(),
            "evidence": self.evidence.to_dict(),
            "assessment": self.assessment.to_dict(),
        }


@dataclass(frozen=True)
class VerticalDraftOperationResult:
    operation: str
    draft: VerticalDraftView
    changed_paths: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, object]:
        return {
            "operation": self.operation,
            **self.draft.to_dict(),
            "changed_paths": list(self.changed_paths),
        }
