from __future__ import annotations

from pathlib import Path


def export_openspec(proposal_dir: Path, output_dir: Path) -> None:
    """Create a minimal OpenSpec-style change directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    mappings = {
        "proposal.md": "proposal.md",
        "execution-plan.md": "design.md",
        "tasks.yml": "tasks.yml",
    }
    for source, target in mappings.items():
        source_path = proposal_dir / source
        if source_path.exists():
            (output_dir / target).write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")

