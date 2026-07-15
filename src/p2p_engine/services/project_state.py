from __future__ import annotations

import hashlib
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import yaml

from p2p_engine.core.mutation_preview import MutationPreviewService, semantic_sha256, source_precondition
from p2p_engine.foundation.files import read_yaml_mapping, yaml_dump as _yaml_dump
from p2p_engine.services.lifecycle_authority import PROPOSAL_LIFECYCLE_AUTHORITY_POLICY_VERSION
from p2p_engine.services.workspace_transactions import AtomicMutationWriter


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

    def refresh(self) -> list[Path]:
        project_dir = self.p2p_dir / "project"
        features_dir = project_dir / "features"
        accepted = self.accepted_proposals()
        project_name = self.project_name()
        files: dict[Path, str] = {
            project_dir / "overview.md": project_overview_markdown(project_name, accepted),
            project_dir / "problem.md": project_problem_markdown(accepted),
            project_dir / "scope.md": project_scope_markdown(accepted),
            project_dir / "project-swot.md": project_swot_markdown(),
            project_dir / "decisions-map.yml": _yaml_dump(
                {
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
                "source_fingerprint_sha256": self.source_fingerprint(accepted),
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
        conflicts_path = project_dir / "conflicts.yml"
        conflicts_relative = conflicts_path.relative_to(self.root).as_posix()
        if not conflicts_path.exists():
            candidates[conflicts_relative] = _yaml_dump({"conflicts": []}).encode("utf-8")
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
                    else semantic_sha256(yaml.safe_load(content.decode("utf-8")))
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
        if conflicts_relative in candidates:
            written.append(conflicts_path.relative_to(self.root))
        return written

    def source_fingerprint(self, accepted: list[dict[str, object]] | None = None) -> str:
        records = accepted if accepted is not None else self.accepted_proposals()
        inputs: list[dict[str, object]] = []
        for item in records:
            proposal_dir = Path(item["path"])
            files = []
            for name in ("proposal.md", "decision.md", "tasks.yml"):
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
                    "files": files,
                }
            )
        return semantic_sha256(inputs)

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
