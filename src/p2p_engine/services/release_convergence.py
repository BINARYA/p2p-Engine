from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from importlib import resources
from pathlib import Path
from typing import Iterable

from p2p_engine import __version__
from p2p_engine.core.governed_capabilities import GOVERNED_CAPABILITIES
from p2p_engine.core.release_contracts import current_contract_versions
from p2p_engine.core.vertical_registry import VERTICAL_REGISTRY_PROTOCOL_VERSION
from p2p_engine.services.agent_templates import agent_policy
from p2p_engine.services.public_surface_inventory import public_surface_snapshot

CONVERGENCE_GATE_CONTRACT = "p2p-0.6.6-convergence-gate/v1"
WAVEKIT_CLI_FIXTURE_BUNDLE_CONTRACT = "p2p-wavekit-cli-fixtures/v1"
WAVEKIT_CLI_FIXTURE_RESOURCE = "wavekit-cli-fixtures-v1.json"
RELEASE_LINE = "0.6.6"
SUPPORTED_RELEASE_PYTHONS = ("3.12",)


@dataclass(frozen=True)
class OperationTrace:
    requirement_group: str
    operation: str
    cli_paths: tuple[str, ...]
    mcp_tools: tuple[str, ...]
    capability: str
    authority_context: str
    receipt_evidence: str
    mcp_parity: str
    hosted_boundary: str
    fixture_group: str
    tests: tuple[str, ...]
    deferred: bool = False

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["cli_paths"] = list(self.cli_paths)
        payload["mcp_tools"] = list(self.mcp_tools)
        payload["tests"] = list(self.tests)
        return payload


@dataclass(frozen=True)
class ConvergenceIssue:
    code: str
    target: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def operation_traceability_inventory() -> tuple[OperationTrace, ...]:
    return (
        OperationTrace(
            requirement_group="P1 authority",
            operation="project.initialize",
            cli_paths=("p2p init",),
            mcp_tools=("p2p_init_project",),
            capability="project.initialize",
            authority_context="local_policy_or_external_attestation",
            receipt_evidence="mutation-receipt/schema-3 when operation key is supplied",
            mcp_parity="semantic_same_service",
            hosted_boundary="Engine records neutral AuthorityContext evidence; hosted services enforce access.",
            fixture_group="bootstrap",
            tests=(
                "tests/test_project_initialization_receipts.py",
                "tests/test_authority_contracts.py",
            ),
        ),
        OperationTrace(
            requirement_group="P1 authority",
            operation="project.authority.rotate",
            cli_paths=(
                "p2p project authority rotate preview",
                "p2p project authority rotate apply",
                "p2p project authority rotate status",
            ),
            mcp_tools=(),
            capability="project.authority.rotate",
            authority_context="local_policy_or_external_attestation",
            receipt_evidence="mutation-receipt/schema-3",
            mcp_parity="cli_only_privileged_authority_admin",
            hosted_boundary="Rotation changes project authority metadata only; provider policy stays external.",
            fixture_group="authority",
            tests=("tests/test_authority_rotation.py",),
        ),
        OperationTrace(
            requirement_group="P1 linked replica",
            operation="project.replica.manage",
            cli_paths=(
                "p2p wavekit clone",
                "p2p wavekit attach",
                "p2p wavekit status",
                "p2p sync status",
                "p2p sync catch-up",
                "p2p sync recover",
                "p2p watch",
                "p2p wavekit replica move",
                "p2p wavekit replica register-copy",
                "p2p wavekit replica read-only",
            ),
            mcp_tools=(
                "p2p_linked_replica_status",
                "p2p_linked_replica_catch_up",
            ),
            capability="project.replica.manage",
            authority_context="wavekit_authenticated_owner_and_server_capability",
            receipt_evidence=(
                "replica registration plus immutable operation receipt, change batch and cursor"
            ),
            mcp_parity="domain_reads_catch_up_domain_writes_route_status_and_catch_up_explicit",
            hosted_boundary=(
                "WaveKit authorizes replica registration and supplies logical snapshots; "
                "P2P materializes only through its selected local adapter."
            ),
            fixture_group="linked_replica",
            tests=(
                "tests/test_linked_replica.py",
                "tests/test_durable_project_replication.py",
            ),
        ),
        OperationTrace(
            requirement_group="P1 linked lifecycle",
            operation="project.lifecycle.manage",
            cli_paths=(
                "p2p wavekit lifecycle status",
                "p2p wavekit lifecycle preview",
                "p2p wavekit lifecycle apply",
                "p2p wavekit lifecycle recover",
                "p2p wavekit suspend",
                "p2p wavekit resume",
                "p2p wavekit detach",
                "p2p wavekit create-from-local",
                "p2p wavekit publish-copy",
                "p2p wavekit remove-local-replica",
                "p2p wavekit archive",
                "p2p wavekit restore",
                "p2p wavekit delete-remote",
            ),
            mcp_tools=(
                "p2p_project_lifecycle_status",
                "p2p_project_lifecycle_preview",
                "p2p_project_publication_list",
            ),
            capability="project.replica.manage",
            authority_context="wavekit_authenticated_owner_explicit_confirmation",
            receipt_evidence="lifecycle operation receipt, detach receipt and tombstone evidence",
            mcp_parity="status_preview_and_publication_reads_only_privileged_apply_cli",
            hosted_boundary=(
                "WaveKit authorizes lifecycle transitions; P2P stages and atomically "
                "activates only verified snapshots through the selected local adapter."
            ),
            fixture_group="linked_project_lifecycle",
            tests=("tests/test_project_lifecycle.py",),
        ),
        OperationTrace(
            requirement_group="P1 linked replica drift",
            operation="project.replica.reconcile",
            cli_paths=(
                "p2p drift status",
                "p2p drift verify",
                "p2p drift diff",
                "p2p drift backup",
                "p2p drift report",
                "p2p drift discard",
                "p2p reconcile preview",
                "p2p reconcile apply",
            ),
            mcp_tools=(
                "p2p_replica_drift_status",
                "p2p_replica_drift_diff",
            ),
            capability="project.replica.manage",
            authority_context="wavekit_authenticated_owner_current_plan_confirmation",
            receipt_evidence="forensic reference, exact plan digest and ordinary command receipt",
            mcp_parity="sanitized_status_and_diff_only_rebuild_and_apply_cli",
            hosted_boundary=(
                "WaveKit stores bounded logical health evidence only; suspect local "
                "files, database pages and Git state never cross the boundary."
            ),
            fixture_group="linked_replica_drift",
            tests=("tests/test_replica_drift.py",),
        ),
        OperationTrace(
            requirement_group="P2 domain and source",
            operation="project.domain.change",
            cli_paths=(
                "p2p project domain set",
                "p2p project domain clear",
                "p2p project domain show",
            ),
            mcp_tools=(
                "p2p_project_domain_set",
                "p2p_project_domain_clear",
                "p2p_project_domain_show",
            ),
            capability="project.domain.change",
            authority_context="subject_executor_separated",
            receipt_evidence="mutation-receipt/schema-3",
            mcp_parity="semantic_same_service_with_consent",
            hosted_boundary="Classification is advisory metadata and cannot select structure or grant moderation.",
            fixture_group="project_domain",
            tests=("tests/test_project_domain.py",),
        ),
        OperationTrace(
            requirement_group="P3 structure editing",
            operation="project.structure.edit",
            cli_paths=(
                "p2p project structure add-section",
                "p2p project structure update-metadata",
                "p2p project structure reorder",
                "p2p project structure show",
                "p2p project structure history",
            ),
            mcp_tools=(
                "p2p_project_structure_add_section",
                "p2p_project_structure_update_metadata",
                "p2p_project_structure_reorder_sections",
                "p2p_project_structure_show",
                "p2p_project_structure_history",
            ),
            capability="project.structure.edit",
            authority_context="subject_executor_separated",
            receipt_evidence="mutation-receipt/schema-3 plus structure event contract",
            mcp_parity="semantic_same_service_with_consent",
            hosted_boundary="Project-owned structure is detached from vertical lock and source releases.",
            fixture_group="project_structure",
            tests=("tests/test_project_structure.py",),
        ),
        OperationTrace(
            requirement_group="P4 memory classification",
            operation="project.memory.classify",
            cli_paths=(
                "p2p project memory classification",
                "p2p proposal scope show",
                "p2p proposal scope set",
            ),
            mcp_tools=(
                "p2p_project_memory_classification",
                "p2p_proposal_scope_show",
                "p2p_proposal_scope_set",
            ),
            capability="project.memory.classify",
            authority_context="subject_executor_separated",
            receipt_evidence="mutation-receipt/schema-3 plus memory-scope mutation contract",
            mcp_parity="semantic_same_service_with_consent",
            hosted_boundary="Scope is organization only; it cannot decide proposals or override readiness.",
            fixture_group="project_memory",
            tests=("tests/test_project_memory_classification.py",),
        ),
        OperationTrace(
            requirement_group="P5 readiness",
            operation="proposal.readiness.assess",
            cli_paths=("p2p proposal readiness assess",),
            mcp_tools=("p2p_proposal_readiness_assess",),
            capability="proposal.readiness.assess",
            authority_context="local_policy_existing_worker_key",
            receipt_evidence="mutation-receipt/schema-3 for keyed CLI worker apply",
            mcp_parity="same_assessment_semantics_protocol_native_mcp",
            hosted_boundary="Assessment is advisory evidence; it does not apply proposal decisions.",
            fixture_group="proposal_readiness",
            tests=("tests/test_proposal_readiness_write_contract.py",),
        ),
        OperationTrace(
            requirement_group="P5 readiness",
            operation="project.readiness.review",
            cli_paths=(
                "p2p project readiness review",
                "p2p project readiness gaps",
                "p2p project readiness questions status",
                "p2p project readiness questions next",
            ),
            mcp_tools=(
                "p2p_project_readiness_review",
                "p2p_project_readiness_gaps",
                "p2p_project_questions_status",
                "p2p_project_questions_next",
            ),
            capability="read_only",
            authority_context="not_required_read_only",
            receipt_evidence="not_applicable",
            mcp_parity="semantic_same_service_read_only",
            hosted_boundary="Readiness excludes retired/origin criteria and classification debt from scoring.",
            fixture_group="project_readiness",
            tests=("tests/test_project_readiness_service.py",),
        ),
        OperationTrace(
            requirement_group="P6 retirement",
            operation="project.structure.retire",
            cli_paths=(
                "p2p project structure retire preview",
                "p2p project structure retire apply",
                "p2p project structure retire status",
            ),
            mcp_tools=(
                "p2p_project_structure_retirement_preview",
                "p2p_project_structure_retirement_apply",
            ),
            capability="project.structure.retire",
            authority_context="subject_executor_separated",
            receipt_evidence="mutation-receipt/schema-3 plus retirement result contract",
            mcp_parity="semantic_same_service_with_consent",
            hosted_boundary="Disposition plan governs memory movement without reading project history as source.",
            fixture_group="project_structure_retirement",
            tests=("tests/test_project_structure.py",),
        ),
        OperationTrace(
            requirement_group="P7 registry v2",
            operation="vertical.remote.discovery",
            cli_paths=(
                "p2p vertical domain list",
                "p2p vertical domain search",
                "p2p vertical domain inspect",
                "p2p vertical search",
                "p2p vertical list",
            ),
            mcp_tools=(
                "p2p_vertical_domain_list",
                "p2p_vertical_domain_search",
                "p2p_vertical_domain_inspect",
                "p2p_vertical_release_list",
                "p2p_vertical_release_search",
            ),
            capability="read_only",
            authority_context="not_required_read_only",
            receipt_evidence="not_applicable",
            mcp_parity="semantic_same_service_remote_read",
            hosted_boundary="Registry v2 discovery is provider-neutral and cannot imply project authority.",
            fixture_group="registry_v2",
            tests=("tests/test_vertical_registry_remote.py",),
        ),
        OperationTrace(
            requirement_group="P7 registry v2",
            operation="vertical.remote.obtain",
            cli_paths=("p2p vertical pull",),
            mcp_tools=(),
            capability="read_only",
            authority_context="user_local_or_authenticated_registry_user",
            receipt_evidence="immutable cache metadata, no project mutation receipt",
            mcp_parity="cli_only_user_cache_write",
            hosted_boundary="Pull writes only the user cache and does not mutate the project.",
            fixture_group="registry_v2",
            tests=("tests/test_vertical_registry_remote.py",),
        ),
        OperationTrace(
            requirement_group="P8 export",
            operation="project.vertical.export",
            cli_paths=(
                "p2p project vertical export eligibility",
                "p2p project vertical export preview",
                "p2p project vertical export apply",
            ),
            mcp_tools=(
                "p2p_project_structure_export_eligibility",
                "p2p_project_structure_export_preview",
            ),
            capability="project.vertical.export",
            authority_context="subject_executor_separated",
            receipt_evidence="mutation-receipt/schema-3 plus export marker/result contract",
            mcp_parity="cli_apply_mcp_read_only_deferral",
            hosted_boundary="Authority does not grant publisher ownership, remote publication or moderation rights.",
            fixture_group="structure_export",
            tests=("tests/test_project_structure_export.py",),
        ),
        OperationTrace(
            requirement_group="P9 replacement",
            operation="project.structure.replace",
            cli_paths=(
                "p2p project structure replace preview",
                "p2p project structure replace apply",
                "p2p project structure replace status",
            ),
            mcp_tools=(
                "p2p_project_structure_replacement_inspect",
                "p2p_project_structure_replacement_preview",
            ),
            capability="project.structure.replace",
            authority_context="subject_executor_separated",
            receipt_evidence="mutation-receipt/schema-3 plus replacement result contract",
            mcp_parity="cli_apply_mcp_read_only_deferral",
            hosted_boundary="Replacement copies an exact release; it is not adopt, migrate, pull or subscription.",
            fixture_group="structure_replacement",
            tests=("tests/test_project_structure_replacement.py",),
        ),
        OperationTrace(
            requirement_group="P2-P7 worker authoring",
            operation="proposal.create",
            cli_paths=(
                "p2p proposal create",
                "p2p proposal list",
                "p2p proposal show",
            ),
            mcp_tools=(
                "p2p_proposal_create",
                "p2p_proposal_list",
                "p2p_proposal_show",
            ),
            capability="proposal.create",
            authority_context="local_policy_existing_worker_key",
            receipt_evidence="mutation-receipt/schema-3 for keyed CLI worker writes",
            mcp_parity="semantic_same_service_protocol_native_mcp",
            hosted_boundary="Proposal creation records explicit unassigned scope and no decision authority.",
            fixture_group="proposal_authoring",
            tests=("tests/test_proposal_read_contract.py",),
        ),
        OperationTrace(
            requirement_group="P2-P7 worker authoring",
            operation="proposal.update",
            cli_paths=(
                "p2p proposal update",
                "p2p proposal show",
            ),
            mcp_tools=(
                "p2p_proposal_update",
                "p2p_proposal_show",
            ),
            capability="proposal.update",
            authority_context="local_policy_existing_worker_key",
            receipt_evidence="mutation-receipt/schema-3 for keyed CLI worker writes",
            mcp_parity="semantic_same_service_protocol_native_mcp",
            hosted_boundary="Proposal updates do not decide or change implementation state.",
            fixture_group="proposal_authoring",
            tests=("tests/test_proposal_read_contract.py",),
        ),
        OperationTrace(
            requirement_group="P2-P7 worker authoring",
            operation="proposal.contribution.add",
            cli_paths=(
                "p2p proposal contribution add",
                "p2p proposal contribution list",
            ),
            mcp_tools=(
                "p2p_proposal_contribution_add",
                "p2p_proposal_contribution_list",
            ),
            capability="proposal.contribution.add",
            authority_context="local_policy_existing_worker_key",
            receipt_evidence="mutation-receipt/schema-3 for keyed CLI worker writes",
            mcp_parity="semantic_same_service_protocol_native_mcp",
            hosted_boundary="Proposal memory does not imply implementation, membership or governance decision.",
            fixture_group="proposal_authoring",
            tests=("tests/test_proposal_contribution_contract.py",),
        ),
        OperationTrace(
            requirement_group="P1 decisions",
            operation="proposal.decide",
            cli_paths=(
                "p2p decision preview",
                "p2p decision apply",
                "p2p decision status",
                "p2p decision history",
                "p2p decision impact",
            ),
            mcp_tools=(
                "p2p_proposal_decision_preview",
                "p2p_proposal_decision_apply",
                "p2p_proposal_decision_status",
                "p2p_proposal_decision_history",
                "p2p_proposal_decision_impact",
            ),
            capability="proposal.decide",
            authority_context="subject_executor_separated",
            receipt_evidence="append-only decision event plus typed AuthorityContext evidence",
            mcp_parity="semantic_same_service_with_consent",
            hosted_boundary="Decision capability and readiness override capability remain separate grants.",
            fixture_group="proposal_decisions",
            tests=("tests/test_proposal_decision_service.py",),
        ),
        OperationTrace(
            requirement_group="P6 vertical lifecycle",
            operation="project.vertical.install",
            cli_paths=(
                "p2p project vertical install preview",
                "p2p project vertical install apply",
            ),
            mcp_tools=(),
            capability="project.vertical.install",
            authority_context="local_policy_existing_unintegrated",
            receipt_evidence="mutation-receipt/schema-3 for CLI apply",
            mcp_parity="cli_only_project_vertical_mutation",
            hosted_boundary="Install adds one exact release without making it authoritative structure.",
            fixture_group="vertical_transition",
            tests=("tests/test_vertical_transition_impact.py",),
        ),
        OperationTrace(
            requirement_group="P6 vertical lifecycle",
            operation="project.vertical.adopt",
            cli_paths=(
                "p2p project vertical adopt preview",
                "p2p project vertical adopt apply",
            ),
            mcp_tools=(),
            capability="project.vertical.adopt",
            authority_context="local_policy_existing_unintegrated",
            receipt_evidence="mutation-receipt/schema-3 for CLI apply",
            mcp_parity="cli_only_project_vertical_mutation",
            hosted_boundary="Adopt affects vertical lifecycle metadata, not the detached project structure.",
            fixture_group="vertical_transition",
            tests=("tests/test_vertical_transition_impact.py",),
        ),
        OperationTrace(
            requirement_group="P6 vertical lifecycle",
            operation="project.vertical.migrate",
            cli_paths=(
                "p2p project vertical migrate preview",
                "p2p project vertical migrate apply",
            ),
            mcp_tools=(),
            capability="project.vertical.migrate",
            authority_context="local_policy_existing_unintegrated",
            receipt_evidence="mutation-receipt/schema-3 for CLI apply",
            mcp_parity="cli_only_project_vertical_mutation",
            hosted_boundary="Migration preserves evidence by exact mapping and does not replace structure.",
            fixture_group="vertical_transition",
            tests=("tests/test_vertical_transition_impact.py",),
        ),
        OperationTrace(
            requirement_group="P8 structure merge",
            operation="project.structure.merge",
            cli_paths=(
                "p2p project structure merge compare",
                "p2p project structure merge preview",
                "p2p project structure merge apply",
                "p2p project structure merge status",
                "p2p project structure merge recover",
            ),
            mcp_tools=("p2p_project_structure_merge_compare",),
            capability="project.structure.merge",
            authority_context="subject_executor_separated",
            receipt_evidence="mutation-receipt/schema-3 plus structure transition result",
            mcp_parity="cli_apply_mcp_read_only_deferral",
            hosted_boundary=(
                "Merge imports an explicit typed closure from one exact source without "
                "creating a release subscription or server persistence dependency."
            ),
            fixture_group="project_structure_merge_restore",
            tests=("tests/test_project_structure_merge_restore.py",),
        ),
        OperationTrace(
            requirement_group="P8 structure restore",
            operation="project.structure.restore",
            cli_paths=(
                "p2p project structure retained list",
                "p2p project structure retained inspect",
                "p2p project structure restore preview",
                "p2p project structure restore apply",
                "p2p project structure restore status",
                "p2p project structure restore recover",
            ),
            mcp_tools=("p2p_project_structure_retained_inspect",),
            capability="project.structure.restore",
            authority_context="subject_executor_separated",
            receipt_evidence="mutation-receipt/schema-3 plus structure transition result",
            mcp_parity="cli_apply_mcp_read_only_deferral",
            hosted_boundary=(
                "Restore uses one retained canonical snapshot as a forward revision and "
                "never rewinds non-structure project history."
            ),
            fixture_group="project_structure_merge_restore",
            tests=("tests/test_project_structure_merge_restore.py",),
        ),
    )


def obsolete_reference_allowlist() -> tuple[dict[str, str], ...]:
    return (
        {
            "path": "CHANGELOG.md",
            "pattern": "0.4.x release headings and notes",
            "reason": "immutable release history remains historically accurate",
        },
        {
            "path": "tests/fixtures/vertical_transition/legacy-0.4.7-characterization.json",
            "pattern": "legacy 0.4.7 characterization",
            "reason": "bounded regression fixture for historical behavior",
        },
    )


def packaged_resource_inventory() -> dict[str, object]:
    return {
        "contract_versions": current_contract_versions(),
        "packaged_resources": [
            "p2p_engine/resources/verticals/base_project",
            "p2p_engine/resources/verticals/board_game_design",
            "p2p_engine/resources/verticals/grant_document_design",
            "p2p_engine/resources/verticals/packaging_or_physical_product_design",
            "p2p_engine/resources/verticals/social_impact_program_design",
            "p2p_engine/resources/verticals/software_project",
            f"p2p_engine/resources/contracts/{WAVEKIT_CLI_FIXTURE_RESOURCE}",
        ],
        "ci_python_matrix": list(SUPPORTED_RELEASE_PYTHONS),
        "installed_wheel_smoke": {
            "script": "scripts/test-installed.sh",
            "selector": "pytest -m smoke",
            "required": True,
        },
    }


def validate_convergence_inventory() -> tuple[ConvergenceIssue, ...]:
    snapshot = public_surface_snapshot()
    cli_paths = set(snapshot.cli_paths)
    mcp_tools = set(snapshot.mcp_tools)
    governed = {item.capability for item in GOVERNED_CAPABILITIES}
    issues: list[ConvergenceIssue] = [
        ConvergenceIssue(issue.code, issue.target, issue.message)
        for issue in snapshot.issues
    ]
    for trace in operation_traceability_inventory():
        if trace.deferred:
            continue
        for path in trace.cli_paths:
            if path not in cli_paths:
                issues.append(
                    ConvergenceIssue(
                        "P2P_CONVERGENCE_UNKNOWN_CLI_PATH",
                        path,
                        f"{trace.operation} references an unregistered CLI path.",
                    )
                )
        for tool in trace.mcp_tools:
            if tool not in mcp_tools:
                issues.append(
                    ConvergenceIssue(
                        "P2P_CONVERGENCE_UNKNOWN_MCP_TOOL",
                        tool,
                        f"{trace.operation} references an unregistered MCP tool.",
                    )
                )
        if (
            trace.capability != "read_only"
            and trace.capability not in governed
            and not trace.deferred
        ):
            issues.append(
                ConvergenceIssue(
                    "P2P_CONVERGENCE_UNKNOWN_CAPABILITY",
                    trace.capability,
                    f"{trace.operation} references an undeclared governed capability.",
                )
            )
        if not trace.fixture_group:
            issues.append(
                ConvergenceIssue(
                    "P2P_CONVERGENCE_MISSING_FIXTURE_GROUP",
                    trace.operation,
                    "Trace entry lacks a fixture group.",
                )
            )
    return tuple(issues)


def convergence_gate_payload() -> dict[str, object]:
    snapshot = public_surface_snapshot()
    operations = [trace.to_dict() for trace in operation_traceability_inventory()]
    return {
        "contract_version": CONVERGENCE_GATE_CONTRACT,
        "release_line": RELEASE_LINE,
        "engine_version": __version__,
        "contract_versions": current_contract_versions(),
        "operation_inventory": operations,
        "operation_inventory_sha256": _sha256(operations),
        "public_surface": {
            "contract_version": snapshot.contract_version,
            "capability_catalog_version": snapshot.capability_catalog_version,
            "cli_path_count": len(snapshot.cli_paths),
            "mcp_tool_count": len(snapshot.mcp_tools),
            "semantic_sha256": snapshot.semantic_sha256,
        },
        "obsolete_reference_allowlist": list(obsolete_reference_allowlist()),
        "packaged_resource_inventory": packaged_resource_inventory(),
        "residual_risks": [],
        "issues": [issue.to_dict() for issue in validate_convergence_inventory()],
    }


def wavekit_cli_fixture_bundle() -> dict[str, object]:
    worker = agent_policy(
        "P2P Release Gate",
        ["generic"],
        "local",
    )["wavekit_cli_worker_contract"]
    assert isinstance(worker, dict)
    command_groups = [
        {
            "group": "preflight",
            "mutates_project": False,
            "commands": list(worker["preflight_commands"]),
        },
        {
            "group": "read",
            "mutates_project": False,
            "commands": list(worker["read_commands"]),
        },
        {
            "group": "registry_v2_read",
            "mutates_project": False,
            "commands": list(worker["registry_v2_read_commands"]),
        },
        {
            "group": "write",
            "mutates_project": True,
            "commands": list(worker["write_commands"]),
        },
        {
            "group": "recovery",
            "mutates_project": False,
            "commands": [str(worker["status_command"])],
        },
        {
            "group": "linked_replica_owner",
            "mutates_project": True,
            "commands": [
                "p2p wavekit clone REMOTE-ID --server SERVER --account-profile PROFILE --operation-key OWNER-KEY --target WORKSPACE --confirm --format json",
                "p2p wavekit attach REMOTE-ID --server SERVER --account-profile PROFILE --operation-key OWNER-KEY --root WORKSPACE --confirm --format json",
                "p2p wavekit replica move --operation-key OWNER-KEY --confirm --root WORKSPACE --format json",
                "p2p wavekit replica register-copy --operation-key OWNER-KEY --confirm --root WORKSPACE --format json",
            ],
        },
        {
            "group": "linked_replica_status",
            "mutates_project": False,
            "commands": [
                "p2p wavekit status --root WORKSPACE --format json",
                "p2p sync status --root WORKSPACE --format json",
                "p2p watch --max-events COUNT --root WORKSPACE --format json",
            ],
        },
        {
            "group": "linked_replica_sync",
            "mutates_project": True,
            "commands": [
                "p2p sync catch-up --root WORKSPACE --format json",
                "p2p sync recover --root WORKSPACE --format json",
            ],
        },
        {
            "group": "project_replication_worker",
            "mutates_project": True,
            "commands": [
                "p2p project replication initialize --authority-epoch EPOCH --project-revision REVISION --retention-batches COUNT --confirm --root WORKSPACE --format json",
                "p2p project replication status --root WORKSPACE --format json",
                "p2p project replication operation-status OPERATION-ID --root WORKSPACE --format json",
                "p2p project replication feed --after-revision REVISION --replica-id REPLICA-ID --limit COUNT --root WORKSPACE --format json",
                "p2p project replication compact --retain-after-revision REVISION --confirm --root WORKSPACE --format json",
                "p2p --replication-command-envelope COMMAND.json project domain set DOMAIN --name NAME --actor ACTOR --operation-key wavekit:<uuid> --root WORKSPACE --format json",
            ],
        },
        {
            "group": "linked_project_lifecycle_status",
            "mutates_project": False,
            "commands": [
                "p2p wavekit lifecycle status --root WORKSPACE --format json",
                "p2p wavekit lifecycle preview ACTION --operation-id OPERATION-ID --root WORKSPACE --format json",
            ],
        },
        {
            "group": "linked_project_lifecycle_owner",
            "mutates_project": True,
            "commands": [
                "p2p wavekit lifecycle apply ACTION --operation-id OPERATION-ID --preview-token PREVIEW --confirm --root WORKSPACE --format json",
                "p2p wavekit lifecycle recover OPERATION-ID --root WORKSPACE --format json",
                "p2p wavekit detach --operation-id OPERATION-ID --preview-token PREVIEW --target DETACHED-ROOT --local-owner OWNER --preserve-origin --as-independent --confirm --root WORKSPACE --format json",
                "p2p wavekit remove-local-replica --operation-id OPERATION-ID --preview-token PREVIEW --disposition archive --integration remove --archive-to ARCHIVE --confirm --root WORKSPACE --format json",
            ],
        },
        {
            "group": "linked_replica_drift_status",
            "mutates_project": False,
            "commands": [
                "p2p drift status --root WORKSPACE --format json",
                "p2p drift diff --root WORKSPACE --format json",
                "p2p reconcile preview --root WORKSPACE --format json",
            ],
        },
        {
            "group": "linked_replica_drift_owner",
            "mutates_project": True,
            "commands": [
                "p2p drift discard --confirm --root WORKSPACE --format json",
                "p2p reconcile apply --plan-digest SHA256 --confirm --root WORKSPACE --format json",
            ],
        },
        {
            "group": "linked_replica_server_snapshot",
            "mutates_project": False,
            "commands": [
                "p2p project memory snapshot-export --output-directory SNAPSHOT-DIR --root WORKSPACE --format json",
            ],
        },
    ]
    payload: dict[str, object] = {
        "contract_version": WAVEKIT_CLI_FIXTURE_BUNDLE_CONTRACT,
        "engine_version": __version__,
        "transport": {
            "kind": "cli_json",
            "envelope": str(worker["contract_version"]),
            "operation_key_format": str(worker["operation_key_format"]),
            "raw_operation_key_in_status_output": bool(
                worker["raw_operation_key_in_status_output"]
            ),
            "parse_human_text": bool(worker["parse_human_text"]),
            "mcp_stdio_transport": str(worker["mcp_stdio_transport"]),
        },
        "contract_versions": current_contract_versions(),
        "authority": {
            "project_authority_identity": "PROJECT-AUTHORITY-ID",
            "subject_identity": "ACTOR",
            "executor_identity": "EXECUTOR",
            "subject_executor_separated": True,
            "wavekit_membership_role_required": False,
            "mutable_owner_identity_is_project_authority": False,
        },
        "registry_v2": {
            "protocol_version": VERTICAL_REGISTRY_PROTOCOL_VERSION,
            "protocol_v1_behavior": "deterministic_rejection",
            "domain_filtering": "exact_external_id_only",
            "mutation_performed": False,
        },
        "mcp_policy": {
            "responses_are_cli_enveloped": False,
            "export_apply_available": False,
            "replacement_apply_available": False,
            "merge_compare_available": True,
            "retained_inspect_available": True,
            "merge_apply_available": False,
            "restore_apply_available": False,
            "registry_v2_reads_available": True,
            "linked_lifecycle_reads_available": True,
            "linked_drift_reads_available": True,
            "linked_lifecycle_apply_available": False,
            "linked_drift_apply_available": False,
        },
        "sanitization": {
            "root_placeholder": "<PROJECT_ROOT>",
            "operation_key_placeholder": "wavekit:<uuid>",
            "no_local_absolute_paths": True,
            "no_secrets_or_tokens": True,
        },
        "command_groups": command_groups,
        "operation_inventory_sha256": _sha256(
            [trace.to_dict() for trace in operation_traceability_inventory()]
        ),
    }
    payload["semantic_sha256"] = _sha256(
        {key: value for key, value in payload.items() if key != "semantic_sha256"}
    )
    return payload


def load_packaged_wavekit_cli_fixture_bundle() -> dict[str, object]:
    text = (
        resources.files("p2p_engine.resources.contracts")
        .joinpath(WAVEKIT_CLI_FIXTURE_RESOURCE)
        .read_text(encoding="utf-8")
    )
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("P2P_CONVERGENCE_FIXTURE_INVALID: expected JSON object")
    return payload


def fixture_commands(payload: dict[str, object]) -> tuple[str, ...]:
    groups = payload.get("command_groups")
    if not isinstance(groups, list):
        return ()
    commands: list[str] = []
    for group in groups:
        if not isinstance(group, dict):
            continue
        entries = group.get("commands")
        if isinstance(entries, list):
            commands.extend(str(item) for item in entries)
    return tuple(commands)


def validate_wavekit_cli_fixture_bundle(
    payload: dict[str, object],
) -> tuple[ConvergenceIssue, ...]:
    issues: list[ConvergenceIssue] = []
    if payload.get("contract_version") != WAVEKIT_CLI_FIXTURE_BUNDLE_CONTRACT:
        issues.append(
            ConvergenceIssue(
                "P2P_CONVERGENCE_FIXTURE_CONTRACT",
                "contract_version",
                "Unsupported fixture bundle contract.",
            )
        )
    if payload.get("engine_version") != __version__:
        issues.append(
            ConvergenceIssue(
                "P2P_CONVERGENCE_FIXTURE_VERSION",
                "engine_version",
                "Fixture engine version does not match installed package.",
            )
        )
    if payload.get("contract_versions") != current_contract_versions():
        issues.append(
            ConvergenceIssue(
                "P2P_CONVERGENCE_FIXTURE_CONTRACT_VERSIONS",
                "contract_versions",
                "Fixture contract tuple differs from the installed package.",
            )
        )
    authority = payload.get("authority")
    if not isinstance(authority, dict):
        issues.append(
            ConvergenceIssue(
                "P2P_CONVERGENCE_FIXTURE_AUTHORITY",
                "authority",
                "Fixture authority payload is missing or invalid.",
            )
        )
    else:
        if authority.get("wavekit_membership_role_required") is not False:
            issues.append(
                ConvergenceIssue(
                    "P2P_CONVERGENCE_FIXTURE_WAVEKIT_ROLE",
                    "authority.wavekit_membership_role_required",
                    "Fixture must not encode WaveKit membership role authority.",
                )
            )
        if authority.get("mutable_owner_identity_is_project_authority") is not False:
            issues.append(
                ConvergenceIssue(
                    "P2P_CONVERGENCE_FIXTURE_OWNER_AUTHORITY",
                    "authority.mutable_owner_identity_is_project_authority",
                    "Fixture must not model mutable owner identity as project authority.",
                )
            )
    registry = payload.get("registry_v2")
    if not isinstance(registry, dict) or registry.get("protocol_version") != (
        VERTICAL_REGISTRY_PROTOCOL_VERSION
    ):
        issues.append(
            ConvergenceIssue(
                "P2P_CONVERGENCE_FIXTURE_REGISTRY_PROTOCOL",
                "registry_v2.protocol_version",
                "Fixture must use the current registry-v2 protocol.",
            )
        )
    mcp_policy = payload.get("mcp_policy")
    if not isinstance(mcp_policy, dict):
        issues.append(
            ConvergenceIssue(
                "P2P_CONVERGENCE_FIXTURE_MCP_POLICY",
                "mcp_policy",
                "Fixture MCP policy payload is missing or invalid.",
            )
        )
    else:
        unavailable = (
            "export_apply_available",
            "replacement_apply_available",
            "linked_lifecycle_apply_available",
            "linked_drift_apply_available",
        )
        for key in unavailable:
            if mcp_policy.get(key) is not False:
                issues.append(
                    ConvergenceIssue(
                        "P2P_CONVERGENCE_FIXTURE_MCP_APPLY",
                        f"mcp_policy.{key}",
                        "Fixture must keep privileged MCP apply operations unavailable.",
                    )
                )
        for key in (
            "linked_lifecycle_reads_available",
            "linked_drift_reads_available",
        ):
            if mcp_policy.get(key) is not True:
                issues.append(
                    ConvergenceIssue(
                        "P2P_CONVERGENCE_FIXTURE_MCP_READ",
                        f"mcp_policy.{key}",
                        "Fixture must expose approved linked-project MCP reads.",
                    )
                )
    expected_sha = _sha256(
        {key: value for key, value in payload.items() if key != "semantic_sha256"}
    )
    if payload.get("semantic_sha256") != expected_sha:
        issues.append(
            ConvergenceIssue(
                "P2P_CONVERGENCE_FIXTURE_HASH",
                "semantic_sha256",
                "Fixture semantic hash does not match its content.",
            )
        )
    for command in fixture_commands(payload):
        issues.extend(_fixture_sanitization_issues(command))
    required = {
        "p2p version --format json",
        "p2p status --format json",
        "p2p project structure show --format json",
        "p2p project vertical export eligibility --format json",
        "p2p project vertical export apply --target build/vertical --output dist/vertical.p2pv --publisher PUBLISHER --id VERTICAL-ID --version VERSION --name NAME --license LICENSE --primary-domain-key DOMAIN --primary-domain-name NAME --lineage-mode independent --expected-structure-revision REV --expected-structure-checksum SHA256 --token TOKEN --idempotency-key wavekit:<uuid> --confirm --actor ACTOR --format json",
        "p2p project structure replace apply COORDINATE --expected-structure-revision REV --expected-memory-revision SHA256 --preview-token TOKEN --operation-key wavekit:<uuid> --plan replacement-plan.yml --actor ACTOR --confirm --format json",
        "p2p vertical domain list --registry REGISTRY --format json",
        "p2p vertical search software --registry REGISTRY --domain DOMAIN-ID --format json",
        "p2p mutation status --operation-key wavekit:<uuid> --format json",
        "p2p sync status --root WORKSPACE --format json",
        "p2p sync catch-up --root WORKSPACE --format json",
        "p2p project replication status --root WORKSPACE --format json",
        "p2p wavekit lifecycle status --root WORKSPACE --format json",
        "p2p wavekit lifecycle preview ACTION --operation-id OPERATION-ID --root WORKSPACE --format json",
        "p2p drift status --root WORKSPACE --format json",
        "p2p drift diff --root WORKSPACE --format json",
        "p2p reconcile preview --root WORKSPACE --format json",
    }
    missing = sorted(required - set(fixture_commands(payload)))
    for command in missing:
        issues.append(
            ConvergenceIssue(
                "P2P_CONVERGENCE_FIXTURE_COMMAND_MISSING",
                command,
                "Fixture bundle is missing a required worker command.",
            )
        )
    return tuple(issues)


def _fixture_sanitization_issues(command: str) -> tuple[ConvergenceIssue, ...]:
    forbidden = (
        "/home/",
        "/Users/",
        "/tmp/",
        "davide",
        "matteo",
        "secret",
        "password",
        "token:",
    )
    return tuple(
        ConvergenceIssue(
            "P2P_CONVERGENCE_FIXTURE_NOT_SANITIZED",
            command,
            f"Fixture command contains forbidden token {token!r}.",
        )
        for token in forbidden
        if token in command
    )


def _sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def sorted_json(payload: object) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def write_wavekit_cli_fixture_bundle(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(sorted_json(wavekit_cli_fixture_bundle()), encoding="utf-8")


def issue_codes(issues: Iterable[ConvergenceIssue]) -> tuple[str, ...]:
    return tuple(sorted(issue.code for issue in issues))
