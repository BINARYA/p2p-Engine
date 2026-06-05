from __future__ import annotations

import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SoftwareSpecExportStatus:
    change_id: str
    target: str
    title: str
    status: str
    path: Path


@dataclass(frozen=True)
class SoftwareSpecExportValidation:
    change_id: str
    target: str
    path: Path
    checked: list[Path]


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
        export_targets: Callable[[], tuple[str, ...]] | None = None,
        required_spec_files: Callable[[], tuple[str, ...]] | None = None,
        export_files: Callable[[str, str, str, Path, str, dict[str, object]], dict[str, str]] | None = None,
        export_required_files: Callable[[str, str, Path], list[Path]] | None = None,
        export_show_file: Callable[[str], str] | None = None,
        project_definition_sections: Callable[[], tuple[str, ...]] | None = None,
        markdown_has_section: Callable[[str, str], bool] | None = None,
        read_yaml_mapping: Callable[[Path, dict[str, object]], dict[str, object]] | None = None,
        read_optional: Callable[[Path], str] | None = None,
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.show_change_set = show_change_set
        self.status = status
        self.accepted_proposals = accepted_proposals
        self.proposal_summaries = proposal_summaries
        self.export_targets = export_targets or (lambda: ("generic", "openspec", "speckit"))
        self.required_spec_files = required_spec_files or (
            lambda: ("index.md", "requirements.md", "design.md", "commands.yml", "data-model.yml", "acceptance.md", "provenance.yml")
        )
        self.export_files = export_files
        self.export_required_files = export_required_files
        self.export_show_file = export_show_file
        self.project_definition_sections = project_definition_sections
        self.markdown_has_section = markdown_has_section
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
            if self.project_definition_sections is None or self.markdown_has_section is None:
                raise ValueError("Project definition validators are not configured")
            project_text = (export_dir / "project.md").read_text(encoding="utf-8")
            for section in self.project_definition_sections():
                if not self.markdown_has_section(project_text, section):
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
        source_spec = {filename: self.read_optional(spec_dir / filename) for filename in self.required_spec_files()}
        return {
            "project_name": str(project.get("name") or self.status().project_name),
            "domain": str(project.get("domain") or "generic"),
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
        if self.export_files is None:
            raise ValueError("Software spec export renderer is not configured")
        return self.export_files(change_id, target, title, spec_dir, software_spec_path, definition)

    def _export_required_files(self, change_id: str, target: str, export_dir: Path) -> list[Path]:
        if self.export_required_files is None:
            if target == "generic":
                return [Path("project.md"), Path("propose.md")]
            if target == "openspec":
                return [Path("propose.md")]
            if target == "speckit":
                return [Path("speckit.constitution.md"), Path("speckit.specify.md"), Path("speckit.plan.md")]
            raise ValueError(f"Unsupported software spec export target: {target}")
        return self.export_required_files(change_id, target, export_dir)

    def _export_show_file(self, target: str) -> str:
        if self.export_show_file is not None:
            return self.export_show_file(target)
        if target == "generic":
            return "project.md"
        if target == "openspec":
            return "propose.md"
        if target == "speckit":
            return "speckit.constitution.md"
        return "index.md"

    def _read_optional(self, path: Path) -> str:
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def _read_yaml_mapping(self, path: Path, default: dict[str, object]) -> dict[str, object]:
        return default
