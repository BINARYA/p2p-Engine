from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from p2p_engine.cli import app
from p2p_engine.core.decision import DecisionOutcome
from p2p_engine.core.derived_freshness import FreshnessNodeDefinition
from p2p_engine.services.derived_freshness import NODE_CATALOG, validate_freshness_graph
from p2p_engine.services.project_state import ProjectStateService
from p2p_engine.services.registries import REGISTRY_DEFINITIONS
from p2p_engine.services.software_spec import SOFTWARE_SPEC_REQUIRED_FILES
from p2p_engine.services.workspace_transactions import AtomicMutationWriter
from p2p_engine.storage.filesystem import P2PWorkspace


runner = CliRunner()


def _tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        digest.update(path.relative_to(root).as_posix().encode())
        if path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()


def _accepted(workspace: P2PWorkspace, title: str, outcome: DecisionOutcome = DecisionOutcome.accepted) -> str:
    proposal = workspace.create_proposal_with_details(
        title,
        problem=f"{title} needs a deterministic project projection.",
        proposal=f"Project {title} into derived state.",
    )
    workspace.record_decision(proposal.proposal_id, outcome, "Committed project direction.", "owner")
    return proposal.proposal_id


def test_freshness_graph_validates_unknown_dependencies_and_cycles() -> None:
    ordered = validate_freshness_graph(reversed(NODE_CATALOG))
    assert ordered[0].node_id == "canonical_sources"
    with pytest.raises(ValueError, match="unknown dependency"):
        validate_freshness_graph((FreshnessNodeDefinition("a", ("missing",), "x", "none", "", ()),))
    with pytest.raises(ValueError, match="cycle"):
        validate_freshness_graph(
            (
                FreshnessNodeDefinition("a", ("b",), "x", "none", "", ()),
                FreshnessNodeDefinition("b", ("a",), "x", "none", "", ()),
            )
        )


def test_freshness_detects_fresh_registry_with_stale_project_projection(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Freshness", owner="owner")
    _accepted(workspace, "First")
    workspace.refresh_registries()
    workspace.refresh_project_state()
    _accepted(workspace, "Conditional", DecisionOutcome.accepted_with_changes)
    workspace.refresh_registries()
    before = _tree_hash(tmp_path)

    freshness = workspace.project_freshness()

    assert _tree_hash(tmp_path) == before
    nodes = {node.node_id: node for node in freshness.nodes}
    assert nodes["registries"].status == "current"
    assert nodes["project_projections"].status == "stale"
    assert any("count_mismatch" in reason or "fingerprint_changed" in reason for reason in nodes["project_projections"].reasons)
    assert nodes["decision_context"].current_fingerprint_sha256
    assert [action.order for action in freshness.rebuild_plan] == list(range(1, len(freshness.rebuild_plan) + 1))
    project_action = next(action for action in freshness.rebuild_plan if action.node_id == "project_projections")
    assert project_action.command == "p2p project refresh"


def test_registry_freshness_owns_only_registry_service_outputs(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Registry ownership", owner="owner")
    workspace.refresh_registries()
    work_registry = tmp_path / ".p2p" / "registries" / "work.yml"
    work_registry.write_text("scanned_branches: []\nwork_items: []\n", encoding="utf-8")

    registry_node = next(
        node for node in workspace.project_freshness().nodes if node.node_id == "registries"
    )

    expected = sorted(
        f".p2p/registries/{definition['filename']}"
        for definition in REGISTRY_DEFINITIONS.values()
    )
    assert list(registry_node.output_paths) == expected
    assert ".p2p/registries/work.yml" not in registry_node.output_paths


def test_software_spec_freshness_owns_only_required_refresh_outputs() -> None:
    software_specs = next(
        definition for definition in NODE_CATALOG if definition.node_id == "software_specs"
    )

    assert software_specs.output_patterns == tuple(
        f".p2p/outputs/software-spec/*/{filename}"
        for filename in SOFTWARE_SPEC_REQUIRED_FILES
    )
    assert all("spec-refine.prompt.md" not in pattern for pattern in software_specs.output_patterns)


def test_supported_brief_and_next_action_writes_satisfy_manual_freshness_until_inputs_change(
    tmp_path: Path,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Manual freshness", owner="owner")
    workspace.refresh_registries()
    workspace.refresh_project_state()
    workspace.create_project_brief_prompt()
    source = tmp_path / "brief.md"
    source.write_text("# Operational Brief\n\nCurrent.\n", encoding="utf-8")
    workspace.import_project_brief(source)
    workspace.next_actions_refresh()

    current = {node.node_id: node for node in workspace.project_freshness().nodes}

    assert current["operational_brief"].status == "current_legacy_fallback"
    assert current["next_actions"].status == "current_legacy_fallback"
    assert "supported_manual_output_newer_than_dependencies" in current["operational_brief"].reasons
    assert not any(
        action.node_id in {"operational_brief", "next_actions"}
        for action in workspace.project_freshness().rebuild_plan
    )

    workspace.create_project_brief_prompt()
    changed = {node.node_id: node for node in workspace.project_freshness().nodes}

    assert changed["operational_brief"].status == "stale"
    assert changed["next_actions"].status == "owner_action_required"


def test_publication_review_cannot_become_current_from_a_fresh_file_alone(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Publication review freshness", owner="owner")
    review = tmp_path / "outputs" / "latest" / "publication-review.yml"
    review.parent.mkdir(parents=True)
    review.write_text("status: pending\n", encoding="utf-8")

    node = next(
        item for item in workspace.project_freshness().nodes if item.node_id == "publication_review"
    )

    assert node.status == "owner_action_required"


def test_projection_refresh_counts_conditional_acceptance_and_reconciles_owned_outputs(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Projection", owner="owner")
    first = _accepted(workspace, "First projection")
    conditional = _accepted(workspace, "Conditional projection", DecisionOutcome.accepted_with_changes)
    workspace.refresh_project_state()
    manifest = workspace._project_state_service().projection_manifest()["project_projection"]
    assert manifest["accepted_projection_count"] == 2
    project_node = next(
        node for node in workspace.project_freshness().nodes if node.node_id == "project_projections"
    )
    assert set(project_node.output_paths) == set(manifest["owned_paths"])

    features = tmp_path / ".p2p" / "project" / "features"
    unknown = features / "manual-owner-notes"
    unknown.mkdir()
    (unknown / "notes.md").write_text("Owner maintained.\n", encoding="utf-8")
    workspace.record_decision(conditional, DecisionOutcome.superseded, "Replaced by another proposal.", "owner")
    workspace.refresh_project_state()

    assert len(workspace._project_state_service().accepted_proposals()) == 1
    assert unknown.joinpath("notes.md").read_text(encoding="utf-8") == "Owner maintained.\n"
    generated = [path for path in features.iterdir() if path.is_dir() and path.name != "manual-owner-notes"]
    assert len(generated) == 1
    assert first in (generated[0] / "feature.md").read_text(encoding="utf-8")


def test_manual_feature_directory_cannot_mask_missing_generated_projection(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Projection identity", owner="owner")
    _accepted(workspace, "First generated")
    _accepted(workspace, "Second generated")
    workspace.refresh_registries()
    workspace.refresh_project_state()
    features = tmp_path / ".p2p" / "project" / "features"
    generated = sorted(path for path in features.iterdir() if path.is_dir())
    for child in generated[0].iterdir():
        child.unlink()
    generated[0].rmdir()
    manual = features / "manual-owner-notes"
    manual.mkdir()
    (manual / "notes.md").write_text("Owner maintained.\n", encoding="utf-8")

    freshness = workspace.project_freshness()
    project = next(node for node in freshness.nodes if node.node_id == "project_projections")

    assert project.status == "stale"
    assert any(reason.startswith("feature_projection_set_mismatch") for reason in project.reasons)


def test_freshness_detects_82_projections_for_93_accepted_plus_one_conditional(
    tmp_path: Path,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Ninety four projections", owner="owner")
    proposals = tmp_path / ".p2p" / "proposals"
    for number in range(1, 95):
        proposal_id = f"PROP-{number:03d}"
        title = f"Projection {number:03d}"
        status = "accepted_with_changes" if number == 94 else "accepted"
        proposal_dir = proposals / f"{proposal_id}-{title.lower().replace(' ', '-')}"
        proposal_dir.mkdir()
        (proposal_dir / "proposal.md").write_text(
            f"# {proposal_id} - {title}\n\n"
            f"## Status\n`{status}`\n\n"
            "## Problem\nProjection evidence is missing.\n\n"
            "## Goals\n- Preserve committed authority.\n\n"
            "## Non-Goals\n- None.\n\n"
            "## Proposal\nGenerate the exact project projection.\n\n"
            "## Decision\nCommitted.\n",
            encoding="utf-8",
        )
        (proposal_dir / "decision.md").write_text(
            f"# Decision - {proposal_id}\n\n## Status\n`{status}`\n",
            encoding="utf-8",
        )
        (proposal_dir / "tasks.yml").write_text("tasks: []\n", encoding="utf-8")

    workspace.refresh_registries()
    project_dir = tmp_path / ".p2p" / "project"
    features = project_dir / "features"
    features.mkdir(exist_ok=True)
    for number in range(1, 83):
        feature = features / f"projection-{number:03d}"
        feature.mkdir()
        (feature / "feature.md").write_text(
            f"# Projection {number:03d}\n\n## Provenance\n\n- proposal: PROP-{number:03d}\n",
            encoding="utf-8",
        )
    (project_dir / "decisions-map.yml").write_text(
        yaml.safe_dump(
            {
                "decisions": [
                    {"proposal": f"PROP-{number:03d}"}
                    for number in range(1, 83)
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    freshness = workspace.project_freshness()
    project = next(node for node in freshness.nodes if node.node_id == "project_projections")

    accepted = workspace._project_state_service().accepted_proposals()
    assert len(accepted) == 94
    assert sum(item["status"] == "accepted_with_changes" for item in accepted) == 1
    assert project.status == "stale"
    assert "decision_projection_count_mismatch:82!=94" in project.reasons
    assert "feature_projection_set_mismatch:generated=82,expected=94" in project.reasons


def test_projection_refresh_failure_restores_owned_files(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Projection rollback", owner="owner")
    _accepted(workspace, "First projection")
    workspace.refresh_project_state()
    overview = tmp_path / ".p2p" / "project" / "overview.md"
    before = overview.read_bytes()
    _accepted(workspace, "Second projection")

    def fail(stage: str, target: str) -> None:
        if stage == "after_replace":
            raise OSError(f"injected failure after {target}")

    original = workspace._project_state_service()
    service = ProjectStateService(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        accepted_proposals=original.accepted_proposals,
        project_name=original.project_name,
        next_actions=original.next_actions,
        registry_status=original.registry_status,
        project_brief_context=original.project_brief_context,
        validate_yaml_key=original.validate_yaml_key,
        atomic_writer=AtomicMutationWriter(
            root=tmp_path,
            p2p_dir=tmp_path / ".p2p",
            failure_injector=fail,
        ),
    )

    with pytest.raises(ValueError, match="rolled back"):
        service.refresh()
    assert overview.read_bytes() == before


def test_project_freshness_cli_json_is_read_only(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Freshness CLI", owner="owner")
    before = _tree_hash(tmp_path)

    result = runner.invoke(app, ["project", "freshness", "--format", "json", "--root", str(tmp_path)])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)["project_freshness"]
    assert payload["graph_version"] == 1
    assert any(node["node_id"] == "publication_review" for node in payload["nodes"])
    assert _tree_hash(tmp_path) == before
