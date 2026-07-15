from __future__ import annotations

from pathlib import Path

import yaml


def initialize_project(root: Path) -> Path:
    proposals = root / ".p2p" / "proposals"
    proposals.mkdir(parents=True, exist_ok=True)
    return proposals


def write_proposal(
    root: Path,
    proposal_id: str,
    *,
    title: str = "Example Proposal",
    status: str = "draft",
    problem: str = "The project loses relevant decision context.",
    goals: tuple[str, ...] = ("Preserve source evidence.",),
    non_goals: tuple[str, ...] = ("Replace canonical files.",),
    proposal: str = "Build a derived decision context index.",
    acceptance: tuple[str, ...] = ("Context retrieval is deterministic.",),
    decision_outcome: str | None = None,
    decision_reason: str = "The architecture direction is approved.",
    decision_date: str = "2026-07-15",
    approver: str = "owner",
    newline: str = "\n",
) -> Path:
    proposals_root = initialize_project(root)
    slug = proposal_id.lower() + "-example"
    proposal_dir = proposals_root / slug
    proposal_dir.mkdir(parents=True, exist_ok=True)
    proposal_text = newline.join(
        (
            f"# {proposal_id} - {title}",
            "",
            "## Status",
            "",
            f"`{status}`",
            "",
            "## Problem",
            "",
            problem,
            "",
            "## Goals",
            "",
            *[f"- {item}" for item in goals],
            "",
            "## Non-Goals",
            "",
            *[f"- {item}" for item in non_goals],
            "",
            "## Proposal",
            "",
            proposal,
            "",
            "## Acceptance Criteria",
            "",
            *[f"- {item}" for item in acceptance],
            "",
            "## Decision",
            "",
            "Pending.",
            "",
        )
    )
    (proposal_dir / "proposal.md").write_text(proposal_text, encoding="utf-8", newline="")
    if decision_outcome is not None:
        decision_text = newline.join(
            (
                f"# Decision - {proposal_id}",
                "",
                "## Status",
                "",
                f"`{decision_outcome}`",
                "",
                "## Outcome",
                "",
                decision_outcome,
                "",
                "## Reason",
                "",
                decision_reason,
                "",
                "## Date",
                "",
                decision_date,
                "",
                "## Approver",
                "",
                approver,
                "",
            )
        )
        (proposal_dir / "decision.md").write_text(decision_text, encoding="utf-8", newline="")
    return proposal_dir


def project_files(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def write_yaml(root: Path, relative_path: str, payload: object) -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def write_markdown(
    root: Path,
    relative_path: str,
    *,
    title: str,
    frontmatter: dict[str, object] | None = None,
    sections: tuple[tuple[str, str], ...] = (),
) -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    if frontmatter is not None:
        lines.extend(("---", yaml.safe_dump(frontmatter, sort_keys=False).rstrip(), "---", ""))
    lines.extend((f"# {title}", ""))
    for label, text in sections:
        lines.extend((f"## {label}", "", text, ""))
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
