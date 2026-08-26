#!/usr/bin/env python3
from __future__ import annotations

from p2p_engine.services.release_convergence import (
    convergence_gate_payload,
    fixture_commands,
    issue_codes,
    load_packaged_wavekit_cli_fixture_bundle,
    validate_convergence_inventory,
    validate_wavekit_cli_fixture_bundle,
    wavekit_cli_fixture_bundle,
)


def main() -> int:
    inventory_issues = validate_convergence_inventory()
    expected = wavekit_cli_fixture_bundle()
    packaged = load_packaged_wavekit_cli_fixture_bundle()
    fixture_issues = validate_wavekit_cli_fixture_bundle(packaged)
    payload = convergence_gate_payload()

    failures: list[str] = []
    if inventory_issues:
        failures.append(
            "inventory=" + ",".join(issue_codes(inventory_issues))
        )
    if fixture_issues:
        failures.append("fixture=" + ",".join(issue_codes(fixture_issues)))
    if packaged != expected:
        failures.append("fixture=packaged_resource_drift")
    if payload["issues"]:
        failures.append("payload=convergence_issues_present")

    if failures:
        raise SystemExit("convergence gate failed: " + "; ".join(failures))

    print(
        "convergence gate verified: "
        f"release={payload['release_line']} "
        f"operations={len(payload['operation_inventory'])} "
        f"fixture_commands={len(fixture_commands(expected))}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
