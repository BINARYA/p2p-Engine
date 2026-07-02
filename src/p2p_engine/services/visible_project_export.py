from __future__ import annotations

import shutil
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from p2p_engine.core.project_verticals import ProjectDefinitionView, ProjectReadinessReview, VerticalLockStatus
from p2p_engine.foundation.markdown import read_markdown_section


@dataclass(frozen=True)
class VisibleProjectExportResult:
    status: str
    latest_path: Path
    archived_path: Path | None
    exports_dir: Path


@dataclass(frozen=True)
class VisibleProjectExportStatus:
    latest_exists: bool
    latest_path: Path
    review_paths: list[Path]
    exports_dir: Path


def _read_optional(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _section_or_default(text: str, section: str, default: str = "Not recorded.") -> str:
    return read_markdown_section(text, section) or default


def _artifact_section(proposal_dir: Path, filename: str, default: str = "Not recorded.") -> str:
    content = _read_optional(proposal_dir / filename).strip()
    if not content:
        return default
    return content


def _relative(path: Path, root: Path) -> Path:
    try:
        return path.relative_to(root)
    except ValueError:
        return path


class VisibleProjectExportService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        project_name: Callable[[], str],
        accepted_proposals: Callable[[], list[dict[str, object]]],
        project_readiness_review: Callable[[], ProjectReadinessReview] | None = None,
        project_vertical_lock_status: Callable[[], VerticalLockStatus] | None = None,
        project_definition_view: Callable[[], ProjectDefinitionView] | None = None,
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.project_name = project_name
        self.accepted_proposals = accepted_proposals
        self.project_readiness_review = project_readiness_review
        self.project_vertical_lock_status = project_vertical_lock_status
        self.project_definition_view = project_definition_view

    def export(self) -> VisibleProjectExportResult:
        outputs_dir = self.root / "outputs"
        latest_dir = outputs_dir / "latest"
        archived_path = self._archive_latest(outputs_dir, latest_dir)

        exports_dir = latest_dir / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        project_path = latest_dir / "project.md"
        project_path.write_text(self._render_project_markdown(), encoding="utf-8")

        return VisibleProjectExportResult(
            status="exported",
            latest_path=_relative(project_path, self.root),
            archived_path=_relative(archived_path, self.root) if archived_path else None,
            exports_dir=_relative(exports_dir, self.root),
        )

    def status(self) -> VisibleProjectExportStatus:
        outputs_dir = self.root / "outputs"
        latest_path = outputs_dir / "latest" / "project.md"
        review_paths = [
            _relative(path, self.root)
            for path in sorted(outputs_dir.glob("review-[0-9][0-9][0-9]"))
            if path.is_dir()
        ]
        return VisibleProjectExportStatus(
            latest_exists=latest_path.exists(),
            latest_path=_relative(latest_path, self.root),
            review_paths=review_paths,
            exports_dir=_relative(outputs_dir / "latest" / "exports", self.root),
        )

    def _archive_latest(self, outputs_dir: Path, latest_dir: Path) -> Path | None:
        if not latest_dir.exists() or not any(latest_dir.iterdir()):
            return None
        review_dir = self._next_review_dir(outputs_dir)
        review_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(latest_dir), str(review_dir))
        return review_dir

    def _next_review_dir(self, outputs_dir: Path) -> Path:
        index = 1
        while True:
            candidate = outputs_dir / f"review-{index:03d}"
            if not candidate.exists():
                return candidate
            index += 1

    def _render_project_markdown(self) -> str:
        project_name = self.project_name()
        accepted = self.accepted_proposals()
        lines: list[str] = [
            f"# {project_name} Project Definition",
            "",
            "## Generated Metadata",
            "",
            f"- generated_at: {date.today().isoformat()}",
            "- generator: p2p project export",
            "- source_of_truth: .p2p/",
            "- output_role: generated human-facing project definition",
            "- default_output: outputs/latest/project.md",
            "- profile_exports: outputs/latest/exports/<profile-or-vertical>/",
            "",
            "## Executive Summary",
            "",
            self._executive_summary(accepted),
            "",
            "## Project Purpose",
            "",
            self._proposal_sections(accepted, "Proposal"),
            "",
            "## Domain And Context",
            "",
            self._proposal_sections(accepted, "Context"),
            "",
            "## Scope",
            "",
            self._scope_section(accepted),
            "",
            "## Accepted Proposals And Decisions",
            "",
            self._accepted_proposals_section(accepted),
            "",
            "## Requirements And Acceptance",
            "",
            self._proposal_sections(accepted, "Acceptance Criteria"),
            "",
            "## Alternatives And Tradeoffs",
            "",
            self._artifact_sections(accepted, ("alternatives.md", "findings.md")),
            "",
            "## Risks",
            "",
            self._artifact_sections(accepted, ("risks.md",)),
            "",
            "## Assumptions",
            "",
            self._artifact_sections(accepted, ("assumptions.md",)),
            "",
            "## Open Questions",
            "",
            self._artifact_sections(accepted, ("open-questions.md",)),
            "",
            "## Readiness",
            "",
            self._vertical_readiness_section(),
            "",
            self._vertical_state_summary_section(),
            "",
            self._artifact_sections(accepted, ("readiness.yml",)),
            "",
            "## Delivery And Export Context",
            "",
            (
                "The default visible export is this chaptered Markdown document. "
                "Specialized vertical or tool-specific exports belong under "
                "`outputs/latest/exports/<profile-or-vertical>/`. Existing "
                "`.p2p/outputs` spec exports remain compatibility artifacts unless "
                "a separate migration changes them."
            ),
            "",
            "## Source Traceability",
            "",
            self._traceability_section(accepted),
            "",
        ]
        return "\n".join(lines)

    def _vertical_state_summary_section(self) -> str:
        lines = ["### Vertical Runtime State", ""]
        if self.project_vertical_lock_status is None:
            lines.append("- lock_status: unavailable")
        else:
            try:
                lock_status = self.project_vertical_lock_status()
            except ValueError:
                lock_status = None
            if lock_status is None:
                lines.append("- lock_status: unavailable")
            else:
                lines.append(f"- lock_status: {lock_status.status}")
                if lock_status.locked:
                    lines.append(f"- locked_vertical: {lock_status.locked.vertical_id}")
        if self.project_definition_view is None:
            lines.append("- definition_state: unavailable")
        else:
            try:
                definition = self.project_definition_view()
            except ValueError:
                definition = None
            if definition is None:
                lines.append("- definition_state: unavailable")
            else:
                lines.append(f"- definition_state_exists: {str(definition.exists).lower()}")
                lines.append(f"- definition_state_valid: {str(definition.valid).lower()}")
                if definition.state:
                    counts: dict[str, int] = {}
                    for section in definition.state.sections:
                        counts[section.status] = counts.get(section.status, 0) + 1
                    for status, count in sorted(counts.items()):
                        lines.append(f"- definition_sections_{status}: {count}")
        return "\n".join(lines)

    def _executive_summary(self, accepted: list[dict[str, object]]) -> str:
        if not accepted:
            return "No accepted proposals are recorded yet."
        return (
            f"This project definition synthesizes {len(accepted)} accepted proposal"
            f"{'' if len(accepted) == 1 else 's'} from P2P-managed state into a "
            "human-facing document. It is generated output; `.p2p/` remains the "
            "managed source of truth."
        )

    def _vertical_readiness_section(self) -> str:
        if self.project_readiness_review is None:
            return "Vertical readiness review not available."
        try:
            review = self.project_readiness_review()
        except ValueError:
            return "Vertical readiness review not available."
        lines = [
            "### Project Vertical Skeleton",
            "",
            f"- active_vertical: {review.active_vertical_id}",
            f"- source: {review.vertical_source}",
            f"- fallback_used: {str(review.fallback_used).lower()}",
            "",
            "### Vertical Coverage",
            "",
        ]
        if not review.sections:
            lines.append("No vertical sections are available.")
        else:
            for section in review.sections:
                proposals = ", ".join(section.proposals) if section.proposals else "none"
                lines.append(f"- {section.section_id}: {section.status} (proposals: {proposals})")
        if review.generated_questions:
            lines.extend(["", "### Vertical Questions", ""])
            lines.extend(f"- {question}" for question in review.generated_questions)
        return "\n".join(lines)

    def _proposal_sections(self, accepted: list[dict[str, object]], section: str) -> str:
        if not accepted:
            return "Not recorded."
        lines: list[str] = []
        for item in accepted:
            proposal_dir = Path(str(item["path"]))
            proposal_text = _read_optional(proposal_dir / "proposal.md")
            lines.extend(
                [
                    f"### {item['proposal_id']} - {item['title']}",
                    "",
                    _section_or_default(proposal_text, section),
                    "",
                ]
            )
        return "\n".join(lines).strip()

    def _scope_section(self, accepted: list[dict[str, object]]) -> str:
        if not accepted:
            return "Not recorded."
        lines: list[str] = []
        for item in accepted:
            proposal_dir = Path(str(item["path"]))
            proposal_text = _read_optional(proposal_dir / "proposal.md")
            lines.extend(
                [
                    f"### {item['proposal_id']} - {item['title']}",
                    "",
                    "#### Goals",
                    "",
                    _section_or_default(proposal_text, "Goals"),
                    "",
                    "#### Non-Goals",
                    "",
                    _section_or_default(proposal_text, "Non-Goals"),
                    "",
                    "#### Suggested Scope",
                    "",
                    _artifact_section(proposal_dir, "suggested-scope.md"),
                    "",
                ]
            )
        return "\n".join(lines).strip()

    def _accepted_proposals_section(self, accepted: list[dict[str, object]]) -> str:
        if not accepted:
            return "No accepted proposals are recorded yet."
        lines: list[str] = []
        for item in accepted:
            proposal_dir = Path(str(item["path"]))
            decision_text = _read_optional(proposal_dir / "decision.md")
            reason = read_markdown_section(decision_text, "Reason") or "Not recorded."
            lines.extend(
                [
                    f"- {item['proposal_id']} - {item['title']}",
                    f"  - source: {item['source']}",
                    f"  - decision_reason: {reason}",
                ]
            )
        return "\n".join(lines)

    def _artifact_sections(self, accepted: list[dict[str, object]], filenames: tuple[str, ...]) -> str:
        if not accepted:
            return "Not recorded."
        lines: list[str] = []
        any_content = False
        for item in accepted:
            proposal_dir = Path(str(item["path"]))
            proposal_lines: list[str] = []
            for filename in filenames:
                content = _read_optional(proposal_dir / filename).strip()
                if not content:
                    continue
                proposal_lines.extend([f"#### {filename}", "", content, ""])
            if proposal_lines:
                any_content = True
                lines.extend([f"### {item['proposal_id']} - {item['title']}", "", *proposal_lines])
        return "\n".join(lines).strip() if any_content else "Not recorded."

    def _traceability_section(self, accepted: list[dict[str, object]]) -> str:
        if not accepted:
            return "- No accepted proposal sources recorded."
        lines = ["- .p2p/project.yml", "- .p2p/proposals/"]
        for item in accepted:
            lines.append(f"- {item['source']}")
        return "\n".join(lines)
