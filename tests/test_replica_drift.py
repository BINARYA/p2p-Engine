from __future__ import annotations

from pathlib import Path
from types import MethodType

import pytest
import yaml
from typer.testing import CliRunner

from p2p_engine.cli import app
from p2p_engine.core.replica_drift import DriftClassification, ReplicaDriftStatus
from p2p_engine.mcp.tools import call_tool
from p2p_engine.services.linked_replica import LinkedReplicaService
from p2p_engine.services.project_application import ProjectApplicationService
from p2p_engine.services.replica_drift import ReplicaDriftService
from tests.cli_assertions import cli_data, cli_error
from tests.test_linked_replica import (
    FakeIntegration,
    _clone,
    _credentials,
)

runner = CliRunner()


def test_linked_revision_zero_remains_an_exact_cross_repository_integer() -> None:
    status = ReplicaDriftStatus(
        status="healthy",
        classification=DriftClassification.transient_valid,
        project_uuid="16ec9e72-57a8-4c13-8ff0-9bc0e329c42d",
        replica_id="c25babe6-a431-4568-9f24-35e72e7ea7ce",
        authority_epoch=1,
        confirmed_revision=0,
    )

    assert status.to_dict()["confirmed_revision"] == 0


def _service(tmp_path: Path):
    target, snapshot, bundle, digest, transport, result = _clone(tmp_path)
    original_request = transport.request_json

    def request_with_snapshot(self, method, url, **kwargs):
        if method == "GET" and url.endswith("/snapshot"):
            return {"linked_replica_snapshot": self._manifest(self.replica_id, session="4")}
        if method == "POST" and url.endswith("/drift"):
            return {
                "replica_health": {
                    "contract": "wavekit-replica-health/v1",
                    "health_state": kwargs["json_body"]["status"]["status"],
                }
            }
        if method == "POST" and url.endswith("/reconciliation/preview"):
            return {
                "reconciliation_preview": {
                    "contract": "wavekit-replica-reconciliation-preview/v1",
                    "status": "ready",
                    "preview_token": "sha256:" + "a" * 64,
                }
            }
        if method == "POST" and url.endswith("/reconciliation/apply"):
            assert kwargs["json_body"]["confirm"] is True
            return {
                "reconciliation_result": {
                    "contract": "wavekit-replica-reconciliation-result/v1",
                    "status": "submitted",
                    "plan_digest": kwargs["json_body"]["plan_digest"],
                    "receipts": [{"status": "completed", "project_revision": 2}],
                    "raw_local_state_received": False,
                }
            }
        return original_request(method, url, **kwargs)

    transport.request_json = MethodType(request_with_snapshot, transport)
    application = ProjectApplicationService(target)
    linked = LinkedReplicaService(
        root=target,
        transport=transport,
        credentials=_credentials(),
        integration_transition=lambda: FakeIntegration(),
        snapshot_reader=application.adapter.repository.snapshot,
        store=application.adapter.linked_replicas,
        now=lambda: 1_900_000_100,
    )
    drift = ReplicaDriftService(
        root=target,
        adapter=application.adapter,
        linked_replica=linked,
    )
    return target, application, linked, drift, transport, snapshot, result, bundle, digest


def _change_domain(target: Path) -> None:
    path = target / ".p2p" / "project" / "domain.yml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    payload["project_domain"]["descriptor"] = {
        "key": "software",
        "name": "Software",
        "source": "local",
        "external_ref": None,
    }
    payload["project_domain"]["revision"] += 1
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def test_valid_replica_ignores_replica_local_and_git_bytes(tmp_path: Path) -> None:
    target, _application, linked, drift, *_rest = _service(tmp_path)
    local = target / ".p2p" / "local" / "diagnostic.bin"
    local.write_bytes(b"adapter transient bytes")
    (target / ".git").mkdir()
    (target / ".git" / "HEAD").write_text("ref: refs/heads/unrelated\n", encoding="utf-8")

    status = drift.status()

    assert status.status == "healthy"
    assert status.classification == DriftClassification.transient_valid
    assert linked.verify_local_integrity().semantic_state_digest == status.current_semantic_digest


def test_formatting_only_change_does_not_create_semantic_drift(tmp_path: Path) -> None:
    target, _application, _linked, drift, *_rest = _service(tmp_path)
    path = target / ".p2p" / "project" / "domain.yml"
    path.write_text("# user formatting\n" + path.read_text(encoding="utf-8"), encoding="utf-8")

    assert drift.status().status == "healthy"


def test_missing_managed_blob_and_replica_identity_change_fail_closed(
    tmp_path: Path,
) -> None:
    target, _application, _linked, drift, _transport, _snapshot, _result, _bundle, digest = (
        _service(tmp_path)
    )
    blob = target / ".p2p" / "blobs" / "sha256" / digest[:2] / digest
    blob.unlink()
    assert drift.status().classification == DriftClassification.structural_corruption

    target2, _application2, _linked2, drift2, *_rest = _service(tmp_path / "identity")
    identity = target2 / ".p2p" / "local" / "replica.yml"
    value = yaml.safe_load(identity.read_text(encoding="utf-8"))
    value["project_replica"]["replica_id"] = "736f2c07-5ac7-4d65-aa24-d04a4b17e925"
    identity.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")
    assert drift2.status().classification == DriftClassification.identity_mismatch


def test_semantic_drift_blocks_catch_up_and_has_bounded_diff(tmp_path: Path) -> None:
    target, _application, linked, drift, transport, *_rest = _service(tmp_path)
    requests_before = len(transport.requests)
    _change_domain(target)

    status = drift.status()

    assert status.classification == DriftClassification.semantic_drift
    assert status.writes_permitted is False
    with pytest.raises(ValueError, match="P2P_LINKED_REPLICA_SEMANTIC_DRIFT"):
        linked.catch_up()
    assert len(transport.requests) == requests_before

    difference = drift.semantic_diff(limit=10)
    assert difference.complete is True
    assert difference.entries[0].entity_type == "p2p.project.domain"
    assert all("path" not in str(item.to_dict()) for item in difference.entries)


def test_domain_only_drift_builds_exact_command_plan(tmp_path: Path) -> None:
    target, _application, _linked, drift, *_rest = _service(tmp_path)
    _change_domain(target)

    plan = drift.reconciliation_preview()

    assert plan.complete is True
    assert plan.unsupported_differences == ()
    assert len(plan.commands) == 1
    assert plan.commands[0].command == "project.domain.set"
    assert plan.commands[0].payload["key"] == "software"
    assert (
        target
        / ".p2p"
        / "local"
        / "project-replication"
        / "reconciliation-plans"
        / f"{plan.plan_digest}.json"
    ).is_file()


def test_unknown_drift_remains_explicitly_unsupported(tmp_path: Path) -> None:
    target, _application, _linked, drift, *_rest = _service(tmp_path)
    constitution = target / ".p2p" / "governance" / "constitution.md"
    constitution.write_text("# Constitution\n\nAltered outside authority.\n", encoding="utf-8")

    plan = drift.reconciliation_preview()

    assert plan.complete is False
    assert plan.commands == ()
    assert plan.unsupported_differences[0]["entity_type"] == "p2p.governance.document"


def test_reconciliation_apply_recovers_lost_response_without_second_backup(
    tmp_path: Path,
) -> None:
    target, _application, _linked, drift, transport, *_rest = _service(tmp_path)
    _change_domain(target)
    plan = drift.reconciliation_preview()
    normal_request = transport.request_json
    failed_once = False

    def lose_first_apply(self, method, url, **kwargs):
        nonlocal failed_once
        if method == "POST" and url.endswith("/reconciliation/apply") and not failed_once:
            failed_once = True
            raise ValueError("P2P_WAVEKIT_UNAVAILABLE: response lost after submission")
        return normal_request(method, url, **kwargs)

    transport.request_json = MethodType(lose_first_apply, transport)
    with pytest.raises(ValueError, match="response lost"):
        drift.reconciliation_apply(plan_digest=plan.plan_digest, confirm=True)
    backups = list((target / ".p2p-forensics" / plan.project_uuid).glob("*.tar"))
    assert len(backups) == 1

    result = drift.reconciliation_apply(plan_digest=plan.plan_digest, confirm=True)

    assert result["status"] == "applied"
    assert len(list((target / ".p2p-forensics" / plan.project_uuid).glob("*.tar"))) == 1
    state = (
        target
        / ".p2p/local/project-replication/reconciliation-plans"
        / f"{plan.plan_digest}.apply.json"
    ).read_text(encoding="utf-8")
    assert '"state":"completed"' in state


def test_corruption_reports_incomplete_diff_and_forensic_backup(tmp_path: Path) -> None:
    target, _application, _linked, drift, *_rest = _service(tmp_path)
    (target / ".p2p" / "project.yml").write_text("project: [", encoding="utf-8")

    status = drift.status()
    difference = drift.semantic_diff()
    backup = drift.forensic_backup()

    assert status.classification == DriftClassification.structural_corruption
    assert difference.complete is False
    assert difference.entries == ()
    assert backup.verified is True
    assert backup.backup_ref.startswith("fr_")
    assert backup.to_dict()["physical_path_exposed"] is False
    assert (
        target / ".p2p-forensics" / (status.project_uuid or "unbound-project")
    ).is_dir()


def test_discard_preserves_forensic_copy_and_restores_authority(tmp_path: Path) -> None:
    target, _application, _linked, drift, *_rest = _service(tmp_path)
    _change_domain(target)

    with pytest.raises(ValueError, match="P2P_CONFIRMATION_REQUIRED"):
        drift.discard_and_rebuild(confirm=False)
    result = drift.discard_and_rebuild(confirm=True)

    assert result["status"] == "rebuilt"
    assert result["suspect_bytes_uploaded"] is False
    refreshed = ProjectApplicationService(target)
    linked = LinkedReplicaService(
        root=target,
        transport=drift.linked_replica.transport,
        credentials=_credentials(),
        snapshot_reader=refreshed.adapter.repository.snapshot,
        store=refreshed.adapter.linked_replicas,
    )
    verified = ReplicaDriftService(
        root=target, adapter=refreshed.adapter, linked_replica=linked
    ).status()
    assert verified.status == "healthy"


def test_mcp_exposes_only_read_only_drift_tools(tmp_path: Path, monkeypatch) -> None:
    target, _application, _linked, drift, *_rest = _service(tmp_path)
    _change_domain(target)
    monkeypatch.setattr(
        ProjectApplicationService,
        "_replica_drift_service",
        lambda _self: drift,
    )

    status = call_tool("p2p_replica_drift_status", {"root": str(target)})
    difference = call_tool(
        "p2p_replica_drift_diff", {"root": str(target), "limit": 10}
    )

    assert status["mutation_performed"] is False
    assert difference["mutation_performed"] is False
    assert "p2p_replica_drift_discard" not in call_tool.__globals__["TOOL_NAMES"]
    assert "p2p_replica_reconciliation_apply" not in call_tool.__globals__["TOOL_NAMES"]


def test_cli_and_mcp_status_are_sanitized_and_semantically_equal(
    tmp_path: Path, monkeypatch
) -> None:
    target, _application, _linked, drift, *_rest = _service(tmp_path)
    _change_domain(target)
    monkeypatch.setattr(
        ProjectApplicationService,
        "_replica_drift_service",
        lambda _self: drift,
    )

    cli = runner.invoke(
        app, ["drift", "status", "--root", str(target), "--format", "json"]
    )
    mcp = call_tool("p2p_replica_drift_status", {"root": str(target)})
    missing_confirmation = runner.invoke(
        app, ["drift", "discard", "--root", str(target), "--format", "json"]
    )

    assert cli.exit_code == 0
    assert cli_data(cli)["replica_drift_status"] == mcp["replica_drift_status"]
    assert cli_error(missing_confirmation)["code"] == "P2P_CONFIRMATION_REQUIRED"
    rendered = cli.stdout + missing_confirmation.stdout
    assert "/home/" not in rendered
    assert ".p2p/project" not in rendered


def test_standalone_drift_status_routes_to_local_memory_recovery(tmp_path: Path) -> None:
    application = ProjectApplicationService(tmp_path)
    application.init_project("Standalone recovery")

    status = application.replica_drift_status()

    assert status.status == "standalone"
    assert status.classification is None
    assert status.next_actions == (
        "p2p project memory backup",
        "p2p project memory restore preview",
    )
