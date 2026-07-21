from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from p2p_engine.cli import app
from p2p_engine.services.proposal_artifacts import ProposalArtifactService
from p2p_engine.services.workspace_transactions import AtomicMutationWriter
from p2p_engine.storage.filesystem import P2PWorkspace


runner = CliRunner()


def _workspace(root: Path) -> tuple[P2PWorkspace, str]:
    workspace = P2PWorkspace(root)
    workspace.init_project(
        "Coverage",
        project_domain="software",
        vertical_id="software_project",
        owner="owner",
    )
    proposal = workspace.create_proposal_with_details(
        "Domain data model lifecycle",
        problem="Domain entities, data model state transitions, and lifecycle are not explicit.",
        proposal="Define domain entities and a data model with explicit state lifecycle transitions.",
    )
    return workspace, proposal.proposal_id


def _payload(proposal_id: str, section_id: str = "data_model") -> dict[str, object]:
    return {
        "vertical_coverage": {
            "schema_version": 2,
            "proposal_id": proposal_id,
            "vertical_id": "software_project",
            "sections": [
                {
                    "id": section_id,
                    "relevance": "direct",
                    "rationale": "The proposal changes domain entities and their lifecycle.",
                    "source": "owner_review",
                    "provenance": {"evidence": ["proposal.md"]},
                }
            ],
            "provenance": {
                "operation_id": f"proposal-vertical-coverage:{proposal_id}",
                "actor": "owner",
                "authority": "owner_confirmed",
                "source": "owner_review",
            },
        }
    }


def _tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        digest.update(path.relative_to(root).as_posix().encode())
        if path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()


def test_coverage_status_and_suggestion_are_read_only(tmp_path: Path) -> None:
    workspace, proposal_id = _workspace(tmp_path)
    before = _tree_hash(tmp_path)

    status = workspace.proposal_vertical_coverage_status(proposal_id)
    suggestion = workspace.suggest_proposal_vertical_coverage(proposal_id)

    assert status.state == "absent_legacy"
    assert suggestion.candidates
    assert suggestion.candidates[0].section_id == "data_model"
    assert all("heuristic_only_requires_review" in item.reasons for item in suggestion.candidates)
    assert _tree_hash(tmp_path) == before


def test_coverage_preview_and_apply_commit_artifact_state_together(tmp_path: Path) -> None:
    workspace, proposal_id = _workspace(tmp_path)
    payload = _payload(proposal_id)
    proposal_dir = workspace._proposal_document_service().find_dir(proposal_id)

    preview = workspace.preview_proposal_vertical_coverage(proposal_id, payload, actor="owner")
    assert not (proposal_dir / "vertical-coverage.yml").exists()

    result = workspace.apply_proposal_vertical_coverage(
        proposal_id,
        payload,
        preview_token=preview.preview_token,
        actor="owner",
        confirm=True,
    )

    assert result.status == "applied"
    assert workspace.proposal_vertical_coverage_status(proposal_id).state == "valid"
    artifact = next(
        item for item in workspace.read_proposal_artifacts(proposal_id).artifacts
        if item.artifact_id == "vertical_coverage"
    )
    assert artifact.status.value == "satisfied"
    assert artifact.confirmation.value == "owner_confirmed"


def test_coverage_rejects_stale_preview_and_active_vertical_change(tmp_path: Path) -> None:
    workspace, proposal_id = _workspace(tmp_path)
    payload = _payload(proposal_id)
    preview = workspace.preview_proposal_vertical_coverage(proposal_id, payload, actor="owner")
    changed = _payload(proposal_id, "system_objective")

    stale = workspace.apply_proposal_vertical_coverage(
        proposal_id,
        changed,
        preview_token=preview.preview_token,
        actor="owner",
        confirm=True,
    )
    assert stale.status == "stale_preview"

    workspace.select_project_vertical("base_project", actor="owner")
    try:
        workspace.apply_proposal_vertical_coverage(
            proposal_id,
            payload,
            preview_token=preview.preview_token,
            actor="owner",
            confirm=True,
        )
    except ValueError as exc:
        assert "active vertical" in str(exc)
    else:
        raise AssertionError("vertical change must invalidate coverage apply")


def test_coverage_commit_failure_restores_both_targets(tmp_path: Path) -> None:
    workspace, proposal_id = _workspace(tmp_path)
    proposal_dir = workspace._proposal_document_service().find_dir(proposal_id)
    state_before = (proposal_dir / "artifact-state.yml").read_bytes()

    def fail_after_first(stage: str, target: str) -> None:
        if stage == "after_replace":
            raise OSError(f"injected after {target}")

    writer = AtomicMutationWriter(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        failure_injector=fail_after_first,
    )
    service = ProposalArtifactService(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        find_proposal_dir=workspace._proposal_document_service().find_dir,
        decision_context_index=workspace.decision_context_index,
        atomic_writer=writer,
        vertical_service=workspace._project_vertical_service(),
        artifact_state_service=workspace._proposal_artifact_state_service(),
    )
    payload = _payload(proposal_id)
    preview = service.preview_vertical_coverage(proposal_id, payload, actor="owner")
    result = service.apply_vertical_coverage(
        proposal_id,
        payload,
        preview_token=preview.preview_token,
        actor="owner",
        confirm=True,
    )

    assert result.status == "rolled_back"
    assert not (proposal_dir / "vertical-coverage.yml").exists()
    assert (proposal_dir / "artifact-state.yml").read_bytes() == state_before


def test_vertical_coverage_cli_json_preview_and_import(tmp_path: Path) -> None:
    workspace, proposal_id = _workspace(tmp_path)
    source = tmp_path / "coverage.yml"
    source.write_text(yaml.safe_dump(_payload(proposal_id), sort_keys=False), encoding="utf-8")

    preview_call = runner.invoke(
        app,
        ["proposal", "vertical-coverage", "preview", proposal_id, str(source), "--actor", "owner", "--format", "json", "--root", str(tmp_path)],
    )
    assert preview_call.exit_code == 0, preview_call.output
    token = json.loads(preview_call.output)["preview_token"]

    apply_call = runner.invoke(
        app,
        ["proposal", "vertical-coverage", "import", proposal_id, str(source), "--actor", "owner", "--preview-token", token, "--confirm", "--format", "json", "--root", str(tmp_path)],
    )
    assert apply_call.exit_code == 0, apply_call.output
    assert json.loads(apply_call.output)["status"] == "applied"


def test_vertical_coverage_cli_json_suggestion_preserves_long_paths(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project(
        "Coverage",
        project_domain="software",
        vertical_id="software_project",
        owner="owner",
    )
    proposal = workspace.create_proposal_with_details(
        "Domain data model lifecycle with deliberately verbose persistence boundaries",
        problem="Domain entities, data model state transitions, and lifecycle are not explicit.",
        proposal="Define domain entities and a data model with explicit state lifecycle transitions.",
    )

    result = runner.invoke(
        app,
        [
            "proposal",
            "vertical-coverage",
            "suggest",
            proposal.proposal_id,
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["proposal_id"] == proposal.proposal_id
    assert payload["candidates"]
    assert any(
        "domain-data-model-lifecycle-with-deliberately-verbose" in source
        for source in payload["source_paths"]
    )


def test_coverage_import_adds_record_to_older_artifact_state(tmp_path: Path) -> None:
    workspace, proposal_id = _workspace(tmp_path)
    proposal_dir = workspace._proposal_document_service().find_dir(proposal_id)
    state_path = proposal_dir / "artifact-state.yml"
    workspace._proposal_artifact_state_service().initialize(proposal_id, actor="legacy-owner")
    state = yaml.safe_load(state_path.read_text(encoding="utf-8"))
    records = state["proposal_artifacts"]["artifacts"]
    state["proposal_artifacts"]["artifacts"] = [
        item for item in records if item["id"] != "vertical_coverage"
    ]
    state_path.write_text(yaml.safe_dump(state, sort_keys=False), encoding="utf-8")
    proposal_record_before = next(
        item for item in state["proposal_artifacts"]["artifacts"] if item["id"] == "proposal"
    )

    payload = _payload(proposal_id)
    preview = workspace.preview_proposal_vertical_coverage(proposal_id, payload, actor="owner")
    result = workspace.apply_proposal_vertical_coverage(
        proposal_id,
        payload,
        preview_token=preview.preview_token,
        actor="owner",
        confirm=True,
    )

    assert result.status == "applied"
    updated = yaml.safe_load(state_path.read_text(encoding="utf-8"))
    updated_records = updated["proposal_artifacts"]["artifacts"]
    assert next(item for item in updated_records if item["id"] == "proposal") == proposal_record_before
    vertical = next(item for item in updated_records if item["id"] == "vertical_coverage")
    assert vertical["status"] == "satisfied"
    assert vertical["confirmation"] == "owner_confirmed"


def test_vertical_batch_indexes_proposal_directories_once(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project(
        "Coverage scale",
        project_domain="software",
        vertical_id="software_project",
        owner="owner",
    )
    proposal_ids = tuple(f"PROP-{number:05d}" for number in range(1, 1001))
    proposals_dir = tmp_path / ".p2p/proposals"
    for proposal_id in reversed(proposal_ids):
        (proposals_dir / f"{proposal_id}-scale").mkdir()
    service = workspace._project_vertical_service()

    def unexpected_single_lookup(_proposal_id: str) -> Path:
        raise AssertionError("batch evaluation used per-proposal directory lookup")

    service.find_proposal_dir = unexpected_single_lookup
    state = service.vertical_read_state()

    statuses = service.proposal_vertical_coverage_statuses(
        proposal_ids,
        state=state,
    )
    suggestions = service.suggest_proposal_vertical_coverages(
        proposal_ids,
        state=state,
    )

    assert len(statuses) == len(suggestions) == 1000
    assert {item.state for item in statuses.values()} == {"absent_legacy"}
    assert all(not item.candidates for item in suggestions.values())
