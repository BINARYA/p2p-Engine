from __future__ import annotations

import hashlib
from pathlib import Path

import yaml
from typer.testing import CliRunner

from p2p_engine.cli import app
from p2p_engine.services.project_metadata import ProjectMetadataService
from p2p_engine.services.workspace_transactions import AtomicMutationWriter
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.cli_assertions import cli_data


runner = CliRunner()


def _tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if relative.startswith(".p2p/.internal/"):
            continue
        digest.update(relative.encode("utf-8"))
        if path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()


def _workspace(root: Path) -> P2PWorkspace:
    workspace = P2PWorkspace(root)
    workspace.init_project("Metadata", owner="owner")
    return workspace


def _patch(root: Path, **values: str) -> Path:
    path = root / "metadata-patch.yml"
    path.write_text(
        yaml.safe_dump(
            {
                "project_metadata_patch": {
                    "policy_version": 1,
                    "actor": "owner",
                    **values,
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def test_metadata_preview_is_read_only_and_apply_preserves_protected_configuration(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    patch = _patch(
        tmp_path,
        status="active",
        workflow_phase="delivery",
        current_objective="Ship schema migration support.",
    )
    project_path = tmp_path / ".p2p" / "project.yml"
    before_payload = yaml.safe_load(project_path.read_text(encoding="utf-8"))
    protected_before = {
        key: before_payload.get(key)
        for key in ("runtime_contract", "remote", "repository", "storage", "git", "ai")
    }
    before_preview = _tree_hash(tmp_path)

    preview = workspace.preview_project_metadata_update(patch, actor="owner")

    assert preview.apply_allowed is True
    assert preview.authority == "owner_confirmed"
    assert _tree_hash(tmp_path) == before_preview

    result = workspace.apply_project_metadata_update(
        patch,
        preview_token=preview.preview_token,
        actor="owner",
        confirm=True,
    )

    assert result.status == "applied"
    after = yaml.safe_load(project_path.read_text(encoding="utf-8"))
    assert after["project"]["status"] == "active"
    assert after["workflow"]["current_phase"] == "delivery"
    assert after["workflow"]["current_objective"] == "Ship schema migration support."
    assert after["metadata_audit"][-1]["actor"] == "owner"
    assert after["metadata_audit"][-1]["changed_fields"] == [
        "current_objective",
        "status",
        "workflow_phase",
    ]
    assert {
        key: after.get(key)
        for key in ("runtime_contract", "remote", "repository", "storage", "git", "ai")
    } == protected_before


def test_metadata_apply_rejects_stale_preview_without_writing(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    patch = _patch(tmp_path, workflow_phase="delivery")
    preview = workspace.preview_project_metadata_update(patch, actor="owner")
    project_path = tmp_path / ".p2p" / "project.yml"
    payload = yaml.safe_load(project_path.read_text(encoding="utf-8"))
    payload["workflow"]["next_goal"] = "Externally updated."
    project_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    before = project_path.read_bytes()

    result = workspace.apply_project_metadata_update(
        patch,
        preview_token=preview.preview_token,
        actor="owner",
        confirm=True,
    )

    assert result.status == "stale_preview"
    assert project_path.read_bytes() == before


def test_metadata_authority_unknown_fields_and_status_transition_are_rejected(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    patch = _patch(tmp_path, workflow_phase="delivery")
    unauthorized = workspace.preview_project_metadata_update(patch, actor="owner")
    payload = yaml.safe_load(patch.read_text(encoding="utf-8"))
    payload["project_metadata_patch"]["actor"] = "contributor"
    patch.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    contributor = workspace.preview_project_metadata_update(patch, actor="contributor")
    assert unauthorized.apply_allowed is True
    assert contributor.apply_allowed is False

    payload["project_metadata_patch"]["repository"] = "tampered"
    patch.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    try:
        workspace.preview_project_metadata_update(patch, actor="contributor")
    except ValueError as exc:
        assert "Unsupported project metadata fields" in str(exc)
    else:
        raise AssertionError("Arbitrary metadata field was accepted")

    project_path = tmp_path / ".p2p" / "project.yml"
    current = yaml.safe_load(project_path.read_text(encoding="utf-8"))
    current["project"]["status"] = "archived"
    project_path.write_text(yaml.safe_dump(current, sort_keys=False), encoding="utf-8")
    archived_patch = _patch(tmp_path, status="active")
    try:
        workspace.preview_project_metadata_update(archived_patch, actor="owner")
    except ValueError as exc:
        assert "Invalid project status transition" in str(exc)
    else:
        raise AssertionError("Invalid archived-to-active transition was accepted")


def test_metadata_atomic_failure_restores_original_bytes(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    project_path = tmp_path / ".p2p" / "project.yml"
    original = project_path.read_bytes()

    def fail(stage: str, target: str) -> None:
        if stage == "after_replace" and target == ".p2p/project.yml":
            raise OSError("injected metadata failure")

    service = ProjectMetadataService(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        atomic_writer=AtomicMutationWriter(
            root=tmp_path,
            p2p_dir=tmp_path / ".p2p",
            failure_injector=fail,
        ),
    )
    patch = _patch(tmp_path, workflow_phase="delivery")
    preview = service.preview(patch, actor="owner")

    result = service.apply(
        patch,
        preview_token=preview.preview_token,
        actor="owner",
        confirm=True,
    )

    assert result.status == "rolled_back"
    assert project_path.read_bytes() == original


def test_metadata_cli_json_preview_and_apply(tmp_path: Path) -> None:
    _workspace(tmp_path)
    patch = _patch(tmp_path, workflow_phase="delivery")
    preview_result = runner.invoke(
        app,
        [
            "project",
            "metadata",
            "preview",
            str(patch),
            "--actor",
            "owner",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )
    assert preview_result.exit_code == 0
    token = cli_data(preview_result)["project_metadata_preview"]["preview_token"]

    apply_result = runner.invoke(
        app,
        [
            "project",
            "metadata",
            "apply",
            str(patch),
            "--preview-token",
            token,
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
    assert cli_data(apply_result)["project_metadata_apply"]["status"] == "applied"
