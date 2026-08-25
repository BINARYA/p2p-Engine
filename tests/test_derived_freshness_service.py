from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from p2p_engine.cli import app
from p2p_engine.core.decision import DecisionOutcome
from p2p_engine.core.proposal_decision_events import (
    ProposalDecisionCondition,
    ProposalDecisionEventType,
    ProposalDecisionLineage,
    ProposalDecisionLineageKind,
)
from p2p_engine.core.derived_freshness import FreshnessNodeDefinition
from p2p_engine.services.derived_freshness import NODE_CATALOG, validate_freshness_graph
from p2p_engine.services.project_state import ProjectStateService
from p2p_engine.services.registries import REGISTRY_DEFINITIONS
from p2p_engine.services.proposal_decision_ledger import (
    ProposalDecisionLedgerCodec,
    render_decision_projection,
)
from tests.proposal_decision_fixtures import (
    append_event,
    record_decision,
    write_current_proposal,
)
from p2p_engine.services.software_spec import (
    SOFTWARE_SPEC_REQUIRED_FILES,
    SoftwareSpecFreshness,
)
from p2p_engine.services.workspace_transactions import AtomicMutationWriter
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.cli_assertions import cli_data


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
    record_decision(workspace, proposal.proposal_id, outcome, "Committed project direction.", "owner")
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

    assert software_specs.dependencies == ("canonical_sources",)
    assert software_specs.output_patterns == tuple(
        f".p2p/outputs/software-spec/*/{filename}"
        for filename in SOFTWARE_SPEC_REQUIRED_FILES
    )
    assert all("spec-refine.prompt.md" not in pattern for pattern in software_specs.output_patterns)


def test_software_spec_without_current_provenance_is_partial_regardless_of_mtime(
    tmp_path: Path,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Legacy spec freshness")
    proposal_id = _accepted(workspace, "Software spec source")
    change = workspace.create_change_set(proposal_id, "Software spec source")
    workspace.refresh_registries()
    workspace.refresh_project_state()
    workspace.refresh_software_spec(change.change_id)
    spec_dir = tmp_path / ".p2p" / "outputs" / "software-spec" / change.change_id
    provenance_path = spec_dir / "provenance.yml"
    provenance = yaml.safe_load(provenance_path.read_text(encoding="utf-8"))
    provenance.pop("p2p_generation", None)
    provenance_path.write_text(yaml.safe_dump(provenance, sort_keys=False), encoding="utf-8")
    for path in spec_dir.iterdir():
        if path.is_file():
            os.utime(path, (1, 1))

    node = next(
        item for item in workspace.project_freshness().nodes if item.node_id == "software_specs"
    )

    assert node.status == "partial"
    assert node.reasons == ("software_specs_invalid:1",)


def test_software_spec_aggregate_uses_per_spec_semantic_states(
    tmp_path: Path,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Semantic software specs")
    proposal_id = _accepted(workspace, "Software spec source")
    change = workspace.create_change_set(proposal_id, "Software spec source")
    workspace.refresh_registries()
    workspace.refresh_project_state()
    workspace.refresh_software_spec(change.change_id)

    current = next(
        item
        for item in workspace.project_freshness().nodes
        if item.node_id == "software_specs"
    )
    assert current.status == "current"
    assert current.reasons == ("software_specs_current:1",)

    spec_dir = tmp_path / ".p2p" / "outputs" / "software-spec" / change.change_id
    index_path = spec_dir / "index.md"
    index_path.write_text(
        index_path.read_text(encoding="utf-8") + "\nManual edit.\n",
        encoding="utf-8",
    )

    modified = next(
        item
        for item in workspace.project_freshness().nodes
        if item.node_id == "software_specs"
    )
    assert modified.status == "stale"
    assert modified.reasons == ("software_specs_modified:1",)

    (spec_dir / "acceptance.md").unlink()
    incomplete = next(
        item
        for item in workspace.project_freshness().nodes
        if item.node_id == "software_specs"
    )
    assert incomplete.status == "partial"
    assert incomplete.reasons == ("software_specs_incomplete:1",)


def test_imported_and_empty_software_spec_aggregate_policies_are_explicit(
    tmp_path: Path,
) -> None:
    empty_workspace = P2PWorkspace(tmp_path / "empty")
    empty_workspace.init_project("No software specs")
    empty = next(
        item
        for item in empty_workspace.project_freshness().nodes
        if item.node_id == "software_specs"
    )
    assert empty.status == "owner_action_required"
    assert empty.reasons == ("optional_or_curated_output_missing",)

    workspace = P2PWorkspace(tmp_path / "imported")
    workspace.init_project("Imported software spec")
    proposal_id = _accepted(workspace, "Imported source")
    change = workspace.create_change_set(proposal_id, "Imported source")
    source = tmp_path / "refined"
    source.mkdir()
    for filename in ("index.md", "requirements.md", "design.md", "acceptance.md"):
        (source / filename).write_text(f"# {filename}\n", encoding="utf-8")
    (source / "commands.yml").write_text("commands: []\n", encoding="utf-8")
    (source / "data-model.yml").write_text("entities: []\n", encoding="utf-8")
    (source / "provenance.yml").write_text(
        f"source:\n  change: {change.change_id}\n",
        encoding="utf-8",
    )
    workspace.import_software_spec(change.change_id, source)

    imported = next(
        item
        for item in workspace.project_freshness().nodes
        if item.node_id == "software_specs"
    )
    assert imported.status == "current"
    assert imported.reasons == ("software_specs_current_imported:1",)


def test_unrelated_project_projection_drift_does_not_stale_current_spec(
    tmp_path: Path,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Scoped software spec freshness")
    proposal_id = _accepted(workspace, "Software spec source")
    change = workspace.create_change_set(proposal_id, "Software spec source")
    workspace.refresh_registries()
    workspace.refresh_project_state()
    workspace.refresh_software_spec(change.change_id)
    _accepted(workspace, "Unrelated proposal")
    workspace.refresh_registries()

    nodes = {
        item.node_id: item for item in workspace.project_freshness().nodes
    }

    assert nodes["project_projections"].status == "stale"
    assert nodes["software_specs"].status == "current"
    assert nodes["software_specs"].reasons == ("software_specs_current:1",)


def test_semantic_software_spec_state_propagates_to_export_and_publication(
    tmp_path: Path,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project(
        "Semantic downstream freshness",
        owner="owner",
        vertical_id="base_project",
    )
    proposal_id = _accepted(workspace, "Software spec source")
    change = workspace.create_change_set(proposal_id, "Software spec source")
    workspace.refresh_registries()
    workspace.refresh_project_state()
    workspace.refresh_definition_maturity()
    workspace.refresh_software_spec(change.change_id)
    spec_dir = tmp_path / ".p2p" / "outputs" / "software-spec" / change.change_id
    provenance_path = spec_dir / "provenance.yml"
    provenance = yaml.safe_load(provenance_path.read_text(encoding="utf-8"))
    provenance.pop("p2p_generation")
    provenance_path.write_text(
        yaml.safe_dump(provenance, sort_keys=False),
        encoding="utf-8",
    )
    for path in spec_dir.iterdir():
        if path.is_file():
            os.utime(path, (1, 1))
    workspace.export_visible_project_definition()
    workspace.prepare_project_publication()

    invalid_nodes = {
        item.node_id: item for item in workspace.project_freshness().nodes
    }

    assert invalid_nodes["software_specs"].status == "partial"
    assert invalid_nodes["visible_export"].status == "stale"
    assert "upstream_not_current" in invalid_nodes["visible_export"].reasons
    assert invalid_nodes["publication_packet"].status == "stale"
    assert "upstream_not_current" in invalid_nodes["publication_packet"].reasons

    index_path = spec_dir / "index.md"
    index_path.write_text(
        index_path.read_text(encoding="utf-8") + "\nChanged.\n",
        encoding="utf-8",
    )
    stale_nodes = {
        item.node_id: item for item in workspace.project_freshness().nodes
    }

    assert stale_nodes["software_specs"].status == "partial"
    assert stale_nodes["visible_export"].status == "stale"
    assert "upstream_not_current" in stale_nodes["visible_export"].reasons
    assert stale_nodes["publication_packet"].status == "stale"
    assert "upstream_not_current" in stale_nodes["publication_packet"].reasons


def test_software_spec_status_and_freshness_reads_are_side_effect_free(
    tmp_path: Path,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Read-only software spec status")
    proposal_id = _accepted(workspace, "Software spec source")
    change = workspace.create_change_set(proposal_id, "Software spec source")
    workspace.refresh_registries()
    workspace.refresh_project_state()
    workspace.refresh_software_spec(change.change_id)
    before = _tree_hash(tmp_path)

    statuses = workspace.software_spec_statuses()
    freshness = workspace.project_freshness()

    assert statuses[0].freshness == SoftwareSpecFreshness.CURRENT
    assert next(
        item for item in freshness.nodes if item.node_id == "software_specs"
    ).status == "current"
    assert _tree_hash(tmp_path) == before


def test_question_and_definition_impacts_are_explicit_and_topological(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Freshness Impact", owner="owner", vertical_id="base_project")
    service = workspace._derived_freshness_service()

    question_nodes = service.impact_node_ids((".p2p/project/questions.yml",))
    definition_nodes = service.impact_node_ids((".p2p/project/definition.yml",))

    assert {"decision_context", "maturity_progress", "next_actions"} <= set(question_nodes)
    assert {"vertical_project_memory", "project_projections"} <= set(question_nodes)
    assert "software_specs" not in question_nodes
    assert {"decision_context", "vertical_project_memory", "project_projections", "assessment", "maturity_progress", "brief_context_prompt", "visible_export"} <= set(definition_nodes)
    assert "software_specs" not in definition_nodes


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

    assert current["operational_brief"].status == "current"
    assert current["next_actions"].status == "current"
    assert "supported_manual_output_newer_than_dependencies" in current["operational_brief"].reasons
    assert not any(
        action.node_id in {"operational_brief", "next_actions"}
        for action in workspace.project_freshness().rebuild_plan
    )

    workspace.create_project_brief_prompt()
    changed = {node.node_id: node for node in workspace.project_freshness().nodes}

    assert changed["operational_brief"].status == "stale"
    assert changed["next_actions"].status == "owner_action_required"


def test_next_action_audit_log_age_does_not_stale_refreshed_active_actions(
    tmp_path: Path,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Next action audit freshness", owner="owner")
    workspace.refresh_registries()
    workspace.refresh_project_state()
    workspace.create_project_brief_prompt()
    source = tmp_path / "brief.md"
    source.write_text("# Operational Brief\n\nCurrent.\n", encoding="utf-8")
    workspace.import_project_brief(source)
    log_path = tmp_path / ".p2p" / "project" / "next-actions-log.yml"
    log_path.write_text("next_action_log: []\n", encoding="utf-8")
    os.utime(log_path, (1, 1))

    workspace.next_actions_refresh()
    node = next(
        item
        for item in workspace.project_freshness().nodes
        if item.node_id == "next_actions"
    )

    assert node.status == "current"
    assert node.output_paths == (".p2p/project/next-actions.yml",)
    assert "output_older_than_dependency" not in node.reasons


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
    record_decision(
        workspace,
        conditional,
        DecisionOutcome.superseded,
        "Replaced by another proposal.",
        "owner",
        lineage=ProposalDecisionLineage(
            kind=ProposalDecisionLineageKind.supersedes,
            targets=(first,),
        ),
    )
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
    codec = ProposalDecisionLedgerCodec()
    for number in range(1, 95):
        proposal_id = f"PROP-{number:03d}"
        title = f"Projection {number:03d}"
        status = "accepted_with_changes" if number == 94 else "accepted"
        proposal_dir = proposals / f"{proposal_id}-{title.lower().replace(' ', '-')}"
        proposal_text = (
            f"# {proposal_id} - {title}\n\n"
            "## Status\n\n`draft`\n\n"
            "## Problem\n\nProjection evidence is missing.\n\n"
            "## Goals\n\n- Preserve committed authority.\n\n"
            "## Non-Goals\n\n- None.\n\n"
            "## Proposal\n\nGenerate the exact project projection.\n\n"
            "## Decision\n\nPending.\n"
        )
        event_type = ProposalDecisionEventType(status)
        ledger, event = append_event(
            codec.empty(proposal_id),
            event_type=event_type,
            conditions=(
                (
                    ProposalDecisionCondition(
                        condition_id="COND-PROP-094-001",
                        text="Complete the retained condition.",
                    ),
                )
                if status == "accepted_with_changes"
                else ()
            ),
            proposal_text_override=proposal_text,
        )
        write_current_proposal(
            proposal_dir,
            ledger,
            proposal_text_override=proposal_text,
        )
        (proposal_dir / "decision.md").write_text(
            render_decision_projection(proposal_id, event),
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
    payload = cli_data(result)["project_freshness"]
    assert payload["graph_version"] == 1
    assert any(node["node_id"] == "publication_review" for node in payload["nodes"])
    assert _tree_hash(tmp_path) == before
