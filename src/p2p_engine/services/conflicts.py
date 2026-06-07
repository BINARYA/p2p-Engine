from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from p2p_engine.foundation.files import (
    read_yaml_mapping as _read_yaml_mapping,
    yaml_dump as _yaml_dump,
)


@dataclass(frozen=True)
class ConflictStatus:
    conflicts_count: int
    conflicts: list[dict[str, object]]
    conflicts_file: Path


class ConflictMemoryService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        find_proposal_dir: Callable[[str], Path],
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.find_proposal_dir = find_proposal_dir

    def record(
        self,
        *,
        proposals: list[str],
        conflict_type: str,
        reason: str,
        winner: str | None,
    ) -> ConflictStatus:
        if len(proposals) < 2:
            raise ValueError("At least two proposals are required to record a conflict.")
        for proposal_id in proposals:
            self.find_proposal_dir(proposal_id)
        if winner is not None and winner not in proposals:
            raise ValueError("Conflict winner must be one of the conflicting proposals.")

        path = self._path()
        path.parent.mkdir(parents=True, exist_ok=True)
        data = _read_yaml_mapping(path, default={"conflicts": []})
        conflicts = data.setdefault("conflicts", [])
        if not isinstance(conflicts, list):
            raise ValueError("Invalid conflicts.yml: expected `conflicts` list.")
        conflict_id = f"CONFLICT-{len(conflicts) + 1:03d}"
        conflicts.append(
            {
                "id": conflict_id,
                "type": conflict_type,
                "proposals": proposals,
                "winner": winner,
                "rejected": [proposal for proposal in proposals if winner and proposal != winner],
                "reason": reason,
                "recorded_on": date.today().isoformat(),
            }
        )
        path.write_text(_yaml_dump(data), encoding="utf-8")
        return self.status()

    def status(self) -> ConflictStatus:
        path = self._path()
        data = _read_yaml_mapping(path, default={"conflicts": []})
        conflicts = data.get("conflicts", [])
        if not isinstance(conflicts, list):
            raise ValueError("Invalid conflicts.yml: expected `conflicts` list.")
        normalized = [conflict for conflict in conflicts if isinstance(conflict, dict)]
        return ConflictStatus(
            conflicts_count=len(normalized),
            conflicts=normalized,
            conflicts_file=path.relative_to(self.root),
        )

    def _path(self) -> Path:
        return self.p2p_dir / "project" / "conflicts.yml"
