from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import yaml
import pytest
from typer.testing import CliRunner

from p2p_engine.cli import app
from p2p_engine.foundation.markdown import replace_section
from p2p_engine.services.workspace_migrations import WorkspaceMigrationService
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.workspace_migration_fixtures import initialize_legacy_workspace


runner = CliRunner()


class SimulatedProcessExit(BaseException):
    pass


def _hash_tree(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        digest.update(path.relative_to(root).as_posix().encode())
        if path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()


def test_cli_workspace_schema_status_text_and_json(tmp_path: Path) -> None:
    P2PWorkspace(tmp_path).init_project("Current")

    text = runner.invoke(app, ["workspace", "schema", "status", "--root", str(tmp_path)])
    json_result = runner.invoke(
        app,
        ["workspace", "schema", "status", "--format", "json", "--root", str(tmp_path)],
    )

    assert text.exit_code == 0
    assert "layout_status: current" in text.output
    assert json_result.exit_code == 0
    payload = json.loads(json_result.output)
    assert payload["layout_status"] == "current"
    assert payload["alignment_status"] == "aligned"


def test_cli_migration_plan_is_read_only_and_json_stable(tmp_path: Path) -> None:
    P2PWorkspace(tmp_path).init_project("Legacy")
    (tmp_path / ".p2p" / "project" / "workspace-schema.yml").unlink()
    before = _hash_tree(tmp_path)
    command = [
        "workspace",
        "migrate",
        "plan",
        "--to",
        "1",
        "--format",
        "json",
        "--root",
        str(tmp_path),
    ]

    first = runner.invoke(app, command)
    second = runner.invoke(app, command)

    assert first.exit_code == 0
    assert second.exit_code == 0
    assert json.loads(first.output) == json.loads(second.output)
    assert _hash_tree(tmp_path) == before
    assert not (tmp_path / ".p2p" / ".internal").exists()


def test_cli_attestation_template_is_read_only_in_text_and_json(
    tmp_path: Path,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Legacy authority", owner="owner")
    schema_path = tmp_path / ".p2p" / "project" / "workspace-schema.yml"
    schema = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    schema["workspace_schema"]["current_version"] = 2
    schema["workspace_schema"]["applied_migrations"] = []
    schema_path.write_text(
        yaml.safe_dump(schema, sort_keys=False),
        encoding="utf-8",
    )
    proposal = workspace.create_proposal("Accepted by a legacy actor")
    proposal_dir = tmp_path / proposal.path
    proposal_path = proposal_dir / "proposal.md"
    proposal_path.write_text(
        replace_section(
            proposal_path.read_text(encoding="utf-8"),
            "Status",
            "`accepted`",
        ),
        encoding="utf-8",
    )
    (proposal_dir / "decision.md").write_text(
        f"# Decision - {proposal.proposal_id}\n\n"
        "## Status\n\n`accepted`\n\n"
        "## Outcome\n\naccepted\n\n"
        "## Reason\n\nReviewed legacy rationale.\n\n"
        "## Date\n\n2026-07-17\n\n"
        "## Approver\n\nlocal\n",
        encoding="utf-8",
    )
    before = _hash_tree(tmp_path)
    command = [
        "workspace",
        "migrate",
        "attestation-template",
        "--to",
        "3",
        "--owner",
        "owner",
        "--root",
        str(tmp_path),
    ]

    text = runner.invoke(app, command)
    json_result = runner.invoke(app, [*command, "--format", "json"])

    assert text.exit_code == 0
    assert "included_count: 1" in text.output
    assert json_result.exit_code == 0
    payload = json.loads(json_result.output)
    assert payload["included_proposal_ids"] == [proposal.proposal_id]
    assert payload["manual_review_count"] == 0
    assert (
        payload["owner_input"]["proposal_decisions"]["authority_attestations"][
            proposal.proposal_id
        ]["legacy_approver"]
        == "local"
    )
    assert _hash_tree(tmp_path) == before


def test_cli_migration_apply_commits_the_reviewed_plan(tmp_path: Path) -> None:
    initialize_legacy_workspace(tmp_path, owner="owner")
    plan_result = runner.invoke(
        app,
        [
            "workspace",
            "migrate",
            "plan",
            "--to",
            "1",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )
    assert plan_result.exit_code == 0
    fingerprint = json.loads(plan_result.output)["fingerprint_sha256"]

    apply_result = runner.invoke(
        app,
        [
            "workspace",
            "migrate",
            "apply",
            "--to",
            "1",
            "--plan-fingerprint",
            fingerprint,
            "--actor",
            "owner",
            "--confirm",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )

    assert apply_result.exit_code == 0
    payload = json.loads(apply_result.output)
    assert payload["status"] == "applied"
    assert payload["changed_paths"][-1] == ".p2p/project/workspace-schema.yml"
    assert P2PWorkspace(tmp_path).workspace_schema_status().state == "upgrade_available"


def test_cli_recovery_resume_completes_an_interrupted_transaction(tmp_path: Path) -> None:
    workspace = initialize_legacy_workspace(tmp_path, owner="owner")
    compatibility = workspace._workspace_compatibility_service()
    plan = compatibility.plan(1)

    def crash(stage: str, target: str) -> None:
        if stage == "after_journal":
            raise SimulatedProcessExit()

    migration = WorkspaceMigrationService(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        compatibility=compatibility,
        schema_service=workspace._workspace_schema_service(),
        lock_service=workspace._migration_lock_service(),
        failure_injector=crash,
    )
    with pytest.raises(SimulatedProcessExit):
        migration.apply(
            target_version=1,
            owner_inputs={},
            plan_fingerprint=plan.fingerprint_sha256,
            actor="owner",
            confirm=True,
        )
    transaction_id = migration.recovery_status().transaction_id

    result = runner.invoke(
        app,
        [
            "workspace",
            "migrate",
            "recovery",
            "resume",
            "--transaction-id",
            transaction_id,
            "--actor",
            "owner",
            "--confirm",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert json.loads(result.output)["status"] == "applied"
    assert P2PWorkspace(tmp_path).workspace_migration_recovery_status().required is False


def test_cli_downgrade_and_blocked_apply_use_nonzero_exit(tmp_path: Path) -> None:
    P2PWorkspace(tmp_path).init_project("Current")

    downgrade = runner.invoke(
        app,
        ["workspace", "migrate", "plan", "--to", "0", "--root", str(tmp_path)],
    )
    blocked = runner.invoke(
        app,
        [
            "workspace",
            "migrate",
            "apply",
            "--to",
            "1",
            "--plan-fingerprint",
            "invalid",
            "--actor",
            "owner",
            "--root",
            str(tmp_path),
        ],
    )

    assert downgrade.exit_code == 1
    assert "UNSUPPORTED_DOWNGRADE" in downgrade.output
    assert blocked.exit_code == 1
    assert "status: blocked" in blocked.output


def test_cli_recovery_status_is_read_only(tmp_path: Path) -> None:
    P2PWorkspace(tmp_path).init_project("Current")
    before = _hash_tree(tmp_path)

    result = runner.invoke(
        app,
        ["workspace", "migrate", "recovery", "status", "--format", "json", "--root", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert json.loads(result.output)["required"] is False
    assert _hash_tree(tmp_path) == before


def test_schema_and_freshness_are_visible_in_status_doctor_and_context(tmp_path: Path) -> None:
    P2PWorkspace(tmp_path).init_project("Visible State")

    status = runner.invoke(app, ["status", "--root", str(tmp_path)])
    doctor = runner.invoke(app, ["doctor", "--root", str(tmp_path)])
    context = runner.invoke(
        app,
        ["context", "--format", "json", "--root", str(tmp_path)],
    )

    assert status.exit_code == 0
    assert "Workspace schema: current layout=current" in status.output
    assert "Derived freshness:" in status.output
    assert doctor.exit_code == 0
    assert "workspace_schema_state: current" in doctor.output
    assert "derived_freshness:" in doctor.output
    payload = json.loads(context.output)
    assert payload["current_state"]["workspace_schema"]["layout_status"] == "current"
    assert "derived_freshness" in payload["current_state"]


def test_next_prioritizes_recovery_then_migration_then_freshness(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Priority")
    schema_path = tmp_path / ".p2p" / "project" / "workspace-schema.yml"
    schema_path.unlink()

    migration = runner.invoke(app, ["next", "--top", "1", "--root", str(tmp_path)])
    assert migration.exit_code == 0
    assert "NEXT-WORKSPACE-MIGRATION  critical  plan_workspace_migration" in migration.output

    lock_path = tmp_path / ".p2p" / ".internal" / "workspace-migrations" / "apply.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(
        yaml.safe_dump(
            {
                "transaction_id": "migration-stale",
                "pid": os.getpid() + 10_000_000,
                "acquired_at": "2026-07-15T12:00:00Z",
                "owner": "owner",
            }
        ),
        encoding="utf-8",
    )
    recovery = runner.invoke(app, ["next", "--top", "1", "--root", str(tmp_path)])
    assert recovery.exit_code == 0
    assert "NEXT-WORKSPACE-RECOVERY  critical  recover_workspace_migration" in recovery.output

    lock_path.unlink()
    schema_payload = workspace._workspace_schema_service().initialized_current_payload(
        initialized_at="2026-07-15T12:00:00Z",
        actor="owner",
    )
    schema_path.write_text(yaml.safe_dump(schema_payload, sort_keys=False), encoding="utf-8")
    workspace.refresh_registries()
    freshness = runner.invoke(app, ["next", "--top", "1", "--root", str(tmp_path)])
    assert freshness.exit_code == 0
    assert "NEXT-DERIVED-FRESHNESS" in freshness.output
    assert "target: project_projections" in freshness.output
