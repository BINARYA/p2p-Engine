from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from p2p_engine.foundation.files import read_yaml_mapping
from p2p_engine.services.workspace_reads import WorkspaceReadContext


ProjectSnapshotPayload = dict[str, object]


class ProjectSnapshotService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        workspace_status: Callable[..., Any],
        runtime_status: Callable[[], Any],
        transaction_recovery_status: Callable[[], Any],
        active_vertical: Callable[[], Any],
        vertical_lock_status: Callable[[], Any],
        vertical_sections: Callable[[], list[Any]],
        project_progress: Callable[[list[Any], WorkspaceReadContext | None], Any],
        publication_status: Callable[..., Any],
        project_domain: Callable[[], Any],
        project_structure: Callable[[], Any],
        memory_classification: Callable[[], Any],
        project_readiness: Callable[[WorkspaceReadContext | None], Any] | None = None,
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.workspace_status = workspace_status
        self.runtime_status = runtime_status
        self.transaction_recovery_status = transaction_recovery_status
        self.active_vertical = active_vertical
        self.vertical_lock_status = vertical_lock_status
        self.vertical_sections = vertical_sections
        self.project_progress = project_progress
        self.project_readiness = project_readiness
        self.publication_status = publication_status
        self.project_domain = project_domain
        self.project_structure = project_structure
        self.memory_classification = memory_classification

    def snapshot(
        self,
        *,
        limit: int = 20,
        read_context: WorkspaceReadContext | None = None,
    ) -> ProjectSnapshotPayload:
        if limit < 1:
            raise ValueError(
                "P2P_PROJECT_SNAPSHOT_INVALID_LIMIT: limit must be at least 1"
            )
        status = self.workspace_status(read_context=read_context)
        proposals = sorted(
            list(getattr(status, "proposals", ())),
            key=lambda item: getattr(item, "proposal_id", ""),
        )
        progress = self.project_progress(proposals, read_context)
        readiness = (
            self.project_readiness(read_context)
            if self.project_readiness is not None
            else progress
        )
        sections = sorted(
            self.vertical_sections(),
            key=lambda item: (
                int(getattr(item, "priority", 100)),
                str(getattr(item, "section_id", "")),
            ),
        )
        return {
            "contract_version": "p2p-project-snapshot/v1",
            "project": self._project_identity(status, read_context=read_context),
            "runtime": _payload(self.runtime_status()),
            "workspace_schema": _payload(getattr(status, "workspace_schema", None)),
            "transactions": _payload(self.transaction_recovery_status()),
            "structure": self._structure_summary(),
            "memory_classification": _payload(self.memory_classification()),
            "vertical": self._vertical_summary(),
            "sections": self._section_collection(sections, progress=progress, limit=limit),
            "readiness": self._readiness_summary(readiness, limit=limit),
            "proposals": self._proposal_collection(proposals, limit=limit),
            "decisions": self._decision_collection(proposals, limit=limit),
            "outputs": self._output_summary(read_context=read_context),
            "derived_state": _payload(getattr(status, "derived_freshness", None)),
            "limits": {
                "default_limit": limit,
                "proposal_summaries": limit,
                "decision_summaries": limit,
                "section_summaries": limit,
            },
        }

    def _structure_summary(self) -> dict[str, object]:
        structure = self.project_structure()
        active_sections = [
            item
            for item in getattr(structure, "sections", ())
            if getattr(item, "lifecycle", "active") == "active"
        ]
        active_criteria = [
            item
            for item in getattr(structure, "criteria", ())
            if getattr(item, "lifecycle", "active") == "active"
            and bool(getattr(item, "enabled", True))
        ]
        return {
            "contract": str(getattr(structure, "contract", "")),
            "structure_id": str(getattr(structure, "structure_id", "")),
            "revision": int(getattr(structure, "revision", 0)),
            "checksum": str(getattr(structure, "checksum", "")),
            "origin": _payload(getattr(structure, "origin", None)),
            "active_section_count": len(active_sections),
            "active_criterion_count": len(active_criteria),
        }

    def _project_identity(
        self,
        status: Any,
        *,
        read_context: WorkspaceReadContext | None,
    ) -> dict[str, object]:
        project = self._project_payload(read_context=read_context)
        return {
            "id": str(project.get("id") or ""),
            "name": str(
                project.get("name") or getattr(status, "project_name", "Unknown")
            ),
            "version": str(project.get("version") or ""),
            "status": str(project.get("status") or ""),
            "domain": _payload(getattr(self.project_domain(), "descriptor", None)),
            "root": self.root,
        }

    def _project_payload(
        self,
        *,
        read_context: WorkspaceReadContext | None,
    ) -> Mapping[str, object]:
        path = self.p2p_dir / "project.yml"
        try:
            data = (
                read_context.documents.yaml(path)
                if read_context is not None
                else read_yaml_mapping(path, default={})
            )
        except (FileNotFoundError, ValueError):
            data = {}
        project = data.get("project") if isinstance(data, Mapping) else None
        return project if isinstance(project, Mapping) else {}

    def _vertical_summary(self) -> dict[str, object]:
        active = self.active_vertical()
        lock = self.vertical_lock_status()
        locked = getattr(lock, "locked", None)
        return {
            "active": _payload(active),
            "lock": {
                "status": str(getattr(lock, "status", "unknown")),
                "message": str(getattr(lock, "message", "")),
                "suggested_command": str(getattr(lock, "suggested_command", "")),
                "locked": self._locked_vertical_summary(locked),
            },
        }

    def _locked_vertical_summary(self, locked: Any) -> dict[str, object] | None:
        if locked is None:
            return None
        source = getattr(locked, "source", None)
        return {
            "vertical_id": str(getattr(locked, "vertical_id", "")),
            "name": str(getattr(locked, "name", "")),
            "version": str(getattr(locked, "version", "")),
            "coordinate": str(getattr(locked, "coordinate", "")),
            "checksum": str(getattr(locked, "checksum", "")),
            "artifact_checksum": str(getattr(locked, "artifact_checksum", "")),
            "source": _payload(source),
        }

    def _section_collection(
        self,
        sections: list[Any],
        *,
        progress: Any,
        limit: int,
    ) -> dict[str, object]:
        progress_by_section = {
            getattr(item, "section_id", ""): item
            for item in getattr(progress, "sections", ())
        }
        return _bounded_collection(
            sections,
            limit=limit,
            item_mapper=lambda section: self._section_summary(
                section,
                progress_by_section.get(getattr(section, "section_id", "")),
            ),
        )

    def _section_summary(self, section: Any, progress: Any | None) -> dict[str, object]:
        fields = list(getattr(section, "fields", ()) or ())
        return {
            "section_id": str(getattr(section, "section_id", "")),
            "title": str(getattr(section, "title", "")),
            "required": bool(getattr(section, "required", False)),
            "priority": int(getattr(section, "priority", 100)),
            "field_count": len(fields),
            "required_field_count": sum(
                1
                for field in fields
                if bool(getattr(field, "required", False))
            ),
            "progress": _payload(progress) if progress is not None else None,
        }

    def _readiness_summary(self, readiness: Any, *, limit: int) -> dict[str, object]:
        if str(getattr(readiness, "contract_version", "")) == "p2p-project-readiness/v2":
            sections = list(getattr(readiness, "sections", ()) or ())
            diagnostics = list(getattr(readiness, "diagnostics", ()) or ())
            return {
                "contract_version": str(getattr(readiness, "contract_version", "")),
                "status": str(getattr(readiness, "status", "")),
                "snapshot": _payload(getattr(readiness, "snapshot", None)),
                "definition": _payload(getattr(readiness, "definition", None)),
                "evidence": _payload(getattr(readiness, "evidence", None)),
                "sections": _bounded_collection(
                    sections,
                    limit=limit,
                    item_mapper=lambda item: item,
                ),
                "gap_counts": dict(getattr(readiness, "counts", {}) or {}),
                "actions": list(getattr(readiness, "actions", ()) or ()),
                "diagnostics": _bounded_collection(
                    diagnostics,
                    limit=limit,
                    item_mapper=lambda item: item,
                ),
            }
        progress = readiness
        return {
            "vertical_id": str(getattr(progress, "vertical_id", "")),
            "definition": _payload(getattr(progress, "definition", None)),
            "evidence": _payload(getattr(progress, "evidence", None)),
            "question_counts": dict(getattr(progress, "question_counts", {}) or {}),
            "blocker_count": len(getattr(progress, "blockers", ()) or ()),
            "assumption_count": len(getattr(progress, "assumptions", ()) or ()),
            "open_question_count": len(getattr(progress, "open_questions", ()) or ()),
            "warnings": list(getattr(progress, "warnings", ()) or ()),
        }

    def _proposal_collection(self, proposals: list[Any], *, limit: int) -> dict[str, object]:
        status_counts = Counter(
            str(getattr(item, "status", "unknown")) for item in proposals
        )
        effective_counts = Counter(
            str(getattr(item, "effective_state", "unknown")) for item in proposals
        )
        collection = _bounded_collection(
            proposals,
            limit=limit,
            item_mapper=self._proposal_summary,
        )
        collection["counts"] = {
            "by_status": dict(sorted(status_counts.items())),
            "by_effective_state": dict(sorted(effective_counts.items())),
        }
        return collection

    def _proposal_summary(self, proposal: Any) -> dict[str, object]:
        return {
            "proposal_id": str(getattr(proposal, "proposal_id", "")),
            "slug": str(getattr(proposal, "slug", "")),
            "title": str(getattr(proposal, "title", "")),
            "status": str(getattr(proposal, "status", "")),
            "effective_state": str(getattr(proposal, "effective_state", "")),
            "head_event_type": getattr(proposal, "head_event_type", None),
            "head_event_id": getattr(proposal, "head_event_id", None),
            "event_count": int(getattr(proposal, "event_count", 0)),
            "active": bool(getattr(proposal, "active", False)),
            "ever_active": bool(getattr(proposal, "ever_active", False)),
            "authority_resolution": str(getattr(proposal, "authority_resolution", "")),
            "proposal_binding_status": str(getattr(proposal, "proposal_binding_status", "")),
        }

    def _decision_collection(self, proposals: list[Any], *, limit: int) -> dict[str, object]:
        decided = [
            proposal
            for proposal in proposals
            if int(getattr(proposal, "event_count", 0))
            or str(getattr(proposal, "effective_state", ""))
            not in {"", "unknown", "draft", "undecided"}
        ]
        counts = Counter(
            str(getattr(item, "effective_state", "unknown")) for item in proposals
        )
        collection = _bounded_collection(
            decided,
            limit=limit,
            item_mapper=lambda proposal: {
                "proposal_id": str(getattr(proposal, "proposal_id", "")),
                "title": str(getattr(proposal, "title", "")),
                "effective_state": str(getattr(proposal, "effective_state", "")),
                "head_event_type": getattr(proposal, "head_event_type", None),
                "head_event_id": getattr(proposal, "head_event_id", None),
                "event_count": int(getattr(proposal, "event_count", 0)),
                "active": bool(getattr(proposal, "active", False)),
            },
        )
        collection["counts"] = {"by_effective_state": dict(sorted(counts.items()))}
        return collection

    def _output_summary(
        self,
        *,
        read_context: WorkspaceReadContext | None,
    ) -> dict[str, object]:
        publication = self.publication_status(read_context=read_context)
        return {
            "publication": _payload(publication),
            "summary": {
                "validation_status": str(getattr(publication, "validation_status", "unknown")),
                "render_status": str(getattr(publication, "render_status", "unknown")),
                "review_status": str(getattr(publication, "review_status", "unknown")),
                "approved_for_publication": bool(
                    getattr(publication, "approved_for_publication", False)
                ),
            },
        }


def _bounded_collection(
    items: list[Any],
    *,
    limit: int,
    item_mapper: Callable[[Any], object],
) -> dict[str, object]:
    returned = items[:limit]
    return {
        "total": len(items),
        "returned": len(returned),
        "truncated": len(items) > limit,
        "items": [_payload(item_mapper(item)) for item in returned],
    }


def _payload(value: Any) -> Any:
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _payload(value.to_dict())
    if is_dataclass(value):
        return _payload(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, Mapping):
        return {str(key): _payload(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_payload(item) for item in value]
    return value
