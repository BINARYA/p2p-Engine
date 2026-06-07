from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from p2p_engine.foundation.files import (
    read_yaml_mapping as _read_yaml_mapping,
    yaml_dump as _yaml_dump,
)


@dataclass(frozen=True)
class RegistryStatus:
    registries_dir: Path
    files: list[dict[str, object]]
    proposals_count: int
    changes_count: int
    stale: bool


@dataclass(frozen=True)
class RegistryView:
    name: str
    path: Path
    records: list[dict[str, object]]


RegistryRecords = Callable[[], list[dict[str, object]]]
RegistryRecordsFromProposals = Callable[[list[dict[str, object]]], list[dict[str, object]]]
RegistryRecordsFromProposalsChanges = Callable[
    [list[dict[str, object]], list[dict[str, object]]],
    list[dict[str, object]],
]


REGISTRY_DEFINITIONS: dict[str, dict[str, str]] = {
    "proposals": {"filename": "proposals.yml", "source": ".p2p/proposals"},
    "decisions": {"filename": "decisions.yml", "source": ".p2p/proposals/*/decision.md"},
    "changes": {"filename": "changes.yml", "source": ".p2p/changes"},
    "choices": {"filename": "choices.yml", "source": ".p2p/choices and proposal votes"},
    "relations": {"filename": "relations.yml", "source": ".p2p proposal and change metadata"},
    "artifacts": {"filename": "artifacts.yml", "source": ".p2p"},
    "readiness": {"filename": "readiness.yml", "source": ".p2p/proposals/*/readiness.yml"},
}


class RegistryService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        duplicate_proposal_ids: Callable[[], dict[str, list[Path]]],
        duplicate_message: Callable[[dict[str, list[Path]]], str],
        proposal_records: RegistryRecords,
        change_records: RegistryRecords,
        decision_records: RegistryRecordsFromProposals,
        choice_records: RegistryRecords,
        relation_records: RegistryRecordsFromProposalsChanges,
        artifact_records: RegistryRecordsFromProposalsChanges,
        readiness_records: RegistryRecordsFromProposals,
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.duplicate_proposal_ids = duplicate_proposal_ids
        self.duplicate_message = duplicate_message
        self.proposal_records = proposal_records
        self.change_records = change_records
        self.decision_records = decision_records
        self.choice_records = choice_records
        self.relation_records = relation_records
        self.artifact_records = artifact_records
        self.readiness_records = readiness_records

    def refresh(self) -> list[Path]:
        registries_dir = self.p2p_dir / "registries"
        registries_dir.mkdir(parents=True, exist_ok=True)

        duplicates = self.duplicate_proposal_ids()
        if duplicates:
            raise ValueError(self.duplicate_message(duplicates))

        proposals = self.proposal_records()
        changes = self.change_records()
        records_by_name = {
            "proposals": proposals,
            "decisions": self.decision_records(proposals),
            "changes": changes,
            "choices": self.choice_records(),
            "relations": self.relation_records(proposals, changes),
            "artifacts": self.artifact_records(proposals, changes),
            "readiness": self.readiness_records(proposals),
        }

        written: list[Path] = []
        for name, definition in REGISTRY_DEFINITIONS.items():
            filename = definition["filename"]
            path = registries_dir / filename
            path.write_text(
                _yaml_dump(
                    {
                        "generated": True,
                        "source": definition["source"],
                        name: records_by_name[name],
                    }
                ),
                encoding="utf-8",
            )
            written.append(path.relative_to(self.root))
        return written

    def status(self) -> RegistryStatus:
        registries_dir = self.p2p_dir / "registries"
        files: list[dict[str, object]] = []
        stale = False
        for name, definition in REGISTRY_DEFINITIONS.items():
            path = registries_dir / definition["filename"]
            exists = path.exists()
            count = 0
            generated = False
            if exists:
                data = _read_yaml_mapping(path, default={})
                generated = bool(data.get("generated", False))
                records = data.get(name, [])
                count = len(records) if isinstance(records, list) else 0
                if not generated:
                    stale = True
            else:
                stale = True
            files.append(
                {
                    "name": definition["filename"],
                    "exists": exists,
                    "generated": generated,
                    "records": count,
                }
            )

        proposals_count = len(self.proposal_records())
        changes_count = len(self.change_records())
        proposals_file = registries_dir / REGISTRY_DEFINITIONS["proposals"]["filename"]
        changes_file = registries_dir / REGISTRY_DEFINITIONS["changes"]["filename"]
        if proposals_file.exists():
            proposals_data = _read_yaml_mapping(proposals_file, default={})
            proposals_records = proposals_data.get("proposals", [])
            stale = stale or (isinstance(proposals_records, list) and len(proposals_records) != proposals_count)
        if changes_file.exists():
            changes_data = _read_yaml_mapping(changes_file, default={})
            changes_records = changes_data.get("changes", [])
            stale = stale or (isinstance(changes_records, list) and len(changes_records) != changes_count)

        return RegistryStatus(
            registries_dir=registries_dir.relative_to(self.root),
            files=files,
            proposals_count=proposals_count,
            changes_count=changes_count,
            stale=stale,
        )

    def show(self, name: str) -> RegistryView:
        if name not in REGISTRY_DEFINITIONS:
            raise ValueError(f"Unsupported registry: {name}")
        definition = REGISTRY_DEFINITIONS[name]
        path = self.p2p_dir / "registries" / definition["filename"]
        if not path.exists():
            raise ValueError("Registry not found. Run `p2p registry refresh` first.")
        data = _read_yaml_mapping(path, default={})
        records = data.get(name, [])
        if not isinstance(records, list):
            raise ValueError(f"Invalid registry file: expected `{name}` list.")
        return RegistryView(
            name=name,
            path=path.relative_to(self.root),
            records=[record for record in records if isinstance(record, dict)],
        )
