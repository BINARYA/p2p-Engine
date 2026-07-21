from __future__ import annotations

import hashlib
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from p2p_engine.core.mutation_preview import MutationPreviewService, semantic_sha256, source_precondition
from p2p_engine.foundation.files import read_yaml_mapping, yaml_dump as _yaml_dump
from p2p_engine.foundation.yaml_loaders import load_yaml
from p2p_engine.services.lifecycle_authority import PROPOSAL_LIFECYCLE_AUTHORITY_POLICY_VERSION
from p2p_engine.services.workspace_transactions import AtomicMutationWriter
from p2p_engine.core.vertical_memory import VerticalProjectMemoryView


class RegistryStatusLike(Protocol):
    registries_dir: Path
    stale: bool
    proposals_count: int
    changes_count: int


@dataclass(frozen=True)
class ProjectStateStatus:
    accepted_proposals: int
    features: list[str]
    project_dir: Path
    operational_brief_available: bool
    next_actions_count: int
    first_next_action: object | None


@dataclass(frozen=True)
class ProjectBriefPrompt:
    context_path: Path
    prompt_path: Path


def _read_optional(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


class ProjectStateService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        accepted_proposals: Callable[[], list[dict[str, object]]],
        project_name: Callable[[], str],
        next_actions: Callable[[], list[object]],
        registry_status: Callable[[], RegistryStatusLike],
        project_brief_context: Callable[[RegistryStatusLike], str],
        validate_yaml_key: Callable[[str, str], None],
        atomic_writer: AtomicMutationWriter | None = None,
        vertical_memory: Callable[[], VerticalProjectMemoryView] | None = None,
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.accepted_proposals = accepted_proposals
        self.project_name = project_name
        self.next_actions = next_actions
        self.registry_status = registry_status
        self.project_brief_context = project_brief_context
        self.validate_yaml_key = validate_yaml_key
        self.atomic_writer = atomic_writer or AtomicMutationWriter(root=root, p2p_dir=p2p_dir)
        self.vertical_memory = vertical_memory

    def refresh(self) -> list[Path]:
        project_dir = self.p2p_dir / "project"
        features_dir = project_dir / "features"
        accepted = self.accepted_proposals()
        project_name = self.project_name()
        memory = self.vertical_memory() if self.vertical_memory is not None else None
        files: dict[Path, str] = {
            project_dir / "overview.md": (
                vertical_project_overview_markdown(project_name, memory)
                if memory is not None
                else project_overview_markdown(project_name, accepted)
            ),
            project_dir / "problem.md": (
                vertical_project_problem_markdown(memory)
                if memory is not None
                else project_problem_markdown(accepted)
            ),
            project_dir / "scope.md": (
                vertical_project_scope_markdown(memory)
                if memory is not None
                else project_scope_markdown(accepted)
            ),
            project_dir / "project-swot.md": project_swot_markdown(),
            project_dir / "decisions-map.yml": _yaml_dump(
                vertical_decisions_map(memory, accepted)
                if memory is not None
                else {
                    "decisions": [
                        {
                            "proposal": item["proposal_id"],
                            "title": item["title"],
                            "status": item["status"],
                            "feature": item["feature_id"],
                            "source": item["source"],
                        }
                        for item in accepted
                    ]
                }
            ),
        }
        for item in accepted:
            feature_dir = features_dir / str(item["feature_id"])
            files.update({
                feature_dir / "feature.md": feature_markdown(item),
                feature_dir / "tasks.yml": _read_optional(Path(item["path"]) / "tasks.yml") or "tasks: []\n",
                feature_dir / "actions.yml": _yaml_dump({"actions": []}),
            })

        expected_paths = {path.relative_to(self.root).as_posix() for path in files}
        manifest_path = project_dir / "projection-manifest.yml"
        manifest_relative = manifest_path.relative_to(self.root).as_posix()
        owned_paths = sorted({*expected_paths, manifest_relative})
        stale_paths, stale_dirs = self._stale_owned_projection_paths(set(owned_paths))
        manifest = {
            "project_projection": {
                "manifest_version": 1,
                "owner": "ProjectStateService",
                "source_fingerprint_sha256": self.source_fingerprint(
                    accepted,
                    memory.source_fingerprint_sha256 if memory is not None else "",
                ),
                "vertical_memory_source_fingerprint_sha256": (
                    memory.source_fingerprint_sha256 if memory is not None else ""
                ),
                "vertical_memory_source": memory.source if memory is not None else "not_available",
                "lifecycle_authority_policy_version": PROPOSAL_LIFECYCLE_AUTHORITY_POLICY_VERSION,
                "accepted_projection_count": len(accepted),
                "owned_paths": owned_paths,
            }
        }
        files[manifest_path] = _yaml_dump(manifest)
        candidates: dict[str, bytes | None] = {
            path.relative_to(self.root).as_posix(): content.encode("utf-8")
            for path, content in files.items()
        }
        for relative in stale_paths:
            candidates[relative] = None
        sources = tuple(
            source_precondition(relative, (self.root / relative).read_bytes() if (self.root / relative).exists() else None)
            for relative in sorted(candidates)
        )
        if all(
            content is not None
            and (self.root / relative).exists()
            and (self.root / relative).read_bytes() == content
            for relative, content in candidates.items()
        ):
            return [Path(relative) for relative in owned_paths]
        token = MutationPreviewService.token(
            operation_id="project-projection-refresh",
            targets=tuple(candidates),
            sources=sources,
            candidate_semantics={
                relative: (
                    {"deleted": True}
                    if content is None
                    else semantic_sha256(load_yaml(content))
                    if relative.endswith((".yml", ".yaml"))
                    else hashlib.sha256(content).hexdigest()
                )
                for relative, content in candidates.items()
            },
        )
        result = self.atomic_writer.apply(
            operation_id="project-projection-refresh",
            candidates=candidates,
            sources=sources,
            preview_token=token,
            actor="system",
        )
        if result.status != "applied":
            raise ValueError(result.message or f"Project projection refresh failed: {result.status}")
        for directory in sorted(stale_dirs, key=lambda item: len(item.parts), reverse=True):
            try:
                directory.rmdir()
            except OSError:
                pass
        written = [Path(relative) for relative in owned_paths]
        return written

    def source_fingerprint(
        self,
        accepted: list[dict[str, object]] | None = None,
        vertical_memory_source_fingerprint: str = "",
    ) -> str:
        records = accepted if accepted is not None else self.accepted_proposals()
        if not vertical_memory_source_fingerprint and self.vertical_memory is not None:
            vertical_memory_source_fingerprint = (
                self.vertical_memory().source_fingerprint_sha256
            )
        inputs: list[dict[str, object]] = []
        for item in records:
            proposal_dir = Path(item["path"])
            files = []
            for name in (
                "proposal.md",
                "decision-events.yml",
                "decision.md",
                "tasks.yml",
            ):
                path = proposal_dir / name
                files.append(
                    {
                        "name": name,
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None,
                    }
                )
            inputs.append(
                {
                    "proposal_id": item["proposal_id"],
                    "status": item["status"],
                    "feature_id": item["feature_id"],
                    "head_event_id": item.get("head_event_id"),
                    "decision_semantic_sha256": item.get(
                        "decision_semantic_sha256"
                    ),
                    "files": files,
                }
            )
        if not vertical_memory_source_fingerprint:
            return semantic_sha256(inputs)
        return semantic_sha256(
            {
                "accepted_proposals": inputs,
                "vertical_memory_source_fingerprint_sha256": vertical_memory_source_fingerprint,
            }
        )

    def projection_manifest(self) -> dict[str, object]:
        path = self.p2p_dir / "project" / "projection-manifest.yml"
        return read_yaml_mapping(path, default={}) if path.exists() else {}

    def _stale_owned_projection_paths(self, expected_paths: set[str]) -> tuple[set[str], set[Path]]:
        manifest = self.projection_manifest()
        data = manifest.get("project_projection") if isinstance(manifest, dict) else None
        prior_owned = data.get("owned_paths") if isinstance(data, dict) else None
        owned: set[str] = {
            str(path) for path in prior_owned if isinstance(path, str)
        } if isinstance(prior_owned, list) else set()
        features_dir = self.p2p_dir / "project" / "features"
        stale_dirs: set[Path] = set()
        if features_dir.exists():
            for directory in features_dir.iterdir():
                if not directory.is_dir():
                    continue
                feature_path = directory / "feature.md"
                generated = feature_path.exists() and "## Provenance" in feature_path.read_text(encoding="utf-8")
                if generated:
                    owned.update(path.relative_to(self.root).as_posix() for path in directory.rglob("*") if path.is_file())
        stale = {path for path in owned - expected_paths if (self.root / path).is_file()}
        for relative in stale:
            parent = (self.root / relative).parent
            if parent.parent == features_dir:
                stale_dirs.add(parent)
        return stale, stale_dirs

    def status(
        self,
        *,
        accepted_proposals_count: int | None = None,
        next_actions_snapshot: list[object] | None = None,
    ) -> ProjectStateStatus:
        project_dir = self.p2p_dir / "project"
        features_dir = project_dir / "features"
        features = sorted(path.name for path in features_dir.iterdir() if path.is_dir()) if features_dir.exists() else []
        next_actions = next_actions_snapshot if next_actions_snapshot is not None else self.next_actions()
        return ProjectStateStatus(
            accepted_proposals=(
                accepted_proposals_count
                if accepted_proposals_count is not None
                else len(self.accepted_proposals())
            ),
            features=features,
            project_dir=project_dir.relative_to(self.root),
            operational_brief_available=(project_dir / "operational-brief.md").exists(),
            next_actions_count=len(next_actions),
            first_next_action=next_actions[0] if next_actions else None,
        )

    def show(self, section: str) -> str:
        project_dir = self.p2p_dir / "project"
        section_map = {
            "overview": project_dir / "overview.md",
            "problem": project_dir / "problem.md",
            "scope": project_dir / "scope.md",
            "swot": project_dir / "project-swot.md",
        }
        path = section_map.get(section, project_dir / "features" / section / "feature.md")
        if not path.exists():
            raise ValueError(f"Project section not found: {section}")
        return path.read_text(encoding="utf-8")

    def create_brief_prompt(self) -> ProjectBriefPrompt:
        project_dir = self.p2p_dir / "project"
        project_dir.mkdir(parents=True, exist_ok=True)
        context = self.project_brief_context(self.registry_status())
        context_path = project_dir / "brief-context.md"
        prompt_path = project_dir / "brief.prompt.md"
        context_path.write_text(context, encoding="utf-8")
        prompt_path.write_text(project_brief_prompt_markdown(context), encoding="utf-8")
        return ProjectBriefPrompt(
            context_path=context_path.relative_to(self.root),
            prompt_path=prompt_path.relative_to(self.root),
        )

    def import_brief(self, source: Path) -> list[Path]:
        project_dir = self.p2p_dir / "project"
        project_dir.mkdir(parents=True, exist_ok=True)
        source = source.resolve()
        imported: list[Path] = []
        if source.is_dir():
            mappings = {
                "operational-brief.md": None,
                "next-actions.yml": "next_actions",
            }
            for filename, key in mappings.items():
                source_path = source / filename
                if source_path.exists():
                    if key is not None:
                        self.validate_yaml_key(source_path.read_text(encoding="utf-8"), key)
                    target = project_dir / filename
                    shutil.copyfile(source_path, target)
                    imported.append(target.relative_to(self.root))
        elif source.is_file():
            target = project_dir / "operational-brief.md"
            target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            imported.append(target.relative_to(self.root))
        else:
            raise ValueError(f"Project brief source not found: {source}")
        if not imported:
            raise ValueError(f"No project brief artifacts found in: {source}")
        return imported

    def show_brief(self) -> str:
        path = self.p2p_dir / "project" / "operational-brief.md"
        if not path.exists():
            raise ValueError("Project brief not found. Run `p2p project brief import` first.")
        return path.read_text(encoding="utf-8")


def project_overview_markdown(project_name: str, accepted: list[dict[str, object]]) -> str:
    lines = [
        f"# Project State - {project_name}",
        "",
        "This file is generated by `p2p project refresh` from accepted proposals.",
        "",
        "## Accepted Proposals",
        "",
    ]
    if accepted:
        for item in accepted:
            lines.append(f"- {item['proposal_id']} - {item['title']}")
    else:
        lines.append("- None.")
    lines.extend(["", "## Features", ""])
    if accepted:
        for item in accepted:
            lines.append(f"- `{item['feature_id']}` from {item['proposal_id']}")
    else:
        lines.append("- None.")
    lines.append("")
    return "\n".join(lines)


def vertical_project_overview_markdown(
    project_name: str,
    memory: VerticalProjectMemoryView,
) -> str:
    lines = [
        f"# Project State - {project_name}",
        "",
        "This derived view is generated from canonical P2P project sources. It does not establish governance, readiness, implementation, or publication approval.",
        "",
        "## Project Vertical",
        "",
        f"- Active vertical: `{memory.vertical_id}` v{memory.vertical_version}",
        f"- Memory source: `{memory.source}`",
        f"- Source fingerprint: `{memory.source_fingerprint_sha256}`",
        "",
        "## Current Direction By Vertical Section",
        "",
    ]
    active_sections = [section for section in memory.sections if section.active_contributions]
    if not active_sections:
        lines.append("- No active proposal direction has declared vertical coverage.")
    for section in active_sections:
        lines.extend([f"### {section.title} (`{section.section_id}`)", ""])
        for item in section.active_contributions:
            lines.append(
                f"- {item.proposal_id} - {item.title}; authority `{item.authority}`; source `{item.source_path}`"
            )
        lines.append("")
    pending = [
        (section, item)
        for section in memory.sections
        for item in section.conflicts
        if str(item.get("kind") or "") == "conflict"
        and str(item.get("status") or "") == "unresolved"
    ]
    questions = [
        (section, item)
        for section in memory.sections
        for item in section.questions
        if str(item.get("state") or "") in {"to_answer", "answered"}
    ]
    lines.extend(["## Pending Owner Decisions", ""])
    if not pending and not questions:
        lines.append("- None recorded.")
    for section, item in pending:
        lines.append(
            f"- Conflict `{item.get('id')}` in `{section.section_id}`: {item.get('reason') or 'resolution required'}"
        )
    for section, item in questions:
        lines.append(
            f"- Question `{item.get('id')}` in `{section.section_id}` is `{item.get('state')}`."
        )
    lines.extend(["", "## Assumptions And Blockers", ""])
    assumption_or_blocker = False
    for section in memory.sections:
        for item in section.definition.get("assumptions", ()):
            assumption_or_blocker = True
            lines.append(
                f"- Assumption `{item.get('id')}` in `{section.section_id}` is `{item.get('status')}`: {item.get('text')}"
            )
        for item in section.definition.get("blockers", ()):
            assumption_or_blocker = True
            lines.append(
                f"- Blocker `{item.get('id')}` in `{section.section_id}` is `{item.get('status')}`: {item.get('text')}"
            )
    if not assumption_or_blocker:
        lines.append("- None recorded.")
    missing = [
        section
        for section in memory.sections
        if section.required
        and not section.active_contributions
        and str(section.definition.get("status") or "missing") != "not_applicable"
    ]
    lines.extend(["", "## Missing Declared Evidence", ""])
    if missing:
        lines.extend(
            f"- `{section.section_id}` - {section.title}"
            for section in missing
        )
    else:
        lines.append("- None.")
    lines.extend(["", "## Legacy Unmapped Active Proposals", ""])
    if memory.unmapped_active_proposals:
        for item in memory.unmapped_active_proposals:
            lines.append(
                f"- {item.get('proposal_id')} - {item.get('title')}; source `{item.get('source_path')}`"
            )
    else:
        lines.append("- None.")
    historical_count = sum(len(section.historical_contributions) for section in memory.sections)
    lines.extend(
        [
            "",
            "## Historical Context",
            "",
            f"- Historical section contributions: {historical_count}",
            "- Inspect history with `p2p project memory show --section <SECTION-ID> --include-history`.",
            "",
            "`.p2p/` remains the authoritative project source of truth.",
            "",
        ]
    )
    return "\n".join(lines)


def vertical_project_problem_markdown(memory: VerticalProjectMemoryView) -> str:
    lines = [
        "# Project Problem",
        "",
        "Derived problem evidence grouped by active vertical section. `.p2p/` remains authoritative.",
        "",
    ]
    rendered = False
    for section in memory.sections:
        records = [
            (item, evidence)
            for item in section.active_contributions
            for evidence in item.evidence
            if evidence.fragment_kind == "problem"
        ]
        if not records:
            continue
        rendered = True
        lines.extend([f"## {section.title} (`{section.section_id}`)", ""])
        for contribution, evidence in records:
            lines.extend(
                [
                    f"### {contribution.proposal_id} - {contribution.title}",
                    "",
                    evidence.fragment,
                    "",
                    f"Source: `{evidence.source_path}` (`{evidence.evidence_id}`).",
                    "",
                ]
            )
    if not rendered:
        lines.append("No active declared problem evidence is available.\n")
    return "\n".join(lines)


def vertical_project_scope_markdown(memory: VerticalProjectMemoryView) -> str:
    lines = [
        "# Project Scope",
        "",
        "Derived goals and non-goals grouped by active vertical section. `.p2p/` remains authoritative.",
        "",
    ]
    rendered = False
    for section in memory.sections:
        records = [
            (item, evidence)
            for item in section.active_contributions
            for evidence in item.evidence
            if evidence.fragment_kind in {"goals", "non-goals"}
        ]
        if not records:
            continue
        rendered = True
        lines.extend([f"## {section.title} (`{section.section_id}`)", ""])
        for contribution, evidence in records:
            label = "Goals" if evidence.fragment_kind == "goals" else "Non-Goals"
            lines.extend(
                [
                    f"### {label} - {contribution.proposal_id}",
                    "",
                    evidence.fragment,
                    "",
                    f"Source: `{evidence.source_path}` (`{evidence.evidence_id}`).",
                    "",
                ]
            )
    if not rendered:
        lines.append("No active declared scope evidence is available.\n")
    return "\n".join(lines)


def vertical_decisions_map(
    memory: VerticalProjectMemoryView,
    accepted: list[dict[str, object]],
) -> dict[str, object]:
    accepted_by_id = {str(item["proposal_id"]): item for item in accepted}
    active: dict[str, dict[str, object]] = {}
    historical: dict[str, dict[str, object]] = {}
    for section in memory.sections:
        for contribution in section.active_contributions:
            item = accepted_by_id.get(contribution.proposal_id, {})
            record = active.setdefault(
                contribution.contribution_id,
                {
                    "proposal": contribution.proposal_id,
                    "title": contribution.title,
                    "status": contribution.effective_state,
                    "feature": item.get("feature_id"),
                    "source": contribution.source_path,
                    "authority": contribution.authority,
                    "head_event_id": contribution.head_event_id or None,
                    "rationale": contribution.rationale,
                    "constraints": list(contribution.constraints),
                    "sections": [],
                },
            )
            record["sections"].append(section.section_id)
        for contribution in section.historical_contributions:
            record = historical.setdefault(
                contribution.contribution_id,
                {
                    "proposal": contribution.proposal_id,
                    "title": contribution.title,
                    "status": contribution.effective_state,
                    "source": contribution.source_path,
                    "authority": contribution.authority,
                    "head_event_id": contribution.head_event_id or None,
                    "sections": [],
                },
            )
            record["sections"].append(section.section_id)
    represented = {str(item["proposal"]) for item in active.values()}
    for proposal_id, item in sorted(accepted_by_id.items()):
        if proposal_id in represented:
            continue
        active[f"unmapped:{proposal_id}"] = {
            "proposal": proposal_id,
            "title": item["title"],
            "status": item["status"],
            "feature": item["feature_id"],
            "source": item["source"],
            "authority": "active_unmapped",
            "head_event_id": item.get("head_event_id"),
            "rationale": "",
            "constraints": [],
            "sections": [],
        }
    return {
        "projection": {
            "kind": "vertical_first_derived_project_memory",
            "vertical_id": memory.vertical_id,
            "source_fingerprint_sha256": memory.source_fingerprint_sha256,
            "source": memory.source,
            "canonical_source": ".p2p/",
        },
        "decisions": [
            {**record, "sections": sorted(set(record["sections"]))}
            for _, record in sorted(
                active.items(),
                key=lambda item: (
                    tuple(item[1]["sections"]),
                    str(item[1]["proposal"]),
                    item[0],
                ),
            )
        ],
        "historical_decisions": [
            {**record, "sections": sorted(set(record["sections"]))}
            for _, record in sorted(
                historical.items(),
                key=lambda item: (str(item[1]["proposal"]), item[0]),
            )
        ],
    }


def project_problem_markdown(accepted: list[dict[str, object]]) -> str:
    lines = ["# Project Problem", "", "Generated from accepted proposal problem statements.", ""]
    for item in accepted:
        lines.extend([f"## {item['proposal_id']} - {item['title']}", "", str(item["problem"]), ""])
    if not accepted:
        lines.append("No accepted proposals yet.\n")
    return "\n".join(lines)


def project_scope_markdown(accepted: list[dict[str, object]]) -> str:
    lines = ["# Project Scope", "", "Generated from accepted proposal goals and non-goals.", ""]
    for item in accepted:
        lines.extend(
            [
                f"## {item['proposal_id']} - {item['title']}",
                "",
                "### Goals",
                "",
                str(item["goals"]),
                "",
                "### Non-Goals",
                "",
                str(item["non_goals"]),
                "",
            ]
        )
    if not accepted:
        lines.append("No accepted proposals yet.\n")
    return "\n".join(lines)


def project_swot_markdown() -> str:
    return (
        "# Project SWOT\n\n"
        "Generated placeholder. Use `p2p swot prompt <PROP-ID>` for proposal-level SWOT "
        "and consolidate project-level findings here during project refresh evolution.\n"
    )


def feature_markdown(item: dict[str, object]) -> str:
    return (
        f"# {item['title']}\n\n"
        "## Provenance\n\n"
        f"- Proposal: {item['proposal_id']}\n"
        f"- Source: {item['source']}\n\n"
        "## Problem\n\n"
        f"{item['problem']}\n\n"
        "## Proposal\n\n"
        f"{item['proposal']}\n\n"
        "## Decision\n\n"
        f"{str(item['decision']).strip() or 'Not provided.'}\n"
    )


def project_brief_prompt_markdown(context: str) -> str:
    return (
        "# P2P Operational Brief Prompt\n\n"
        "You are helping synthesize the current P2P project state into an operational brief.\n\n"
        "## Governance Boundary\n\n"
        "Do not accept, reject, defer, merge, supersede, or apply recommendations. "
        "Do not decide on behalf of the owner. Recommend next actions only and point to "
        "the P2P commands that would let the owner act explicitly.\n\n"
        "## Project Context\n\n"
        f"{context}\n\n"
        "## Required Output\n\n"
        "Return artifacts with these shapes:\n\n"
        "### operational-brief.md\n\n"
        "```markdown\n"
        "# Operational Brief\n\n"
        "## Where We Are\n"
        "Short synthesis of the current project state.\n\n"
        "## Accepted Direction\n"
        "Accepted decisions and constraints that shape the project.\n\n"
        "## Active Work\n"
        "Change Sets, draft proposals, pending intake, and work still moving.\n\n"
        "## Blockers / Inconsistencies\n"
        "Open choices, conflicts, stale registries, status mismatches, or missing artifacts.\n\n"
        "## Recommended Next Actions\n"
        "1. Action title\n"
        "   Reason: Why this matters now.\n"
        "   Command: p2p ...\n\n"
        "## Not Yet\n"
        "Useful but lower-priority directions.\n"
        "```\n\n"
        "### next-actions.yml\n\n"
        "```yaml\n"
        "next_actions:\n"
        "  - id: NEXT-001\n"
        "    priority: high | medium | low\n"
        "    kind: continue_change | resolve_choice | refresh_registry | inspect_intake | record_conflict | create_change | other\n"
        "    target: CHANGE-000\n"
        "    reason: Short reason.\n"
        "    command: p2p ...\n"
        "```\n"
    )
