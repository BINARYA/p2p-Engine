from __future__ import annotations

import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from p2p_engine.foundation.markdown import markdown_has_section, strip_markdown_title
from p2p_engine.foundation.yaml_loaders import load_yaml


@dataclass(frozen=True)
class SoftwareSpecExportStatus:
    change_id: str
    target: str
    title: str
    status: str
    path: Path
    lifecycle: Any | None = None


@dataclass(frozen=True)
class SoftwareSpecExportValidation:
    change_id: str
    target: str
    path: Path
    checked: list[Path]


def software_spec_export_targets() -> tuple[str, ...]:
    return ("generic", "openspec", "speckit")


def _software_spec_export_required_files(target: str) -> list[Path]:
    if target == "generic":
        return [
            Path("project.md"),
            Path("propose.md"),
        ]
    if target == "openspec":
        return [
            Path("propose.md"),
        ]
    if target == "speckit":
        return [
            Path("speckit.constitution.md"),
            Path("speckit.specify.md"),
            Path("speckit.plan.md"),
        ]
    raise ValueError(f"Unsupported software spec export target: {target}")


def _software_spec_export_show_file(target: str) -> str:
    if target == "generic":
        return "project.md"
    if target == "openspec":
        return "propose.md"
    if target == "speckit":
        return "speckit.constitution.md"
    return "index.md"


def _project_definition_required_sections() -> tuple[str, ...]:
    return (
        "Executive Summary",
        "Vision",
        "Domain",
        "Problem",
        "Goals",
        "Non-Goals / Exclusions",
        "Stakeholders / Users",
        "Workflows",
        "Accepted Decisions",
        "Requirements",
        "Constraints",
        "Assumptions",
        "Dependencies",
        "Operating Model / Architecture",
        "Data / Knowledge Model",
        "Priorities",
        "Success Criteria",
        "Validation / Evaluation Method",
        "Risks And Tradeoffs",
        "Open Questions",
        "Pending Proposals",
        "Source Traceability",
    )


def _definition_value(definition: dict[str, object], key: str, default: str = "NEEDS CLARIFICATION") -> str:
    value = definition.get(key)
    if value is None:
        return default
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) or default
    text = str(value).strip()
    return text or default


def _definition_spec(definition: dict[str, object], filename: str) -> str:
    spec = definition.get("spec", {})
    if not isinstance(spec, dict):
        return ""
    return str(spec.get(filename) or "")


def _definition_accepted(definition: dict[str, object]) -> list[dict[str, object]]:
    accepted = definition.get("accepted_proposals", [])
    return accepted if isinstance(accepted, list) else []


def _definition_drafts(definition: dict[str, object]) -> list[Any]:
    drafts = definition.get("draft_proposals", [])
    return drafts if isinstance(drafts, list) else []


def _accepted_bullets(definition: dict[str, object], key: str, limit: int | None = None) -> str:
    lines: list[str] = []
    for item in _definition_accepted(definition)[:limit]:
        if not isinstance(item, dict):
            continue
        value = str(item.get(key) or "").strip()
        proposal_id = str(item.get("proposal_id") or "PROP-???")
        title = str(item.get("title") or proposal_id)
        if value:
            lines.append(f"- **{proposal_id} {title}**: {value}")
    return "\n".join(lines) or "- NEEDS CLARIFICATION"


def _proposal_sources(definition: dict[str, object]) -> str:
    lines: list[str] = []
    for item in _definition_accepted(definition):
        if not isinstance(item, dict):
            continue
        proposal_id = str(item.get("proposal_id") or "PROP-???")
        title = str(item.get("title") or proposal_id)
        source = str(item.get("source") or "")
        lines.append(f"- `{proposal_id}` {title} — `{source}`")
    return "\n".join(lines) or "- No accepted proposals found."


def _pending_proposals(definition: dict[str, object]) -> str:
    lines = [f"- `{item.proposal_id}` {item.title}" for item in _definition_drafts(definition)]
    return "\n".join(lines) or "- None."


def _structure_sections(definition: dict[str, object]) -> str:
    return (
        "## Structure-Specific Detail\n\n"
        "### Design\n\n"
        f"{strip_markdown_title(_definition_spec(definition, 'design.md')) or 'NEEDS CLARIFICATION'}\n\n"
        "### Commands And Interfaces\n\n"
        "```yaml\n"
        f"{_definition_spec(definition, 'commands.yml').strip() or 'commands: []'}\n"
        "\n```\n\n"
        "### Validation\n\n"
        f"{strip_markdown_title(_definition_spec(definition, 'acceptance.md')) or 'NEEDS CLARIFICATION'}\n"
    )


def _project_definition_markdown(definition: dict[str, object]) -> str:
    project_name = _definition_value(definition, "project_name", "Project")
    change_id = _definition_value(definition, "change_id")
    change_title = _definition_value(definition, "change_title")
    requirements = strip_markdown_title(_definition_spec(definition, "requirements.md")) or "NEEDS CLARIFICATION"
    acceptance = strip_markdown_title(_definition_spec(definition, "acceptance.md")) or "NEEDS CLARIFICATION"
    data_model = _definition_spec(definition, "data-model.yml").strip() or "entities: []"
    return (
        f"# {project_name} Project Definition\n\n"
        "This document is synthesized from accepted P2P memory. It is the canonical generic project export. "
        "Draft or undecided material is listed only as pending or missing information.\n\n"
        "## Executive Summary\n\n"
        f"{_definition_value(definition, 'change_summary')}\n\n"
        "## Vision\n\n"
        "Organize confused, distributed, and discontinuous project intent into a governed project definition that agents can use without rediscovering context from scratch.\n\n"
        "## Domain\n\n"
        f"{_definition_value(definition, 'domain')}\n\n"
        "## Problem\n\n"
        f"{_accepted_bullets(definition, 'problem', limit=8)}\n\n"
        "## Goals\n\n"
        f"{_accepted_bullets(definition, 'goals', limit=8)}\n\n"
        "## Non-Goals / Exclusions\n\n"
        f"{_accepted_bullets(definition, 'non_goals', limit=8)}\n\n"
        "## Stakeholders / Users\n\n"
        "- Humans supervise outputs and make governance decisions.\n"
        "- AI agents use P2P memory and exports as structured project cognition.\n"
        "- Downstream tools receive initialization prompts or documents, not synthetic ownership of P2P state.\n\n"
        "## Workflows\n\n"
        "- Capture rough ideas as intake, proposals, or contributions.\n"
        "- Decide accepted direction through owner-controlled P2P governance.\n"
        "- Derive Change Sets and exports from accepted memory.\n"
        "- Use target-specific outputs to initialize downstream agent workflows.\n\n"
        "## Accepted Decisions\n\n"
        f"{_accepted_bullets(definition, 'decision', limit=12)}\n\n"
        "## Requirements\n\n"
        f"{requirements}\n\n"
        "## Constraints\n\n"
        "- Exports must not invent requirements unsupported by accepted P2P artifacts.\n"
        "- Missing information must be marked as NEEDS CLARIFICATION.\n"
        "- Draft proposals must not be treated as accepted project truth.\n\n"
        "## Assumptions\n\n"
        "- Accepted P2P proposals and decisions are authoritative project memory.\n"
        "- Target-specific exports are initialization artifacts for agents or downstream tools.\n\n"
        "## Dependencies\n\n"
        f"- Source Change Set: `{change_id}` {change_title}\n"
        "- P2P software spec artifacts generated before export.\n"
        "- Downstream tools, if used, run outside P2P export.\n\n"
        "## Operating Model / Architecture\n\n"
        f"{strip_markdown_title(_definition_spec(definition, 'design.md')) or 'NEEDS CLARIFICATION'}\n\n"
        "## Data / Knowledge Model\n\n"
        "```yaml\n"
        f"{data_model}\n"
        "\n```\n\n"
        "## Priorities\n\n"
        "- Preserve accepted project intent and governance first.\n"
        "- Produce small agent-consumable outputs instead of downstream-shaped folders.\n"
        "- Keep target-specific exports derived from this project definition.\n\n"
        "## Success Criteria\n\n"
        f"{acceptance}\n\n"
        "## Validation / Evaluation Method\n\n"
        "- Validate required export files exist.\n"
        "- Validate required project definition sections exist.\n"
        "- Validate source traceability is present.\n\n"
        "## Risks And Tradeoffs\n\n"
        "- Removing folder-shaped exports may surprise users of the previous MVP export layout.\n"
        "- Agent-first documents require clear traceability to avoid over-synthesis.\n\n"
        "## Open Questions\n\n"
        "- Which target-specific constraints still require owner clarification?\n\n"
        "## Pending Proposals\n\n"
        f"{_pending_proposals(definition)}\n\n"
        f"{_structure_sections(definition)}\n\n"
        "## Source Traceability\n\n"
        f"- Source Change Set: `{change_id}` {change_title}\n"
        f"{_proposal_sources(definition)}\n"
    )


def _generic_propose_markdown(definition: dict[str, object]) -> str:
    return (
        "# Generic Project Initialization Prompt\n\n"
        "Use the accompanying `project.md` as authoritative project context. "
        "Initialize or continue the project without inventing requirements beyond accepted P2P memory.\n\n"
        "## Prompt\n\n"
        f"Build or continue the project described in `project.md`: {_definition_value(definition, 'project_name', 'Project')}.\n\n"
        "Respect accepted decisions, constraints, non-goals, and source traceability. "
        "Mark missing details as NEEDS CLARIFICATION.\n"
    )


def _openspec_propose_markdown(definition: dict[str, object]) -> str:
    return (
        "# OpenSpec Proposal Input\n\n"
        "Use this as the proposal-oriented initialization input for OpenSpec or an OpenSpec-aware agent.\n\n"
        "## Problem\n\n"
        f"{_accepted_bullets(definition, 'problem', limit=6)}\n\n"
        "## Proposed Change\n\n"
        f"{_accepted_bullets(definition, 'proposal', limit=6)}\n\n"
        "## Scope\n\n"
        f"{_accepted_bullets(definition, 'goals', limit=6)}\n\n"
        "## Out Of Scope\n\n"
        f"{_accepted_bullets(definition, 'non_goals', limit=6)}\n\n"
        "## Impact\n\n"
        f"- Source Change Set: `{_definition_value(definition, 'change_id')}` {_definition_value(definition, 'change_title')}\n\n"
        "## Risks\n\n"
        "- NEEDS CLARIFICATION: confirm target-specific risks before implementation.\n\n"
        "## Acceptance Criteria\n\n"
        f"{strip_markdown_title(_definition_spec(definition, 'acceptance.md')) or 'NEEDS CLARIFICATION'}\n\n"
        "## Source Traceability\n\n"
        f"{_proposal_sources(definition)}\n"
    )


def _speckit_constitution_markdown(definition: dict[str, object]) -> str:
    return (
        "# Spec Kit Constitution Prompt\n\n"
        "Use this content with `/speckit.constitution`. Establish governing principles from accepted P2P memory.\n\n"
        "## Principles To Establish\n\n"
        "- Preserve accepted project intent and source traceability.\n"
        "- Do not treat draft P2P proposals as accepted requirements.\n"
        "- Mark missing information as NEEDS CLARIFICATION.\n"
        "- Humans supervise outcomes and make governance decisions.\n"
        "- Agents use P2P exports as structured cognition, not as authority to bypass governance.\n\n"
        "## Existing Governance Context\n\n"
        f"{_definition_value(definition, 'constitution', 'NEEDS CLARIFICATION')}\n\n"
        "## Decision Rules\n\n"
        f"{_definition_value(definition, 'decision_rules', 'NEEDS CLARIFICATION')}\n"
    )


def _speckit_specify_markdown(definition: dict[str, object]) -> str:
    return (
        "# Spec Kit Specify Prompt\n\n"
        "Use this content with `/speckit.specify`. Focus on what and why; do not select a tech stack here.\n\n"
        "## What To Build\n\n"
        f"{_accepted_bullets(definition, 'proposal', limit=8)}\n\n"
        "## Why\n\n"
        f"{_accepted_bullets(definition, 'problem', limit=8)}\n\n"
        "## Users And Workflows\n\n"
        "- Humans supervise and decide.\n"
        "- Agents use P2P memory to preserve project context and propose bounded changes.\n\n"
        "## Requirements\n\n"
        f"{strip_markdown_title(_definition_spec(definition, 'requirements.md')) or 'NEEDS CLARIFICATION'}\n\n"
        "## Success Criteria\n\n"
        f"{strip_markdown_title(_definition_spec(definition, 'acceptance.md')) or 'NEEDS CLARIFICATION'}\n"
    )


def _speckit_plan_prompt_markdown(definition: dict[str, object]) -> str:
    return (
        "# Spec Kit Plan Prompt\n\n"
        "Use this content with `/speckit.plan`. Provide technical implementation choices derived from accepted P2P memory.\n\n"
        "## Architecture / Operating Model\n\n"
        f"{strip_markdown_title(_definition_spec(definition, 'design.md')) or 'NEEDS CLARIFICATION'}\n\n"
        "## Implementation Targets\n\n"
        f"{_definition_value(definition, 'implementation_targets')}\n\n"
        "## Data Model\n\n"
        "```yaml\n"
        f"{_definition_spec(definition, 'data-model.yml').strip() or 'entities: []'}\n"
        "\n```\n\n"
        "## Testing And Validation\n\n"
        f"{strip_markdown_title(_definition_spec(definition, 'acceptance.md')) or 'NEEDS CLARIFICATION'}\n\n"
        "## Constraints\n\n"
        "- Preserve P2P provenance.\n"
        "- Do not introduce implementation scope not supported by accepted P2P memory.\n"
    )


class SpecExportService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        show_change_set: Callable[[str], Any],
        status: Callable[[], Any],
        accepted_proposals: Callable[[], list[dict[str, object]]],
        proposal_summaries: Callable[[str | None], list[Any]],
        project_domain: Callable[[], Any] | None = None,
        required_spec_files: Callable[[], tuple[str, ...]] | None = None,
        read_yaml_mapping: Callable[[Path, dict[str, object]], dict[str, object]] | None = None,
        read_optional: Callable[[Path], str] | None = None,
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.show_change_set = show_change_set
        self.status = status
        self.accepted_proposals = accepted_proposals
        self.proposal_summaries = proposal_summaries
        self.project_domain = project_domain or (lambda: None)
        self.export_targets = software_spec_export_targets
        self.required_spec_files = required_spec_files or (
            lambda: ("index.md", "requirements.md", "design.md", "commands.yml", "data-model.yml", "acceptance.md", "provenance.yml")
        )
        self.read_yaml_mapping = read_yaml_mapping or self._read_yaml_mapping
        self.read_optional = read_optional or self._read_optional

    def export(self, change_id: str, target: str) -> SoftwareSpecExportStatus:
        target = target.lower()
        if target not in self.export_targets():
            raise ValueError(f"Unsupported software spec export target: {target}")
        spec_dir = self.p2p_dir / "outputs" / "software-spec" / change_id
        if not spec_dir.is_dir():
            raise ValueError("Software spec not found. Run `p2p spec refresh --change CHANGE-XXX` first.")
        for filename in self.required_spec_files():
            if not (spec_dir / filename).exists():
                raise ValueError(f"Missing required software spec artifact: {filename}")

        change = self.show_change_set(change_id)
        export_dir = self.p2p_dir / "outputs" / "spec-export" / change_id / target
        if export_dir.exists():
            shutil.rmtree(export_dir)
        export_dir.mkdir(parents=True, exist_ok=True)

        files = self._export_files(
            change_id,
            target,
            change.title,
            spec_dir,
            str(spec_dir.relative_to(self.root)),
            self.project_definition(change_id, change, spec_dir),
        )
        for filename, content in files.items():
            output_path = export_dir / filename
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(content, encoding="utf-8")

        return SoftwareSpecExportStatus(
            change_id=change_id,
            target=target,
            title=change.title,
            status="exported",
            path=export_dir.relative_to(self.root),
        )

    def statuses(self) -> list[SoftwareSpecExportStatus]:
        exports_dir = self.p2p_dir / "outputs" / "spec-export"
        statuses: list[SoftwareSpecExportStatus] = []
        for change_dir in sorted(exports_dir.iterdir()) if exports_dir.exists() else []:
            if not change_dir.is_dir():
                continue
            change_id = change_dir.name
            try:
                title = self.show_change_set(change_id).title
            except ValueError:
                title = change_id
            for target_dir in sorted(change_dir.iterdir()):
                if not target_dir.is_dir():
                    continue
                try:
                    required = self._export_required_files(change_id, target_dir.name, target_dir)
                except ValueError:
                    required = [Path("index.md")]
                status = "exported" if all((target_dir / path).exists() for path in required) else "incomplete"
                statuses.append(
                    SoftwareSpecExportStatus(
                        change_id=change_id,
                        target=target_dir.name,
                        title=title,
                        status=status,
                        path=target_dir.relative_to(self.root),
                    )
                )
        return statuses

    def show(self, change_id: str, target: str) -> str:
        target = target.lower()
        export_dir = self.p2p_dir / "outputs" / "spec-export" / change_id / target
        path = export_dir / self._export_show_file(target)
        if not path.exists():
            raise ValueError("Software spec export not found. Run `p2p spec export --change CHANGE-XXX --target TARGET` first.")
        return path.read_text(encoding="utf-8")

    def validate(self, change_id: str, target: str) -> SoftwareSpecExportValidation:
        target = target.lower()
        if target not in self.export_targets():
            raise ValueError(f"Unsupported software spec export target: {target}")
        export_dir = self.p2p_dir / "outputs" / "spec-export" / change_id / target
        if not export_dir.is_dir():
            raise ValueError("Software spec export not found. Run `p2p spec export --change CHANGE-XXX --target TARGET` first.")

        checked: list[Path] = []
        for relative in self._export_required_files(change_id, target, export_dir):
            path = export_dir / relative
            if not path.exists():
                raise ValueError(f"Missing required software spec export artifact: {relative}")
            checked.append(path.relative_to(self.root))

        if target == "generic":
            project_text = (export_dir / "project.md").read_text(encoding="utf-8")
            for section in _project_definition_required_sections():
                if not markdown_has_section(project_text, section):
                    raise ValueError(f"Missing required project definition section: {section}")
            if "## Source Traceability" not in project_text:
                raise ValueError("Missing required project definition source traceability")

        return SoftwareSpecExportValidation(
            change_id=change_id,
            target=target,
            path=export_dir.relative_to(self.root),
            checked=checked,
        )

    def project_definition(self, change_id: str, change: Any, spec_dir: Path) -> dict[str, object]:
        project_data = self.read_yaml_mapping(self.p2p_dir / "project.yml", {})
        project = project_data.get("project", {})
        if not isinstance(project, dict):
            project = {}
        domain_state = self.project_domain()
        descriptor = getattr(domain_state, "descriptor", None)
        source_spec = {filename: self.read_optional(spec_dir / filename) for filename in self.required_spec_files()}
        return {
            "project_name": str(project.get("name") or self.status().project_name),
            "domain": getattr(descriptor, "name", "") or "Unclassified",
            "change_id": change_id,
            "change_title": change.title,
            "change_summary": change.summary,
            "execution_domains": change.execution_domains,
            "implementation_targets": change.implementation_targets,
            "spec_targets": change.spec_targets,
            "export_targets": change.export_targets,
            "accepted_proposals": self.accepted_proposals(),
            "draft_proposals": self.proposal_summaries("draft"),
            "spec": source_spec,
            "constitution": self.read_optional(self.p2p_dir / "governance" / "constitution.md"),
            "decision_rules": self.read_optional(self.p2p_dir / "governance" / "decision-rules.md"),
            "rubrics": self.read_optional(self.p2p_dir / "project" / "rubrics.yml"),
            "assessment": self.read_optional(self.p2p_dir / "project" / "assessment.yml"),
            "maturity": self.read_optional(self.p2p_dir / "project" / "maturity-assessment.yml"),
        }

    def _export_files(
        self,
        change_id: str,
        target: str,
        title: str,
        spec_dir: Path,
        software_spec_path: str,
        definition: dict[str, object],
    ) -> dict[str, str]:
        if target == "generic":
            return {
                "project.md": _project_definition_markdown(definition),
                "propose.md": _generic_propose_markdown(definition),
            }
        if target == "openspec":
            return {
                "propose.md": _openspec_propose_markdown(definition),
            }
        if target == "speckit":
            return {
                "speckit.constitution.md": _speckit_constitution_markdown(definition),
                "speckit.specify.md": _speckit_specify_markdown(definition),
                "speckit.plan.md": _speckit_plan_prompt_markdown(definition),
            }
        raise ValueError(f"Unsupported software spec export target: {target}")

    def _export_required_files(self, change_id: str, target: str, export_dir: Path) -> list[Path]:
        return _software_spec_export_required_files(target)

    def _export_show_file(self, target: str) -> str:
        return _software_spec_export_show_file(target)

    def _read_optional(self, path: Path) -> str:
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def _read_yaml_mapping(self, path: Path, default: dict[str, object]) -> dict[str, object]:
        if not path.exists():
            return default
        data = load_yaml(path.read_bytes())
        if data is None:
            return default
        if not isinstance(data, dict):
            raise ValueError(f"Invalid YAML mapping: {path}")
        return data
