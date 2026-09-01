from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from p2p_engine.core.project_domain import ProjectDomainRef
from p2p_engine.core.project_structure_replacement import (
    structure_replacement_plan_from_mapping,
)
from p2p_engine.core.project_structure_retirement import (
    structure_retirement_plan_from_mapping,
)
from p2p_engine.core.release_contracts import current_contract_versions
from p2p_engine.mcp.handlers.common import optional_string, required, to_jsonable
from p2p_engine.services.project_application import ProjectApplicationService as P2PWorkspace


def handle_project_tool(
    workspace: P2PWorkspace,
    name: str,
    arguments: dict[str, Any],
) -> dict[str, object] | None:
    if name == "p2p_integration_status":
        return {
            "project_integration": workspace.project_integration_status(),
            "mutation_performed": False,
        }
    if name == "p2p_project_identity_show":
        return {
            "project_identity": workspace.project_identity().to_dict(),
            "mutation_performed": False,
        }
    if name == "p2p_project_identity_status":
        return {
            "project_identity_status": workspace.project_identity_status().to_dict(),
            "mutation_performed": False,
        }
    if name == "p2p_project_identity_transitions":
        return {
            "identity_transitions": workspace.project_identity_transition_matrix(),
            "mutation_performed": False,
        }
    if name == "p2p_project_identity_copy_check":
        return {
            "project_copy_assessment": workspace.assess_project_copy(
                observed_project_uuid=required(arguments, "observed_project_uuid"),
                observed_replica_id=optional_string(arguments, "observed_replica_id") or "",
                intent=optional_string(arguments, "intent") or "",
            ).to_dict(),
            "mutation_performed": False,
        }
    if name == "p2p_project_identity_adopt_preview":
        actor_id = required(arguments, "actor_id")
        return {
            "project_identity_adoption": workspace.preview_project_identity_adoption(
                operation_key=required(arguments, "operation_key"),
                actor_id=actor_id,
                executor_id=str(arguments.get("executor_id") or actor_id),
                executor_kind=str(arguments.get("executor_kind") or "person"),
                channel="mcp",
            ).to_dict(),
            "mutation_performed": False,
        }
    if name == "p2p_project_identity_derive_preview":
        actor_id = required(arguments, "actor_id")
        return {
            "project_identity_derivation": workspace.preview_project_identity_derivation(
                operation_key=required(arguments, "operation_key"),
                actor_id=actor_id,
                executor_id=str(arguments.get("executor_id") or actor_id),
                executor_kind=str(arguments.get("executor_kind") or "person"),
                display_name=str(arguments.get("display_name") or ""),
                retain_lineage=bool(arguments.get("retain_lineage", True)),
                lineage_visibility=str(arguments.get("lineage_visibility") or "preserved"),
                channel="mcp",
            ).to_dict(),
            "mutation_performed": False,
        }
    if name in {
        "p2p_project_identity_adopt_apply",
        "p2p_project_identity_derive_apply",
    }:
        return _project_identity_mutation(workspace, name, arguments)
    if name == "p2p_project_domain_show":
        return {
            "project_domain": workspace.project_domain().to_dict(),
            "structure_source": workspace.project_structure_source(),
            "mutation_performed": False,
        }
    if name in {"p2p_project_domain_set", "p2p_project_domain_clear"}:
        return _project_domain_mutation(workspace, name, arguments)
    if name == "p2p_project_structure_show":
        include_retired = bool(arguments.get("include_retired", False))
        return {
            "project_structure": workspace.project_structure(
                include_retired=include_retired
            ).to_dict(include_retired=include_retired),
            "mutation_performed": False,
        }
    if name == "p2p_project_structure_history":
        return {
            "project_structure_history": workspace.project_structure_history(
                limit=int(arguments.get("limit", 20))
            ).to_dict(),
            "mutation_performed": False,
        }
    if name == "p2p_project_structure_export_eligibility":
        return {
            "project_structure_export_eligibility": workspace.project_structure_export_eligibility().to_dict(),
            "mutation_performed": False,
        }
    if name == "p2p_project_structure_export_preview":
        primary_domain = arguments.get("primary_domain")
        if not isinstance(primary_domain, dict):
            primary_domain = {}
        result = workspace.preview_project_structure_export(
            publisher=required(arguments, "publisher"),
            vertical_id=required(arguments, "vertical_id"),
            version=required(arguments, "version"),
            name=required(arguments, "name"),
            license_id=required(arguments, "license"),
            primary_domain=primary_domain,
            domain_tags=[
                str(item)
                for item in arguments.get("domain_tags", [])
                if str(item).strip()
            ]
            if isinstance(arguments.get("domain_tags", []), list)
            else [],
            lineage_mode=required(arguments, "lineage_mode"),
            parent_coordinate=optional_string(arguments, "parent_coordinate"),
            parent_semantic_checksum=optional_string(arguments, "parent_semantic_checksum"),
            description=optional_string(arguments, "description"),
            actor_id=str(arguments.get("actor_id") or "owner"),
            executor_id=str(arguments.get("executor_id") or arguments.get("actor_id") or "owner"),
        )
        return {
            "project_structure_export_preview": result.to_dict(),
            "mutation_performed": False,
        }
    if name == "p2p_project_structure_replacement_inspect":
        result = workspace.inspect_project_structure_replacement_target(
            required(arguments, "target")
        )
        return {
            "project_structure_replacement_inspection": result.to_dict(),
            "mutation_performed": False,
        }
    if name == "p2p_project_structure_replacement_preview":
        actor_id = required(arguments, "actor_id")
        result = workspace.preview_project_structure_replacement(
            target=required(arguments, "target"),
            expected_structure_revision=int(arguments.get("expected_structure_revision", 0)),
            expected_memory_revision=required(arguments, "expected_memory_revision"),
            actor_id=actor_id,
            executor_id=str(arguments.get("executor_id") or actor_id),
            executor_kind=str(arguments.get("executor_kind") or "person"),
            plan=_replacement_plan(arguments),
            channel="mcp",
            limit=int(arguments.get("limit", 100)),
        )
        return {
            "project_structure_replacement_preview": result.to_dict(),
            "mutation_performed": False,
        }
    if name == "p2p_project_structure_merge_compare":
        raw_selected = arguments.get("selected", [])
        if not isinstance(raw_selected, list) or not all(
            isinstance(item, dict) for item in raw_selected
        ):
            raise ValueError("P2P_STRUCTURE_SELECTION_INVALID: selected must be a list of objects")
        result = workspace.compare_project_structure_merge(
            source=required(arguments, "source"),
            selected=raw_selected,
            limit=int(arguments.get("limit", 250)),
        )
        return {
            "project_structure_merge_comparison": result.to_dict(),
            "mutation_performed": False,
        }
    if name == "p2p_project_structure_retained_inspect":
        result = workspace.inspect_retained_project_structure_revision(
            revision=int(arguments.get("revision", 0)),
            include_structure=bool(arguments.get("include_structure", False)),
        )
        return {
            "retained_project_structure": result,
            "mutation_performed": False,
        }
    if name in {
        "p2p_project_structure_add_section",
        "p2p_project_structure_update_metadata",
        "p2p_project_structure_reorder_sections",
    }:
        return _project_structure_mutation(workspace, name, arguments)
    if name == "p2p_project_structure_retirement_preview":
        return _project_structure_retirement_preview(workspace, arguments)
    if name == "p2p_project_structure_retirement_apply":
        return _project_structure_retirement_apply(workspace, arguments)
    if name == "p2p_project_memory_classification":
        return {
            "memory_classification": workspace.project_memory_classification().to_dict(
                limit=int(arguments.get("limit", 100))
            ),
            "mutation_performed": False,
        }
    if name == "p2p_canonical_memory_inspect":
        return {
            "canonical_memory": workspace.canonical_memory_inspect().to_dict(
                limit=int(arguments.get("limit", 4096))
            ),
            "mutation_performed": False,
        }
    if name == "p2p_canonical_memory_verify":
        return {
            "memory_verification": workspace.canonical_memory_verify().to_dict(),
            "mutation_performed": False,
        }
    if name == "p2p_project_bundle_export_metadata":
        return {
            "bundle_export": workspace.canonical_bundle_metadata().to_dict(),
            "mutation_performed": False,
        }
    if name == "p2p_project_archive_verify":
        return {
            "archive_verification": workspace.canonical_archive_verify(
                Path(required(arguments, "source"))
            ).to_dict(),
            "mutation_performed": False,
        }
    if name == "p2p_proposal_scope_show":
        return {
            "project_memory_scope": workspace.proposal_memory_scope(
                required(arguments, "proposal_id")
            ).to_dict(),
            "mutation_performed": False,
        }
    if name == "p2p_proposal_scope_set":
        return _project_memory_scope_mutation(workspace, arguments)
    if name == "p2p_agent_list":
        return {"agent_integrations": to_jsonable(workspace.agent_integrations_list())}
    if name == "p2p_agent_show":
        return {
            "agent_integration": to_jsonable(
                workspace.agent_integration_show(str(arguments.get("adapter") or "generic"))
            )
        }
    if name == "p2p_agent_doctor":
        return {"agent_doctor": to_jsonable(workspace.agent_doctor(str(arguments.get("adapter") or "all")))}
    if name == "p2p_validate":
        return {"validation": to_jsonable(workspace.validate())}
    if name == "p2p_context":
        return {
            "context": to_jsonable(
                workspace.context_packet(
                    budget=str(arguments.get("budget") or "small"),
                    target=optional_string(arguments, "target"),
                )
            )
        }
    if name == "p2p_assess_show":
        return {"assessment": to_jsonable(workspace.show_project_assessment())}
    if name == "p2p_project_rubrics_show":
        return {"rubrics": to_jsonable(workspace.show_project_rubrics())}
    if name == "p2p_maturity_show":
        return {"maturity": to_jsonable(workspace.show_definition_maturity())}
    if name == "p2p_intake_status":
        return {"intake_status": to_jsonable(workspace.intake_statuses())}
    if name == "p2p_project_brief_show":
        return {"operational_brief": workspace.show_project_brief()}
    if name == "p2p_choice_discover":
        return {"choice_discovery": to_jsonable(workspace.discover_choices())}
    if name == "p2p_conflict_status":
        return {"conflicts": to_jsonable(workspace.conflict_status())}
    if name == "p2p_governance_status":
        return {
            "governance_status": to_jsonable(workspace.governance_status()),
            "mutation_performed": False,
        }
    if name == "p2p_governance_validate":
        return {
            "governance_validation": to_jsonable(workspace.validate_governance_policy()),
            "mutation_performed": False,
        }
    if name == "p2p_choice_governance_preflight":
        return {
            "governance_preflight": to_jsonable(
                workspace.choice_governance_preflight(
                    required(arguments, "choice_id"),
                    option=required(arguments, "option"),
                    actor=required(arguments, "actor"),
                    precedent_id=optional_string(arguments, "precedent_id"),
                    tag=optional_string(arguments, "tag"),
                )
            ),
            "decision_made": False,
            "mutation_performed": False,
        }
    if name == "p2p_vote_status":
        return {
            "vote_status": to_jsonable(workspace.vote_status(required(arguments, "proposal_id"))),
            "mutation_performed": False,
        }
    if name == "p2p_precedent_search":
        return {
            "precedents": to_jsonable(
                workspace.search_decision_precedents(
                    precedent_id=optional_string(arguments, "precedent_id"),
                    proposal_id=optional_string(arguments, "proposal_id"),
                    choice_id=optional_string(arguments, "choice_id"),
                    tag=optional_string(arguments, "tag"),
                )
            ),
            "mutation_performed": False,
        }
    if name == "p2p_workspace_schema_status":
        return {
            "workspace_schema": workspace.workspace_schema_status().to_dict(),
            "contract_versions": current_contract_versions(),
            "mutation_performed": False,
        }
    if name == "p2p_proposal_vertical_coverage_show":
        return {
            "vertical_coverage": to_jsonable(
                workspace.proposal_vertical_coverage_status(required(arguments, "proposal_id"))
            ),
            "mutation_performed": False,
        }
    if name == "p2p_proposal_vertical_coverage_suggest":
        return {
            "vertical_coverage_suggestion": to_jsonable(
                workspace.suggest_proposal_vertical_coverage(required(arguments, "proposal_id"))
            ),
            "mutation_performed": False,
        }
    if name == "p2p_project_status":
        return {"project_status": to_jsonable(workspace.project_state_status())}
    if name == "p2p_project_progress":
        return {"project_progress": to_jsonable(workspace.project_progress()), "mutation_performed": False}
    if name == "p2p_project_freshness":
        return {"project_freshness": to_jsonable(workspace.project_freshness()), "mutation_performed": False}
    if name == "p2p_project_interaction_style_show":
        return {"interaction_style": to_jsonable(workspace.project_interaction_style())}
    if name == "p2p_project_interaction_style_set":
        return {
            "interaction_style": to_jsonable(
                workspace.set_project_interaction_style(
                    technical_verbosity=arguments.get("technical_verbosity"),
                    formality=arguments.get("formality"),
                    assertiveness=arguments.get("assertiveness"),
                    actor=str(arguments.get("actor") or "local"),
                )
            )
        }
    if name == "p2p_project_export":
        return {"export": to_jsonable(workspace.export_visible_project_definition())}
    if name == "p2p_project_export_status":
        return {"export_status": to_jsonable(workspace.visible_project_definition_export_status())}
    if name == "p2p_project_publish_prepare":
        return {
            "publication_prepare": to_jsonable(
                workspace.prepare_project_publication(
                    language=str(arguments.get("language") or "en"),
                    output_name=str(arguments.get("output_name") or "project"),
                    contributions=str(arguments.get("contributions") or "auto"),
                )
            )
        }
    if name == "p2p_project_publish_import":
        return {
            "publication_import": to_jsonable(
                workspace.import_project_publication(
                    Path(required(arguments, "source")),
                    model=(Path(str(arguments["model"])) if arguments.get("model") else None),
                    evidence_accounting=(
                        Path(str(arguments["evidence_accounting"]))
                        if arguments.get("evidence_accounting")
                        else None
                    ),
                    language=str(arguments.get("language") or "en"),
                    output_name=str(arguments.get("output_name") or "project"),
                )
            )
        }
    if name == "p2p_project_publish_validate":
        return {
            "publication_validation": to_jsonable(
                workspace.validate_project_publication(
                    language=str(arguments.get("language") or "en"),
                    output_name=str(arguments.get("output_name") or "project"),
                )
            )
        }
    if name == "p2p_project_publish_render":
        return {
            "publication_render": to_jsonable(
                workspace.render_project_publication(
                    language=str(arguments.get("language") or "en"),
                    output_name=str(arguments.get("output_name") or "project"),
                )
            )
        }
    if name == "p2p_project_publish_status":
        return {
            "publication_status": to_jsonable(
                workspace.project_publication_status(
                    language=str(arguments.get("language") or "en"),
                    output_name=str(arguments.get("output_name") or "project"),
                )
            )
        }
    if name == "p2p_project_publish_list":
        return {"publication_editions": to_jsonable(workspace.project_publication_editions())}
    if name == "p2p_project_vertical_list":
        return {
            "verticals": to_jsonable(workspace.project_verticals()),
            "active": to_jsonable(workspace.active_project_vertical()),
        }
    if name == "p2p_project_vertical_show":
        return {"vertical": to_jsonable(workspace.show_project_vertical(required(arguments, "vertical_id")))}
    if name == "p2p_project_vertical_validate":
        return {"validation": to_jsonable(workspace.validate_project_vertical(required(arguments, "target")))}
    if name == "p2p_project_vertical_select":
        modules = arguments.get("modules")
        if modules is not None and not isinstance(modules, list):
            raise ValueError("Expected list argument: modules")
        return {
            "active": to_jsonable(
                workspace.select_project_vertical(
                    required(arguments, "vertical_id"),
                    actor=str(arguments.get("actor") or "local"),
                    profile=str(arguments.get("profile") or "default"),
                    modules=[str(item) for item in modules if str(item).strip()] if isinstance(modules, list) else None,
                )
            ),
            "lock_status": to_jsonable(workspace.project_vertical_lock_status()),
            "definition": to_jsonable(workspace.project_definition_view()),
        }
    if name == "p2p_project_vertical_lock_show":
        return {"lock_status": to_jsonable(workspace.project_vertical_lock_status())}
    if name == "p2p_project_vertical_lock_repair":
        return {
            "lock": to_jsonable(
                workspace.repair_project_vertical_lock(actor=str(arguments.get("actor") or "local"))
            )
        }
    if name == "p2p_project_context":
        return {"project_context": to_jsonable(workspace.project_vertical_context())}
    if name == "p2p_project_sections":
        return {
            "sections": to_jsonable(
                workspace.project_vertical_sections(optional_string(arguments, "vertical_id"))
            )
        }
    if name == "p2p_project_section_show":
        return {
            "section": to_jsonable(
                workspace.project_vertical_section(
                    required(arguments, "section_id"),
                    optional_string(arguments, "vertical_id"),
                )
            )
        }
    if name == "p2p_project_definition_show":
        return {"definition": to_jsonable(workspace.project_definition_view())}
    if name == "p2p_project_definition_update":
        return {
            "definition_update": to_jsonable(
                workspace.update_project_definition(Path(required(arguments, "patch")))
            )
        }
    if name == "p2p_next":
        top = arguments.get("top")
        limit = int(top) if top is not None else None
        return {"next_actions": to_jsonable(workspace.next_actions(limit=limit))}
    if name == "p2p_choice_list":
        return {"choices": to_jsonable(workspace.choice_statuses())}
    if name == "p2p_choice_show":
        return {"choice": to_jsonable(workspace.show_choice(required(arguments, "choice_id")))}
    if name == "p2p_registry_status":
        return {"registry_status": to_jsonable(workspace.registry_status())}
    if name == "p2p_registry_show":
        return {"registry": to_jsonable(workspace.show_registry(required(arguments, "name")))}
    if name == "p2p_project_memory_status":
        return {
            "project_memory_status": to_jsonable(workspace.vertical_project_memory_status()),
            "mutation_performed": False,
        }
    if name == "p2p_project_memory_show":
        return {
            "project_memory": to_jsonable(
                workspace.show_vertical_project_memory(
                    section_id=optional_string(arguments, "section"),
                    include_history=bool(arguments.get("include_history") or False),
                    limit=int(arguments.get("limit", 20)),
                    cursor=str(arguments.get("cursor") or ""),
                )
            ),
            "mutation_performed": False,
        }
    if name == "p2p_project_show":
        section = required(arguments, "section")
        return {"section": section, "content": workspace.show_project_state(section)}
    return None


def _project_identity_mutation(
    workspace: P2PWorkspace,
    name: str,
    arguments: dict[str, Any],
) -> dict[str, object]:
    actor_id = required(arguments, "actor_id")
    consent_id = required(arguments, "consent_id")
    preview_token = required(arguments, "preview_token")
    kind = "adopt" if name == "p2p_project_identity_adopt_apply" else "derive"
    consent_operation = f"project_identity_{kind}_apply"
    consent_target = f"project-identity@{preview_token}"
    consent = workspace.consent_show(consent_id)
    if consent.status == "granted":
        workspace.consent_validate(
            consent_id,
            operation=consent_operation,
            target=consent_target,
            actor_id=actor_id,
        )
    elif consent.status != "consumed":
        raise ValueError(f"Consent receipt is not granted: {consent_id}")
    common = {
        "operation_key": required(arguments, "operation_key"),
        "actor_id": actor_id,
        "executor_id": str(arguments.get("executor_id") or actor_id),
        "executor_kind": str(arguments.get("executor_kind") or "person"),
        "preview_token": preview_token,
        "confirm": bool(arguments.get("confirm", False)),
        "channel": "mcp",
    }
    result = (
        workspace.apply_project_identity_adoption(**common)
        if kind == "adopt"
        else workspace.apply_project_identity_derivation(
            **common,
            display_name=str(arguments.get("display_name") or ""),
            retain_lineage=bool(arguments.get("retain_lineage", True)),
            lineage_visibility=str(arguments.get("lineage_visibility") or "preserved"),
        )
    )
    consumed = consent
    if consent.status == "granted" and result.status in {"applied", "already_applied"}:
        consumed = workspace.consent_consume(
            consent_id,
            result={
                "operation": consent_operation,
                "target": consent_target,
                "actor_id": actor_id,
                "project_uuid": result.current.project_uuid.value,
                "mutation_status": result.status,
            },
        )
    return {
        "project_identity_mutation": result.to_dict(),
        "consent": to_jsonable(consumed),
        "mutation_performed": result.status == "applied",
    }


def _project_domain_mutation(
    workspace: P2PWorkspace,
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, object]:
    operation = "set" if tool_name.endswith("_set") else "clear"
    consent_operation = f"project_domain_{operation}"
    actor_id = required(arguments, "actor_id")
    consent_id = required(arguments, "consent_id")
    consent = workspace.consent_show(consent_id)
    consent_sha256: str | None = None
    if consent.status == "granted":
        workspace.consent_validate(
            consent_id,
            operation=consent_operation,
            target="project-domain",
            actor_id=actor_id,
        )
        consent_sha256 = hashlib.sha256(
            workspace.read_governed_bytes(consent.path.as_posix())
        ).hexdigest()
    elif consent.status != "consumed":
        raise ValueError(f"Consent receipt is not granted: {consent_id}")
    descriptor = None
    if operation == "set":
        key = required(arguments, "key")
        descriptor = ProjectDomainRef(
            key=key,
            name=str(arguments.get("name") or key.replace("_", " ").replace("-", " ").title()),
            source=str(arguments.get("source") or "local"),
            external_ref=optional_string(arguments, "external_ref"),
        )
    result = workspace.change_project_domain(
        operation=operation,
        operation_key=required(arguments, "operation_key"),
        actor_id=actor_id,
        executor_id=str(arguments.get("executor_id") or actor_id),
        executor_kind=str(arguments.get("executor_kind") or "person"),
        descriptor=descriptor,
        channel="mcp",
        consent_id=consent_id,
        consent_sha256=consent_sha256,
    )
    consumed = consent
    if consent.status == "granted":
        consumed = workspace.consent_consume(
            consent_id,
            result={
                "operation": consent_operation,
                "target": "project-domain",
                "actor_id": actor_id,
                "project_memory_revision": result.current.project_memory_revision,
                "mutation_status": result.status,
            },
        )
    return {
        "project_domain_mutation": result.to_dict(),
        "consent": to_jsonable(consumed),
        "mutation_performed": result.status == "applied",
    }


def _project_structure_mutation(
    workspace: P2PWorkspace,
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, object]:
    operation_by_tool = {
        "p2p_project_structure_add_section": "add_section",
        "p2p_project_structure_update_metadata": "update_metadata",
        "p2p_project_structure_reorder_sections": "reorder_sections",
    }
    operation = operation_by_tool[tool_name]
    consent_operation = f"project_structure_{operation}"
    actor_id = required(arguments, "actor_id")
    consent_id = required(arguments, "consent_id")
    consent = workspace.consent_show(consent_id)
    consent_sha256: str | None = None
    if consent.status == "granted":
        workspace.consent_validate(
            consent_id,
            operation=consent_operation,
            target="project-structure",
            actor_id=actor_id,
        )
        consent_sha256 = hashlib.sha256(
            workspace.read_governed_bytes(consent.path.as_posix())
        ).hexdigest()
    elif consent.status != "consumed":
        raise ValueError(f"Consent receipt is not granted: {consent_id}")
    if operation == "add_section":
        request: dict[str, object] = {
            "title": required(arguments, "title"),
            "description": str(arguments.get("description") or ""),
            "required": bool(arguments.get("required", True)),
        }
        if optional_string(arguments, "section_id"):
            request["section_id"] = required(arguments, "section_id")
    elif operation == "update_metadata":
        request = {
            "element_kind": required(arguments, "element_kind"),
            "element_id": required(arguments, "element_id"),
        }
        if optional_string(arguments, "section_id"):
            request["section_id"] = required(arguments, "section_id")
        for key in ("title", "description", "required", "enabled", "priority", "keywords"):
            if key in arguments:
                request[key] = arguments[key]
    else:
        section_ids = arguments.get("section_ids")
        if not isinstance(section_ids, list):
            raise ValueError("Expected list argument: section_ids")
        request = {"section_ids": [str(item) for item in section_ids]}
    result = workspace.change_project_structure(
        operation=operation,
        operation_key=required(arguments, "operation_key"),
        expected_revision=int(arguments.get("expected_revision", 0)),
        actor_id=actor_id,
        executor_id=str(arguments.get("executor_id") or actor_id),
        executor_kind=str(arguments.get("executor_kind") or "person"),
        request=request,
        channel="mcp",
        consent_id=consent_id,
        consent_sha256=consent_sha256,
    )
    consumed = consent
    if consent.status == "granted":
        consumed = workspace.consent_consume(
            consent_id,
            result={
                "operation": consent_operation,
                "target": "project-structure",
                "actor_id": actor_id,
                "structure_revision": result.current.revision,
                "structure_checksum": result.current.checksum,
                "mutation_status": result.status,
            },
        )
    return {
        "project_structure_mutation": result.to_dict(),
        "consent": to_jsonable(consumed),
        "mutation_performed": result.status == "applied",
    }


def _project_structure_retirement_preview(
    workspace: P2PWorkspace,
    arguments: dict[str, Any],
) -> dict[str, object]:
    actor_id = required(arguments, "actor_id")
    result = workspace.preview_project_structure_retirement(
        targets=_retirement_targets(arguments),
        expected_structure_revision=int(arguments.get("expected_structure_revision", 0)),
        expected_memory_revision=required(arguments, "expected_memory_revision"),
        actor_id=actor_id,
        executor_id=str(arguments.get("executor_id") or actor_id),
        executor_kind=str(arguments.get("executor_kind") or "person"),
        plan=_retirement_plan(arguments),
        channel="mcp",
        limit=int(arguments.get("limit", 100)),
    )
    return {
        "project_structure_retirement_preview": result.to_dict(),
        "mutation_performed": False,
    }


def _project_structure_retirement_apply(
    workspace: P2PWorkspace,
    arguments: dict[str, Any],
) -> dict[str, object]:
    actor_id = required(arguments, "actor_id")
    consent_id = required(arguments, "consent_id")
    consent_operation = "project_structure_retire_apply"
    consent = workspace.consent_show(consent_id)
    consent_sha256: str | None = None
    if consent.status == "granted":
        workspace.consent_validate(
            consent_id,
            operation=consent_operation,
            target="project-structure",
            actor_id=actor_id,
        )
        consent_sha256 = hashlib.sha256(
            workspace.read_governed_bytes(consent.path.as_posix())
        ).hexdigest()
    elif consent.status != "consumed":
        raise ValueError(f"Consent receipt is not granted: {consent_id}")
    result = workspace.apply_project_structure_retirement(
        targets=_retirement_targets(arguments),
        expected_structure_revision=int(arguments.get("expected_structure_revision", 0)),
        expected_memory_revision=required(arguments, "expected_memory_revision"),
        preview_token=required(arguments, "preview_token"),
        operation_key=required(arguments, "operation_key"),
        confirm=bool(arguments.get("confirm", False)),
        actor_id=actor_id,
        executor_id=str(arguments.get("executor_id") or actor_id),
        executor_kind=str(arguments.get("executor_kind") or "person"),
        plan=_retirement_plan(arguments),
        channel="mcp",
        consent_id=consent_id,
        consent_sha256=consent_sha256,
        limit=int(arguments.get("limit", 100)),
    )
    consumed = consent
    if consent.status == "granted":
        consumed = workspace.consent_consume(
            consent_id,
            result={
                "operation": consent_operation,
                "target": "project-structure",
                "actor_id": actor_id,
                "structure_revision": result.current.revision,
                "structure_checksum": result.current.checksum,
                "memory_revision": result.current_memory_revision,
                "mutation_status": result.status,
            },
        )
    return {
        "project_structure_retirement": result.to_dict(),
        "consent": to_jsonable(consumed),
        "mutation_performed": result.status == "applied",
    }


def _retirement_targets(arguments: dict[str, Any]) -> list[dict[str, object]]:
    raw_targets = arguments.get("targets")
    if not isinstance(raw_targets, list) or not raw_targets:
        raise ValueError("Expected non-empty list argument: targets")
    targets: list[dict[str, object]] = []
    for item in raw_targets:
        if not isinstance(item, dict):
            raise ValueError("Expected object entries in argument: targets")
        targets.append(dict(item))
    return targets


def _retirement_plan(arguments: dict[str, Any]):
    raw_plan = arguments.get("plan")
    if raw_plan is None:
        return None
    if not isinstance(raw_plan, dict):
        raise ValueError("Expected object argument: plan")
    return structure_retirement_plan_from_mapping(raw_plan)


def _replacement_plan(arguments: dict[str, Any]):
    raw_plan = arguments.get("plan")
    if raw_plan is None:
        return None
    if not isinstance(raw_plan, dict):
        raise ValueError("Expected object argument: plan")
    return structure_replacement_plan_from_mapping(raw_plan)


def _project_memory_scope_mutation(
    workspace: P2PWorkspace,
    arguments: dict[str, Any],
) -> dict[str, object]:
    actor_id = required(arguments, "actor_id")
    proposal_id = required(arguments, "proposal_id")
    consent_id = required(arguments, "consent_id")
    consent_operation = "project_memory_scope_set"
    consent = workspace.consent_show(consent_id)
    consent_sha256: str | None = None
    if consent.status == "granted":
        workspace.consent_validate(
            consent_id,
            operation=consent_operation,
            target=f"proposal:{proposal_id}",
            actor_id=actor_id,
        )
        consent_sha256 = hashlib.sha256(
            workspace.read_governed_bytes(consent.path.as_posix())
        ).hexdigest()
    elif consent.status != "consumed":
        raise ValueError(f"Consent receipt is not granted: {consent_id}")
    raw_sections = arguments.get("section_ids", [])
    if not isinstance(raw_sections, list):
        raise ValueError("Expected list argument: section_ids")
    result = workspace.assign_proposal_memory_scope(
        proposal_id=proposal_id,
        kind=required(arguments, "kind"),
        section_ids=[str(item) for item in raw_sections],
        operation_key=required(arguments, "operation_key"),
        expected_memory_revision=required(arguments, "expected_memory_revision"),
        expected_structure_revision=int(arguments.get("expected_structure_revision", 0)),
        actor_id=actor_id,
        executor_id=str(arguments.get("executor_id") or actor_id),
        executor_kind=str(arguments.get("executor_kind") or "person"),
        channel="mcp",
        consent_id=consent_id,
        consent_sha256=consent_sha256,
    )
    consumed = consent
    if consent.status == "granted":
        consumed = workspace.consent_consume(
            consent_id,
            result={
                "operation": consent_operation,
                "target": f"proposal:{proposal_id}",
                "actor_id": actor_id,
                "scope_revision": result.current.revision,
                "memory_revision": result.current_memory_revision,
                "mutation_status": result.status,
            },
        )
    return {
        "project_memory_scope_mutation": result.to_dict(),
        "consent": to_jsonable(consumed),
        "mutation_performed": result.status == "applied",
    }
