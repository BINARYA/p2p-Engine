#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from p2p_engine.foundation.yaml_loaders import UNIQUE_LOADER_CONTRACT, load_yaml

REQUIRED_FIELDS = {"advisory_id", "owner", "rationale", "expires_on"}


def validate(path: Path, *, today: date) -> tuple[list[str], list[str]]:
    try:
        payload = load_yaml(path.read_bytes(), loader_contract=UNIQUE_LOADER_CONTRACT)
    except ValueError as exc:
        return [f"security audit exceptions are invalid: {exc}"], []
    issues: list[str] = []
    advisory_ids: list[str] = []
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        return ["security audit exception schema_version must be 1"], []
    exceptions = payload.get("exceptions")
    if not isinstance(exceptions, list):
        return ["security audit exceptions must be a list"], []
    for index, item in enumerate(exceptions):
        prefix = f"security audit exception {index}"
        if not isinstance(item, dict):
            issues.append(f"{prefix} must be a mapping")
            continue
        missing = sorted(REQUIRED_FIELDS - set(item))
        if missing:
            issues.append(f"{prefix} is missing: {', '.join(missing)}")
            continue
        values = {field: str(item.get(field) or "").strip() for field in REQUIRED_FIELDS}
        empty = sorted(field for field, value in values.items() if not value)
        if empty:
            issues.append(f"{prefix} has empty fields: {', '.join(empty)}")
            continue
        try:
            expires_on = date.fromisoformat(values["expires_on"])
        except ValueError:
            issues.append(f"{prefix} has invalid expires_on")
            continue
        if expires_on < today:
            issues.append(f"{prefix} expired on {expires_on.isoformat()}")
            continue
        advisory_ids.append(values["advisory_id"])
    if len(advisory_ids) != len(set(advisory_ids)):
        issues.append("security audit exception advisory_id values must be unique")
    return issues, advisory_ids


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate owner-approved audit exceptions.")
    parser.add_argument(
        "--file",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "security-audit-exceptions.yml",
    )
    parser.add_argument("--today", type=date.fromisoformat, default=date.today())
    parser.add_argument("--emit-arguments", action="store_true")
    args = parser.parse_args()
    issues, advisory_ids = validate(args.file, today=args.today)
    if issues:
        for issue in issues:
            print(issue)
        return 1
    if args.emit_arguments:
        for advisory_id in advisory_ids:
            print(f"--ignore-vuln={advisory_id}")
    else:
        print(f"security audit exceptions verified: count={len(advisory_ids)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
