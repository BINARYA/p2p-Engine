from __future__ import annotations

from pathlib import Path
import shutil

import yaml

from p2p_engine import __version__ as P2P_ENGINE_VERSION
from p2p_engine.core.runtime_contract import (
    RUNTIME_CONTRACT_ADOPTION_STATUS_ADOPTED,
    RUNTIME_CONTRACT_ADOPTION_STATUS_BLOCKED,
    RUNTIME_CONTRACT_BLOCKER_CONFIRMATION_REQUIRED,
    RUNTIME_CONTRACT_BLOCKER_INVALID_PROPOSED_CONTRACT,
    RUNTIME_CONTRACT_BLOCKER_OWNER_AUTHORITY_REQUIRED,
    RUNTIME_CONTRACT_BLOCKER_STALE_PREVIEW,
    RUNTIME_CONTRACT_BLOCKER_UNMANAGED_SETUP_GUIDE,
    RUNTIME_CONTRACT_BLOCKER_UNSUPPORTED_CURRENT_STATE,
    RUNTIME_CONTRACT_BLOCKER_UNTRUSTED_CURRENT_CONTRACT,
    RUNTIME_CONTRACT_IMPACT_CURRENT_RUNTIME_EXCLUDED,
    RUNTIME_CONTRACT_IMPACT_RANGE_TIGHTENING,
    RUNTIME_CONTRACT_IMPACT_RANGE_WIDENING,
    RUNTIME_CONTRACT_IMPACT_RECOMMENDED_ONLY,
    RUNTIME_CONTRACT_UPDATE_STATUS_APPLICABLE,
    RUNTIME_CONTRACT_UPDATE_STATUS_BLOCKED,
    RUNTIME_CONTRACT_UPDATE_STATUS_NO_CHANGE,
    RUNTIME_CONTRACT_UPDATE_STATUS_PARTIAL_FAILURE,
    RUNTIME_CONTRACT_UPDATE_STATUS_PREVIEW_BLOCKED,
    RUNTIME_CONTRACT_UPDATE_STATUS_UPDATED,
    RUNTIME_CONTRACT_INSTALLER_FIELD,
    RUNTIME_CONTRACT_LEGACY_UNDECLARED,
    RUNTIME_CONTRACT_MISSING,
    RUNTIME_SETUP_GUIDE_DRIFT,
    RUNTIME_SETUP_GUIDE_MARKER,
    RUNTIME_SETUP_GUIDE_UNMANAGED,
    RUNTIME_STATUS_COMPATIBLE,
    RUNTIME_STATUS_INCOMPATIBLE,
    RUNTIME_STATUS_LEGACY_UNDECLARED,
    RUNTIME_STATUS_MISSING_CONTRACT,
)
from p2p_engine.services.runtime_contract import RuntimeContractService
from p2p_engine.storage.filesystem import P2PWorkspace


def _write_yaml(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _project_manifest(required: bool) -> dict[str, object]:
    payload: dict[str, object] = {"project": {"name": "Demo"}}
    if required:
        payload["runtime_contract"] = {"required": True}
    return payload


def test_runtime_contract_service_reports_compatible_contract(tmp_path: Path) -> None:
    service = RuntimeContractService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    _write_yaml(service.project_manifest_path, _project_manifest(required=True))
    service.write_default_contract()

    status = service.status()

    assert status.state == RUNTIME_STATUS_COMPATIBLE
    assert status.compatible is True
    assert status.requires == f"=={P2P_ENGINE_VERSION}"
    assert status.recommended == P2P_ENGINE_VERSION
    assert status.findings == []


def test_runtime_contract_service_distinguishes_missing_required_from_legacy(tmp_path: Path) -> None:
    required = RuntimeContractService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    _write_yaml(required.project_manifest_path, _project_manifest(required=True))

    missing = required.status()

    assert missing.state == RUNTIME_STATUS_MISSING_CONTRACT
    assert missing.findings[0].code == RUNTIME_CONTRACT_MISSING

    legacy_root = tmp_path / "legacy"
    legacy = RuntimeContractService(root=legacy_root, p2p_dir=legacy_root / ".p2p")
    _write_yaml(legacy.project_manifest_path, _project_manifest(required=False))

    status = legacy.status()

    assert status.state == RUNTIME_STATUS_LEGACY_UNDECLARED
    assert status.findings[0].code == RUNTIME_CONTRACT_LEGACY_UNDECLARED
    assert status.findings[0].severity == "warning"


def test_runtime_contract_adoption_writes_contract_marker_and_setup_guide(tmp_path: Path) -> None:
    service = RuntimeContractService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    _write_yaml(service.project_manifest_path, _project_manifest(required=False))

    result = service.adopt_contract(
        requires=f"=={P2P_ENGINE_VERSION}",
        recommended=P2P_ENGINE_VERSION,
        confirm=True,
    )

    assert result.status == RUNTIME_CONTRACT_ADOPTION_STATUS_ADOPTED
    assert result.current_state == RUNTIME_STATUS_LEGACY_UNDECLARED
    assert result.files_changed == [".p2p/project/runtime.yml", "P2P-SETUP.md", ".p2p/project.yml"]
    payload = yaml.safe_load(service.contract_path.read_text(encoding="utf-8"))
    assert payload["runtime"]["p2p"] == {
        "requires": f"=={P2P_ENGINE_VERSION}",
        "recommended": P2P_ENGINE_VERSION,
    }
    project = yaml.safe_load(service.project_manifest_path.read_text(encoding="utf-8"))
    assert project["project"]["name"] == "Demo"
    assert project["runtime_contract"] == {"required": True}
    assert RUNTIME_SETUP_GUIDE_MARKER in service.setup_guide_path.read_text(encoding="utf-8")
    assert service.status().state == RUNTIME_STATUS_COMPATIBLE


def test_runtime_contract_adoption_requires_confirmation(tmp_path: Path) -> None:
    service = RuntimeContractService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    _write_yaml(service.project_manifest_path, _project_manifest(required=False))

    result = service.adopt_contract(
        requires=f"=={P2P_ENGINE_VERSION}",
        recommended=P2P_ENGINE_VERSION,
    )

    assert result.status == RUNTIME_CONTRACT_ADOPTION_STATUS_BLOCKED
    assert result.blocked_reason == RUNTIME_CONTRACT_BLOCKER_CONFIRMATION_REQUIRED
    assert result.files_changed == []
    assert not service.contract_path.exists()
    assert not service.setup_guide_path.exists()
    project = yaml.safe_load(service.project_manifest_path.read_text(encoding="utf-8"))
    assert "runtime_contract" not in project


def test_runtime_contract_adoption_requires_owner_authority(tmp_path: Path) -> None:
    service = RuntimeContractService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    _write_yaml(service.project_manifest_path, _project_manifest(required=False))

    result = service.adopt_contract(
        requires=f"=={P2P_ENGINE_VERSION}",
        recommended=P2P_ENGINE_VERSION,
        confirm=True,
        actor="contributor",
    )

    assert result.status == RUNTIME_CONTRACT_ADOPTION_STATUS_BLOCKED
    assert result.blocked_reason == RUNTIME_CONTRACT_BLOCKER_OWNER_AUTHORITY_REQUIRED
    assert result.files_changed == []
    assert not service.contract_path.exists()


def test_runtime_contract_adoption_blocks_unmanaged_setup_guide(tmp_path: Path) -> None:
    service = RuntimeContractService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    _write_yaml(service.project_manifest_path, _project_manifest(required=False))
    service.setup_guide_path.write_text("# Local setup\n", encoding="utf-8")

    result = service.adopt_contract(
        requires=f"=={P2P_ENGINE_VERSION}",
        recommended=P2P_ENGINE_VERSION,
        confirm=True,
    )

    assert result.status == RUNTIME_CONTRACT_ADOPTION_STATUS_BLOCKED
    assert result.blocked_reason == RUNTIME_CONTRACT_BLOCKER_UNMANAGED_SETUP_GUIDE
    assert result.files_changed == []
    assert not service.contract_path.exists()


def test_runtime_contract_adoption_blocks_non_legacy_state(tmp_path: Path) -> None:
    service = RuntimeContractService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    _write_yaml(service.project_manifest_path, _project_manifest(required=True))
    service.write_default_contract()

    result = service.adopt_contract(
        requires=f"=={P2P_ENGINE_VERSION}",
        recommended=P2P_ENGINE_VERSION,
        confirm=True,
    )

    assert result.status == RUNTIME_CONTRACT_ADOPTION_STATUS_BLOCKED
    assert result.blocked_reason == RUNTIME_CONTRACT_BLOCKER_UNSUPPORTED_CURRENT_STATE
    assert result.files_changed == []


def test_runtime_contract_adoption_rejects_invalid_proposed_contract(tmp_path: Path) -> None:
    service = RuntimeContractService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    _write_yaml(service.project_manifest_path, _project_manifest(required=False))

    result = service.adopt_contract(
        requires=">=0.2.0,<0.3",
        recommended="0.3.0",
        confirm=True,
    )

    assert result.status == RUNTIME_CONTRACT_ADOPTION_STATUS_BLOCKED
    assert result.blocked_reason == RUNTIME_CONTRACT_BLOCKER_INVALID_PROPOSED_CONTRACT
    assert result.validation_errors == ["runtime.p2p.recommended must satisfy runtime.p2p.requires."]
    assert not service.contract_path.exists()


def test_runtime_contract_service_rejects_installer_fields(tmp_path: Path) -> None:
    service = RuntimeContractService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    _write_yaml(service.project_manifest_path, _project_manifest(required=True))
    payload = service.default_contract_payload()
    runtime = payload["runtime"]
    assert isinstance(runtime, dict)
    p2p = runtime["p2p"]
    assert isinstance(p2p, dict)
    p2p["wheel"] = "p2p_engine-0.1.9.whl"
    _write_yaml(service.contract_path, payload)

    status = service.status()

    assert status.compatible is False
    assert status.findings[0].code == RUNTIME_CONTRACT_INSTALLER_FIELD


def test_runtime_contract_service_reports_incompatible_runtime(tmp_path: Path) -> None:
    service = RuntimeContractService(root=tmp_path, p2p_dir=tmp_path / ".p2p", current_version="0.2.0")
    _write_yaml(service.project_manifest_path, _project_manifest(required=True))
    _write_yaml(
        service.contract_path,
        {
            "runtime_contract": {"schema_version": 1},
            "runtime": {"p2p": {"requires": "==0.1.9", "recommended": "0.1.9"}},
        },
    )

    status = service.status()

    assert status.state == RUNTIME_STATUS_INCOMPATIBLE
    assert status.compatible is False
    assert status.requires == "==0.1.9"


def test_runtime_setup_guide_drift_uses_full_rendered_content(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Runtime Setup")
    setup_path = tmp_path / "P2P-SETUP.md"
    setup_path.write_text(
        setup_path.read_text(encoding="utf-8").replace("official installation guidance", "manual notes"),
        encoding="utf-8",
    )

    findings = workspace._runtime_contract_service().validation_findings()

    assert RUNTIME_SETUP_GUIDE_DRIFT in {finding.code for finding in findings}


def test_runtime_setup_guide_unmanaged_file_is_reported(tmp_path: Path) -> None:
    service = RuntimeContractService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    _write_yaml(service.project_manifest_path, _project_manifest(required=True))
    service.write_default_contract()
    service.setup_guide_path.write_text("# Local setup\n", encoding="utf-8")

    findings = service.validation_findings()

    assert RUNTIME_SETUP_GUIDE_UNMANAGED in {finding.code for finding in findings}


def test_runtime_setup_guide_render_contains_managed_marker(tmp_path: Path) -> None:
    service = RuntimeContractService(root=tmp_path, p2p_dir=tmp_path / ".p2p")

    content = service.render_setup_guide()

    assert RUNTIME_SETUP_GUIDE_MARKER in content
    assert ".p2p/project/runtime.yml" in content
    assert "p2p runtime status" in content


def test_runtime_contract_status_survives_copied_project_without_git_metadata(tmp_path: Path) -> None:
    source = tmp_path / "source"
    copied = tmp_path / "copied"
    workspace = P2PWorkspace(source)
    workspace.init_project("Copied Runtime Project")

    shutil.copytree(source, copied)

    copied_workspace = P2PWorkspace(copied)
    assert copied_workspace.runtime_status().state == RUNTIME_STATUS_COMPATIBLE
    assert not (copied / ".git").exists()


def test_runtime_contract_status_survives_extracted_project_archive(tmp_path: Path) -> None:
    source = tmp_path / "source"
    extracted = tmp_path / "extracted"
    workspace = P2PWorkspace(source)
    workspace.init_project("Archived Runtime Project")

    archive = shutil.make_archive(str(tmp_path / "project-archive"), "zip", root_dir=source)
    shutil.unpack_archive(archive, extracted)

    extracted_workspace = P2PWorkspace(extracted)
    assert extracted_workspace.runtime_status().state == RUNTIME_STATUS_COMPATIBLE
    assert (extracted / ".p2p" / "project" / "runtime.yml").exists()
    assert not (extracted / ".git").exists()


def test_runtime_contract_update_preview_supports_recommended_only(tmp_path: Path) -> None:
    service = RuntimeContractService(root=tmp_path, p2p_dir=tmp_path / ".p2p", current_version="0.2.3")
    _write_yaml(service.project_manifest_path, _project_manifest(required=True))
    _write_yaml(
        service.contract_path,
        {
            "runtime_contract": {"schema_version": 1},
            "runtime": {"p2p": {"requires": ">=0.2.0,<0.3", "recommended": "0.2.1"}},
        },
    )

    preview = service.preview_update(requires=">=0.2.0,<0.3", recommended="0.2.4")

    assert preview.status == RUNTIME_CONTRACT_UPDATE_STATUS_APPLICABLE
    assert preview.impact_labels == [RUNTIME_CONTRACT_IMPACT_RECOMMENDED_ONLY]
    assert preview.reason_required is False
    assert preview.expected_state_token is not None
    assert preview.apply_allowed is True


def test_runtime_contract_update_rejects_invalid_proposed_contract(tmp_path: Path) -> None:
    service = RuntimeContractService(root=tmp_path, p2p_dir=tmp_path / ".p2p", current_version="0.2.3")
    _write_yaml(service.project_manifest_path, _project_manifest(required=True))
    _write_yaml(
        service.contract_path,
        {
            "runtime_contract": {"schema_version": 1},
            "runtime": {"p2p": {"requires": ">=0.2.0,<0.3", "recommended": "0.2.1"}},
        },
    )

    preview = service.preview_update(requires=">=0.2.0,<0.3", recommended="0.3.0")

    assert preview.status == RUNTIME_CONTRACT_UPDATE_STATUS_PREVIEW_BLOCKED
    assert preview.proposed_valid is False
    assert preview.expected_state_token is None


def test_runtime_contract_update_token_is_deterministic_and_binds_reason(tmp_path: Path) -> None:
    service = RuntimeContractService(root=tmp_path, p2p_dir=tmp_path / ".p2p", current_version="0.2.3")
    _write_yaml(service.project_manifest_path, _project_manifest(required=True))
    _write_yaml(
        service.contract_path,
        {
            "runtime_contract": {"schema_version": 1},
            "runtime": {"p2p": {"requires": ">=0.2.0,<0.4", "recommended": "0.2.1"}},
        },
    )

    first = service.preview_update(requires=">=0.2.0,<0.3", recommended="0.2.4", reason="Tighten range.")
    second = service.preview_update(requires=">=0.2.0,<0.3", recommended="0.2.4", reason="Tighten range.")
    changed_reason = service.preview_update(
        requires=">=0.2.0,<0.3",
        recommended="0.2.4",
        reason="Different reason.",
    )

    assert first.expected_state_token == second.expected_state_token
    assert first.expected_state_token != changed_reason.expected_state_token


def test_runtime_contract_update_apply_updates_contract_and_setup_guide(tmp_path: Path) -> None:
    service = RuntimeContractService(root=tmp_path, p2p_dir=tmp_path / ".p2p", current_version="0.2.3")
    _write_yaml(service.project_manifest_path, _project_manifest(required=True))
    _write_yaml(
        service.contract_path,
        {
            "runtime_contract": {"schema_version": 1},
            "runtime": {"p2p": {"requires": ">=0.2.0,<0.3", "recommended": "0.2.1"}},
        },
    )
    preview = service.preview_update(requires=">=0.2.0,<0.3", recommended="0.2.4")

    result = service.apply_update(
        requires=">=0.2.0,<0.3",
        recommended="0.2.4",
        expected_state_token=preview.expected_state_token or "",
        confirm=True,
    )

    assert result.status == RUNTIME_CONTRACT_UPDATE_STATUS_UPDATED
    assert result.files_changed == ["P2P-SETUP.md", ".p2p/project/runtime.yml"]
    payload = yaml.safe_load(service.contract_path.read_text(encoding="utf-8"))
    assert payload["runtime"]["p2p"]["recommended"] == "0.2.4"
    assert "0.2.4" in service.setup_guide_path.read_text(encoding="utf-8")


def test_runtime_contract_update_reports_setup_guide_write_failure_without_contract_change(
    tmp_path: Path,
    monkeypatch,
) -> None:
    service = RuntimeContractService(root=tmp_path, p2p_dir=tmp_path / ".p2p", current_version="0.2.3")
    _write_yaml(service.project_manifest_path, _project_manifest(required=True))
    _write_yaml(
        service.contract_path,
        {
            "runtime_contract": {"schema_version": 1},
            "runtime": {"p2p": {"requires": ">=0.2.0,<0.3", "recommended": "0.2.1"}},
        },
    )
    preview = service.preview_update(requires=">=0.2.0,<0.3", recommended="0.2.4")

    def fail_write_text(*args, **kwargs) -> None:
        raise OSError("setup guide write failed")

    monkeypatch.setattr("p2p_engine.services.runtime_contract.write_text_atomic", fail_write_text)

    result = service.apply_update(
        requires=">=0.2.0,<0.3",
        recommended="0.2.4",
        expected_state_token=preview.expected_state_token or "",
        confirm=True,
    )

    payload = yaml.safe_load(service.contract_path.read_text(encoding="utf-8"))
    assert result.status == RUNTIME_CONTRACT_UPDATE_STATUS_PARTIAL_FAILURE
    assert result.files_changed == []
    assert payload["runtime"]["p2p"]["recommended"] == "0.2.1"


def test_runtime_contract_update_reports_contract_write_failure_after_setup_change(
    tmp_path: Path,
    monkeypatch,
) -> None:
    service = RuntimeContractService(root=tmp_path, p2p_dir=tmp_path / ".p2p", current_version="0.2.3")
    _write_yaml(service.project_manifest_path, _project_manifest(required=True))
    _write_yaml(
        service.contract_path,
        {
            "runtime_contract": {"schema_version": 1},
            "runtime": {"p2p": {"requires": ">=0.2.0,<0.3", "recommended": "0.2.1"}},
        },
    )
    preview = service.preview_update(requires=">=0.2.0,<0.3", recommended="0.2.4")

    def fail_write_yaml(*args, **kwargs) -> None:
        raise OSError("contract write failed")

    monkeypatch.setattr("p2p_engine.services.runtime_contract.write_yaml_atomic", fail_write_yaml)

    result = service.apply_update(
        requires=">=0.2.0,<0.3",
        recommended="0.2.4",
        expected_state_token=preview.expected_state_token or "",
        confirm=True,
    )

    payload = yaml.safe_load(service.contract_path.read_text(encoding="utf-8"))
    assert result.status == RUNTIME_CONTRACT_UPDATE_STATUS_PARTIAL_FAILURE
    assert result.files_changed == ["P2P-SETUP.md"]
    assert payload["runtime"]["p2p"]["recommended"] == "0.2.1"
    assert "0.2.4" in service.setup_guide_path.read_text(encoding="utf-8")


def test_runtime_contract_update_blocks_unmanaged_setup_guide(tmp_path: Path) -> None:
    service = RuntimeContractService(root=tmp_path, p2p_dir=tmp_path / ".p2p", current_version="0.2.3")
    _write_yaml(service.project_manifest_path, _project_manifest(required=True))
    _write_yaml(
        service.contract_path,
        {
            "runtime_contract": {"schema_version": 1},
            "runtime": {"p2p": {"requires": ">=0.2.0,<0.3", "recommended": "0.2.1"}},
        },
    )
    service.setup_guide_path.write_text("# Human setup\n", encoding="utf-8")

    preview = service.preview_update(requires=">=0.2.0,<0.3", recommended="0.2.4")

    assert preview.status == RUNTIME_CONTRACT_UPDATE_STATUS_PREVIEW_BLOCKED
    assert preview.blocked_reason == RUNTIME_CONTRACT_BLOCKER_UNMANAGED_SETUP_GUIDE
    assert preview.expected_state_token is None


def test_runtime_contract_update_preview_is_diagnostic_for_missing_contract(tmp_path: Path) -> None:
    service = RuntimeContractService(root=tmp_path, p2p_dir=tmp_path / ".p2p", current_version="0.2.3")
    _write_yaml(service.project_manifest_path, _project_manifest(required=True))

    preview = service.preview_update(requires=">=0.2.0,<0.3", recommended="0.2.4")

    assert preview.status == RUNTIME_CONTRACT_UPDATE_STATUS_PREVIEW_BLOCKED
    assert preview.current_state == RUNTIME_STATUS_MISSING_CONTRACT
    assert preview.blocked_reason == RUNTIME_CONTRACT_BLOCKER_UNTRUSTED_CURRENT_CONTRACT
    assert preview.required_workflow == "contract_recovery"
    assert preview.expected_state_token is None


def test_runtime_contract_update_apply_requires_owner_authority(tmp_path: Path) -> None:
    service = RuntimeContractService(root=tmp_path, p2p_dir=tmp_path / ".p2p", current_version="0.2.3")
    _write_yaml(service.project_manifest_path, _project_manifest(required=True))
    _write_yaml(
        service.contract_path,
        {
            "runtime_contract": {"schema_version": 1},
            "runtime": {"p2p": {"requires": ">=0.2.0,<0.3", "recommended": "0.2.1"}},
        },
    )
    preview = service.preview_update(requires=">=0.2.0,<0.3", recommended="0.2.4", actor="contributor")

    assert preview.status == RUNTIME_CONTRACT_UPDATE_STATUS_APPLICABLE
    assert preview.apply_allowed is False
    assert preview.expected_state_token is not None

    result = service.apply_update(
        requires=">=0.2.0,<0.3",
        recommended="0.2.4",
        expected_state_token=preview.expected_state_token or "",
        confirm=True,
        actor="contributor",
    )

    assert result.status == RUNTIME_CONTRACT_UPDATE_STATUS_BLOCKED
    assert result.blocked_reason == RUNTIME_CONTRACT_BLOCKER_OWNER_AUTHORITY_REQUIRED


def test_runtime_contract_update_apply_requires_confirmation_and_reason(tmp_path: Path) -> None:
    service = RuntimeContractService(root=tmp_path, p2p_dir=tmp_path / ".p2p", current_version="0.2.3")
    _write_yaml(service.project_manifest_path, _project_manifest(required=True))
    _write_yaml(
        service.contract_path,
        {
            "runtime_contract": {"schema_version": 1},
            "runtime": {"p2p": {"requires": ">=0.2.0,<0.4", "recommended": "0.2.1"}},
        },
    )
    preview = service.preview_update(requires=">=0.2.0,<0.3", recommended="0.2.4")

    missing_confirm = service.apply_update(
        requires=">=0.2.0,<0.3",
        recommended="0.2.4",
        expected_state_token=preview.expected_state_token or "",
    )
    missing_reason = service.apply_update(
        requires=">=0.2.0,<0.3",
        recommended="0.2.4",
        expected_state_token=preview.expected_state_token or "",
        confirm=True,
    )

    assert missing_confirm.status == RUNTIME_CONTRACT_UPDATE_STATUS_BLOCKED
    assert missing_confirm.blocked_reason == "confirmation_required"
    assert missing_reason.status == RUNTIME_CONTRACT_UPDATE_STATUS_BLOCKED
    assert missing_reason.blocked_reason == "reason_required"


def test_runtime_contract_update_apply_rejects_stale_preview(tmp_path: Path) -> None:
    service = RuntimeContractService(root=tmp_path, p2p_dir=tmp_path / ".p2p", current_version="0.2.3")
    _write_yaml(service.project_manifest_path, _project_manifest(required=True))
    _write_yaml(
        service.contract_path,
        {
            "runtime_contract": {"schema_version": 1},
            "runtime": {"p2p": {"requires": ">=0.2.0,<0.3", "recommended": "0.2.1"}},
        },
    )
    preview = service.preview_update(requires=">=0.2.0,<0.3", recommended="0.2.4")
    service.setup_guide_path.write_text(f"{RUNTIME_SETUP_GUIDE_MARKER}\n\nDrift\n", encoding="utf-8")

    result = service.apply_update(
        requires=">=0.2.0,<0.3",
        recommended="0.2.4",
        expected_state_token=preview.expected_state_token or "",
        confirm=True,
    )

    assert result.status == RUNTIME_CONTRACT_UPDATE_STATUS_BLOCKED
    assert result.blocked_reason == RUNTIME_CONTRACT_BLOCKER_STALE_PREVIEW


def test_runtime_contract_update_classifies_overlapping_range_as_widening_and_tightening(
    tmp_path: Path,
) -> None:
    service = RuntimeContractService(root=tmp_path, p2p_dir=tmp_path / ".p2p", current_version="0.3.5")
    _write_yaml(service.project_manifest_path, _project_manifest(required=True))
    _write_yaml(
        service.contract_path,
        {
            "runtime_contract": {"schema_version": 1},
            "runtime": {"p2p": {"requires": ">=0.2.0,<0.4", "recommended": "0.2.4"}},
        },
    )

    preview = service.preview_update(
        requires=">=0.3.0,<0.5",
        recommended="0.3.5",
        reason="Move the project runtime line.",
    )

    assert RUNTIME_CONTRACT_IMPACT_RANGE_WIDENING in preview.impact_labels
    assert RUNTIME_CONTRACT_IMPACT_RANGE_TIGHTENING in preview.impact_labels
    assert preview.range_comparison["ranges_overlap"] is True
    assert preview.reason_required is True


def test_runtime_contract_update_no_change_does_not_repair_drift_only(tmp_path: Path) -> None:
    service = RuntimeContractService(root=tmp_path, p2p_dir=tmp_path / ".p2p", current_version=P2P_ENGINE_VERSION)
    _write_yaml(service.project_manifest_path, _project_manifest(required=True))
    service.write_default_contract()
    service.setup_guide_path.write_text(f"{RUNTIME_SETUP_GUIDE_MARKER}\n\nDrift\n", encoding="utf-8")

    preview = service.preview_update(requires=f"=={P2P_ENGINE_VERSION}", recommended=P2P_ENGINE_VERSION)

    assert preview.status == RUNTIME_CONTRACT_UPDATE_STATUS_NO_CHANGE
    assert preview.expected_state_token is None
    assert preview.setup_guide["state"] == "managed_drifted"


def test_runtime_contract_update_reports_current_runtime_excluded(tmp_path: Path) -> None:
    service = RuntimeContractService(root=tmp_path, p2p_dir=tmp_path / ".p2p", current_version="0.3.1")
    _write_yaml(service.project_manifest_path, _project_manifest(required=True))
    _write_yaml(
        service.contract_path,
        {
            "runtime_contract": {"schema_version": 1},
            "runtime": {"p2p": {"requires": ">=0.2.0,<0.4", "recommended": "0.2.4"}},
        },
    )

    preview = service.preview_update(requires=">=0.2.0,<0.3", recommended="0.2.4", reason="Exclude 0.3 line.")

    assert RUNTIME_CONTRACT_IMPACT_CURRENT_RUNTIME_EXCLUDED in preview.impact_labels
    assert preview.reason_required is True
