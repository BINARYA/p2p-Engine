from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from typer.testing import CliRunner

from p2p_engine.cli import app
from p2p_engine.core.mutation_preview import source_precondition
from p2p_engine.services.mutation_receipts import MutationReceiptService
from p2p_engine.services.workspace_transactions import (
    AtomicMutationWriter,
    WorkspaceTransactionRecoveryService,
)
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.cli_assertions import cli_data, cli_error


runner = CliRunner()
TARGET = ".p2p/project/definition.yml"


def _prepared_receipt(
    root: Path,
    *,
    key: str,
    candidate: bytes,
) -> tuple[MutationReceiptService, str, bytes, str]:
    service = MutationReceiptService(root=root, p2p_dir=root / ".p2p")
    fingerprint = service.fingerprint(
        operation="adopt",
        actor="owner",
        preview_token="preview-token",
        semantic_inputs={"coordinate": "test/example@1.0.0"},
    )
    receipt_path, receipt_content, _receipt = service.prepare(
        idempotency_key=key,
        operation="adopt",
        actor="owner",
        request_fingerprint_sha256=fingerprint,
        preview_token="preview-token",
        result={
            "impact_contract": "p2p-vertical-transition-impact/v1",
            "operation": "adopt",
            "operation_id": "project-vertical-adopt:test-example-1-0-0",
            "coordinate": "test/example@1.0.0",
            "analysis_fingerprint_sha256": "a" * 64,
            "plan_fingerprint_sha256": None,
            "semantic_postconditions": {
                "active_coordinate": "test/example@1.0.0",
                "lock_semantic_checksum": None,
                "lock_artifact_checksum": None,
                "definition_semantic_sha256": "b" * 64,
                "questions_semantic_sha256": None,
                "rubrics_semantic_sha256": None,
            },
            "decision_summary": [],
            "changed_paths": [TARGET],
        },
        candidates={TARGET: candidate},
    )
    return service, receipt_path, receipt_content, fingerprint


@pytest.mark.unit
def test_receipt_keys_are_required_bounded_and_status_not_found_is_redacted(
    tmp_path: Path,
) -> None:
    service = MutationReceiptService(root=tmp_path, p2p_dir=tmp_path / ".p2p")

    with pytest.raises(ValueError, match="P2P_IDEMPOTENCY_KEY_REQUIRED"):
        service.status("")
    with pytest.raises(ValueError, match="P2P_IDEMPOTENCY_KEY_INVALID"):
        service.status("x" * 257)

    key = "opaque-wavekit-operation"
    status = service.status(key)

    assert status.state == "not_found"
    assert key not in service.relative_path(key)
    assert key not in str(status.to_dict())


@pytest.mark.unit
def test_receipt_size_limit_rejects_oversized_typed_result(tmp_path: Path) -> None:
    service = MutationReceiptService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    fingerprint = service.fingerprint(
        operation="adopt",
        actor="owner",
        preview_token="preview-token",
        semantic_inputs={"coordinate": "test/example@1.0.0"},
    )
    with pytest.raises(ValueError, match="P2P_VERTICAL_IMPACT_LIMIT_EXCEEDED"):
        service.prepare(
            idempotency_key="oversized-result",
            operation="adopt",
            actor="owner-" + ("x" * 70_000),
            request_fingerprint_sha256=fingerprint,
            preview_token="preview-token",
            result={
                "impact_contract": "p2p-vertical-transition-impact/v1",
                "operation": "adopt",
                "operation_id": "project-vertical-adopt:test-example-1-0-0",
                "coordinate": "test/example@1.0.0",
                "analysis_fingerprint_sha256": "a" * 64,
                "plan_fingerprint_sha256": None,
                "semantic_postconditions": {
                    "active_coordinate": "test/example@1.0.0",
                    "lock_semantic_checksum": None,
                    "lock_artifact_checksum": None,
                    "definition_semantic_sha256": "b" * 64,
                    "questions_semantic_sha256": None,
                    "rubrics_semantic_sha256": None,
                },
                "decision_summary": [],
                "changed_paths": [TARGET],
            },
            candidates={TARGET: b"candidate"},
        )


@pytest.mark.unit
def test_corrupt_or_duplicate_key_receipt_fails_closed(tmp_path: Path) -> None:
    service = MutationReceiptService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    key = "corrupt-operation"
    path = tmp_path / service.relative_path(key)
    path.parent.mkdir(parents=True)
    path.write_text(
        "mutation_receipt:\n"
        "  schema_version: 2\n"
        "  schema_version: 2\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="P2P_IDEMPOTENCY_RECEIPT_CORRUPT"):
        service.status(key)


@pytest.mark.unit
def test_writer_allows_only_hashed_receipts_in_internal_namespace(tmp_path: Path) -> None:
    target = tmp_path / TARGET
    target.parent.mkdir(parents=True)
    target.write_bytes(b"before")
    disallowed = ".p2p/.internal/mutation-receipts/not-a-hash.yml"

    result = AtomicMutationWriter(root=tmp_path, p2p_dir=tmp_path / ".p2p").apply(
        operation_id="unsafe-internal-target",
        candidates={disallowed: b"content"},
        sources=(source_precondition(disallowed, None),),
        preview_token="preview-token",
        actor="owner",
    )

    assert result.status == "failed"
    assert "outside allowed canonical paths" in result.message
    assert not (tmp_path / disallowed).exists()


@pytest.mark.service
def test_receipt_and_domain_candidate_roll_back_together_on_injected_failure(
    tmp_path: Path,
) -> None:
    target = tmp_path / TARGET
    target.parent.mkdir(parents=True)
    target.write_bytes(b"before")
    key = "rolled-back-operation"
    service, receipt_path, receipt_content, _fingerprint = _prepared_receipt(
        tmp_path,
        key=key,
        candidate=b"after",
    )
    replacements = 0

    def fail_after_domain_write(stage: str, _target: str) -> None:
        nonlocal replacements
        if stage == "after_replace":
            replacements += 1
            if replacements == 2:
                raise RuntimeError("injected failure")

    result = AtomicMutationWriter(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        failure_injector=fail_after_domain_write,
    ).apply(
        operation_id="receipt-rollback",
        candidates={TARGET: b"after", receipt_path: receipt_content},
        sources=(
            source_precondition(TARGET, b"before"),
            source_precondition(receipt_path, None),
        ),
        preview_token="preview-token",
        actor="owner",
    )

    assert result.status == "rolled_back"
    assert target.read_bytes() == b"before"
    assert not (tmp_path / receipt_path).exists()
    assert service.status(key).state == "not_found"


@pytest.mark.service
def test_interrupted_receipt_transaction_reports_incomplete_and_resumes_safely(
    tmp_path: Path,
) -> None:
    target = tmp_path / TARGET
    target.parent.mkdir(parents=True)
    target.write_bytes(b"before")
    key = "recovery-operation"
    service, receipt_path, receipt_content, _fingerprint = _prepared_receipt(
        tmp_path,
        key=key,
        candidate=b"after",
    )
    live_receipt = tmp_path / receipt_path

    def interrupt_receipt(stage: str, relative: str) -> None:
        if stage == "after_replace" and relative == receipt_path:
            live_receipt.write_bytes(b"external-interruption")
            raise RuntimeError("injected interruption")

    result = AtomicMutationWriter(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        failure_injector=interrupt_receipt,
    ).apply(
        operation_id="receipt-recovery",
        candidates={TARGET: b"after", receipt_path: receipt_content},
        sources=(
            source_precondition(TARGET, b"before"),
            source_precondition(receipt_path, None),
        ),
        preview_token="preview-token",
        actor="owner",
    )

    status = service.status(key)
    assert result.status == "recovery_required"
    assert status.state == "incomplete"
    assert status.recovery_required is True
    assert status.transaction_id

    live_receipt.write_bytes(receipt_content)
    recovery = WorkspaceTransactionRecoveryService(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
    )
    resumed = recovery.resume(
        transaction_id=status.transaction_id,
        actor="owner",
        confirm=True,
    )

    assert resumed.status == "applied"
    assert target.read_bytes() == b"after"
    assert service.status(key).state == "applied"
    assert recovery.status().required is False


@pytest.mark.cli
def test_mutation_status_cli_returns_not_found_and_typed_corruption(tmp_path: Path) -> None:
    P2PWorkspace(tmp_path).init_project("Mutation status", owner="owner")
    key = "missing-operation"
    missing = runner.invoke(
        app,
        [
            "mutation",
            "status",
            "--idempotency-key",
            key,
            "--root",
            str(tmp_path),
            "--format",
            "json",
        ],
    )

    assert missing.exit_code == 0
    assert cli_data(missing)["state"] == "not_found"
    assert key not in missing.stdout

    missing_text = runner.invoke(
        app,
        [
            "mutation",
            "status",
            "--idempotency-key",
            key,
            "--root",
            str(tmp_path),
            "--format",
            "text",
        ],
    )
    assert missing_text.exit_code == 0
    assert "state: not_found" in missing_text.stdout
    assert key not in missing_text.stdout

    service = MutationReceiptService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    corrupt_path = tmp_path / service.relative_path(key)
    corrupt_path.parent.mkdir(parents=True)
    corrupt_path.write_bytes(b"not: [valid")
    corrupt = runner.invoke(
        app,
        [
            "mutation",
            "status",
            "--idempotency-key",
            key,
            "--root",
            str(tmp_path),
            "--format",
            "json",
        ],
    )

    assert corrupt.exit_code == 1
    assert cli_error(corrupt)["code"] == "P2P_IDEMPOTENCY_RECEIPT_CORRUPT"
    assert key not in corrupt.stdout


@pytest.mark.cli
def test_mutation_status_cli_accepts_wavekit_operation_key_alias(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Mutation status alias", owner="owner")
    proposal = workspace.create_proposal_with_details(
        title="Classified status",
        problem="WaveKit needs to inspect retries by operation key.",
        proposal="Expose mutation status through a WaveKit-facing alias.",
    )
    operation_key = f"wavekit:{uuid4()}"
    added = runner.invoke(
        app,
        [
            "proposal",
            "contribution",
            "add",
            proposal.proposal_id,
            "Check status through the operation key.",
            "--type",
            "suggestion",
            "--author",
            "supporter",
            "--operation-key",
            operation_key,
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )
    assert added.exit_code == 0, added.output

    status = runner.invoke(
        app,
        [
            "mutation",
            "status",
            "--operation-key",
            operation_key,
            "--root",
            str(tmp_path),
        ],
    )

    assert status.exit_code == 0, status.output
    data = cli_data(status, operation="mutation.status")
    assert data["state"] == "applied"
    assert data["operation"] == "proposal_contribution_add"
    assert data["operation_key"] == {
        "classification": "wavekit_uuid",
        "raw_value_returned": False,
    }
    assert operation_key not in status.stdout
