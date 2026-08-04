from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "archive-project-state.py"
SPEC = importlib.util.spec_from_file_location("archive_project_state", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_semantic_inventory_is_read_only_and_records_governed_families(tmp_path: Path) -> None:
    root = tmp_path / "project"
    proposal = root / ".p2p" / "proposals" / "PROP-001-example"
    change = root / ".p2p" / "changes" / "CHANGE-001-example"
    proposal.mkdir(parents=True)
    change.mkdir(parents=True)
    (root / ".p2p" / "project").mkdir()
    (root / ".p2p" / "project.yml").write_text("project:\n  name: Demo\n", encoding="utf-8")
    (root / ".p2p" / "project" / "workspace-schema.yml").write_text(
        "workspace_schema:\n  current_version: 3\n",
        encoding="utf-8",
    )
    (proposal / "proposal.md").write_text(
        "---\nid: PROP-001\nstatus: accepted\n---\n\n# Example\n",
        encoding="utf-8",
    )
    (proposal / "decision-events.yml").write_text(
        yaml.safe_dump(
            {
                "proposal_decision_ledger": {
                    "contract_version": 1,
                    "events": [
                        {
                            "event_id": "PDE-001",
                            "event_type": "accepted",
                            "effective_state": "accepted",
                        }
                    ],
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (change / "change.md").write_text(
        "---\nid: CHANGE-001\nstatus: proposed\n---\n\n# Change\n",
        encoding="utf-8",
    )
    before = MODULE._file_manifest(root)

    inventory = MODULE.collect_inventory(
        root,
        validation={"status": "captured", "exit_code": 0},
    )

    assert inventory["contract"] == "p2p-project-semantic-inventory-v1"
    assert inventory["project"]["project"]["name"] == "Demo"
    assert inventory["proposals"][0]["id"] == "PROP-001"
    assert inventory["proposals"][0]["decision_head"]["event_id"] == "PDE-001"
    assert inventory["change_sets"][0]["id"] == "CHANGE-001"
    assert inventory["validation"]["exit_code"] == 0
    assert inventory["files"] == before


def test_json_serialization_normalizes_yaml_dates() -> None:
    value = yaml.safe_load("created_at: 2026-08-04\n")["created_at"]

    assert MODULE._json_default(value) == "2026-08-04"
