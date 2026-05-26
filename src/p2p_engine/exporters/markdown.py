from __future__ import annotations

from pathlib import Path


def export_markdown(proposal_dir: Path, output_path: Path) -> None:
    """Export a proposal folder into a single Markdown document."""
    parts = []
    for filename in ("proposal.md", "decision.md", "execution-plan.md"):
        path = proposal_dir / filename
        if path.exists():
            parts.append(path.read_text(encoding="utf-8"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n\n---\n\n".join(parts), encoding="utf-8")

