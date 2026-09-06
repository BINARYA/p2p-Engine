from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.main import get_command
from typer.testing import CliRunner

from p2p_engine import __version__
from p2p_engine.cli import app
from p2p_engine.cli_contract import (
    CLI_CONTRACT_VERSION,
    error_envelope,
    exit_code_for_error,
    json_command_inventory,
    success_envelope,
)
from p2p_engine.core.portable_verticals import (
    PORTABLE_VERTICAL_PACKAGE_VERSION,
    PORTABLE_VERTICAL_SCHEMA_VERSION,
)
from p2p_engine.core.release_contracts import current_contract_versions
from p2p_engine.core.workspace_schema import CURRENT_WORKSPACE_SCHEMA_VERSION

runner = CliRunner()

EXPECTED_JSON_OPERATIONS = frozenset(
    """
auth.login
auth.logout
auth.status
choice.governance-preflight
choice.decide
choice.supersede
choice.transition-apply
choice.transition-preview
choice.withdraw
conflict.preview-update
conflict.show
conflict.update
contribution.add
contribution.list
context
decision.apply
decision.history
decision.impact
decision.ledger-repair-apply
decision.ledger-repair-preview
decision.preview
decision.projection-repair-apply
decision.projection-repair-preview
decision.record
decision.status
drift.backup
drift.diff
drift.discard
drift.report
drift.status
drift.verify
governance.status
governance.validate
impact.apply
impact.preview
init
integration.install
integration.profile
integration.refresh
integration.remove
integration.status
mutation.status
precedent.search
project.context
project.authority.capabilities
project.authority.rotate.apply
project.authority.rotate.preview
project.authority.rotate.status
project.authority.show
project.definition.apply
project.definition.preview
project.definition.show
project.definition.update
project.domain.clear
project.domain.set
project.domain.show
project.structure.add-section
project.structure.history
project.structure.reorder
project.structure.replace.apply
project.structure.replace.preview
project.structure.replace.status
project.structure.merge.apply
project.structure.merge.compare
project.structure.merge.preview
project.structure.merge.recover
project.structure.merge.status
project.structure.retained.inspect
project.structure.retained.list
project.structure.restore.apply
project.structure.restore.preview
project.structure.restore.recover
project.structure.restore.status
project.structure.retire.apply
project.structure.retire.preview
project.structure.retire.status
project.structure.show
project.structure.update-metadata
project.freshness
project.identity.adopt.apply
project.identity.adopt.preview
project.identity.copy-check
project.identity.derive.apply
project.identity.derive.preview
project.identity.show
project.identity.status
project.identity.transitions
project.memory.classification
project.memory.inspect
project.memory.verify
project.memory.bundle-export
project.memory.bundle-materialize
project.memory.snapshot-export
project.memory.archive-verify
project.memory.backup
project.memory.restore-preview
project.memory.restore-apply
project.memory.recovery-status
project.memory.show
project.memory.status
project.metadata.apply
project.metadata.preview
project.metadata.show
project.replication.compact
project.replication.feed
project.replication.initialize
project.replication.operation-status
project.replication.status
project.transfer.apply
project.transfer.preview
project.transfer.recover
project.transfer.status
wavekit.archive
wavekit.attach
wavekit.clone
wavekit.create-from-local
wavekit.delete-remote
wavekit.detach
wavekit.lifecycle.apply
wavekit.lifecycle.preview
wavekit.lifecycle.recover
wavekit.lifecycle.status
wavekit.publish-copy
wavekit.remove-local-replica
wavekit.replica.move
wavekit.replica.read-only
wavekit.replica.register-copy
wavekit.restore
wavekit.resume
wavekit.status
wavekit.suspend
wavekit.sync.catch-up
wavekit.sync.recover
sync.catch-up
sync.recover
sync.status
watch
project.progress
project.publish.import
project.publish.list
project.publish.prepare
project.publish.render
project.publish.review
project.publish.status
project.publish.validate
project.readiness.apply
project.readiness.gap
project.readiness.gaps
project.readiness.preview
project.readiness.questions.answer
project.readiness.questions.defer
project.readiness.questions.mute
project.readiness.questions.next
project.readiness.questions.reconcile-apply
project.readiness.questions.reconcile-preview
project.readiness.questions.reopen
project.readiness.questions.status
project.readiness.review
project.rubrics.show
project.section
project.sections
project.snapshot
project.vertical.adopt.apply
project.vertical.adopt.preview
project.vertical.export.apply
project.vertical.export.eligibility
project.vertical.export.preview
project.vertical.inspect
project.vertical.install.apply
project.vertical.install.preview
project.vertical.list
project.vertical.lock.repair
project.vertical.lock.show
project.vertical.migrate.apply
project.vertical.migrate.preview
project.vertical.package
project.vertical.scaffold
project.vertical.schema
project.vertical.select
project.vertical.show
project.vertical.validate
proposal.accept
proposal.contribution.add
proposal.contribution.list
proposal.contributions
proposal.create
proposal.defer
proposal.list
proposal.readiness.assess
proposal.reject
proposal.scope.set
proposal.scope.show
proposal.show
proposal.update
proposal.vertical-coverage.import
proposal.vertical-coverage.preview
proposal.vertical-coverage.show
proposal.vertical-coverage.suggest
reconcile.apply
reconcile.preview
runtime.contract.apply
runtime.contract.preview
runtime.status
status
validate
version
vertical.inspect
vertical.domain.inspect
vertical.domain.list
vertical.domain.search
vertical.draft.add-local
vertical.draft.create
vertical.draft.inspect
vertical.draft.materialize
vertical.draft.package
vertical.draft.publish
vertical.draft.update
vertical.draft.validate
vertical.login
vertical.list
vertical.logout
vertical.pull
vertical.registry.add
vertical.registry.list
vertical.registry.remove
vertical.search
vote.status
workspace.schema.status
workspace.transaction.resume
workspace.transaction.rollback
workspace.transaction.status
""".split()
)


@pytest.mark.unit
def test_cli_envelope_has_one_versioned_transport_shape() -> None:
    success = success_envelope("example", {"value": 1})
    failure = error_envelope("example", code="P2P_EXAMPLE", message="failed")

    assert tuple(success) == (
        "contract_version",
        "ok",
        "operation",
        "data",
        "warnings",
        "error",
    )
    assert tuple(failure) == tuple(success)
    assert success["contract_version"] == failure["contract_version"] == CLI_CONTRACT_VERSION
    assert failure["error"] == {
        "code": "P2P_EXAMPLE",
        "message": "failed",
        "details": {},
    }


@pytest.mark.unit
def test_cli_envelopes_match_golden_fixtures() -> None:
    fixtures = Path(__file__).parent / "fixtures" / "cli_contract"
    success = json.loads((fixtures / "success-v1.json").read_text(encoding="utf-8"))
    failure = json.loads((fixtures / "error-v1.json").read_text(encoding="utf-8"))

    assert success_envelope("example.read", {"value": 1}) == success
    assert error_envelope(
        "example.write",
        code="P2P_EXAMPLE_CONFLICT",
        message="Example conflict.",
        details={"state": "stale"},
    ) == failure


@pytest.mark.cli
def test_cli_json_operation_inventory_is_reviewed_and_guarded() -> None:
    inventory = json_command_inventory(get_command(app))

    assert frozenset(inventory) == EXPECTED_JSON_OPERATIONS
    assert len(inventory) == 231
    assert inventory["status"] == "text"
    assert inventory["vertical.inspect"] == "json"
    assert inventory["workspace.schema.status"] == "text"


@pytest.mark.cli
def test_cli_parser_errors_use_envelope_when_json_is_explicit() -> None:
    result = runner.invoke(app, ["version", "--format", "json", "--unknown"])

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert tuple(payload) == (
        "contract_version",
        "data",
        "error",
        "ok",
        "operation",
        "warnings",
    )
    assert payload["ok"] is False
    assert payload["operation"] == "version"
    assert payload["error"]["code"] == "P2P_CLI_INVALID_REQUEST"
    assert payload["data"] is None


@pytest.mark.cli
def test_cli_parser_errors_use_envelope_for_default_json_command() -> None:
    result = runner.invoke(app, ["vertical", "inspect"])

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["operation"] == "vertical.inspect"
    assert payload["error"]["code"] == "P2P_CLI_INVALID_REQUEST"
    assert "Missing argument" in payload["error"]["message"]


@pytest.mark.cli
def test_default_json_command_help_remains_human_click_help() -> None:
    result = runner.invoke(app, ["mutation", "status", "--help"])

    assert result.exit_code == 0
    assert "Usage:" in result.stdout
    assert not result.stdout.strip().startswith("{")


@pytest.mark.cli
def test_every_json_command_path_has_normalized_parser_failure() -> None:
    for operation in sorted(EXPECTED_JSON_OPERATIONS):
        result = runner.invoke(
            app,
            [*operation.split("."), "--format", "json", "--p2p-invalid-option"],
        )
        assert result.exit_code == 2, (operation, result.stdout, result.exception)
        payload = json.loads(result.stdout)
        assert payload["contract_version"] == CLI_CONTRACT_VERSION
        assert payload["ok"] is False
        assert payload["operation"] == operation
        assert payload["error"]["code"] == "P2P_CLI_INVALID_REQUEST"


@pytest.mark.unit
def test_cli_error_codes_map_to_stable_exit_classes() -> None:
    assert exit_code_for_error("P2P_CLI_INVALID_REQUEST") == 2
    assert exit_code_for_error("P2P_STATE_CONFLICT") == 3
    assert exit_code_for_error("P2P_PERMISSION_DENIED") == 4
    assert exit_code_for_error("P2P_REGISTRY_UNAVAILABLE") == 5
    assert exit_code_for_error("P2P_UNKNOWN_FAILURE") == 1


@pytest.mark.cli
def test_version_json_works_without_project_root() -> None:
    result = runner.invoke(app, ["version", "--format", "json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["contract_version"] == CLI_CONTRACT_VERSION
    assert payload["ok"] is True
    assert payload["operation"] == "version"
    assert payload["error"] is None
    assert payload["data"] == current_contract_versions()


@pytest.mark.cli
def test_version_text_reports_distinct_contracts() -> None:
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert f"P2P Engine {__version__}" in result.stdout
    assert f"workspace schema: {CURRENT_WORKSPACE_SCHEMA_VERSION}" in result.stdout
    assert f"vertical pack schema: {PORTABLE_VERTICAL_SCHEMA_VERSION}" in result.stdout
    assert f"portable package format: {PORTABLE_VERTICAL_PACKAGE_VERSION}" in result.stdout
    assert "vertical registry protocol version: p2p-vertical-registry/v2" in result.stdout
    assert "authority context schema: p2p-authority-context/v1" in result.stdout


@pytest.mark.cli
@pytest.mark.parametrize(
    ("state", "runtime_text"),
    [
        ("missing_contract", None),
        ("invalid_contract", "runtime_contract: [\n"),
        (
            "unsupported_contract",
            "runtime_contract:\n  schema_version: 999\nruntime:\n  p2p:\n    requires: '>=0'\n    recommended: 0.5.0\n",
        ),
        (
            "incompatible",
            "runtime_contract:\n  schema_version: 1\nruntime:\n  p2p:\n    requires: '<0.5.0'\n    recommended: 0.4.11\n",
        ),
    ],
)
@pytest.mark.parametrize("terminal_width", [40, 120])
def test_runtime_status_diagnostics_are_raw_json_at_any_width(
    tmp_path: Path,
    state: str,
    runtime_text: str | None,
    terminal_width: int,
) -> None:
    initialized = runner.invoke(app, ["init", "Runtime JSON", "--root", str(tmp_path)])
    assert initialized.exit_code == 0
    runtime_path = tmp_path / ".p2p" / "project" / "runtime.yml"
    if runtime_text is None:
        runtime_path.unlink()
    else:
        runtime_path.write_text(runtime_text, encoding="utf-8")

    result = runner.invoke(
        app,
        ["runtime", "status", "--format", "json", "--root", str(tmp_path)],
        terminal_width=terminal_width,
        color=True,
    )

    assert result.exit_code == 0
    assert "\x1b[" not in result.stdout
    payload = json.loads(result.stdout)
    assert payload["contract_version"] == CLI_CONTRACT_VERSION
    assert payload["ok"] is True
    assert payload["operation"] == "runtime.status"
    assert payload["data"]["state"] == state


@pytest.mark.cli
@pytest.mark.parametrize("terminal_width", [40, 120])
def test_validate_failure_preserves_structured_result_at_any_width(
    tmp_path: Path,
    terminal_width: int,
) -> None:
    initialized = runner.invoke(app, ["init", "Validation JSON", "--root", str(tmp_path)])
    assert initialized.exit_code == 0
    (tmp_path / ".p2p" / "project" / "runtime.yml").unlink()

    result = runner.invoke(
        app,
        ["validate", "--format", "json", "--root", str(tmp_path)],
        terminal_width=terminal_width,
        color=True,
    )

    assert result.exit_code == 2
    assert "\x1b[" not in result.stdout
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["operation"] == "validate"
    assert payload["error"]["code"] == "P2P266_RUNTIME_CONTRACT_MISSING"
    validation = payload["error"]["details"]["result"]
    assert validation["errors"] >= 1
    assert isinstance(validation["findings"], list)
    assert validation["findings"][0]["code"]
