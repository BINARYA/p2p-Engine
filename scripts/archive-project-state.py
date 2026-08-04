#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import UTC, date, datetime
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
from typing import Any

import yaml


INVENTORY_CONTRACT = "p2p-project-semantic-inventory-v1"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Archive a P2P project and record semantic evidence without conversion."
    )
    parser.add_argument("--root", type=Path, required=True, help="Project-state repository root")
    parser.add_argument("--archive", type=Path, required=True, help="External .tar.gz destination")
    parser.add_argument("--inventory", type=Path, required=True, help="External JSON inventory destination")
    parser.add_argument("--p2p-command", type=Path, help="Optional P2P executable for read-only validation")
    return parser.parse_args()


def _yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        return {"parse_error": str(exc)}
    return payload if isinstance(payload, dict) else {"observed_type": type(payload).__name__}


def _frontmatter(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return {"parse_error": str(exc)}
    if not text.startswith("---\n"):
        return {}
    closing = text.find("\n---\n", 4)
    if closing < 0:
        return {"parse_error": "unterminated frontmatter"}
    try:
        payload = yaml.safe_load(text[4:closing])
    except yaml.YAMLError as exc:
        return {"parse_error": str(exc)}
    return payload if isinstance(payload, dict) else {}


def _directory_records(parent: Path, markdown_name: str) -> list[dict[str, Any]]:
    if not parent.is_dir():
        return []
    return [
        {
            "id": child.name.split("-", 2)[:2][0] + (
                f"-{child.name.split('-', 2)[1]}" if "-" in child.name else ""
            ),
            "directory": child.name,
            "frontmatter": _frontmatter(child / markdown_name),
        }
        for child in sorted(parent.iterdir())
        if child.is_dir()
    ]


def _proposal_records(parent: Path) -> list[dict[str, Any]]:
    records = _directory_records(parent, "proposal.md")
    for record in records:
        proposal_dir = parent / str(record["directory"])
        ledger = _yaml(proposal_dir / "decision-events.yml").get(
            "proposal_decision_ledger", {}
        )
        events = ledger.get("events", []) if isinstance(ledger, dict) else []
        head = events[-1] if isinstance(events, list) and events else {}
        record["decision_head"] = {
            "contract_version": ledger.get("contract_version") if isinstance(ledger, dict) else None,
            "event_count": len(events) if isinstance(events, list) else 0,
            "event_id": head.get("event_id") if isinstance(head, dict) else None,
            "event_type": head.get("event_type") if isinstance(head, dict) else None,
            "effective_state": head.get("effective_state") if isinstance(head, dict) else None,
        }
    return records


def _file_manifest(root: Path) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        data = path.read_bytes()
        entries.append(
            {
                "path": relative,
                "size": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    semantic = hashlib.sha256(
        json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {"count": len(entries), "semantic_sha256": semantic, "entries": entries}


def collect_inventory(root: Path, *, validation: dict[str, Any]) -> dict[str, Any]:
    p2p = root / ".p2p"
    if not p2p.is_dir():
        raise ValueError(f"P2P project state not found: {p2p}")
    return {
        "contract": INVENTORY_CONTRACT,
        "captured_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "root_name": root.name,
        "project": _yaml(p2p / "project.yml"),
        "workspace_schema": _yaml(p2p / "project" / "workspace-schema.yml"),
        "active_vertical": _yaml(p2p / "project" / "vertical.yml"),
        "vertical_lock": _yaml(p2p / "project" / "vertical.lock.yml"),
        "project_definition": _yaml(p2p / "project" / "definition.yml"),
        "proposals": _proposal_records(p2p / "proposals"),
        "choices": _directory_records(p2p / "choices", "choice.md"),
        "change_sets": _directory_records(p2p / "changes", "change.md"),
        "work": _directory_records(p2p / "work", "work.md"),
        "validation": validation,
        "files": _file_manifest(root),
    }


def _validation(p2p_command: Path | None, root: Path) -> dict[str, Any]:
    if p2p_command is None:
        return {"status": "not_requested"}
    command = [
        str(p2p_command.resolve()),
        "validate",
        "--format",
        "json",
        "--root",
        str(root.resolve()),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    try:
        payload: Any = json.loads(result.stdout)
    except json.JSONDecodeError:
        payload = {"stdout": result.stdout.strip(), "stderr": result.stderr.strip()}
    return {"status": "captured", "exit_code": result.returncode, "payload": payload}


def _outside_root(target: Path, root: Path) -> None:
    resolved = target.resolve()
    if resolved == root.resolve() or resolved.is_relative_to(root.resolve()):
        raise ValueError(f"Archive evidence must be outside the project root: {target}")
    if target.exists():
        raise ValueError(f"Refusing to overwrite existing archive evidence: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)


def _json_default(value: object) -> object:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def main() -> int:
    args = _parse_args()
    root = args.root.resolve()
    archive = args.archive.resolve()
    inventory_path = args.inventory.resolve()
    _outside_root(archive, root)
    _outside_root(inventory_path, root)

    validation = _validation(args.p2p_command, root)
    inventory = collect_inventory(root, validation=validation)
    temporary_archive = archive.with_name(archive.name + ".tmp")
    temporary_inventory = inventory_path.with_name(inventory_path.name + ".tmp")
    for temporary in (temporary_archive, temporary_inventory):
        if temporary.exists():
            raise ValueError(f"Refusing to overwrite temporary archive evidence: {temporary}")
    try:
        with tarfile.open(temporary_archive, "x:gz") as bundle:
            bundle.add(root, arcname=root.name, recursive=True)
        archive_data = temporary_archive.read_bytes()
        inventory["archive"] = {
            "path": str(archive),
            "size": len(archive_data),
            "sha256": hashlib.sha256(archive_data).hexdigest(),
        }
        temporary_inventory.write_text(
            json.dumps(inventory, indent=2, sort_keys=True, default=_json_default) + "\n",
            encoding="utf-8",
        )
        temporary_archive.replace(archive)
        temporary_inventory.replace(inventory_path)
    except Exception:
        temporary_archive.unlink(missing_ok=True)
        temporary_inventory.unlink(missing_ok=True)
        raise
    print(
        f"project archive created: archive={archive} inventory={inventory_path} "
        f"files={inventory['files']['count']} proposals={len(inventory['proposals'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
