from __future__ import annotations

from p2p_engine import __version__
from p2p_engine.cli_contract import CLI_CONTRACT_VERSION
from p2p_engine.core.authority import (
    AUTHORITY_CONTEXT_SCHEMA,
    AUTHORITY_EVIDENCE_SCHEMA,
    LOCAL_AUTHORITY_POLICY_VERSION,
    PROJECT_AUTHORITY_SCHEMA,
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
    }
