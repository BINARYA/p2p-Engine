from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from p2p_engine.cli import app
from p2p_engine.core.authority import (
    AuthorityBasis,
    AuthorityClaim,
    AuthorityContext,
    AuthorityIdentity,
    AuthorityIdentityKind,
    AuthorityMode,
    AuthorityProjectBinding,
)
from p2p_engine.core.project_domain import ProjectDomainRef, StructureSource
from p2p_engine.mcp.tools import call_tool
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.cli_assertions import cli_data, cli_error


runner = CliRunner()


def _init_json(root: Path, *extra: str):
    return runner.invoke(
        app,
        [
            "init",
            "Domain Project",
            "--owner",
            "owner",
            "--operation-key",
            "domain-init-12345678",
            "--format",
            "json",
            *extra,
            "--root",
            str(root),
        ],
    )


def _tree_hash(root: Path, *, exclude_domain_state: bool = False) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if exclude_domain_state and (
            relative == ".p2p/project/domain.yml"
            or relative == ".p2p/.internal/mutation-receipts"
            or relative.startswith(".p2p/.internal/mutation-receipts/")
            or relative == ".p2p/.internal/workspace-transactions"
            or relative.startswith(".p2p/.internal/workspace-transactions/")
        ):
            continue
        digest.update(relative.encode("utf-8"))
        if path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()


def _external_context(capability: str, *, decision: str) -> AuthorityContext:
    return AuthorityContext(
        mode=AuthorityMode.external_attestation,
        project_authority=AuthorityProjectBinding(
            authority_id="hosted-authority-01",
            generation=1,
            provider_id="hosted-provider",
            provider_policy_version="project-capabilities-v1",
        ),
        subject=AuthorityIdentity("hosted-owner-01", AuthorityIdentityKind.user),
        executor=AuthorityIdentity("hosted-client-01", AuthorityIdentityKind.client),
        authorization_decision_id=decision,
        authorized_at="2026-08-25T12:00:00Z",
        claims=(
            AuthorityClaim(
                capability=capability,
                basis=AuthorityBasis.root_authority,
                authority_generation=1,
            ),
        ),
    )


def test_json_init_accepts_free_domain_with_explicit_generic_starter(tmp_path: Path) -> None:
    result = _init_json(tmp_path, "--domain", "gardening", "--starter", "generic")

    assert result.exit_code == 0, result.output
    payload = cli_data(result, operation="init")["project_init"]
    assert payload["domain"] == {
        "key": "gardening",
        "name": "Gardening",
        "source": "local",
        "external_ref": None,
    }
    assert payload["structure_source"] == {
        "kind": "starter",
        "starter_id": "generic",
    }
    project = yaml.safe_load((tmp_path / ".p2p/project.yml").read_text())
    assert "domain" not in project["project"]
    rubrics = yaml.safe_load((tmp_path / ".p2p/project/rubrics.yml").read_text())
    assert rubrics["structure_source"] == {
        "kind": "vertical_release",
        "coordinate": "binarya/base_project@2.0.0",
    }


def test_empty_starter_has_no_sections_or_readiness_criteria(tmp_path: Path) -> None:
    result = _init_json(
        tmp_path,
        "--domain",
        "lunar-gardening",
        "--starter",
        "empty",
    )

    assert result.exit_code == 0, result.output
    workspace = P2PWorkspace(tmp_path)
    assert workspace.active_project_vertical().vertical_id == "empty"
    assert workspace.project_vertical_sections() == []
    rubrics = workspace.show_project_rubrics()
    assert rubrics.structure_source == "empty"
    assert rubrics.criteria == []
    assert workspace.project_vertical_lock_status().status == "not_applicable"


def test_exact_pack_is_only_structure_source_for_unrelated_domain(tmp_path: Path) -> None:
    result = _init_json(
        tmp_path,
        "--domain",
        "automotive",
        "--vertical",
        "binarya/packaging_or_physical_product_design@2.0.0",
    )

    assert result.exit_code == 0, result.output
    payload = cli_data(result)["project_init"]
    assert payload["domain"]["key"] == "automotive"
    assert payload["structure_source"]["kind"] == "vertical_release"
    assert payload["structure_source"]["coordinate"] == (
        "binarya/packaging_or_physical_product_design@2.0.0"
    )
    sections = P2PWorkspace(tmp_path).project_vertical_sections()
    assert {item.section_id for item in sections} >= {
        "contained_product",
        "prototype_testing",
        "vision",
    }


def test_machine_init_requires_exactly_one_explicit_source(tmp_path: Path) -> None:
    missing = _init_json(tmp_path, "--domain", "gardening")

    assert missing.exit_code == 2
    assert cli_error(missing, operation="init")["code"] == "P2P_STRUCTURE_SOURCE_REQUIRED"
    assert not (tmp_path / ".p2p").exists()

    conflict = _init_json(
        tmp_path,
        "--starter",
        "generic",
        "--vertical",
        "binarya/software_project@2.0.0",
    )
    assert conflict.exit_code == 3
    assert cli_error(conflict, operation="init")["code"] == "P2P_STRUCTURE_SOURCE_CONFLICT"
    assert not (tmp_path / ".p2p").exists()


def test_domain_set_clear_replay_and_never_change_structure(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project(
        "Stable Structure",
        owner="owner",
        project_domain="gardening",
        starter_id="generic",
    )
    before_structure = _tree_hash(tmp_path, exclude_domain_state=True)
    before_revision = workspace._project_domain_service().project_memory_revision()

    descriptor = ProjectDomainRef("lunar-gardening", "Lunar Gardening")
    first = workspace.change_project_domain(
        operation="set",
        operation_key="domain-change-12345678",
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
        descriptor=descriptor,
    )
    replay = workspace.change_project_domain(
        operation="set",
        operation_key="domain-change-12345678",
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
        descriptor=descriptor,
    )

    assert first.status == "applied"
    assert replay.status == "already_applied"
    assert first.current.project_memory_revision == before_revision
    assert _tree_hash(tmp_path, exclude_domain_state=True) == before_structure
    with pytest.raises(ValueError, match="P2P_IDEMPOTENCY_CONFLICT"):
        workspace.change_project_domain(
            operation="set",
            operation_key="domain-change-12345678",
            actor_id="owner",
            executor_id="owner",
            executor_kind="person",
            descriptor=ProjectDomainRef("automotive", "Automotive"),
        )

    cleared = workspace.change_project_domain(
        operation="clear",
        operation_key="domain-clear-12345678",
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
        descriptor=None,
    )
    assert cleared.current.descriptor is None
    assert _tree_hash(tmp_path, exclude_domain_state=True) == before_structure


@pytest.mark.parametrize(
    "key",
    ["", "../garden", "garden/path", "Garden Space", "x" * 65, "garden\x00plot"],
)
def test_domain_key_rejects_unsafe_or_oversized_values(key: str) -> None:
    with pytest.raises(ValueError, match="P2P_PROJECT_DOMAIN_INVALID"):
        ProjectDomainRef(key, "Garden")


def test_domain_cli_reports_invalid_input_through_json_contract(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Invalid domain", owner="owner")

    result = runner.invoke(
        app,
        [
            "project",
            "domain",
            "set",
            "../unsafe",
            "--operation-key",
            "invalid-domain-12345678",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )

    assert result.exit_code != 0
    assert cli_error(result, operation="project.domain.set")["code"] == (
        "P2P_PROJECT_DOMAIN_INVALID"
    )


def test_structure_source_rejects_non_exact_coordinate_and_mismatched_origin() -> None:
    with pytest.raises(ValueError, match="P2P_STRUCTURE_SOURCE_INVALID"):
        StructureSource.vertical_release("software_project", "a" * 64)


def test_vertical_schema_three_domain_metadata_is_advisory_and_round_trips(
    tmp_path: Path,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Pack Metadata", starter_id="empty")
    pack = workspace.show_project_vertical("binarya/software_project@2.0.0")
    assert pack.schema_version == 3
    assert pack.manifest is not None
    assert pack.manifest.primary_domain == ProjectDomainRef(
        "software", "Software", source="system"
    )
    assert pack.manifest.domain_tags == ("technology",)
    payload = workspace._project_vertical_service().serialized_pack(pack)
    assert payload["vertical"]["manifest"]["primary_domain"]["key"] == "software"


def test_schema_two_vertical_is_rejected_without_conversion(tmp_path: Path) -> None:
    pack = tmp_path / "legacy-pack"
    (pack / "sections").mkdir(parents=True)
    (pack / "manifest.yml").write_text(
        yaml.safe_dump(
            {
                "manifest": {
                    "schema_version": 2,
                    "publisher": "test",
                    "id": "legacy",
                    "name": "Legacy",
                    "version": "1.0.0",
                    "license": "MIT",
                    "extends": None,
                    "lineage": {},
                    "dependencies": [],
                    "compatibility": {},
                }
            },
            sort_keys=False,
        )
    )
    (pack / "vertical.yml").write_text(
        yaml.safe_dump(
            {
                "vertical": {
                    "schema_version": 2,
                    "id": "legacy",
                    "name": "Legacy",
                    "version": "1.0.0",
                    "description": "Legacy schema",
                    "extends": None,
                }
            },
            sort_keys=False,
        )
    )
    (pack / "sections/010-scope.yml").write_text(
        "section:\n  id: scope\n  title: Scope\n  purpose: Scope.\n  required: true\n  priority: 10\n"
    )
    (pack / "rubrics.yml").write_text("rubrics: []\n")

    workspace = P2PWorkspace(tmp_path)
    result = workspace.validate_project_vertical(str(pack))
    assert result.valid is False
    assert any(item.code == "P2P_VERTICAL_UNSUPPORTED_SCHEMA" for item in result.issues)


def test_domain_change_rejects_unsupported_workspace_without_writes(
    tmp_path: Path,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Unsupported Domain", owner="owner")
    schema_path = tmp_path / ".p2p/project/workspace-schema.yml"
    schema = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    schema["workspace_schema"]["current_version"] = 3
    schema_path.write_text(yaml.safe_dump(schema, sort_keys=False), encoding="utf-8")
    domain_before = (tmp_path / ".p2p/project/domain.yml").read_bytes()

    with pytest.raises(ValueError, match="P2P_WORKSPACE_UNSUPPORTED_SCHEMA"):
        workspace.change_project_domain(
            operation="set",
            operation_key="unsupported-domain-12345678",
            actor_id="owner",
            executor_id="owner",
            executor_kind="person",
            descriptor=ProjectDomainRef("gardening", "Gardening"),
        )

    assert (tmp_path / ".p2p/project/domain.yml").read_bytes() == domain_before


def test_domain_change_fails_closed_while_workspace_transaction_is_active(
    tmp_path: Path,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Concurrent Domain", owner="owner")
    lock_path = tmp_path / ".p2p/.internal/workspace-transactions/apply.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(
        yaml.safe_dump(
            {
                "transaction_id": "concurrent-domain-test",
                "pid": os.getpid(),
                "acquired_at": "2026-08-25T12:00:00Z",
                "owner": "test",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    domain_before = (tmp_path / ".p2p/project/domain.yml").read_bytes()

    with pytest.raises(ValueError, match="P2P_GOVERNED_WRITE_BLOCKED_BY_TRANSACTION"):
        workspace.change_project_domain(
            operation="set",
            operation_key="concurrent-domain-12345678",
            actor_id="owner",
            executor_id="owner",
            executor_kind="person",
            descriptor=ProjectDomainRef("gardening", "Gardening"),
        )

    assert (tmp_path / ".p2p/project/domain.yml").read_bytes() == domain_before


def test_mcp_domain_mutation_requires_consent_and_replays_consumed_receipt(
    tmp_path: Path,
) -> None:
    call_tool(
        "p2p_init_project",
        {
            "root": str(tmp_path),
            "name": "MCP Domain",
            "owner": "owner",
            "starter": "generic",
        },
    )
    workspace = P2PWorkspace(tmp_path)
    consent = workspace.consent_grant(
        "project_domain_set",
        "project-domain",
        "owner",
        approved_by="owner",
    )
    arguments = {
        "root": str(tmp_path),
        "key": "automotive",
        "actor_id": "owner",
        "consent_id": consent.consent_id,
        "operation_key": "mcp-domain-12345678",
    }

    first = call_tool("p2p_project_domain_set", arguments)
    replay = call_tool("p2p_project_domain_set", arguments)

    assert first["project_domain_mutation"]["status"] == "applied"
    assert first["consent"]["status"] == "consumed"
    assert replay["project_domain_mutation"]["status"] == "already_applied"
    assert replay["consent"]["status"] == "consumed"


def test_external_authority_initialization_and_domain_change_bind_exact_claims(
    tmp_path: Path,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project(
        "Hosted Domain",
        starter_id="generic",
        authority_context=_external_context(
            "project.initialize",
            decision="hosted-init-decision-01",
        ),
    )
    context = _external_context(
        "project.domain.change",
        decision="hosted-domain-decision-01",
    )

    result = workspace.change_project_domain(
        operation="set",
        operation_key="external-domain-12345678",
        actor_id=context.subject.identity_id,
        executor_id=context.executor.identity_id,
        executor_kind=context.executor.kind.value,
        descriptor=ProjectDomainRef("gardening", "Gardening", source="external", external_ref="wk:domain:7"),
        authority_context=context,
    )
    status = workspace.mutation_status(idempotency_key="external-domain-12345678")

    assert result.status == "applied"
    assert status.authority is not None
    assert status.authority["subject"]["id"] == "hosted-owner-01"
    assert status.authority["executor"]["id"] == "hosted-client-01"
    assert status.authority["claims"] == [
        {
            "capability": "project.domain.change",
            "basis": "root_authority",
            "authority_generation": 1,
        }
    ]
