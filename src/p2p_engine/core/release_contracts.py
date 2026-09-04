from __future__ import annotations

from p2p_engine import __version__
from p2p_engine.cli_contract import CLI_CONTRACT_VERSION
from p2p_engine.core.authority import (
    AUTHORITY_CONTEXT_SCHEMA,
    AUTHORITY_EVIDENCE_SCHEMA,
    LOCAL_AUTHORITY_POLICY_VERSION,
    PROJECT_AUTHORITY_SCHEMA,
)
from p2p_engine.core.authority_transfer import (
    AUTHORITY_TRANSFER_PROTOCOL,
    AUTHORITY_TRANSFER_RECEIPT_CONTRACT,
)
from p2p_engine.core.linked_replica import (
    LINKED_REPLICA_BINDING_CONTRACT,
    LINKED_REPLICA_CAPABILITY_CONTRACT,
    LINKED_REPLICA_CHANGE_CONTRACT,
    LINKED_REPLICA_PROTOCOL,
    LINKED_REPLICA_SNAPSHOT_CONTRACT,
)
from p2p_engine.core.mutation_receipts import MUTATION_RECEIPT_SCHEMA_VERSION
from p2p_engine.core.portable_verticals import (
    PORTABLE_VERTICAL_PACKAGE_VERSION,
    PORTABLE_VERTICAL_SCHEMA_VERSION,
)
from p2p_engine.core.project_domain import (
    PROJECT_DOMAIN_CONTRACT,
    STRUCTURE_SOURCE_CONTRACT,
)
from p2p_engine.core.project_integration import current_integration_versions
from p2p_engine.core.project_lifecycle import (
    DETACH_RECEIPT_CONTRACT,
    PROJECT_LIFECYCLE_CAPABILITY_CONTRACT,
    PROJECT_LIFECYCLE_LOCAL_STATE_CONTRACT,
    PROJECT_LIFECYCLE_PREVIEW_CONTRACT,
    PROJECT_LIFECYCLE_PROTOCOL,
    PROJECT_LIFECYCLE_RECEIPT_CONTRACT,
    PROJECT_LIFECYCLE_STATUS_CONTRACT,
    PROJECT_PUBLICATION_CONTRACT,
)
from p2p_engine.core.project_memory import (
    MEMORY_CLASSIFICATION_CONTRACT,
    PROJECT_MEMORY_SCOPE_CONTRACT,
    PROJECT_MEMORY_SCOPE_EVENTS_CONTRACT,
    PROJECT_MEMORY_SCOPE_MUTATION_CONTRACT,
)
from p2p_engine.core.project_readiness import (
    PROJECT_READINESS_ALGORITHM_VERSION,
    PROJECT_READINESS_CONTRACT,
    PROJECT_READINESS_CURSOR_POLICY_VERSION,
    PROJECT_READINESS_GAP_POLICY_VERSION,
)
from p2p_engine.core.project_readiness_convergence import (
    PROJECT_READINESS_CONVERGENCE_POLICY_VERSION,
)
from p2p_engine.core.project_replication import (
    PROJECT_ACTIVITY_CONTRACT,
    PROJECT_CHANGE_BATCH_CONTRACT,
    PROJECT_CHANGE_FEED_CONTRACT,
    PROJECT_COMMAND_CONTRACT,
    PROJECT_NOTIFICATION_CONTRACT,
    PROJECT_OPERATION_RECEIPT_CONTRACT,
    PROJECT_PRESENCE_CONTRACT,
    PROJECT_REPLICATION_PROTOCOL,
)
from p2p_engine.core.project_structure import (
    PROJECT_STRUCTURE_CONTRACT,
    PROJECT_STRUCTURE_EVENTS_CONTRACT,
    PROJECT_STRUCTURE_MUTATION_CONTRACT,
)
from p2p_engine.core.project_structure_export import (
    PROJECT_STRUCTURE_EXPORT_MARKER_CONTRACT,
    PROJECT_STRUCTURE_EXPORT_PREVIEW_CONTRACT,
    PROJECT_STRUCTURE_EXPORT_RESULT_CONTRACT,
)
from p2p_engine.core.project_structure_merge_restore import (
    STRUCTURE_COMPARISON_CONTRACT,
    STRUCTURE_MERGE_PLAN_CONTRACT,
    STRUCTURE_MERGE_PREVIEW_CONTRACT,
    STRUCTURE_RESTORE_PLAN_CONTRACT,
    STRUCTURE_RESTORE_PREVIEW_CONTRACT,
    STRUCTURE_SNAPSHOT_CONTRACT,
    STRUCTURE_SNAPSHOT_LEDGER_CONTRACT,
    STRUCTURE_TRANSITION_RESULT_CONTRACT,
)
from p2p_engine.core.project_structure_replacement import (
    STRUCTURE_REPLACEMENT_IMPACT_CONTRACT,
    STRUCTURE_REPLACEMENT_PLAN_CONTRACT,
    STRUCTURE_REPLACEMENT_RESULT_CONTRACT,
)
from p2p_engine.core.project_structure_retirement import (
    STRUCTURE_RETIREMENT_IMPACT_CONTRACT,
    STRUCTURE_RETIREMENT_PLAN_CONTRACT,
    STRUCTURE_RETIREMENT_RESULT_CONTRACT,
)
from p2p_engine.core.vertical_drafts import (
    VERTICAL_DRAFT_DOCUMENT_VERSION,
    VERTICAL_DRAFT_EVIDENCE_VERSION,
    VERTICAL_DRAFT_STATE_VERSION,
)
from p2p_engine.core.vertical_registry import (
    VERTICAL_REGISTRY_CONFIG_SCHEMA_VERSION,
    VERTICAL_REGISTRY_PROTOCOL_VERSION,
)
from p2p_engine.core.workspace_schema import (
    CURRENT_WORKSPACE_SCHEMA_VERSION,
    WORKSPACE_SCHEMA_CONTRACT_VERSION,
    WORKSPACE_SCHEMA_POLICY_VERSION,
)

RELEASE_CONTRACT_INVENTORY_VERSION = "p2p-release-contracts/v1"


def current_contract_versions() -> dict[str, object]:
    integration_versions = current_integration_versions()
    return {
        "contract_inventory_version": RELEASE_CONTRACT_INVENTORY_VERSION,
        "engine_version": __version__,
        "cli_contract_version": CLI_CONTRACT_VERSION,
        "workspace_schema_version": CURRENT_WORKSPACE_SCHEMA_VERSION,
        "workspace_schema_contract_version": WORKSPACE_SCHEMA_CONTRACT_VERSION,
        "workspace_schema_policy_version": WORKSPACE_SCHEMA_POLICY_VERSION,
        "vertical_pack_schema_version": PORTABLE_VERTICAL_SCHEMA_VERSION,
        "portable_package_format_version": PORTABLE_VERTICAL_PACKAGE_VERSION,
        "vertical_registry_protocol_version": VERTICAL_REGISTRY_PROTOCOL_VERSION,
        "vertical_registry_config_schema_version": VERTICAL_REGISTRY_CONFIG_SCHEMA_VERSION,
        "vertical_draft_document_contract": VERTICAL_DRAFT_DOCUMENT_VERSION,
        "vertical_draft_state_contract": VERTICAL_DRAFT_STATE_VERSION,
        "vertical_draft_evidence_contract": VERTICAL_DRAFT_EVIDENCE_VERSION,
        "project_domain_contract": PROJECT_DOMAIN_CONTRACT,
        "structure_source_contract": STRUCTURE_SOURCE_CONTRACT,
        "project_structure_contract": PROJECT_STRUCTURE_CONTRACT,
        "project_structure_events_contract": PROJECT_STRUCTURE_EVENTS_CONTRACT,
        "project_structure_mutation_contract": PROJECT_STRUCTURE_MUTATION_CONTRACT,
        "project_structure_export_preview_contract": PROJECT_STRUCTURE_EXPORT_PREVIEW_CONTRACT,
        "project_structure_export_result_contract": PROJECT_STRUCTURE_EXPORT_RESULT_CONTRACT,
        "project_structure_export_marker_contract": PROJECT_STRUCTURE_EXPORT_MARKER_CONTRACT,
        "structure_retirement_impact_contract": STRUCTURE_RETIREMENT_IMPACT_CONTRACT,
        "structure_retirement_plan_contract": STRUCTURE_RETIREMENT_PLAN_CONTRACT,
        "structure_retirement_result_contract": STRUCTURE_RETIREMENT_RESULT_CONTRACT,
        "structure_replacement_impact_contract": STRUCTURE_REPLACEMENT_IMPACT_CONTRACT,
        "structure_replacement_plan_contract": STRUCTURE_REPLACEMENT_PLAN_CONTRACT,
        "structure_replacement_result_contract": STRUCTURE_REPLACEMENT_RESULT_CONTRACT,
        "structure_comparison_contract": STRUCTURE_COMPARISON_CONTRACT,
        "structure_merge_plan_contract": STRUCTURE_MERGE_PLAN_CONTRACT,
        "structure_merge_preview_contract": STRUCTURE_MERGE_PREVIEW_CONTRACT,
        "structure_restore_plan_contract": STRUCTURE_RESTORE_PLAN_CONTRACT,
        "structure_restore_preview_contract": STRUCTURE_RESTORE_PREVIEW_CONTRACT,
        "structure_snapshot_contract": STRUCTURE_SNAPSHOT_CONTRACT,
        "structure_snapshot_ledger_contract": STRUCTURE_SNAPSHOT_LEDGER_CONTRACT,
        "structure_transition_result_contract": STRUCTURE_TRANSITION_RESULT_CONTRACT,
        "project_memory_scope_contract": PROJECT_MEMORY_SCOPE_CONTRACT,
        "project_memory_scope_events_contract": PROJECT_MEMORY_SCOPE_EVENTS_CONTRACT,
        "project_memory_scope_mutation_contract": PROJECT_MEMORY_SCOPE_MUTATION_CONTRACT,
        "memory_classification_contract": MEMORY_CLASSIFICATION_CONTRACT,
        "project_readiness_contract": PROJECT_READINESS_CONTRACT,
        "project_readiness_algorithm_version": PROJECT_READINESS_ALGORITHM_VERSION,
        "project_readiness_gap_policy_version": PROJECT_READINESS_GAP_POLICY_VERSION,
        "project_readiness_cursor_policy_version": PROJECT_READINESS_CURSOR_POLICY_VERSION,
        "project_readiness_convergence_policy_version": (
            PROJECT_READINESS_CONVERGENCE_POLICY_VERSION
        ),
        "project_authority_schema": PROJECT_AUTHORITY_SCHEMA,
        "authority_context_schema": AUTHORITY_CONTEXT_SCHEMA,
        "authority_evidence_schema": AUTHORITY_EVIDENCE_SCHEMA,
        "local_authority_policy_version": LOCAL_AUTHORITY_POLICY_VERSION,
        "mutation_receipt_schema_version": MUTATION_RECEIPT_SCHEMA_VERSION,
        "authority_transfer_protocol": AUTHORITY_TRANSFER_PROTOCOL,
        "authority_transfer_receipt_contract": AUTHORITY_TRANSFER_RECEIPT_CONTRACT,
        "linked_replica_protocol": LINKED_REPLICA_PROTOCOL,
        "linked_replica_capability_contract": LINKED_REPLICA_CAPABILITY_CONTRACT,
        "linked_replica_binding_contract": LINKED_REPLICA_BINDING_CONTRACT,
        "linked_replica_snapshot_contract": LINKED_REPLICA_SNAPSHOT_CONTRACT,
        "linked_replica_change_contract": LINKED_REPLICA_CHANGE_CONTRACT,
        "project_lifecycle_protocol": PROJECT_LIFECYCLE_PROTOCOL,
        "project_lifecycle_capability_contract": PROJECT_LIFECYCLE_CAPABILITY_CONTRACT,
        "project_lifecycle_preview_contract": PROJECT_LIFECYCLE_PREVIEW_CONTRACT,
        "project_lifecycle_receipt_contract": PROJECT_LIFECYCLE_RECEIPT_CONTRACT,
        "project_lifecycle_status_contract": PROJECT_LIFECYCLE_STATUS_CONTRACT,
        "project_lifecycle_local_state_contract": PROJECT_LIFECYCLE_LOCAL_STATE_CONTRACT,
        "project_detach_receipt_contract": DETACH_RECEIPT_CONTRACT,
        "project_publication_contract": PROJECT_PUBLICATION_CONTRACT,
        "project_replication_protocol": PROJECT_REPLICATION_PROTOCOL,
        "project_command_contract": PROJECT_COMMAND_CONTRACT,
        "project_operation_receipt_contract": PROJECT_OPERATION_RECEIPT_CONTRACT,
        "project_change_batch_contract": PROJECT_CHANGE_BATCH_CONTRACT,
        "project_change_feed_contract": PROJECT_CHANGE_FEED_CONTRACT,
        "project_notification_contract": PROJECT_NOTIFICATION_CONTRACT,
        "project_activity_contract": PROJECT_ACTIVITY_CONTRACT,
        "project_presence_contract": PROJECT_PRESENCE_CONTRACT,
        "linked_replica_server_snapshot_contract": (
            "p2p-linked-replica-server-snapshot/v1"
        ),
        "local_memory_schema_version": integration_versions["local_memory"],
        "domain_memory_contract_version": integration_versions["domain"],
        "project_bundle_contract_version": integration_versions["bundle"],
        "bundle_materialization_contract": "p2p-bundle-materialization/v1",
        "sync_protocol_version": integration_versions["sync"],
        "project_integration_contract_version": integration_versions["integration"],
    }
