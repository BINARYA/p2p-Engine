from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml

from p2p_engine.core.mutation_preview import (
    MutationPreview,
    MutationPreviewService,
    MutationResult,
    semantic_sha256,
    source_precondition,
)

from p2p_engine.foundation.files import (
    read_yaml_mapping as _read_yaml_mapping,
    yaml_dump as _yaml_dump,
)
from p2p_engine.foundation.yaml_loaders import load_yaml
from p2p_engine.services.workspace_transactions import AtomicMutationWriter


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
        atomic_writer: AtomicMutationWriter | None = None,
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.find_proposal_dir = find_proposal_dir
        self.atomic_writer = atomic_writer or AtomicMutationWriter(root=root, p2p_dir=p2p_dir)

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

    def show(self, conflict_id: str) -> dict[str, object]:
        return dict(self._find_conflict(conflict_id)[1])

    def preview_update(
        self,
        conflict_id: str,
        patch: dict[str, object],
        *,
        actor: str,
    ) -> MutationPreview:
        path = self._path()
        data = _read_yaml_mapping(path, default={"conflicts": []})
        index, current = self._find_conflict(conflict_id, data=data)
        candidate_record = self._updated_record(conflict_id, current, patch, actor=actor)
        candidate_data = yaml.safe_load(yaml.safe_dump(data, sort_keys=False))
        conflicts = candidate_data.get("conflicts") if isinstance(candidate_data, dict) else None
        if not isinstance(conflicts, list):
            raise ValueError("Invalid conflicts.yml: expected `conflicts` list.")
        conflicts[index] = candidate_record
        relative = path.relative_to(self.root).as_posix()
        current_bytes = path.read_bytes() if path.exists() else None
        authority = "owner_confirmed" if _actor_role(self.p2p_dir / "project" / "permissions.yml", actor) == "owner" else "owner_required"
        return MutationPreviewService.build(
            operation_id=f"conflict-update:{conflict_id}",
            targets=(relative,),
            actor=actor,
            authority=authority,
            sources=(source_precondition(relative, current_bytes),),
            candidate_semantics={relative: candidate_data},
            semantic_diff={
                relative: {
                    "conflict_id": conflict_id,
                    "before_semantic_sha256": semantic_sha256(current),
                    "candidate_semantic_sha256": semantic_sha256(candidate_record),
                    "changed_fields": sorted(
                        key for key in candidate_record if candidate_record.get(key) != current.get(key)
                    ),
                }
            },
            blockers=() if authority == "owner_confirmed" else (authority,),
        )

    def update(
        self,
        conflict_id: str,
        patch: dict[str, object],
        *,
        preview_token: str,
        actor: str,
        confirm: bool,
    ) -> MutationResult:
        preview = self.preview_update(conflict_id, patch, actor=actor)
        if not confirm:
            return MutationResult(
                status="blocked",
                operation_id=preview.operation_id,
                preview_token=preview.preview_token,
                actor=actor,
                message="Explicit confirmation is required for conflict correction.",
            )
        if preview.preview_token != preview_token:
            return MutationResult(
                status="stale_preview",
                operation_id=preview.operation_id,
                preview_token=preview.preview_token,
                actor=actor,
                message="Conflict source or candidate patch changed after preview.",
            )
        if not preview.apply_allowed:
            return MutationResult(
                status="blocked",
                operation_id=preview.operation_id,
                preview_token=preview.preview_token,
                actor=actor,
                message="Actor is not authorized to update project conflict memory.",
            )
        data = _read_yaml_mapping(self._path(), default={"conflicts": []})
        index, current = self._find_conflict(conflict_id, data=data)
        candidate = yaml.safe_load(yaml.safe_dump(data, sort_keys=False))
        conflicts = candidate.get("conflicts") if isinstance(candidate, dict) else None
        if not isinstance(conflicts, list):
            raise ValueError("Invalid conflicts.yml: expected `conflicts` list.")
        conflicts[index] = self._updated_record(conflict_id, current, patch, actor=actor)
        relative = self._path().relative_to(self.root).as_posix()
        return self.atomic_writer.apply(
            operation_id=preview.operation_id,
            candidates={relative: _yaml_dump(candidate).encode("utf-8")},
            sources=preview.source_preconditions,
            preview_token=preview.preview_token,
            actor=actor,
        )

    def _find_conflict(
        self,
        conflict_id: str,
        *,
        data: dict[str, object] | None = None,
    ) -> tuple[int, dict[str, object]]:
        payload = data if data is not None else _read_yaml_mapping(self._path(), default={"conflicts": []})
        conflicts = payload.get("conflicts", [])
        if not isinstance(conflicts, list):
            raise ValueError("Invalid conflicts.yml: expected `conflicts` list.")
        for index, conflict in enumerate(conflicts):
            if isinstance(conflict, dict) and conflict.get("id") == conflict_id:
                return index, conflict
        raise ValueError(f"Conflict not found: {conflict_id}")

    def _updated_record(
        self,
        conflict_id: str,
        current: dict[str, object],
        patch: dict[str, object],
        *,
        actor: str,
    ) -> dict[str, object]:
        allowed = {"type", "proposals", "winner", "rejected", "reason", "provenance"}
        unknown = set(patch) - allowed
        if unknown:
            raise ValueError(f"Unsupported conflict patch field: {sorted(unknown)[0]}")
        if "id" in patch or "conflicts" in patch:
            raise ValueError("Conflict correction updates one stable id and cannot append a record.")
        candidate = dict(current)
        candidate.update(patch)
        candidate["id"] = conflict_id
        conflict_type = str(candidate.get("type") or "").strip()
        reason = str(candidate.get("reason") or "").strip()
        proposals_raw = candidate.get("proposals")
        if not conflict_type or not reason:
            raise ValueError("Conflict type and reason are required.")
        if not isinstance(proposals_raw, list) or not all(isinstance(item, str) for item in proposals_raw):
            raise ValueError("Conflict proposals must be a sequence of proposal ids.")
        proposals = [item.strip() for item in proposals_raw if item.strip()]
        if len(proposals) < 2 or len(set(proposals)) != len(proposals):
            raise ValueError("Conflict proposals must contain at least two unique proposal ids.")
        for proposal_id in proposals:
            self.find_proposal_dir(proposal_id)
        winner_raw = candidate.get("winner")
        winner = str(winner_raw or "").strip()
        if winner and winner not in proposals:
            raise ValueError("Conflict winner must be one of the conflicting proposals.")
        rejected_raw = candidate.get("rejected", [])
        if rejected_raw is None:
            rejected_raw = []
        if not isinstance(rejected_raw, list) or not all(isinstance(item, str) for item in rejected_raw):
            raise ValueError("Conflict rejected must be a sequence of proposal ids.")
        rejected = [item.strip() for item in rejected_raw if item.strip()]
        if any(item not in proposals or item == winner for item in rejected) or len(set(rejected)) != len(rejected):
            raise ValueError("Conflict rejected values must be unique non-winner conflicting proposals.")
        if winner and set(rejected) != set(proposals) - {winner}:
            raise ValueError("Resolved conflict must reject every non-winning proposal.")
        provenance = candidate.get("provenance", {})
        if provenance is None:
            provenance = {}
        if not isinstance(provenance, dict):
            raise ValueError("Conflict provenance must be a mapping.")
        candidate.update(
            {
                "type": conflict_type,
                "proposals": proposals,
                "winner": winner or None,
                "rejected": rejected,
                "reason": reason,
                "provenance": {**provenance, "updated_by": actor},
            }
        )
        return candidate

    def _path(self) -> Path:
        return self.p2p_dir / "project" / "conflicts.yml"


def _actor_role(path: Path, actor: str) -> str:
    if not actor or not path.exists():
        return ""
    try:
        payload = load_yaml(path.read_bytes())
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return ""
    identities = payload.get("identities") if isinstance(payload, dict) else None
    identity = identities.get(actor) if isinstance(identities, dict) else None
    return str(identity.get("role") or "") if isinstance(identity, dict) else ""
