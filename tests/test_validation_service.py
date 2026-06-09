import shutil
from pathlib import Path

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
    )


def _codes(result) -> set[str]:
    return {finding.code for finding in result.findings}


def test_validation_service_accepts_valid_refreshed_project(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Demo Project")
    workspace.refresh_registries()

    result = _validation_service(workspace).validate()

    assert result.ok is True
    assert result.errors == 0
    assert result.warnings == 0


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
