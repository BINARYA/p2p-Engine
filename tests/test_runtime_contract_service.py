from __future__ import annotations

from pathlib import Path
import shutil

import yaml

from p2p_engine import __version__ as P2P_ENGINE_VERSION
from p2p_engine.core.runtime_contract import (
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
