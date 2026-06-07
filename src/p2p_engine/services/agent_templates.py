from __future__ import annotations

from pathlib import Path

BUILT_IN_AGENT_ADAPTERS = ("generic", "codex", "claude", "cursor", "copilot", "gemini", "opencode")
AGENT_PROFILES = {*BUILT_IN_AGENT_ADAPTERS, "all"}


def normalize_agent_profile(profile: str) -> str:
    normalized = profile.strip().lower().replace("_", "-")
    if "," in normalized:
        parts = [item.strip() for item in normalized.split(",") if item.strip()]
        normalized_parts = [normalize_agent_profile(item) for item in parts]
        if "all" in normalized_parts:
            return "all"
        return ",".join(sorted(set(normalized_parts)))
    aliases = {
        "claude-code": "claude",
        "anthropic": "claude",
        "openai-codex": "codex",
        "github-copilot": "copilot",
        "gemini-cli": "gemini",
        "open-code": "opencode",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in AGENT_PROFILES:
        valid = ", ".join([*BUILT_IN_AGENT_ADAPTERS, "all"])
        raise ValueError(f"Agent profile must be one of: {valid}")
    return normalized


def expanded_agent_profiles(profile: str) -> list[str]:
    if "," in profile:
        expanded: set[str] = {"generic"}
        for item in profile.split(","):
            expanded.update(expanded_agent_profiles(item))
        return sorted(expanded)
    if profile == "all":
        return list(BUILT_IN_AGENT_ADAPTERS)
    if profile == "generic":
        return ["generic"]
    return ["generic", profile]


def managed_markdown_header(adapter: str, template_id: str) -> str:
    return (
        "<!--\n"
        "Managed by P2P Engine.\n"
        f"Adapter: {adapter}\n"
        f"Template: {template_id}\n"
        "Do not edit generated sections unless you accept drift.\n"
        "-->\n\n"
    )


READINESS_GAP_HANDLING_BLOCK = """When a proposal is weak, low-confidence, below target, or has failed readiness gates, do not stop at diagnosis.

For each failed gate or material gap:
1. explain why the gate failed in proposal-specific terms;
2. propose one to three concrete alternatives;
3. recommend one option when evidence supports a recommendation;
4. identify the owner decision required;
5. draft the exact artifact update that would close the gap;
6. ask for confirmation only where owner authority is required;
7. re-check or request readiness re-check after refinement."""


def agent_adapter_capabilities(adapter_id: str) -> dict[str, object]:
    return {
        "mcp": "supported",
        "shell": "supported",
        "project_instructions": True,
        "skill": adapter_id in {"codex"},
    }


def agent_instruction_files(
    project_name: str,
    profiles: list[str],
    repository_mode: str,
) -> dict[Path, str]:
    profiles = sorted(set(profiles))
    files = {Path("AGENTS.md"): agents_markdown(project_name, profiles, repository_mode)}
    if "codex" in profiles:
        files[Path(".agents/skills/p2p-project/SKILL.md")] = shared_p2p_project_skill(
            project_name,
            repository_mode,
        )
        files[Path(".codex/skills/p2p-project/SKILL.md")] = codex_project_skill(
            project_name,
            repository_mode,
        )
    if "claude" in profiles:
        files[Path("CLAUDE.md")] = claude_markdown(project_name, repository_mode)
    if "cursor" in profiles:
        files[Path(".cursor/rules/p2p.mdc")] = cursor_rule(project_name, repository_mode)
    if "copilot" in profiles:
        files[Path(".github/copilot-instructions.md")] = copilot_instructions(
            project_name,
            repository_mode,
        )
    if "gemini" in profiles:
        files[Path("GEMINI.md")] = gemini_markdown(project_name, repository_mode)
    return files


def agent_adapter_files(
    project_name: str,
    adapter_id: str,
    profiles: list[str],
    repository_mode: str,
) -> list[tuple[Path, str, bool, str]]:
    files: list[tuple[Path, str, bool, str]] = []
    if adapter_id == "generic":
        files.append((Path("AGENTS.md"), "generic-agents-md-v1", True, "generic"))
        files.append((Path(".p2p/agent-policy.yml"), "generic-agent-policy-v1", True, "generic"))
    elif adapter_id == "codex":
        files.append((Path("AGENTS.md"), "generic-agents-md-v1", True, "generic"))
        files.append((Path(".agents/skills/p2p-project/SKILL.md"), "codex-p2p-skill-v1", False, "codex"))
        files.append((Path(".codex/skills/p2p-project/SKILL.md"), "codex-legacy-p2p-skill-v1", False, "codex"))
    elif adapter_id == "claude":
        files.append((Path("AGENTS.md"), "generic-agents-md-v1", True, "generic"))
        files.append((Path("CLAUDE.md"), "claude-md-v1", False, "claude"))
    elif adapter_id == "cursor":
        files.append((Path("AGENTS.md"), "generic-agents-md-v1", True, "generic"))
        files.append((Path(".cursor/rules/p2p.mdc"), "cursor-p2p-rule-v1", False, "cursor"))
    elif adapter_id == "copilot":
        files.append((Path("AGENTS.md"), "generic-agents-md-v1", True, "generic"))
        files.append((Path(".github/copilot-instructions.md"), "copilot-instructions-v1", False, "copilot"))
    elif adapter_id == "gemini":
        files.append((Path("AGENTS.md"), "generic-agents-md-v1", True, "generic"))
        files.append((Path("GEMINI.md"), "gemini-md-v1", False, "gemini"))
    elif adapter_id == "opencode":
        files.append((Path("AGENTS.md"), "generic-agents-md-v1", True, "generic"))
    return files


def agent_policy(project_name: str, profiles: list[str], repository_mode: str) -> dict[str, object]:
    return {
        "p2p_agent_policy": {
            "version": "1.0",
            "project_name": project_name,
            "source_of_truth": "p2p_cli",
            "missing_primitive_behavior": "stop_and_report",
            "direct_p2p_file_edits": "forbidden",
            "owner_controls_governance": True,
        },
        "repository": {
            "mode": repository_mode,
            "cloud_is_advisory_until_configured": repository_mode == "cloud",
        },
        "agent_profiles": profiles,
        "runtime_bootstrap": {
            "discovery_order": [
                "p2p",
                ".venv/bin/p2p",
                "python -m p2p_engine",
                "available MCP tools",
            ],
            "doctor_commands": [
                "p2p doctor",
                "p2p agent doctor",
                ".venv/bin/p2p agent doctor",
                "python -m p2p_engine agent doctor",
            ],
            "when_unavailable": "stop_and_report_diagnostics",
        },
        "mcp": {
            "default_mode": "read_only",
            "write_tools_require_explicit_tool_schema": True,
            "missing_write_tool_behavior": "stop_and_report",
        },
        "owner_controlled_actions": [
            "proposal_accept",
            "proposal_reject",
            "proposal_defer",
            "choice_decide",
            "work_accept",
            "work_finalize",
            "work_cleanup",
            "proposal_branch_accept",
            "proposal_branch_reject",
            "proposal_branch_merge",
            "proposal_branch_finalize",
            "proposal_branch_remote_publish",
            "direct_git_merge",
            "raw_git_managed_branch",
            "raw_git_managed_sync",
        ],
        "proposal_readiness": {
            "inspect_before_acceptance_recommendation": True,
            "gap_handling": {
                "do_not_stop_at_diagnosis": True,
                "steps": [
                    "explain_failed_gate",
                    "propose_alternatives",
                    "recommend_when_supported",
                    "identify_owner_decision",
                    "draft_candidate_update",
                    "ask_only_for_owner_authority",
                    "recheck_readiness",
                ],
            },
            "commands": [
                "p2p proposal readiness show PROP-XXX",
                "p2p proposal readiness init PROP-XXX",
                "p2p proposal readiness refresh PROP-XXX",
                "p2p proposal readiness explain PROP-XXX",
            ],
            "mcp_tools": [
                "p2p_proposal_readiness_get",
                "p2p_proposal_readiness_init",
                "p2p_proposal_readiness_refresh",
                "p2p_proposal_readiness_explain",
                "p2p_proposal_readiness_list_gaps",
            ],
            "computed_score_is_advisory": True,
            "owner_override_must_not_falsify_computed_score": True,
        },
        "managed_git_collaboration": {
            "raw_git_for_managed_state": "forbidden_without_owner_escape_hatch",
            "inspect_before_branching": [
                "p2p status",
                "p2p sync status",
            ],
            "proposal_branch_commands": [
                "p2p proposal branch PROP-XXX --actor <actor>",
                "p2p proposal status PROP-XXX",
                "p2p proposal publish PROP-XXX",
                "p2p proposal publish PROP-XXX --auto-renumber",
                "p2p proposal request-review PROP-XXX",
                "p2p proposal scan",
                "p2p proposal retire-branch PROP-XXX --reason <reason>",
            ],
            "sync_commands": [
                "p2p sync status",
                "p2p sync fetch",
                "p2p sync pull",
                "p2p sync push",
            ],
            "mcp_tools": [
                "p2p_project_remote_configure",
                "p2p_consent_request",
                "p2p_sync_status",
                "p2p_sync_fetch",
                "p2p_sync_pull",
                "p2p_sync_push",
                "p2p_proposal_draft_commit",
                "p2p_proposal_branch",
                "p2p_proposal_branch_status",
                "p2p_proposal_publish",
                "p2p_proposal_request_review",
                "p2p_proposal_accept_branch",
                "p2p_proposal_reject_branch",
                "p2p_proposal_merge",
                "p2p_proposal_finalize",
                "p2p_proposal_cleanup",
                "p2p_proposal_branch_scan",
            ],
            "deferred_permission_gated_mcp_tools": [
                "p2p_proposal_retire_branch",
                "p2p_work_publish",
                "p2p_work_finalize",
            ],
        },
        "allowed_mutation_boundary": {
            "use_p2p_cli_commands": True,
            "use_mcp_write_tools_only_when_available": True,
            "invent_internal_p2p_files": False,
            "invent_ids_or_registry_entries": False,
            "write_decision_files_directly": False,
        },
        "explain_existing_artifacts": {
            "read_before_explaining": True,
            "allowed_sources": [
                "p2p context",
                "p2p proposal show",
                "p2p choice show",
                "p2p change show",
                "p2p work show",
                "equivalent MCP show/read tools",
            ],
            "avoid_memory_only_explanations": True,
        },
        "token_budget": {
            "compact_context_first": True,
            "default_command": "p2p context --budget small",
            "mcp_tool": "p2p_context",
            "read_details_only_by_id": True,
            "broad_scans_require_explicit_need": True,
            "advanced_token_estimation": "deferred",
        },
    }


def agents_markdown(project_name: str, profiles: list[str], repository_mode: str) -> str:
    profile_text = ", ".join(profiles)
    return f"""{managed_markdown_header("generic", "generic-agents-md-v1")}# Agent Instructions - {project_name}

This project uses P2P Engine.

## Source Of Truth

- Use the `p2p` CLI as the public write interface.
- Treat `.p2p/` as managed project state.
- Do not create, edit, rename, or delete files under `.p2p/` by hand unless the owner explicitly asks for a repair.
- Do not invent proposal IDs, choice IDs, change IDs, work IDs, registry entries, or internal P2P file layouts.

## Missing Primitive Rule

If the requested action cannot be performed with an available `p2p` command or an explicit MCP write tool, stop and report the limitation.

Do not satisfy the request by reverse-engineering `.p2p/` and writing files directly.

## Runtime Bootstrap

If `p2p` is not available on `PATH`, try this discovery order before stopping:

```bash
p2p doctor
.venv/bin/p2p agent doctor
python -m p2p_engine agent doctor
python -m p2p_engine.mcp.server --root /path/to/project
```

Use the first available P2P command as the write interface. If no CLI command or explicit MCP write tool is available, report the diagnostics and ask the owner to install P2P Engine or provide a runner/container with P2P installed. Do not edit `.p2p/` manually as a fallback.

## Governance Boundary

The owner controls governance decisions. Agents may draft, analyze, compare, and suggest actions, but must not decide on behalf of the owner.

Owner-controlled actions include:

- accepting, rejecting, or deferring proposals;
- deciding choices;
- accepting, finalizing, cleaning up, or merging managed work;
- accepting, rejecting, merging, or finalizing managed proposal branches;
- changing governance policy;
- creating direct Git merges into the main branch.

## Proposal Readiness

Before recommending proposal acceptance, inspect readiness with:

```bash
p2p proposal readiness show PROP-XXX
p2p proposal readiness init PROP-XXX
p2p proposal readiness refresh PROP-XXX
p2p proposal readiness explain PROP-XXX
```

If readiness is missing, weak, below target, or blocked by failed gates, ask focused owner questions and identify concrete missing artifacts before recommending acceptance. Readiness is advisory; the owner may still decide, but an owner override must be described separately from the computed score.

### Readiness Gap Handling

{READINESS_GAP_HANDLING_BLOCK}

## Managed Git Collaboration

Do not run raw `git branch`, `git fetch`, `git pull`, `git push`, `git merge`, or provider PR/MR commands for managed P2P project state unless the owner explicitly authorizes an escape hatch.

Use P2P-managed commands instead:

```bash
p2p sync status
p2p sync fetch
p2p sync pull
p2p sync push
p2p proposal branch PROP-XXX --actor "name-or-agent"
p2p proposal status PROP-XXX
p2p proposal publish PROP-XXX
p2p proposal publish PROP-XXX --auto-renumber
p2p proposal request-review PROP-XXX
p2p proposal scan
p2p proposal retire-branch PROP-XXX --reason "..."
```

Before creating proposal or Work branches, inspect P2P state and sync state. Stop for owner approval before remote publication, accept, reject, merge, finalize, cleanup, or any operation marked owner-controlled by policy.

## MCP Boundary

Assume MCP tools are read-only unless the tool schema explicitly describes a write action.

When MCP is read-only, use it for status and inspection only. For mutations, use `p2p` CLI commands when available or explicit write-safe MCP tools such as `p2p_project_remote_configure`, `p2p_consent_request`, `p2p_proposal_draft_commit`, `p2p_proposal_branch`, and `p2p_sync_fetch` when their schema matches the requested action.

MCP may use implemented permission-gated repository tools only with a valid consent receipt. MCP must not retire or create provider PR/MR handoffs until those operations are explicitly implemented and authorized.

## Explaining Existing P2P Artifacts

Before explaining an existing proposal, choice, Change Set, or Work item, read it from P2P state first.

Use `p2p proposal show`, `p2p choice show`, `p2p change show`, `p2p work show`, or an equivalent MCP show/read tool. Do not explain existing P2P artifacts only from conversation memory.

## Token Budget Discipline

AI is expensive. CLI is cheap. Git is memory. `.p2p` is governance. Owner decides. Agent works in bounded sessions.

Before broad reads, use compact context:

```bash
p2p context --budget small
p2p context --target PROP-XXX --budget small
```

With MCP, use `p2p_context` first.

Read summaries first; read details only by explicit ID. Do not scan all `.p2p/`, all registries, all proposals, all source files, or Git history unless the task explicitly requires it or compact context is insufficient.

## Recommended Start

Run or request:

```bash
p2p status
p2p context --budget small
p2p registry refresh
p2p next
```

For a new idea, prefer:

```bash
p2p intake prompt "idea"
```

or, when the owner explicitly wants a new proposal:

```bash
p2p proposal create "Title" --problem "..." --goal "..." --proposal "..." --acceptance "..."
```

## Project Bootstrap

- Initial agent profiles: {profile_text}
- Repository mode: {repository_mode}
- Additional agent instructions can be added later with `p2p agent instructions refresh`.
"""


def shared_p2p_project_skill(project_name: str, repository_mode: str) -> str:
    return f"""---
name: p2p-project
description: Use when working in this P2P-managed project. Enforces P2P Engine boundaries for any compatible project skill loader.
---

{managed_markdown_header("codex", "codex-p2p-skill-v1")}\
# P2P Project Skill - {project_name}

Use P2P Engine as the source of truth for project governance and planning.

## Required Behavior

- Read `AGENTS.md` and `.p2p/agent-policy.yml` before modifying project state.
- Use `p2p` CLI commands or explicit MCP write tools for P2P mutations.
- If no CLI command or MCP write tool exists for the requested operation, stop and report the missing primitive.
- Do not edit `.p2p/` internals directly, invent IDs, or synthesize decision files.
- Do not accept, reject, defer, decide, merge, finalize, or cleanup without explicit owner instruction.
- Do not recommend proposal acceptance before checking readiness.
- Do not run raw Git commands for managed branch, sync, publish, or merge work unless the owner explicitly authorizes an escape hatch.
- Use compact context before broad file reads.

## Readiness Gap Handling

{READINESS_GAP_HANDLING_BLOCK}

Repository mode: `{repository_mode}`.
"""


def codex_project_skill(project_name: str, repository_mode: str) -> str:
    return f"""---
name: p2p-project
description: Use when working in this P2P-managed project. Enforces P2P Engine boundaries for Codex.
---

{managed_markdown_header("codex", "codex-legacy-p2p-skill-v1")}\
# P2P Project Skill - {project_name}

Use P2P Engine as the source of truth for project governance and planning.

## Required Behavior

- Read `AGENTS.md` and `.p2p/agent-policy.yml` before modifying project state.
- Use `p2p` CLI commands for P2P mutations.
- If `p2p` is not on `PATH`, try `.venv/bin/p2p`, then `python -m p2p_engine`, then available MCP tools. Use `p2p agent doctor` or equivalent diagnostics before stopping.
- Use MCP only within the tool schema; read-only MCP tools do not authorize filesystem writes.
- If no CLI command or MCP write tool exists for the requested operation, stop and report the missing primitive.
- Do not edit `.p2p/` internals directly, invent IDs, or synthesize decision files.
- Do not accept, reject, defer, decide, merge, finalize, or cleanup without explicit owner instruction.
- Do not recommend proposal acceptance before checking readiness or explicitly stating that readiness is missing.
- Do not run raw Git commands for managed branch, sync, publish, or merge work unless the owner explicitly authorizes an escape hatch.
- Use `p2p sync status` before managed branch work, `p2p proposal branch` for proposal branches, and `p2p proposal publish --auto-renumber` only when publish reports a recoverable proposal ID collision.
- Before explaining existing proposals, choices, Change Sets, or Work items, use the relevant `p2p ... show` command or equivalent MCP read tool.
- Use `p2p context --budget small` or MCP `p2p_context` before broad file reads.
- Do not scan all `.p2p/`, registries, source files, or Git history unless the task explicitly requires it.

## Readiness Gap Handling

{READINESS_GAP_HANDLING_BLOCK}

## Useful Commands

```bash
p2p status
p2p context --budget small
p2p registry refresh
p2p next
p2p proposal list
p2p proposal readiness show PROP-XXX
p2p proposal readiness init PROP-XXX
p2p proposal readiness refresh PROP-XXX
p2p proposal readiness explain PROP-XXX
p2p proposal branch PROP-XXX --actor "codex"
p2p proposal status PROP-XXX
p2p proposal publish PROP-XXX
p2p proposal publish PROP-XXX --auto-renumber
p2p proposal request-review PROP-XXX
p2p proposal scan
p2p sync status
p2p sync fetch
p2p sync pull
p2p sync push
p2p choice list
p2p change status
p2p work status
```

Repository mode: `{repository_mode}`.
"""


def claude_markdown(project_name: str, repository_mode: str) -> str:
    return f"""{managed_markdown_header("claude", "claude-md-v1")}# Claude Instructions - {project_name}

This repository is managed with P2P Engine.

Follow `AGENTS.md` and `.p2p/agent-policy.yml`.

Key rules:

- Use `p2p` CLI commands for P2P writes.
- Do not modify `.p2p/` internals directly.
- If a requested P2P action has no available command or MCP write tool, stop and explain the missing primitive.
- Do not make owner-controlled governance decisions unless the owner explicitly instructs the exact decision.
- Do not recommend proposal acceptance before checking readiness or explicitly stating that readiness is missing.
- Do not run raw Git commands for managed branch, sync, publish, or merge work unless the owner explicitly authorizes an escape hatch.
- Use `p2p sync status`, `p2p proposal branch`, `p2p proposal publish`, `p2p proposal request-review`, and `p2p proposal scan` for managed collaboration workflows.
- Treat MCP as read-only unless a tool explicitly declares a write operation.
- Before explaining existing proposals, choices, Change Sets, or Work items, read them with the relevant `p2p ... show` command or equivalent MCP read tool.
- Use `p2p context --budget small` or MCP `p2p_context` before broad file reads.
- Do not scan all `.p2p/`, registries, source files, or Git history unless the task explicitly requires it.

## Readiness Gap Handling

{READINESS_GAP_HANDLING_BLOCK}

Repository mode: `{repository_mode}`.
"""


def cursor_rule(project_name: str, repository_mode: str) -> str:
    return f"""---
description: P2P Engine project governance and agent workflow rules
alwaysApply: true
---

{managed_markdown_header("cursor", "cursor-p2p-rule-v1")}\
# Cursor P2P Rules - {project_name}

- Use `p2p` CLI commands or explicit MCP write tools for P2P mutations.
- Do not edit `.p2p/` internals directly.
- Do not make owner-controlled governance decisions without explicit owner instruction.
- Inspect proposal readiness before recommending acceptance.
- Use compact context before broad file reads.

## Readiness Gap Handling

{READINESS_GAP_HANDLING_BLOCK}

Repository mode: `{repository_mode}`.
"""


def copilot_instructions(project_name: str, repository_mode: str) -> str:
    return f"""{managed_markdown_header("copilot", "copilot-instructions-v1")}# GitHub Copilot Instructions - {project_name}

This repository is managed with P2P Engine.

- Use `p2p` CLI commands for P2P writes when shell access is available.
- Use explicit MCP write tools only when the tool schema supports the requested operation.
- Do not edit `.p2p/` internals directly.
- Do not invent proposal, choice, change, work, registry, or decision IDs.
- Owner-controlled governance decisions require explicit owner instruction.
- Inspect readiness before recommending proposal acceptance.
- Prefer compact context before broad reads.

## Readiness Gap Handling

{READINESS_GAP_HANDLING_BLOCK}

Repository mode: `{repository_mode}`.
"""


def gemini_markdown(project_name: str, repository_mode: str) -> str:
    return f"""{managed_markdown_header("gemini", "gemini-md-v1")}# Gemini Instructions - {project_name}

This repository is managed with P2P Engine.

- Use `p2p` CLI commands or explicit MCP write tools for P2P mutations.
- Do not edit `.p2p/` internals directly.
- If no write primitive exists, stop and report the limitation.
- The owner controls governance decisions.
- Inspect readiness before recommending proposal acceptance.
- Use compact context before broad file reads.

## Readiness Gap Handling

{READINESS_GAP_HANDLING_BLOCK}

Repository mode: `{repository_mode}`.
"""
