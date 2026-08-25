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
from p2p_engine.core.workspace_schema import CURRENT_WORKSPACE_SCHEMA_VERSION


runner = CliRunner()

EXPECTED_JSON_OPERATIONS = frozenset(
    """
choice.governance-preflight
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
governance.status
governance.validate
impact.apply
impact.preview
init
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
project.freshness
project.memory.show
project.memory.status
project.metadata.apply
project.metadata.preview
project.metadata.show
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
proposal.show
proposal.update
proposal.vertical-coverage.import
proposal.vertical-coverage.preview
proposal.vertical-coverage.show
proposal.vertical-coverage.suggest
runtime.contract.apply
runtime.contract.preview
runtime.status
validate
version
vertical.inspect
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
    assert len(inventory) == 126
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
    assert payload["data"] == {
        "engine_version": __version__,
        "cli_contract_version": CLI_CONTRACT_VERSION,
        "workspace_schema_version": CURRENT_WORKSPACE_SCHEMA_VERSION,
        "vertical_pack_schema_version": PORTABLE_VERTICAL_SCHEMA_VERSION,
        "portable_package_format_version": PORTABLE_VERTICAL_PACKAGE_VERSION,
        "project_domain_contract": "p2p-project-domain/v1",
        "structure_source_contract": "p2p-structure-source/v1",
    }


@pytest.mark.cli
def test_version_text_reports_distinct_contracts() -> None:
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert f"P2P Engine {__version__}" in result.stdout
    assert f"workspace schema: {CURRENT_WORKSPACE_SCHEMA_VERSION}" in result.stdout
    assert f"vertical pack schema: {PORTABLE_VERTICAL_SCHEMA_VERSION}" in result.stdout
    assert f"portable package format: {PORTABLE_VERTICAL_PACKAGE_VERSION}" in result.stdout
