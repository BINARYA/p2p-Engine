from __future__ import annotations

from pathlib import Path

import yaml
from typer.testing import CliRunner

from p2p_engine.cli import app
from p2p_engine.services.authority_rotation import ProjectAuthorityRotationService
from p2p_engine.services.workspace_transactions import AtomicMutationWriter
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.cli_assertions import cli_data


runner = CliRunner()


def test_local_authority_rotation_is_atomic_receipt_backed_and_replayable(
    tmp_path: Path,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Rotation fixture", owner="Davide")
    operation_key = "authority-rotation-001"
    preview = workspace.preview_project_authority_rotation(
        operation_key=operation_key,
        actor_id="davide",
        executor_id="davide",
        executor_kind="person",
        display_name="Transferred authority",
        rotated_at="2026-08-25T13:00:00Z",
    )

    result = workspace.apply_project_authority_rotation(
        operation_key=operation_key,
        actor_id="davide",
        executor_id="davide",
        executor_kind="person",
        preview_token=preview.mutation.preview_token,
        confirm=True,
        display_name="Transferred authority",
        rotated_at="2026-08-25T13:00:00Z",
    )

    assert result.status == "applied"
    assert result.previous_descriptor.generation == 1
    assert result.new_descriptor.generation == 2
    assert result.new_descriptor.authority_id == result.previous_descriptor.authority_id
    assert workspace.project_authority().generation == 2
    status = workspace.mutation_status(idempotency_key=operation_key)
    assert status.operation == "project_authority_rotate"
    assert status.authority is not None
    assert status.authority["subject"]["id"] == "davide"

    replay = workspace.apply_project_authority_rotation(
        operation_key=operation_key,
        actor_id="davide",
        executor_id="davide",
        executor_kind="person",
        preview_token=preview.mutation.preview_token,
        confirm=True,
        display_name="Transferred authority",
        rotated_at="2026-08-25T13:00:00Z",
    )
    assert replay.status == "already_applied"
    assert workspace.project_authority().generation == 2


def test_authority_rotation_failure_rolls_back_descriptor_event_and_receipt(
    tmp_path: Path,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Rotation failure", owner="owner")

    def fail_after_first_replace(stage: str, target: str) -> None:
        if stage == "after_replace":
            raise RuntimeError(f"injected after {target}")

    service = ProjectAuthorityRotationService(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        authority=workspace._project_authority_service(),
        receipts=workspace._mutation_receipt_service(),
        atomic_writer=AtomicMutationWriter(
            root=tmp_path,
            p2p_dir=tmp_path / ".p2p",
            failure_injector=fail_after_first_replace,
        ),
    )
    preview = service.preview(
        operation_key="authority-rotation-failure",
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
        display_name="Not committed",
        rotated_at="2026-08-25T13:30:00Z",
    )

    result = service.apply(
        operation_key="authority-rotation-failure",
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
        preview_token=preview.mutation.preview_token,
        confirm=True,
        display_name="Not committed",
        rotated_at="2026-08-25T13:30:00Z",
    )

    assert result.status == "rolled_back"
    assert workspace.project_authority().generation == 1
    assert not (tmp_path / ".p2p/project/authority-events.yml").exists()
    assert workspace.mutation_status(
        idempotency_key="authority-rotation-failure"
    ).state == "not_found"


def test_project_authority_cli_exposes_descriptor_capabilities_and_rotation(
    tmp_path: Path,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("CLI authority", owner="owner")

    show = runner.invoke(
        app,
        ["project", "authority", "show", "--format", "json", "--root", str(tmp_path)],
    )
    capabilities = runner.invoke(
        app,
        ["project", "authority", "capabilities", "--format", "json"],
    )
    preview_result = runner.invoke(
        app,
        [
            "project",
            "authority",
            "rotate",
            "preview",
            "--operation-key",
            "authority-cli-001",
            "--display-name",
            "CLI rotated",
            "--rotated-at",
            "2026-08-25T14:00:00Z",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )

    assert show.exit_code == 0, show.output
    assert cli_data(show)["project_authority"]["generation"] == 1
    assert capabilities.exit_code == 0, capabilities.output
    names = {
        item["capability"]
        for item in cli_data(capabilities)["governed_capabilities"]["capabilities"]
    }
    assert "proposal.decide" in names
    assert preview_result.exit_code == 0, preview_result.output
    preview = cli_data(preview_result)["project_authority_rotation"]

    applied = runner.invoke(
        app,
        [
            "project",
            "authority",
            "rotate",
            "apply",
            "--operation-key",
            "authority-cli-001",
            "--preview-token",
            preview["preview"]["preview_token"],
            "--rotated-at",
            preview["rotation_request"]["rotated_at"],
            "--display-name",
            "CLI rotated",
            "--confirm",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )

    assert applied.exit_code == 0, applied.output
    assert cli_data(applied)["project_authority_rotation"]["status"] == "applied"
    descriptor = yaml.safe_load(
        (tmp_path / ".p2p/project/authority.yml").read_text(encoding="utf-8")
    )
    assert descriptor["project_authority"]["generation"] == 2
