#!/usr/bin/env python3
"""Canonicalize and verify the current WaveKit vertical-transition fixture set."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from p2p_engine import __version__
from p2p_engine.cli_contract import CLI_CONTRACT_VERSION
from p2p_engine.core.mutation_receipts import (
    MUTATION_RECEIPT_MAX_FILE_BYTES,
    MUTATION_RECEIPT_SCHEMA_VERSION,
)
from p2p_engine.core.vertical_transition_impact import (
    VERTICAL_TRANSITION_COLLECTION_LIMIT,
    VERTICAL_TRANSITION_IMPACT_CONTRACT,
    VERTICAL_TRANSITION_TOTAL_ITEM_LIMIT,
)
from p2p_engine.core.vertical_transition_plan import (
    VERTICAL_TRANSITION_PLAN_CONTRACT,
    VERTICAL_TRANSITION_PLAN_MAX_DECISIONS,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "vertical_transition"
MANIFEST_PATH = FIXTURE_ROOT / "manifest-v1.json"
CURRENT_MEMBERS = (
    "adoption-apply-v1.json",
    "adoption-empty-v1.json",
    "adoption-populated-v1.json",
    "install-apply-v1.json",
    "install-preview-v1.json",
    "migration-apply-v1.json",
    "migration-complete-plan-v1.json",
    "migration-decision-required-v1.json",
)


def _canonical_bytes(payload: object) -> bytes:
    return (json.dumps(payload, indent=2, ensure_ascii=True) + "\n").encode("utf-8")


def _load_current_member(name: str) -> tuple[dict[str, object], bytes]:
    path = FIXTURE_ROOT / name
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Current fixture must be an object: {name}")
    if name == "migration-complete-plan-v1.json":
        plan = payload.get("vertical_transition_plan")
        if not isinstance(plan, dict) or plan.get("contract_version") != VERTICAL_TRANSITION_PLAN_CONTRACT:
            raise ValueError(f"Current fixture has the wrong plan contract: {name}")
    else:
        if payload.get("contract_version") != CLI_CONTRACT_VERSION:
            raise ValueError(f"Current fixture has the wrong CLI contract: {name}")
        if payload.get("ok") is not True or not str(payload.get("operation") or "").startswith(
            "project.vertical."
        ):
            raise ValueError(f"Current fixture is not a successful vertical transition: {name}")
    serialized = _canonical_bytes(payload)
    forbidden = (b"/home/", b"/Users/", b"\\\\", b".p2p/", b"token:", b"password")
    if any(marker in serialized for marker in forbidden):
        raise ValueError(f"Current fixture contains private or physical state: {name}")
    return payload, serialized


def _manifest(member_bytes: dict[str, bytes]) -> dict[str, object]:
    return {
        "engine_version": __version__,
        "cli_contract_version": CLI_CONTRACT_VERSION,
        "impact_contract_version": VERTICAL_TRANSITION_IMPACT_CONTRACT,
        "plan_contract_version": VERTICAL_TRANSITION_PLAN_CONTRACT,
        "receipt_schema_version": MUTATION_RECEIPT_SCHEMA_VERSION,
        "limits": {
            "collection_items": VERTICAL_TRANSITION_COLLECTION_LIMIT,
            "transition_material_items": VERTICAL_TRANSITION_TOTAL_ITEM_LIMIT,
            "plan_decisions": VERTICAL_TRANSITION_PLAN_MAX_DECISIONS,
            "receipt_bytes": MUTATION_RECEIPT_MAX_FILE_BYTES,
        },
        "fixtures": {
            name: hashlib.sha256(member_bytes[name]).hexdigest()
            for name in CURRENT_MEMBERS
        },
        "wavekit_7_8_assertions": {
            "classification": [
                "data.impact.source_state.classification",
                "data.impact.source_state.evidence",
            ],
            "preservation_and_mapping": [
                "data.impact.evidence_transitions",
                "data.impact.required_decisions",
                "data.impact.plan_fingerprint_sha256",
                "data.postconditions",
            ],
        },
        "wavekit_owned": [
            "authorization",
            "preview_expiry",
            "queue_concurrency",
            "crash_recovery_orchestration",
            "post_apply_validation",
        ],
    }


def generate(*, check: bool) -> None:
    actual_names = {
        path.name
        for path in FIXTURE_ROOT.glob("*.json")
        if path.name not in {"manifest-v1.json", "legacy-0.4.7-characterization.json"}
    }
    expected_names = set(CURRENT_MEMBERS)
    if actual_names != expected_names:
        raise SystemExit(
            "Current fixture member drift: "
            f"missing={sorted(expected_names - actual_names)} extra={sorted(actual_names - expected_names)}"
        )
    member_bytes: dict[str, bytes] = {}
    drift: list[str] = []
    for name in CURRENT_MEMBERS:
        _, canonical = _load_current_member(name)
        member_bytes[name] = canonical
        path = FIXTURE_ROOT / name
        if path.read_bytes() != canonical:
            if check:
                drift.append(name)
            else:
                path.write_bytes(canonical)
    manifest_bytes = _canonical_bytes(_manifest(member_bytes))
    if MANIFEST_PATH.read_bytes() != manifest_bytes:
        if check:
            drift.append(MANIFEST_PATH.name)
        else:
            MANIFEST_PATH.write_bytes(manifest_bytes)
    if drift:
        raise SystemExit(
            "WaveKit transition fixtures are stale; run "
            f"scripts/generate-wavekit-transition-fixtures.py: {', '.join(drift)}"
        )
    print(
        f"WaveKit transition fixtures {'verified' if check else 'generated'}: "
        f"engine={__version__} receipt_schema={MUTATION_RECEIPT_SCHEMA_VERSION}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Fail instead of writing drifted files")
    arguments = parser.parse_args()
    generate(check=arguments.check)


if __name__ == "__main__":
    main()
