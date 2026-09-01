from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from p2p_engine.core.project_structure import ProjectStructure
from p2p_engine.core.project_structure_merge_restore import (
    STRUCTURE_SNAPSHOT_LEDGER_CONTRACT,
    STRUCTURE_SNAPSHOT_RETENTION_LIMIT,
    RetainedStructureLedger,
    RetainedStructureSnapshot,
    retained_snapshot_from_mapping,
)
from p2p_engine.foundation.files import yaml_dump
from p2p_engine.foundation.yaml_loaders import UNIQUE_LOADER_CONTRACT, load_yaml

PROJECT_STRUCTURE_SNAPSHOTS_PATH = ".p2p/project/structure-snapshots.yml"


class ProjectStructureSnapshotService:
    """Filesystem adapter for canonical retained structure snapshots.

    The public contract is revision/checksum based. This class is the selected
    adapter implementation and is the only layer that knows the physical
    locator used by the filesystem backend.
    """

    def __init__(self, *, root: Path) -> None:
        self.root = root.resolve()
        self.path = self.root / PROJECT_STRUCTURE_SNAPSHOTS_PATH

    def load(self, *, structure_id: str) -> RetainedStructureLedger:
        if not self.path.exists():
            return RetainedStructureLedger(structure_id=structure_id)
        if self.path.is_symlink() or not self.path.is_file():
            raise ValueError("P2P_STRUCTURE_SNAPSHOT_LEDGER_INVALID: ledger is unsafe")
        try:
            payload = load_yaml(self.path.read_bytes(), loader_contract=UNIQUE_LOADER_CONTRACT)
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            raise ValueError(f"P2P_STRUCTURE_SNAPSHOT_LEDGER_INVALID: {exc}") from exc
        return retained_structure_ledger_from_mapping(payload, structure_id=structure_id)

    def inspect(
        self,
        *,
        structure_id: str,
        revision: int,
        include_structure: bool = False,
    ) -> dict[str, object]:
        ledger = self.load(structure_id=structure_id)
        snapshot = ledger.resolve(revision)
        return {
            "contract": STRUCTURE_SNAPSHOT_LEDGER_CONTRACT,
            "retention": retention_policy(),
            "snapshot": snapshot.to_dict(include_structure=include_structure),
        }

    def list(self, *, structure_id: str, limit: int = 20) -> dict[str, object]:
        if isinstance(limit, bool) or not 1 <= limit <= STRUCTURE_SNAPSHOT_RETENTION_LIMIT:
            raise ValueError(
                "P2P_STRUCTURE_SNAPSHOT_LIMIT_INVALID: limit must be between 1 and 100"
            )
        ledger = self.load(structure_id=structure_id)
        visible = ledger.snapshots[-limit:]
        return {
            "contract": STRUCTURE_SNAPSHOT_LEDGER_CONTRACT,
            "structure_id": structure_id,
            "retention": retention_policy(),
            "total": len(ledger.snapshots),
            "returned": len(visible),
            "truncated": len(visible) < len(ledger.snapshots),
            "snapshots": [item.to_dict() for item in visible],
        }

    def candidate_bytes(
        self,
        *,
        previous: ProjectStructure,
        retained_at: str,
        retained_by: str,
        reason: str,
    ) -> bytes:
        ledger = self.load(structure_id=previous.structure_id)
        retained = ledger.retain(
            RetainedStructureSnapshot(
                structure=previous,
                retained_at=retained_at,
                retained_by=retained_by,
                reason=reason,
            )
        )
        return retained_structure_ledger_bytes(retained)

    def source_content(self) -> bytes | None:
        return (
            self.path.read_bytes() if self.path.is_file() and not self.path.is_symlink() else None
        )


def retention_policy() -> dict[str, object]:
    return {
        "mode": "newest-revisions",
        "limit": STRUCTURE_SNAPSHOT_RETENTION_LIMIT,
        "automatic_pruning": True,
        "restore_guarantee": (
            "A listed revision remains restorable until it leaves the newest-100 window; "
            "missing or pruned revisions fail closed."
        ),
    }


def retained_structure_ledger_bytes(ledger: RetainedStructureLedger) -> bytes:
    return yaml_dump({"project_structure_snapshots": ledger.to_storage_dict()}).encode("ascii")


def retained_structure_ledger_from_mapping(
    value: object,
    *,
    structure_id: str | None = None,
) -> RetainedStructureLedger:
    if not isinstance(value, Mapping) or set(value) != {"project_structure_snapshots"}:
        raise ValueError(
            "P2P_STRUCTURE_SNAPSHOT_LEDGER_INVALID: expected project_structure_snapshots root"
        )
    raw = value.get("project_structure_snapshots")
    if not isinstance(raw, Mapping):
        raise ValueError("P2P_STRUCTURE_SNAPSHOT_LEDGER_INVALID: ledger must be a mapping")
    if set(raw) != {"contract", "structure_id", "retention", "snapshots"}:
        raise ValueError("P2P_STRUCTURE_SNAPSHOT_LEDGER_INVALID: ledger fields are not exact")
    retention = raw.get("retention")
    if not isinstance(retention, Mapping) or dict(retention) != {
        "mode": "newest-revisions",
        "limit": STRUCTURE_SNAPSHOT_RETENTION_LIMIT,
        "automatic_pruning": True,
    }:
        raise ValueError("P2P_STRUCTURE_SNAPSHOT_RETENTION_INVALID: policy is unsupported")
    snapshots = raw.get("snapshots")
    if isinstance(snapshots, (str, bytes)) or not isinstance(snapshots, Sequence):
        raise ValueError("P2P_STRUCTURE_SNAPSHOT_LEDGER_INVALID: snapshots must be a list")
    ledger = RetainedStructureLedger(
        contract=str(raw.get("contract") or ""),
        structure_id=str(raw.get("structure_id") or ""),
        snapshots=tuple(retained_snapshot_from_mapping(item) for item in snapshots),
    )
    if structure_id is not None and ledger.structure_id != structure_id:
        raise ValueError("P2P_STRUCTURE_SNAPSHOT_LEDGER_INVALID: active structure differs")
    return ledger
