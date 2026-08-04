from __future__ import annotations

import hashlib
import fnmatch
import re
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Any

from p2p_engine.core.derived_freshness import (
    DERIVED_FRESHNESS_GRAPH_VERSION,
    DerivedFreshnessStatus,
    FreshnessNode,
    FreshnessNodeDefinition,
    FreshnessRebuildAction,
)
from p2p_engine.core.mutation_preview import semantic_sha256
from p2p_engine.foundation.yaml_loaders import load_yaml
from p2p_engine.services.lifecycle_authority import (
    PROPOSAL_LIFECYCLE_AUTHORITY_POLICY_VERSION,
    is_active_project_projection,
)
from p2p_engine.services.proposal_decision_ledger import (
    DECISION_SEMANTICS_POLICY_VERSION,
    EVENT_SCHEMA_VERSION,
    LEDGER_CONTRACT_VERSION,
    PROPOSAL_SEMANTICS_POLICY_VERSION,
)
from p2p_engine.services.registries import REGISTRY_DEFINITIONS
from p2p_engine.services.software_spec import SOFTWARE_SPEC_REQUIRED_FILES


REGISTRY_OUTPUT_PATTERNS = tuple(
    f".p2p/registries/{definition['filename']}"
    for definition in REGISTRY_DEFINITIONS.values()
)
SOFTWARE_SPEC_OUTPUT_PATTERNS = tuple(
    f".p2p/outputs/software-spec/*/{filename}"
    for filename in SOFTWARE_SPEC_REQUIRED_FILES
)


NODE_CATALOG: tuple[FreshnessNodeDefinition, ...] = (
    FreshnessNodeDefinition("canonical_sources", (), "canonical", "none", "", ()),
    FreshnessNodeDefinition("registries", ("canonical_sources",), "RegistryService", "deterministic", "p2p registry refresh", REGISTRY_OUTPUT_PATTERNS),
    FreshnessNodeDefinition("vertical_project_memory", ("canonical_sources",), "VerticalProjectMemoryService", "deterministic", "p2p project refresh", (".p2p/project/vertical-memory/**/*.yml",), source_classes=("project_definition", "project_questions", "accepted_proposals", "decision_sources", "declared_vertical_coverage"), source_patterns=(".p2p/project/vertical.yml", ".p2p/project/vertical.lock.yml", ".p2p/project/definition.yml", ".p2p/project/questions.yml", ".p2p/project/conflicts.yml", ".p2p/proposals/**/*", ".p2p/choices/**/*", ".p2p/verticals/**/*")),
    FreshnessNodeDefinition("project_projections", ("vertical_project_memory", "registries"), "ProjectStateService", "deterministic", "p2p project refresh", (".p2p/project/overview.md", ".p2p/project/problem.md", ".p2p/project/scope.md", ".p2p/project/project-swot.md", ".p2p/project/decisions-map.yml", ".p2p/project/features/*/*", ".p2p/project/projection-manifest.yml")),
    FreshnessNodeDefinition("decision_context", ("canonical_sources",), "ProjectDecisionContextService", "deterministic", "p2p context --budget small", (), "durable_decision_context_snapshot_refresh", source_classes=("decision_sources", "project_definition", "project_questions"), source_patterns=(".p2p/proposals/**/*", ".p2p/choices/**/*", ".p2p/changes/**/*", ".p2p/work/**/*", ".p2p/project/definition.yml", ".p2p/project/questions.yml")),
    FreshnessNodeDefinition("assessment", ("registries", "project_projections", "decision_context", "vertical_project_memory"), "ProjectAssessmentService", "deterministic", "p2p assess refresh", (".p2p/project/assessment.yml",)),
    FreshnessNodeDefinition("maturity_progress", ("project_projections", "decision_context", "vertical_project_memory"), "ProjectMaturityService+ProjectProgressService", "deterministic", "p2p assess maturity refresh", (".p2p/project/maturity-assessment.yml",)),
    FreshnessNodeDefinition("brief_context_prompt", ("registries", "project_projections"), "ProjectStateService", "deterministic", "p2p project brief prompt", (".p2p/project/brief-context.md", ".p2p/project/brief.prompt.md"), source_classes=("project_definition",), source_patterns=(".p2p/project/definition.yml",)),
    FreshnessNodeDefinition("operational_brief", ("brief_context_prompt",), "owner_or_agent", "agent_curated", "p2p project brief import <source>", (".p2p/project/operational-brief.md",)),
    FreshnessNodeDefinition("next_actions", ("operational_brief", "decision_context", "vertical_project_memory"), "NextActionService", "owner_review", "p2p next refresh", (".p2p/project/next-actions.yml",)),
    FreshnessNodeDefinition("software_specs", ("canonical_sources",), "SoftwareSpecService", "deterministic", "p2p spec refresh --change <CHANGE-ID>", SOFTWARE_SPEC_OUTPUT_PATTERNS, source_classes=("accepted_proposals", "change_sets"), source_patterns=(".p2p/proposals/**/*", ".p2p/changes/**/*")),
    FreshnessNodeDefinition("visible_export", ("project_projections", "maturity_progress", "software_specs"), "VisibleProjectExportService", "deterministic", "p2p project export", ("outputs/latest/project.md",), source_classes=("project_definition",), source_patterns=(".p2p/project/definition.yml",)),
    FreshnessNodeDefinition("publication_packet", ("visible_export",), "ProjectPublicationService", "deterministic", "p2p project publish prepare --language en --output-name project", ("outputs/latest/publication-evidence.yml", "outputs/latest/publications/project-en/profile.yml", "outputs/latest/publications/project-en/curator-input.md", "outputs/latest/publications/project-en/manifest.yml")),
    FreshnessNodeDefinition("curated_publication", ("publication_packet",), "project_curator", "agent_curated", "p2p project publish import <markdown> --model <model> --evidence-accounting <accounting>", ("outputs/latest/project-en.md", "outputs/latest/publications/project-en/project-model.yml", "outputs/latest/publications/project-en/evidence-accounting.yml")),
    FreshnessNodeDefinition("publication_validation", ("curated_publication",), "ProjectPublicationValidator", "deterministic", "p2p project publish validate --language en --output-name project", ("outputs/latest/publications/project-en/validation.yml",)),
    FreshnessNodeDefinition("publication_render", ("publication_validation",), "ProjectPublicationService", "deterministic", "p2p project publish render --language en --output-name project", ("outputs/latest/project-en.pdf",)),
    FreshnessNodeDefinition("publication_review", ("publication_render",), "owner", "owner_review", "p2p project publish review --language en --output-name project --status approved --reviewer <owner>", ("outputs/latest/publications/project-en/review.yml",)),
)


class DerivedFreshnessService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        registry_status: Callable[[], Any],
        project_state_service: Any,
        decision_context_index: Callable[[], Any],
        project_progress: Callable[[], Any],
        software_spec_statuses: Callable[[], list[Any]],
        visible_export_status: Callable[[], Any],
        publication_status: Callable[[], Any],
        vertical_memory_status: Callable[[], Any] | None = None,
        vertical_memory_view: Callable[[], Any] | None = None,
    ) -> None:
        self.root = root.resolve()
        self.p2p_dir = p2p_dir.resolve()
        self.registry_status = registry_status
        self.project_state_service = project_state_service
        self.decision_context_index = decision_context_index
        self.project_progress = project_progress
        self.software_spec_statuses = software_spec_statuses
        self.visible_export_status = visible_export_status
        self.publication_status = publication_status
        self.vertical_memory_status = vertical_memory_status
        self.vertical_memory_view = vertical_memory_view
        self._order = validate_freshness_graph(NODE_CATALOG)

    def status(
        self,
        *,
        registry_status_snapshot: Any | None = None,
        decision_context_index_snapshot: Any | None = None,
        proposal_summaries_snapshot: list[Any] | None = None,
    ) -> DerivedFreshnessStatus:
        digest_cache: dict[Path, bytes] = {}
        relative_cache: dict[Path, str] = {}
        source_pattern_cache: dict[str, tuple[Path, ...]] = {}
        output_pattern_cache: dict[str, tuple[Path, ...]] = {}
        canonical_paths = self._canonical_paths()
        canonical_fingerprint = _paths_fingerprint(
            self.root,
            canonical_paths,
            digest_cache=digest_cache,
            relative_cache=relative_cache,
        )
        node_by_id: dict[str, FreshnessNode] = {}
        registry = registry_status_snapshot if registry_status_snapshot is not None else self.registry_status()
        memory_status = self.vertical_memory_status() if self.vertical_memory_status else None
        memory_view = None
        if (
            str(getattr(memory_status, "state", "")) == "current"
            and self.vertical_memory_view is not None
        ):
            try:
                memory_view = self.vertical_memory_view()
            except ValueError:
                memory_view = None
        publication = self._publication_status()
        publication_stages = {
            str(getattr(stage, "name", "")): stage
            for stage in getattr(publication, "stages", ())
        } if publication is not None else {}
        for definition in self._order:
            outputs = self._output_paths(definition, cache=output_pattern_cache)
            direct_sources = self._source_paths(definition, cache=source_pattern_cache)
            dependency_nodes = [node_by_id[node_id] for node_id in definition.dependencies]
            source_fingerprint = semantic_sha256(
                {
                    "node_id": definition.node_id,
                    "dependencies": {
                        node.node_id: node.current_fingerprint_sha256 for node in dependency_nodes
                    },
                    "direct_sources": _paths_fingerprint(
                        self.root,
                        direct_sources,
                        digest_cache=digest_cache,
                        relative_cache=relative_cache,
                    ),
                    "source_classes": list(definition.source_classes),
                    "lifecycle_authority_policy_version": PROPOSAL_LIFECYCLE_AUTHORITY_POLICY_VERSION,
                    "decision_ledger_contract_version": LEDGER_CONTRACT_VERSION,
                    "decision_event_schema_version": EVENT_SCHEMA_VERSION,
                    "proposal_semantics_policy_version": (
                        PROPOSAL_SEMANTICS_POLICY_VERSION
                    ),
                    "decision_semantics_policy_version": (
                        DECISION_SEMANTICS_POLICY_VERSION
                    ),
                }
            )
            output_fingerprint = _paths_fingerprint(
                self.root,
                outputs,
                digest_cache=digest_cache,
                relative_cache=relative_cache,
            )
            current_fingerprint = canonical_fingerprint if definition.node_id == "canonical_sources" else semantic_sha256(
                {"source": source_fingerprint, "output": output_fingerprint}
            )
            recorded = ""
            reasons: list[str] = []
            status = "current"
            if definition.node_id == "canonical_sources":
                reasons.append("canonical_content_fingerprint_collected")
            elif definition.node_id == "registries":
                if bool(getattr(registry, "stale", True)):
                    status = "stale"
                    reasons.append("registry_service_reports_stale")
                elif not outputs:
                    status = "missing"
                    reasons.append("registry_outputs_missing")
            elif definition.node_id == "vertical_project_memory":
                memory = memory_status
                memory_state = str(getattr(memory, "state", "missing"))
                status = "current" if memory_state == "current" else memory_state
                recorded = str(getattr(memory, "source_fingerprint_sha256", ""))
                reasons.append(str(getattr(memory, "reason", "vertical_memory_not_available")))
            elif definition.node_id == "project_projections":
                accepted_snapshot = (
                    _accepted_projection_records(self.p2p_dir, proposal_summaries_snapshot)
                    if proposal_summaries_snapshot is not None
                    else None
                )
                status, recorded, reasons = self._project_projection_state(
                    source_fingerprint,
                    outputs,
                    accepted_snapshot=accepted_snapshot,
                    vertical_memory_source_fingerprint=str(
                        getattr(memory_status, "source_fingerprint_sha256", "")
                    ),
                )
            elif definition.node_id == "decision_context":
                index = (
                    decision_context_index_snapshot
                    if decision_context_index_snapshot is not None
                    else self.decision_context_index()
                )
                current_fingerprint = str(getattr(index, "semantic_fingerprint_sha256", current_fingerprint))
                reasons.append("request_scoped_index_current")
                if definition.missing_primitive:
                    reasons.append(f"missing_optional_primitive:{definition.missing_primitive}")
            elif definition.node_id == "maturity_progress":
                if proposal_summaries_snapshot is None and memory_view is None:
                    self.project_progress()
                elif proposal_summaries_snapshot is None:
                    self.project_progress(vertical_memory_snapshot=memory_view)
                elif memory_view is None:
                    self.project_progress(
                        proposal_summaries_snapshot=proposal_summaries_snapshot,
                    )
                else:
                    self.project_progress(
                        proposal_summaries_snapshot=proposal_summaries_snapshot,
                        vertical_memory_snapshot=memory_view,
                    )
                status, reasons = self._output_state(definition, outputs, dependency_nodes)
                reasons.append("progress_is_request_scoped")
            elif definition.node_id == "software_specs":
                specs = self.software_spec_statuses()
                if not specs:
                    status, reasons = self._output_state(
                        definition,
                        outputs,
                        dependency_nodes,
                        optional=True,
                    )
                else:
                    states = [
                        str(getattr(item, "freshness", "invalid"))
                        for item in specs
                    ]
                    counts = {
                        state: states.count(state)
                        for state in sorted(set(states))
                    }
                    reasons = [
                        f"software_specs_{state}:{count}"
                        for state, count in counts.items()
                    ]
                    if any(state in {"stale", "modified"} for state in states):
                        status = "stale"
                    elif any(state in {"invalid", "incomplete"} for state in states):
                        status = "partial"
                    else:
                        status = "current"
            elif definition.node_id == "visible_export":
                visible = self.visible_export_status()
                status, reasons = self._output_state(definition, outputs, dependency_nodes)
                if not bool(getattr(visible, "latest_exists", False)):
                    status = "missing"
                    reasons.append("visible_export_missing")
            elif definition.node_id.startswith("publication_") or definition.node_id == "curated_publication":
                stage_name = {
                    "publication_packet": "packet",
                    "curated_publication": "curated",
                    "publication_validation": "validation",
                    "publication_render": "render",
                    "publication_review": "review",
                }[definition.node_id]
                if definition.node_id == "publication_packet":
                    stage_name = "curator_packet"
                stage = publication_stages.get(stage_name)
                status, reasons = self._publication_node_state(definition, outputs, dependency_nodes, stage)
                recorded = str(getattr(publication, "source_fingerprint_sha256", "")) if publication else ""
            else:
                optional = definition.node_id in {"operational_brief", "next_actions"}
                status, reasons = self._output_state(
                    definition,
                    outputs,
                    dependency_nodes,
                    optional=optional,
                    manual_action_satisfied_by_fresh_output=optional,
                )

            if definition.node_id not in {"canonical_sources", "software_specs"} and any(
                node.status != "current"
                for node in dependency_nodes
            ):
                if definition.action_class in {"agent_curated", "owner_review"}:
                    status = "owner_action_required"
                else:
                    status = "stale"
                reasons.append("upstream_not_current")
            node_by_id[definition.node_id] = FreshnessNode(
                node_id=definition.node_id,
                status=status,
                dependencies=definition.dependencies,
                ownership=definition.ownership,
                action_class=definition.action_class,
                current_fingerprint_sha256=current_fingerprint,
                recorded_source_fingerprint_sha256=recorded,
                source_count=(
                    len(direct_sources)
                    + (sum(node.output_count for node in dependency_nodes) or len(canonical_paths))
                ),
                output_count=len(outputs),
                output_paths=tuple(path.relative_to(self.root).as_posix() for path in outputs),
                reasons=tuple(dict.fromkeys(reasons)),
                command=definition.command,
                missing_primitive=definition.missing_primitive,
                source_classes=definition.source_classes,
                source_paths=tuple(path.relative_to(self.root).as_posix() for path in direct_sources),
            )
        nodes = tuple(node_by_id[item.node_id] for item in self._order)
        rebuild = self._rebuild_plan(nodes)
        overall = "current" if all(node.status == "current" for node in nodes) else "attention_required"
        return DerivedFreshnessStatus(
            graph_version=DERIVED_FRESHNESS_GRAPH_VERSION,
            status=overall,
            canonical_fingerprint_sha256=canonical_fingerprint,
            nodes=nodes,
            rebuild_plan=rebuild,
        )

    def _project_projection_state(
        self,
        source_fingerprint: str,
        outputs: list[Path],
        *,
        accepted_snapshot: list[dict[str, object]] | None = None,
        vertical_memory_source_fingerprint: str = "",
    ) -> tuple[str, str, list[str]]:
        manifest = self.project_state_service.projection_manifest()
        data = manifest.get("project_projection") if isinstance(manifest, Mapping) else None
        recorded = str(data.get("source_fingerprint_sha256") or "") if isinstance(data, Mapping) else ""
        expected = (
            accepted_snapshot
            if accepted_snapshot is not None
            else self.project_state_service.accepted_proposals()
        )
        expected_count = len(expected)
        expected_feature_ids = {str(item.get("feature_id") or "") for item in expected}
        decisions = self.p2p_dir / "project" / "decisions-map.yml"
        decision_count = _yaml_sequence_count(decisions, "decisions")
        generated_feature_ids = _generated_feature_ids(self.p2p_dir / "project" / "features")
        reasons: list[str] = []
        if decision_count != expected_count:
            reasons.append(f"decision_projection_count_mismatch:{decision_count}!={expected_count}")
        if generated_feature_ids != expected_feature_ids:
            reasons.append(
                "feature_projection_set_mismatch:"
                f"generated={len(generated_feature_ids)},expected={len(expected_feature_ids)}"
            )
        expected_source = self.project_state_service.source_fingerprint(
            expected,
            vertical_memory_source_fingerprint=vertical_memory_source_fingerprint,
        )
        if recorded and recorded != expected_source:
            reasons.append("projection_source_fingerprint_changed")
        if reasons:
            return "stale", recorded, reasons
        if not recorded:
            return "partial", "", ["projection_ownership_manifest_missing"]
        owned = data.get("owned_paths") if isinstance(data, Mapping) else None
        if not isinstance(owned, list):
            return "partial", recorded, ["projection_owned_paths_missing"]
        return "current", recorded, ["projection_manifest_matches_current_sources"]

    def _output_state(
        self,
        definition: FreshnessNodeDefinition,
        outputs: list[Path],
        dependencies: list[FreshnessNode],
        *,
        optional: bool = False,
        manual_action_satisfied_by_fresh_output: bool = False,
    ) -> tuple[str, list[str]]:
        if not outputs:
            if definition.action_class in {"agent_curated", "owner_review"} or optional:
                return "owner_action_required", ["optional_or_curated_output_missing"]
            return "missing", ["owned_output_missing"]
        dependency_paths = [self.root / path for node in dependencies for path in node.output_paths]
        latest_source = max((path.stat().st_mtime_ns for path in dependency_paths if path.exists()), default=0)
        oldest_output = min(path.stat().st_mtime_ns for path in outputs)
        if latest_source and oldest_output < latest_source:
            return "stale", ["output_older_than_dependency"]
        if (
            definition.action_class in {"agent_curated", "owner_review"}
            and not manual_action_satisfied_by_fresh_output
        ):
            return "owner_action_required", ["owner_or_agent_review_required"]
        reasons = ["content_hash_collected", "output_not_older_than_dependencies"]
        if manual_action_satisfied_by_fresh_output:
            reasons.insert(0, "supported_manual_output_newer_than_dependencies")
        return "current", reasons

    def _publication_node_state(
        self,
        definition: FreshnessNodeDefinition,
        outputs: list[Path],
        dependencies: list[FreshnessNode],
        stage: Any | None,
    ) -> tuple[str, list[str]]:
        if stage is not None:
            stage_status = str(getattr(stage, "status", ""))
            stale = bool(getattr(stage, "stale", False))
            reason = str(getattr(stage, "reason", ""))
            if stale:
                return "stale", [reason or f"publication_stage_{stage_status}"]
            if stage_status in {"current", "ready", "valid", "rendered", "approved", "prepared", "imported"}:
                return "current", [f"publication_manifest_stage:{stage_status}"]
        return self._output_state(definition, outputs, dependencies)

    def _rebuild_plan(self, nodes: tuple[FreshnessNode, ...]) -> tuple[FreshnessRebuildAction, ...]:
        stale_ids = {node.node_id for node in nodes if node.status != "current"}
        actions: list[FreshnessRebuildAction] = []
        for node in nodes:
            if node.node_id not in stale_ids or node.action_class == "none":
                continue
            blocked_by = tuple(dependency for dependency in node.dependencies if dependency in stale_ids)
            actions.append(
                FreshnessRebuildAction(
                    order=len(actions) + 1,
                    node_id=node.node_id,
                    action_class=node.action_class,
                    command=node.command,
                    automatic=node.action_class == "deterministic" and not blocked_by and not node.missing_primitive,
                    blocked_by=blocked_by,
                    missing_primitive=node.missing_primitive,
                )
            )
        return tuple(actions)

    def _canonical_paths(self) -> list[Path]:
        paths: list[Path] = []
        for relative in ("project.yml", "proposals", "changes", "choices", "work", "consents", "intakes"):
            target = self.p2p_dir / relative
            if target.is_file():
                paths.append(target)
            elif target.exists():
                paths.extend(path for path in target.rglob("*") if path.is_file() and not path.is_symlink())
        project_dir = self.p2p_dir / "project"
        derived_names = {
            "assessment.yml", "maturity-assessment.yml", "overview.md", "problem.md", "scope.md",
            "project-swot.md", "decisions-map.yml", "projection-manifest.yml", "brief-context.md", "brief.prompt.md",
            "operational-brief.md", "next-actions.yml", "next-actions-log.yml",
        }
        if project_dir.exists():
            paths.extend(
                path for path in project_dir.iterdir()
                if path.is_file() and path.name not in derived_names and not path.is_symlink()
            )
        return sorted(set(paths), key=lambda path: path.relative_to(self.root).as_posix())

    def _output_paths(
        self,
        definition: FreshnessNodeDefinition,
        *,
        cache: dict[str, tuple[Path, ...]] | None = None,
    ) -> list[Path]:
        paths: set[Path] = set()
        for pattern in definition.output_patterns:
            if cache is not None and pattern in cache:
                paths.update(cache[pattern])
                continue
            selected = tuple(
                path
                for path in self.root.glob(pattern)
                if path.is_file() and not path.is_symlink()
            )
            if cache is not None:
                cache[pattern] = selected
            paths.update(selected)
        return sorted(paths, key=lambda path: path.relative_to(self.root).as_posix())

    def _source_paths(
        self,
        definition: FreshnessNodeDefinition,
        *,
        cache: dict[str, tuple[Path, ...]] | None = None,
    ) -> list[Path]:
        paths: set[Path] = set()
        for pattern in definition.source_patterns:
            if cache is not None and pattern in cache:
                paths.update(cache[pattern])
                continue
            selected = tuple(
                path
                for path in self.root.glob(pattern)
                if path.is_file() and not path.is_symlink()
            )
            if cache is not None:
                cache[pattern] = selected
            paths.update(selected)
        return sorted(paths, key=lambda path: path.relative_to(self.root).as_posix())

    def impact_node_ids(self, changed_paths: Iterable[str]) -> tuple[str, ...]:
        normalized = tuple(sorted({str(item).replace("\\", "/") for item in changed_paths}))
        directly_affected = {
            definition.node_id
            for definition in self._order
            if any(
                fnmatch.fnmatch(path, pattern)
                for path in normalized
                for pattern in definition.source_patterns
            )
        }
        affected = set(directly_affected)
        for definition in self._order:
            if set(definition.dependencies) & affected:
                affected.add(definition.node_id)
        return tuple(item.node_id for item in self._order if item.node_id in affected)

    def _publication_status(self) -> Any | None:
        try:
            return self.publication_status()
        except ValueError:
            return None


def _accepted_projection_records(
    p2p_dir: Path,
    proposal_summaries: list[Any],
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for proposal in proposal_summaries:
        status = str(getattr(proposal, "status", ""))
        if not is_active_project_projection(status):
            continue
        title = str(getattr(proposal, "title", ""))
        feature_id = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "project"
        records.append(
            {
                "proposal_id": str(getattr(proposal, "proposal_id", "")),
                "status": status,
                "feature_id": feature_id,
                "path": p2p_dir / "proposals" / str(getattr(proposal, "slug", "")),
            }
        )
    return records


def validate_freshness_graph(
    definitions: Iterable[FreshnessNodeDefinition],
) -> tuple[FreshnessNodeDefinition, ...]:
    items = tuple(definitions)
    by_id = {item.node_id: item for item in items}
    if len(by_id) != len(items):
        raise ValueError("Freshness graph contains duplicate node ids.")
    for item in items:
        unknown = set(item.dependencies) - set(by_id)
        if unknown:
            raise ValueError(f"Freshness node `{item.node_id}` has unknown dependency `{sorted(unknown)[0]}`.")
    ordered: list[FreshnessNodeDefinition] = []
    remaining = set(by_id)
    while remaining:
        ready = sorted(node_id for node_id in remaining if set(by_id[node_id].dependencies) <= {item.node_id for item in ordered})
        if not ready:
            raise ValueError("Freshness graph contains a dependency cycle.")
        for node_id in ready:
            ordered.append(by_id[node_id])
            remaining.remove(node_id)
    return tuple(ordered)


def _paths_fingerprint(
    root: Path,
    paths: Iterable[Path],
    *,
    digest_cache: dict[Path, bytes] | None = None,
    relative_cache: dict[Path, str] | None = None,
) -> str:
    digest = hashlib.sha256()
    digest_cache = digest_cache if digest_cache is not None else {}
    relative_cache = relative_cache if relative_cache is not None else {}

    def relative(path: Path) -> str:
        value = relative_cache.get(path)
        if value is None:
            value = path.relative_to(root).as_posix()
            relative_cache[path] = value
        return value

    for path in sorted(paths, key=relative):
        digest.update(relative(path).encode("utf-8"))
        digest.update(b"\0")
        content_digest = digest_cache.get(path)
        if content_digest is None:
            content_digest = hashlib.sha256(path.read_bytes()).digest()
            digest_cache[path] = content_digest
        digest.update(content_digest)
    return digest.hexdigest()


def _yaml_sequence_count(path: Path, key: str) -> int:
    if not path.exists():
        return 0
    import yaml

    try:
        payload = load_yaml(path.read_bytes())
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return 0
    value = payload.get(key) if isinstance(payload, dict) else None
    return len(value) if isinstance(value, list) else 0


def _generated_feature_ids(features_dir: Path) -> set[str]:
    if not features_dir.exists():
        return set()
    generated: set[str] = set()
    for directory in features_dir.iterdir():
        feature = directory / "feature.md"
        if (
            directory.is_dir()
            and feature.is_file()
            and "## Provenance" in feature.read_text(encoding="utf-8")
        ):
            generated.add(directory.name)
    return generated
