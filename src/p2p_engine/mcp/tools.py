from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from p2p_engine.core.contribution import ContributionType
from p2p_engine.core.decision import DecisionOutcome
from p2p_engine.storage.git import commit_all, head_commit, push_branch
from p2p_engine.storage.filesystem import P2PWorkspace, ProposalMergeConflict


TOOL_NAMES = (
    "p2p_init_project",
    "p2p_agent_instructions_refresh",
    "p2p_registry_refresh",
    "p2p_validate",
    "p2p_context",
    "p2p_assess_refresh",
    "p2p_assess_show",
    "p2p_project_rubrics_init",
    "p2p_project_rubrics_show",
    "p2p_maturity_refresh",
    "p2p_maturity_show",
    "p2p_proposal_create",
    "p2p_proposal_update",
    "p2p_proposal_contribution_add",
    "p2p_proposal_contribution_list",
    "p2p_intake_prompt",
    "p2p_intake_status",
    "p2p_project_brief_prompt",
    "p2p_project_brief_show",
    "p2p_choice_discover",
    "p2p_conflict_status",
    "p2p_impact_prompt",
    "p2p_project_status",
    "p2p_next",
    "p2p_next_add",
    "p2p_next_complete",
    "p2p_next_retire",
    "p2p_next_refresh",
    "p2p_proposal_list",
    "p2p_proposal_show",
    "p2p_proposal_readiness_get",
    "p2p_proposal_readiness_init",
    "p2p_proposal_readiness_refresh",
    "p2p_proposal_readiness_explain",
    "p2p_proposal_readiness_list_gaps",
    "p2p_choice_list",
    "p2p_choice_show",
    "p2p_change_status",
    "p2p_change_show",
    "p2p_change_tasks",
    "p2p_work_list",
    "p2p_work_status",
    "p2p_work_show",
    "p2p_registry_status",
    "p2p_registry_show",
    "p2p_project_show",
    "p2p_project_remote_show",
    "p2p_project_remote_configure",
    "p2p_permissions_show",
    "p2p_consent_request",
    "p2p_consent_status",
    "p2p_consent_show",
    "p2p_sync_status",
    "p2p_sync_fetch",
    "p2p_sync_pull",
    "p2p_sync_push",
    "p2p_proposal_draft_commit",
    "p2p_proposal_branch",
    "p2p_proposal_branch_status",
    "p2p_proposal_publish",
    "p2p_proposal_request_review",
    "p2p_proposal_accept",
    "p2p_proposal_reject",
    "p2p_proposal_defer",
    "p2p_proposal_accept_branch",
    "p2p_proposal_reject_branch",
    "p2p_proposal_merge",
    "p2p_proposal_finalize",
    "p2p_proposal_cleanup",
    "p2p_proposal_branch_scan",
    "p2p_spec_status",
    "p2p_spec_show",
    "p2p_spec_export_status",
    "p2p_spec_export_show",
    "p2p_change_create",
    "p2p_project_refresh",
    "p2p_spec_refresh",
    "p2p_spec_export",
    "p2p_spec_export_validate",
    "p2p_work_plan",
    "p2p_explore_prompt",
    "p2p_digest_prompt",
    "p2p_clarify_prompt",
    "p2p_synthesize_prompt",
    "p2p_plan_prompt",
    "p2p_tasks_prompt",
    "p2p_swot_prompt",
    "p2p_spec_prompt",
)

_PROMPT_TOOL_KINDS = {
    "p2p_explore_prompt": "explore",
    "p2p_digest_prompt": "digest",
    "p2p_clarify_prompt": "clarify",
    "p2p_synthesize_prompt": "synthesize",
    "p2p_plan_prompt": "plan",
    "p2p_tasks_prompt": "tasks",
    "p2p_swot_prompt": "swot",
}


def _prompt_tool_definitions() -> list[dict[str, object]]:
    definitions = []
    for tool_name, kind in _PROMPT_TOOL_KINDS.items():
        definitions.append(
            {
                "name": tool_name,
                "description": (
                    f"Advisory prompt tool: generate a {kind} prompt for an existing "
                    "proposal. Does not import output or change decisions."
                ),
                "inputSchema": _schema(
                    {"root": {"type": "string"}, "proposal_id": {"type": "string"}},
                    ["proposal_id"],
                ),
            }
        )
    definitions.append(
        {
            "name": "p2p_spec_prompt",
            "description": (
                "Advisory prompt tool: generate a software-spec refinement prompt for "
                "a Change Set. Does not import output or change decisions."
            ),
            "inputSchema": _schema(
                {"root": {"type": "string"}, "change_id": {"type": "string"}},
                ["change_id"],
            ),
        }
    )
    return definitions


def tool_definitions() -> list[dict[str, object]]:
    return [
        {
            "name": "p2p_init_project",
            "description": (
                "Write-safe bootstrap tool: initialize a P2P project and generate "
                "agent boundary instructions. Does not make governance decisions."
            ),
            "inputSchema": _schema(
                {
                    "root": {"type": "string"},
                    "name": {"type": "string"},
                    "agent": {
                        "type": "string",
                        "enum": ["generic", "codex", "claude", "all"],
                    },
                    "repository": {
                        "type": "string",
                        "enum": ["local", "cloud"],
                    },
                    "domain": {
                        "type": "string",
                        "enum": ["none", "custom", "generic", "software", "grant_document", "board_game"],
                    },
                },
                ["name"],
            ),
        },
        {
            "name": "p2p_agent_instructions_refresh",
            "description": (
                "Write-safe bootstrap tool: add or refresh agent instructions and "
                "agent policy. Does not remove other profiles or make decisions."
            ),
            "inputSchema": _schema(
                {
                    "root": {"type": "string"},
                    "profile": {
                        "type": "string",
                        "enum": ["generic", "codex", "claude", "all"],
                    },
                    "repository": {
                        "type": "string",
                        "enum": ["local", "cloud"],
                    },
                },
            ),
        },
        {
            "name": "p2p_registry_refresh",
            "description": (
                "Write-safe maintenance tool: regenerate deterministic P2P registries "
                "from existing project state. Does not decide or mutate proposals."
            ),
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_validate",
            "description": (
                "Read-only validation tool: report structural and semantic P2P "
                "findings. Does not repair, refresh, or mutate project state."
            ),
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_context",
            "description": (
                "Read-only token-aware context tool: return a compact deterministic "
                "context packet for agents before broad file reads."
            ),
            "inputSchema": _schema(
                {
                    "root": {"type": "string"},
                    "budget": {"type": "string", "enum": ["small", "medium"]},
                    "target": {"type": "string"},
                },
            ),
        },
        {
            "name": "p2p_assess_refresh",
            "description": (
                "Write-safe analysis tool: generate a deterministic project readiness "
                "assessment from current P2P state. Does not make governance decisions."
            ),
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_assess_show",
            "description": (
                "Read-only analysis tool: show the stored project readiness assessment. "
                "Does not refresh or mutate project state."
            ),
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_project_rubrics_init",
            "description": (
                "Write-safe project setup tool: create deterministic project definition "
                "rubrics for a domain. Does not make governance decisions."
            ),
            "inputSchema": _schema(
                {
                    "root": {"type": "string"},
                    "domain": {
                        "type": "string",
                        "enum": ["none", "custom", "generic", "software", "grant_document", "board_game"],
                    },
                    "force": {"type": "boolean"},
                },
            ),
        },
        {
            "name": "p2p_project_rubrics_show",
            "description": "Read configured project definition maturity rubrics.",
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_maturity_refresh",
            "description": (
                "Write-safe analysis tool: generate deterministic project definition "
                "maturity from configured rubrics. Does not assess implementation completeness."
            ),
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_maturity_show",
            "description": "Read stored project definition maturity assessment.",
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_proposal_create",
            "description": (
                "Write-safe draft tool: create a draft P2P proposal using the core "
                "proposal scaffold. Does not accept, reject, defer, or decide."
            ),
            "inputSchema": _schema(
                {
                    "root": {"type": "string"},
                    "title": {"type": "string"},
                    "problem": {"type": "string"},
                    "context": {"type": "string"},
                    "goals": {"type": "array", "items": {"type": "string"}},
                    "non_goals": {"type": "array", "items": {"type": "string"}},
                    "proposal": {"type": "string"},
                    "acceptance_criteria": {"type": "array", "items": {"type": "string"}},
                },
                ["title"],
            ),
        },
        {
            "name": "p2p_proposal_update",
            "description": (
                "Write-safe refinement tool: update structured sections of an existing "
                "P2P proposal. Does not accept, reject, defer, or decide."
            ),
            "inputSchema": _schema(
                {
                    "root": {"type": "string"},
                    "proposal_id": {"type": "string"},
                    "problem": {"type": "string"},
                    "context": {"type": "string"},
                    "goals": {"type": "array", "items": {"type": "string"}},
                    "non_goals": {"type": "array", "items": {"type": "string"}},
                    "proposal": {"type": "string"},
                    "acceptance_criteria": {"type": "array", "items": {"type": "string"}},
                },
                ["proposal_id"],
            ),
        },
        {
            "name": "p2p_proposal_contribution_add",
            "description": (
                "Write-safe contribution tool: append a typed contribution to an "
                "existing proposal. Does not accept, reject, defer, merge, or decide."
            ),
            "inputSchema": _schema(
                {
                    "root": {"type": "string"},
                    "proposal_id": {"type": "string"},
                    "text": {"type": "string"},
                    "type": {
                        "type": "string",
                        "enum": [item.value for item in ContributionType],
                    },
                    "relevance": {"type": "string"},
                    "author": {"type": "string"},
                },
                ["proposal_id", "text"],
            ),
        },
        {
            "name": "p2p_proposal_contribution_list",
            "description": "Read-only proposal contribution tool: list contributions recorded for an existing proposal.",
            "inputSchema": _schema({"root": {"type": "string"}, "proposal_id": {"type": "string"}}, ["proposal_id"]),
        },
        {
            "name": "p2p_intake_prompt",
            "description": (
                "Write-safe draft tool: create an intake prompt for a raw idea. "
                "Does not apply recommendations or make governance decisions."
            ),
            "inputSchema": _schema(
                {"root": {"type": "string"}, "idea": {"type": "string"}},
                ["idea"],
            ),
        },
        {
            "name": "p2p_intake_status",
            "description": "List intake records and whether analysis artifacts are populated.",
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_project_brief_prompt",
            "description": (
                "Advisory workflow tool: create project brief context and prompt artifacts "
                "from current project state. Does not import or decide."
            ),
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_project_brief_show",
            "description": "Show the stored operational project brief if one has been imported.",
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_choice_discover",
            "description": (
                "Advisory analysis tool: discover choice candidates and blockers without "
                "creating, deciding, blocking, or unblocking choices."
            ),
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_conflict_status",
            "description": "Read recorded project conflicts without recording new conflicts.",
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_impact_prompt",
            "description": (
                "Advisory analysis tool: generate an impact-analysis prompt for an "
                "existing proposal. Does not import impact output or change decisions."
            ),
            "inputSchema": _schema(
                {"root": {"type": "string"}, "proposal_id": {"type": "string"}},
                ["proposal_id"],
            ),
        },
        {
            "name": "p2p_project_status",
            "description": "Show deterministic P2P project state status.",
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_next",
            "description": "Show advisory next actions from P2P project state.",
            "inputSchema": _schema({"root": {"type": "string"}, "top": {"type": "integer", "minimum": 1}}),
        },
        {
            "name": "p2p_next_add",
            "description": (
                "Write-safe project planning tool: add a curated next action. Does "
                "not decide governance, publish, merge, or run external provider operations."
            ),
            "inputSchema": _schema(
                {
                    "root": {"type": "string"},
                    "kind": {"type": "string"},
                    "target": {"type": "string"},
                    "reason": {"type": "string"},
                    "command": {"type": "string"},
                    "priority": {"type": "string"},
                    "action_id": {"type": "string"},
                },
                ["kind", "reason"],
            ),
        },
        {
            "name": "p2p_next_complete",
            "description": (
                "Write-safe project planning tool: complete a curated next action and "
                "move it to the next-action audit log."
            ),
            "inputSchema": _schema(
                {"root": {"type": "string"}, "action_id": {"type": "string"}, "reason": {"type": "string"}},
                ["action_id", "reason"],
            ),
        },
        {
            "name": "p2p_next_retire",
            "description": (
                "Write-safe project planning tool: retire a curated next action and "
                "move it to the next-action audit log."
            ),
            "inputSchema": _schema(
                {"root": {"type": "string"}, "action_id": {"type": "string"}, "reason": {"type": "string"}},
                ["action_id", "reason"],
            ),
        },
        {
            "name": "p2p_next_refresh",
            "description": "Write-safe project planning tool: normalize curated next actions and report generated action count.",
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_proposal_list",
            "description": "List P2P proposals, optionally filtered by status.",
            "inputSchema": _schema({"root": {"type": "string"}, "status": {"type": "string"}}),
        },
        {
            "name": "p2p_proposal_show",
            "description": "Show one P2P proposal summary.",
            "inputSchema": _schema({"root": {"type": "string"}, "proposal_id": {"type": "string"}}, ["proposal_id"]),
        },
        {
            "name": "p2p_proposal_readiness_get",
            "description": (
                "Read-only proposal readiness tool: show the stored readiness "
                "assessment or not_assessed status. Does not refresh or decide."
            ),
            "inputSchema": _schema({"root": {"type": "string"}, "proposal_id": {"type": "string"}}, ["proposal_id"]),
        },
        {
            "name": "p2p_proposal_readiness_init",
            "description": (
                "Write-safe analysis tool: bootstrap a conservative proposal readiness "
                "assessment from existing proposal artifacts. Does not accept, reject, "
                "defer, override, or decide."
            ),
            "inputSchema": _schema({"root": {"type": "string"}, "proposal_id": {"type": "string"}}, ["proposal_id"]),
        },
        {
            "name": "p2p_proposal_readiness_refresh",
            "description": (
                "Write-safe analysis tool: refresh a proposal readiness snapshot "
                "from stored assessment evidence. Does not accept, reject, defer, "
                "override, or decide."
            ),
            "inputSchema": _schema({"root": {"type": "string"}, "proposal_id": {"type": "string"}}, ["proposal_id"]),
        },
        {
            "name": "p2p_proposal_readiness_explain",
            "description": (
                "Read-only proposal readiness tool: explain score, failed gates, "
                "missing criteria, and suggested next actions."
            ),
            "inputSchema": _schema({"root": {"type": "string"}, "proposal_id": {"type": "string"}}, ["proposal_id"]),
        },
        {
            "name": "p2p_proposal_readiness_list_gaps",
            "description": (
                "Read-only proposal readiness tool: list only failed gates, missing "
                "criteria, and suggested next actions for an existing proposal."
            ),
            "inputSchema": _schema({"root": {"type": "string"}, "proposal_id": {"type": "string"}}, ["proposal_id"]),
        },
        {
            "name": "p2p_choice_list",
            "description": "List project choices.",
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_choice_show",
            "description": "Show one project choice.",
            "inputSchema": _schema({"root": {"type": "string"}, "choice_id": {"type": "string"}}, ["choice_id"]),
        },
        {
            "name": "p2p_change_status",
            "description": "List Change Set statuses.",
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_change_show",
            "description": "Show one Change Set summary.",
            "inputSchema": _schema({"root": {"type": "string"}, "change_id": {"type": "string"}}, ["change_id"]),
        },
        {
            "name": "p2p_change_tasks",
            "description": "Show one Change Set task and action view.",
            "inputSchema": _schema({"root": {"type": "string"}, "change_id": {"type": "string"}}, ["change_id"]),
        },
        {
            "name": "p2p_work_list",
            "description": "List P2P Work manifests.",
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_work_status",
            "description": "Show operational Work item summaries.",
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_work_show",
            "description": "Show one P2P Work manifest.",
            "inputSchema": _schema({"root": {"type": "string"}, "work_id": {"type": "string"}}, ["work_id"]),
        },
        {
            "name": "p2p_registry_status",
            "description": "Show generated registry availability and freshness checks.",
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_registry_show",
            "description": "Show a generated P2P registry.",
            "inputSchema": _schema({"root": {"type": "string"}, "name": {"type": "string"}}, ["name"]),
        },
        {
            "name": "p2p_project_show",
            "description": "Show a generated project definition section or feature document.",
            "inputSchema": _schema({"root": {"type": "string"}, "section": {"type": "string"}}, ["section"]),
        },
        {
            "name": "p2p_project_remote_show",
            "description": "Show local/cloud remote project profile metadata.",
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_project_remote_configure",
            "description": (
                "Write-safe project setup tool: configure P2P remote profile metadata "
                "without creating provider repositories, opening PRs, or editing Git remotes."
            ),
            "inputSchema": _schema(
                {
                    "root": {"type": "string"},
                    "mode": {"type": "string", "enum": ["local", "remote"]},
                    "provider": {"type": "string", "enum": ["local", "generic", "github", "gitlab"]},
                    "remote": {"type": "string"},
                    "url": {"type": "string"},
                },
                ["mode"],
            ),
        },
        {
            "name": "p2p_permissions_show",
            "description": "Read project-declared permission identities and role policy.",
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_consent_request",
            "description": (
                "Write-safe consent workflow tool: record a pending consent request for "
                "an owner-controlled operation. Does not grant consent and cannot authorize execution."
            ),
            "inputSchema": _schema(
                {
                    "root": {"type": "string"},
                    "operation": {"type": "string"},
                    "target": {"type": "string"},
                    "actor_id": {"type": "string"},
                    "requested_by": {"type": "string"},
                    "scope": {"type": "string"},
                    "expires_on": {"type": "string"},
                },
                ["operation", "target", "actor_id"],
            ),
        },
        {
            "name": "p2p_consent_status",
            "description": "List permission-gated consent receipts without creating or consuming them.",
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_consent_show",
            "description": "Show one permission-gated consent receipt without creating or consuming it.",
            "inputSchema": _schema({"root": {"type": "string"}, "consent_id": {"type": "string"}}, ["consent_id"]),
        },
        {
            "name": "p2p_sync_status",
            "description": (
                "Read-only managed Git sync tool: show repository, branch, remote, "
                "clean-worktree, and sync readiness without running Git transport."
            ),
            "inputSchema": _schema({"root": {"type": "string"}, "remote": {"type": "string"}}),
        },
        {
            "name": "p2p_sync_fetch",
            "description": (
                "Managed Git sync tool: fetch configured remote refs through P2P "
                "remote-profile validation. Does not merge, pull, push, or decide."
            ),
            "inputSchema": _schema({"root": {"type": "string"}, "remote": {"type": "string"}}),
        },
        {
            "name": "p2p_sync_pull",
            "description": (
                "Permission-gated managed Git sync tool: fast-forward pull the current "
                "branch only with a valid sync_pull consent receipt. Does not merge "
                "divergent history."
            ),
            "inputSchema": _schema(
                {
                    "root": {"type": "string"},
                    "actor_id": {"type": "string"},
                    "consent_id": {"type": "string"},
                    "remote": {"type": "string"},
                },
                ["actor_id", "consent_id"],
            ),
        },
        {
            "name": "p2p_sync_push",
            "description": (
                "Permission-gated managed Git sync tool: push the current branch only "
                "with a valid sync_push consent receipt. Does not merge or open PRs."
            ),
            "inputSchema": _schema(
                {
                    "root": {"type": "string"},
                    "actor_id": {"type": "string"},
                    "consent_id": {"type": "string"},
                    "remote": {"type": "string"},
                },
                ["actor_id", "consent_id"],
            ),
        },
        {
            "name": "p2p_proposal_branch",
            "description": (
                "Managed proposal collaboration tool: create and check out a P2P "
                "proposal branch with actor metadata from an explicit safe base branch. "
                "Does not publish, accept, reject, or merge."
            ),
            "inputSchema": _schema(
                {
                    "root": {"type": "string"},
                    "proposal_id": {"type": "string"},
                    "actor": {"type": "string"},
                    "base_branch": {"type": "string"},
                    "allow_proposal_base": {"type": "boolean"},
                },
                ["proposal_id"],
            ),
        },
        {
            "name": "p2p_proposal_draft_commit",
            "description": (
                "Managed proposal collaboration tool: commit current draft proposal "
                "changes before creating a proposal branch. Does not publish, push, or decide."
            ),
            "inputSchema": _schema(
                {"root": {"type": "string"}, "proposal_id": {"type": "string"}, "actor": {"type": "string"}},
                ["proposal_id"],
            ),
        },
        {
            "name": "p2p_proposal_branch_status",
            "description": "Show one managed proposal branch status and metadata.",
            "inputSchema": _schema(
                {"root": {"type": "string"}, "proposal_id": {"type": "string"}},
                ["proposal_id"],
            ),
        },
        {
            "name": "p2p_proposal_publish",
            "description": (
                "Permission-gated managed proposal collaboration tool: publish the "
                "current proposal branch only with a valid consent receipt matching "
                "operation proposal_publish, target proposal_id, and actor_id. Does not "
                "open provider PRs or merge."
            ),
            "inputSchema": _schema(
                {
                    "root": {"type": "string"},
                    "proposal_id": {"type": "string"},
                    "actor_id": {"type": "string"},
                    "consent_id": {"type": "string"},
                    "remote": {"type": "string"},
                    "auto_renumber": {"type": "boolean"},
                },
                ["proposal_id", "actor_id", "consent_id"],
            ),
        },
        {
            "name": "p2p_proposal_request_review",
            "description": (
                "Permission-gated managed proposal collaboration tool: record review "
                "handoff metadata only with a valid proposal_request_review consent "
                "receipt. Does not open provider PRs or merge."
            ),
            "inputSchema": _schema(
                {
                    "root": {"type": "string"},
                    "proposal_id": {"type": "string"},
                    "actor_id": {"type": "string"},
                    "consent_id": {"type": "string"},
                    "provider": {"type": "string", "enum": ["generic", "github", "gitlab"]},
                },
                ["proposal_id", "actor_id", "consent_id"],
            ),
        },
        {
            "name": "p2p_proposal_accept",
            "description": (
                "Permission-gated governance tool: accept a draft proposal with a "
                "valid proposal_accept consent receipt. This records the same "
                "proposal decision as the CLI and does not branch, publish, merge, "
                "or cleanup."
            ),
            "inputSchema": _schema(
                {
                    "root": {"type": "string"},
                    "proposal_id": {"type": "string"},
                    "actor_id": {"type": "string"},
                    "consent_id": {"type": "string"},
                    "reason": {"type": "string"},
                },
                ["proposal_id", "actor_id", "consent_id", "reason"],
            ),
        },
        {
            "name": "p2p_proposal_reject",
            "description": (
                "Permission-gated governance tool: reject a draft proposal with a "
                "valid proposal_reject consent receipt. This records the same "
                "proposal decision as the CLI and does not branch, publish, merge, "
                "or cleanup."
            ),
            "inputSchema": _schema(
                {
                    "root": {"type": "string"},
                    "proposal_id": {"type": "string"},
                    "actor_id": {"type": "string"},
                    "consent_id": {"type": "string"},
                    "reason": {"type": "string"},
                },
                ["proposal_id", "actor_id", "consent_id", "reason"],
            ),
        },
        {
            "name": "p2p_proposal_defer",
            "description": (
                "Permission-gated governance tool: defer a draft proposal with a "
                "valid proposal_defer consent receipt. This records the same "
                "proposal decision as the CLI and does not branch, publish, merge, "
                "or cleanup."
            ),
            "inputSchema": _schema(
                {
                    "root": {"type": "string"},
                    "proposal_id": {"type": "string"},
                    "actor_id": {"type": "string"},
                    "consent_id": {"type": "string"},
                    "reason": {"type": "string"},
                },
                ["proposal_id", "actor_id", "consent_id", "reason"],
            ),
        },
        {
            "name": "p2p_proposal_accept_branch",
            "description": (
                "Permission-gated managed proposal collaboration tool: record an "
                "owner-controlled governance acceptance for a proposal branch. Does "
                "not merge, finalize, or cleanup."
            ),
            "inputSchema": _schema(
                {
                    "root": {"type": "string"},
                    "proposal_id": {"type": "string"},
                    "actor_id": {"type": "string"},
                    "consent_id": {"type": "string"},
                    "reason": {"type": "string"},
                },
                ["proposal_id", "actor_id", "consent_id", "reason"],
            ),
        },
        {
            "name": "p2p_proposal_reject_branch",
            "description": (
                "Permission-gated managed proposal collaboration tool: record an "
                "owner-controlled governance rejection for a proposal branch. Does "
                "not merge, finalize, or cleanup."
            ),
            "inputSchema": _schema(
                {
                    "root": {"type": "string"},
                    "proposal_id": {"type": "string"},
                    "actor_id": {"type": "string"},
                    "consent_id": {"type": "string"},
                    "reason": {"type": "string"},
                },
                ["proposal_id", "actor_id", "consent_id", "reason"],
            ),
        },
        {
            "name": "p2p_proposal_merge",
            "description": (
                "Permission-gated managed proposal collaboration tool: merge a proposal "
                "branch into its base branch with a valid proposal_merge consent receipt. "
                "Does not finalize or cleanup."
            ),
            "inputSchema": _schema(
                {
                    "root": {"type": "string"},
                    "proposal_id": {"type": "string"},
                    "actor_id": {"type": "string"},
                    "consent_id": {"type": "string"},
                },
                ["proposal_id", "actor_id", "consent_id"],
            ),
        },
        {
            "name": "p2p_proposal_finalize",
            "description": (
                "Permission-gated managed proposal collaboration tool: finalize a merged "
                "proposal branch by pushing its base branch with a valid proposal_finalize "
                "consent receipt. Does not cleanup or delete branches."
            ),
            "inputSchema": _schema(
                {
                    "root": {"type": "string"},
                    "proposal_id": {"type": "string"},
                    "actor_id": {"type": "string"},
                    "consent_id": {"type": "string"},
                    "remote": {"type": "string"},
                },
                ["proposal_id", "actor_id", "consent_id"],
            ),
        },
        {
            "name": "p2p_proposal_cleanup",
            "description": (
                "Permission-gated managed proposal collaboration tool: delete a finalized, "
                "rejected, or retired managed proposal branch with a valid proposal_cleanup "
                "consent receipt. Deletes the remote branch only when delete_remote is true."
            ),
            "inputSchema": _schema(
                {
                    "root": {"type": "string"},
                    "proposal_id": {"type": "string"},
                    "actor_id": {"type": "string"},
                    "consent_id": {"type": "string"},
                    "delete_remote": {"type": "boolean"},
                    "remote": {"type": "string"},
                },
                ["proposal_id", "actor_id", "consent_id"],
            ),
        },
        {
            "name": "p2p_proposal_branch_scan",
            "description": (
                "Read-oriented managed proposal collaboration tool: scan local "
                "p2p/proposal/* branches and refresh the proposal branch registry."
            ),
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_spec_status",
            "description": "List generated P2P-native software specs.",
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_spec_show",
            "description": "Show a generated P2P-native software spec index.",
            "inputSchema": _schema({"root": {"type": "string"}, "change_id": {"type": "string"}}, ["change_id"]),
        },
        {
            "name": "p2p_spec_export_status",
            "description": "List generated software spec exports.",
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_spec_export_show",
            "description": "Show the primary document for an existing software spec export.",
            "inputSchema": _schema(
                {
                    "root": {"type": "string"},
                    "change_id": {"type": "string"},
                    "target": {"type": "string", "enum": ["generic", "openspec", "speckit"]},
                },
                ["change_id", "target"],
            ),
        },
        {
            "name": "p2p_change_create",
            "description": (
                "Write-safe deterministic tool: create a metadata-only Change Set from "
                "an accepted proposal. Does not update status, branch, commit, or merge."
            ),
            "inputSchema": _schema(
                {"root": {"type": "string"}, "source": {"type": "string"}, "title": {"type": "string"}},
                ["source"],
            ),
        },
        {
            "name": "p2p_project_refresh",
            "description": (
                "Write-safe deterministic tool: refresh generated project definition files "
                "from accepted P2P state. Does not make governance decisions."
            ),
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_spec_refresh",
            "description": (
                "Write-safe deterministic tool: generate a P2P-native software spec from "
                "a Change Set. Does not import external edits."
            ),
            "inputSchema": _schema({"root": {"type": "string"}, "change_id": {"type": "string"}}, ["change_id"]),
        },
        {
            "name": "p2p_spec_export",
            "description": (
                "Write-safe deterministic tool: export generated spec artifacts for "
                "generic, OpenSpec, or Spec Kit targets."
            ),
            "inputSchema": _schema(
                {
                    "root": {"type": "string"},
                    "change_id": {"type": "string"},
                    "target": {"type": "string", "enum": ["generic", "openspec", "speckit"]},
                },
                ["change_id", "target"],
            ),
        },
        {
            "name": "p2p_spec_export_validate",
            "description": "Read-only validation tool: validate an existing software spec export.",
            "inputSchema": _schema(
                {
                    "root": {"type": "string"},
                    "change_id": {"type": "string"},
                    "target": {"type": "string", "enum": ["generic", "openspec", "speckit"]},
                },
                ["change_id", "target"],
            ),
        },
        {
            "name": "p2p_work_plan",
            "description": (
                "Write-safe deterministic tool: create a Work manifest from a validated "
                "spec export. Does not create branches, commits, PRs, or merges."
            ),
            "inputSchema": _schema(
                {
                    "root": {"type": "string"},
                    "change_id": {"type": "string"},
                    "target": {"type": "string", "enum": ["generic", "openspec", "speckit"]},
                },
                ["change_id", "target"],
            ),
        },
        *_prompt_tool_definitions(),
    ]


def call_tool(name: str, arguments: dict[str, Any] | None = None) -> dict[str, object]:
    arguments = arguments or {}
    root = Path(str(arguments.get("root") or Path.cwd()))
    workspace = P2PWorkspace(root)

    if name == "p2p_init_project":
        created = workspace.init_project(
            name=_required(arguments, "name"),
            agent_profile=str(arguments.get("agent") or "generic"),
            repository_mode=str(arguments.get("repository") or "local"),
            project_domain=str(arguments.get("domain") or "none"),
        )
        return {
            "initialized": True,
            "root": workspace.root,
            "created_or_updated": created,
        }
    if name == "p2p_agent_instructions_refresh":
        repository = arguments.get("repository")
        result = workspace.refresh_agent_instructions(
            profile=str(arguments.get("profile") or "generic"),
            repository_mode=str(repository) if repository is not None else None,
        )
        return {"agent_instructions": _to_jsonable(result)}
    if name == "p2p_registry_refresh":
        return {"written": _to_jsonable(workspace.refresh_registries())}
    if name == "p2p_validate":
        return {"validation": _to_jsonable(workspace.validate())}
    if name == "p2p_context":
        return {
            "context": _to_jsonable(
                workspace.context_packet(
                    budget=str(arguments.get("budget") or "small"),
                    target=_optional_string(arguments, "target"),
                )
            )
        }
    if name == "p2p_assess_refresh":
        return {"assessment": _to_jsonable(workspace.refresh_project_assessment())}
    if name == "p2p_assess_show":
        return {"assessment": _to_jsonable(workspace.show_project_assessment())}
    if name == "p2p_project_rubrics_init":
        return {
            "rubrics": _to_jsonable(
                workspace.init_project_rubrics(
                    domain=str(arguments.get("domain") or "generic"),
                    force=bool(arguments.get("force") or False),
                )
            )
        }
    if name == "p2p_project_rubrics_show":
        return {"rubrics": _to_jsonable(workspace.show_project_rubrics())}
    if name == "p2p_maturity_refresh":
        return {"maturity": _to_jsonable(workspace.refresh_definition_maturity())}
    if name == "p2p_maturity_show":
        return {"maturity": _to_jsonable(workspace.show_definition_maturity())}
    if name == "p2p_proposal_create":
        proposal = workspace.create_proposal_with_details(
            title=_required(arguments, "title"),
            problem=_optional_string(arguments, "problem"),
            context=_optional_string(arguments, "context"),
            goals=_optional_string_list(arguments, "goals"),
            non_goals=_optional_string_list(arguments, "non_goals"),
            proposal=_optional_string(arguments, "proposal"),
            acceptance_criteria=_optional_string_list(arguments, "acceptance_criteria"),
        )
        return {
            "proposal": _to_jsonable(proposal),
            "governance": {
                "status": "draft",
                "owner_decision_required": True,
                "decision_made": False,
            },
        }
    if name == "p2p_proposal_update":
        path = workspace.update_proposal(
            proposal_id=_required(arguments, "proposal_id"),
            problem=_optional_string(arguments, "problem"),
            context=_optional_string(arguments, "context"),
            goals=_optional_string_list(arguments, "goals"),
            non_goals=_optional_string_list(arguments, "non_goals"),
            proposal=_optional_string(arguments, "proposal"),
            acceptance_criteria=_optional_string_list(arguments, "acceptance_criteria"),
        )
        return {
            "updated": _to_jsonable(path),
            "proposal": _to_jsonable(workspace.show_proposal(_required(arguments, "proposal_id"))),
            "governance": {
                "owner_decision_required": True,
                "decision_made": False,
            },
        }
    if name == "p2p_proposal_contribution_add":
        contribution = workspace.add_contribution(
            proposal_id=_required(arguments, "proposal_id"),
            contribution_type=_contribution_type(arguments),
            text=_required(arguments, "text"),
            relevance_hint=str(arguments.get("relevance") or "medium"),
            author=str(arguments.get("author") or "mcp"),
        )
        return {
            "contribution": _to_jsonable(contribution),
            "proposal": _to_jsonable(workspace.show_proposal(_required(arguments, "proposal_id"))),
            "governance": {
                "owner_decision_required": True,
                "decision_made": False,
            },
        }
    if name == "p2p_proposal_contribution_list":
        return {"contributions": _to_jsonable(workspace.list_contributions(_required(arguments, "proposal_id")))}
    if name == "p2p_intake_prompt":
        return {"intake": _to_jsonable(workspace.create_intake_prompt(_required(arguments, "idea")))}
    if name == "p2p_intake_status":
        return {"intake_status": _to_jsonable(workspace.intake_statuses())}
    if name == "p2p_project_brief_prompt":
        return {"project_brief_prompt": _to_jsonable(workspace.create_project_brief_prompt())}
    if name == "p2p_project_brief_show":
        return {"operational_brief": workspace.show_project_brief()}
    if name == "p2p_choice_discover":
        return {"choice_discovery": _to_jsonable(workspace.discover_choices())}
    if name == "p2p_conflict_status":
        return {"conflicts": _to_jsonable(workspace.conflict_status())}
    if name == "p2p_impact_prompt":
        path = workspace.generate_prompt(_required(arguments, "proposal_id"), "impact")
        return {"impact_prompt": _to_jsonable({"path": path})}
    if name == "p2p_project_status":
        return {"project_status": _to_jsonable(workspace.project_state_status())}
    if name == "p2p_next":
        top = arguments.get("top")
        limit = int(top) if top is not None else None
        return {"next_actions": _to_jsonable(workspace.next_actions(limit=limit))}
    if name == "p2p_next_add":
        action = workspace.next_action_add(
            kind=_required(arguments, "kind"),
            target=str(arguments.get("target") or ""),
            reason=_required(arguments, "reason"),
            command=str(arguments.get("command") or ""),
            priority=str(arguments.get("priority") or "medium"),
            action_id=_optional_string(arguments, "action_id"),
        )
        return {"next_action": _to_jsonable(action)}
    if name == "p2p_next_complete":
        return {
            "next_action_result": _to_jsonable(
                workspace.next_action_complete(
                    _required(arguments, "action_id"),
                    _required(arguments, "reason"),
                )
            )
        }
    if name == "p2p_next_retire":
        return {
            "next_action_result": _to_jsonable(
                workspace.next_action_retire(
                    _required(arguments, "action_id"),
                    _required(arguments, "reason"),
                )
            )
        }
    if name == "p2p_next_refresh":
        return {"next_action_refresh": _to_jsonable(workspace.next_actions_refresh())}
    if name == "p2p_proposal_list":
        status = arguments.get("status")
        return {"proposals": _to_jsonable(workspace.proposal_summaries(str(status) if status else None))}
    if name == "p2p_proposal_show":
        return {"proposal": _to_jsonable(workspace.show_proposal(_required(arguments, "proposal_id")))}
    if name == "p2p_proposal_readiness_get":
        return {"readiness": _to_jsonable(workspace.read_proposal_readiness(_required(arguments, "proposal_id")))}
    if name == "p2p_proposal_readiness_init":
        readiness = workspace.initialize_proposal_readiness(_required(arguments, "proposal_id"))
        return {
            "readiness": _to_jsonable(readiness),
            "governance": {
                "owner_decision_required": False,
                "decision_made": False,
                "override_applied": False,
            },
        }
    if name == "p2p_proposal_readiness_refresh":
        readiness = workspace.refresh_proposal_readiness(_required(arguments, "proposal_id"))
        return {
            "readiness": _to_jsonable(readiness),
            "governance": {
                "owner_decision_required": False,
                "decision_made": False,
                "override_applied": False,
            },
        }
    if name == "p2p_proposal_readiness_explain":
        readiness = workspace.read_proposal_readiness(_required(arguments, "proposal_id"))
        return {
            "readiness": _to_jsonable(readiness),
            "explanation": {
                "failed_gates": readiness.failed_gates,
                "missing": readiness.missing,
                "suggested_next": readiness.suggested_next,
            },
        }
    if name == "p2p_proposal_readiness_list_gaps":
        readiness = workspace.read_proposal_readiness(_required(arguments, "proposal_id"))
        return {
            "gaps": {
                "proposal_id": readiness.proposal_id,
                "failed_gates": readiness.failed_gates,
                "missing": readiness.missing,
                "suggested_next": readiness.suggested_next,
            }
        }
    if name == "p2p_choice_list":
        return {"choices": _to_jsonable(workspace.choice_statuses())}
    if name == "p2p_choice_show":
        return {"choice": _to_jsonable(workspace.show_choice(_required(arguments, "choice_id")))}
    if name == "p2p_change_status":
        return {"changes": _to_jsonable(workspace.change_set_statuses())}
    if name == "p2p_change_show":
        return {"change": _to_jsonable(workspace.show_change_set(_required(arguments, "change_id")))}
    if name == "p2p_change_tasks":
        return {"tasks": _to_jsonable(workspace.change_set_tasks(_required(arguments, "change_id")))}
    if name == "p2p_work_list":
        return {"work": _to_jsonable(workspace.work_statuses())}
    if name == "p2p_work_status":
        return {"work": _to_jsonable(workspace.work_summaries())}
    if name == "p2p_work_show":
        return {"work": _to_jsonable(workspace.show_work(_required(arguments, "work_id")))}
    if name == "p2p_registry_status":
        return {"registry_status": _to_jsonable(workspace.registry_status())}
    if name == "p2p_registry_show":
        return {"registry": _to_jsonable(workspace.show_registry(_required(arguments, "name")))}
    if name == "p2p_project_show":
        section = _required(arguments, "section")
        return {"section": section, "content": workspace.show_project_state(section)}
    if name == "p2p_project_remote_show":
        return {"remote": _to_jsonable(workspace.remote_profile())}
    if name == "p2p_project_remote_configure":
        profile = workspace.configure_remote_profile(
            mode=_required(arguments, "mode"),
            provider=_optional_string(arguments, "provider"),
            remote=str(arguments.get("remote") or "origin"),
            url=_optional_string(arguments, "url"),
        )
        return {
            "remote": _to_jsonable(profile),
            "sync": _to_jsonable(workspace.sync_status(profile.remote)),
            "provider_side_effects": {
                "creates_remote_repository": False,
                "opens_external_request": False,
                "changes_git_remote": False,
            },
        }
    if name == "p2p_permissions_show":
        return {"permissions": _to_jsonable(workspace.permissions_show())}
    if name == "p2p_consent_request":
        consent = workspace.consent_request(
            operation=_required(arguments, "operation"),
            target=_required(arguments, "target"),
            actor_id=_required(arguments, "actor_id"),
            requested_by=_optional_string(arguments, "requested_by"),
            scope=_optional_string(arguments, "scope"),
            expires_on=_optional_string(arguments, "expires_on"),
        )
        return {
            "consent": _to_jsonable(consent),
            "governance": {
                "owner_decision_required": True,
                "consent_granted": False,
                "execution_authorized": False,
                "next": "Owner must grant consent through CLI, UI, or an authenticated server workflow.",
            },
        }
    if name == "p2p_consent_status":
        return {"consents": _to_jsonable(workspace.consent_statuses())}
    if name == "p2p_consent_show":
        return {"consent": _to_jsonable(workspace.consent_show(_required(arguments, "consent_id")))}
    if name == "p2p_sync_status":
        return {"sync": _to_jsonable(workspace.sync_status(_optional_string(arguments, "remote")))}
    if name == "p2p_sync_fetch":
        return {"sync": _to_jsonable(workspace.sync_fetch(_optional_string(arguments, "remote")))}
    if name == "p2p_sync_pull":
        actor_id = _required(arguments, "actor_id")
        consent_id = _required(arguments, "consent_id")
        before_head = _safe_head(workspace)
        target = _sync_consent_target(workspace, _optional_string(arguments, "remote"))
        workspace.consent_validate(consent_id, operation="sync_pull", target=target, actor_id=actor_id)
        try:
            result = workspace.sync_pull(_optional_string(arguments, "remote"))
        except ValueError as exc:
            _mark_consent_error_on_head_change(workspace, consent_id, before_head, str(exc), "sync_pull", target, actor_id)
            raise
        consumed = _consume_consent_with_audit(
            workspace,
            consent_id,
            result={
                "operation": "sync_pull",
                "target": target,
                "actor_id": actor_id,
                "branch": result.branch,
                "remote": result.remote,
                "head_before": before_head,
                "head_after": _safe_head(workspace),
            },
            push_remote=result.remote,
            push_branch_name=result.branch,
        )
        return {"sync": _to_jsonable(result), "consent": _to_jsonable(consumed)}
    if name == "p2p_sync_push":
        actor_id = _required(arguments, "actor_id")
        consent_id = _required(arguments, "consent_id")
        target = _sync_consent_target(workspace, _optional_string(arguments, "remote"))
        workspace.consent_validate(consent_id, operation="sync_push", target=target, actor_id=actor_id)
        before_head = _safe_head(workspace)
        try:
            result = workspace.sync_push(_optional_string(arguments, "remote"))
        except ValueError as exc:
            _mark_consent_error_on_head_change(workspace, consent_id, before_head, str(exc), "sync_push", target, actor_id)
            raise
        consumed = _consume_consent_with_audit(
            workspace,
            consent_id,
            result={
                "operation": "sync_push",
                "target": target,
                "actor_id": actor_id,
                "branch": result.branch,
                "remote": result.remote,
                "head_before": before_head,
                "head_after": _safe_head(workspace),
            },
            push_remote=result.remote,
            push_branch_name=result.branch,
        )
        return {"sync": _to_jsonable(result), "consent": _to_jsonable(consumed)}
    if name == "p2p_proposal_draft_commit":
        return {
            "proposal_draft_commit": _to_jsonable(
                workspace.commit_proposal_draft(
                    _required(arguments, "proposal_id"),
                    actor=str(arguments.get("actor") or "local"),
                )
            ),
            "governance": {
                "owner_decision_required": False,
                "decision_made": False,
                "published": False,
            },
        }
    if name == "p2p_proposal_branch":
        return {
            "proposal_branch": _to_jsonable(
                workspace.branch_proposal(
                    _required(arguments, "proposal_id"),
                    actor=str(arguments.get("actor") or "local"),
                    base_branch=str(arguments.get("base_branch") or "main"),
                    allow_proposal_base=bool(arguments.get("allow_proposal_base") or False),
                )
            ),
            "governance": {
                "owner_decision_required": False,
                "decision_made": False,
                "merge_performed": False,
            },
        }
    if name == "p2p_proposal_branch_status":
        return {"proposal_branch": _to_jsonable(workspace.show_proposal_branch(_required(arguments, "proposal_id")))}
    if name == "p2p_proposal_publish":
        proposal_id = _required(arguments, "proposal_id")
        actor_id = _required(arguments, "actor_id")
        consent_id = _required(arguments, "consent_id")
        workspace.consent_validate(
            consent_id,
            operation="proposal_publish",
            target=proposal_id,
            actor_id=actor_id,
        )
        before_head = _safe_head(workspace)
        try:
            branch = workspace.publish_proposal_branch(
                proposal_id,
                _optional_string(arguments, "remote"),
                auto_renumber=bool(arguments.get("auto_renumber") or False),
            )
        except ValueError as exc:
            after_head = _safe_head(workspace)
            if before_head and after_head and before_head != after_head:
                workspace.consent_mark_used_with_error(
                    consent_id,
                    error=str(exc),
                    result={
                        "operation": "proposal_publish",
                        "target": proposal_id,
                        "actor_id": actor_id,
                        "head_before": before_head,
                        "head_after": after_head,
                    },
                )
            raise
        consumed = workspace.consent_consume(
            consent_id,
            result={
                "operation": "proposal_publish",
                "target": branch.proposal_id,
                "actor_id": actor_id,
                "branch": branch.branch_name,
                "remote": branch.remote,
                "remote_branch": branch.metadata.get("remote_branch"),
            },
        )
        _commit_and_push_consent_audit(workspace, consent_id, push_remote=branch.remote, push_branch_name=branch.branch_name)
        return {
            "proposal_branch": _to_jsonable(branch),
            "consent": _to_jsonable(consumed),
            "governance": {
                "owner_decision_required": True,
                "decision_made": False,
                "merge_performed": False,
            },
        }
    if name == "p2p_proposal_request_review":
        proposal_id = _required(arguments, "proposal_id")
        actor_id = _required(arguments, "actor_id")
        consent_id = _required(arguments, "consent_id")
        workspace.consent_validate(
            consent_id,
            operation="proposal_request_review",
            target=proposal_id,
            actor_id=actor_id,
        )
        before_head = _safe_head(workspace)
        try:
            branch = workspace.request_proposal_branch_review(
                proposal_id,
                _optional_string(arguments, "provider"),
            )
        except ValueError as exc:
            _mark_consent_error_on_head_change(
                workspace,
                consent_id,
                before_head,
                str(exc),
                "proposal_request_review",
                proposal_id,
                actor_id,
            )
            raise
        consumed = _consume_consent_with_audit(
            workspace,
            consent_id,
            result={
                "operation": "proposal_request_review",
                "target": branch.proposal_id,
                "actor_id": actor_id,
                "branch": branch.branch_name,
                "remote": branch.remote,
                "review": branch.metadata.get("review"),
            },
            push_remote=branch.remote,
            push_branch_name=branch.branch_name,
        )
        return {
            "proposal_branch": _to_jsonable(branch),
            "consent": _to_jsonable(consumed),
            "governance": {
                "owner_decision_required": True,
                "decision_made": False,
                "merge_performed": False,
            },
        }
    if name == "p2p_proposal_accept":
        return _proposal_decision_tool(workspace, arguments, "proposal_accept", DecisionOutcome.accepted)
    if name == "p2p_proposal_reject":
        return _proposal_decision_tool(workspace, arguments, "proposal_reject", DecisionOutcome.rejected)
    if name == "p2p_proposal_defer":
        return _proposal_decision_tool(workspace, arguments, "proposal_defer", DecisionOutcome.deferred)
    if name == "p2p_proposal_accept_branch":
        proposal_id = _required(arguments, "proposal_id")
        actor_id = _required(arguments, "actor_id")
        consent_id = _required(arguments, "consent_id")
        workspace.consent_validate(
            consent_id,
            operation="proposal_accept_branch",
            target=proposal_id,
            actor_id=actor_id,
        )
        before_head = _safe_head(workspace)
        try:
            branch = workspace.accept_proposal_branch(proposal_id, _required(arguments, "reason"))
        except ValueError as exc:
            _mark_consent_error_on_head_change(
                workspace,
                consent_id,
                before_head,
                str(exc),
                "proposal_accept_branch",
                proposal_id,
                actor_id,
            )
            raise
        consumed = _consume_consent_with_audit(
            workspace,
            consent_id,
            result={
                "operation": "proposal_accept_branch",
                "target": branch.proposal_id,
                "actor_id": actor_id,
                "branch": branch.branch_name,
                "status": branch.status,
                "decision": branch.metadata.get("branch_decision"),
            },
            push_remote=branch.remote,
            push_branch_name=branch.branch_name,
        )
        return {
            "proposal_branch": _to_jsonable(branch),
            "consent": _to_jsonable(consumed),
            "governance": {
                "owner_decision_required": True,
                "decision_made": True,
                "decision_outcome": "accepted",
                "merge_performed": False,
            },
        }
    if name == "p2p_proposal_reject_branch":
        proposal_id = _required(arguments, "proposal_id")
        actor_id = _required(arguments, "actor_id")
        consent_id = _required(arguments, "consent_id")
        workspace.consent_validate(
            consent_id,
            operation="proposal_reject_branch",
            target=proposal_id,
            actor_id=actor_id,
        )
        before_head = _safe_head(workspace)
        try:
            branch = workspace.reject_proposal_branch(proposal_id, _required(arguments, "reason"))
        except ValueError as exc:
            _mark_consent_error_on_head_change(
                workspace,
                consent_id,
                before_head,
                str(exc),
                "proposal_reject_branch",
                proposal_id,
                actor_id,
            )
            raise
        consumed = _consume_consent_with_audit(
            workspace,
            consent_id,
            result={
                "operation": "proposal_reject_branch",
                "target": branch.proposal_id,
                "actor_id": actor_id,
                "branch": branch.branch_name,
                "status": branch.status,
                "decision": branch.metadata.get("branch_decision"),
            },
            push_remote=branch.remote,
            push_branch_name=branch.branch_name,
        )
        return {
            "proposal_branch": _to_jsonable(branch),
            "consent": _to_jsonable(consumed),
            "governance": {
                "owner_decision_required": True,
                "decision_made": True,
                "decision_outcome": "rejected",
                "merge_performed": False,
            },
        }
    if name == "p2p_proposal_merge":
        proposal_id = _required(arguments, "proposal_id")
        actor_id = _required(arguments, "actor_id")
        consent_id = _required(arguments, "consent_id")
        workspace.consent_validate(
            consent_id,
            operation="proposal_merge",
            target=proposal_id,
            actor_id=actor_id,
        )
        before_head = _safe_head(workspace)
        try:
            merge = workspace.merge_proposal_branch(proposal_id)
        except ValueError as exc:
            _mark_consent_error_on_head_change(
                workspace,
                consent_id,
                before_head,
                str(exc),
                "proposal_merge",
                proposal_id,
                actor_id,
            )
            raise
        if isinstance(merge, ProposalMergeConflict):
            conflict_receipt = workspace.consent_mark_used_with_error(
                consent_id,
                error="merge_conflict",
                result={
                    "operation": "proposal_merge",
                    "target": proposal_id,
                    "actor_id": actor_id,
                    "branch": merge.branch_name,
                    "base_branch": merge.base_branch,
                    "conflicted_files": merge.conflicted_files,
                    "head_before": before_head,
                    "head_after": _safe_head(workspace),
                },
            )
            return {
                "proposal_merge_conflict": _to_jsonable(merge),
                "consent": _to_jsonable(conflict_receipt),
                "governance": {
                    "owner_decision_required": True,
                    "decision_made": False,
                    "merge_performed": False,
                    "manual_resolution_required": True,
                },
            }
        consumed = _consume_consent_with_audit(
            workspace,
            consent_id,
            result={
                "operation": "proposal_merge",
                "target": merge.proposal_id,
                "actor_id": actor_id,
                "branch": merge.branch_name,
                "base_branch": merge.base_branch,
                "merge_commit": merge.merge_commit,
            },
        )
        return {
            "proposal_merge": _to_jsonable(merge),
            "consent": _to_jsonable(consumed),
            "governance": {
                "owner_decision_required": True,
                "decision_made": False,
                "merge_performed": True,
            },
        }
    if name == "p2p_proposal_finalize":
        proposal_id = _required(arguments, "proposal_id")
        actor_id = _required(arguments, "actor_id")
        consent_id = _required(arguments, "consent_id")
        workspace.consent_validate(
            consent_id,
            operation="proposal_finalize",
            target=proposal_id,
            actor_id=actor_id,
        )
        before_head = _safe_head(workspace)
        try:
            finalize = workspace.finalize_proposal_branch(
                proposal_id,
                _optional_string(arguments, "remote"),
            )
        except ValueError as exc:
            _mark_consent_error_on_head_change(
                workspace,
                consent_id,
                before_head,
                str(exc),
                "proposal_finalize",
                proposal_id,
                actor_id,
            )
            raise
        consumed = _consume_consent_with_audit(
            workspace,
            consent_id,
            result={
                "operation": "proposal_finalize",
                "target": finalize.proposal_id,
                "actor_id": actor_id,
                "branch": finalize.branch_name,
                "base_branch": finalize.base_branch,
                "remote": finalize.remote,
                "finalize_commit": finalize.finalize_commit,
            },
            push_remote=finalize.remote,
            push_branch_name=finalize.base_branch,
        )
        return {
            "proposal_finalize": _to_jsonable(finalize),
            "consent": _to_jsonable(consumed),
            "governance": {
                "owner_decision_required": True,
                "decision_made": False,
                "merge_performed": True,
                "finalized": True,
                "cleanup_performed": False,
            },
        }
    if name == "p2p_proposal_cleanup":
        proposal_id = _required(arguments, "proposal_id")
        actor_id = _required(arguments, "actor_id")
        consent_id = _required(arguments, "consent_id")
        workspace.consent_validate(
            consent_id,
            operation="proposal_cleanup",
            target=proposal_id,
            actor_id=actor_id,
        )
        before_head = _safe_head(workspace)
        try:
            cleanup = workspace.cleanup_proposal_branch(
                proposal_id,
                delete_remote=bool(arguments.get("delete_remote") or False),
                remote=_optional_string(arguments, "remote"),
            )
        except ValueError as exc:
            _mark_consent_error_on_head_change(
                workspace,
                consent_id,
                before_head,
                str(exc),
                "proposal_cleanup",
                proposal_id,
                actor_id,
            )
            raise
        consumed = _consume_consent_with_audit(
            workspace,
            consent_id,
            result={
                "operation": "proposal_cleanup",
                "target": cleanup.proposal_id,
                "actor_id": actor_id,
                "branch": cleanup.branch_name,
                "base_branch": cleanup.base_branch,
                "remote": cleanup.remote,
                "local_deleted": cleanup.local_deleted,
                "remote_deleted": cleanup.remote_deleted,
                "cleanup_commit": cleanup.cleanup_commit,
            },
            push_remote=cleanup.remote if cleanup.remote_url else None,
            push_branch_name=cleanup.base_branch if cleanup.remote_url else None,
        )
        return {
            "proposal_cleanup": _to_jsonable(cleanup),
            "consent": _to_jsonable(consumed),
            "governance": {
                "owner_decision_required": True,
                "decision_made": False,
                "merge_performed": False,
                "cleanup_performed": True,
            },
        }
    if name == "p2p_proposal_branch_scan":
        return {"proposal_branch_scan": _to_jsonable(workspace.scan_proposal_branches())}
    if name == "p2p_spec_status":
        return {"specs": _to_jsonable(workspace.software_spec_statuses())}
    if name == "p2p_spec_show":
        change_id = _required(arguments, "change_id")
        return {"change_id": change_id, "content": workspace.show_software_spec(change_id)}
    if name == "p2p_spec_export_status":
        return {"exports": _to_jsonable(workspace.software_spec_export_statuses())}
    if name == "p2p_spec_export_show":
        change_id = _required(arguments, "change_id")
        target = _required(arguments, "target")
        return {
            "change_id": change_id,
            "target": target,
            "content": workspace.show_software_spec_export(change_id, target),
        }
    if name == "p2p_change_create":
        return {
            "change": _to_jsonable(
                workspace.create_change_set(
                    source=_required(arguments, "source"),
                    title=_optional_string(arguments, "title"),
                )
            )
        }
    if name == "p2p_project_refresh":
        return {"written": _to_jsonable(workspace.refresh_project_state())}
    if name == "p2p_spec_refresh":
        return {"spec": _to_jsonable(workspace.refresh_software_spec(_required(arguments, "change_id")))}
    if name == "p2p_spec_export":
        return {
            "export": _to_jsonable(
                workspace.export_software_spec(
                    _required(arguments, "change_id"),
                    _required(arguments, "target"),
                )
            )
        }
    if name == "p2p_spec_export_validate":
        return {
            "validation": _to_jsonable(
                workspace.validate_software_spec_export(
                    _required(arguments, "change_id"),
                    _required(arguments, "target"),
                )
            )
        }
    if name == "p2p_work_plan":
        return {
            "work": _to_jsonable(
                workspace.create_work_plan(
                    _required(arguments, "change_id"),
                    _required(arguments, "target"),
                )
            )
        }
    if name in _PROMPT_TOOL_KINDS:
        path = workspace.generate_prompt(_required(arguments, "proposal_id"), _PROMPT_TOOL_KINDS[name])
        return {_PROMPT_TOOL_KINDS[name] + "_prompt": _to_jsonable({"path": path})}
    if name == "p2p_spec_prompt":
        return {"spec_prompt": _to_jsonable(workspace.create_software_spec_prompt(_required(arguments, "change_id")))}

    raise ValueError(f"Unknown MCP tool: {name}")


def _schema(properties: dict[str, object], required: list[str] | None = None) -> dict[str, object]:
    return {
        "type": "object",
        "properties": properties,
        "required": required or [],
        "additionalProperties": False,
    }


def _required(arguments: dict[str, Any], name: str) -> str:
    value = arguments.get(name)
    if value is None or str(value).strip() == "":
        raise ValueError(f"Missing required argument: {name}")
    return str(value)


def _optional_string(arguments: dict[str, Any], name: str) -> str | None:
    value = arguments.get(name)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_string_list(arguments: dict[str, Any], name: str) -> list[str] | None:
    value = arguments.get(name)
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError(f"Expected list argument: {name}")
    items = [str(item).strip() for item in value if str(item).strip()]
    return items or None


def _contribution_type(arguments: dict[str, Any]) -> ContributionType:
    value = str(arguments.get("type") or ContributionType.suggestion.value)
    try:
        return ContributionType(value)
    except ValueError as exc:
        allowed = ", ".join(item.value for item in ContributionType)
        raise ValueError(f"Invalid contribution type: {value}. Allowed: {allowed}") from exc


def _safe_head(workspace: P2PWorkspace) -> str | None:
    try:
        return head_commit(workspace.root)
    except Exception:
        return None


def _sync_consent_target(workspace: P2PWorkspace, remote: str | None) -> str:
    status = workspace.sync_status(remote)
    if not status.branch:
        raise ValueError("Cannot resolve sync consent target from detached HEAD")
    selected_remote = remote or status.remote or "origin"
    return f"{selected_remote}/{status.branch}"


def _proposal_decision_tool(
    workspace: P2PWorkspace,
    arguments: dict[str, Any],
    operation: str,
    outcome: DecisionOutcome,
) -> dict[str, object]:
    proposal_id = _required(arguments, "proposal_id")
    actor_id = _required(arguments, "actor_id")
    consent_id = _required(arguments, "consent_id")
    reason = _required(arguments, "reason")
    workspace.consent_validate(
        consent_id,
        operation=operation,
        target=proposal_id,
        actor_id=actor_id,
    )
    before_head = _safe_head(workspace)
    try:
        decision = workspace.record_decision(
            proposal_id=proposal_id,
            outcome=outcome,
            reason=reason,
            approver=actor_id,
        )
    except ValueError as exc:
        _mark_consent_error_on_head_change(
            workspace,
            consent_id,
            before_head,
            str(exc),
            operation,
            proposal_id,
            actor_id,
        )
        raise
    consumed = _consume_consent_with_audit(
        workspace,
        consent_id,
        result={
            "operation": operation,
            "target": proposal_id,
            "actor_id": actor_id,
            "decision_outcome": decision.outcome.value,
        },
    )
    return {
        "proposal_decision": {
            "proposal_id": decision.proposal_id,
            "outcome": decision.outcome.value,
            "reason": decision.reason,
            "approver": decision.approver,
            "decided_on": decision.decided_on.isoformat(),
        },
        "consent": _to_jsonable(consumed),
        "governance": {
            "owner_decision_required": True,
            "decision_made": True,
            "decision_outcome": decision.outcome.value,
            "merge_performed": False,
        },
    }


def _consume_consent_with_audit(
    workspace: P2PWorkspace,
    consent_id: str,
    *,
    result: dict[str, object],
    push_remote: str | None = None,
    push_branch_name: str | None = None,
) -> object:
    consumed = workspace.consent_consume(consent_id, result=result)
    _commit_and_push_consent_audit(
        workspace,
        consent_id,
        push_remote=push_remote,
        push_branch_name=push_branch_name,
    )
    return consumed


def _commit_and_push_consent_audit(
    workspace: P2PWorkspace,
    consent_id: str,
    *,
    push_remote: str | None = None,
    push_branch_name: str | None = None,
) -> None:
    if commit_all(workspace.root, f"P2P consent consume {consent_id}") is None:
        raise ValueError(f"Failed to commit consent consumption audit for {consent_id}")
    if push_remote and push_branch_name and not push_branch(workspace.root, push_branch_name, push_remote):
        raise ValueError(f"Failed to push consent consumption audit for {consent_id}")


def _mark_consent_error_on_head_change(
    workspace: P2PWorkspace,
    consent_id: str,
    before_head: str | None,
    error: str,
    operation: str,
    target: str,
    actor_id: str,
) -> None:
    after_head = _safe_head(workspace)
    if before_head and after_head and before_head != after_head:
        workspace.consent_mark_used_with_error(
            consent_id,
            error=error,
            result={
                "operation": operation,
                "target": target,
                "actor_id": actor_id,
                "head_before": before_head,
                "head_after": after_head,
            },
        )


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _to_jsonable(asdict(value))
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(item) for item in value]
    return value
