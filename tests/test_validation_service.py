import shutil
from pathlib import Path

import pytest
import yaml

from p2p_engine.services.permissions import PermissionsService
from p2p_engine.services.proposals import ProposalDocumentService
from p2p_engine.services.validation import ValidationService
from p2p_engine.storage.filesystem import P2PWorkspace


def _validation_service(workspace: P2PWorkspace) -> ValidationService:
    proposal_documents = ProposalDocumentService(root=workspace.root, p2p_dir=workspace.p2p_dir)
    permissions = PermissionsService(root=workspace.root, p2p_dir=workspace.p2p_dir)
    return ValidationService(
        root=workspace.root,
        p2p_dir=workspace.p2p_dir,
        duplicate_proposal_ids=proposal_documents.duplicate_ids,
        registry_status=workspace.registry_status,
        agent_integrations_path=workspace._agent_instruction_service().path,
        permissions_path=permissions.path,
        interaction_style_validation_findings=workspace._project_interaction_style_service().validation_findings,
        governance_validation_findings=workspace._governance_policy_service().validation_findings,
    )


def _codes(result) -> set[str]:
    return {finding.code for finding in result.findings}


def _agent_registry(workspace: P2PWorkspace) -> dict[str, object]:
    return yaml.safe_load(workspace._agent_instruction_service().path().read_text(encoding="utf-8"))


def _write_agent_registry(workspace: P2PWorkspace, payload: dict[str, object]) -> None:
    workspace._agent_instruction_service().write_registry(payload)


def _agent_integration_finding(result):
    return next(finding for finding in result.findings if finding.code == "P2P240_INVALID_AGENT_INTEGRATIONS")


def test_validation_service_accepts_valid_refreshed_project(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Demo Project", agent_profile="all")
    workspace.refresh_registries()

    result = _validation_service(workspace).validate()

    assert result.ok is True
    assert result.errors == 0
    assert result.warnings == 0


def test_validation_service_rejects_missing_runtime_without_marker(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Legacy Project")
    (tmp_path / ".p2p" / "project" / "runtime.yml").unlink()
    project_path = tmp_path / ".p2p" / "project.yml"
    project = yaml.safe_load(project_path.read_text(encoding="utf-8"))
    project.pop("runtime_contract")
    project_path.write_text(yaml.safe_dump(project, sort_keys=False), encoding="utf-8")

    result = _validation_service(workspace).validate()
    finding = next(finding for finding in result.findings if finding.code == "P2P266_RUNTIME_CONTRACT_MISSING")

    assert result.ok is False
    assert finding.severity == "error"


def test_validation_service_reports_missing_required_runtime_contract(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Missing Runtime Project")
    (tmp_path / ".p2p" / "project" / "runtime.yml").unlink()

    result = _validation_service(workspace).validate()
    finding = next(finding for finding in result.findings if finding.code == "P2P266_RUNTIME_CONTRACT_MISSING")

    assert result.ok is False
    assert finding.severity == "error"


def test_validation_service_reports_runtime_setup_guide_drift(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Runtime Setup Drift")
    setup_path = tmp_path / "P2P-SETUP.md"
    setup_path.write_text(setup_path.read_text(encoding="utf-8") + "manual edit\n", encoding="utf-8")

    result = _validation_service(workspace).validate()

    assert "P2P268_RUNTIME_SETUP_GUIDE_DRIFT" in _codes(result)


def test_validation_service_reports_governance_policy_artifact_errors(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Demo Project")
    (tmp_path / ".p2p" / "governance" / "governance.yml").write_text(
        "governance:\n  mode: unknown\n",
        encoding="utf-8",
    )
    (tmp_path / ".p2p" / "governance" / "decision-precedents.yml").write_text(
        "precedents:\n  - id: DP001\n  - id: DP001\n",
        encoding="utf-8",
    )

    result = _validation_service(workspace).validate()

    assert result.ok is False
    assert {"P2P250_INVALID_GOVERNANCE_MODE", "P2P252_DUPLICATE_DECISION_PRECEDENT"} <= _codes(result)


def test_validation_service_allows_missing_optional_governance_artifacts(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Demo Project")
    shutil.rmtree(tmp_path / ".p2p" / "governance", ignore_errors=True)
    workspace.refresh_registries()

    result = _validation_service(workspace).validate()

    assert "P2P250_INVALID_GOVERNANCE_MODE" not in _codes(result)
    assert "P2P252_INVALID_DECISION_PRECEDENTS" not in _codes(result)


@pytest.mark.parametrize(
    ("mutate", "expected_message"),
    [
        (
            lambda registry: registry["adapters"].pop("generic"),
            "must include generic adapter",
        ),
        (
            lambda registry: registry.__setitem__("active_agent", "codex"),
            "must not define active_agent",
        ),
        (
            lambda registry: registry["adapters"].__setitem__("unknown", {"status": "installed", "files": []}),
            "Unknown agent adapter: unknown",
        ),
        (
            lambda registry: registry["adapters"]["generic"].pop("template_version"),
            "Agent adapter record missing template_version",
        ),
        (
            lambda registry: registry["adapters"]["generic"]["files"][0].__setitem__("path", "/tmp/AGENTS.md"),
            "Agent adapter file path must be relative",
        ),
        (
            lambda registry: registry["adapters"]["generic"]["files"][0].__setitem__("path", "../AGENTS.md"),
            "Agent adapter file path must not escape project root",
        ),
        (
            lambda registry: registry["adapters"]["generic"]["files"][0].__setitem__("sha256", "not-a-sha"),
            "Invalid SHA-256",
        ),
        (
            lambda registry: registry["adapters"]["generic"]["files"][0].__setitem__("drift", "surprising"),
            "Invalid drift state",
        ),
        (
            lambda registry: registry["adapters"]["codex"]["files"][0].__setitem__("shared", False),
            "Duplicate agent file path has incompatible ownership",
        ),
    ],
)
def test_validation_service_reports_semantic_agent_registry_errors(
    tmp_path: Path,
    mutate,
    expected_message: str,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Demo Project", agent_profile="all")
    registry = _agent_registry(workspace)
    mutate(registry)
    _write_agent_registry(workspace, registry)

    result = _validation_service(workspace).validate()
    finding = _agent_integration_finding(result)

    assert result.ok is False
    assert finding.severity == "error"
    assert expected_message in finding.message


def test_validation_service_reports_missing_agent_registry_file(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Demo Project", agent_profile="generic")
    (tmp_path / "AGENTS.md").unlink()

    result = _validation_service(workspace).validate()
    finding = _agent_integration_finding(result)

    assert result.ok is False
    assert "Managed agent file is missing: AGENTS.md" in finding.message


def test_validation_service_reports_agent_registry_hash_mismatch(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Demo Project", agent_profile="generic")
    agents = tmp_path / "AGENTS.md"
    agents.write_text(agents.read_text(encoding="utf-8") + "\nmanual edit\n", encoding="utf-8")

    result = _validation_service(workspace).validate()
    finding = _agent_integration_finding(result)

    assert result.ok is False
    assert "Managed agent file hash mismatch: AGENTS.md" in finding.message


def test_validation_service_reports_invalid_yaml(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Demo Project")
    (tmp_path / ".p2p" / "project.yml").write_text("project: [\n", encoding="utf-8")

    result = _validation_service(workspace).validate()

    assert result.ok is False
    assert "P2P010_INVALID_YAML" in _codes(result)


def test_validation_service_reports_invalid_permissions_and_consent(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Demo Project")
    permissions_path = PermissionsService(root=workspace.root, p2p_dir=workspace.p2p_dir).path()
    permissions = yaml.safe_load(permissions_path.read_text(encoding="utf-8"))
    permissions["identities"]["owner"]["role"] = "invalid-role"
    permissions_path.write_text(yaml.safe_dump(permissions, sort_keys=False), encoding="utf-8")
    consent_path = tmp_path / ".p2p" / "consents" / "CONSENT-001" / "consent.yml"
    consent_path.parent.mkdir(parents=True, exist_ok=True)
    consent_path.write_text(
        yaml.safe_dump(
            {
                "consent_id": "CONSENT-999",
                "operation": "invalid_operation",
                "status": "invalid_status",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = _validation_service(workspace).validate()
    codes = _codes(result)

    assert "P2P213_INVALID_PERMISSION_ROLE" in codes
    assert "P2P215_MISSING_OWNER_IDENTITY" in codes
    assert "P2P221_CONSENT_ID_MISMATCH" in codes
    assert "P2P222_INVALID_CONSENT_OPERATION" in codes
    assert "P2P223_INVALID_CONSENT_STATUS" in codes
    assert "P2P224_MISSING_CONSENT_FIELD" in codes


def test_validation_service_reports_duplicate_proposal_ids(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Demo Project")
    proposal = workspace.create_proposal("Draft Work")
    proposal_dir = tmp_path / proposal.path
    shutil.copytree(proposal_dir, tmp_path / ".p2p" / "proposals" / "PROP-001-other-draft")

    result = _validation_service(workspace).validate()
    duplicate = next(finding for finding in result.findings if finding.code == "P2P104_DUPLICATE_PROPOSAL_ID")

    assert result.ok is False
    assert duplicate.severity == "error"
    assert "Duplicate proposal ID PROP-001" in duplicate.message
    assert "PROP-001-draft-work" in duplicate.message
    assert "PROP-001-other-draft" in duplicate.message


def test_validation_service_reports_malformed_proposal_artifact_state(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Demo Project")
    proposal = workspace.create_proposal("Artifact State")
    artifact_path = tmp_path / proposal.path / "artifact-state.yml"
    payload = yaml.safe_load(artifact_path.read_text(encoding="utf-8"))
    payload["proposal_artifacts"]["artifacts"][0]["status"] = "invalid"
    artifact_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    result = _validation_service(workspace).validate()
    finding = next(finding for finding in result.findings if finding.code == "P2P233_INVALID_PROPOSAL_ARTIFACT_STATE")

    assert result.ok is False
    assert finding.severity == "error"
    assert "Invalid proposal artifact status" in finding.message


def test_validation_service_accepts_missing_interaction_style_state(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Demo Project")

    result = _validation_service(workspace).validate()

    assert result.ok is True
    assert "P2P250_INVALID_PROJECT_INTERACTION_STYLE" not in _codes(result)


def test_validation_service_reports_malformed_interaction_style_state(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Demo Project")
    path = tmp_path / ".p2p" / "project" / "interaction-style.yml"
    path.write_text(
        yaml.safe_dump(
            {
                "interaction_style": {
                    "schema_version": 1,
                    "scope": "project",
                    "technical_verbosity": 2,
                    "formality": 8,
                    "assertiveness": 0,
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = _validation_service(workspace).validate()
    finding = next(finding for finding in result.findings if finding.code == "P2P250_INVALID_PROJECT_INTERACTION_STYLE")

    assert result.ok is False
    assert finding.severity == "error"
    assert finding.path == Path(".p2p/project/interaction-style.yml")
    assert "formality" in finding.message
    assert "p2p project interaction-style set" in finding.suggested_command
