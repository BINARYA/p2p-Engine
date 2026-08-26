from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
import hashlib
import inspect
from pathlib import Path
import re

from p2p_engine.core.mutation_preview import semantic_sha256
from p2p_engine.core.project_publication import (
    PUBLICATION_CONTRACT_VERSION,
    PUBLICATION_EVIDENCE_GENERATOR,
    PublicationContributionSummary,
    PublicationEvidenceEntry,
    contribution_share_summary,
)
from p2p_engine.core.project_memory import PROJECT_MEMORY_OBJECT_LIMIT
from p2p_engine.core.proposal_decision_events import ProposalDecisionLifecycleView
from p2p_engine.core.vertical_memory import VerticalProjectMemoryView
from p2p_engine.foundation.yaml_loaders import UNIQUE_LOADER_CONTRACT, load_yaml_mapping
from p2p_engine.services.workspace_reads import WorkspaceReadContext
from p2p_engine.services.project_publication_contracts import (
    validate_publication_evidence_index,
)


_PROPOSAL_ID = re.compile(r"^(PROP-\d+)(?:-|$)")
_TEXT_SUFFIXES = {".md", ".txt"}
_YAML_SUFFIXES = {".yml", ".yaml"}
_PROCESS_ONLY_NAMES = {
    "artifact-state.yml",
    "decision-events.yml",
    "decision.md",
    "readiness.yml",
    "tasks.yml",
    "execution-plan.md",
    "implementation-plan.md",
    "memory-scope.yml",
    "memory-scope-events.yml",
}
_UNCERTAINTY_NAMES = {
    "assumptions.md",
    "open-questions.md",
    "risks.md",
    "questions.yml",
}
_INSUFFICIENT_NAMES = {"open-questions.md", "questions.yml"}
_PROJECT_EVIDENCE_NAMES = {
    "conflicts.yml",
    "definition.yml",
    "operational-brief.md",
    "questions.yml",
    "vertical.lock.yml",
    "vertical.yml",
}
_PROJECT_DERIVED_NAMES = {
    "assessment.yml",
    "brief-context.md",
    "brief.prompt.md",
    "decisions-map.yml",
    "maturity-assessment.yml",
    "next-actions-log.yml",
    "next-actions.yml",
    "overview.md",
    "problem.md",
    "project-swot.md",
    "projection-manifest.yml",
    "scope.md",
}


@dataclass(frozen=True)
class PublicationEvidenceCapture:
    source_fingerprint_sha256: str
    source_inputs: tuple[dict[str, str], ...]
    vertical: dict[str, object]
    memory_classification: dict[str, object]
    entries: tuple[PublicationEvidenceEntry, ...]
    contributions: PublicationContributionSummary
    diagnostics: tuple[dict[str, str], ...]
    read_operations: dict[str, object]


class ProjectPublicationEvidenceService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        accepted_proposals: Callable[[], list[dict[str, object]]],
        proposal_decision_lifecycles: Callable[..., dict[str, ProposalDecisionLifecycleView]] | None = None,
        vertical_memory: Callable[..., VerticalProjectMemoryView] | None = None,
        memory_classification: Callable[..., object] | None = None,
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.accepted_proposals = accepted_proposals
        self.proposal_decision_lifecycles = proposal_decision_lifecycles
        self.vertical_memory = vertical_memory
        self.memory_classification = memory_classification

    def build(
        self,
        *,
        source_fingerprint_sha256: str,
        source_export_path: Path,
        source_export_sha256: str,
    ) -> dict[str, object]:
        capture = self.capture()
        return self.build_from_capture(
            capture,
            source_fingerprint_sha256=source_fingerprint_sha256,
            source_export_path=source_export_path,
            source_export_sha256=source_export_sha256,
        )

    def capture(
        self,
        *,
        read_context: WorkspaceReadContext | None = None,
    ) -> PublicationEvidenceCapture:
        read_context = read_context or WorkspaceReadContext(self.root)
        lifecycle = (
            _invoke_provider(self.proposal_decision_lifecycles, read_context)
            if self.proposal_decision_lifecycles
            else {}
        )
        accepted_records = [] if lifecycle else self.accepted_proposals()
        accepted_ids = {
            str(item.get("proposal_id") or item.get("id") or "").strip()
            for item in accepted_records
        }
        accepted_ids.discard("")
        vertical_view = self._vertical_view(read_context)
        sections_by_proposal = _sections_by_proposal(vertical_view)
        unmapped = _unmapped_proposal_ids(vertical_view)
        classification_payload: dict[str, object] = {}
        scope_kind_by_proposal: dict[str, str] = {}
        if self.memory_classification is not None:
            classification = _invoke_provider(self.memory_classification, read_context)
            if hasattr(classification, "to_dict"):
                classification_payload = classification.to_dict(
                    limit=PROJECT_MEMORY_OBJECT_LIMIT
                )
                sections_by_proposal, unmapped, scope_kind_by_proposal = (
                    _classification_proposal_maps(classification_payload)
                )

        entries: list[PublicationEvidenceEntry] = []
        sources: list[dict[str, str]] = []
        contribution_authors: list[str] = []
        contribution_evidence_ids: list[str] = []

        for path in self._selected_paths(read_context):
            relative = path.relative_to(self.root).as_posix()
            content = read_context.documents.bytes(path)
            physical_sha256 = hashlib.sha256(content).hexdigest()
            payload = _complete_payload(path, content)
            proposal_id = _proposal_id_for_path(path, self.p2p_dir)
            authority_class = _authority_class(proposal_id, accepted_ids, lifecycle)
            vertical_sections = tuple(sorted(sections_by_proposal.get(proposal_id, ())))
            kind, editorial_class = _classify_path(
                path,
                proposal_id=proposal_id,
                authority_class=authority_class,
                vertical_sections=vertical_sections,
                explicitly_unmapped=proposal_id in unmapped,
            )
            source_selector = "file:complete"
            semantic_payload = {
                "kind": kind,
                "source_path": relative,
                "source_selector": source_selector,
                "payload": payload,
            }
            semantic_hash = semantic_sha256(semantic_payload)
            evidence_id = f"EVD-{semantic_hash[:20].upper()}"
            entry = PublicationEvidenceEntry(
                evidence_id=evidence_id,
                kind=kind,
                authority_class=authority_class,
                editorial_class=editorial_class,
                vertical_sections=vertical_sections,
                source_path=relative,
                source_selector=source_selector,
                semantic_sha256=semantic_hash,
                content_mode="inline_complete",
                memory_scope_kind=scope_kind_by_proposal.get(
                    proposal_id,
                    "inherited" if proposal_id else "project_global",
                ),
                payload=payload,
            )
            entries.append(entry)
            sources.append({"path": relative, "sha256": physical_sha256})
            if path.name == "contributions.yml" and authority_class == "active":
                contribution_authors.extend(_contribution_authors(payload))
                contribution_evidence_ids.append(evidence_id)

        entries = _mark_duplicate_evidence(entries)
        consistency = read_context.finalize()
        if not consistency.current:
            raise ValueError(
                "Publication evidence sources changed during generation; retry prepare. "
                f"paths={','.join(consistency.changed_paths) or 'none'}; "
                f"directories={','.join(consistency.changed_directories) or 'none'}"
            )
        entries.sort(key=lambda item: (item.source_path, item.source_selector, item.evidence_id))
        sources.sort(key=lambda item: item["path"])
        contribution_summary = contribution_share_summary(
            contribution_authors,
            source_evidence_ids=contribution_evidence_ids,
        )
        vertical_payload = _vertical_payload(vertical_view)
        return PublicationEvidenceCapture(
            source_fingerprint_sha256=_source_fingerprint(sources),
            source_inputs=tuple(sources),
            vertical=vertical_payload,
            memory_classification=classification_payload,
            entries=tuple(entries),
            contributions=contribution_summary,
            diagnostics=tuple(_diagnostics(vertical_view, entries)),
            read_operations=read_context.counters.to_dict(),
        )

    def build_from_capture(
        self,
        capture: PublicationEvidenceCapture,
        *,
        source_fingerprint_sha256: str | None = None,
        source_export_path: Path,
        source_export_sha256: str,
    ) -> dict[str, object]:
        fingerprint = source_fingerprint_sha256 or capture.source_fingerprint_sha256
        body: dict[str, object] = {
            "schema_version": PUBLICATION_CONTRACT_VERSION,
            "generator": PUBLICATION_EVIDENCE_GENERATOR,
            "source_fingerprint_sha256": fingerprint,
            "vertical": capture.vertical,
            "memory_classification": capture.memory_classification,
            "source_export": {
                "path": source_export_path.relative_to(self.root).as_posix(),
                "sha256": source_export_sha256,
            },
            "source_catalog": {
                "policy": "publication-evidence-sources-v2",
                "source_count": len(capture.source_inputs),
                "included_classes": [
                    "project_definition",
                    "vertical_interpretation",
                    "active_mapped_proposal_artifacts",
                    "active_cross_cutting_proposal_artifacts",
                    "historical_proposal_context",
                    "project_uncertainties",
                    "recorded_contributions",
                    "choices_changes_work_process_metadata",
                ],
                "excluded_classes": [
                    "generated_registries",
                    "generated_project_projections",
                    "generated_vertical_memory_files",
                    "publication_outputs",
                    "source_code_and_repository_docs",
                ],
                "excluded_project_files": sorted(_PROJECT_DERIVED_NAMES),
                "sources": list(capture.source_inputs),
            },
            "counts": _entry_counts(list(capture.entries)),
            "entries": [entry.to_dict() for entry in capture.entries],
            "contributions": capture.contributions.to_dict(),
            "diagnostics": list(capture.diagnostics),
            "read_operations": capture.read_operations,
        }
        body["semantic_sha256"] = semantic_sha256(body)
        return validate_publication_evidence_index(body)

    def source_fingerprint(
        self,
        *,
        read_context: WorkspaceReadContext | None = None,
        finalize: bool = True,
    ) -> tuple[str, tuple[dict[str, str], ...]]:
        read_context = read_context or WorkspaceReadContext(self.root)
        sources = []
        for path in self._selected_paths(read_context):
            document = read_context.documents.capture(path)
            if document.physical_sha256 is not None:
                sources.append(
                    {
                        "path": path.relative_to(self.root).as_posix(),
                        "sha256": document.physical_sha256,
                    }
                )
        if finalize:
            consistency = read_context.finalize()
            if not consistency.current:
                raise ValueError(
                    "Publication evidence sources changed during fingerprinting; retry. "
                    f"paths={','.join(consistency.changed_paths) or 'none'}; "
                    f"directories={','.join(consistency.changed_directories) or 'none'}"
                )
        sources.sort(key=lambda item: item["path"])
        return _source_fingerprint(sources), tuple(sources)

    def _selected_paths(self, read_context: WorkspaceReadContext) -> list[Path]:
        selected: dict[str, Path] = {}
        roots = (
            self.p2p_dir / "project",
            self.p2p_dir / "proposals",
            self.p2p_dir / "choices",
            self.p2p_dir / "changes",
            self.p2p_dir / "work",
            self.p2p_dir / "verticals",
        )
        for source_root in roots:
            if not source_root.exists():
                continue
            discovered = read_context.documents.discover(
                source_root,
                policy="publication-evidence-v2",
                predicate=lambda path, selected_root=source_root: (
                    path.is_file()
                    and path.suffix.lower() in (_TEXT_SUFFIXES | _YAML_SUFFIXES)
                    and "vertical-memory" not in path.parts
                    and (
                        selected_root != self.p2p_dir / "project"
                        or path.name in _PROJECT_EVIDENCE_NAMES
                    )
                ),
                recursive=True,
            )
            for path in discovered:
                selected[path.relative_to(self.root).as_posix()] = path
        project_yml = self.p2p_dir / "project.yml"
        if project_yml.exists() and project_yml.is_file():
            selected[project_yml.relative_to(self.root).as_posix()] = project_yml
        return [selected[key] for key in sorted(selected)]

    def _vertical_view(self, read_context: WorkspaceReadContext) -> VerticalProjectMemoryView | None:
        if self.vertical_memory is None:
            return None
        try:
            return _invoke_provider(self.vertical_memory, read_context)
        except ValueError:
            return None


def _invoke_provider(callback: Callable[..., object], read_context: WorkspaceReadContext):
    try:
        parameters = inspect.signature(callback).parameters.values()
    except (TypeError, ValueError):
        return callback()
    accepts_context = any(
        parameter.kind in {parameter.POSITIONAL_ONLY, parameter.POSITIONAL_OR_KEYWORD}
        or parameter.name == "read_context"
        for parameter in parameters
    )
    if not accepts_context:
        return callback()
    if any(parameter.name == "read_context" for parameter in parameters):
        return callback(read_context=read_context)
    return callback(read_context)


def evidence_index_hash(payload: Mapping[str, object]) -> str:
    return semantic_sha256(dict(payload))


def _source_fingerprint(sources: list[dict[str, str]]) -> str:
    return semantic_sha256(
        {
            "version": 2,
            "inputs": sorted(sources, key=lambda item: item["path"]),
        }
    )


def evidence_index_is_current(
    payload: Mapping[str, object],
    *,
    source_fingerprint_sha256: str,
    source_export_sha256: str,
    generator: str = PUBLICATION_EVIDENCE_GENERATOR,
) -> bool:
    if int(payload.get("schema_version") or 0) != PUBLICATION_CONTRACT_VERSION:
        return False
    if str(payload.get("generator") or "") != generator:
        return False
    if str(payload.get("source_fingerprint_sha256") or "") != source_fingerprint_sha256:
        return False
    export = payload.get("source_export")
    if not isinstance(export, Mapping) or str(export.get("sha256") or "") != source_export_sha256:
        return False
    recorded = str(payload.get("semantic_sha256") or "")
    content = dict(payload)
    content.pop("semantic_sha256", None)
    return bool(recorded) and semantic_sha256(content) == recorded


def contribution_summary_from_index(payload: Mapping[str, object]) -> PublicationContributionSummary:
    raw = payload.get("contributions")
    if not isinstance(raw, Mapping):
        return contribution_share_summary(())
    rows = raw.get("rows")
    authors: list[str] = []
    if isinstance(rows, list):
        for item in rows:
            if not isinstance(item, Mapping):
                continue
            authors.extend([str(item.get("author") or "")] * int(item.get("count") or 0))
    return contribution_share_summary(
        authors,
        source_evidence_ids=[str(item) for item in raw.get("source_evidence_ids", ())],
    )


def _complete_payload(path: Path, content: bytes) -> dict[str, object]:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"Publication evidence source must be UTF-8: {path}") from exc
    if path.suffix.lower() in _YAML_SUFFIXES:
        value = load_yaml_mapping(text, loader_contract=UNIQUE_LOADER_CONTRACT)
        return {"format": "yaml", "value": value}
    return {"format": "text", "value": text}


def _proposal_id_for_path(path: Path, p2p_dir: Path) -> str:
    proposals = p2p_dir / "proposals"
    try:
        first = path.relative_to(proposals).parts[0]
    except (ValueError, IndexError):
        return ""
    match = _PROPOSAL_ID.match(first)
    return match.group(1) if match else ""


def _authority_class(
    proposal_id: str,
    accepted_ids: set[str],
    lifecycle: Mapping[str, ProposalDecisionLifecycleView],
) -> str:
    if not proposal_id:
        return "project"
    view = lifecycle.get(proposal_id)
    if view is not None:
        state = getattr(view.effective_state, "value", str(view.effective_state))
        return "active" if state in {"accepted", "accepted_with_changes"} else "historical"
    return "active" if proposal_id in accepted_ids else "historical"


def _classify_path(
    path: Path,
    *,
    proposal_id: str,
    authority_class: str,
    vertical_sections: tuple[str, ...],
    explicitly_unmapped: bool,
) -> tuple[str, str]:
    name = path.name
    if name == "decision-events.yml" and proposal_id:
        if authority_class == "historical":
            return "proposal_decision_record", "historical_context"
        return (
            "proposal_decision_record",
            "cross_cutting" if explicitly_unmapped or not vertical_sections else "project_evidence",
        )
    if "choices" in path.parts and name == "choice.md":
        return "project_choice", "project_evidence"
    if name in _PROCESS_ONLY_NAMES:
        return "process_metadata", "process_only"
    if name == "conflicts.yml" and "project" in path.parts:
        return "project_conflict", "contradictory"
    if name == "contributions.yml":
        return "recorded_contribution", "contribution_metadata"
    if name in _UNCERTAINTY_NAMES:
        if authority_class == "historical":
            return "project_uncertainty", "historical_context"
        if name in _INSUFFICIENT_NAMES:
            return "project_uncertainty", "insufficient"
        return "project_uncertainty", "project_evidence"
    if not proposal_id:
        if any(part in {"choices", "changes", "work"} for part in path.parts):
            return "process_metadata", "process_only"
        return "project_definition", "project_evidence"
    if authority_class == "historical":
        return "proposal_artifact", "historical_context"
    if explicitly_unmapped or not vertical_sections:
        return "proposal_artifact", "cross_cutting"
    return "proposal_artifact", "project_evidence"


def _sections_by_proposal(view: VerticalProjectMemoryView | None) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    if view is None:
        return result
    for section in view.sections:
        for contribution in (*section.active_contributions, *section.historical_contributions):
            result.setdefault(contribution.proposal_id, set()).add(section.section_id)
    return result


def _unmapped_proposal_ids(view: VerticalProjectMemoryView | None) -> set[str]:
    if view is None:
        return set()
    return {
        str(item.get("proposal_id") or item.get("id") or "")
        for item in view.unmapped_active_proposals
        if str(item.get("proposal_id") or item.get("id") or "")
    }


def _classification_proposal_maps(
    payload: Mapping[str, object],
) -> tuple[dict[str, set[str]], set[str], dict[str, str]]:
    sections: dict[str, set[str]] = {}
    unassigned: set[str] = set()
    kinds: dict[str, str] = {}
    collections = payload.get("collections")
    if not isinstance(collections, Mapping):
        return sections, unassigned, kinds
    for collection in collections.values():
        if not isinstance(collection, Mapping):
            continue
        items = collection.get("items")
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, Mapping) or item.get("object_type") != "proposal":
                continue
            proposal_id = str(item.get("object_id") or "")
            if not proposal_id:
                continue
            scope_kind = str(item.get("scope_kind") or "unknown")
            kinds[proposal_id] = scope_kind
            raw_sections = item.get("active_section_ids") or item.get("section_ids") or []
            if isinstance(raw_sections, list):
                sections[proposal_id] = {str(value) for value in raw_sections if str(value)}
            if scope_kind == "unassigned" or item.get("state") in {
                "unassigned",
                "requires_reassignment",
                "unknown",
            }:
                unassigned.add(proposal_id)
    return sections, unassigned, kinds


def _vertical_payload(view: VerticalProjectMemoryView | None) -> dict[str, object]:
    if view is None:
        return {
            "available": False,
            "id": "",
            "version": "",
            "required_sections": [],
            "reader_questions": [],
        }
    required_sections = []
    reader_questions = []
    for section in sorted(view.sections, key=lambda item: (item.priority, item.section_id)):
        if section.required:
            required_sections.append(
                {
                    "id": section.section_id,
                    "title": section.title,
                    "purpose": section.purpose,
                    "priority": section.priority,
                }
            )
        questions = section.declared_questions or tuple(
            str(item.get("question") or item.get("text") or "")
            for item in section.questions
        )
        for index, question in enumerate(item for item in questions if item):
            reader_questions.append(
                {
                    "id": f"VRQ-{section.section_id}-{index + 1:03d}",
                    "section_id": section.section_id,
                    "question": question,
                }
            )
    return {
        "available": True,
        "id": view.vertical_id,
        "version": view.vertical_version,
        "checksum": view.vertical_checksum,
        "profile": view.profile,
        "modules": list(view.modules),
        "fallback_used": view.fallback_used,
        "definition_exists": view.definition_exists,
        "definition_valid": view.definition_valid,
        "required_sections": required_sections,
        "reader_questions": reader_questions,
    }


def _contribution_authors(payload: Mapping[str, object]) -> list[str]:
    value = payload.get("value")
    if not isinstance(value, Mapping):
        return []
    contributions = value.get("contributions")
    if not isinstance(contributions, list):
        return []
    return [str(item.get("author") or "") for item in contributions if isinstance(item, Mapping)]


def _entry_counts(entries: list[PublicationEvidenceEntry]) -> dict[str, int]:
    counts = {
        "total": len(entries),
        "active": 0,
        "historical": 0,
        "project_evidence": 0,
        "mapped": 0,
        "unmapped": 0,
        "cross_cutting": 0,
        "process_only": 0,
        "contribution_metadata": 0,
        "historical_context": 0,
        "contradictory": 0,
        "duplicate": 0,
        "insufficient": 0,
    }
    for entry in entries:
        if entry.authority_class in counts:
            counts[entry.authority_class] += 1
        if entry.editorial_class in counts:
            counts[entry.editorial_class] += 1
        if entry.authority_class == "active" and entry.editorial_class == "project_evidence":
            counts["mapped"] += 1
        if entry.authority_class == "active" and entry.editorial_class == "cross_cutting":
            counts["unmapped"] += 1
    return counts


def _mark_duplicate_evidence(
    entries: list[PublicationEvidenceEntry],
) -> list[PublicationEvidenceEntry]:
    eligible = {"project_evidence", "cross_cutting", "insufficient", "contradictory"}
    seen: set[str] = set()
    result: list[PublicationEvidenceEntry] = []
    for entry in sorted(entries, key=lambda item: (item.source_path, item.source_selector)):
        content_identity = semantic_sha256({"kind": entry.kind, "payload": dict(entry.payload)})
        if entry.editorial_class not in eligible or content_identity not in seen:
            if entry.editorial_class in eligible:
                seen.add(content_identity)
            result.append(entry)
            continue
        semantic_payload = {
            "kind": entry.kind,
            "source_path": entry.source_path,
            "source_selector": entry.source_selector,
            "payload": dict(entry.payload),
        }
        semantic_hash = semantic_sha256(semantic_payload)
        result.append(
            replace(
                entry,
                editorial_class="duplicate",
                semantic_sha256=semantic_hash,
            )
        )
    return result


def _diagnostics(
    view: VerticalProjectMemoryView | None,
    entries: list[PublicationEvidenceEntry],
) -> list[dict[str, str]]:
    diagnostics: list[dict[str, str]] = []
    if view is None:
        diagnostics.append(
            {
                "code": "publication_vertical_unavailable",
                "severity": "advisory",
                "message": "No current vertical project memory was available; use generic project framing.",
            }
        )
    if any(item.editorial_class == "cross_cutting" for item in entries):
        diagnostics.append(
            {
                "code": "publication_cross_cutting_evidence",
                "severity": "advisory",
                "message": "Active evidence without vertical section mapping requires explicit accounting.",
            }
        )
    return diagnostics
