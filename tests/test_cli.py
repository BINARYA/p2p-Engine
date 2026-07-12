from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import yaml
from typer.testing import CliRunner

from p2p_engine import __version__ as P2P_ENGINE_VERSION
from p2p_engine.cli import app
from p2p_engine.foundation.markdown import read_frontmatter, replace_frontmatter
from p2p_engine.storage.filesystem import P2PWorkspace

runner = CliRunner()


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


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
    assert "p2p project vertical propose" in agents
    assert "Managed Git Collaboration" in agents
    assert "p2p sync status" in agents
    assert "p2p proposal publish PROP-XXX --auto-renumber" in agents
    assert "Do not run raw `git branch`, `git fetch`, `git pull`, `git push`, `git merge`" in agents
    assert "p2p context --budget small" in agents
    assert "Runtime Bootstrap" in agents
    assert ".venv/bin/p2p agent doctor" in agents
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
    payload = json.loads(json_result.output)
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
    preview_payload = json.loads(preview.output)
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
    apply_payload = json.loads(applied.output)
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


def test_cli_runtime_contract_adopt_json(tmp_path: Path) -> None:
    p2p_dir = tmp_path / ".p2p"
    p2p_dir.mkdir()
    (p2p_dir / "project.yml").write_text(
        yaml.safe_dump({"project": {"name": "Legacy Project"}}, sort_keys=False),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "runtime",
            "contract",
            "adopt",
            "--requires",
            f"=={P2P_ENGINE_VERSION}",
            "--recommended",
            P2P_ENGINE_VERSION,
            "--confirm",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["status"] == "adopted"
    assert payload["current_state"] == "legacy_undeclared"
    assert payload["files_changed"] == [".p2p/project/runtime.yml", "P2P-SETUP.md", ".p2p/project.yml"]
    project = yaml.safe_load((p2p_dir / "project.yml").read_text(encoding="utf-8"))
    assert project["runtime_contract"] == {"required": True}
    runtime = yaml.safe_load((p2p_dir / "project" / "runtime.yml").read_text(encoding="utf-8"))
    assert runtime["runtime"]["p2p"]["recommended"] == P2P_ENGINE_VERSION


def test_cli_runtime_contract_adopt_text_requires_confirmation(tmp_path: Path) -> None:
    p2p_dir = tmp_path / ".p2p"
    p2p_dir.mkdir()
    (p2p_dir / "project.yml").write_text(
        yaml.safe_dump({"project": {"name": "Legacy Project"}}, sort_keys=False),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "runtime",
            "contract",
            "adopt",
            "--requires",
            f"=={P2P_ENGINE_VERSION}",
            "--recommended",
            P2P_ENGINE_VERSION,
            "--root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "Runtime contract adopt" in result.output
    assert "status: blocked" in result.output
    assert "blocked_reason: confirmation_required" in result.output
    assert not (p2p_dir / "project" / "runtime.yml").exists()


def test_cli_runtime_contract_adopt_blocks_unmanaged_setup_guide(tmp_path: Path) -> None:
    p2p_dir = tmp_path / ".p2p"
    p2p_dir.mkdir()
    (p2p_dir / "project.yml").write_text(
        yaml.safe_dump({"project": {"name": "Legacy Project"}}, sort_keys=False),
        encoding="utf-8",
    )
    (tmp_path / "P2P-SETUP.md").write_text("# Human setup\n", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "runtime",
            "contract",
            "adopt",
            "--requires",
            f"=={P2P_ENGINE_VERSION}",
            "--recommended",
            P2P_ENGINE_VERSION,
            "--confirm",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["status"] == "blocked"
    assert payload["blocked_reason"] == "unmanaged_setup_guide"
    assert payload["files_changed"] == []
    assert not (p2p_dir / "project" / "runtime.yml").exists()


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
    runner.invoke(app, ["proposal", "accept", "PROP-001", "--reason", "Ready.", "--root", str(tmp_path)])

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
            "proposal_publish",
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
    assert "operation: proposal_publish" in result.output

    consent_path = tmp_path / ".p2p" / "consents" / "CONSENT-001" / "consent.yml"
    receipt = yaml.safe_load(consent_path.read_text(encoding="utf-8"))
    assert receipt["actor_id"] == "lorenzo"
    assert receipt["approved_by"] == "matteo"
    assert receipt["single_use"] is True

    result = runner.invoke(app, ["consent", "status", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "CONSENT-001  granted  proposal_publish  PROP-001  lorenzo" in result.output

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
            "proposal_publish",
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


def test_cli_init_default_domain_and_rubric_are_unresolved(tmp_path: Path) -> None:
    result = runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])

    assert result.exit_code == 0
    domain = yaml.safe_load((tmp_path / ".p2p" / "project" / "domain.yml").read_text(encoding="utf-8"))
    rubrics = yaml.safe_load((tmp_path / ".p2p" / "project" / "rubrics.yml").read_text(encoding="utf-8"))
    next_actions = yaml.safe_load((tmp_path / ".p2p" / "project" / "next-actions.yml").read_text(encoding="utf-8"))

    assert domain["status"] == "unresolved"
    assert domain["type"] == "none"
    assert rubrics["status"] == "unresolved"
    assert rubrics["criteria"] == []
    assert next_actions["next_actions"][0]["kind"] == "define_domain"

    result = runner.invoke(app, ["assess", "maturity", "refresh", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert "status: rubric_missing" in result.output
    assert "Define the project domain" in result.output


def test_cli_init_domain_template_populates_rubric(tmp_path: Path) -> None:
    result = runner.invoke(app, ["init", "Demo Project", "--domain", "software", "--root", str(tmp_path)])

    assert result.exit_code == 0
    domain = yaml.safe_load((tmp_path / ".p2p" / "project" / "domain.yml").read_text(encoding="utf-8"))
    rubrics = yaml.safe_load((tmp_path / ".p2p" / "project" / "rubrics.yml").read_text(encoding="utf-8"))

    assert domain["status"] == "template_selected"
    assert domain["template"] == "software"
    assert rubrics["status"] == "template_selected"
    assert rubrics["template"] == "software"
    assert any(criterion["id"] == "security_privacy" for criterion in rubrics["criteria"])
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
    payload = json.loads(result.output)
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
    payload = json.loads(preflight.output)
    assert payload["schema_version"] == "governance-preflight/v1"
    assert payload["vote_summary"]["alignment"] == "conflicts"
    assert "P2P_GOV_VOTE_CONFLICT" in [warning["code"] for warning in payload["warnings"]]
    assert "P2P_GOV_RELATED_PRECEDENTS" in [warning["code"] for warning in payload["warnings"]]
    decision = tmp_path / ".p2p" / "choices" / "CHOICE-001-deployment-strategy" / "decision.md"
    assert "Pending." in decision.read_text(encoding="utf-8")
    assert vote_status.exit_code == 0
    assert json.loads(vote_status.output)["winner"] == "A"
    assert governance_validate.exit_code == 0
    assert json.loads(governance_validate.output)["ok"] is True
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
    assert [(item["precedent_id"], item["match_reason"]) for item in json.loads(explicit.output)["precedents"]] == [
        ("DP001", "related_choice")
    ]
    assert fuzzy.exit_code == 0
    assert json.loads(fuzzy.output)["precedents"] == []


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


def test_cli_proposal_branch_creates_managed_branch_metadata(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Chiusura Magnetica", "--root", str(tmp_path)])
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline")
    _git(tmp_path, "branch", "-M", "main")

    result = runner.invoke(app, ["proposal", "branch", "PROP-001", "--actor", "lorenzo", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert "Managed proposal branch created" in result.output
    assert "proposal: PROP-001" in result.output
    assert "status: branched" in result.output
    assert "branch: p2p/proposal/PROP-001-chiusura-magnetica-lorenzo-" in result.output
    branch_name = _git(tmp_path, "branch", "--show-current").stdout.strip()
    assert branch_name.startswith("p2p/proposal/PROP-001-chiusura-magnetica-lorenzo-")
    assert len(branch_name.rsplit("-", 1)[1]) == 16
    assert _git(tmp_path, "status", "--porcelain").stdout.strip() == ""
    assert _git(tmp_path, "log", "-1", "--pretty=%s").stdout.strip() == "P2P proposal branch PROP-001"

    branch_metadata = tmp_path / ".p2p" / "proposals" / "PROP-001-chiusura-magnetica" / "branch.yml"
    data = yaml.safe_load(branch_metadata.read_text(encoding="utf-8"))
    assert data["proposal_id"] == "PROP-001"
    assert data["status"] == "branched"
    assert data["actor"] == "lorenzo"
    assert data["branch_hash16"] == branch_name.rsplit("-", 1)[1]

    result = runner.invoke(app, ["proposal", "status", "PROP-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Proposal branch status" in result.output
    assert "status: branched" in result.output


def test_cli_proposal_publish_request_review_and_scan(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Chiusura Magnetica", "--root", str(tmp_path)])
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    remote_path = tmp_path.parent / f"{tmp_path.name}.git"
    _git(tmp_path, "init", "--bare", str(remote_path))
    _git(tmp_path, "remote", "add", "origin", str(remote_path))
    runner.invoke(
        app,
        [
            "project",
            "remote",
            "configure",
            "--mode",
            "remote",
            "--provider",
            "github",
            "--root",
            str(tmp_path),
        ],
    )
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline")
    _git(tmp_path, "branch", "-M", "main")

    runner.invoke(app, ["proposal", "branch", "PROP-001", "--actor", "lorenzo", "--root", str(tmp_path)])
    branch_name = _git(tmp_path, "branch", "--show-current").stdout.strip()

    result = runner.invoke(app, ["proposal", "publish", "PROP-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Managed proposal branch published" in result.output
    assert "status: published" in result.output
    assert "remote: origin" in result.output
    assert branch_name in _git(tmp_path, "ls-remote", "--heads", "origin", branch_name).stdout
    assert _git(tmp_path, "status", "--porcelain").stdout.strip() == ""
    assert _git(tmp_path, "log", "-1", "--pretty=%s").stdout.strip() == "P2P proposal publish PROP-001"

    result = runner.invoke(app, ["proposal", "request-review", "PROP-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Managed proposal review requested" in result.output
    assert "status: review_requested" in result.output
    assert "suggested_next:" in result.output
    assert _git(tmp_path, "log", "-1", "--pretty=%s").stdout.strip() == "P2P proposal request review PROP-001"

    result = runner.invoke(app, ["proposal", "scan", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Proposal branch scan" in result.output
    assert "proposal_branches: 1" in result.output
    assert "PROP-001  review_requested" in result.output
    assert (tmp_path / ".p2p" / "registries" / "proposal-branches.yml").exists()


def test_cli_proposal_publish_auto_renumbers_on_remote_id_collision(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Chiusura Magnetica", "--root", str(tmp_path)])
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    remote_path = tmp_path.parent / f"{tmp_path.name}.git"
    _git(tmp_path, "init", "--bare", str(remote_path))
    _git(tmp_path, "remote", "add", "origin", str(remote_path))
    runner.invoke(
        app,
        [
            "project",
            "remote",
            "configure",
            "--mode",
            "remote",
            "--provider",
            "generic",
            "--root",
            str(tmp_path),
        ],
    )
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline")
    _git(tmp_path, "branch", "-M", "main")
    _git(
        tmp_path,
        "push",
        "origin",
        "main:refs/heads/p2p/proposal/PROP-001-existing-matteo-aaaaaaaaaaaaaaaa",
    )

    runner.invoke(app, ["proposal", "branch", "PROP-001", "--actor", "lorenzo", "--root", str(tmp_path)])

    result = runner.invoke(app, ["proposal", "publish", "PROP-001", "--root", str(tmp_path)])
    assert result.exit_code == 1
    assert "Proposal ID collision detected on remote: PROP-001" in result.output
    assert "--auto-renumber" in result.output
    assert (tmp_path / ".p2p" / "proposals" / "PROP-001-chiusura-magnetica").exists()

    result = runner.invoke(app, ["proposal", "publish", "PROP-001", "--auto-renumber", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert "Managed proposal branch published" in result.output
    assert "proposal: PROP-002" in result.output
    assert "status: published" in result.output
    branch_name = _git(tmp_path, "branch", "--show-current").stdout.strip()
    assert branch_name.startswith("p2p/proposal/PROP-002-chiusura-magnetica-lorenzo-")
    assert len(branch_name.rsplit("-", 1)[1]) == 16
    assert not (tmp_path / ".p2p" / "proposals" / "PROP-001-chiusura-magnetica").exists()
    branch_metadata = tmp_path / ".p2p" / "proposals" / "PROP-002-chiusura-magnetica" / "branch.yml"
    data = yaml.safe_load(branch_metadata.read_text(encoding="utf-8"))
    assert data["proposal_id"] == "PROP-002"
    assert data["renumbered_from"] == "PROP-001"
    assert data["id_collision_check"]["old_proposal_id"] == "PROP-001"
    assert data["id_collision_check"]["new_proposal_id"] == "PROP-002"
    assert branch_name in _git(tmp_path, "ls-remote", "--heads", "origin", branch_name).stdout
    assert _git(tmp_path, "status", "--porcelain").stdout.strip() == ""
    assert _git(tmp_path, "log", "--pretty=%s", "-2").stdout.splitlines() == [
        "P2P proposal publish PROP-002",
        "P2P proposal auto-renumber PROP-001 to PROP-002",
    ]


def test_cli_proposal_publish_detects_collision_from_remote_main(tmp_path: Path) -> None:
    remote_path = tmp_path / "remote.git"
    _git(tmp_path, "init", "--bare", str(remote_path))

    seed_path = tmp_path / "seed"
    seed_path.mkdir()
    runner.invoke(app, ["init", "Seed Project", "--root", str(seed_path)])
    runner.invoke(app, ["proposal", "create", "Existing Remote Idea", "--root", str(seed_path)])
    _git(seed_path, "init")
    _git(seed_path, "config", "user.email", "test@example.com")
    _git(seed_path, "config", "user.name", "Test User")
    _git(seed_path, "remote", "add", "origin", str(remote_path))
    _git(seed_path, "add", ".")
    _git(seed_path, "commit", "-m", "remote main proposal")
    _git(seed_path, "branch", "-M", "main")
    _git(seed_path, "push", "origin", "main")

    work_path = tmp_path / "work"
    work_path.mkdir()
    runner.invoke(app, ["init", "Demo Project", "--root", str(work_path)])
    runner.invoke(app, ["proposal", "create", "Local Concurrent Idea", "--root", str(work_path)])
    _git(work_path, "init")
    _git(work_path, "config", "user.email", "test@example.com")
    _git(work_path, "config", "user.name", "Test User")
    _git(work_path, "remote", "add", "origin", str(remote_path))
    runner.invoke(
        app,
        [
            "project",
            "remote",
            "configure",
            "--mode",
            "remote",
            "--provider",
            "generic",
            "--root",
            str(work_path),
        ],
    )
    _git(work_path, "add", ".")
    _git(work_path, "commit", "-m", "local baseline")
    _git(work_path, "branch", "-M", "main")
    runner.invoke(app, ["proposal", "branch", "PROP-001", "--actor", "lorenzo", "--root", str(work_path)])

    result = runner.invoke(app, ["proposal", "publish", "PROP-001", "--root", str(work_path)])

    assert result.exit_code == 1
    assert "Proposal ID collision detected on remote: PROP-001" in result.output

    result = runner.invoke(app, ["proposal", "publish", "PROP-001", "--auto-renumber", "--root", str(work_path)])

    assert result.exit_code == 0
    assert "proposal: PROP-002" in result.output
    assert (work_path / ".p2p" / "proposals" / "PROP-002-local-concurrent-idea").exists()
    assert "PROP-002-local-concurrent-idea" not in _git(seed_path, "ls-tree", "-r", "--name-only", "origin/main").stdout


def test_cli_proposal_retire_branch_records_reason(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Chiusura Magnetica", "--root", str(tmp_path)])
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline")
    _git(tmp_path, "branch", "-M", "main")
    runner.invoke(app, ["proposal", "branch", "PROP-001", "--actor", "lorenzo", "--root", str(tmp_path)])

    result = runner.invoke(
        app,
        ["proposal", "retire-branch", "PROP-001", "--reason", "Superseded by another idea.", "--root", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert "Managed proposal branch retired" in result.output
    assert "status: retired" in result.output
    assert _git(tmp_path, "log", "-1", "--pretty=%s").stdout.strip() == "P2P proposal retire PROP-001"
    branch_metadata = tmp_path / ".p2p" / "proposals" / "PROP-001-chiusura-magnetica" / "branch.yml"
    data = yaml.safe_load(branch_metadata.read_text(encoding="utf-8"))
    assert data["retirement"]["reason"] == "Superseded by another idea."


def test_cli_proposal_merge_merges_reviewed_branch_into_base(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Chiusura Magnetica", "--root", str(tmp_path)])
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    remote_path = tmp_path.parent / f"{tmp_path.name}.git"
    _git(tmp_path, "init", "--bare", str(remote_path))
    _git(tmp_path, "remote", "add", "origin", str(remote_path))
    runner.invoke(app, ["project", "remote", "configure", "--mode", "remote", "--provider", "generic", "--root", str(tmp_path)])
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline")
    _git(tmp_path, "branch", "-M", "main")
    runner.invoke(app, ["proposal", "branch", "PROP-001", "--actor", "lorenzo", "--root", str(tmp_path)])
    proposal_path = tmp_path / ".p2p" / "proposals" / "PROP-001-chiusura-magnetica" / "proposal.md"
    proposal_path.write_text(proposal_path.read_text(encoding="utf-8") + "\nBranch refinement.\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "refine proposal")
    runner.invoke(app, ["proposal", "publish", "PROP-001", "--root", str(tmp_path)])
    _git(tmp_path, "checkout", "main")

    result = runner.invoke(app, ["proposal", "merge", "PROP-001", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert "Managed proposal branch merged" in result.output
    assert "proposal: PROP-001" in result.output
    assert _git(tmp_path, "branch", "--show-current").stdout.strip() == "main"
    assert _git(tmp_path, "log", "-1", "--pretty=%s").stdout.strip() == "P2P proposal merge PROP-001"
    branch_metadata = tmp_path / ".p2p" / "proposals" / "PROP-001-chiusura-magnetica" / "branch.yml"
    data = yaml.safe_load(branch_metadata.read_text(encoding="utf-8"))
    assert data["status"] == "merged"
    assert data["merge"]["source_branch"].startswith("p2p/proposal/PROP-001-chiusura-magnetica-lorenzo-")


def test_cli_proposal_accept_branch_records_governance_decision(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Chiusura Magnetica", "--root", str(tmp_path)])
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    remote_path = tmp_path.parent / f"{tmp_path.name}.git"
    _git(tmp_path, "init", "--bare", str(remote_path))
    _git(tmp_path, "remote", "add", "origin", str(remote_path))
    runner.invoke(app, ["project", "remote", "configure", "--mode", "remote", "--provider", "generic", "--root", str(tmp_path)])
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline")
    _git(tmp_path, "branch", "-M", "main")
    runner.invoke(app, ["proposal", "branch", "PROP-001", "--actor", "lorenzo", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "publish", "PROP-001", "--root", str(tmp_path)])

    result = runner.invoke(
        app,
        ["proposal", "accept-branch", "PROP-001", "--reason", "Ready to merge.", "--root", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert "Managed proposal branch accepted" in result.output
    assert "status: accepted" in result.output
    assert _git(tmp_path, "log", "-1", "--pretty=%s").stdout.strip() == "P2P proposal branch accept PROP-001"
    branch_metadata = tmp_path / ".p2p" / "proposals" / "PROP-001-chiusura-magnetica" / "branch.yml"
    data = yaml.safe_load(branch_metadata.read_text(encoding="utf-8"))
    assert data["status"] == "accepted"
    assert data["branch_decision"]["outcome"] == "accepted"
    assert data["branch_decision"]["reason"] == "Ready to merge."

    _git(tmp_path, "checkout", "main")
    result = runner.invoke(app, ["proposal", "merge", "PROP-001", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert "Managed proposal branch merged" in result.output


def test_cli_proposal_finalize_pushes_merged_base_branch(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Chiusura Magnetica", "--root", str(tmp_path)])
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    remote_path = tmp_path.parent / f"{tmp_path.name}.git"
    _git(tmp_path, "init", "--bare", str(remote_path))
    _git(tmp_path, "remote", "add", "origin", str(remote_path))
    runner.invoke(app, ["project", "remote", "configure", "--mode", "remote", "--provider", "generic", "--root", str(tmp_path)])
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline")
    _git(tmp_path, "branch", "-M", "main")
    runner.invoke(app, ["proposal", "branch", "PROP-001", "--actor", "lorenzo", "--root", str(tmp_path)])
    proposal_path = tmp_path / ".p2p" / "proposals" / "PROP-001-chiusura-magnetica" / "proposal.md"
    proposal_path.write_text(proposal_path.read_text(encoding="utf-8") + "\nBranch refinement.\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "refine proposal")
    runner.invoke(app, ["proposal", "publish", "PROP-001", "--root", str(tmp_path)])
    _git(tmp_path, "checkout", "main")
    runner.invoke(app, ["proposal", "merge", "PROP-001", "--root", str(tmp_path)])

    result = runner.invoke(app, ["proposal", "finalize", "PROP-001", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert "Managed proposal branch finalized" in result.output
    assert "proposal: PROP-001" in result.output
    assert "cleanup: disabled" in result.output
    assert _git(tmp_path, "branch", "--show-current").stdout.strip() == "main"
    assert _git(tmp_path, "log", "-1", "--pretty=%s").stdout.strip() == "P2P proposal finalize PROP-001"
    assert "refs/heads/main" in _git(tmp_path, "ls-remote", "--heads", "origin", "main").stdout
    branch_metadata = tmp_path / ".p2p" / "proposals" / "PROP-001-chiusura-magnetica" / "branch.yml"
    data = yaml.safe_load(branch_metadata.read_text(encoding="utf-8"))
    assert data["status"] == "finalized"
    assert data["merge"]["pushed"] is True
    assert data["merge"]["cleanup"] is False
    assert data["finalize"]["base_branch"] == "main"
    assert data["finalize"]["cleanup"] is False


def test_cli_proposal_cleanup_deletes_local_and_remote_branch(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Chiusura Magnetica", "--root", str(tmp_path)])
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    remote_path = tmp_path.parent / f"{tmp_path.name}.git"
    _git(tmp_path, "init", "--bare", str(remote_path))
    _git(tmp_path, "remote", "add", "origin", str(remote_path))
    runner.invoke(app, ["project", "remote", "configure", "--mode", "remote", "--provider", "generic", "--root", str(tmp_path)])
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline")
    _git(tmp_path, "branch", "-M", "main")
    runner.invoke(app, ["proposal", "branch", "PROP-001", "--actor", "lorenzo", "--root", str(tmp_path)])
    branch_name = _git(tmp_path, "branch", "--show-current").stdout.strip()
    proposal_path = tmp_path / ".p2p" / "proposals" / "PROP-001-chiusura-magnetica" / "proposal.md"
    proposal_path.write_text(proposal_path.read_text(encoding="utf-8") + "\nBranch refinement.\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "refine proposal")
    runner.invoke(app, ["proposal", "publish", "PROP-001", "--root", str(tmp_path)])
    assert branch_name in _git(tmp_path, "ls-remote", "--heads", "origin", branch_name).stdout
    _git(tmp_path, "checkout", "main")
    runner.invoke(app, ["proposal", "merge", "PROP-001", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "finalize", "PROP-001", "--root", str(tmp_path)])

    result = runner.invoke(app, ["proposal", "cleanup", "PROP-001", "--delete-remote", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert "Managed proposal branch cleaned" in result.output
    assert "local_deleted: true" in result.output
    assert "remote_deleted: true" in result.output
    assert _git(tmp_path, "log", "-1", "--pretty=%s").stdout.strip() == "P2P proposal cleanup PROP-001"
    assert branch_name not in _git(tmp_path, "branch", "--list", branch_name).stdout
    assert branch_name not in _git(tmp_path, "ls-remote", "--heads", "origin", branch_name).stdout
    branch_metadata = tmp_path / ".p2p" / "proposals" / "PROP-001-chiusura-magnetica" / "branch.yml"
    data = yaml.safe_load(branch_metadata.read_text(encoding="utf-8"))
    assert data["status"] == "cleaned"
    assert data["cleanup"]["previous_status"] == "finalized"
    assert data["cleanup"]["local_deleted"] is True
    assert data["cleanup"]["remote_deleted"] is True


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
    runner.invoke(app, ["init", "Demo Project", "--domain", "software", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "Security Model",
            "--problem",
            "Security and privacy need explicit permission boundaries.",
            "--proposal",
            "Define auth, sandbox permissions, and privacy expectations.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(app, ["proposal", "accept", "PROP-001", "--reason", "Needed.", "--root", str(tmp_path)])

    result = runner.invoke(app, ["project", "rubrics", "show", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert "domain: software" in result.output
    assert "security_privacy" in result.output

    result = runner.invoke(app, ["assess", "maturity", "refresh", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert "Project definition maturity refreshed" in result.output
    assert "security_privacy  covered  100/100" in result.output
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


def test_cli_init_without_name_runs_guided_wizard(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["init", "--root", str(tmp_path)],
        input="Wizard Project\ncodex\ncloud\nsoftware\nn\ny\n",
    )

    assert result.exit_code == 0
    assert "P2P project initialization" in result.output
    assert "P2P workspace initialized" in result.output
    assert "MCP setup hint" in result.output
    assert "codex mcp add" in result.output
    assert "Domain template" in result.output
    assert "Customize rubric criteria" in result.output
    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / ".codex" / "skills" / "p2p-project" / "SKILL.md").exists()


def test_cli_init_guided_wizard_uses_detected_agent_as_default(
    tmp_path: Path,
) -> None:
    result = runner.invoke(
        app,
        ["init", "--root", str(tmp_path)],
        input="Wizard Project\n\nlocal\nnone\nn\n",
        env={"P2P_CURRENT_AGENT": "codex"},
    )

    assert result.exit_code == 0
    assert "Detected current client: codex" in result.output
    assert "Installed adapters: generic, codex" in result.output
    assert (tmp_path / ".codex" / "skills" / "p2p-project" / "SKILL.md").exists()
    assert not (tmp_path / "CLAUDE.md").exists()


def test_cli_init_guided_wizard_keeps_all_available_with_footprint_warning(
    tmp_path: Path,
) -> None:
    result = runner.invoke(
        app,
        ["init", "--root", str(tmp_path)],
        input="Wizard Project\nall\nlocal\nnone\nn\n",
        env={"P2P_CURRENT_AGENT": "codex"},
    )

    assert result.exit_code == 0
    assert "all installs every built-in adapter integration" in result.output
    assert "Installed adapters: generic, codex, claude, cursor, copilot, gemini, opencode" in result.output
    assert (tmp_path / "CLAUDE.md").exists()


def test_cli_init_mcp_hint_uses_root_aware_project_python_command(tmp_path: Path) -> None:
    root = tmp_path / "Project With Spaces & Symbols"
    result = runner.invoke(app, ["init", "Demo Project", "--mcp-hint", "--root", str(root)])

    assert result.exit_code == 0
    assert "MCP setup" in result.output
    assert "governed P2P decision root" in result.output
    assert "codex mcp add" in result.output
    assert ".venv/bin/python" in result.output
    assert "p2p_engine.mcp.server" in result.output
    assert "p2p-mcp-server" in result.output
    assert "Project With" in result.output
    assert "Spaces" in result.output
    assert "Symbols" in result.output


def test_cli_init_prints_repository_hygiene_summary(tmp_path: Path) -> None:
    result = runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert "Repository hygiene" in result.output
    assert "status: applied" in result.output
    assert "path: .gitignore" in result.output
    assert (tmp_path / ".gitignore").exists()


def test_cli_init_guided_wizard_can_disable_rubric_criteria(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["init", "--root", str(tmp_path)],
        input=(
            "Wizard Project\n"
            "generic\n"
            "local\n"
            "generic\n"
            "y\n"
            "y\n"
            "n\n"
            "y\n"
            "y\n"
            "y\n"
            "n\n"
        ),
    )

    assert result.exit_code == 0
    rubrics = yaml.safe_load(
        (tmp_path / ".p2p" / "project" / "rubrics.yml").read_text(encoding="utf-8")
    )
    criteria = {item["id"]: item["enabled"] for item in rubrics["criteria"]}
    assert criteria["problem_definition"] is True
    assert criteria["scope_boundaries"] is False
    assert criteria["requirements"] is True
    project = (tmp_path / ".p2p" / "project.yml").read_text(encoding="utf-8")
    assert "name: Wizard Project" in project
    assert "mode: local" in project


def test_cli_init_can_generate_agent_specific_instructions(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "init",
            "Demo Project",
            "--agent",
            "codex",
            "--repository",
            "cloud",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / ".codex" / "skills" / "p2p-project" / "SKILL.md").exists()

    policy = (tmp_path / ".p2p" / "agent-policy.yml").read_text(encoding="utf-8")
    assert "missing_primitive_behavior: stop_and_report" in policy
    assert "runtime_bootstrap:" in policy
    assert "python -m p2p_engine" in policy
    assert "direct_p2p_file_edits: forbidden" in policy
    assert "read_before_explaining: true" in policy
    assert "mode: cloud" in policy


def test_cli_init_without_detection_falls_back_to_all_agent_integrations(tmp_path: Path) -> None:
    result = runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert "Could not reliably detect the current agent" in result.output
    assert "Installed adapters: generic, codex, claude, cursor, copilot, gemini, opencode" in result.output
    assert "p2p agent uninstall <adapter>" in result.output
    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / ".agents" / "skills" / "p2p-project" / "SKILL.md").exists()
    assert (tmp_path / ".codex" / "skills" / "p2p-project" / "SKILL.md").exists()
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
    assert registry["schema_version"] == 1
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
    assert (tmp_path / ".codex" / "skills" / "p2p-project" / "SKILL.md").exists()
    assert not (tmp_path / "CLAUDE.md").exists()
    registry = yaml.safe_load((tmp_path / ".p2p" / "agent-integrations.yml").read_text(encoding="utf-8"))
    assert set(registry["adapters"]) == {"generic", "codex"}


def test_cli_init_narrow_agent_still_includes_generic(tmp_path: Path) -> None:
    result = runner.invoke(app, ["init", "Demo Project", "--agent", "cursor", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / ".cursor" / "rules" / "p2p.mdc").exists()
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
    assert "AGENTS.md shared=true owner=generic status=missing drift=drifted" in shown.output
    assert "generic: installed=true health=error drift=drifted" in listed.output


def test_cli_doctor_reports_runtime_readiness(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    _git(tmp_path, "init")

    result = runner.invoke(app, ["doctor", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert "P2P doctor" in result.output
    assert "project: true" in result.output
    assert "package_importable: true" in result.output
    assert "python_module_cli: python -m p2p_engine" in result.output
    assert "mcp_server_importable: true" in result.output
    assert "git_repository: true" in result.output
    assert "discovery_order: p2p -> .venv/bin/p2p -> python -m p2p_engine -> MCP" in result.output
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


def test_cli_init_cloud_configures_remote_profile(tmp_path: Path) -> None:
    _git(tmp_path, "init")
    remote_url = "git@github.com:example/scatola-perfetta.git"
    _git(tmp_path, "remote", "add", "origin", remote_url)

    result = runner.invoke(
        app,
        [
            "init",
            "Scatola Perfetta",
            "--repository",
            "cloud",
            "--provider",
            "github",
            "--remote",
            "origin",
            "--remote-url",
            remote_url,
            "--root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "Remote profile" in result.output
    assert "provider: github" in result.output
    assert "profile_url: git@github.com:example/scatola-perfetta.git" in result.output
    assert "git_remote_url: git@github.com:example/scatola-perfetta.git" in result.output
    assert "can_sync: true" in result.output

    project = yaml.safe_load((tmp_path / ".p2p" / "project.yml").read_text(encoding="utf-8"))
    assert project["repository"]["mode"] == "cloud"
    assert project["remote"]["mode"] == "remote"
    assert project["remote"]["provider"] == "github"
    assert project["remote"]["remote"] == "origin"
    assert project["remote"]["url"] == remote_url


def test_cli_init_rejects_ambiguous_repository_remote_alias(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["init", "Demo Project", "--repository", "remote", "--root", str(tmp_path)],
    )

    assert result.exit_code == 1
    assert "Repository mode must be local or cloud" in result.output


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
    assert (tmp_path / ".codex" / "skills" / "p2p-project" / "SKILL.md").exists()
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
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert "Decision recorded" in result.output

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

    result = runner.invoke(
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
            "--root",
            str(tmp_path),
        ],
    )

    readiness_path = tmp_path / ".p2p" / "proposals" / "PROP-001-override-readiness" / "readiness.yml"
    readiness = yaml.safe_load(readiness_path.read_text(encoding="utf-8"))["readiness"]

    assert result.exit_code == 0
    assert "Readiness override recorded" in result.output
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

    result = runner.invoke(
        app,
        [
            "proposal",
            "accept",
            "PROP-001",
            "--reason",
            "Ready for implementation.",
            "--approver",
            "owner",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert "Proposal decision recorded" in result.output
    assert "outcome: accepted" in result.output

    result = runner.invoke(
        app,
        [
            "proposal",
            "reject",
            "PROP-002",
            "--reason",
            "Out of scope.",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert "outcome: rejected" in result.output

    result = runner.invoke(
        app,
        [
            "proposal",
            "defer",
            "PROP-003",
            "--reason",
            "Needs more context.",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert "outcome: deferred" in result.output

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
    runner.invoke(
        app,
        [
            "proposal",
            "accept",
            "PROP-001",
            "--reason",
            "Useful for agent skills.",
            "--root",
            str(tmp_path),
        ],
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
            "--option",
            "A",
            "--option",
            "B",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(
        app,
        [
            "choice",
            "decide",
            "CHOICE-001",
            "--option",
            "A",
            "--reason",
            "Pick A.",
            "--root",
            str(tmp_path),
        ],
    )
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
            "Privileges are delegated to Git hosting for now.",
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
            "Build a Git-native CLI foundation.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(
        app,
        [
            "decision",
            "record",
            "PROP-001",
            "--outcome",
            "accepted",
            "--reason",
            "Required for bootstrap.",
            "--root",
            str(tmp_path),
        ],
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
    runner.invoke(
        app,
        [
            "decision",
            "record",
            "PROP-001",
            "--outcome",
            "accepted",
            "--reason",
            "Chosen baseline.",
            "--root",
            str(tmp_path),
        ],
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
        "    relationship: mutually_exclusive\n",
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
    assert result.exit_code == 0
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


def test_cli_change_create_status_and_policy(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Draft Work", "--root", str(tmp_path)])

    result = runner.invoke(
        app,
        ["change", "create", "--from", "PROP-001", "--root", str(tmp_path)],
    )
    assert result.exit_code == 1
    assert "PROP-001 is not accepted yet" in result.output

    runner.invoke(
        app,
        [
            "decision",
            "record",
            "PROP-001",
            "--outcome",
            "accepted",
            "--reason",
            "Ready for operational work.",
            "--root",
            str(tmp_path),
        ],
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
    assert (change_dir / "git-policy.yml").exists()
    change_text = (change_dir / "change.md").read_text(encoding="utf-8")
    assert "implementation_targets:" in change_text
    assert "- local_cli" in change_text
    assert "spec_targets:" in change_text
    assert "- p2p_spec" in change_text
    assert "export_targets:" in change_text
    assert "- openspec" in change_text
    assert "- speckit" in change_text
    assert "operation_level: metadata_only" in (change_dir / "git-policy.yml").read_text(
        encoding="utf-8"
    )

    result = runner.invoke(app, ["change", "status", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "CHANGE-001" in result.output
    assert "proposed" in result.output

    result = runner.invoke(app, ["change", "policy", "CHANGE-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "operation_level: metadata_only" in result.output
    assert "auto_branch: False" in result.output


def test_cli_change_lifecycle_show_and_tasks(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Lifecycle Work", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "decision",
            "record",
            "PROP-001",
            "--outcome",
            "accepted",
            "--reason",
            "Ready for lifecycle tracking.",
            "--root",
            str(tmp_path),
        ],
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
    runner.invoke(
        app,
        [
            "decision",
            "record",
            "PROP-001",
            "--outcome",
            "accepted",
            "--reason",
            "Needed for project navigation.",
            "--root",
            str(tmp_path),
        ],
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
    runner.invoke(
        app,
        [
            "proposal",
            "accept",
            "PROP-001",
            "--reason",
            "Needed before export.",
            "--root",
            str(tmp_path),
        ],
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

    result = runner.invoke(app, ["spec", "status", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "CHANGE-001  generated  Spec Work" in result.output

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
    runner.invoke(app, ["proposal", "accept", "PROP-001", "--reason", "Ready.", "--root", str(tmp_path)])
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
            "Need invisible Git handoff.",
            "--proposal",
            "Create a P2P Work manifest.",
            "--acceptance",
            "Work manifest exists.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(
        app,
        ["proposal", "accept", "PROP-001", "--reason", "Ready for handoff.", "--root", str(tmp_path)],
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
    assert "branch: p2p/work/work-001-change-001-speckit" in result.output

    manifest = tmp_path / ".p2p" / "work" / "WORK-001" / "manifest.yml"
    assert manifest.exists()
    manifest_text = manifest.read_text(encoding="utf-8")
    assert "visibility: internal_git" in manifest_text
    assert "auto_branch: false" in manifest_text
    assert "auto_commit: false" in manifest_text
    assert "auto_merge: false" in manifest_text
    assert "export_validated: true" in manifest_text

    result = runner.invoke(app, ["work", "list", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "WORK-001  planned  CHANGE-001  speckit" in result.output

    result = runner.invoke(app, ["work", "status", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Work status" in result.output
    assert "WORK-001  planned" in result.output
    assert "change: CHANGE-001" in result.output
    assert "branch: p2p/work/work-001-change-001-speckit" in result.output
    assert "next: p2p work branch WORK-001" in result.output

    result = runner.invoke(app, ["work", "show", "WORK-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "WORK-001 - planned" in result.output
    assert "managed_branch_candidate" in result.output


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
            "Retire planned Work without touching Git.",
            "--acceptance",
            "The Work item is marked retired.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(app, ["proposal", "accept", "PROP-001", "--reason", "Ready.", "--root", str(tmp_path)])
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
    assert "Managed work retired" in result.output
    assert "status: retired" in result.output
    assert "git: unchanged" in result.output

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
            "Retire planned Work without touching Git.",
            "--acceptance",
            "The Work item is marked retired.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(app, ["proposal", "accept", "PROP-001", "--reason", "Ready.", "--root", str(tmp_path)])
    runner.invoke(app, ["change", "create", "--from", "PROP-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "refresh", "--change", "CHANGE-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "export", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])
    runner.invoke(app, ["work", "plan", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])

    _git(tmp_path, "init")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "-c", "user.email=test@example.com", "-c", "user.name=Test User", "commit", "-m", "baseline")
    _git(tmp_path, "branch", "-M", "main")
    runner.invoke(app, ["work", "branch", "WORK-001", "--root", str(tmp_path)])

    result = runner.invoke(
        app,
        ["work", "retire", "WORK-001", "--reason", "Obsolete.", "--root", str(tmp_path)],
    )

    assert result.exit_code != 0
    assert "Work item must be planned before retire" in result.output


def test_cli_work_branch_creates_managed_branch(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "Managed Work Branch",
            "--problem",
            "Need an isolated implementation branch.",
            "--proposal",
            "Create a managed branch from a Work manifest.",
            "--acceptance",
            "The Work item is marked branched.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(
        app,
        ["proposal", "accept", "PROP-001", "--reason", "Ready.", "--root", str(tmp_path)],
    )
    runner.invoke(app, ["change", "create", "--from", "PROP-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "refresh", "--change", "CHANGE-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "export", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])
    runner.invoke(app, ["work", "plan", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])

    _git(tmp_path, "init")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "-c", "user.email=test@example.com", "-c", "user.name=Test User", "commit", "-m", "baseline")
    _git(tmp_path, "branch", "-M", "main")

    result = runner.invoke(app, ["work", "branch", "WORK-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Managed work branch created" in result.output
    assert "branch: p2p/work/work-001-change-001-speckit" in result.output
    assert "commits: disabled" in result.output
    assert _git(tmp_path, "branch", "--show-current").stdout.strip() == "p2p/work/work-001-change-001-speckit"

    manifest = tmp_path / ".p2p" / "work" / "WORK-001" / "manifest.yml"
    manifest_text = manifest.read_text(encoding="utf-8")
    assert "status: branched" in manifest_text
    assert "mode: managed_branch" in manifest_text
    assert "current_branch: p2p/work/work-001-change-001-speckit" in manifest_text
    assert "head_commit:" in manifest_text
    assert "base_commit:" in manifest_text


def test_cli_work_branch_requires_clean_worktree(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "Managed Work Branch",
            "--problem",
            "Need an isolated implementation branch.",
            "--proposal",
            "Create a managed branch from a Work manifest.",
            "--acceptance",
            "The Work item is marked branched.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(
        app,
        ["proposal", "accept", "PROP-001", "--reason", "Ready.", "--root", str(tmp_path)],
    )
    runner.invoke(app, ["change", "create", "--from", "PROP-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "refresh", "--change", "CHANGE-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "export", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])
    runner.invoke(app, ["work", "plan", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])

    _git(tmp_path, "init")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "-c", "user.email=test@example.com", "-c", "user.name=Test User", "commit", "-m", "baseline")
    _git(tmp_path, "branch", "-M", "main")
    (tmp_path / "dirty.txt").write_text("uncommitted\n", encoding="utf-8")

    result = runner.invoke(app, ["work", "branch", "WORK-001", "--root", str(tmp_path)])
    assert result.exit_code != 0
    assert "Cannot create managed work branch with uncommitted changes" in result.output
    assert _git(tmp_path, "branch", "--show-current").stdout.strip() == "main"


def test_cli_work_submit_creates_local_commit(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "Managed Work Submit",
            "--problem",
            "Need a local submit commit.",
            "--proposal",
            "Submit managed branch work as a commit.",
            "--acceptance",
            "The Work item is submitted.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(app, ["proposal", "accept", "PROP-001", "--reason", "Ready.", "--root", str(tmp_path)])
    runner.invoke(app, ["change", "create", "--from", "PROP-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "refresh", "--change", "CHANGE-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "export", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])
    runner.invoke(app, ["work", "plan", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])

    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline")
    _git(tmp_path, "branch", "-M", "main")
    runner.invoke(app, ["work", "branch", "WORK-001", "--root", str(tmp_path)])

    feature_file = tmp_path / "feature.txt"
    feature_file.write_text("submitted work\n", encoding="utf-8")

    result = runner.invoke(app, ["work", "submit", "WORK-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Managed work submitted" in result.output
    assert "branch: p2p/work/work-001-change-001-speckit" in result.output
    assert "changed_files: 1" in result.output
    assert "feature.txt" in result.output
    assert "push: disabled" in result.output

    manifest = tmp_path / ".p2p" / "work" / "WORK-001" / "manifest.yml"
    manifest_text = manifest.read_text(encoding="utf-8")
    assert "status: submitted" in manifest_text
    assert "mode: managed_submit" in manifest_text
    assert "pushed: false" in manifest_text
    assert "merged: false" in manifest_text
    assert "feature.txt" in manifest_text
    assert _git(tmp_path, "status", "--porcelain").stdout.strip() == ""
    assert _git(tmp_path, "log", "-1", "--pretty=%s").stdout.strip() == "P2P submit WORK-001: CHANGE-001"


def test_cli_work_submit_requires_non_manifest_changes(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "Managed Work Submit",
            "--problem",
            "Need a local submit commit.",
            "--proposal",
            "Submit managed branch work as a commit.",
            "--acceptance",
            "The Work item is submitted.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(app, ["proposal", "accept", "PROP-001", "--reason", "Ready.", "--root", str(tmp_path)])
    runner.invoke(app, ["change", "create", "--from", "PROP-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "refresh", "--change", "CHANGE-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "export", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])
    runner.invoke(app, ["work", "plan", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])

    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline")
    _git(tmp_path, "branch", "-M", "main")
    runner.invoke(app, ["work", "branch", "WORK-001", "--root", str(tmp_path)])

    result = runner.invoke(app, ["work", "submit", "WORK-001", "--root", str(tmp_path)])
    assert result.exit_code != 0
    assert "Cannot submit managed work with only Work manifest changes" in result.output


def test_cli_work_review_requests_local_review(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "Managed Work Review",
            "--problem",
            "Need a local review request.",
            "--proposal",
            "Request owner review for submitted work.",
            "--acceptance",
            "The Work item is review_requested.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(app, ["proposal", "accept", "PROP-001", "--reason", "Ready.", "--root", str(tmp_path)])
    runner.invoke(app, ["change", "create", "--from", "PROP-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "refresh", "--change", "CHANGE-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "export", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])
    runner.invoke(app, ["work", "plan", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])

    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline")
    _git(tmp_path, "branch", "-M", "main")
    runner.invoke(app, ["work", "branch", "WORK-001", "--root", str(tmp_path)])
    (tmp_path / "feature.txt").write_text("submitted work\n", encoding="utf-8")
    runner.invoke(app, ["work", "submit", "WORK-001", "--root", str(tmp_path)])
    review_commit = _git(tmp_path, "rev-parse", "HEAD").stdout.strip()

    result = runner.invoke(app, ["work", "review", "WORK-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Managed work review requested" in result.output
    assert f"review_commit: {review_commit}" in result.output
    assert "pull_request: disabled" in result.output
    assert "merge: owner-controlled" in result.output
    assert _git(tmp_path, "status", "--porcelain").stdout.strip() == ""
    assert _git(tmp_path, "log", "-1", "--pretty=%s").stdout.strip() == "P2P review WORK-001"

    manifest = tmp_path / ".p2p" / "work" / "WORK-001" / "manifest.yml"
    manifest_text = manifest.read_text(encoding="utf-8")
    assert "status: review_requested" in manifest_text
    assert "mode: managed_review" in manifest_text
    assert f"review_commit: {review_commit}" in manifest_text
    assert "pull_request: null" in manifest_text
    assert "merged: false" in manifest_text


def test_cli_work_review_requires_submitted_clean_branch(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "Managed Work Review",
            "--problem",
            "Need a local review request.",
            "--proposal",
            "Request owner review for submitted work.",
            "--acceptance",
            "The Work item is review_requested.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(app, ["proposal", "accept", "PROP-001", "--reason", "Ready.", "--root", str(tmp_path)])
    runner.invoke(app, ["change", "create", "--from", "PROP-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "refresh", "--change", "CHANGE-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "export", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])
    runner.invoke(app, ["work", "plan", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])

    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline")
    _git(tmp_path, "branch", "-M", "main")

    result = runner.invoke(app, ["work", "review", "WORK-001", "--root", str(tmp_path)])
    assert result.exit_code != 0
    assert "Work item must be submitted before review" in result.output

    runner.invoke(app, ["work", "branch", "WORK-001", "--root", str(tmp_path)])
    (tmp_path / "feature.txt").write_text("submitted work\n", encoding="utf-8")
    runner.invoke(app, ["work", "submit", "WORK-001", "--root", str(tmp_path)])
    (tmp_path / "dirty.txt").write_text("dirty\n", encoding="utf-8")

    result = runner.invoke(app, ["work", "review", "WORK-001", "--root", str(tmp_path)])
    assert result.exit_code != 0
    assert "Cannot request managed work review with uncommitted changes" in result.output


def test_cli_work_publish_pushes_reviewed_branch(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "Managed Work Publish",
            "--problem",
            "Need a remote handoff.",
            "--proposal",
            "Publish reviewed work to origin.",
            "--acceptance",
            "The Work branch is pushed.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(app, ["proposal", "accept", "PROP-001", "--reason", "Ready.", "--root", str(tmp_path)])
    runner.invoke(app, ["change", "create", "--from", "PROP-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "refresh", "--change", "CHANGE-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "export", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])
    runner.invoke(app, ["work", "plan", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])

    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline")
    _git(tmp_path, "branch", "-M", "main")
    remote_path = tmp_path.parent / f"{tmp_path.name}.git"
    _git(tmp_path, "init", "--bare", str(remote_path))
    _git(tmp_path, "remote", "add", "origin", str(remote_path))

    runner.invoke(app, ["work", "branch", "WORK-001", "--root", str(tmp_path)])
    (tmp_path / "feature.txt").write_text("published work\n", encoding="utf-8")
    runner.invoke(app, ["work", "submit", "WORK-001", "--root", str(tmp_path)])
    runner.invoke(app, ["work", "review", "WORK-001", "--root", str(tmp_path)])

    result = runner.invoke(app, ["work", "publish", "WORK-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Managed work published" in result.output
    assert "branch: p2p/work/work-001-change-001-speckit" in result.output
    assert "remote: origin" in result.output
    assert "pull_request: disabled" in result.output
    assert "merge: owner-controlled" in result.output
    assert _git(tmp_path, "status", "--porcelain").stdout.strip() == ""
    assert _git(tmp_path, "log", "-1", "--pretty=%s").stdout.strip() == "P2P publish WORK-001"

    remote_branch = _git(
        tmp_path,
        "ls-remote",
        "--heads",
        "origin",
        "p2p/work/work-001-change-001-speckit",
    ).stdout
    assert "refs/heads/p2p/work/work-001-change-001-speckit" in remote_branch

    manifest = tmp_path / ".p2p" / "work" / "WORK-001" / "manifest.yml"
    manifest_text = manifest.read_text(encoding="utf-8")
    assert "status: published" in manifest_text
    assert "mode: managed_publish" in manifest_text
    assert "remote_branch: p2p/work/work-001-change-001-speckit" in manifest_text
    assert "pull_request: null" in manifest_text
    assert "merged: false" in manifest_text


def test_cli_sync_status_reports_local_project_without_remote(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])

    result = runner.invoke(app, ["sync", "status", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert "Sync status" in result.output
    assert "repository: false" in result.output
    assert "mode: local" in result.output
    assert "can_sync: false" in result.output
    assert "not a Git repository" in result.output


def test_cli_sync_status_detects_git_origin_when_p2p_profile_is_local(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    _git(tmp_path, "init")
    _git(tmp_path, "remote", "add", "origin", "git@github.com:example/demo.git")

    result = runner.invoke(app, ["sync", "status", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert "repository: true" in result.output
    assert "mode: local" in result.output
    assert "can_sync: false" in result.output
    assert "project remote profile is local, but Git remote origin exists" in result.output
    normalized_output = result.output.replace("\n", " ")
    assert "p2p project remote configure --mode remote --remote origin" in normalized_output


def test_cli_sync_status_detects_remote_profile_url_mismatch(tmp_path: Path) -> None:
    _git(tmp_path, "init")
    _git(tmp_path, "remote", "add", "origin", "git@github.com:example/git-url.git")
    runner.invoke(
        app,
        [
            "init",
            "Demo Project",
            "--repository",
            "cloud",
            "--provider",
            "github",
            "--remote",
            "origin",
            "--remote-url",
            "git@github.com:example/p2p-url.git",
            "--root",
            str(tmp_path),
        ],
    )

    result = runner.invoke(app, ["sync", "status", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert "profile_url: git@github.com:example/p2p-url.git" in result.output
    assert "remote_url: git@github.com:example/git-url.git" in result.output
    assert "can_sync: false" in result.output
    assert "P2P remote profile URL does not match Git remote origin" in result.output


def test_cli_sync_push_fetch_and_pull_wrap_git_remote(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    _git(tmp_path, "branch", "-M", "main")
    remote_path = tmp_path.parent / f"{tmp_path.name}.git"
    _git(tmp_path, "init", "--bare", str(remote_path))
    _git(tmp_path, "remote", "add", "origin", str(remote_path))
    runner.invoke(
        app,
        [
            "project",
            "remote",
            "configure",
            "--mode",
            "remote",
            "--provider",
            "generic",
            "--remote",
            "origin",
            "--root",
            str(tmp_path),
        ],
    )
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline")

    result = runner.invoke(app, ["sync", "status", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "repository: true" in result.output
    assert "branch: main" in result.output
    assert "clean: true" in result.output
    assert "remote: origin" in result.output
    assert "can_sync: true" in result.output

    result = runner.invoke(app, ["sync", "push", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Sync pushed" in result.output
    assert "action: push" in result.output
    assert "branch: main" in result.output
    assert "refs/heads/main" in _git(tmp_path, "ls-remote", "--heads", "origin", "main").stdout

    clone_path = tmp_path.parent / f"{tmp_path.name}-clone"
    subprocess.run(
        ["git", "clone", "--branch", "main", str(remote_path), str(clone_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    _git(clone_path, "config", "user.email", "test@example.com")
    _git(clone_path, "config", "user.name", "Test User")
    (clone_path / "remote-change.txt").write_text("from remote\n", encoding="utf-8")
    _git(clone_path, "add", ".")
    _git(clone_path, "commit", "-m", "remote change")
    _git(clone_path, "push", "origin", "main")

    result = runner.invoke(app, ["sync", "fetch", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Sync fetched" in result.output

    result = runner.invoke(app, ["sync", "pull", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Sync pulled" in result.output
    assert (tmp_path / "remote-change.txt").read_text(encoding="utf-8") == "from remote\n"


def test_cli_sync_pull_requires_clean_worktree(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    _git(tmp_path, "branch", "-M", "main")
    remote_path = tmp_path.parent / f"{tmp_path.name}.git"
    _git(tmp_path, "init", "--bare", str(remote_path))
    _git(tmp_path, "remote", "add", "origin", str(remote_path))
    runner.invoke(
        app,
        [
            "project",
            "remote",
            "configure",
            "--mode",
            "remote",
            "--provider",
            "generic",
            "--root",
            str(tmp_path),
        ],
    )
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline")
    runner.invoke(app, ["sync", "push", "--root", str(tmp_path)])
    (tmp_path / "dirty.txt").write_text("dirty\n", encoding="utf-8")

    result = runner.invoke(app, ["sync", "pull", "--root", str(tmp_path)])

    assert result.exit_code == 1
    assert "Cannot pull with uncommitted changes" in result.output


def test_cli_work_publish_requires_review_and_remote(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "Managed Work Publish",
            "--problem",
            "Need a remote handoff.",
            "--proposal",
            "Publish reviewed work to origin.",
            "--acceptance",
            "The Work branch is pushed.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(app, ["proposal", "accept", "PROP-001", "--reason", "Ready.", "--root", str(tmp_path)])
    runner.invoke(app, ["change", "create", "--from", "PROP-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "refresh", "--change", "CHANGE-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "export", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])
    runner.invoke(app, ["work", "plan", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])

    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline")
    _git(tmp_path, "branch", "-M", "main")

    result = runner.invoke(app, ["work", "publish", "WORK-001", "--root", str(tmp_path)])
    assert result.exit_code != 0
    assert "Work item must be review_requested before publish" in result.output

    runner.invoke(app, ["work", "branch", "WORK-001", "--root", str(tmp_path)])
    (tmp_path / "feature.txt").write_text("published work\n", encoding="utf-8")
    runner.invoke(app, ["work", "submit", "WORK-001", "--root", str(tmp_path)])
    runner.invoke(app, ["work", "review", "WORK-001", "--root", str(tmp_path)])

    result = runner.invoke(app, ["work", "publish", "WORK-001", "--root", str(tmp_path)])
    assert result.exit_code != 0
    assert "Git remote not found: origin" in result.output


def test_cli_project_remote_configure_and_show(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])

    result = runner.invoke(
        app,
        [
            "project",
            "remote",
            "configure",
            "--mode",
            "remote",
            "--provider",
            "github",
            "--remote",
            "origin",
            "--url",
            "git@github.com:example/demo.git",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert "Project remote profile configured" in result.output
    assert "provider: github" in result.output
    assert "opens_external_request: false" in result.output

    show = runner.invoke(app, ["project", "remote", "show", "--root", str(tmp_path)])
    assert show.exit_code == 0
    assert "mode: remote" in show.output
    assert "provider: github" in show.output
    assert "url: git@github.com:example/demo.git" in show.output

    project_text = (tmp_path / ".p2p" / "project.yml").read_text(encoding="utf-8")
    assert "remote:" in project_text
    assert "provider: github" in project_text
    assert "opens_external_request: false" in project_text


def test_cli_work_request_review_records_provider_handoff(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "Remote Review Request",
            "--problem",
            "Need optional external review handoff.",
            "--proposal",
            "Record provider-agnostic review request metadata.",
            "--acceptance",
            "The Work item keeps published status and records external_review.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(app, ["proposal", "accept", "PROP-001", "--reason", "Ready.", "--root", str(tmp_path)])
    runner.invoke(app, ["change", "create", "--from", "PROP-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "refresh", "--change", "CHANGE-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "export", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])
    runner.invoke(app, ["work", "plan", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])

    runner.invoke(
        app,
        [
            "project",
            "remote",
            "configure",
            "--mode",
            "remote",
            "--provider",
            "github",
            "--url",
            "git@github.com:example/demo.git",
            "--root",
            str(tmp_path),
        ],
    )
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline")
    _git(tmp_path, "branch", "-M", "main")
    remote_path = tmp_path.parent / f"{tmp_path.name}.git"
    _git(tmp_path, "init", "--bare", str(remote_path))
    _git(tmp_path, "remote", "add", "origin", str(remote_path))

    runner.invoke(app, ["work", "branch", "WORK-001", "--root", str(tmp_path)])
    (tmp_path / "feature.txt").write_text("published work\n", encoding="utf-8")
    runner.invoke(app, ["work", "submit", "WORK-001", "--root", str(tmp_path)])
    runner.invoke(app, ["work", "review", "WORK-001", "--root", str(tmp_path)])
    runner.invoke(app, ["work", "publish", "WORK-001", "--root", str(tmp_path)])

    result = runner.invoke(app, ["work", "request-review", "WORK-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "External review request recorded" in result.output
    assert "provider: github" in result.output
    assert "opens_external_request: false" in result.output
    assert "https://github.com/example/demo/compare/p2p/work/work-001-change-001-speckit" in result.output
    assert _git(tmp_path, "status", "--porcelain").stdout.strip() == ""
    assert _git(tmp_path, "log", "-1", "--pretty=%s").stdout.strip() == "P2P request review WORK-001"

    manifest = tmp_path / ".p2p" / "work" / "WORK-001" / "manifest.yml"
    manifest_text = manifest.read_text(encoding="utf-8")
    assert "status: published" in manifest_text
    assert "external_review:" in manifest_text
    assert "provider: github" in manifest_text
    assert "opens_external_request: false" in manifest_text


def test_cli_work_accept_merges_published_branch(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "Managed Work Accept",
            "--problem",
            "Need owner-controlled merge.",
            "--proposal",
            "Accept published work locally.",
            "--acceptance",
            "The Work branch is merged into main.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(app, ["proposal", "accept", "PROP-001", "--reason", "Ready.", "--root", str(tmp_path)])
    runner.invoke(app, ["change", "create", "--from", "PROP-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "refresh", "--change", "CHANGE-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "export", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])
    runner.invoke(app, ["work", "plan", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])

    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline")
    _git(tmp_path, "branch", "-M", "main")
    remote_path = tmp_path.parent / f"{tmp_path.name}.git"
    _git(tmp_path, "init", "--bare", str(remote_path))
    _git(tmp_path, "remote", "add", "origin", str(remote_path))

    runner.invoke(app, ["work", "branch", "WORK-001", "--root", str(tmp_path)])
    (tmp_path / "feature.txt").write_text("accepted work\n", encoding="utf-8")
    runner.invoke(app, ["work", "submit", "WORK-001", "--root", str(tmp_path)])
    runner.invoke(app, ["work", "review", "WORK-001", "--root", str(tmp_path)])
    runner.invoke(app, ["work", "publish", "WORK-001", "--root", str(tmp_path)])
    _git(tmp_path, "checkout", "main")

    result = runner.invoke(app, ["work", "accept", "WORK-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Managed work accepted" in result.output
    assert "source_branch: p2p/work/work-001-change-001-speckit" in result.output
    assert "merged_into: main" in result.output
    assert "push: disabled" in result.output
    assert "cleanup: disabled" in result.output
    assert _git(tmp_path, "branch", "--show-current").stdout.strip() == "main"
    assert _git(tmp_path, "status", "--porcelain").stdout.strip() == ""
    assert _git(tmp_path, "log", "-1", "--pretty=%s").stdout.strip() == "P2P accept WORK-001"
    assert (tmp_path / "feature.txt").read_text(encoding="utf-8") == "accepted work\n"

    manifest = tmp_path / ".p2p" / "work" / "WORK-001" / "manifest.yml"
    manifest_text = manifest.read_text(encoding="utf-8")
    assert "status: accepted" in manifest_text
    assert "mode: managed_accept" in manifest_text
    assert "source_branch: p2p/work/work-001-change-001-speckit" in manifest_text
    assert "merged_into: main" in manifest_text
    assert "pushed: false" in manifest_text
    assert "cleanup: false" in manifest_text

    result = runner.invoke(app, ["work", "status", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "WORK-001  accepted" in result.output
    assert "base: main" in result.output
    assert "remote: origin" in result.output
    assert "next: p2p work finalize WORK-001" in result.output

    result = runner.invoke(app, ["work", "finalize", "WORK-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Managed work finalized" in result.output
    assert "base_branch: main" in result.output
    assert "remote: origin" in result.output
    assert "cleanup: disabled" in result.output
    assert _git(tmp_path, "status", "--porcelain").stdout.strip() == ""
    assert _git(tmp_path, "log", "-1", "--pretty=%s").stdout.strip() == "P2P finalize WORK-001"
    remote_main = _git(tmp_path, "ls-remote", "--heads", "origin", "main").stdout
    assert "refs/heads/main" in remote_main

    manifest_text = manifest.read_text(encoding="utf-8")
    assert "status: finalized" in manifest_text
    assert "mode: managed_finalize" in manifest_text
    assert "base_branch: main" in manifest_text
    assert "cleanup: false" in manifest_text

    result = runner.invoke(app, ["work", "status", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "WORK-001  finalized" in result.output
    assert "next: p2p work cleanup WORK-001" in result.output

    result = runner.invoke(app, ["work", "cleanup", "WORK-001", "--remote", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Managed work cleaned" in result.output
    assert "local_deleted: true" in result.output
    assert "remote_deleted: true" in result.output
    assert _git(tmp_path, "status", "--porcelain").stdout.strip() == ""
    assert _git(tmp_path, "log", "-1", "--pretty=%s").stdout.strip() == "P2P cleanup WORK-001"
    assert _git(tmp_path, "branch", "--list", "p2p/work/work-001-change-001-speckit").stdout.strip() == ""
    remote_work_branch = _git(
        tmp_path,
        "ls-remote",
        "--heads",
        "origin",
        "p2p/work/work-001-change-001-speckit",
    ).stdout
    assert remote_work_branch.strip() == ""
    assert "status: cleaned" in manifest.read_text(encoding="utf-8")


def test_cli_work_accept_requires_published_base_branch(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "Managed Work Accept",
            "--problem",
            "Need owner-controlled merge.",
            "--proposal",
            "Accept published work locally.",
            "--acceptance",
            "The Work branch is merged into main.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(app, ["proposal", "accept", "PROP-001", "--reason", "Ready.", "--root", str(tmp_path)])
    runner.invoke(app, ["change", "create", "--from", "PROP-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "refresh", "--change", "CHANGE-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "export", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])
    runner.invoke(app, ["work", "plan", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])

    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline")
    _git(tmp_path, "branch", "-M", "main")
    runner.invoke(app, ["work", "branch", "WORK-001", "--root", str(tmp_path)])
    (tmp_path / "feature.txt").write_text("reviewed work\n", encoding="utf-8")
    runner.invoke(app, ["work", "submit", "WORK-001", "--root", str(tmp_path)])
    runner.invoke(app, ["work", "review", "WORK-001", "--root", str(tmp_path)])

    result = runner.invoke(app, ["work", "accept", "WORK-001", "--root", str(tmp_path)])
    assert result.exit_code != 0
    assert "expected base branch main" in result.output

    _git(tmp_path, "checkout", "main")
    result = runner.invoke(app, ["work", "accept", "WORK-001", "--root", str(tmp_path)])
    assert result.exit_code != 0
    assert "Work item must be published before accept" in result.output


def test_cli_work_finalize_requires_accepted_and_remote(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "Managed Work Finalize",
            "--problem",
            "Need base branch push.",
            "--proposal",
            "Finalize accepted work.",
            "--acceptance",
            "The base branch is pushed.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(app, ["proposal", "accept", "PROP-001", "--reason", "Ready.", "--root", str(tmp_path)])
    runner.invoke(app, ["change", "create", "--from", "PROP-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "refresh", "--change", "CHANGE-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "export", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])
    runner.invoke(app, ["work", "plan", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])

    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline")
    _git(tmp_path, "branch", "-M", "main")

    result = runner.invoke(app, ["work", "finalize", "WORK-001", "--root", str(tmp_path)])
    assert result.exit_code != 0
    assert "Work item must be accepted before finalize" in result.output

    runner.invoke(app, ["work", "branch", "WORK-001", "--root", str(tmp_path)])
    (tmp_path / "feature.txt").write_text("accepted work\n", encoding="utf-8")
    runner.invoke(app, ["work", "submit", "WORK-001", "--root", str(tmp_path)])
    runner.invoke(app, ["work", "review", "WORK-001", "--root", str(tmp_path)])
    remote_path = tmp_path.parent / f"{tmp_path.name}.git"
    _git(tmp_path, "init", "--bare", str(remote_path))
    _git(tmp_path, "remote", "add", "origin", str(remote_path))
    runner.invoke(app, ["work", "publish", "WORK-001", "--root", str(tmp_path)])
    _git(tmp_path, "checkout", "main")
    runner.invoke(app, ["work", "accept", "WORK-001", "--root", str(tmp_path)])
    _git(tmp_path, "remote", "remove", "origin")

    result = runner.invoke(app, ["work", "finalize", "WORK-001", "--root", str(tmp_path)])
    assert result.exit_code != 0
    assert "Git remote not found: origin" in result.output


def test_cli_work_cleanup_requires_finalized_branch(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "Managed Work Cleanup",
            "--problem",
            "Need branch cleanup.",
            "--proposal",
            "Cleanup finalized work.",
            "--acceptance",
            "The Work branch is deleted.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(app, ["proposal", "accept", "PROP-001", "--reason", "Ready.", "--root", str(tmp_path)])
    runner.invoke(app, ["change", "create", "--from", "PROP-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "refresh", "--change", "CHANGE-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "export", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])
    runner.invoke(app, ["work", "plan", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])

    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline")
    _git(tmp_path, "branch", "-M", "main")

    result = runner.invoke(app, ["work", "cleanup", "WORK-001", "--root", str(tmp_path)])
    assert result.exit_code != 0
    assert "Work item must be finalized before cleanup" in result.output


def test_cli_work_accept_conflict_continue_and_abort(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "Managed Work Conflict",
            "--problem",
            "Need guided merge conflict recovery.",
            "--proposal",
            "Mark conflicts and support continue/abort.",
            "--acceptance",
            "The Work item records merge_conflict.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(app, ["proposal", "accept", "PROP-001", "--reason", "Ready.", "--root", str(tmp_path)])
    runner.invoke(app, ["change", "create", "--from", "PROP-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "refresh", "--change", "CHANGE-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "export", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])
    runner.invoke(app, ["work", "plan", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])

    conflict_file = tmp_path / "conflict.txt"
    conflict_file.write_text("base\n", encoding="utf-8")
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline")
    _git(tmp_path, "branch", "-M", "main")
    remote_path = tmp_path.parent / f"{tmp_path.name}.git"
    _git(tmp_path, "init", "--bare", str(remote_path))
    _git(tmp_path, "remote", "add", "origin", str(remote_path))

    runner.invoke(app, ["work", "branch", "WORK-001", "--root", str(tmp_path)])
    conflict_file.write_text("work branch\n", encoding="utf-8")
    runner.invoke(app, ["work", "submit", "WORK-001", "--root", str(tmp_path)])
    runner.invoke(app, ["work", "review", "WORK-001", "--root", str(tmp_path)])
    runner.invoke(app, ["work", "publish", "WORK-001", "--root", str(tmp_path)])

    _git(tmp_path, "checkout", "main")
    conflict_file.write_text("main branch\n", encoding="utf-8")
    _git(tmp_path, "add", "conflict.txt")
    _git(tmp_path, "commit", "-m", "main conflict")

    result = runner.invoke(app, ["work", "accept", "WORK-001", "--root", str(tmp_path)])
    assert result.exit_code != 0
    assert "Managed work accept blocked by merge conflicts" in result.output
    assert "conflict.txt" in result.output
    assert "p2p work accept --continue WORK-001" in result.output
    manifest = tmp_path / ".p2p" / "work" / "WORK-001" / "manifest.yml"
    manifest_text = manifest.read_text(encoding="utf-8")
    assert "status: merge_conflict" in manifest_text
    assert "conflicted_files:" in manifest_text

    result = runner.invoke(app, ["work", "accept", "--abort", "WORK-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Managed work accept aborted" in result.output
    assert _git(tmp_path, "status", "--porcelain").stdout.strip() == ""
    assert _git(tmp_path, "log", "-1", "--pretty=%s").stdout.strip() == "P2P abort accept WORK-001"
    assert "status: published" in manifest.read_text(encoding="utf-8")

    result = runner.invoke(app, ["work", "accept", "WORK-001", "--root", str(tmp_path)])
    assert result.exit_code != 0
    assert "Managed work accept blocked by merge conflicts" in result.output

    result = runner.invoke(app, ["work", "accept", "--continue", "WORK-001", "--root", str(tmp_path)])
    assert result.exit_code != 0
    assert "unresolved conflicts:" in result.output
    assert "conflict.txt" in result.output

    conflict_file.write_text("resolved\n", encoding="utf-8")
    result = runner.invoke(app, ["work", "accept", "--continue", "WORK-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Managed work accepted" in result.output
    assert _git(tmp_path, "status", "--porcelain").stdout.strip() == ""
    assert _git(tmp_path, "log", "-1", "--pretty=%s").stdout.strip() == "P2P accept WORK-001"
    assert "status: accepted" in manifest.read_text(encoding="utf-8")


def test_cli_work_scan_reads_local_branch_without_checkout(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    _git(tmp_path, "init")
    _git(tmp_path, "add", ".p2p/project.yml")
    _git(tmp_path, "-c", "user.email=test@example.com", "-c", "user.name=Test User", "commit", "-m", "init")
    _git(tmp_path, "branch", "-M", "main")

    _git(tmp_path, "checkout", "-b", "p2p/work/work-999-change-001-speckit")
    manifest_dir = tmp_path / ".p2p" / "work" / "WORK-999"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "manifest.yml").write_text(
        "work_id: WORK-999\n"
        "status: planned\n"
        "source:\n"
        "  change: CHANGE-001\n"
        "handoff:\n"
        "  target: speckit\n"
        "git:\n"
        "  branch_name: p2p/work/work-999-change-001-speckit\n",
        encoding="utf-8",
    )
    _git(tmp_path, "add", ".p2p/work/WORK-999/manifest.yml")
    _git(
        tmp_path,
        "-c",
        "user.email=test@example.com",
        "-c",
        "user.name=Test User",
        "commit",
        "-m",
        "add work manifest",
    )
    _git(tmp_path, "checkout", "main")

    result = runner.invoke(app, ["work", "scan", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "branches: 1" in result.output
    assert "work_items: 1" in result.output
    assert "WORK-999  planned  CHANGE-001  speckit  p2p/work/work-999-change-001-speckit" in result.output

    work_registry = tmp_path / ".p2p" / "registries" / "work.yml"
    assert work_registry.exists()
    registry_text = work_registry.read_text(encoding="utf-8")
    assert "WORK-999" in registry_text
    assert "p2p/work/work-999-change-001-speckit" in registry_text

    result = runner.invoke(app, ["work", "list", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "WORK-999  planned  CHANGE-001  speckit" in result.output


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
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert "Choice decided" in result.output
    assert "selected: C - Prompt-only first, AI adapter later" in result.output

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


def test_cli_choice_discovery_blocking_and_next_integration(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--domain", "software", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Governance Model", "--root", str(tmp_path)])
    runner.invoke(app, ["vote", "record", "PROP-001", "--choice", "A", "--reason", "Prefer A", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "accept", "PROP-001", "--reason", "Needed.", "--root", str(tmp_path)])
    runner.invoke(app, ["change", "create", "--from", "PROP-001", "--title", "Governance Model", "--root", str(tmp_path)])
    runner.invoke(app, ["change", "set-status", "CHANGE-001", "planned", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "choice",
            "create",
            "--title",
            "Governance Scope",
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
    result = runner.invoke(app, ["next", "--top", "1", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "continue_change" in result.output
    assert "target: CHANGE-001" in result.output


def test_cli_intake_prompt_import_and_status(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "CLI Foundation", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "decision",
            "record",
            "PROP-001",
            "--outcome",
            "accepted",
            "--reason",
            "Baseline CLI work.",
            "--root",
            str(tmp_path),
        ],
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
        "    relationship: alternative_to\n"
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
    runner.invoke(
        app,
        [
            "proposal",
            "accept",
            "PROP-001",
            "--reason",
            "Baseline CLI work.",
            "--root",
            str(tmp_path),
        ],
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

    result = runner.invoke(app, ["next", "--top", "1", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "NEXT-001  high  create_change" in result.output

    result = runner.invoke(app, ["project", "status", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "operational:" in result.output
    assert "brief: available" in result.output
    assert "next actions: 2" in result.output
    assert "first next: NEXT-001 high create_change PROP-001" in result.output


def test_cli_next_falls_back_without_imported_next_actions(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--domain", "software", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Managed Git", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "accept",
            "PROP-001",
            "--reason",
            "Needed for collaboration.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(
        app,
        ["change", "create", "--from", "PROP-001", "--title", "Managed Git", "--root", str(tmp_path)],
    )
    runner.invoke(app, ["change", "set-status", "CHANGE-001", "planned", "--root", str(tmp_path)])

    result = runner.invoke(app, ["next", "--top", "1", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "NEXT-FALLBACK-001  high  refresh_registry" in result.output
    assert "p2p registry refresh" in result.output

    runner.invoke(app, ["registry", "refresh", "--root", str(tmp_path)])
    result = runner.invoke(app, ["next", "--top", "1", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "NEXT-FALLBACK-001  high  continue_change" in result.output
    assert "target: CHANGE-001" in result.output
    assert "p2p change tasks CHANGE-001" in result.output
    assert "source: generated" in result.output


def test_cli_next_falls_back_to_draft_proposal_review(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--domain", "software", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Draft Work", "--root", str(tmp_path)])
    runner.invoke(app, ["registry", "refresh", "--root", str(tmp_path)])

    result = runner.invoke(app, ["next", "--top", "1", "--root", str(tmp_path)])

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

    result = runner.invoke(app, ["next", "--top", "1", "--root", str(tmp_path)])

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
