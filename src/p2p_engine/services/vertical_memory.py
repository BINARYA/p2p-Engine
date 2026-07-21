from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
import base64
import hashlib
import json
from pathlib import Path
import re

from p2p_engine.core.mutation_preview import MutationPreviewService, semantic_sha256, source_precondition
from p2p_engine.core.project_questions import ProjectQuestionArtifact
from p2p_engine.core.proposal_decision_events import ProposalDecisionLifecycleView
from p2p_engine.core.vertical_memory import (
    VERTICAL_MEMORY_GENERATOR_CONTRACT,
    VERTICAL_MEMORY_CURSOR_POLICY_VERSION,
    VERTICAL_MEMORY_IDENTITY_POLICY,
    VERTICAL_MEMORY_MANIFEST_VERSION,
    VERTICAL_MEMORY_PROJECT_VERSION,
    VERTICAL_MEMORY_ROOT,
    VERTICAL_MEMORY_SECTION_VERSION,
    VERTICAL_MEMORY_SOURCE_POLICY,
    VerticalMemoryCandidate,
    VerticalMemoryAggregate,
    DerivedUpdateResult,
    VerticalMemoryContribution,
    VerticalMemoryEvidence,
    VerticalMemoryImpact,
    VerticalMemoryOperationResult,
    VerticalMemoryPage,
    VerticalMemorySection,
    VerticalMemoryStatus,
    VerticalProjectMemoryView,
    validate_vertical_memory_owned_path,
    validate_vertical_memory_owned_source,
    validate_vertical_memory_view,
    vertical_memory_section_path,
)
from p2p_engine.foundation.files import read_yaml_mapping, yaml_dump
from p2p_engine.foundation.markdown import read_frontmatter, read_markdown_section, read_title
from p2p_engine.foundation.yaml_loaders import load_yaml_mapping
from p2p_engine.services.project_verticals import _section_fields
from p2p_engine.services.workspace_reads import WorkspaceReadContext
from p2p_engine.services.workspace_transactions import AtomicMutationWriter


_FRAGMENT_LIMIT = 4000
_MANIFEST_PATH = f"{VERTICAL_MEMORY_ROOT}/manifest.yml"
_PROJECT_PATH = f"{VERTICAL_MEMORY_ROOT}/project.yml"


class VerticalProjectMemoryBuilder:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        vertical_service: object,
        question_artifact: Callable[[], ProjectQuestionArtifact | None],
        proposal_lifecycles: Callable[
            [WorkspaceReadContext],
            Mapping[str, ProposalDecisionLifecycleView],
        ],
        proposal_lifecycles_for: (
            Callable[
                [Sequence[str], WorkspaceReadContext],
                Mapping[str, ProposalDecisionLifecycleView],
            ]
            | None
        ) = None,
        find_proposal_dir: Callable[[str], Path],
    ) -> None:
        self.root = root.resolve()
        self.p2p_dir = p2p_dir.resolve()
        self.vertical_service = vertical_service
        self.question_artifact = question_artifact
        self.proposal_lifecycles = proposal_lifecycles
        self.proposal_lifecycles_for = proposal_lifecycles_for
        self.find_proposal_dir = find_proposal_dir

    def build_full(self, context: WorkspaceReadContext) -> VerticalMemoryCandidate:
        catalog = self._source_catalog(context)
        source_fingerprint, source_scopes = _source_fingerprints(catalog)
        vertical_state = context.provide(
            "vertical_memory.vertical_state",
            (),
            self.vertical_service.vertical_read_state,
        )
        definition_view = context.provide(
            "vertical_memory.definition",
            (),
            self.vertical_service.project_definition_view,
        )
        questions = context.provide(
            "vertical_memory.questions",
            (),
            self.question_artifact,
        )
        lifecycles = context.provide(
            "vertical_memory.lifecycles",
            (),
            lambda: dict(self.proposal_lifecycles(context)),
        )
        proposal_ids = tuple(sorted(lifecycles))
        proposal_dirs = self._proposal_directories(context, proposal_ids)
        coverages = context.provide(
            "vertical_memory.coverages",
            (proposal_ids,),
            lambda: self.vertical_service.proposal_vertical_coverage_statuses(
                proposal_ids,
                state=vertical_state,
            ),
        )
        heuristic_suggestions = context.provide(
            "vertical_memory.heuristic_suggestions",
            (proposal_ids,),
            lambda: self.vertical_service.suggest_proposal_vertical_coverages(
                proposal_ids,
                state=vertical_state,
            ),
        )
        readiness_heuristics_by_section: dict[str, list[Mapping[str, object]]] = {}
        for proposal_id in proposal_ids:
            proposal_dir = proposal_dirs[proposal_id]
            selected_paths = tuple(
                proposal_dir / filename
                for filename in ("proposal.md", "decision.md", "suggested-scope.md", "risks.md")
                if (proposal_dir / filename).is_file()
            )
            combined = "\n".join(context.documents.text(path) for path in selected_paths).lower()
            for section in vertical_state.pack.sections:
                if section.section_id in vertical_state.base_section_ids:
                    continue
                terms = vertical_state.readiness_terms_by_section.get(section.section_id, ())
                matched = tuple(term for term in terms if term and term in combined)
                if matched:
                    readiness_heuristics_by_section.setdefault(section.section_id, []).append(
                        {
                            "proposal_id": proposal_id,
                            "policy": "project-readiness-legacy-v1",
                            "matched_terms": list(matched),
                            "source_paths": [
                                path.relative_to(self.root).as_posix() for path in selected_paths
                            ],
                        }
                    )
        definition_sections = {
            item.section_id: item
            for item in (
                definition_view.state.sections
                if definition_view.exists and definition_view.state is not None
                else ()
            )
        }
        questions_by_section: dict[str, list[Mapping[str, object]]] = {}
        if questions is not None:
            for item in questions.questions:
                questions_by_section.setdefault(item.section_id, []).append(
                    {
                        "id": item.question_id,
                        "revision": item.revision,
                        "state": item.state.value,
                        "applicability": item.applicability.value,
                        "priority": item.priority,
                        "question": item.question,
                        "target": item.target.to_dict(),
                    }
                )
        active_by_section: dict[str, list[VerticalMemoryContribution]] = {
            item.section_id: [] for item in vertical_state.pack.sections
        }
        historical_by_section: dict[str, list[VerticalMemoryContribution]] = {
            item.section_id: [] for item in vertical_state.pack.sections
        }
        coverage_sections_by_proposal: dict[str, tuple[str, ...]] = {}
        unmapped: list[Mapping[str, object]] = []
        diagnostics: list[Mapping[str, object]] = [
            {
                "code": issue.code or "VERTICAL_MEMORY_DEFINITION_DIAGNOSTIC",
                "severity": issue.severity,
                "message": issue.message,
                "section_id": "",
                "suggested_command": "p2p project definition show",
            }
            for issue in definition_view.issues
        ]
        for proposal_id in proposal_ids:
            lifecycle = lifecycles[proposal_id]
            coverage_status = coverages[proposal_id]
            proposal_path = proposal_dirs[proposal_id] / "proposal.md"
            text = context.documents.text(proposal_path) if proposal_path.exists() else ""
            title = _clean_title(read_title(text) or proposal_id, proposal_id)
            if coverage_status.state != "valid" or coverage_status.coverage is None:
                if lifecycle.active_projection:
                    suggestion = heuristic_suggestions.get(proposal_id)
                    unmapped.append(
                        {
                            "proposal_id": proposal_id,
                            "title": title,
                            "effective_state": lifecycle.effective_state.value,
                            "reason": coverage_status.state,
                            "source_path": proposal_path.relative_to(self.root).as_posix(),
                            "heuristic_sections": [
                                item.section_id
                                for item in getattr(suggestion, "candidates", ())
                            ],
                        }
                    )
                if coverage_status.state == "invalid":
                    diagnostics.append(
                        {
                            "code": "VERTICAL_MEMORY_INVALID_COVERAGE",
                            "proposal_id": proposal_id,
                            "message": coverage_status.message,
                        }
                    )
                continue
            for coverage in sorted(
                coverage_status.coverage.sections,
                key=lambda item: item.section_id,
            ):
                if coverage.section_id not in active_by_section:
                    diagnostics.append(
                        {
                            "code": "VERTICAL_MEMORY_UNKNOWN_SECTION",
                            "proposal_id": proposal_id,
                            "section_id": coverage.section_id,
                        }
                    )
                    continue
                contribution = _contribution(
                    proposal_id=proposal_id,
                    title=title,
                    section_id=coverage.section_id,
                    lifecycle=lifecycle,
                    coverage_rationale=coverage.rationale,
                    proposal_path=proposal_path.relative_to(self.root),
                    proposal_text=text,
                )
                if lifecycle.active_projection:
                    active_by_section[coverage.section_id].append(contribution)
                else:
                    historical_by_section[coverage.section_id].append(contribution)
            coverage_sections_by_proposal[proposal_id] = tuple(
                sorted(item.section_id for item in coverage_status.coverage.sections)
            )
        topology_by_section, topology_diagnostics = self._topology(
            context,
            coverage_sections_by_proposal=coverage_sections_by_proposal,
        )
        diagnostics.extend(topology_diagnostics)
        sections: list[VerticalMemorySection] = []
        for section in sorted(
            vertical_state.pack.sections,
            key=lambda item: (item.priority, item.section_id),
        ):
            definition = definition_sections.get(section.section_id)
            sections.append(
                VerticalMemorySection(
                    section_id=section.section_id,
                    title=section.title,
                    purpose=section.purpose,
                    required=section.required,
                    priority=section.priority,
                    definition=_definition_payload(
                        definition,
                        required_field_ids=tuple(
                            field.field_id
                            for field in _section_fields(section, vertical_state.pack)
                            if field.required
                        ),
                    ),
                    questions=tuple(
                        sorted(
                            questions_by_section.get(section.section_id, ()),
                            key=lambda item: str(item.get("id") or ""),
                        )
                    ),
                    active_contributions=tuple(
                        sorted(
                            active_by_section[section.section_id],
                            key=lambda item: (item.proposal_id, item.contribution_id),
                        )
                    ),
                    historical_contributions=tuple(
                        sorted(
                            historical_by_section[section.section_id],
                            key=lambda item: (item.proposal_id, item.contribution_id),
                        )
                    ),
                    declared_questions=tuple(
                        item.question
                        for item in vertical_state.pack.questions
                        if item.section_id == section.section_id
                    ),
                    heuristic_suggestions=tuple(
                        sorted(
                            readiness_heuristics_by_section.get(section.section_id, ()),
                            key=lambda item: str(item.get("proposal_id") or ""),
                        )
                    ),
                    conflicts=tuple(
                        sorted(
                            topology_by_section.get(section.section_id, ()),
                            key=lambda item: (
                                str(item.get("kind") or ""),
                                str(item.get("id") or ""),
                            ),
                        )
                    ),
                )
            )
        lock_status = context.provide(
            "vertical_memory.vertical_lock",
            (),
            self.vertical_service.vertical_lock_status,
        )
        checksum = (
            lock_status.resolved.checksum
            if getattr(lock_status, "resolved", None) is not None
            else semantic_sha256(
                {
                    "vertical_id": vertical_state.pack.vertical_id,
                    "version": vertical_state.pack.version,
                }
            )
        )
        view = VerticalProjectMemoryView(
            vertical_id=vertical_state.pack.vertical_id,
            vertical_version=vertical_state.pack.version,
            vertical_checksum=checksum,
            sections=tuple(sections),
            unmapped_active_proposals=tuple(
                sorted(unmapped, key=lambda item: str(item["proposal_id"]))
            ),
            diagnostics=tuple(
                sorted(
                    diagnostics,
                    key=lambda item: (
                        str(item.get("code") or ""),
                        str(item.get("proposal_id") or ""),
                        str(item.get("section_id") or ""),
                    ),
                )
            ),
            source_fingerprint_sha256=source_fingerprint,
            profile=(
                definition_view.state.profile
                if definition_view.exists and definition_view.state is not None
                else "default"
            ),
            modules=tuple(
                definition_view.state.modules
                if definition_view.exists and definition_view.state is not None
                else ()
            ),
            fallback_used=vertical_state.active.fallback_used,
            vertical_source=vertical_state.active.source or vertical_state.pack.source,
            vertical_lock_checksum=(
                lock_status.resolved.checksum
                if getattr(lock_status, "resolved", None) is not None
                else ""
            ),
            definition_exists=definition_view.exists,
            definition_valid=definition_view.valid,
        )
        validate_vertical_memory_view(view)
        return self._render_candidate(
            view,
            catalog=catalog,
            source_scopes=source_scopes,
        )

    def _render_candidate(
        self,
        view: VerticalProjectMemoryView,
        *,
        catalog: tuple[tuple[str, bytes], ...],
        source_scopes: Mapping[str, str],
        reused_sections: Mapping[str, bytes] | None = None,
    ) -> VerticalMemoryCandidate:
        reused_sections = reused_sections or {}
        candidates: dict[str, bytes] = {}
        section_outputs: dict[str, dict[str, object]] = {}
        for section in view.sections:
            relative = vertical_memory_section_path(section.section_id)
            content = reused_sections.get(section.section_id)
            if content is None:
                content = yaml_dump(section.to_dict()).encode("utf-8")
            elif _section_from_payload(load_yaml_mapping(content)) != section:
                raise ValueError(
                    f"Reused vertical-memory section does not match typed view: {section.section_id}"
                )
            candidates[relative] = content
            section_outputs[section.section_id] = {
                "path": relative,
                "sha256": hashlib.sha256(content).hexdigest(),
                "active_contributions": len(section.active_contributions),
                "historical_contributions": len(section.historical_contributions),
            }
        project_payload = {
            "vertical_project_memory": {
                "schema_version": VERTICAL_MEMORY_PROJECT_VERSION,
                "vertical": {
                    "id": view.vertical_id,
                    "version": view.vertical_version,
                    "checksum": view.vertical_checksum,
                },
                "source_fingerprint_sha256": view.source_fingerprint_sha256,
                "profile": view.profile,
                "modules": list(view.modules),
                "fallback_used": view.fallback_used,
                "vertical_source": view.vertical_source,
                "vertical_lock_checksum": view.vertical_lock_checksum,
                "definition_exists": view.definition_exists,
                "definition_valid": view.definition_valid,
                "sections": [
                    {
                        "id": section.section_id,
                        **section_outputs[section.section_id],
                    }
                    for section in view.sections
                ],
                "unmapped_active_proposals": [dict(item) for item in view.unmapped_active_proposals],
                "diagnostics": [dict(item) for item in view.diagnostics],
            }
        }
        project_content = yaml_dump(project_payload).encode("utf-8")
        candidates[_PROJECT_PATH] = project_content
        owned_paths = tuple(sorted((*candidates, _MANIFEST_PATH)))
        manifest_payload = {
            "vertical_project_memory_manifest": {
                "manifest_version": VERTICAL_MEMORY_MANIFEST_VERSION,
                "generator_contract_version": VERTICAL_MEMORY_GENERATOR_CONTRACT,
                "source_catalog_policy_version": VERTICAL_MEMORY_SOURCE_POLICY,
                "identity_policy_version": VERTICAL_MEMORY_IDENTITY_POLICY,
                "vertical": {
                    "id": view.vertical_id,
                    "version": view.vertical_version,
                    "checksum": view.vertical_checksum,
                },
                "source_fingerprint_sha256": view.source_fingerprint_sha256,
                "source_scopes": dict(sorted(source_scopes.items())),
                "source_records": {
                    path: hashlib.sha256(content).hexdigest()
                    for path, content in catalog
                },
                "generation_mode": "deterministic",
                "outputs": {
                    path: {"sha256": hashlib.sha256(content).hexdigest()}
                    for path, content in sorted(candidates.items())
                },
                "section_count": len(view.sections),
                "owned_paths": list(owned_paths),
            }
        }
        candidates[_MANIFEST_PATH] = yaml_dump(manifest_payload).encode("utf-8")
        return VerticalMemoryCandidate(
            view=view,
            candidates=candidates,
            source_preconditions=tuple(
                source_precondition(item[0], item[1]) for item in catalog
            ),
            owned_paths=owned_paths,
            source_scopes=source_scopes,
        )

    def build_incremental(
        self,
        context: WorkspaceReadContext,
        *,
        prior_view: VerticalProjectMemoryView,
        impact: VerticalMemoryImpact,
        reused_sections: Mapping[str, bytes],
    ) -> tuple[VerticalMemoryCandidate, VerticalMemoryImpact]:
        if impact.full_rebuild:
            raise ValueError("Vertical-memory impact requires a full rebuild")
        proposal_ids = tuple(sorted(set(impact.proposal_ids)))
        if not proposal_ids:
            raise ValueError("Incremental vertical-memory build requires exact proposal impact")
        catalog = self._source_catalog(context)
        source_fingerprint, source_scopes = _source_fingerprints(catalog)
        vertical_state = context.provide(
            "vertical_memory.vertical_state",
            (),
            self.vertical_service.vertical_read_state,
        )
        if (
            vertical_state.pack.vertical_id != prior_view.vertical_id
            or vertical_state.pack.version != prior_view.vertical_version
        ):
            raise ValueError("Active vertical changed; a full vertical-memory rebuild is required")
        lifecycles = dict(
            self.proposal_lifecycles_for(proposal_ids, context)
            if self.proposal_lifecycles_for is not None
            else {
                key: value
                for key, value in self.proposal_lifecycles(context).items()
                if key in proposal_ids
            }
        )
        if set(lifecycles) != set(proposal_ids):
            raise ValueError("Incremental lifecycle capture did not resolve every affected proposal")
        proposal_dirs = self._proposal_directories(context, proposal_ids)
        coverages = self.vertical_service.proposal_vertical_coverage_statuses(
            proposal_ids,
            state=vertical_state,
        )
        suggestions = self.vertical_service.suggest_proposal_vertical_coverages(
            proposal_ids,
            state=vertical_state,
        )
        sections_by_id = {section.section_id: section for section in prior_view.sections}
        affected_sections = set(impact.section_ids)
        active_by_section = {
            section_id: [
                item
                for item in section.active_contributions
                if item.proposal_id not in proposal_ids
            ]
            for section_id, section in sections_by_id.items()
        }
        historical_by_section = {
            section_id: [
                item
                for item in section.historical_contributions
                if item.proposal_id not in proposal_ids
            ]
            for section_id, section in sections_by_id.items()
        }
        heuristics_by_section = {
            section_id: [
                item
                for item in section.heuristic_suggestions
                if str(item.get("proposal_id") or "") not in proposal_ids
            ]
            for section_id, section in sections_by_id.items()
        }
        for section in prior_view.sections:
            if any(
                item.proposal_id in proposal_ids
                for item in (*section.active_contributions, *section.historical_contributions)
            ) or any(
                str(item.get("proposal_id") or "") in proposal_ids
                for item in section.heuristic_suggestions
            ):
                affected_sections.add(section.section_id)

        unmapped = [
            dict(item)
            for item in prior_view.unmapped_active_proposals
            if str(item.get("proposal_id") or "") not in proposal_ids
        ]
        diagnostics = [
            dict(item)
            for item in prior_view.diagnostics
            if str(item.get("proposal_id") or "") not in proposal_ids
            and str(item.get("code") or "")
            not in {
                "VERTICAL_MEMORY_INVALID_CONFLICTS",
                "VERTICAL_MEMORY_UNMAPPED_CONFLICT",
                "VERTICAL_MEMORY_UNMAPPED_CHOICE",
            }
        ]
        coverage_sections_by_proposal = _coverage_sections_from_view(prior_view)
        for proposal_id in proposal_ids:
            lifecycle = lifecycles[proposal_id]
            coverage_status = coverages[proposal_id]
            proposal_path = proposal_dirs[proposal_id] / "proposal.md"
            text = context.documents.text(proposal_path) if proposal_path.is_file() else ""
            title = _clean_title(read_title(text) or proposal_id, proposal_id)
            new_sections: tuple[str, ...] = ()
            if coverage_status.state == "valid" and coverage_status.coverage is not None:
                new_sections = tuple(
                    sorted(item.section_id for item in coverage_status.coverage.sections)
                )
                coverage_sections_by_proposal[proposal_id] = new_sections
                for coverage in coverage_status.coverage.sections:
                    contribution = _contribution(
                        proposal_id=proposal_id,
                        title=title,
                        section_id=coverage.section_id,
                        lifecycle=lifecycle,
                        coverage_rationale=coverage.rationale,
                        proposal_path=proposal_path.relative_to(self.root),
                        proposal_text=text,
                    )
                    target = (
                        active_by_section if lifecycle.active_projection else historical_by_section
                    )
                    target[coverage.section_id].append(contribution)
                    affected_sections.add(coverage.section_id)
            else:
                coverage_sections_by_proposal.pop(proposal_id, None)
                if lifecycle.active_projection:
                    suggestion = suggestions[proposal_id]
                    unmapped.append(
                        {
                            "proposal_id": proposal_id,
                            "title": title,
                            "effective_state": lifecycle.effective_state.value,
                            "reason": coverage_status.state,
                            "source_path": proposal_path.relative_to(self.root).as_posix(),
                            "heuristic_sections": [
                                item.section_id for item in suggestion.candidates
                            ],
                        }
                    )
                if coverage_status.state == "invalid":
                    diagnostics.append(
                        {
                            "code": "VERTICAL_MEMORY_INVALID_COVERAGE",
                            "proposal_id": proposal_id,
                            "message": coverage_status.message,
                        }
                    )
            selected_paths = tuple(
                proposal_dirs[proposal_id] / filename
                for filename in ("proposal.md", "decision.md", "suggested-scope.md", "risks.md")
                if (proposal_dirs[proposal_id] / filename).is_file()
            )
            combined = "\n".join(context.documents.text(path) for path in selected_paths).lower()
            for section in vertical_state.pack.sections:
                if section.section_id in vertical_state.base_section_ids:
                    continue
                terms = vertical_state.readiness_terms_by_section.get(section.section_id, ())
                matched = tuple(term for term in terms if term and term in combined)
                if not matched:
                    continue
                heuristics_by_section[section.section_id].append(
                    {
                        "proposal_id": proposal_id,
                        "policy": "project-readiness-legacy-v1",
                        "matched_terms": list(matched),
                        "source_paths": [
                            path.relative_to(self.root).as_posix() for path in selected_paths
                        ],
                    }
                )
                affected_sections.add(section.section_id)

        topology_by_section, topology_diagnostics = self._topology(
            context,
            coverage_sections_by_proposal=coverage_sections_by_proposal,
        )
        diagnostics.extend(topology_diagnostics)
        sections: list[VerticalMemorySection] = []
        for prior in prior_view.sections:
            conflicts = tuple(
                sorted(
                    topology_by_section.get(prior.section_id, ()),
                    key=lambda item: (
                        str(item.get("kind") or ""),
                        str(item.get("id") or ""),
                    ),
                )
            )
            if conflicts != prior.conflicts:
                affected_sections.add(prior.section_id)
            sections.append(
                replace(
                    prior,
                    active_contributions=tuple(
                        sorted(
                            active_by_section[prior.section_id],
                            key=lambda item: (item.proposal_id, item.contribution_id),
                        )
                    ),
                    historical_contributions=tuple(
                        sorted(
                            historical_by_section[prior.section_id],
                            key=lambda item: (item.proposal_id, item.contribution_id),
                        )
                    ),
                    heuristic_suggestions=tuple(
                        sorted(
                            heuristics_by_section[prior.section_id],
                            key=lambda item: str(item.get("proposal_id") or ""),
                        )
                    ),
                    conflicts=conflicts,
                )
            )
        view = replace(
            prior_view,
            sections=tuple(sections),
            unmapped_active_proposals=tuple(
                sorted(unmapped, key=lambda item: str(item.get("proposal_id") or ""))
            ),
            diagnostics=tuple(
                sorted(
                    diagnostics,
                    key=lambda item: (
                        str(item.get("code") or ""),
                        str(item.get("proposal_id") or ""),
                        str(item.get("section_id") or ""),
                    ),
                )
            ),
            source_fingerprint_sha256=source_fingerprint,
            source="candidate",
        )
        validate_vertical_memory_view(view)
        final_impact = replace(
            impact,
            section_ids=tuple(sorted(affected_sections)),
            aggregate_changed=True,
        )
        reusable = {
            section_id: content
            for section_id, content in reused_sections.items()
            if section_id not in affected_sections
        }
        return (
            self._render_candidate(
                view,
                catalog=catalog,
                source_scopes=source_scopes,
                reused_sections=reusable,
            ),
            final_impact,
        )

    def build_section_incremental(
        self,
        context: WorkspaceReadContext,
        *,
        prior_view: VerticalProjectMemoryView,
        impact: VerticalMemoryImpact,
        reused_sections: Mapping[str, bytes],
    ) -> tuple[VerticalMemoryCandidate, VerticalMemoryImpact]:
        affected = set(impact.section_ids)
        if impact.full_rebuild or not affected:
            raise ValueError("Exact affected sections are required for incremental definition refresh")
        catalog = self._source_catalog(context)
        source_fingerprint, source_scopes = _source_fingerprints(catalog)
        vertical_state = context.provide(
            "vertical_memory.vertical_state",
            (),
            self.vertical_service.vertical_read_state,
        )
        if (
            vertical_state.pack.vertical_id != prior_view.vertical_id
            or vertical_state.pack.version != prior_view.vertical_version
        ):
            raise ValueError("Active vertical changed; a full vertical-memory rebuild is required")
        valid_sections = {item.section_id for item in vertical_state.pack.sections}
        unknown = affected - valid_sections
        if unknown:
            raise ValueError(
                "Unknown affected vertical-memory section: " + ", ".join(sorted(unknown))
            )
        definition_view = context.provide(
            "vertical_memory.definition",
            (),
            self.vertical_service.project_definition_view,
        )
        questions = context.provide(
            "vertical_memory.questions",
            (),
            self.question_artifact,
        )
        definitions = {
            item.section_id: item
            for item in (
                definition_view.state.sections
                if definition_view.exists and definition_view.state is not None
                else ()
            )
        }
        questions_by_section: dict[str, list[Mapping[str, object]]] = {}
        if questions is not None:
            for item in questions.questions:
                questions_by_section.setdefault(item.section_id, []).append(
                    {
                        "id": item.question_id,
                        "revision": item.revision,
                        "state": item.state.value,
                        "applicability": item.applicability.value,
                        "priority": item.priority,
                        "question": item.question,
                        "target": item.target.to_dict(),
                    }
                )
        pack_sections = {item.section_id: item for item in vertical_state.pack.sections}
        sections: list[VerticalMemorySection] = []
        for prior in prior_view.sections:
            if prior.section_id not in affected:
                sections.append(prior)
                continue
            pack_section = pack_sections[prior.section_id]
            sections.append(
                replace(
                    prior,
                    definition=_definition_payload(
                        definitions.get(prior.section_id),
                        required_field_ids=tuple(
                            field.field_id
                            for field in _section_fields(pack_section, vertical_state.pack)
                            if field.required
                        ),
                    ),
                    questions=tuple(
                        sorted(
                            questions_by_section.get(prior.section_id, ()),
                            key=lambda item: str(item.get("id") or ""),
                        )
                    ),
                )
            )
        diagnostics = [
            dict(item)
            for item in prior_view.diagnostics
            if str(item.get("suggested_command") or "") != "p2p project definition show"
        ]
        diagnostics.extend(
            {
                "code": issue.code or "VERTICAL_MEMORY_DEFINITION_DIAGNOSTIC",
                "severity": issue.severity,
                "message": issue.message,
                "section_id": "",
                "suggested_command": "p2p project definition show",
            }
            for issue in definition_view.issues
        )
        view = replace(
            prior_view,
            sections=tuple(sections),
            diagnostics=tuple(
                sorted(
                    diagnostics,
                    key=lambda item: (
                        str(item.get("code") or ""),
                        str(item.get("proposal_id") or ""),
                        str(item.get("section_id") or ""),
                    ),
                )
            ),
            source_fingerprint_sha256=source_fingerprint,
            profile=(
                definition_view.state.profile
                if definition_view.exists and definition_view.state is not None
                else "default"
            ),
            modules=tuple(
                definition_view.state.modules
                if definition_view.exists and definition_view.state is not None
                else ()
            ),
            definition_exists=definition_view.exists,
            definition_valid=definition_view.valid,
            source="candidate",
        )
        validate_vertical_memory_view(view)
        return (
            self._render_candidate(
                view,
                catalog=catalog,
                source_scopes=source_scopes,
                reused_sections={
                    section_id: content
                    for section_id, content in reused_sections.items()
                    if section_id not in affected
                },
            ),
            replace(impact, aggregate_changed=True),
        )

    def _source_catalog(
        self,
        context: WorkspaceReadContext,
    ) -> tuple[tuple[str, bytes], ...]:
        selected: set[Path] = set()
        fixed = (
            self.p2p_dir / "project" / "vertical.yml",
            self.p2p_dir / "project" / "vertical.lock.yml",
            self.p2p_dir / "project" / "definition.yml",
            self.p2p_dir / "project" / "questions.yml",
            self.p2p_dir / "project" / "conflicts.yml",
        )
        for path in fixed:
            if context.documents.capture(path).exists:
                selected.add(path)
        for domain in ("proposals", "choices"):
            base = self.p2p_dir / domain
            for path in context.documents.discover(
                base,
                policy=f"vertical-memory-{domain}-sources-v1",
                predicate=lambda item: item.is_file(),
                recursive=True,
            ):
                if path.is_file() and _is_vertical_memory_source(path, domain):
                    selected.add(path)
        verticals = self.p2p_dir / "verticals"
        for path in context.documents.discover(
            verticals,
            policy="vertical-memory-packs-v1",
            predicate=lambda item: item.is_file(),
            recursive=True,
        ):
            selected.add(path)
        return tuple(
            (path.relative_to(self.root).as_posix(), context.documents.bytes(path))
            for path in sorted(selected, key=lambda item: item.relative_to(self.root).as_posix())
        )

    def _proposal_directories(
        self,
        context: WorkspaceReadContext,
        proposal_ids: Sequence[str],
    ) -> dict[str, Path]:
        requested = set(proposal_ids)
        directories = context.documents.discover(
            self.p2p_dir / "proposals",
            policy="vertical-memory-proposal-directories-v1",
            predicate=lambda item: item.is_dir(),
        )
        result: dict[str, Path] = {}
        for path in directories:
            parts = path.name.split("-", 2)
            if len(parts) < 2 or parts[0] != "PROP" or not parts[1].isdigit():
                continue
            proposal_id = f"PROP-{parts[1]}"
            if proposal_id not in requested:
                continue
            if proposal_id in result:
                raise ValueError(f"Ambiguous proposal ID: {proposal_id}")
            result[proposal_id] = path
        missing = tuple(sorted(requested - set(result)))
        if missing:
            raise ValueError(f"Proposal not found: {missing[0]}")
        return result

    def _topology(
        self,
        context: WorkspaceReadContext,
        *,
        coverage_sections_by_proposal: Mapping[str, tuple[str, ...]],
    ) -> tuple[dict[str, list[Mapping[str, object]]], list[Mapping[str, object]]]:
        by_section: dict[str, list[Mapping[str, object]]] = {}
        diagnostics: list[Mapping[str, object]] = []
        conflict_path = self.p2p_dir / "project" / "conflicts.yml"
        if conflict_path.is_file():
            payload = context.documents.yaml(conflict_path, loader_contract="unique-v1")
            if not isinstance(payload, Mapping) or not isinstance(payload.get("conflicts", ()), list):
                diagnostics.append(
                    {
                        "code": "VERTICAL_MEMORY_INVALID_CONFLICTS",
                        "severity": "error",
                        "message": "Project conflicts must contain a conflicts list.",
                        "suggested_command": "p2p conflict status",
                    }
                )
            else:
                for item in payload.get("conflicts", ()):
                    if not isinstance(item, Mapping):
                        continue
                    proposals = tuple(
                        sorted({str(value) for value in item.get("proposals", ()) if str(value)})
                    )
                    sections = _topology_sections(proposals, coverage_sections_by_proposal)
                    record = {
                        "kind": "conflict",
                        "id": str(item.get("id") or ""),
                        "type": str(item.get("type") or ""),
                        "status": "resolved" if item.get("winner") else "unresolved",
                        "proposals": list(proposals),
                        "winner": item.get("winner"),
                        "rejected": sorted(str(value) for value in item.get("rejected", ()) if str(value)),
                        "reason": str(item.get("reason") or ""),
                        "source_path": conflict_path.relative_to(self.root).as_posix(),
                    }
                    if sections:
                        for section_id in sections:
                            by_section.setdefault(section_id, []).append(record)
                    else:
                        diagnostics.append(
                            {
                                "code": "VERTICAL_MEMORY_UNMAPPED_CONFLICT",
                                "severity": "warning",
                                "message": f"Conflict `{record['id']}` has no declared vertical section.",
                                "suggested_command": "p2p project memory show",
                            }
                        )

        choices_dir = self.p2p_dir / "choices"
        for choice_dir in sorted(choices_dir.iterdir()) if choices_dir.is_dir() else ():
            if not choice_dir.is_dir() or choice_dir.is_symlink():
                continue
            choice_path = choice_dir / "choice.md"
            links_path = choice_dir / "links.yml"
            decision_path = choice_dir / "decision.md"
            choice_text = context.documents.text(choice_path) if choice_path.is_file() else ""
            frontmatter = read_frontmatter(choice_text)
            links = (
                context.documents.yaml(links_path, loader_contract="unique-v1")
                if links_path.is_file()
                else {}
            )
            if not isinstance(links, Mapping):
                links = {}
            related = tuple(
                sorted(
                    {
                        str(item.get("proposal") or "")
                        for item in links.get("related_proposals", ())
                        if isinstance(item, Mapping) and str(item.get("proposal") or "")
                    }
                )
            )
            sections = _topology_sections(related, coverage_sections_by_proposal)
            decision_text = (
                context.documents.text(decision_path) if decision_path.is_file() else ""
            )
            selected = read_markdown_section(decision_text, "Selected Option")
            choice_id = str(
                frontmatter.get("choice_id") or "-".join(choice_dir.name.split("-", 2)[:2])
            )
            record = {
                "kind": "choice",
                "id": choice_id,
                "title": str(frontmatter.get("title") or read_title(choice_text) or choice_id),
                "status": "decided" if selected else str(frontmatter.get("status") or "open"),
                "selected_option": selected,
                "proposals": list(related),
                "source_path": choice_path.relative_to(self.root).as_posix(),
            }
            if sections:
                for section_id in sections:
                    by_section.setdefault(section_id, []).append(record)
            elif related:
                diagnostics.append(
                    {
                        "code": "VERTICAL_MEMORY_UNMAPPED_CHOICE",
                        "severity": "warning",
                        "message": f"Choice `{choice_id}` has no declared vertical section.",
                        "suggested_command": f"p2p choice show {choice_id}",
                    }
                )
        return by_section, diagnostics


class VerticalMemoryImpactClassifier:
    def classify(
        self,
        changed_paths: Sequence[str],
        *,
        prior_view: VerticalProjectMemoryView | None = None,
        typed_section_ids: Sequence[str] = (),
        typed_proposal_id: str = "",
    ) -> VerticalMemoryImpact:
        scopes: set[str] = set()
        sections: set[str] = set()
        proposal_ids: set[str] = {typed_proposal_id} if typed_proposal_id else set()
        reasons: set[str] = set()
        full = False
        prior_membership = _coverage_sections_from_view(prior_view) if prior_view else {}
        for raw in sorted(set(changed_paths)):
            path = raw.replace("\\", "/")
            if path.endswith(("/vertical.yml", "/vertical.lock.yml")) or "/verticals/" in path:
                scopes.add("vertical")
                reasons.add("vertical_contract_changed")
                full = True
            elif path.endswith("/definition.yml") or path.endswith("/questions.yml"):
                scopes.add("definition")
                reasons.add("project_definition_changed")
                if typed_section_ids:
                    sections.update(typed_section_ids)
                else:
                    full = True
            elif path.endswith("/vertical-coverage.yml"):
                scopes.add("coverage")
                reasons.add("declared_coverage_changed")
                proposal_id = _proposal_id_from_path(path)
                if proposal_id:
                    proposal_ids.add(proposal_id)
                    sections.update(prior_membership.get(proposal_id, ()))
                else:
                    full = True
            elif "/proposals/" in path:
                if path.endswith(("/related-proposals.yml", "/conflict-analysis.yml", "/impact-map.yml")):
                    scopes.add("topology")
                    reasons.add("proposal_topology_changed")
                    full = True
                else:
                    scopes.add("proposals")
                    reasons.add("proposal_or_decision_changed")
                    proposal_id = _proposal_id_from_path(path)
                    if proposal_id:
                        proposal_ids.add(proposal_id)
                        sections.update(prior_membership.get(proposal_id, ()))
                    else:
                        full = True
            elif "/choices/" in path or path.endswith("/conflicts.yml"):
                scopes.add("topology")
                reasons.add("choice_or_conflict_changed")
                full = True
            elif any(
                token in path
                for token in (
                    "/registries/",
                    "/vertical-memory/",
                    "/outputs/",
                    "/changes/",
                    "/work/",
                    "outputs/",
                )
            ):
                reasons.add("non_authoritative_derived_or_delivery_change")
            else:
                scopes.add("unknown")
                reasons.add("unclassified_source_change")
                full = True
        return VerticalMemoryImpact(
            scopes=tuple(sorted(scopes)),
            section_ids=tuple(sorted(sections)),
            aggregate_changed=bool(changed_paths),
            full_rebuild=full,
            reasons=tuple(sorted(reasons)),
            proposal_ids=tuple(sorted(proposal_ids)),
        )


class VerticalProjectMemoryService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        builder: VerticalProjectMemoryBuilder,
        atomic_writer: AtomicMutationWriter | None = None,
    ) -> None:
        self.root = root.resolve()
        self.p2p_dir = p2p_dir.resolve()
        self.builder = builder
        self.atomic_writer = atomic_writer or AtomicMutationWriter(
            root=self.root,
            p2p_dir=self.p2p_dir,
        )
        self.impact_classifier = VerticalMemoryImpactClassifier()

    def status(
        self,
        *,
        read_context: WorkspaceReadContext | None = None,
    ) -> VerticalMemoryStatus:
        context = read_context or WorkspaceReadContext(self.root)
        manifest_path = self.root / _MANIFEST_PATH
        display = Path(_MANIFEST_PATH)
        try:
            manifest_document = context.documents.capture(manifest_path)
        except ValueError as exc:
            return VerticalMemoryStatus("invalid", str(exc), display)
        if not manifest_document.exists:
            return VerticalMemoryStatus("missing", "Vertical project memory is not materialized.", display)
        try:
            manifest = _parse_manifest(context.documents.bytes(manifest_path))
        except ValueError as exc:
            state = "unsupported" if "Unsupported" in str(exc) else "invalid"
            return VerticalMemoryStatus(state, str(exc), display)
        catalog = self.builder._source_catalog(context)
        current_fingerprint, current_scopes = _source_fingerprints(catalog)
        current_records = {
            path: hashlib.sha256(content).hexdigest() for path, content in catalog
        }
        recorded_records = manifest["source_records"]
        assert isinstance(recorded_records, Mapping)
        changed_paths = tuple(
            sorted(
                path
                for path in set(map(str, recorded_records)) | set(current_records)
                if str(recorded_records.get(path) or "") != current_records.get(path, "")
            )
        )
        outputs = manifest["outputs"]
        assert isinstance(outputs, Mapping)
        for path, metadata in outputs.items():
            target = self.root / str(path)
            try:
                document = context.documents.capture(target)
            except ValueError as exc:
                return _status_from_manifest(
                    manifest,
                    state="invalid",
                    reason=str(exc),
                    current_fingerprint=current_fingerprint,
                    changed_paths=changed_paths,
                )
            if not document.exists:
                return _status_from_manifest(
                    manifest,
                    state="invalid",
                    reason=f"Vertical-memory output is missing or unsafe: {path}",
                    current_fingerprint=current_fingerprint,
                    changed_paths=changed_paths,
                )
            expected = str(metadata.get("sha256") or "") if isinstance(metadata, Mapping) else ""
            if document.physical_sha256 != expected:
                return _status_from_manifest(
                    manifest,
                    state="invalid",
                    reason=f"Vertical-memory output digest mismatch: {path}",
                    current_fingerprint=current_fingerprint,
                    changed_paths=changed_paths,
                )
        try:
            project = load_yaml_mapping(context.documents.bytes(self.root / _PROJECT_PATH))
            _validate_project_aggregate(project, manifest)
        except (OSError, ValueError) as exc:
            return _status_from_manifest(
                manifest,
                state="invalid",
                reason=str(exc),
                current_fingerprint=current_fingerprint,
                changed_paths=changed_paths,
            )
        recorded_scopes = manifest.get("source_scopes")
        changed_scopes = tuple(
            sorted(
                key
                for key, value in current_scopes.items()
                if not isinstance(recorded_scopes, Mapping)
                or str(recorded_scopes.get(key) or "") != value
            )
        )
        if current_fingerprint != manifest["source_fingerprint_sha256"]:
            return _status_from_manifest(
                manifest,
                state="stale",
                reason="Canonical vertical-memory sources changed after refresh.",
                current_fingerprint=current_fingerprint,
                changed_scopes=changed_scopes,
                changed_paths=changed_paths,
            )
        return _status_from_manifest(
            manifest,
            state="current",
            reason="Vertical project memory is current.",
            current_fingerprint=current_fingerprint,
            changed_paths=(),
        )

    def fast_status(
        self,
        *,
        read_context: WorkspaceReadContext | None = None,
    ) -> VerticalMemoryStatus:
        context = read_context or WorkspaceReadContext(self.root)
        display = Path(_MANIFEST_PATH)
        try:
            manifest_document = context.documents.capture(self.root / _MANIFEST_PATH)
        except ValueError as exc:
            return VerticalMemoryStatus("invalid", str(exc), display)
        if not manifest_document.exists:
            return VerticalMemoryStatus(
                "missing",
                "Vertical project memory is not materialized.",
                display,
            )
        try:
            manifest = _parse_manifest(
                context.documents.bytes(self.root / _MANIFEST_PATH)
            )
        except ValueError as exc:
            state = "unsupported" if "Unsupported" in str(exc) else "invalid"
            return VerticalMemoryStatus(state, str(exc), display)
        outputs = manifest["outputs"]
        assert isinstance(outputs, Mapping)
        for path, metadata in outputs.items():
            try:
                document = context.documents.capture(self.root / str(path))
            except ValueError as exc:
                return _status_from_manifest(
                    manifest,
                    state="invalid",
                    reason=str(exc),
                    current_fingerprint="",
                )
            expected = (
                str(metadata.get("sha256") or "")
                if isinstance(metadata, Mapping)
                else ""
            )
            if not document.exists or document.physical_sha256 != expected:
                return _status_from_manifest(
                    manifest,
                    state="invalid",
                    reason=f"Vertical-memory output digest mismatch: {path}",
                    current_fingerprint="",
                )
        return _status_from_manifest(
            manifest,
            state="current",
            reason=(
                "Vertical-memory manifest and outputs are intact; canonical "
                "sources were not rehashed."
            ),
            current_fingerprint="",
            changed_paths=(),
        )

    def build_full(
        self,
        read_context: WorkspaceReadContext | None = None,
    ) -> VerticalMemoryCandidate:
        return self.builder.build_full(read_context or WorkspaceReadContext(self.root))

    def build_incremental(
        self,
        changed_paths: Sequence[str],
        *,
        typed_section_ids: Sequence[str] = (),
        typed_proposal_id: str = "",
    ) -> tuple[VerticalMemoryCandidate, VerticalMemoryImpact]:
        status = self.status()
        if status.state not in {"current", "stale"}:
            impact = self.impact_classifier.classify(
                changed_paths,
                prior_view=None,
                typed_section_ids=typed_section_ids,
                typed_proposal_id=typed_proposal_id,
            )
            return self.build_full(), replace(
                impact,
                full_rebuild=True,
                reasons=tuple(sorted({*impact.reasons, "prior_generation_unavailable"})),
            )
        prior = self._read_materialized_view()
        impact = self.impact_classifier.classify(
            changed_paths,
            prior_view=prior,
            typed_section_ids=typed_section_ids,
            typed_proposal_id=typed_proposal_id,
        )
        if impact.full_rebuild:
            return self.build_full(), replace(
                impact,
                full_rebuild=True,
                reasons=tuple(sorted({*impact.reasons, "incremental_scope_unproven"})),
            )
        reused = {
            section.section_id: (
                self.root / vertical_memory_section_path(section.section_id)
            ).read_bytes()
            for section in prior.sections
        }
        if impact.proposal_ids:
            return self.builder.build_incremental(
                WorkspaceReadContext(self.root),
                prior_view=prior,
                impact=impact,
                reused_sections=reused,
            )
        if impact.section_ids and set(impact.scopes) <= {"definition"}:
            return self.builder.build_section_incremental(
                WorkspaceReadContext(self.root),
                prior_view=prior,
                impact=impact,
                reused_sections=reused,
            )
        return self.build_full(), replace(
            impact,
            full_rebuild=True,
            reasons=tuple(sorted({*impact.reasons, "incremental_scope_unproven"})),
        )

    def refresh(self) -> VerticalMemoryOperationResult:
        last_error = ""
        for _attempt in range(2):
            candidate = self.build_full()
            try:
                return self._commit_candidate(candidate, mode="full")
            except ValueError as exc:
                last_error = str(exc)
                if "source changed" not in last_error.lower():
                    break
        raise ValueError(last_error or "Vertical project-memory refresh failed")

    def refresh_incremental(
        self,
        changed_paths: Sequence[str],
        *,
        typed_section_ids: Sequence[str] = (),
        typed_proposal_id: str = "",
    ) -> DerivedUpdateResult:
        status = self.status()
        if status.state not in {"current", "stale"}:
            return DerivedUpdateResult(
                state="not_applicable",
                target="vertical_project_memory",
                reason=f"Prior vertical project memory is {status.state}; explicit full refresh required.",
            )
        manifest = self._manifest_optional()
        if manifest is None:
            return DerivedUpdateResult(
                state="not_applicable",
                target="vertical_project_memory",
                reason="Prior vertical project-memory manifest is unavailable.",
            )
        actual_changed = self._changed_source_paths(manifest)
        declared_changed = {str(path).replace("\\", "/") for path in changed_paths}
        if not actual_changed.issubset(declared_changed):
            unexpected = ", ".join(sorted(actual_changed - declared_changed))
            return DerivedUpdateResult(
                state="stale",
                target="vertical_project_memory",
                reason=f"Additional canonical source drift requires explicit refresh: {unexpected}",
            )
        try:
            candidate, impact = self.build_incremental(
                changed_paths,
                typed_section_ids=typed_section_ids,
                typed_proposal_id=typed_proposal_id,
            )
        except ValueError as exc:
            return DerivedUpdateResult(
                state="failed",
                target="vertical_project_memory",
                reason=str(exc),
            )
        if impact.full_rebuild:
            return DerivedUpdateResult(
                state="stale",
                target="vertical_project_memory",
                reason="Impact requires an explicit full project refresh: " + ", ".join(impact.reasons),
                affected_sections=impact.section_ids,
            )
        try:
            result = self._commit_candidate(
                candidate,
                mode="incremental",
                affected_sections=impact.section_ids,
            )
        except ValueError as exc:
            return DerivedUpdateResult(
                state="failed",
                target="vertical_project_memory",
                reason=str(exc),
                affected_sections=impact.section_ids,
            )
        return DerivedUpdateResult(
            state="unchanged" if result.status == "unchanged" else "updated",
            target="vertical_project_memory",
            changed_paths=result.changed_paths,
            affected_sections=impact.section_ids,
        )

    def _commit_candidate(
        self,
        candidate: VerticalMemoryCandidate,
        *,
        mode: str,
        affected_sections: Sequence[str] = (),
    ) -> VerticalMemoryOperationResult:
            live_manifest = self._manifest_optional()
            prior_owned = set(live_manifest.get("owned_paths", ())) if live_manifest else set()
            candidates: dict[str, bytes | None] = dict(candidate.candidates)
            for stale in sorted(prior_owned - set(candidate.owned_paths)):
                validate_vertical_memory_owned_path(str(stale))
                candidates[str(stale)] = None
            if all(
                content is not None
                and (self.root / path).is_file()
                and (self.root / path).read_bytes() == content
                for path, content in candidates.items()
            ):
                return VerticalMemoryOperationResult(
                    status="unchanged",
                    mode="no_op",
                    changed_paths=(),
                    source_fingerprint_sha256=candidate.view.source_fingerprint_sha256,
                    affected_sections=tuple(sorted(affected_sections)),
                )
            source_map = {
                item.path: item
                for item in candidate.source_preconditions
            }
            for path in candidates:
                target = self.root / path
                source_map[path] = source_precondition(
                    path,
                    target.read_bytes() if target.is_file() else None,
                )
            sources = tuple(source_map[path] for path in sorted(source_map))
            token = MutationPreviewService.token(
                operation_id="vertical-project-memory-refresh",
                targets=tuple(candidates),
                sources=sources,
                candidate_semantics={
                    path: {"delete": True}
                    if content is None
                    else hashlib.sha256(content).hexdigest()
                    for path, content in candidates.items()
                },
            )

            def validate_candidate(view) -> None:
                manifest = _parse_manifest(view.read_bytes(_MANIFEST_PATH))
                outputs = manifest["outputs"]
                assert isinstance(outputs, Mapping)
                for path, metadata in outputs.items():
                    content = view.read_bytes(str(path))
                    expected = str(metadata.get("sha256") or "") if isinstance(metadata, Mapping) else ""
                    if hashlib.sha256(content).hexdigest() != expected:
                        raise ValueError(f"Vertical-memory candidate digest mismatch: {path}")
                project = load_yaml_mapping(view.read_bytes(_PROJECT_PATH))
                project_data = project.get("vertical_project_memory")
                if not isinstance(project_data, Mapping):
                    raise ValueError("Vertical-memory project candidate is invalid")
                view.assert_owned_reads_used_candidates()

            result = self.atomic_writer.apply(
                operation_id="vertical-project-memory-refresh",
                candidates=candidates,
                sources=sources,
                preview_token=token,
                actor="p2p-project-refresh",
                candidate_validator=validate_candidate,
            )
            if result.status == "applied":
                self._cleanup_empty_section_directories()
                return VerticalMemoryOperationResult(
                    status="applied",
                    mode=mode,
                    changed_paths=result.changed_paths,
                    source_fingerprint_sha256=candidate.view.source_fingerprint_sha256,
                    affected_sections=tuple(sorted(affected_sections)),
                )
            raise ValueError(result.message or result.status)

    def _changed_source_paths(self, manifest: Mapping[str, object]) -> set[str]:
        recorded = manifest.get("source_records")
        if not isinstance(recorded, Mapping):
            return {"manifest_without_source_records"}
        context = WorkspaceReadContext(self.root)
        current = {
            path: hashlib.sha256(content).hexdigest()
            for path, content in self.builder._source_catalog(context)
        }
        paths = set(str(path) for path in recorded) | set(current)
        return {
            path
            for path in paths
            if str(recorded.get(path) or "") != current.get(path, "")
        }

    def view(
        self,
        *,
        allow_fallback: bool = True,
        allow_stale: bool = False,
        read_context: WorkspaceReadContext | None = None,
    ) -> VerticalProjectMemoryView:
        context = read_context or WorkspaceReadContext(self.root)
        status = self.status(read_context=context)
        if status.current or (allow_stale and status.state == "stale"):
            view = self._read_materialized_view(read_context=context)
            return replace(view, source="materialized" if status.current else "stale_last_known")
        if allow_fallback:
            context.record_canonical_fallback("vertical_project_memory")
            return replace(self.build_full(context).view, source="canonical_fallback")
        raise ValueError(f"Vertical project memory is {status.state}: {status.reason}")

    def show(
        self,
        *,
        section_id: str | None = None,
        include_history: bool = False,
        limit: int = 20,
        cursor: str = "",
    ) -> VerticalMemoryAggregate | VerticalMemoryPage:
        view = self.view()
        _validate_page_limit(limit)
        if section_id is None:
            values = sorted(
                (dict(item) for item in view.unmapped_active_proposals),
                key=_vertical_memory_item_key,
            )
            page, next_cursor = _vertical_memory_page_values(
                values,
                limit=limit,
                cursor=cursor,
                source_fingerprint=view.source_fingerprint_sha256,
                section_id="__aggregate__",
                include_history=False,
            )
            return VerticalMemoryAggregate(
                vertical_id=view.vertical_id,
                vertical_version=view.vertical_version,
                source=view.source,
                source_fingerprint_sha256=view.source_fingerprint_sha256,
                sections=tuple(
                    {
                        "id": item.section_id,
                        "title": item.title,
                        "required": item.required,
                        "priority": item.priority,
                        "definition_status": str(
                            item.definition.get("status") or "not_initialized"
                        ),
                        "active_contributions": len(item.active_contributions),
                        "historical_contributions": len(item.historical_contributions),
                        "questions": len(item.questions),
                        "conflicts": len(item.conflicts),
                    }
                    for item in view.sections
                ),
                unmapped_active_proposals=tuple(page),
                total=len(values),
                returned=len(page),
                truncated=bool(next_cursor),
                next_cursor=next_cursor,
                diagnostics_count=len(view.diagnostics),
            )
        section = next((item for item in view.sections if item.section_id == section_id), None)
        if section is None:
            raise ValueError(f"Unknown vertical-memory section: {section_id}")
        values = [item.to_dict() for item in section.active_contributions]
        if include_history:
            values.extend(item.to_dict() for item in section.historical_contributions)
        values.sort(key=lambda item: (str(item.get("proposal_id") or ""), str(item.get("id") or "")))
        page, next_cursor = _vertical_memory_page_values(
            values,
            limit=limit,
            cursor=cursor,
            source_fingerprint=view.source_fingerprint_sha256,
            section_id=section_id,
            include_history=include_history,
        )
        return VerticalMemoryPage(
            section_id=section_id,
            items=tuple(page),
            total=len(values),
            returned=len(page),
            truncated=bool(next_cursor),
            next_cursor=next_cursor,
        )

    def _manifest_optional(self) -> Mapping[str, object] | None:
        path = self.root / _MANIFEST_PATH
        if not path.is_file():
            return None
        try:
            return _parse_manifest(path.read_bytes())
        except ValueError:
            return None

    def _read_materialized_view(
        self,
        *,
        read_context: WorkspaceReadContext | None = None,
    ) -> VerticalProjectMemoryView:
        context = read_context or WorkspaceReadContext(self.root)
        project = load_yaml_mapping(context.documents.bytes(self.root / _PROJECT_PATH))
        data = project.get("vertical_project_memory")
        if not isinstance(data, Mapping):
            raise ValueError("Invalid materialized vertical-memory project")
        if int(data.get("schema_version") or 0) != VERTICAL_MEMORY_PROJECT_VERSION:
            raise ValueError("Unsupported vertical-memory project schema version")
        vertical = data.get("vertical")
        if not isinstance(vertical, Mapping):
            raise ValueError("Invalid materialized vertical-memory vertical")
        sections: list[VerticalMemorySection] = []
        for item in data.get("sections", ()):
            if not isinstance(item, Mapping):
                raise ValueError("Invalid materialized vertical-memory section reference")
            path = str(item.get("path") or "")
            validate_vertical_memory_owned_path(path)
            sections.append(
                _section_from_payload(
                    load_yaml_mapping(context.documents.bytes(self.root / path))
                )
            )
        view = VerticalProjectMemoryView(
            vertical_id=str(vertical.get("id") or ""),
            vertical_version=str(vertical.get("version") or ""),
            vertical_checksum=str(vertical.get("checksum") or ""),
            sections=tuple(sections),
            unmapped_active_proposals=tuple(
                dict(item) for item in data.get("unmapped_active_proposals", ()) if isinstance(item, Mapping)
            ),
            diagnostics=tuple(
                dict(item) for item in data.get("diagnostics", ()) if isinstance(item, Mapping)
            ),
            source_fingerprint_sha256=str(data.get("source_fingerprint_sha256") or ""),
            profile=str(data.get("profile") or "default"),
            modules=tuple(str(item) for item in data.get("modules", ())),
            fallback_used=bool(data.get("fallback_used", False)),
            vertical_source=str(data.get("vertical_source") or ""),
            vertical_lock_checksum=str(data.get("vertical_lock_checksum") or ""),
            definition_exists=bool(data.get("definition_exists", False)),
            definition_valid=bool(data.get("definition_valid", False)),
            source="materialized",
        )
        validate_vertical_memory_view(view)
        return view

    def _cleanup_empty_section_directories(self) -> None:
        sections = self.root / VERTICAL_MEMORY_ROOT / "sections"
        if sections.exists():
            try:
                sections.rmdir()
            except OSError:
                pass


def _is_vertical_memory_source(path: Path, domain: str) -> bool:
    if domain == "choices":
        return path.name in {"choice.md", "options.yml", "decision.md", "links.yml"}
    return path.name in {
        "proposal.md",
        "decision.md",
        "decision-events.yml",
        "vertical-coverage.yml",
        "related-proposals.yml",
        "conflict-analysis.yml",
        "contributions.yml",
        "impact-map.yml",
        "suggested-scope.md",
        "risks.md",
    }


def _source_fingerprints(
    catalog: tuple[tuple[str, bytes], ...],
) -> tuple[str, dict[str, str]]:
    records = [(path, hashlib.sha256(content).hexdigest()) for path, content in catalog]
    scopes: dict[str, list[tuple[str, str]]] = {
        "vertical": [],
        "definition": [],
        "questions": [],
        "proposals": [],
        "decisions": [],
        "coverage": [],
        "relations_conflicts_choices": [],
    }
    for record in records:
        path = record[0]
        if path.endswith(("vertical.yml", "vertical.lock.yml")) or "/verticals/" in path:
            scopes["vertical"].append(record)
        if path.endswith("definition.yml"):
            scopes["definition"].append(record)
        if path.endswith("questions.yml"):
            scopes["questions"].append(record)
        if "/proposals/" in path and path.endswith(
            ("proposal.md", "suggested-scope.md", "risks.md", "contributions.yml")
        ):
            scopes["proposals"].append(record)
        if path.endswith(("decision.md", "decision-events.yml")):
            scopes["decisions"].append(record)
        if path.endswith("vertical-coverage.yml"):
            scopes["coverage"].append(record)
        if any(
            token in path
            for token in (
                "related-proposals",
                "conflict",
                "/choices/",
                "impact-map",
            )
        ):
            scopes["relations_conflicts_choices"].append(record)
    return semantic_sha256(records), {
        scope: semantic_sha256(values) for scope, values in sorted(scopes.items())
    }


def _contribution(
    *,
    proposal_id: str,
    title: str,
    section_id: str,
    lifecycle: ProposalDecisionLifecycleView,
    coverage_rationale: str,
    proposal_path: Path,
    proposal_text: str,
) -> VerticalMemoryContribution:
    event = lifecycle.current_event
    authority_id = lifecycle.head_event_id or lifecycle.decision_semantic_sha256 or proposal_id
    contribution_id = "VMC-" + semantic_sha256(
        {
            "policy": VERTICAL_MEMORY_IDENTITY_POLICY,
            "proposal_id": proposal_id,
            "authority_id": authority_id,
        }
    )[:24]
    evidence: list[VerticalMemoryEvidence] = []
    source_sha = hashlib.sha256(proposal_text.encode("utf-8")).hexdigest()
    for heading in ("Problem", "Goals", "Non-Goals", "Proposal", "Acceptance Criteria"):
        fragment = read_markdown_section(proposal_text, heading)
        if not fragment:
            continue
        truncated = len(fragment) > _FRAGMENT_LIMIT
        bounded = fragment[:_FRAGMENT_LIMIT]
        evidence.append(
            VerticalMemoryEvidence(
                evidence_id="VME-" + semantic_sha256(
                    {
                        "contribution": contribution_id,
                        "kind": heading.lower().replace(" ", "_"),
                        "fragment_sha256": hashlib.sha256(fragment.encode("utf-8")).hexdigest(),
                    }
                )[:24],
                source_path=proposal_path.as_posix(),
                source_sha256=source_sha,
                fragment=bounded,
                fragment_kind=heading.lower().replace(" ", "_"),
                truncated=truncated,
            )
        )
    return VerticalMemoryContribution(
        contribution_id=contribution_id,
        proposal_id=proposal_id,
        title=title,
        section_id=section_id,
        authority=lifecycle.authority_resolution.value,
        activation="active" if lifecycle.active_projection else "historical",
        effective_state=lifecycle.effective_state.value,
        head_event_id=lifecycle.head_event_id or "",
        head_event_type=lifecycle.head_event_type.value if lifecycle.head_event_type else "",
        rationale=event.rationale if event is not None else "",
        constraints=tuple(item.text for item in event.conditions) if event is not None else (),
        applicability=section_id,
        coverage_rationale=coverage_rationale,
        source_path=proposal_path.as_posix(),
        proposal_semantic_sha256=lifecycle.proposal_semantic_sha256 or "",
        decision_semantic_sha256=lifecycle.decision_semantic_sha256 or "",
        lineage=lifecycle.lineage.to_dict(),
        evidence=tuple(evidence),
    )


def _definition_payload(
    value: object | None,
    *,
    required_field_ids: tuple[str, ...] = (),
) -> Mapping[str, object]:
    if value is None:
        return {
            "status": "missing",
            "fields": {},
            "required_field_ids": list(required_field_ids),
            "missing_required_fields": [],
            "assumptions": [],
            "open_questions": [],
            "blockers": [],
        }
    return {
        "status": str(getattr(value, "status", "missing")),
        "fields": {
            key: {
                "value": item.value,
                "source": item.source,
            }
            for key, item in sorted(getattr(value, "fields", {}).items())
        },
        "required_field_ids": list(required_field_ids),
        "missing_required_fields": list(getattr(value, "missing_required_fields", ())),
        "assumptions": [
            {
                "id": item.assumption_id,
                "text": item.text,
                "status": item.status,
                "field_id": item.field_id,
            }
            for item in sorted(getattr(value, "assumptions", ()), key=lambda item: item.assumption_id)
        ],
        "open_questions": [
            {
                "id": item.question_id,
                "question": item.question,
                "status": item.status,
                "field_id": item.field_id,
            }
            for item in sorted(getattr(value, "open_questions", ()), key=lambda item: item.question_id)
        ],
        "blockers": [
            {"id": item.blocker_id, "text": item.text, "status": item.status}
            for item in sorted(getattr(value, "blockers", ()), key=lambda item: item.blocker_id)
        ],
    }


def _topology_sections(
    proposal_ids: Sequence[str],
    coverage_sections_by_proposal: Mapping[str, tuple[str, ...]],
) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                section_id
                for proposal_id in proposal_ids
                for section_id in coverage_sections_by_proposal.get(proposal_id, ())
            }
        )
    )


def _coverage_sections_from_view(
    view: VerticalProjectMemoryView,
) -> dict[str, tuple[str, ...]]:
    values: dict[str, set[str]] = {}
    for section in view.sections:
        for contribution in (
            *section.active_contributions,
            *section.historical_contributions,
        ):
            values.setdefault(contribution.proposal_id, set()).add(section.section_id)
    return {
        proposal_id: tuple(sorted(section_ids))
        for proposal_id, section_ids in values.items()
    }


def _proposal_id_from_path(path: str) -> str:
    match = re.search(r"(?:^|/)proposals/(PROP-\d+)(?:-|/)", path)
    return match.group(1) if match else ""


def _clean_title(title: str, proposal_id: str) -> str:
    return re.sub(rf"^{re.escape(proposal_id)}\s*[-:]?\s*", "", title, flags=re.IGNORECASE) or title


def _parse_manifest(content: bytes) -> dict[str, object]:
    payload = load_yaml_mapping(content)
    data = payload.get("vertical_project_memory_manifest")
    if not isinstance(data, Mapping):
        raise ValueError("Invalid vertical-memory manifest")
    if int(data.get("manifest_version") or 0) != VERTICAL_MEMORY_MANIFEST_VERSION:
        raise ValueError(f"Unsupported vertical-memory manifest version: {data.get('manifest_version')}")
    if data.get("generator_contract_version") != VERTICAL_MEMORY_GENERATOR_CONTRACT:
        raise ValueError("Unsupported vertical-memory generator contract")
    if data.get("source_catalog_policy_version") != VERTICAL_MEMORY_SOURCE_POLICY:
        raise ValueError("Unsupported vertical-memory source policy")
    if data.get("identity_policy_version") != VERTICAL_MEMORY_IDENTITY_POLICY:
        raise ValueError("Unsupported vertical-memory identity policy")
    outputs = data.get("outputs")
    owned = data.get("owned_paths")
    source_records = data.get("source_records")
    source_scopes = data.get("source_scopes")
    vertical = data.get("vertical")
    if (
        not isinstance(outputs, Mapping)
        or not isinstance(owned, list)
        or not isinstance(source_records, Mapping)
        or not isinstance(source_scopes, Mapping)
        or not isinstance(vertical, Mapping)
    ):
        raise ValueError("Invalid vertical-memory manifest collections")
    if data.get("generation_mode") != "deterministic":
        raise ValueError("Unsupported vertical-memory generation mode")
    source_fingerprint = str(data.get("source_fingerprint_sha256") or "")
    if not re.fullmatch(r"[0-9a-f]{64}", source_fingerprint):
        raise ValueError("Invalid vertical-memory source fingerprint")
    if not str(vertical.get("id") or "") or not str(vertical.get("version") or ""):
        raise ValueError("Invalid vertical-memory vertical identity")
    if not re.fullmatch(r"[0-9a-f]{64}", str(vertical.get("checksum") or "")):
        raise ValueError("Invalid vertical-memory vertical checksum")
    if len(owned) != len(set(map(str, owned))):
        raise ValueError("Duplicate vertical-memory owned path")
    for path in owned:
        validate_vertical_memory_owned_path(str(path))
    if set(str(path) for path in owned) != {*map(str, outputs), _MANIFEST_PATH}:
        raise ValueError("Vertical-memory manifest owned paths and outputs disagree")
    if _PROJECT_PATH not in outputs or _MANIFEST_PATH in outputs:
        raise ValueError("Vertical-memory manifest output set is incomplete")
    for path, metadata in outputs.items():
        validate_vertical_memory_owned_path(str(path))
        if not isinstance(metadata, Mapping) or not re.fullmatch(
            r"[0-9a-f]{64}", str(metadata.get("sha256") or "")
        ):
            raise ValueError(f"Invalid vertical-memory output metadata: {path}")
    for path, digest in source_records.items():
        validate_vertical_memory_owned_source(str(path))
        if str(path).startswith(f"{VERTICAL_MEMORY_ROOT}/"):
            raise ValueError("Vertical-memory source catalog includes its own output")
        if not re.fullmatch(r"[0-9a-f]{64}", str(digest or "")):
            raise ValueError(f"Invalid vertical-memory source record: {path}")
    expected_scopes = {
        "coverage",
        "decisions",
        "definition",
        "proposals",
        "questions",
        "relations_conflicts_choices",
        "vertical",
    }
    if set(map(str, source_scopes)) != expected_scopes or any(
        not re.fullmatch(r"[0-9a-f]{64}", str(value or ""))
        for value in source_scopes.values()
    ):
        raise ValueError("Invalid vertical-memory source scopes")
    section_count = data.get("section_count")
    if isinstance(section_count, bool) or not isinstance(section_count, int) or section_count < 0:
        raise ValueError("Invalid vertical-memory section count")
    section_outputs = [
        path
        for path in outputs
        if str(path).startswith(f"{VERTICAL_MEMORY_ROOT}/sections/")
    ]
    if len(section_outputs) != section_count:
        raise ValueError("Vertical-memory section count does not match outputs")
    return dict(data)


def _validate_project_aggregate(
    payload: Mapping[str, object],
    manifest: Mapping[str, object],
) -> None:
    data = payload.get("vertical_project_memory")
    if not isinstance(data, Mapping):
        raise ValueError("Invalid vertical-memory project aggregate")
    if int(data.get("schema_version") or 0) != VERTICAL_MEMORY_PROJECT_VERSION:
        raise ValueError("Unsupported vertical-memory project schema version")
    vertical = data.get("vertical")
    manifest_vertical = manifest.get("vertical")
    if not isinstance(vertical, Mapping) or not isinstance(manifest_vertical, Mapping):
        raise ValueError("Invalid vertical-memory project vertical identity")
    if {
        "id": str(vertical.get("id") or ""),
        "version": str(vertical.get("version") or ""),
        "checksum": str(vertical.get("checksum") or ""),
    } != {
        "id": str(manifest_vertical.get("id") or ""),
        "version": str(manifest_vertical.get("version") or ""),
        "checksum": str(manifest_vertical.get("checksum") or ""),
    }:
        raise ValueError("Vertical-memory project and manifest verticals disagree")
    if data.get("source_fingerprint_sha256") != manifest.get("source_fingerprint_sha256"):
        raise ValueError("Vertical-memory project and manifest fingerprints disagree")
    sections = data.get("sections")
    outputs = manifest.get("outputs")
    if not isinstance(sections, list) or not isinstance(outputs, Mapping):
        raise ValueError("Invalid vertical-memory project section references")
    if len(sections) != int(manifest.get("section_count") or 0):
        raise ValueError("Vertical-memory project section count disagrees with manifest")
    seen: set[str] = set()
    for section in sections:
        if not isinstance(section, Mapping):
            raise ValueError("Invalid vertical-memory project section reference")
        section_id = str(section.get("id") or "")
        path = str(section.get("path") or "")
        if section_id in seen or path != vertical_memory_section_path(section_id):
            raise ValueError("Invalid vertical-memory project section identity")
        seen.add(section_id)
        metadata = outputs.get(path)
        if not isinstance(metadata, Mapping) or section.get("sha256") != metadata.get("sha256"):
            raise ValueError("Vertical-memory project section digest disagrees with manifest")


def _status_from_manifest(
    manifest: Mapping[str, object],
    *,
    state: str,
    reason: str,
    current_fingerprint: str,
    changed_scopes: tuple[str, ...] = (),
    changed_paths: tuple[str, ...] = (),
) -> VerticalMemoryStatus:
    vertical = manifest.get("vertical")
    vertical = vertical if isinstance(vertical, Mapping) else {}
    outputs = manifest.get("outputs")
    return VerticalMemoryStatus(
        state=state,
        reason=reason,
        manifest_path=Path(_MANIFEST_PATH),
        vertical_id=str(vertical.get("id") or ""),
        vertical_version=str(vertical.get("version") or ""),
        source_fingerprint_sha256=str(manifest.get("source_fingerprint_sha256") or ""),
        current_source_fingerprint_sha256=current_fingerprint,
        changed_scopes=changed_scopes,
        changed_paths=changed_paths,
        section_count=int(manifest.get("section_count") or 0),
        output_count=len(outputs) if isinstance(outputs, Mapping) else 0,
    )


def _section_from_payload(payload: Mapping[str, object]) -> VerticalMemorySection:
    data = payload.get("vertical_memory_section")
    if not isinstance(data, Mapping) or int(data.get("schema_version") or 0) != VERTICAL_MEMORY_SECTION_VERSION:
        raise ValueError("Invalid vertical-memory section payload")
    section = data.get("section")
    if not isinstance(section, Mapping):
        raise ValueError("Invalid vertical-memory section identity")
    return VerticalMemorySection(
        section_id=str(section.get("id") or ""),
        title=str(section.get("title") or ""),
        purpose=str(section.get("purpose") or ""),
        required=bool(section.get("required", False)),
        priority=int(section.get("priority") or 0),
        definition=dict(data.get("definition") or {}),
        questions=tuple(dict(item) for item in data.get("questions", ()) if isinstance(item, Mapping)),
        active_contributions=tuple(
            _contribution_from_payload(item)
            for item in data.get("active_contributions", ())
            if isinstance(item, Mapping)
        ),
        historical_contributions=tuple(
            _contribution_from_payload(item)
            for item in data.get("historical_contributions", ())
            if isinstance(item, Mapping)
        ),
        declared_questions=tuple(str(item) for item in data.get("declared_questions", ())),
        heuristic_suggestions=tuple(
            dict(item)
            for item in data.get("heuristic_suggestions", ())
            if isinstance(item, Mapping)
        ),
        conflicts=tuple(dict(item) for item in data.get("conflicts", ()) if isinstance(item, Mapping)),
        diagnostics=tuple(dict(item) for item in data.get("diagnostics", ()) if isinstance(item, Mapping)),
    )


def _contribution_from_payload(data: Mapping[str, object]) -> VerticalMemoryContribution:
    evidence = tuple(
        VerticalMemoryEvidence(
            evidence_id=str(item.get("id") or ""),
            source_path=str(item.get("source_path") or ""),
            source_sha256=str(item.get("source_sha256") or ""),
            fragment=str(item.get("fragment") or ""),
            fragment_kind=str(item.get("fragment_kind") or ""),
            truncated=bool(item.get("truncated", False)),
        )
        for item in data.get("evidence", ())
        if isinstance(item, Mapping)
    )
    return VerticalMemoryContribution(
        contribution_id=str(data.get("id") or ""),
        proposal_id=str(data.get("proposal_id") or ""),
        title=str(data.get("title") or ""),
        section_id=str(data.get("section_id") or ""),
        authority=str(data.get("authority") or ""),
        activation=str(data.get("activation") or ""),
        effective_state=str(data.get("effective_state") or ""),
        head_event_id=str(data.get("head_event_id") or ""),
        head_event_type=str(data.get("head_event_type") or ""),
        rationale=str(data.get("rationale") or ""),
        constraints=tuple(str(item) for item in data.get("constraints", ())),
        applicability=str(data.get("applicability") or ""),
        coverage_rationale=str(data.get("coverage_rationale") or ""),
        source_path=str(data.get("source_path") or ""),
        proposal_semantic_sha256=str(data.get("proposal_semantic_sha256") or ""),
        decision_semantic_sha256=str(data.get("decision_semantic_sha256") or ""),
        lineage=dict(data.get("lineage") or {}),
        evidence=evidence,
    )


def _validate_page_limit(limit: int) -> None:
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        raise ValueError("Vertical-memory limit must be between 1 and 100")


def _vertical_memory_item_key(item: Mapping[str, object]) -> tuple[str, str]:
    return str(item.get("proposal_id") or ""), str(item.get("id") or item.get("source_path") or "")


def _vertical_memory_page_values(
    values: Sequence[Mapping[str, object]],
    *,
    limit: int,
    cursor: str,
    source_fingerprint: str,
    section_id: str,
    include_history: bool,
) -> tuple[list[Mapping[str, object]], str]:
    after = _decode_cursor(
        cursor,
        source_fingerprint=source_fingerprint,
        section_id=section_id,
        include_history=include_history,
    )
    start = 0
    if after is not None:
        try:
            start = next(
                index + 1
                for index, item in enumerate(values)
                if _vertical_memory_item_key(item) == after
            )
        except StopIteration as exc:
            raise ValueError("Vertical-memory cursor boundary is no longer available") from exc
    page = list(values[start : start + limit])
    next_cursor = ""
    if start + len(page) < len(values) and page:
        next_cursor = _encode_cursor(
            source_fingerprint=source_fingerprint,
            section_id=section_id,
            include_history=include_history,
            after=_vertical_memory_item_key(page[-1]),
        )
    return page, next_cursor


def _encode_cursor(
    *,
    source_fingerprint: str,
    section_id: str,
    include_history: bool,
    after: tuple[str, str],
) -> str:
    payload = json.dumps(
        {
            "policy": VERTICAL_MEMORY_CURSOR_POLICY_VERSION,
            "source_fingerprint_sha256": source_fingerprint,
            "section_id": section_id,
            "include_history": include_history,
            "after": list(after),
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _decode_cursor(
    cursor: str,
    *,
    source_fingerprint: str,
    section_id: str,
    include_history: bool,
) -> tuple[str, str] | None:
    if not cursor:
        return None
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        payload = json.loads(base64.b64decode(padded, altchars=b"-_", validate=True))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid vertical-memory cursor") from exc
    if not isinstance(payload, dict):
        raise ValueError("Invalid vertical-memory cursor")
    after = payload.get("after")
    if (
        payload.get("policy") != VERTICAL_MEMORY_CURSOR_POLICY_VERSION
        or payload.get("source_fingerprint_sha256") != source_fingerprint
        or payload.get("section_id") != section_id
        or payload.get("include_history") is not include_history
        or not isinstance(after, list)
        or len(after) != 2
        or not all(isinstance(item, str) for item in after)
    ):
        raise ValueError("Vertical-memory cursor does not match this result set")
    return after[0], after[1]
