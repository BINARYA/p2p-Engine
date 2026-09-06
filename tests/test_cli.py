from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml
from typer.testing import CliRunner

from p2p_engine.cli import app
from p2p_engine.foundation.markdown import read_frontmatter, replace_frontmatter
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.cli_assertions import cli_data
from tests.filesystem_assertions import assert_no_workspace_mutation
from tests.proposal_decision_fixtures import ensure_global_scope
from tests.publication_fixtures import write_publication_candidates

runner = CliRunner()


def test_cli_spec_export_help_classifies_software_spec_handoff() -> None:
    group = runner.invoke(app, ["spec", "--help"])
    command = runner.invoke(app, ["spec", "export", "--help"])

    assert group.exit_code == 0
    assert command.exit_code == 0
    assert "software-spec handoff bundle" in group.output
    assert "software-spec handoff bundle" in command.output
    assert "project definition outputs" not in group.output
    assert "project definition outputs" not in command.output


def _apply_proposal_decision(
    root: Path,
    proposal_id: str,
    *,
    outcome: str = "accepted",
    reason: str = "Ready.",
    approver: str = "owner",
    override_readiness: bool = False,
):
    ensure_global_scope(P2PWorkspace(root), proposal_id, actor=approver)
    command = {
        "accepted": "accept",
        "rejected": "reject",
        "deferred": "defer",
    }[outcome]
    base = [
        "proposal",
        command,
        proposal_id,
        "--reason",
        reason,
        "--approver",
        approver,
    ]
    if override_readiness:
        base.append("--override-readiness")
    preview = runner.invoke(
        app,
        [*base, "--format", "json", "--root", str(root)],
    )
    assert preview.exit_code == 0, preview.output
    payload = cli_data(preview)
    request = payload["request"]
    mutation = payload["preview"]
    apply_arguments = [
        *base,
        "--decided-on",
        request["decided_on"],
        "--operation-key",
        request["operation_key"],
        "--preview-token",
        mutation["preview_token"],
        "--confirm",
        "--format",
        "json",
        "--root",
        str(root),
    ]
    if request["source_head_event_id"]:
        apply_arguments.extend(
            ["--source-head-event-id", request["source_head_event_id"]]
        )
    applied = runner.invoke(app, apply_arguments)
    assert applied.exit_code == 0, applied.output
    return applied


def _assert_codex_curator_skill(root: Path) -> None:
    skill = root / ".agents" / "skills" / "p2p-project-curator" / "SKILL.md"

    assert skill.exists()
    content = skill.read_text(encoding="utf-8")
    assert "name: p2p-project-curator" in content
    assert "p2p project publish prepare" in content
    assert "reader who has no knowledge of P2P" in content
    for name in (
        "editorial-workflow.md",
        "publication-contracts.md",
        "vertical-interpretation.md",
        "editorial-rubric.md",
    ):
        assert f"references/{name}" in content
        assert (skill.parent / "references" / name).is_file()


def test_cli_init_status_create_and_prompt_flow(tmp_path: Path) -> None:
    result = runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "P2P workspace initialized" in result.output
    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / ".p2p" / "agent-policy.yml").exists()
    assert (tmp_path / ".p2p" / "project" / "rubrics.yml").exists()
    permissions = yaml.safe_load((tmp_path / ".p2p" / "project" / "permissions.yml").read_text(encoding="utf-8"))
    agent_policy = yaml.safe_load((tmp_path / ".p2p" / "agent-policy.yml").read_text(encoding="utf-8"))
    assert permissions["permissions"]["model"] == "role_plus_consent_receipt"
    assert permissions["identities"]["owner"]["role"] == "owner"
    assert permissions["identities"]["contributor"]["role"] == "contributor"
    assert agent_policy["proposal_readiness"]["inspect_before_acceptance_recommendation"] is True
    assert agent_policy["project_vertical_orchestration"]["prioritize_when_missing_or_fallback"] is True
    assert agent_policy["write_policy"]["analysis_without_write"] == "allowed"
    assert agent_policy["write_policy"]["preview_can_be_skipped_when"] == (
        "owner_requested_exact_operation_and_artifact"
    )
    assert agent_policy["placement_policy"]["mode"] == "strict"
    assert agent_policy["placement_policy"]["unknown_destination"]["behavior"] == "preview_and_ask_or_stop"
    assert agent_policy["artifact_contract_policy"]["agent_must_not_invent_durable_output_paths"] is True
    agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "Do not create, edit, rename, or delete files under `.p2p/` by hand" in agents
    assert "Persistent Write Policy" in agents
    assert "Do not invent durable output paths." in agents
    assert "stop and report the limitation" in agents
    assert "Do not explain existing P2P artifacts only from conversation memory" in agents
    assert "Before recommending proposal acceptance, inspect readiness" in agents
    assert "ask one focused question at a time" in agents
    assert "p2p proposal questions next PROP-XXX" in agents
    assert "Project Vertical Orchestration" in agents
    assert "p2p project readiness review" in agents
    assert "p2p project vertical scaffold" in agents
    assert "p2p context --budget small" in agents
    assert "Runtime Bootstrap" in agents
    assert "uv tool environment outside the project" in agents
    assert "do not install uv, Python or P2P Engine" in agents
    assert ".venv/bin/p2p agent doctor" in agents
    assert ".venv/Scripts/p2p.exe agent doctor" in agents
    assert "python -m p2p_engine agent doctor" in agents
    assert (tmp_path / ".p2p" / "project" / "runtime.yml").exists()
    assert (tmp_path / "P2P-SETUP.md").exists()

    result = runner.invoke(app, ["status", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Project: Demo Project" in result.output
    assert "Proposals: none" in result.output

    result = runner.invoke(app, ["check", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Workspace OK" in result.output

    result = runner.invoke(
        app,
        [
            "proposal",
            "create",
            "Exploration Phase",
            "--problem",
            "Ideas need structured exploration.",
            "--goal",
            "Generate exploration prompts.",
            "--acceptance",
            "explore prompt creates a file.",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert "id: PROP-001" in result.output
    assert "Next canonical P2P commands:" in result.output
    assert "p2p contribution add PROP-001" in result.output
    assert "p2p proposal readiness init PROP-001" in result.output

    proposal_dir = tmp_path / ".p2p" / "proposals" / "PROP-001-exploration-phase"
    proposal = (proposal_dir / "proposal.md").read_text(encoding="utf-8")
    assert "Ideas need structured exploration." in proposal
    assert "- Generate exploration prompts." in proposal
    assert not (proposal_dir / "findings.md").exists()
    assert not (proposal_dir / "open-questions.md").exists()

    result = runner.invoke(
        app,
        [
            "proposal",
            "contribution",
            "add",
            "PROP-001",
            "Explore rough ideas before synthesis.",
            "--type",
            "objective",
            "--relevance",
            "high",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert "Contribution added" in result.output

    result = runner.invoke(app, ["explore", "prompt", "PROP-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert ".p2p/prompts/PROP-001/explore.prompt.md" in result.output

    prompt = (tmp_path / ".p2p" / "prompts" / "PROP-001" / "explore.prompt.md").read_text(
        encoding="utf-8"
    )
    assert "P2P Exploration Prompt" in prompt
    assert "findings.md" in prompt

    result = runner.invoke(app, ["explore", "status", "PROP-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Exploration status for PROP-001" in result.output
    assert "open-questions.md" in result.output
    assert "missing" in result.output


def test_cli_runtime_status_text_and_json(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Runtime Project", "--root", str(tmp_path)])

    text = runner.invoke(app, ["runtime", "status", "--root", str(tmp_path)])

    assert text.exit_code == 0
    assert "Runtime" in text.output
    assert "state: compatible" in text.output
    assert ".p2p/project/runtime.yml" in text.output

    json_result = runner.invoke(app, ["runtime", "status", "--format", "json", "--root", str(tmp_path)])

    assert json_result.exit_code == 0
    payload = cli_data(json_result)
    assert payload["state"] == "compatible"
    assert payload["contract_path"] == ".p2p/project/runtime.yml"


def test_cli_runtime_status_reports_missing_contract(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Runtime Project", "--root", str(tmp_path)])
    (tmp_path / ".p2p" / "project" / "runtime.yml").unlink()

    result = runner.invoke(app, ["runtime", "status", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert "state: missing_contract" in result.output
    assert "P2P266_RUNTIME_CONTRACT_MISSING" in result.output


def test_cli_runtime_contract_preview_and_apply_json(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Runtime Project", "--root", str(tmp_path)])
    runtime_path = tmp_path / ".p2p" / "project" / "runtime.yml"
    runtime_path.write_text(
        yaml.safe_dump(
            {
                "runtime_contract": {"schema_version": 1},
                "runtime": {"p2p": {"requires": ">=0.0.0,<9999.0", "recommended": "0.0.1"}},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    preview = runner.invoke(
        app,
        [
            "runtime",
            "contract",
            "preview",
            "--requires",
            ">=0.0.0,<9999.0",
            "--recommended",
            "0.0.2",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )

    assert preview.exit_code == 0
    preview_payload = cli_data(preview)
    assert preview_payload["status"] == "applicable"
    assert preview_payload["expected_state_token"]

    applied = runner.invoke(
        app,
        [
            "runtime",
            "contract",
            "apply",
            "--requires",
            ">=0.0.0,<9999.0",
            "--recommended",
            "0.0.2",
            "--expected-state-token",
            preview_payload["expected_state_token"],
            "--confirm",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )

    assert applied.exit_code == 0
    apply_payload = cli_data(applied)
    assert apply_payload["status"] == "updated"
    assert apply_payload["files_changed"] == ["P2P-SETUP.md", ".p2p/project/runtime.yml"]
    payload = yaml.safe_load(runtime_path.read_text(encoding="utf-8"))
    assert payload["runtime"]["p2p"]["recommended"] == "0.0.2"


def test_cli_runtime_contract_preview_text_output(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Runtime Project", "--root", str(tmp_path)])
    runtime_path = tmp_path / ".p2p" / "project" / "runtime.yml"
    payload = yaml.safe_load(runtime_path.read_text(encoding="utf-8"))
    p2p_runtime = payload["runtime"]["p2p"]

    result = runner.invoke(
        app,
        [
            "runtime",
            "contract",
            "preview",
            "--requires",
            p2p_runtime["requires"],
            "--recommended",
            p2p_runtime["recommended"],
            "--root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "Runtime contract preview" in result.output
    assert "status: no_change" in result.output
    assert "impact_labels: none" in result.output


def test_cli_runtime_contract_adopt_is_not_registered(tmp_path: Path) -> None:
    with assert_no_workspace_mutation(tmp_path):
        result = runner.invoke(app, ["runtime", "contract", "adopt", "--root", str(tmp_path)])

    assert result.exit_code != 0
    assert "No such command 'adopt'" in result.output


def test_cli_project_interaction_style_show_and_set(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Style Project", "--root", str(tmp_path)])

    shown = runner.invoke(app, ["project", "interaction-style", "show", "--root", str(tmp_path)])
    assert shown.exit_code == 0
    assert "Project interaction style" in shown.output
    assert "configured: false" in shown.output
    assert "technical_verbosity: 2  balanced" in shown.output
    assert "formality: 2  direct" in shown.output
    assert "assertiveness: 0  baseline" in shown.output
    assert not (tmp_path / ".p2p" / "project" / "interaction-style.yml").exists()

    updated = runner.invoke(
        app,
        [
            "project",
            "interaction-style",
            "set",
            "--technical-verbosity",
            "4",
            "--assertiveness",
            "3",
            "--actor",
            "codex",
            "--root",
            str(tmp_path),
        ],
    )
    assert updated.exit_code == 0
    assert "Project interaction style updated" in updated.output
    assert "configured: true" in updated.output
    assert "technical_verbosity: 4  detailed" in updated.output
    assert "formality: 2  direct" in updated.output
    assert "assertiveness: 3  proactive" in updated.output
    payload = yaml.safe_load((tmp_path / ".p2p" / "project" / "interaction-style.yml").read_text(encoding="utf-8"))
    assert payload["interaction_style"]["updated_by"] == "codex"

    missing = runner.invoke(app, ["project", "interaction-style", "set", "--root", str(tmp_path)])
    assert missing.exit_code == 1
    assert "At least one interaction style value is required" in missing.output

    invalid = runner.invoke(
        app,
        ["project", "interaction-style", "set", "--formality", "6", "--root", str(tmp_path)],
    )
    assert invalid.exit_code == 1
    assert "Invalid interaction style value for formality: 6" in invalid.output


def test_cli_init_owner_populates_permissions_policy(tmp_path: Path) -> None:
    result = runner.invoke(app, ["init", "Demo Project", "--owner", "Matteo Rossi", "--root", str(tmp_path)])

    assert result.exit_code == 0
    permissions = yaml.safe_load((tmp_path / ".p2p" / "project" / "permissions.yml").read_text(encoding="utf-8"))
    assert permissions["identities"]["matteo-rossi"]["role"] == "owner"
    assert permissions["identities"]["matteo-rossi"]["display_name"] == "Matteo Rossi"

    result = runner.invoke(app, ["permissions", "show", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "matteo-rossi:" in result.output
    assert "role: owner" in result.output


def test_cli_project_export_writes_visible_latest_and_review_snapshot(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "Visible Project Output",
            "--problem",
            "Project definitions are hard to inspect when hidden under P2P state.",
            "--goal",
            "Generate a visible project document.",
            "--non-goal",
            "Do not replace managed P2P state.",
            "--proposal",
            "Write a chaptered project definition to outputs/latest/project.md.",
            "--acceptance",
            "outputs/latest/project.md exists.",
            "--root",
            str(tmp_path),
        ],
    )
    _apply_proposal_decision(tmp_path, "PROP-001")

    result = runner.invoke(app, ["project", "export", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert "Project definition exported" in result.output
    assert "latest: outputs/latest/project.md" in result.output
    assert "archived: none" in result.output
    latest = tmp_path / "outputs" / "latest" / "project.md"
    assert latest.exists()
    latest_text = latest.read_text(encoding="utf-8")
    assert "# Demo Project Project Definition" in latest_text
    assert "source_of_truth: .p2p/" in latest_text
    assert "## Accepted Proposals And Decisions" in latest_text
    assert (tmp_path / "outputs" / "latest" / "exports").is_dir()

    latest.write_text("old generated output\n", encoding="utf-8")
    result = runner.invoke(app, ["project", "export", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert "archived: outputs/review-001" in result.output
    assert (tmp_path / "outputs" / "review-001" / "project.md").read_text(encoding="utf-8") == "old generated output\n"

    status = runner.invoke(app, ["project", "export-status", "--root", str(tmp_path)])
    assert status.exit_code == 0
    assert "latest_exists: true" in status.output
    assert "outputs/review-001" in status.output


def test_cli_project_publish_prepare_import_and_status(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "Canonical Project Publication",
            "--problem",
            "Generated project output is hard to read.",
            "--goal",
            "Prepare one canonical human project publication.",
            "--proposal",
            "Create a staged publication pipeline above outputs/latest/project.md.",
            "--acceptance",
            "A curated publication can be imported.",
            "--root",
            str(tmp_path),
        ],
    )
    _apply_proposal_decision(tmp_path, "PROP-001")

    first = runner.invoke(app, ["project", "publish", "prepare", "--root", str(tmp_path)])
    second = runner.invoke(app, ["project", "publish", "prepare", "--root", str(tmp_path)])

    assert first.exit_code == 0
    assert "Project publication prepared" in first.output
    assert "exported: true" in first.output
    assert "edition: project-en" in first.output
    assert "curator_input: outputs/latest/publications/project-en/curator-input.md" in first.output
    assert "candidate_model: drafts/project-publication/project-en.model.yml" in first.output
    assert second.exit_code == 0
    assert "exported: false" in second.output
    assert "reused_export: true" in second.output
    assert not (tmp_path / "outputs" / "review-001").exists()

    draft, model, accounting = write_publication_candidates(tmp_path)
    imported = runner.invoke(
        app,
        [
            "project",
            "publish",
            "import",
            str(draft),
            "--model",
            str(model),
            "--evidence-accounting",
            str(accounting),
            "--root",
            str(tmp_path),
        ],
    )
    assert imported.exit_code == 0
    assert "Project publication imported" in imported.output
    assert "curated: outputs/latest/project-en.md" in imported.output
    assert "model: outputs/latest/publications/project-en/project-model.yml" in imported.output

    before_validation = runner.invoke(app, ["project", "publish", "status", "--root", str(tmp_path)])
    assert before_validation.exit_code == 0
    assert "curated: ready" in before_validation.output
    assert "validation: missing" in before_validation.output

    validation = runner.invoke(app, ["project", "publish", "validate", "--root", str(tmp_path)])
    assert validation.exit_code == 0
    assert "Project publication validation" in validation.output
    assert "status: passed" in validation.output

    status = runner.invoke(app, ["project", "publish", "status", "--root", str(tmp_path)])
    assert status.exit_code == 0
    assert "approved_for_publication: false" in status.output
    assert "validation_status: passed" in status.output
    assert "validation: ready" in status.output

    italian = runner.invoke(
        app,
        [
            "project",
            "publish",
            "prepare",
            "--language",
            "it",
            "--output-name",
            "manual",
            "--root",
            str(tmp_path),
        ],
    )
    editions = runner.invoke(app, ["project", "publish", "list", "--root", str(tmp_path)])
    assert italian.exit_code == 0
    assert "edition: manual-it" in italian.output
    assert editions.exit_code == 0
    assert "manual-it" in editions.output
    assert "project-en" in editions.output


def test_cli_project_publish_render_and_review_with_fake_renderer(tmp_path: Path, monkeypatch) -> None:
    def fake_renderer(markdown_text: str, output_path: Path, root: Path, **metadata) -> str:
        assert metadata["language"] == "en"
        output_path.write_bytes(b"%PDF-1.4\n% fake cli publication pdf\n")
        return "fake-cli-renderer"

    monkeypatch.setattr("p2p_engine.services.project_publication.render_pdf_with_weasyprint", fake_renderer)
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "Canonical Project Publication",
            "--problem",
            "Generated project output is hard to read.",
            "--goal",
            "Prepare one canonical human project publication.",
            "--proposal",
            "Create a staged publication pipeline above outputs/latest/project.md.",
            "--acceptance",
            "A curated publication can be imported.",
            "--root",
            str(tmp_path),
        ],
    )
    _apply_proposal_decision(tmp_path, "PROP-001")
    runner.invoke(app, ["project", "publish", "prepare", "--root", str(tmp_path)])
    draft, model, accounting = write_publication_candidates(tmp_path)
    runner.invoke(
        app,
        [
            "project",
            "publish",
            "import",
            str(draft),
            "--model",
            str(model),
            "--evidence-accounting",
            str(accounting),
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(app, ["project", "publish", "validate", "--root", str(tmp_path)])

    rendered = runner.invoke(app, ["project", "publish", "render", "--root", str(tmp_path)])
    reviewed = runner.invoke(
        app,
        [
            "project",
            "publish",
            "review",
            "--status",
            "approved",
            "--reviewer",
            "owner",
            "--note",
            "Ready.",
            "--root",
            str(tmp_path),
        ],
    )
    status = runner.invoke(app, ["project", "publish", "status", "--root", str(tmp_path)])

    assert rendered.exit_code == 0
    assert "Project publication PDF rendered" in rendered.output
    assert reviewed.exit_code == 0
    assert "Project publication review recorded" in reviewed.output
    assert "approved_for_publication: true" in status.output
    assert "render_status: rendered" in status.output
    assert "review_status: approved" in status.output


def test_cli_permissions_actor_and_consent_receipts(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--owner", "matteo", "--root", str(tmp_path)])

    result = runner.invoke(
        app,
        [
            "permissions",
            "actor",
            "add",
            "lorenzo",
            "--role",
            "contributor",
            "--kind",
            "person",
            "--root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "Permission actor recorded" in result.output
    assert "actor: lorenzo" in result.output

    result = runner.invoke(
        app,
        [
            "consent",
            "grant",
            "proposal_decision_apply",
            "PROP-001",
            "--actor",
            "lorenzo",
            "--approved-by",
            "matteo",
            "--expires-on",
            "2026-06-03",
            "--root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "Consent granted" in result.output
    assert "consent: CONSENT-001" in result.output
    assert "operation: proposal_decision_apply" in result.output

    consent_path = tmp_path / ".p2p" / "consents" / "CONSENT-001" / "consent.yml"
    receipt = yaml.safe_load(consent_path.read_text(encoding="utf-8"))
    assert receipt["actor_id"] == "lorenzo"
    assert receipt["approved_by"] == "matteo"
    assert receipt["single_use"] is True

    result = runner.invoke(app, ["consent", "status", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "CONSENT-001  granted  proposal_decision_apply  PROP-001  lorenzo" in result.output

    result = runner.invoke(app, ["consent", "show", "CONSENT-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "approved_by: matteo" in result.output

    result = runner.invoke(app, ["consent", "revoke", "CONSENT-001", "--reason", "No longer needed.", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Consent revoked" in result.output
    assert "status: revoked" in result.output


def test_cli_consent_grant_requires_owner_approver(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--owner", "matteo", "--root", str(tmp_path)])
    runner.invoke(app, ["permissions", "actor", "add", "lorenzo", "--role", "contributor", "--root", str(tmp_path)])

    result = runner.invoke(
        app,
        [
            "consent",
            "grant",
            "proposal_decision_apply",
            "PROP-001",
            "--actor",
            "lorenzo",
            "--approved-by",
            "lorenzo",
            "--root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 1
    assert "Only an owner identity can approve consent receipts" in result.output


def test_cli_validate_reports_invalid_permissions_policy(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    permissions_path = tmp_path / ".p2p" / "project" / "permissions.yml"
    data = yaml.safe_load(permissions_path.read_text(encoding="utf-8"))
    data["identities"]["owner"]["role"] = "superuser"
    permissions_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    result = runner.invoke(app, ["validate", "--root", str(tmp_path)])

    assert result.exit_code == 1
    assert "P2P213_INVALID_PERMISSION_ROLE" in result.output


def test_cli_init_default_domain_is_empty_and_generic_structure_is_explicit(tmp_path: Path) -> None:
    result = runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])

    assert result.exit_code == 0
    domain = yaml.safe_load((tmp_path / ".p2p" / "project" / "domain.yml").read_text(encoding="utf-8"))
    rubrics = yaml.safe_load((tmp_path / ".p2p" / "project" / "rubrics.yml").read_text(encoding="utf-8"))
    source = yaml.safe_load(
        (tmp_path / ".p2p" / "project" / "structure-source.yml").read_text(
            encoding="utf-8"
        )
    )

    assert domain["project_domain"]["descriptor"] is None
    assert source["structure_source"]["source"] == {
        "kind": "starter",
        "starter_id": "generic",
    }
    assert rubrics["status"] == "vertical_selected"
    assert rubrics["criteria"]
    assert not (tmp_path / ".p2p" / "project" / "next-actions.yml").exists()

    result = runner.invoke(app, ["assess", "maturity", "refresh", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert "status: calculated" in result.output


def test_cli_init_domain_and_vertical_are_independent(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "init",
            "Demo Project",
            "--domain",
            "gardening",
            "--vertical",
            "binarya/software_project@2.0.0",
            "--root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    domain = yaml.safe_load((tmp_path / ".p2p" / "project" / "domain.yml").read_text(encoding="utf-8"))
    rubrics = yaml.safe_load((tmp_path / ".p2p" / "project" / "rubrics.yml").read_text(encoding="utf-8"))

    assert domain["project_domain"]["descriptor"]["key"] == "gardening"
    assert rubrics["status"] == "vertical_selected"
    assert rubrics["structure_source"] == {
        "kind": "vertical_release",
        "coordinate": "binarya/software_project@2.0.0",
    }
    assert any(
        criterion["id"] == "software_constraints_nfr_coverage"
        for criterion in rubrics["criteria"]
    )
    assert not (tmp_path / ".p2p" / "project" / "next-actions.yml").exists()


def test_cli_validate_valid_project_and_json_output(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["registry", "refresh", "--root", str(tmp_path)])

    result = runner.invoke(app, ["validate", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert "Validation" in result.output
    assert "errors: 0" in result.output

    result = runner.invoke(app, ["validate", "--format", "json", "--root", str(tmp_path)])

    assert result.exit_code == 0
    payload = cli_data(result)
    assert payload["ok"] is True
    assert payload["errors"] == 0


def test_cli_governance_policy_read_only_surfaces(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Vote Target", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "choice",
            "create",
            "--title",
            "Deployment Strategy",
            "--problem",
            "Choose the deployment strategy.",
            "--context",
            "The project needs one stable governed deployment direction.",
            "--option",
            "Blue",
            "--option",
            "Green",
            "--related",
            "PROP-001",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(
        app,
        [
            "vote",
            "record",
            "PROP-001",
            "--choice",
            "A",
            "--reason",
            "Prefer blue.",
            "--voter",
            "owner",
            "--role",
            "owner",
            "--root",
            str(tmp_path),
        ],
    )
    precedent_path = tmp_path / ".p2p" / "governance" / "decision-precedents.yml"
    precedent_path.parent.mkdir(parents=True, exist_ok=True)
    precedent_path.write_text(
        yaml.safe_dump({"precedents": [{"id": "DP001", "related_choices": ["CHOICE-001"]}]}),
        encoding="utf-8",
    )
    before = {
        path.relative_to(tmp_path): path.read_text(encoding="utf-8")
        for path in sorted((tmp_path / ".p2p").rglob("*"))
        if path.is_file()
    }

    preflight = runner.invoke(
        app,
        [
            "choice",
            "governance-preflight",
            "CHOICE-001",
            "--option",
            "B",
            "--actor",
            "owner",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )
    vote_status = runner.invoke(app, ["vote", "status", "PROP-001", "--format", "json", "--root", str(tmp_path)])
    governance_validate = runner.invoke(app, ["governance", "validate", "--format", "json", "--root", str(tmp_path)])

    assert preflight.exit_code == 0
    payload = cli_data(preflight)
    assert payload["schema_version"] == "governance-preflight/v1"
    assert payload["vote_summary"]["alignment"] == "conflicts"
    assert "P2P_GOV_VOTE_CONFLICT" in [warning["code"] for warning in payload["warnings"]]
    assert "P2P_GOV_RELATED_PRECEDENTS" in [warning["code"] for warning in payload["warnings"]]
    decision = tmp_path / ".p2p" / "choices" / "CHOICE-001-deployment-strategy" / "decision.md"
    assert "Pending." in decision.read_text(encoding="utf-8")
    assert vote_status.exit_code == 0
    assert cli_data(vote_status)["winner"] == "A"
    assert governance_validate.exit_code == 0
    assert cli_data(governance_validate)["ok"] is True
    after = {
        path.relative_to(tmp_path): path.read_text(encoding="utf-8")
        for path in sorted((tmp_path / ".p2p").rglob("*"))
        if path.is_file()
    }
    assert after == before


def test_cli_precedent_search_matches_explicit_fields_only(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    precedent_path = tmp_path / ".p2p" / "governance" / "decision-precedents.yml"
    precedent_path.parent.mkdir(parents=True, exist_ok=True)
    precedent_path.write_text(
        yaml.safe_dump(
            {
                "precedents": [
                    {
                        "id": "DP001",
                        "title": "Deployment precedent",
                        "related_choices": ["CHOICE-001"],
                        "tags": ["deployment"],
                    },
                    {
                        "id": "DP002",
                        "title": "Similar deployment title",
                        "tags": ["release"],
                    },
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    explicit = runner.invoke(
        app,
        ["precedent", "search", "--choice", "CHOICE-001", "--format", "json", "--root", str(tmp_path)],
    )
    fuzzy = runner.invoke(
        app,
        ["precedent", "search", "--tag", "deployments", "--format", "json", "--root", str(tmp_path)],
    )

    assert explicit.exit_code == 0
    assert [(item["precedent_id"], item["match_reason"]) for item in cli_data(explicit)["precedents"]] == [
        ("DP001", "related_choice")
    ]
    assert fuzzy.exit_code == 0
    assert cli_data(fuzzy)["precedents"] == []


def test_cli_validate_reports_invalid_yaml_as_error(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    (tmp_path / ".p2p" / "project.yml").write_text("project: [\n", encoding="utf-8")

    result = runner.invoke(app, ["validate", "--root", str(tmp_path)])

    assert result.exit_code == 1
    assert "P2P010_INVALID_YAML" in result.output


def test_cli_validate_reports_invalid_proposal_questions(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Question Validation", "--root", str(tmp_path)])
    questions_path = tmp_path / ".p2p" / "proposals" / "PROP-001-question-validation" / "questions.yml"
    questions_path.write_text(
        "proposal_questions:\n"
        "  schema_version: 1\n"
        "  proposal_id: PROP-001\n"
        "  groups: []\n"
        "  questions:\n"
        "    - id: Q001\n"
        "      state: invalid\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["validate", "--root", str(tmp_path)])

    assert result.exit_code == 1
    assert "P2P232_INVALID_PROPOSAL_QUESTIONS" in result.output


def test_cli_validate_reports_stale_registries_as_warning(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Draft Work", "--root", str(tmp_path)])

    result = runner.invoke(app, ["validate", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert "P2P201_STALE_REGISTRY" in result.output
    assert "command: p2p registry refresh" in result.output


def test_cli_validate_reports_duplicate_proposal_ids_as_error(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Draft Work", "--root", str(tmp_path)])
    proposals_dir = tmp_path / ".p2p" / "proposals"
    shutil.copytree(proposals_dir / "PROP-001-draft-work", proposals_dir / "PROP-001-other-draft")

    result = runner.invoke(app, ["validate", "--root", str(tmp_path)])

    assert result.exit_code == 1
    assert "P2P104_DUPLICATE_PROPOSAL_ID" in result.output
    assert "Duplicate proposal ID PROP-001" in result.output
    assert "PROP-001-draft-work" in result.output
    assert "PROP-001-other-draft" in result.output


def test_cli_registry_refresh_rejects_duplicate_proposal_ids(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Draft Work", "--root", str(tmp_path)])
    proposals_dir = tmp_path / ".p2p" / "proposals"
    shutil.copytree(proposals_dir / "PROP-001-draft-work", proposals_dir / "PROP-001-other-draft")

    result = runner.invoke(app, ["registry", "refresh", "--root", str(tmp_path)])

    assert result.exit_code == 1
    assert "Duplicate proposal IDs found" in result.output
    assert "PROP-001" in result.output
    assert "generated registries would be ambiguous" in result.output


def test_cli_proposal_show_reports_ambiguous_duplicate_id_guidance(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Draft Work", "--root", str(tmp_path)])
    proposals_dir = tmp_path / ".p2p" / "proposals"
    shutil.copytree(proposals_dir / "PROP-001-draft-work", proposals_dir / "PROP-001-other-draft")

    result = runner.invoke(app, ["proposal", "show", "PROP-001", "--root", str(tmp_path)])

    assert result.exit_code == 1
    assert "Ambiguous proposal ID: PROP-001" in result.output
    assert "p2p validate" in result.output


def test_cli_assess_refresh_and_show(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Draft Work", "--root", str(tmp_path)])
    runner.invoke(app, ["registry", "refresh", "--root", str(tmp_path)])

    result = runner.invoke(app, ["assess", "refresh", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert "Project assessment refreshed" in result.output
    assert "Project readiness assessment" in result.output
    assert "completion:" in result.output
    assert "Accept at least one proposal" in result.output
    assert (tmp_path / ".p2p" / "project" / "assessment.yml").exists()

    result = runner.invoke(app, ["assess", "show", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert "Project readiness assessment" in result.output
    assert "maturity: n/a not_assessed" in result.output


def test_cli_assess_show_requires_refresh(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])

    result = runner.invoke(app, ["assess", "show", "--root", str(tmp_path)])

    assert result.exit_code == 1
    assert "Project assessment not found" in result.output


def test_cli_project_rubrics_and_definition_maturity(tmp_path: Path) -> None:
    runner.invoke(
        app,
        [
            "init",
            "Demo Project",
            "--domain",
            "software",
            "--vertical",
            "binarya/software_project@2.0.0",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "Security Model",
            "--problem",
            "Security and privacy risks need explicit permission boundaries.",
            "--proposal",
            "Define auth, sandbox permissions, and privacy expectations.",
            "--root",
            str(tmp_path),
        ],
    )
    _apply_proposal_decision(tmp_path, "PROP-001", reason="Needed.")

    result = runner.invoke(app, ["project", "rubrics", "show", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert "structure source: binarya/software_project@2.0.0" in result.output
    assert "software_constraints_nfr_coverage" in result.output

    result = runner.invoke(app, ["assess", "maturity", "refresh", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert "Project definition maturity refreshed" in result.output
    assert "software_constraints_nfr_coverage  missing  0/100" in result.output
    assert "implementation completeness" not in result.output
    assert (tmp_path / ".p2p" / "project" / "maturity-assessment.yml").exists()

    result = runner.invoke(app, ["assess", "maturity", "show", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert "Project definition maturity" in result.output


def test_cli_context_returns_compact_packet(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Draft Work", "--root", str(tmp_path)])
    runner.invoke(app, ["registry", "refresh", "--root", str(tmp_path)])

    result = runner.invoke(app, ["context", "--budget", "small", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert "P2P compact context" in result.output
    assert "budget: small" in result.output
    assert "Do not scan all .p2p/" in result.output
    assert "p2p proposal show PROP-001" in result.output


def test_cli_context_target_limits_artifact_details(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "Draft Work",
            "--problem",
            "This is a long problem statement that should not be printed in small budget context.",
            "--proposal",
            "This is a long proposal body that should not be printed in small budget context.",
            "--root",
            str(tmp_path),
        ],
    )

    result = runner.invoke(
        app,
        ["context", "--target", "PROP-001", "--budget", "small", "--root", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert "target: PROP-001" in result.output
    assert "p2p proposal show PROP-001" in result.output
    assert "long problem statement" not in result.output
    assert "Nearby decision context:" in result.output
    assert "none: no_relevant_context" in result.output

    result = runner.invoke(
        app,
        [
            "context",
            "--target",
            "PROP-001",
            "--budget",
            "medium",
            "--format",
            "yaml",
            "--root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    payload = yaml.safe_load(result.output)
    assert payload["target"] == "PROP-001"
    assert payload["relevant_artifacts"][0]["problem"].startswith("This is a long problem")
    assert payload["nearby_context"]["schema_version"] == "decision-context-v1"
    assert payload["nearby_context"]["budget"] == "medium"
    assert payload["nearby_context"]["empty_reason"] == "no_relevant_context"
    assert payload["nearby_context"]["diagnostics"][0]["code"] == "DC-RETRIEVAL-EMPTY"

    result = runner.invoke(
        app,
        [
            "context",
            "--target",
            "PROP-001",
            "--budget",
            "small",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    json_payload = cli_data(result)
    assert json_payload["nearby_context"]["budget"] == "small"
    assert json_payload["nearby_context"]["schema_version"] == "decision-context-v1"


def test_cli_init_without_name_runs_guided_wizard(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["init", "--root", str(tmp_path)],
        input="Wizard Project\ncodex\nsoftware\ngeneric\nn\ny\n",
    )

    assert result.exit_code == 0
    assert "P2P project initialization" in result.output
    assert "P2P workspace initialized" in result.output
    assert "MCP setup hint" in result.output
    assert "codex mcp add" in result.output
    assert "Domain key (optional)" in result.output
    assert "Structure starter" in result.output
    assert "Customize rubric criteria" in result.output
    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / ".agents" / "skills" / "p2p-project" / "SKILL.md").exists()
    _assert_codex_curator_skill(tmp_path)


def test_cli_init_guided_wizard_uses_detected_agent_as_default(
    tmp_path: Path,
) -> None:
    result = runner.invoke(
        app,
        ["init", "--root", str(tmp_path)],
        input="Wizard Project\n\n\nempty\nn\n",
        env={"P2P_CURRENT_AGENT": "codex"},
    )

    assert result.exit_code == 0
    assert "Detected current client: codex" in result.output
    assert "Installed adapters: generic, codex" in result.output
    assert (tmp_path / ".agents" / "skills" / "p2p-project" / "SKILL.md").exists()
    _assert_codex_curator_skill(tmp_path)
    assert not (tmp_path / "CLAUDE.md").exists()


def test_cli_init_guided_wizard_keeps_all_available_with_footprint_warning(
    tmp_path: Path,
) -> None:
    result = runner.invoke(
        app,
        ["init", "--root", str(tmp_path)],
        input="Wizard Project\nall\n\nempty\nn\n",
        env={"P2P_CURRENT_AGENT": "codex"},
    )

    assert result.exit_code == 0
    assert "all installs every built-in adapter integration" in result.output
    assert "Installed adapters: generic, codex, claude, cursor, copilot, gemini, opencode" in result.output
    assert (tmp_path / "CLAUDE.md").exists()
    _assert_codex_curator_skill(tmp_path)


def test_cli_init_mcp_hint_uses_root_aware_running_runtime_command(tmp_path: Path) -> None:
    root = tmp_path / "Project With Spaces & Symbols"
    result = runner.invoke(app, ["init", "Demo Project", "--mcp-hint", "--root", str(root)])

    assert result.exit_code == 0
    assert "MCP setup" in result.output
    assert "governed P2P decision root" in result.output
    assert "codex mcp add" in result.output
    assert "invocation" not in result.output
    assert "p2p_engine.mcp.server" in result.output
    assert "No existing project-local" in result.output
    assert "Project With" in result.output
    assert "Spaces" in result.output
    assert "Symbols" in result.output


def test_cli_init_guided_wizard_can_disable_rubric_criteria(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["init", "--root", str(tmp_path)],
        input=(
            "Wizard Project\n"
            "generic\n"
            "\n"
            "generic\n"
            "y\n"
            "y\n"
            "n\n"
            "y\n"
            "y\n"
            "y\n"
            "n\n"
            "n\n"
        ),
    )

    assert result.exit_code == 0
    rubrics = yaml.safe_load(
        (tmp_path / ".p2p" / "project" / "rubrics.yml").read_text(encoding="utf-8")
    )
    criteria = {item["id"]: item["enabled"] for item in rubrics["criteria"]}
    assert criteria["vision_clarity"] is True
    assert criteria["objective_clarity"] is False
    assert criteria["stakeholder_alignment"] is True
    project = (tmp_path / ".p2p" / "project.yml").read_text(encoding="utf-8")
    assert "name: Wizard Project" in project


def test_cli_init_can_generate_agent_specific_instructions(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "init",
            "Demo Project",
            "--agent",
            "codex",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / ".agents" / "skills" / "p2p-project" / "SKILL.md").exists()
    _assert_codex_curator_skill(tmp_path)

    policy = (tmp_path / ".p2p" / "agent-policy.yml").read_text(encoding="utf-8")
    assert "missing_primitive_behavior: stop_and_report" in policy
    assert "runtime_bootstrap:" in policy
    assert "python -m p2p_engine" in policy
    assert "direct_p2p_file_edits: forbidden" in policy
    assert "read_before_explaining: true" in policy


def test_cli_init_without_detection_falls_back_to_all_agent_integrations(tmp_path: Path) -> None:
    result = runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert "Could not reliably detect the current agent" in result.output
    assert "Installed adapters: generic, codex, claude, cursor, copilot, gemini, opencode" in result.output
    assert "p2p agent uninstall <adapter>" in result.output
    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / ".agents" / "skills" / "p2p-project" / "SKILL.md").exists()
    _assert_codex_curator_skill(tmp_path)
    assert (tmp_path / "CLAUDE.md").exists()
    assert (tmp_path / ".cursor" / "rules" / "p2p.mdc").exists()
    assert (tmp_path / ".github" / "copilot-instructions.md").exists()
    assert (tmp_path / "GEMINI.md").exists()
    assert not (tmp_path / ".cursorrules").exists()
    assert not (tmp_path / "opencode.json").exists()
    assert (tmp_path / ".agents" / "skills" / "p2p-project" / "SKILL.md").read_text(
        encoding="utf-8"
    ).startswith("---\n")
    assert (tmp_path / ".cursor" / "rules" / "p2p.mdc").read_text(encoding="utf-8").startswith(
        "---\n"
    )

    registry = yaml.safe_load((tmp_path / ".p2p" / "agent-integrations.yml").read_text(encoding="utf-8"))
    assert registry["schema_version"] == 2
    assert registry["baseline_profile"] == "generic"
    assert set(registry["adapters"]) == {
        "generic",
        "codex",
        "claude",
        "cursor",
        "copilot",
        "gemini",
        "opencode",
    }
    agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "do not stop at diagnosis" in agents


def test_cli_init_with_detected_agent_installs_generic_plus_detected_adapter(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["init", "Demo Project", "--root", str(tmp_path)],
        env={"P2P_CURRENT_AGENT": "codex"},
    )

    assert result.exit_code == 0
    assert "Detected current client: codex" in result.output
    assert "Installed adapters: generic, codex" in result.output
    assert "This does not make codex the project identity" in result.output
    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / ".agents" / "skills" / "p2p-project" / "SKILL.md").exists()
    _assert_codex_curator_skill(tmp_path)
    assert not (tmp_path / "CLAUDE.md").exists()
    registry = yaml.safe_load((tmp_path / ".p2p" / "agent-integrations.yml").read_text(encoding="utf-8"))
    assert set(registry["adapters"]) == {"generic", "codex"}


def test_cli_init_narrow_agent_still_includes_generic(tmp_path: Path) -> None:
    result = runner.invoke(app, ["init", "Demo Project", "--agent", "cursor", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / ".cursor" / "rules" / "p2p.mdc").exists()
    assert not (tmp_path / ".agents" / "skills" / "p2p-project-curator" / "SKILL.md").exists()
    assert not (tmp_path / ".codex" / "skills" / "p2p-project-curator" / "SKILL.md").exists()
    assert not (tmp_path / "CLAUDE.md").exists()
    registry = yaml.safe_load((tmp_path / ".p2p" / "agent-integrations.yml").read_text(encoding="utf-8"))
    assert set(registry["adapters"]) == {"generic", "cursor"}


def test_cli_agent_uninstall_refuses_generic_baseline(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--agent", "cursor", "--root", str(tmp_path)])

    result = runner.invoke(app, ["agent", "uninstall", "generic", "--root", str(tmp_path)])

    assert result.exit_code == 1
    assert "generic cannot be uninstalled" in result.output
    registry = yaml.safe_load((tmp_path / ".p2p" / "agent-integrations.yml").read_text(encoding="utf-8"))
    assert "generic" in registry["adapters"]


def test_cli_agent_lifecycle_update_refuses_drift_and_uninstall_preserves_shared(
    tmp_path: Path,
) -> None:
    runner.invoke(app, ["init", "Demo Project", "--agent", "cursor", "--root", str(tmp_path)])
    cursor_rule = tmp_path / ".cursor" / "rules" / "p2p.mdc"
    cursor_rule.write_text(cursor_rule.read_text(encoding="utf-8") + "\nmanual edit\n", encoding="utf-8")

    update = runner.invoke(app, ["agent", "update", "cursor", "--root", str(tmp_path)])

    assert update.exit_code == 0
    assert "drifted" in update.output
    assert "manual edit" in cursor_rule.read_text(encoding="utf-8")

    uninstall = runner.invoke(app, ["agent", "uninstall", "cursor", "--root", str(tmp_path)])

    assert uninstall.exit_code == 0
    assert "drifted" in uninstall.output
    assert cursor_rule.exists()
    assert (tmp_path / "AGENTS.md").exists()

    forced = runner.invoke(app, ["agent", "update", "cursor", "--force", "--root", str(tmp_path)])
    assert forced.exit_code == 0
    clean_uninstall = runner.invoke(app, ["agent", "uninstall", "cursor", "--root", str(tmp_path)])
    assert clean_uninstall.exit_code == 0
    assert not cursor_rule.exists()
    assert (tmp_path / "AGENTS.md").exists()


def test_cli_agent_update_force_is_scoped_to_target_adapter(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    cursor_rule = tmp_path / ".cursor" / "rules" / "p2p.mdc"
    gemini = tmp_path / "GEMINI.md"
    cursor_rule.write_text(cursor_rule.read_text(encoding="utf-8") + "\ncursor edit\n", encoding="utf-8")
    gemini.write_text(gemini.read_text(encoding="utf-8") + "\ngemini edit\n", encoding="utf-8")

    result = runner.invoke(app, ["agent", "update", "cursor", "--force", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert ".cursor/rules/p2p.mdc" in result.output
    assert "GEMINI.md" not in result.output
    assert "cursor edit" not in cursor_rule.read_text(encoding="utf-8")
    assert "gemini edit" in gemini.read_text(encoding="utf-8")


def test_cli_agent_install_does_not_claim_unmanaged_existing_file(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--agent", "generic", "--root", str(tmp_path)])
    (tmp_path / ".p2p" / "agent-integrations.yml").unlink()
    agents = tmp_path / "AGENTS.md"
    agents.write_text("# Custom Agents\n", encoding="utf-8")

    result = runner.invoke(app, ["agent", "install", "cursor", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert "unmanaged_exists" in result.output
    registry = yaml.safe_load((tmp_path / ".p2p" / "agent-integrations.yml").read_text(encoding="utf-8"))
    generic_agents = registry["adapters"]["generic"]["files"][0]
    assert generic_agents["path"] == "AGENTS.md"
    assert generic_agents["managed"] is False
    assert generic_agents["drift"] == "unmanaged"


def test_cli_agent_instructions_refresh_reports_skipped_drift(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--agent", "generic", "--root", str(tmp_path)])
    agents = tmp_path / "AGENTS.md"
    agents.write_text(agents.read_text(encoding="utf-8") + "\nmanual edit\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["agent", "instructions", "refresh", "--profile", "claude", "--root", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert "skipped:" in result.output
    assert "AGENTS.md: drifted" in result.output
    assert "manual edit" in agents.read_text(encoding="utf-8")


def test_cli_agent_show_and_list_report_adapter_health(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--agent", "generic", "--root", str(tmp_path)])
    (tmp_path / "AGENTS.md").unlink()

    shown = runner.invoke(app, ["agent", "show", "generic", "--root", str(tmp_path)])
    listed = runner.invoke(app, ["agent", "list", "--root", str(tmp_path)])

    assert shown.exit_code == 0
    assert listed.exit_code == 0
    assert "health: error" in shown.output
    assert "AGENTS.md shared=true owner=generic status=missing" in shown.output
    assert "content=missing" in shown.output
    assert "generation=current" in shown.output
    assert "generic: installed=true health=error drift=drifted" in listed.output


def test_cli_doctor_reports_runtime_readiness(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])

    result = runner.invoke(app, ["doctor", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert "P2P doctor" in result.output
    assert "project: true" in result.output
    assert "package_importable: true" in result.output
    assert "running_runtime_importable: true" in result.output
    assert "python_module_cli:" in result.output
    assert "mcp_server_importable: true" in result.output
    assert "discovery_order: p2p on PATH -> running P2P runtime" in result.output
    assert "suggested_start:" in result.output


def test_cli_agent_doctor_reports_missing_primitive_recovery(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])

    result = runner.invoke(app, ["agent", "doctor", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert "missing_primitive_rule:" in result.output
    assert "stop and report these diagnostics instead of editing .p2p by hand" in result.output
    assert "Agent integration doctor" in result.output
    assert "health: clean" in result.output


def test_cli_agent_doctor_reports_agent_findings_and_error_exit(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--agent", "generic", "--root", str(tmp_path)])
    (tmp_path / "AGENTS.md").unlink()

    result = runner.invoke(app, ["agent", "doctor", "generic", "--root", str(tmp_path)])

    assert result.exit_code == 1
    assert "Agent integration doctor" in result.output
    assert "target: generic" in result.output
    assert "health: error" in result.output
    assert "P2P_AGENT_FILE_MISSING" in result.output
    assert "AGENTS.md" in result.output


def test_python_module_entrypoint_exposes_cli_help() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "p2p_engine", "--help"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "P2P Engine CLI" in result.stdout
    assert "doctor" in result.stdout


def test_cli_agent_instructions_refresh_adds_profiles_without_removing_existing(
    tmp_path: Path,
) -> None:
    runner.invoke(app, ["init", "Demo Project", "--agent", "codex", "--root", str(tmp_path)])

    result = runner.invoke(
        app,
        ["agent", "instructions", "refresh", "--profile", "claude", "--root", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert "Agent instructions refreshed" in result.output
    assert (tmp_path / ".agents" / "skills" / "p2p-project" / "SKILL.md").exists()
    _assert_codex_curator_skill(tmp_path)
    assert (tmp_path / "CLAUDE.md").exists()

    policy = (tmp_path / ".p2p" / "agent-policy.yml").read_text(encoding="utf-8")
    assert "- claude" in policy
    assert "- codex" in policy
    assert "write_decision_files_directly: false" in policy
    assert "write_policy:" in policy
    assert "placement_policy:" in policy
    assert "agent_must_not_invent_durable_output_paths: true" in policy


def test_cli_import_exploration_file_and_record_decision(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Decision Flow", "--root", str(tmp_path)])

    source = tmp_path / "exploration-output.md"
    source.write_text("# Exploration\n\nConcrete exploration output.\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["explore", "import", "PROP-001", str(source), "--root", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert "Exploration imported" in result.output
    ensure_global_scope(P2PWorkspace(tmp_path), "PROP-001")

    preview_result = runner.invoke(
        app,
        [
            "decision",
            "record",
            "PROP-001",
            "--outcome",
            "accepted",
            "--reason",
            "Scope is clear enough.",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )
    assert preview_result.exit_code == 0
    preview = cli_data(preview_result)
    assert preview["status"] == "preview_required"

    request = preview["request"]
    result = runner.invoke(
        app,
        [
            "decision",
            "record",
            "PROP-001",
            "--outcome",
            "accepted",
            "--reason",
            "Scope is clear enough.",
            "--decided-on",
            request["decided_on"],
            "--operation-key",
            request["operation_key"],
            "--preview-token",
            preview["preview"]["preview_token"],
            "--confirm",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert cli_data(result)["status"] == "applied"

    decision = (
        tmp_path / ".p2p" / "proposals" / "PROP-001-decision-flow" / "decision.md"
    ).read_text(encoding="utf-8")
    assert "Scope is clear enough." in decision


def test_cli_proposal_readiness_status_refresh_and_explain(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "Readiness Workflow",
            "--problem",
            "The proposal workflow needs a visible maturity signal before acceptance.",
            "--goal",
            "Expose a conservative readiness assessment.",
            "--acceptance",
            "Readiness commands show a computed score.",
            "--root",
            str(tmp_path),
        ],
    )

    result = runner.invoke(app, ["proposal", "readiness", "show", "PROP-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Proposal readiness for PROP-001" in result.output
    assert "status: not_assessed" in result.output
    assert "profile: none" in result.output

    result = runner.invoke(app, ["proposal", "readiness", "refresh", "PROP-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Proposal readiness refreshed" in result.output
    assert "status: not_assessed" in result.output
    assert "suggested_next: p2p proposal readiness init PROP-001" in result.output
    assert (tmp_path / ".p2p" / "proposals" / "PROP-001-readiness-workflow" / "readiness.yml").exists()

    result = runner.invoke(app, ["proposal", "readiness", "init", "PROP-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Proposal readiness initialized" in result.output
    assert "status: assessed" in result.output
    assert "computed_score:" in result.output

    result = runner.invoke(app, ["proposal", "readiness", "explain", "PROP-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "failed_gates:" in result.output
    assert "suggested_next:" in result.output


def test_cli_proposal_questions_lifecycle_and_refresh_guidance(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Question Flow", "--root", str(tmp_path)])

    result = runner.invoke(app, ["proposal", "questions", "status", "PROP-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "status: not_initialized" in result.output
    assert "suggested_next: p2p proposal questions init PROP-001" in result.output

    result = runner.invoke(app, ["proposal", "questions", "init", "PROP-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Proposal question state initialized" in result.output

    result = runner.invoke(
        app,
        [
            "proposal",
            "questions",
            "add",
            "PROP-001",
            "--gap",
            "alternatives_quality",
            "--priority",
            "high",
            "--question",
            "Which alternative should be compared first?",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert "Q001" in result.output
    assert "alternatives_quality" in result.output

    result = runner.invoke(app, ["proposal", "questions", "next", "PROP-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Which alternative should be compared first?" in result.output

    result = runner.invoke(
        app,
        [
            "proposal",
            "questions",
            "answer",
            "PROP-001",
            "Q001",
            "Use a first-class deterministic CLI object.",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert "Question answered" in result.output

    result = runner.invoke(app, ["proposal", "questions", "apply", "PROP-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Answered proposal questions applied to artifact update plan" in result.output
    assert "Artifact update plan" in result.output

    runner.invoke(
        app,
        [
            "proposal",
            "questions",
            "add",
            "PROP-001",
            "--gap",
            "risk_coverage",
            "--question",
            "Which risk matters most?",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(
        app,
        [
            "proposal",
            "questions",
            "add",
            "PROP-001",
            "--gap",
            "risk_coverage",
            "--question",
            "Which implementation risk matters most?",
            "--root",
            str(tmp_path),
        ],
    )
    assert runner.invoke(app, ["proposal", "questions", "defer", "PROP-001", "Q002", "--root", str(tmp_path)]).exit_code == 0
    assert runner.invoke(app, ["proposal", "questions", "reopen", "PROP-001", "Q002", "--root", str(tmp_path)]).exit_code == 0
    assert runner.invoke(app, ["proposal", "questions", "mute", "PROP-001", "Q002", "--root", str(tmp_path)]).exit_code == 0
    assert runner.invoke(app, ["proposal", "questions", "retire", "PROP-001", "Q003", "--root", str(tmp_path)]).exit_code == 0
    assert runner.invoke(app, ["proposal", "questions", "supersede", "PROP-001", "Q002", "Q003", "--root", str(tmp_path)]).exit_code == 0
    assert runner.invoke(app, ["proposal", "questions", "group-status", "PROP-001", "QG002", "--state", "muted", "--root", str(tmp_path)]).exit_code == 0
    questions_path = tmp_path / ".p2p" / "proposals" / "PROP-001-question-flow" / "questions.yml"
    assert runner.invoke(app, ["proposal", "questions", "import", "PROP-001", str(questions_path), "--root", str(tmp_path)]).exit_code == 0

    result = runner.invoke(app, ["proposal", "readiness", "init", "PROP-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    result = runner.invoke(app, ["proposal", "readiness", "refresh", "PROP-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "guidance: refresh is conservative" in result.output

    result = runner.invoke(app, ["proposal", "readiness", "review", "PROP-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Proposal readiness review for PROP-001" in result.output
    assert "question_state: initialized" in result.output
    assert "assertiveness_guidance:" in result.output
    assert "acceptance_cautions:" in result.output

    result = runner.invoke(app, ["proposal", "readiness", "assess", "PROP-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Proposal readiness assessed" in result.output


def test_cli_readiness_assess_reports_structured_question_state(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Structured Question State", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "questions", "init", "PROP-001", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "questions",
            "add",
            "PROP-001",
            "--gap",
            "owner_questions_resolution",
            "--priority",
            "high",
            "--question",
            "Should structured question state be authoritative?",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(
        app,
        [
            "proposal",
            "questions",
            "answer",
            "PROP-001",
            "Q001",
            "Yes, structured question state is authoritative.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(app, ["proposal", "questions", "apply", "PROP-001", "--root", str(tmp_path)])
    proposal_dir = tmp_path / ".p2p" / "proposals" / "PROP-001-structured-question-state"
    (proposal_dir / "open-questions.md").write_text(
        "# Open Questions\n\n- Should stale markdown reopen an applied structured question?\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["proposal", "readiness", "assess", "PROP-001", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert "owner_question_state:" in result.output
    assert "source: structured" in result.output
    assert "closed_questions:" in result.output
    assert "Q001" in result.output
    assert "owner_questions_resolution:needs_owner_input" not in result.output


def test_cli_lists_proposal_contributions(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Contribution Visibility", "--root", str(tmp_path)])

    add_result = runner.invoke(
        app,
        [
            "proposal",
            "contribution",
            "add",
            "PROP-001",
            "Add a concise MVP boundary before accepting.",
            "--type",
            "suggestion",
            "--relevance",
            "readiness",
            "--author",
            "codex",
            "--root",
            str(tmp_path),
        ],
    )
    assert add_result.exit_code == 0

    result = runner.invoke(app, ["proposal", "contributions", "PROP-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Proposal contributions for PROP-001" in result.output
    assert "C001  suggestion  codex" in result.output
    assert "Add a concise MVP boundary before accepting." in result.output


def test_cli_accepts_canonical_contribution_types_and_reports_allowed_invalid_type(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Contribution Contract", "--root", str(tmp_path)])

    for contribution_type in (
        "finding",
        "open_question",
        "alternative",
        "risk",
        "assumption",
        "constraint",
        "objection",
        "implementation_suggestion",
        "scope_boundary",
    ):
        result = runner.invoke(
            app,
            [
                "proposal",
                "contribution",
                "add",
                "PROP-001",
                f"{contribution_type} content.",
                "--type",
                contribution_type,
                "--root",
                str(tmp_path),
            ],
        )

        assert result.exit_code == 0

    invalid = runner.invoke(
        app,
        [
            "proposal",
            "contribution",
            "add",
            "PROP-001",
            "Unsupported content.",
            "--type",
            "unsupported",
            "--root",
            str(tmp_path),
        ],
    )
    contributions = (
        tmp_path / ".p2p" / "proposals" / "PROP-001-contribution-contract" / "contributions.yml"
    ).read_text(encoding="utf-8")

    assert "type: finding" in contributions
    assert "type: open_question" in contributions
    assert "type: scope_boundary" in contributions
    assert invalid.exit_code == 1
    assert "Invalid contribution type: unsupported" in invalid.output
    assert "Allowed:" in invalid.output
    assert "finding" in invalid.output


def test_cli_proposal_accept_can_record_readiness_override(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Override Readiness", "--root", str(tmp_path)])
    readiness_path = (
        tmp_path
        / ".p2p"
        / "proposals"
        / "PROP-001-override-readiness"
        / "readiness.yml"
    )
    ensure_global_scope(P2PWorkspace(tmp_path), "PROP-001")

    preview = runner.invoke(
        app,
        [
            "proposal",
            "accept",
            "PROP-001",
            "--reason",
            "Owner accepts this intentionally as-is.",
            "--approver",
            "owner",
            "--override-readiness",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )
    assert preview.exit_code == 0, preview.output
    assert cli_data(preview)["status"] == "preview_required"
    assert not readiness_path.exists()

    result = _apply_proposal_decision(
        tmp_path,
        "PROP-001",
        reason="Owner accepts this intentionally as-is.",
        override_readiness=True,
    )
    readiness = yaml.safe_load(readiness_path.read_text(encoding="utf-8"))["readiness"]

    assert cli_data(result)["status"] == "applied"
    assert readiness["status"] == "not_assessed"
    assert readiness["owner_override"] is True
    assert readiness["effective_status"] == "forced_ready"
    assert readiness["effective_score"] == 100
    assert readiness["override_reason"] == "Owner accepts this intentionally as-is."
    assert readiness["override_approver"] == "owner"


def test_cli_proposal_decision_shortcuts(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Acceptable Work", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Rejected Work", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Deferred Work", "--root", str(tmp_path)])

    cases = (
        ("accepted", "PROP-001", "Ready for implementation."),
        ("rejected", "PROP-002", "Out of scope."),
        ("deferred", "PROP-003", "Needs more context."),
    )
    for outcome, proposal_id, reason in cases:
        ensure_global_scope(P2PWorkspace(tmp_path), proposal_id)
        command = {
            "accepted": "accept",
            "rejected": "reject",
            "deferred": "defer",
        }[outcome]
        preview = runner.invoke(
            app,
            [
                "proposal",
                command,
                proposal_id,
                "--reason",
                reason,
                "--format",
                "json",
                "--root",
                str(tmp_path),
            ],
        )
        assert preview.exit_code == 0, preview.output
        assert cli_data(preview)["status"] == "preview_required"

        applied = _apply_proposal_decision(
            tmp_path,
            proposal_id,
            outcome=outcome,
            reason=reason,
        )
        payload = cli_data(applied)
        assert payload["status"] == "applied"
        assert payload["lifecycle"]["effective_state"] == outcome

    result = runner.invoke(app, ["status", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "PROP-001  PROP-001-acceptable-work  accepted" in result.output
    assert "PROP-002  PROP-002-rejected-work  rejected" in result.output
    assert "PROP-003  PROP-003-deferred-work  deferred" in result.output

    decision = (
        tmp_path / ".p2p" / "proposals" / "PROP-001-acceptable-work" / "decision.md"
    ).read_text(encoding="utf-8")
    assert "Ready for implementation." in decision
    assert "owner" in decision


def test_cli_proposal_list_show_and_choice_registry_output(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "CLI Inspection",
            "--problem",
            "Agents need stable proposal inspection.",
            "--proposal",
            "Add proposal list and show commands.",
            "--root",
            str(tmp_path),
        ],
    )
    _apply_proposal_decision(
        tmp_path,
        "PROP-001",
        reason="Useful for agent skills.",
    )

    result = runner.invoke(app, ["proposal", "list", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "PROP-001  accepted  CLI Inspection" in result.output

    result = runner.invoke(app, ["proposal", "list", "--status", "draft", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "PROP-001" not in result.output

    result = runner.invoke(app, ["proposal", "show", "PROP-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "PROP-001 - CLI Inspection" in result.output
    assert "Agents need stable proposal inspection." in result.output
    assert "Add proposal list and show commands." in result.output
    assert "Useful for agent skills." in result.output
    assert "Artifact Status:" not in result.output

    result = runner.invoke(app, ["proposal", "show", "PROP-001", "--full", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Full proposal view for PROP-001" in result.output
    assert "Proposal Body:" in result.output
    assert "Readiness:" in result.output
    assert "Structured Contributions:" in result.output
    assert "Narrative And Imported Artifacts:" in result.output
    assert "Artifact Status:" in result.output
    assert "Grouped Questions:" in result.output
    assert "(evidence)" in result.output

    runner.invoke(
        app,
        [
            "choice",
            "create",
            "--title",
            "Inspection Strategy",
            "--problem",
            "Choose the inspection strategy.",
            "--context",
            "The CLI inspection test needs a complete Choice.",
            "--option",
            "A",
            "--option",
            "B",
            "--root",
            str(tmp_path),
        ],
    )
    preview = runner.invoke(
        app,
        [
            "choice",
            "decide",
            "CHOICE-001",
            "--option",
            "A",
            "--reason",
            "Pick A.",
            "--operation-key",
            "cli-inspection-choice-001",
            "--root",
            str(tmp_path),
        ],
    )
    token = re.search(r"preview token:\s*((?:[0-9a-f]\s*){64})", preview.output)
    assert token is not None
    preview_token = "".join(token.group(1).split())
    applied = runner.invoke(
        app,
        [
            "choice",
            "decide",
            "CHOICE-001",
            "--option",
            "A",
            "--reason",
            "Pick A.",
            "--operation-key",
            "cli-inspection-choice-001",
            "--preview-token",
            preview_token,
            "--confirm",
            "--root",
            str(tmp_path),
        ],
    )
    assert applied.exit_code == 0
    runner.invoke(app, ["registry", "refresh", "--root", str(tmp_path)])
    result = runner.invoke(app, ["registry", "show", "choices", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "CHOICE-001: decided  Inspection Strategy -> A - A" in result.output
    assert "{" not in result.output


def test_cli_missing_proposal_returns_clean_error(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])

    result = runner.invoke(app, ["digest", "prompt", "PROP-999", "--root", str(tmp_path)])

    assert result.exit_code == 1
    assert "Error: Proposal not found: PROP-999" in result.output
    assert "Traceback" not in result.output


def test_cli_prompt_only_import_workflow_to_tasks(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Import Workflow", "--root", str(tmp_path)])

    clarify_source = tmp_path / "clarification-output.md"
    clarify_source.write_text("# Clarifications\n\nQ1 answered.\n", encoding="utf-8")
    result = runner.invoke(
        app,
        ["clarify", "import", "PROP-001", str(clarify_source), "--root", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert "clarifications.md" in result.output

    result = runner.invoke(app, ["synthesize", "prompt", "PROP-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "synthesize.prompt.md" in result.output

    proposal_source = tmp_path / "proposal-output.md"
    proposal_source.write_text("# PROP-001 - Import Workflow\n\n## Status\n\n`ready_for_review`\n", encoding="utf-8")
    result = runner.invoke(
        app,
        ["synthesize", "import", "PROP-001", str(proposal_source), "--root", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert "proposal.md" in result.output

    plan_source = tmp_path / "plan-output.md"
    plan_source.write_text("# Execution Plan\n\nImplement imports.\n", encoding="utf-8")
    result = runner.invoke(
        app,
        ["plan", "import", "PROP-001", str(plan_source), "--root", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert "execution-plan.md" in result.output

    tasks_source = tmp_path / "tasks-output.yml"
    tasks_source.write_text(
        "tasks:\n"
        "  - id: T001\n"
        "    title: Implement imports\n"
        "    workstream: WS1\n"
        "    type: software\n"
        "    status: todo\n"
        "    priority: high\n"
        "    dependencies: []\n"
        "    deliverable: CLI commands\n"
        "    evidence_required: Tests pass\n"
        "    actions: []\n",
        encoding="utf-8",
    )
    result = runner.invoke(
        app,
        ["tasks", "import", "PROP-001", str(tasks_source), "--root", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert "tasks.yml" in result.output

    proposal_dir = tmp_path / ".p2p" / "proposals" / "PROP-001-import-workflow"
    assert "Q1 answered." in (proposal_dir / "clarifications.md").read_text(encoding="utf-8")
    assert "ready_for_review" in (proposal_dir / "proposal.md").read_text(encoding="utf-8")
    assert "Implement imports." in (proposal_dir / "execution-plan.md").read_text(encoding="utf-8")
    assert "Implement imports" in (proposal_dir / "tasks.yml").read_text(encoding="utf-8")


def test_cli_tasks_import_rejects_invalid_yaml_shape(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Import Workflow", "--root", str(tmp_path)])
    source = tmp_path / "bad-tasks.yml"
    source.write_text("not_tasks: []\n", encoding="utf-8")

    result = runner.invoke(app, ["tasks", "import", "PROP-001", str(source), "--root", str(tmp_path)])

    assert result.exit_code == 1
    assert "expected top-level `tasks` list" in result.output


def test_cli_governance_swot_vote_and_precedent_flow(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Governance Model", "--root", str(tmp_path)])

    result = runner.invoke(
        app,
        ["governance", "init", "--mode", "exclusive_vote", "--root", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert "Governance initialized" in result.output

    result = runner.invoke(app, ["governance", "status", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "mode: exclusive_vote" in result.output

    result = runner.invoke(app, ["swot", "prompt", "PROP-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "swot.prompt.md" in result.output
    swot_prompt = (tmp_path / ".p2p" / "prompts" / "PROP-001" / "swot.prompt.md").read_text(
        encoding="utf-8"
    )
    assert "P2P SWOT Prompt" in swot_prompt
    assert "exclusive_vote" in swot_prompt

    result = runner.invoke(
        app,
        [
            "vote",
            "record",
            "PROP-001",
            "--choice",
            "ALT-A",
            "--reason",
            "Keeps governance simple.",
            "--voter",
            "davide",
            "--role",
            "owner",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert "Vote recorded" in result.output
    assert "current winner: ALT-A" in result.output

    result = runner.invoke(app, ["vote", "status", "PROP-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "ALT-A: 1" in result.output

    result = runner.invoke(
        app,
        [
            "precedent",
            "record",
            "PROP-001",
            "--title",
            "Governance is audit-only in MVP",
            "--reason",
            "Privileges are delegated to the external delivery system.",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert "Precedent recorded" in result.output

    precedents = (
        tmp_path / ".p2p" / "governance" / "decision-precedents.yml"
    ).read_text(encoding="utf-8")
    assert "Governance is audit-only in MVP" in precedents


def test_cli_project_refresh_status_and_show(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "CLI Foundation",
            "--problem",
            "The project needs a first CLI.",
            "--goal",
            "Create p2p init.",
            "--proposal",
            "Build a project-state CLI foundation.",
            "--root",
            str(tmp_path),
        ],
    )
    _apply_proposal_decision(
        tmp_path,
        "PROP-001",
        reason="Required for bootstrap.",
    )

    result = runner.invoke(app, ["project", "refresh", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Project state refreshed" in result.output
    assert ".p2p/project/overview.md" in result.output
    assert ".p2p/project/features/cli-foundation/feature.md" in result.output

    result = runner.invoke(app, ["project", "status", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "accepted proposals: 1" in result.output
    assert "cli-foundation" in result.output

    result = runner.invoke(app, ["project", "show", "cli-foundation", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "CLI Foundation" in result.output
    assert "PROP-001" in result.output
    assert "Required for bootstrap." in result.output

    decisions_map = (tmp_path / ".p2p" / "project" / "decisions-map.yml").read_text(
        encoding="utf-8"
    )
    assert "proposal: PROP-001" in decisions_map


def test_cli_impact_import_and_conflict_memory(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Project State", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Alternative State", "--root", str(tmp_path)])
    _apply_proposal_decision(
        tmp_path,
        "PROP-001",
        reason="Chosen baseline.",
    )
    runner.invoke(app, ["project", "refresh", "--root", str(tmp_path)])

    result = runner.invoke(app, ["impact", "prompt", "PROP-002", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "impact.prompt.md" in result.output
    prompt = (tmp_path / ".p2p" / "prompts" / "PROP-002" / "impact.prompt.md").read_text(
        encoding="utf-8"
    )
    assert "P2P Impact Prompt" in prompt
    assert "Existing Project Decisions" in prompt

    source_dir = tmp_path / "impact-output"
    source_dir.mkdir()
    (source_dir / "impact-map.yml").write_text(
        "impact:\n"
        "  proposal: PROP-002\n"
        "  features:\n"
        "    - project-state\n",
        encoding="utf-8",
    )
    (source_dir / "related-proposals.yml").write_text(
        "related_proposals:\n"
        "  - proposal: PROP-001\n"
        "    relationship: conflicts_with\n",
        encoding="utf-8",
    )
    (source_dir / "conflict-analysis.yml").write_text(
        "conflicts:\n"
        "  - type: mutually_exclusive\n"
        "    proposals:\n"
        "      - PROP-001\n"
        "      - PROP-002\n",
        encoding="utf-8",
    )
    result = runner.invoke(
        app,
        ["impact", "import", "PROP-002", str(source_dir), "--root", str(tmp_path)],
    )
    assert result.exit_code == 0, result.output
    assert "impact-map.yml" in result.output
    proposal_dir = tmp_path / ".p2p" / "proposals" / "PROP-002-alternative-state"
    assert (proposal_dir / "impact-map.yml").exists()

    result = runner.invoke(
        app,
        [
            "conflict",
            "record",
            "PROP-001",
            "PROP-002",
            "--type",
            "mutually_exclusive",
            "--reason",
            "Two alternative project-state models.",
            "--winner",
            "PROP-001",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert "Conflict recorded" in result.output

    result = runner.invoke(app, ["conflict", "status", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "CONFLICT-001" in result.output
    assert "PROP-001, PROP-002" in result.output

    runner.invoke(app, ["project", "refresh", "--root", str(tmp_path)])
    conflicts = (tmp_path / ".p2p" / "project" / "conflicts.yml").read_text(encoding="utf-8")
    assert "CONFLICT-001" in conflicts


def test_cli_change_create_and_status(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Draft Work", "--root", str(tmp_path)])

    result = runner.invoke(
        app,
        ["change", "create", "--from", "PROP-001", "--root", str(tmp_path)],
    )
    assert result.exit_code == 1
    assert "PROP-001 has no current active decision" in result.output
    assert "Current state: undecided" in result.output

    _apply_proposal_decision(
        tmp_path,
        "PROP-001",
        reason="Ready for operational work.",
    )

    result = runner.invoke(
        app,
        ["change", "create", "--from", "PROP-001", "--root", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert "Change Set created" in result.output
    assert "id: CHANGE-001" in result.output

    change_dir = tmp_path / ".p2p" / "changes" / "CHANGE-001-draft-work"
    assert (change_dir / "change.md").exists()
    change_text = (change_dir / "change.md").read_text(encoding="utf-8")
    assert "implementation_targets:" in change_text
    assert "- local_cli" in change_text
    assert "spec_targets:" in change_text
    assert "- p2p_spec" in change_text
    assert "export_targets:" in change_text
    assert "- openspec" in change_text
    assert "- speckit" in change_text
    result = runner.invoke(app, ["change", "status", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "CHANGE-001" in result.output
    assert "proposed" in result.output

def test_cli_change_lifecycle_show_and_tasks(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Lifecycle Work", "--root", str(tmp_path)])
    _apply_proposal_decision(
        tmp_path,
        "PROP-001",
        reason="Ready for lifecycle tracking.",
    )
    runner.invoke(app, ["change", "create", "--from", "PROP-001", "--root", str(tmp_path)])

    result = runner.invoke(
        app,
        ["change", "set-status", "CHANGE-001", "completed", "--root", str(tmp_path)],
    )
    assert result.exit_code == 1
    assert "Invalid Change Set transition" in result.output

    for status in ("planned", "implementation_ready", "in_progress", "in_review", "completed"):
        result = runner.invoke(
            app,
            ["change", "set-status", "CHANGE-001", status, "--root", str(tmp_path)],
        )
        assert result.exit_code == 0
        assert f"status: {status}" in result.output

    result = runner.invoke(app, ["change", "show", "CHANGE-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "CHANGE-001" in result.output
    assert "completed" in result.output
    assert "execution_domains: software" in result.output
    assert "implementation_targets: local_cli" in result.output
    assert "spec_targets: p2p_spec" in result.output
    assert "export_targets: openspec, speckit" in result.output

    change_dir = tmp_path / ".p2p" / "changes" / "CHANGE-001-lifecycle-work"
    (change_dir / "actions.yml").write_text(
        "actions:\n"
        "  - id: A001\n"
        "    title: Verify lifecycle output\n"
        "    checked: true\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["change", "tasks", "CHANGE-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Tasks for CHANGE-001" in result.output
    assert "[x] A001: Verify lifecycle output" in result.output


def test_cli_registry_refresh_status_and_show(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Project Registries", "--root", str(tmp_path)])
    _apply_proposal_decision(
        tmp_path,
        "PROP-001",
        reason="Needed for project navigation.",
    )
    runner.invoke(app, ["change", "create", "--from", "PROP-001", "--root", str(tmp_path)])

    result = runner.invoke(app, ["registry", "status", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "stale: True" in result.output

    result = runner.invoke(app, ["registry", "refresh", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Registries refreshed" in result.output
    assert ".p2p/registries/proposals.yml" in result.output
    assert ".p2p/registries/changes.yml" in result.output

    registries_dir = tmp_path / ".p2p" / "registries"
    assert (registries_dir / "proposals.yml").exists()
    assert (registries_dir / "changes.yml").exists()
    assert (registries_dir / "readiness.yml").exists()
    assert "generated: true" in (registries_dir / "proposals.yml").read_text(encoding="utf-8")
    assert "id: PROP-001" in (registries_dir / "proposals.yml").read_text(encoding="utf-8")
    readiness_registry = (registries_dir / "readiness.yml").read_text(encoding="utf-8")
    assert "proposal: PROP-001" in readiness_registry
    assert "status: not_assessed" in readiness_registry
    changes_registry = (registries_dir / "changes.yml").read_text(encoding="utf-8")
    assert "id: CHANGE-001" in changes_registry
    assert "spec_targets:" in changes_registry
    assert "- p2p_spec" in changes_registry
    assert "export_targets:" in changes_registry
    assert "- openspec" in changes_registry
    assert "- speckit" in changes_registry

    result = runner.invoke(app, ["registry", "status", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "stale: False" in result.output
    assert "proposals.yml (1 records)" in result.output
    assert "changes.yml (1 records)" in result.output
    assert "readiness.yml (1 records)" in result.output

    result = runner.invoke(app, ["registry", "show", "proposals", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Registry: proposals" in result.output
    assert "PROP-001: accepted  Project Registries" in result.output

    result = runner.invoke(app, ["registry", "show", "changes", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Registry: changes" in result.output
    assert "CHANGE-001: proposed  Project Registries" in result.output

    result = runner.invoke(app, ["registry", "show", "readiness", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Registry: readiness" in result.output
    assert "PROP-001: not_assessed  none none" in result.output


def test_cli_software_spec_refresh_prompt_import_status_and_show(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "Spec Work",
            "--problem",
            "Need implementation-facing specs.",
            "--proposal",
            "Generate a deterministic software spec.",
            "--acceptance",
            "Spec artifacts exist.",
            "--root",
            str(tmp_path),
        ],
    )
    _apply_proposal_decision(
        tmp_path,
        "PROP-001",
        reason="Needed before export.",
    )
    runner.invoke(app, ["change", "create", "--from", "PROP-001", "--root", str(tmp_path)])

    result = runner.invoke(app, ["spec", "refresh", "--change", "CHANGE-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Software spec refreshed" in result.output
    assert "lifecycle" not in result.output.lower()
    assert "advisories:" in result.output
    assert "software_vertical_not_active" in result.output
    assert ".p2p/outputs/software-spec/CHANGE-001" in result.output

    spec_dir = tmp_path / ".p2p" / "outputs" / "software-spec" / "CHANGE-001"
    for filename in (
        "index.md",
        "requirements.md",
        "design.md",
        "commands.yml",
        "data-model.yml",
        "acceptance.md",
        "provenance.yml",
    ):
        assert (spec_dir / filename).exists()
    assert "Spec Work" in (spec_dir / "index.md").read_text(encoding="utf-8")
    assert "Generate a deterministic software spec." in (spec_dir / "requirements.md").read_text(
        encoding="utf-8"
    )
    assert "source:" in (spec_dir / "provenance.yml").read_text(encoding="utf-8")

    with assert_no_workspace_mutation(tmp_path):
        result = runner.invoke(app, ["spec", "status", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "CHANGE-001  generated  Spec Work" in result.output
    assert "freshness=current" in result.output

    result = runner.invoke(app, ["spec", "show", "CHANGE-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Software Spec - CHANGE-001 - Spec Work" in result.output

    result = runner.invoke(app, ["spec", "prompt", "--change", "CHANGE-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Software spec prompt created" in result.output
    prompt = (spec_dir / "spec-refine.prompt.md").read_text(encoding="utf-8")
    assert "P2P Software Spec Refinement Prompt" in prompt
    assert "Do not add requirements" in prompt

    refined_dir = tmp_path / "refined-spec"
    refined_dir.mkdir()
    for filename in ("index.md", "requirements.md", "design.md", "acceptance.md"):
        (refined_dir / filename).write_text(f"# {filename}\n\nRefined.\n", encoding="utf-8")
    (refined_dir / "commands.yml").write_text("commands: []\n", encoding="utf-8")
    (refined_dir / "data-model.yml").write_text("entities: []\n", encoding="utf-8")
    (refined_dir / "provenance.yml").write_text(
        "source:\n  change: CHANGE-001\n  included_proposals:\n    - PROP-001\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["spec", "import", "CHANGE-001", str(refined_dir), "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Software spec imported" in result.output
    assert "Refined." in (spec_dir / "index.md").read_text(encoding="utf-8")

    result = runner.invoke(
        app,
        ["spec", "export", "--change", "CHANGE-001", "--target", "generic", "--root", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert "Software spec exported" in result.output
    assert "route: preflight_spec_then_export_target" in result.output
    assert ".p2p/outputs/spec-export/CHANGE-001/generic" in result.output

    generic_dir = tmp_path / ".p2p" / "outputs" / "spec-export" / "CHANGE-001" / "generic"
    assert (generic_dir / "project.md").exists()
    assert (generic_dir / "propose.md").exists()
    assert not (generic_dir / "manifest.yml").exists()
    project_text = (generic_dir / "project.md").read_text(encoding="utf-8")
    assert "Demo Project Project Definition" in project_text
    assert "## Executive Summary" in project_text
    assert "## Source Traceability" in project_text
    assert "Generate a deterministic software spec." in project_text

    result = runner.invoke(
        app,
        ["spec", "export", "--change", "CHANGE-001", "--target", "openspec", "--root", str(tmp_path)],
    )
    assert result.exit_code == 0

    openspec_dir = tmp_path / ".p2p" / "outputs" / "spec-export" / "CHANGE-001" / "openspec"
    assert (openspec_dir / "propose.md").exists()
    assert not (openspec_dir / "manifest.yml").exists()
    assert "OpenSpec Proposal Input" in (openspec_dir / "propose.md").read_text(encoding="utf-8")

    result = runner.invoke(
        app,
        ["spec", "export", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)],
    )
    assert result.exit_code == 0

    speckit_dir = tmp_path / ".p2p" / "outputs" / "spec-export" / "CHANGE-001" / "speckit"
    assert (speckit_dir / "speckit.constitution.md").exists()
    assert (speckit_dir / "speckit.specify.md").exists()
    assert (speckit_dir / "speckit.plan.md").exists()
    assert not (speckit_dir / "manifest.yml").exists()
    assert not (speckit_dir / "specs").exists()
    assert "Spec Kit Constitution Prompt" in (speckit_dir / "speckit.constitution.md").read_text(encoding="utf-8")
    assert "Spec Kit Specify Prompt" in (speckit_dir / "speckit.specify.md").read_text(encoding="utf-8")
    assert "Spec Kit Plan Prompt" in (speckit_dir / "speckit.plan.md").read_text(encoding="utf-8")

    result = runner.invoke(app, ["spec", "export-status", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "CHANGE-001  generic  exported  Spec Work" in result.output
    assert "CHANGE-001  openspec  exported  Spec Work" in result.output
    assert "CHANGE-001  speckit  exported  Spec Work" in result.output

    result = runner.invoke(
        app,
        ["spec", "export-show", "CHANGE-001", "--target", "openspec", "--root", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert "OpenSpec Proposal Input" in result.output

    result = runner.invoke(
        app,
        ["spec", "export-show", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert "Spec Kit Constitution Prompt" in result.output

    for target in ("generic", "openspec", "speckit"):
        result = runner.invoke(
            app,
            ["spec", "export-validate", "CHANGE-001", "--target", target, "--root", str(tmp_path)],
        )
        assert result.exit_code == 0
        assert "Software spec export valid" in result.output
        assert f"target: {target}" in result.output

    (openspec_dir / "propose.md").unlink()
    result = runner.invoke(
        app,
        ["spec", "export-validate", "CHANGE-001", "--target", "openspec", "--root", str(tmp_path)],
    )
    assert result.exit_code != 0
    assert "Missing required software spec export artifact: propose.md" in result.output

    runner.invoke(app, ["spec", "export", "--change", "CHANGE-001", "--target", "generic", "--root", str(tmp_path)])
    (generic_dir / "project.md").write_text("# Broken\n\n## Executive Summary\n\nMissing sections.\n", encoding="utf-8")
    result = runner.invoke(
        app,
        ["spec", "export-validate", "CHANGE-001", "--target", "generic", "--root", str(tmp_path)],
    )
    assert result.exit_code != 0
    assert "Missing required project definition section" in result.output

    result = runner.invoke(
        app,
        ["spec", "export", "--change", "CHANGE-001", "--target", "unknown", "--root", str(tmp_path)],
    )
    assert result.exit_code != 0
    assert "Unsupported software spec export target: unknown" in result.output


def test_cli_spec_lifecycle_guidance_and_blocking_preflight(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "Spec Work",
            "--problem",
            "Need implementation-facing specs.",
            "--proposal",
            "Generate a deterministic software spec.",
            "--acceptance",
            "Spec artifacts exist.",
            "--root",
            str(tmp_path),
        ],
    )
    _apply_proposal_decision(tmp_path, "PROP-001")
    runner.invoke(app, ["change", "create", "--from", "PROP-001", "--root", str(tmp_path)])

    result = runner.invoke(
        app,
        ["spec", "lifecycle", "--intent", "implementation_spec", "--change", "CHANGE-001", "--root", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert "Software spec lifecycle" in result.output
    assert "route: preflight_change_set_then_refresh_software_spec" in result.output
    assert "blockers: none" in result.output
    assert "software_vertical_not_active" in result.output
    assert "p2p spec refresh --change CHANGE-001" in result.output

    change_path = tmp_path / ".p2p" / "changes" / "CHANGE-001-spec-work" / "change.md"
    text = change_path.read_text(encoding="utf-8")
    frontmatter = read_frontmatter(text)
    frontmatter["source"] = {"accepted_proposals": []}
    change_path.write_text(replace_frontmatter(text, frontmatter), encoding="utf-8")

    blocked = runner.invoke(app, ["spec", "refresh", "--change", "CHANGE-001", "--root", str(tmp_path)])

    assert blocked.exit_code == 1
    assert "missing_governed_source" in blocked.output
    assert not (tmp_path / ".p2p" / "outputs" / "software-spec" / "CHANGE-001").exists()


def test_cli_spec_lifecycle_rejects_unknown_intent(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])

    result = runner.invoke(app, ["spec", "lifecycle", "--intent", "unknown", "--root", str(tmp_path)])

    assert result.exit_code == 1
    assert "Unsupported software spec lifecycle intent" in result.output
    assert "implementation_spec" in result.output


def test_cli_work_plan_list_and_show(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "Managed Work",
            "--problem",
            "Need a logical implementation handoff.",
            "--proposal",
            "Create a P2P Work manifest.",
            "--acceptance",
            "Work manifest exists.",
            "--root",
            str(tmp_path),
        ],
    )
    _apply_proposal_decision(
        tmp_path,
        "PROP-001",
        reason="Ready for handoff.",
    )
    runner.invoke(app, ["change", "create", "--from", "PROP-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "refresh", "--change", "CHANGE-001", "--root", str(tmp_path)])

    result = runner.invoke(
        app,
        ["work", "plan", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)],
    )
    assert result.exit_code != 0
    assert "Software spec export not found" in result.output

    runner.invoke(app, ["spec", "export", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])

    result = runner.invoke(
        app,
        ["work", "plan", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert "Work plan created" in result.output
    assert "work: WORK-001" in result.output

    manifest = tmp_path / ".p2p" / "work" / "WORK-001" / "manifest.yml"
    assert manifest.exists()
    manifest_text = manifest.read_text(encoding="utf-8")
    assert "visibility: internal_project_state" in manifest_text
    assert "export_validated: true" in manifest_text

    result = runner.invoke(app, ["work", "list", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "WORK-001  planned  CHANGE-001  speckit" in result.output

    result = runner.invoke(app, ["work", "status", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Work status" in result.output
    assert "WORK-001  planned" in result.output
    assert "change: CHANGE-001" in result.output
    assert "next: p2p work show WORK-001" in result.output

    result = runner.invoke(app, ["work", "show", "WORK-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "WORK-001 - planned" in result.output
    assert "visibility: internal_project_state" in result.output


def test_cli_work_retire_marks_planned_work_retired(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "Managed Work Retire",
            "--problem",
            "Need to retire obsolete handoffs.",
            "--proposal",
            "Retire planned logical Work.",
            "--acceptance",
            "The Work item is marked retired.",
            "--root",
            str(tmp_path),
        ],
    )
    _apply_proposal_decision(tmp_path, "PROP-001")
    runner.invoke(app, ["change", "create", "--from", "PROP-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "refresh", "--change", "CHANGE-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "export", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])
    runner.invoke(app, ["work", "plan", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])

    result = runner.invoke(
        app,
        [
            "work",
            "retire",
            "WORK-001",
            "--reason",
            "Superseded by later implementation.",
            "--root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "Work retired" in result.output
    assert "status: retired" in result.output

    manifest_text = (tmp_path / ".p2p" / "work" / "WORK-001" / "manifest.yml").read_text(encoding="utf-8")
    assert "status: retired" in manifest_text
    assert "retirement:" in manifest_text
    assert "Superseded by later implementation." in manifest_text

    status = runner.invoke(app, ["work", "status", "--root", str(tmp_path)])
    assert status.exit_code == 0
    assert "WORK-001  retired" in status.output
    assert "next: none" in status.output
    assert "note: retired" in status.output


def test_cli_work_retire_requires_planned_status(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "Managed Work Retire",
            "--problem",
            "Need to retire obsolete handoffs.",
            "--proposal",
            "Retire planned logical Work.",
            "--acceptance",
            "The Work item is marked retired.",
            "--root",
            str(tmp_path),
        ],
    )
    _apply_proposal_decision(tmp_path, "PROP-001")
    runner.invoke(app, ["change", "create", "--from", "PROP-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "refresh", "--change", "CHANGE-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "export", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])
    runner.invoke(app, ["work", "plan", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])

    manifest_path = tmp_path / ".p2p" / "work" / "WORK-001" / "manifest.yml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["status"] = "completed"
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")

    result = runner.invoke(
        app,
        ["work", "retire", "WORK-001", "--reason", "Obsolete.", "--root", str(tmp_path)],
    )

    assert result.exit_code != 0
    assert "Work item must be planned before retire" in result.output


def test_cli_registry_includes_choice_artifacts(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    choice_dir = tmp_path / ".p2p" / "choices" / "CHOICE-001-initial-ai-strategy"
    choice_dir.mkdir(parents=True)
    (choice_dir / "choice.md").write_text(
        "---\n"
        "choice_id: CHOICE-001\n"
        "title: Initial AI Strategy\n"
        "status: open\n"
        "---\n\n"
        "# CHOICE-001 - Initial AI Strategy\n",
        encoding="utf-8",
    )
    (choice_dir / "options.yml").write_text(
        "options:\n"
        "  - id: A\n"
        "    title: Prompt-only first\n"
        "  - id: B\n"
        "    title: Direct AI now\n",
        encoding="utf-8",
    )
    (choice_dir / "decision.md").write_text(
        "# Decision - CHOICE-001\n\n## Selected Option\n\nPending.\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["registry", "refresh", "--root", str(tmp_path)])
    assert result.exit_code == 0

    result = runner.invoke(app, ["registry", "show", "choices", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "CHOICE-001" in result.output
    assert "Initial AI Strategy" in result.output


def test_cli_choice_create_list_and_decide(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Prompt Workflow", "--root", str(tmp_path)])

    result = runner.invoke(
        app,
        [
            "choice",
            "create",
            "--title",
            "Initial AI Strategy",
            "--problem",
            "Choose the initial AI integration strategy.",
            "--context",
            "The project needs a stable initial implementation direction.",
            "--option",
            "Prompt-only first",
            "--option",
            "Direct AI now",
            "--option",
            "Prompt-only first, AI adapter later",
            "--related",
            "PROP-001",
            "--source",
            "INTAKE-001",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert "Choice created" in result.output
    assert "id: CHOICE-001" in result.output

    choice_dir = tmp_path / ".p2p" / "choices" / "CHOICE-001-initial-ai-strategy"
    assert (choice_dir / "choice.md").exists()
    assert "Prompt-only first" in (choice_dir / "options.yml").read_text(encoding="utf-8")

    result = runner.invoke(app, ["choice", "list", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "CHOICE-001  open  Initial AI Strategy" in result.output

    result = runner.invoke(
        app,
        [
            "choice",
            "decide",
            "CHOICE-001",
            "--option",
            "C",
            "--reason",
            "Keep MVP stable while planning adapters.",
            "--decider",
            "owner",
            "--operation-key",
            "cli-choice-decision-001",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert "Choice transition preview" in result.output
    token = re.search(r"preview token:\s*((?:[0-9a-f]\s*){64})", result.output)
    assert token is not None
    preview_token = "".join(token.group(1).split())
    result = runner.invoke(
        app,
        [
            "choice",
            "decide",
            "CHOICE-001",
            "--option",
            "C",
            "--reason",
            "Keep MVP stable while planning adapters.",
            "--decider",
            "owner",
            "--operation-key",
            "cli-choice-decision-001",
            "--preview-token",
            preview_token,
            "--confirm",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert "Choice transition applied" in result.output

    result = runner.invoke(app, ["choice", "list", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "CHOICE-001  decided  Initial AI Strategy" in result.output
    assert "C - Prompt-only first, AI adapter" in result.output

    decision = (choice_dir / "decision.md").read_text(encoding="utf-8")
    assert "`decided`" in decision
    assert "Keep MVP stable while planning adapters." in decision

    runner.invoke(app, ["registry", "refresh", "--root", str(tmp_path)])
    result = runner.invoke(app, ["registry", "show", "choices", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "CHOICE-001" in result.output


def test_cli_choice_withdraw_and_supersede_use_the_same_preview_apply_contract(
    tmp_path: Path,
) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    for title in ("Withdrawn frame", "Historical frame", "Replacement frame"):
        created = runner.invoke(
            app,
            [
                "choice",
                "create",
                "--title",
                title,
                "--problem",
                f"Choose a direction for {title}.",
                "--context",
                "The project needs a complete immutable decision frame.",
                "--option",
                "Continue",
                "--option",
                "Stop",
                "--root",
                str(tmp_path),
            ],
        )
        assert created.exit_code == 0, created.output

    cases = (
        (
            ["withdraw", "CHOICE-001"],
            ["--reason", "The frame is obsolete."],
            "cli-choice-withdraw-001",
            "withdrawn",
        ),
        (
            ["supersede", "CHOICE-002"],
            [
                "--replacement",
                "CHOICE-003",
                "--reason",
                "A new frame captures the revised question.",
            ],
            "cli-choice-supersede-002",
            "superseded",
        ),
    )
    for command, arguments, operation_key, expected_state in cases:
        base = ["choice", *command, *arguments, "--operation-key", operation_key]
        preview = runner.invoke(app, [*base, "--root", str(tmp_path)])
        assert preview.exit_code == 0, preview.output
        match = re.search(r"preview token:\s*((?:[0-9a-f]\s*){64})", preview.output)
        assert match is not None
        token = "".join(match.group(1).split())

        applied = runner.invoke(
            app,
            [
                *base,
                "--preview-token",
                token,
                "--confirm",
                "--root",
                str(tmp_path),
            ],
        )
        assert applied.exit_code == 0, applied.output
        shown = runner.invoke(
            app,
            ["choice", "show", command[1], "--root", str(tmp_path)],
        )
        assert f"status: {expected_state}" in shown.output

    structured = runner.invoke(
        app,
        [
            "choice",
            "transition-preview",
            "CHOICE-003",
            "--transition",
            "decide",
            "--option",
            "A",
            "--reason",
            "Select the replacement direction.",
            "--operation-key",
            "cli-choice-json-preview",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )
    assert structured.exit_code == 0, structured.output
    assert cli_data(structured)["contract"] == "p2p-choice-transition-preview/v1"
    assert "candidates" not in cli_data(structured)


def test_cli_choice_discovery_blocking_and_next_integration(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--domain", "software", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Governance Model", "--root", str(tmp_path)])
    runner.invoke(app, ["vote", "record", "PROP-001", "--choice", "A", "--reason", "Prefer A", "--root", str(tmp_path)])
    _apply_proposal_decision(tmp_path, "PROP-001", reason="Needed.")
    runner.invoke(app, ["change", "create", "--from", "PROP-001", "--title", "Governance Model", "--root", str(tmp_path)])
    runner.invoke(app, ["change", "set-status", "CHANGE-001", "planned", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "choice",
            "create",
            "--title",
            "Governance Scope",
            "--problem",
            "Choose the governance scope.",
            "--context",
            "The accepted change requires a project-level governance decision.",
            "--option",
            "Minimal governance",
            "--option",
            "Full governance",
            "--related",
            "PROP-001",
            "--root",
            str(tmp_path),
        ],
    )

    result = runner.invoke(app, ["choice", "status", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "project choices:" in result.output
    assert "CHOICE-001  open  Governance Scope" in result.output
    assert "proposal-local candidates:" in result.output
    assert "CHOICE-PROP-001" in result.output

    result = runner.invoke(app, ["choice", "discover", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "proposal_local_choice_candidate" in result.output
    assert "CHOICE-PROP-001" in result.output
    assert "open_project_choice" in result.output

    result = runner.invoke(
        app,
        [
            "choice",
            "block",
            "CHOICE-001",
            "--change",
            "CHANGE-001",
            "--reason",
            "Governance scope must be decided first.",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert "Choice blocker recorded" in result.output

    result = runner.invoke(app, ["choice", "show", "CHOICE-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "blocks:" in result.output
    assert "change CHANGE-001  active" in result.output
    assert "Governance scope must be decided first." in result.output

    result = runner.invoke(app, ["next", "--top", "1", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "NEXT-BLOCKER-001  high  resolve_choice" in result.output
    assert "target: CHOICE-001" in result.output

    result = runner.invoke(
        app,
        ["choice", "unblock", "CHOICE-001", "--change", "CHANGE-001", "--root", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert "Choice blocker cleared" in result.output

    runner.invoke(app, ["registry", "refresh", "--root", str(tmp_path)])
    result = runner.invoke(app, ["next", "--top", "100", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "continue_change" in result.output
    assert "target: CHANGE-001" in result.output


def test_cli_intake_prompt_import_and_status(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "CLI Foundation", "--root", str(tmp_path)])
    _apply_proposal_decision(
        tmp_path,
        "PROP-001",
        reason="Baseline CLI work.",
    )
    runner.invoke(app, ["project", "refresh", "--root", str(tmp_path)])
    runner.invoke(app, ["registry", "refresh", "--root", str(tmp_path)])

    result = runner.invoke(
        app,
        [
            "intake",
            "prompt",
            "La CLI dovrebbe integrare subito Codex",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert "Intake prompt created" in result.output
    assert "id: INTAKE-001" in result.output

    intake_dir = tmp_path / ".p2p" / "intake" / "INTAKE-001"
    prompt = (intake_dir / "intake.prompt.md").read_text(encoding="utf-8")
    assert "P2P Intake Prompt" in prompt
    assert "La CLI dovrebbe integrare subito Codex" in prompt
    assert "PROP-001" in prompt
    assert "Do not accept, reject, defer, merge or supersede proposals" in prompt

    result = runner.invoke(app, ["intake", "status", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "INTAKE-001  pending" in result.output

    output_dir = tmp_path / "intake-output"
    output_dir.mkdir()
    (output_dir / "recommendation.md").write_text(
        "# Recommendation\n\nClassify as alternative to PROP-001.\n",
        encoding="utf-8",
    )
    (output_dir / "related-proposals.yml").write_text(
        "related_proposals:\n"
        "  - proposal: PROP-001\n"
        "    relationship: references\n"
        "    rationale: Changes initial AI strategy.\n",
        encoding="utf-8",
    )
    (output_dir / "suggested-actions.yml").write_text(
        "suggested_actions:\n"
        "  - type: add_contribution\n"
        "    target: PROP-001\n"
        "    rationale: Treat as alternative implementation path.\n",
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["intake", "import", "INTAKE-001", str(output_dir), "--root", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert "Intake imported" in result.output
    assert "suggested-actions.yml" in result.output

    result = runner.invoke(app, ["intake", "status", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "INTAKE-001  analyzed" in result.output

    decision = (
        tmp_path / ".p2p" / "proposals" / "PROP-001-cli-foundation" / "decision.md"
    ).read_text(encoding="utf-8")
    assert "Baseline CLI work." in decision


def test_cli_intake_apply_plan_show_and_run(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Prompt Workflow", "--root", str(tmp_path)])
    intake_dir = tmp_path / ".p2p" / "intake" / "INTAKE-001"
    intake_dir.mkdir(parents=True)
    (intake_dir / "recommendation.md").write_text("# Recommendation\n\nAnalyze direct AI.\n", encoding="utf-8")
    (intake_dir / "related-proposals.yml").write_text("related_proposals: []\n", encoding="utf-8")
    (intake_dir / "suggested-actions.yml").write_text(
        "suggested_actions:\n"
        "  - type: add_contribution\n"
        "    target: PROP-001\n"
        "    rationale: Preserve direct AI as a tracked alternative.\n"
        "  - type: open_choice\n"
        "    target: PROP-001\n"
        "    rationale: Decide whether direct AI belongs in this workflow.\n"
        "  - type: defer\n"
        "    target: PROP-001\n"
        "    rationale: Governance decision preview only.\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["intake", "apply", "plan", "INTAKE-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Intake apply plan created" in result.output
    assert "actions: 3" in result.output

    result = runner.invoke(app, ["intake", "apply", "show", "INTAKE-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "APPLY-001  pending  supported  add_contribution -> PROP-001" in result.output
    assert "APPLY-002  pending  requires_input  open_choice -> PROP-001" in result.output
    assert "APPLY-003  pending  governance_only  defer -> PROP-001" in result.output

    result = runner.invoke(
        app,
        ["intake", "apply", "run", "INTAKE-001", "--action", "APPLY-001", "--root", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert "Intake apply action applied" in result.output
    assert "type: add_contribution" in result.output

    contributions = (
        tmp_path / ".p2p" / "proposals" / "PROP-001-prompt-workflow" / "contributions.yml"
    ).read_text(encoding="utf-8")
    assert "Preserve direct AI as a tracked alternative." in contributions
    assert "intake:INTAKE-001" in contributions

    result = runner.invoke(
        app,
        ["intake", "apply", "run", "INTAKE-001", "--action", "APPLY-002", "--root", str(tmp_path)],
    )
    assert result.exit_code == 1
    assert "requires at least two --option values" in result.output

    result = runner.invoke(
        app,
        [
            "intake",
            "apply",
            "run",
            "INTAKE-001",
            "--action",
            "APPLY-002",
            "--option",
            "Keep prompt-only",
            "--option",
            "Explore direct AI",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert "type: open_choice" in result.output
    assert (tmp_path / ".p2p" / "choices" / "CHOICE-001-intake-intake-001-choice-for-prop-001").exists()

    result = runner.invoke(
        app,
        ["intake", "apply", "run", "INTAKE-001", "--action", "APPLY-003", "--root", str(tmp_path)],
    )
    assert result.exit_code == 1
    assert "governance_only" in result.output

    applied = (intake_dir / "applied-actions.yml").read_text(encoding="utf-8")
    assert "APPLIED-001" in applied
    assert "APPLIED-002" in applied
    assert "add_contribution" in applied
    assert "open_choice" in applied

    plan = (intake_dir / "apply-plan.yml").read_text(encoding="utf-8")
    assert "status: applied" in plan
    assert "created_choice: CHOICE-001" in plan


def test_cli_project_brief_prompt_import_and_show(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "CLI Foundation", "--root", str(tmp_path)])
    _apply_proposal_decision(
        tmp_path,
        "PROP-001",
        reason="Baseline CLI work.",
    )
    runner.invoke(app, ["project", "refresh", "--root", str(tmp_path)])
    runner.invoke(app, ["registry", "refresh", "--root", str(tmp_path)])

    result = runner.invoke(app, ["project", "brief", "prompt", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Project brief prompt created" in result.output
    assert "brief.prompt.md" in result.output

    project_dir = tmp_path / ".p2p" / "project"
    prompt = (project_dir / "brief.prompt.md").read_text(encoding="utf-8")
    context = (project_dir / "brief-context.md").read_text(encoding="utf-8")
    assert "P2P Operational Brief Prompt" in prompt
    assert "Do not accept, reject, defer, merge, supersede, or apply recommendations" in prompt
    assert "CLI Foundation" in context
    assert "## Proposals Registry" in context

    output_dir = tmp_path / "brief-output"
    output_dir.mkdir()
    (output_dir / "operational-brief.md").write_text(
        "# Operational Brief\n\n## Where We Are\n\nThe CLI foundation is accepted.\n",
        encoding="utf-8",
    )
    (output_dir / "next-actions.yml").write_text(
        "next_actions:\n"
        "  - id: NEXT-001\n"
        "    priority: high\n"
        "    kind: create_change\n"
        "    target: PROP-001\n"
        "    reason: Accepted proposal needs operational packaging.\n"
        "    command: p2p change create --from PROP-001\n",
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["project", "brief", "import", str(output_dir), "--root", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert "Project brief imported" in result.output
    assert "operational-brief.md" in result.output
    assert "next-actions.yml" in result.output

    result = runner.invoke(app, ["project", "brief", "show", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "The CLI foundation is accepted." in result.output

    result = runner.invoke(app, ["next", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Next actions" in result.output
    assert "NEXT-001  high  create_change" in result.output
    assert "p2p change create --from PROP-001" in result.output
    assert ".p2p/project/next-actions.yml" in result.output

    result = runner.invoke(app, ["next", "--top", "10", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "NEXT-001  high  create_change" in result.output

    result = runner.invoke(app, ["project", "status", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "operational:" in result.output
    assert "brief: available" in result.output
    assert "next actions: 13" in result.output
    assert "first next: NEXT-DERIVED-FRESHNESS high refresh_derived_state assessment" in result.output
    assert "command: p2p assess refresh" in result.output


def test_cli_next_falls_back_without_imported_next_actions(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--domain", "software", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Managed Delivery", "--root", str(tmp_path)])
    _apply_proposal_decision(
        tmp_path,
        "PROP-001",
        reason="Needed for collaboration.",
    )
    runner.invoke(
        app,
        ["change", "create", "--from", "PROP-001", "--title", "Managed Delivery", "--root", str(tmp_path)],
    )
    runner.invoke(app, ["change", "set-status", "CHANGE-001", "planned", "--root", str(tmp_path)])

    result = runner.invoke(app, ["next", "--top", "100", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "project_question_answer" in result.output

    runner.invoke(app, ["registry", "refresh", "--root", str(tmp_path)])
    result = runner.invoke(app, ["next", "--top", "100", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "NEXT-CHANGE-CHANGE-001  high  continue_change" in result.output
    assert "target: CHANGE-001" in result.output
    assert "p2p change tasks CHANGE-001" in result.output
    assert "source: generated" in result.output


def test_cli_next_falls_back_to_draft_proposal_review(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--domain", "software", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Draft Work", "--root", str(tmp_path)])
    runner.invoke(app, ["registry", "refresh", "--root", str(tmp_path)])

    result = runner.invoke(app, ["next", "--top", "100", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert "assess_proposal_readiness" in result.output
    assert "target: PROP-001" in result.output
    assert "p2p proposal readiness refresh PROP-001" in result.output


def test_cli_next_falls_back_to_improve_low_readiness_draft(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--domain", "software", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Draft Work", "--root", str(tmp_path)])
    workspace = P2PWorkspace(tmp_path)
    workspace.write_proposal_readiness(
        "PROP-001",
        {
            "status": "assessed",
            "profile_id": "default-readiness-v0.1",
            "profile_version": "0.1",
            "computed_score": 64,
            "computed_label": "weak",
        },
    )
    runner.invoke(app, ["registry", "refresh", "--root", str(tmp_path)])

    result = runner.invoke(app, ["next", "--top", "100", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert "improve_proposal_readiness" in result.output
    assert "target: PROP-001" in result.output
    assert "p2p proposal readiness explain PROP-001" in result.output


def test_cli_next_manages_curated_lifecycle_and_log(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--domain", "software", "--root", str(tmp_path)])

    result = runner.invoke(
        app,
        [
            "next",
            "add",
            "verify_integration",
            "mcp-client",
            "--priority",
            "high",
            "--reason",
            "Verify real MCP client setup.",
            "--command",
            "p2p-mcp-server --root /path/to/project",
            "--root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "Next action added." in result.output
    assert "id: NEXT-001" in result.output

    result = runner.invoke(app, ["next", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "NEXT-001  high  verify_integration" in result.output
    assert "source: .p2p/project/next-actions.yml" in result.output

    result = runner.invoke(
        app,
        [
                "next",
                "complete",
                "NEXT-001",
            "--reason",
            "Verified successfully.",
            "--root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "Next action completed." in result.output
    active = yaml.safe_load((tmp_path / ".p2p" / "project" / "next-actions.yml").read_text(encoding="utf-8"))
    assert active["next_actions"] == []
    log = yaml.safe_load((tmp_path / ".p2p" / "project" / "next-actions-log.yml").read_text(encoding="utf-8"))
    assert log["next_action_log"][0]["id"] == "NEXT-001"
    assert log["next_action_log"][0]["status"] == "completed"
    assert log["next_action_log"][0]["closed_reason"] == "Verified successfully."


def test_cli_next_retire_and_refresh(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--domain", "software", "--root", str(tmp_path)])

    result = runner.invoke(
        app,
        [
            "next",
            "add",
            "define_scope",
            "temporary",
            "--reason",
            "Temporary scope item.",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0

    result = runner.invoke(
        app,
        ["next", "retire", "NEXT-001", "--reason", "Superseded.", "--root", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert "Next action retired." in result.output

    log = yaml.safe_load((tmp_path / ".p2p" / "project" / "next-actions-log.yml").read_text(encoding="utf-8"))
    assert log["next_action_log"][0]["status"] == "retired"

    result = runner.invoke(app, ["next", "refresh", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Next actions refreshed." in result.output
    assert "active_curated: 0" in result.output
    assert "generated:" in result.output


def test_cli_next_shows_generated_actions_when_curated_actions_exist(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--domain", "software", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "next",
            "add",
            "verify_integration",
            "mcp-client",
            "--reason",
            "Verify MCP client setup.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(app, ["proposal", "create", "Generated Draft", "--root", str(tmp_path)])
    runner.invoke(app, ["registry", "refresh", "--root", str(tmp_path)])

    result = runner.invoke(app, ["next", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert "NEXT-001  medium  verify_integration" in result.output
    assert "NEXT-FALLBACK-001  high  assess_proposal_readiness" in result.output
    assert "p2p proposal readiness refresh PROP-001" in result.output
    assert "source: generated" in result.output


def test_cli_next_deduplicates_curated_and_generated_actions(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--domain", "software", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Generated Draft", "--root", str(tmp_path)])
    runner.invoke(app, ["registry", "refresh", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "next",
            "add",
            "review_draft_proposal",
            "PROP-001",
            "--reason",
            "Curated review path.",
            "--root",
            str(tmp_path),
        ],
    )

    result = runner.invoke(app, ["next", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert result.output.count("review_draft_proposal") == 1
    assert "Curated review path." in result.output
