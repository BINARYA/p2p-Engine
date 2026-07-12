# P2P MCP Server

This document describes how agents can access P2P Engine through the local MCP
server. The MCP server is a local stdio bridge to P2P project state; it is not a
hosted product and it does not replace the CLI as the source of truth.

## Server

P2P Engine currently exposes MCP over local `stdio`.

In `stdio` mode, the MCP client starts the P2P MCP server as a local subprocess.
The client and server exchange JSON-RPC messages over `stdin` and `stdout`.
Diagnostic logs must go to `stderr`; `stdout` must contain only valid MCP
messages.

This is not a single shared daemon. If Codex, Claude, and VS Code all connect to
the same target project through `stdio`, each client may start its own P2P MCP
server process. Shared state must therefore live outside the MCP process: in the
target repository, `.p2p/`, Git history, and P2P core storage.

For a future multi-agent setup that requires one long-running shared service,
P2P Engine would need a Streamable HTTP MCP server. The current implementation
is local `stdio`.

Run the stdio server from the governed P2P decision root. Prefer the
project-local virtualenv form:

```bash
/path/to/project/.venv/bin/python \
  -m p2p_engine.mcp.server \
  --root /path/to/project
```

`--root` selects the governed P2P project root used for decisions and state. If
`p2p-mcp-server` is available on `PATH`, this shorter form remains valid:

```bash
p2p-mcp-server --root /path/to/project
```

## Verified Client Setup

The exact setup differs by client. Do not assume MCP configuration files are
portable across all clients without adaptation.

### Codex CLI

```bash
codex mcp add p2p-my-project -- \
  /path/to/my-project/.venv/bin/python \
  -m p2p_engine.mcp.server \
  --root /path/to/my-project
```

Codex CLI and the Codex IDE extension share MCP configuration through
`config.toml`. Use `codex mcp --help` to inspect available management commands,
and use `/mcp` inside the Codex terminal UI to inspect active servers.

### Claude Code

```bash
claude mcp add --transport stdio p2p-my-project -- \
  /path/to/my-project/.venv/bin/python \
  -m p2p_engine.mcp.server \
  --root /path/to/my-project
```

Use `claude mcp list`, `claude mcp get p2p-my-project`, and `claude mcp remove
p2p-my-project` to manage the entry. Inside Claude Code, use `/mcp` to inspect
connected servers.

### Claude Desktop

Claude Desktop uses a local MCP JSON configuration file. Add the P2P server with
the same command and arguments:

```json
{
  "mcpServers": {
    "p2p-my-project": {
      "command": "/path/to/my-project/.venv/bin/python",
      "args": [
        "-m",
        "p2p_engine.mcp.server",
        "--root",
        "/path/to/my-project"
      ]
    }
  }
}
```

Documented config paths:

```text
macOS:   ~/Library/Application Support/Claude/claude_desktop_config.json
Windows: %APPDATA%\Claude\claude_desktop_config.json
```

### VS Code With GitHub Copilot Agent

VS Code's MCP configuration is separate from Codex configuration. Use workspace
`.vscode/mcp.json` or the user profile MCP configuration:

```json
{
  "servers": {
    "p2p-my-project": {
      "type": "stdio",
      "command": "${workspaceFolder}/.venv/bin/python",
      "args": [
        "-m",
        "p2p_engine.mcp.server",
        "--root",
        "${workspaceFolder}"
      ]
    }
  }
}
```

Then ask the agent to start with compact context:

```text
Use the P2P MCP server and show p2p_context for this project.
```

## Safety Model

MCP tools are grouped by behavior:

- read-only tools inspect state;
- write-safe tools create drafts or deterministic generated artifacts;
- advisory tools create prompts or analysis without deciding;
- permission-gated tools perform privileged sync/proposal operations only with a matching consent receipt;
- governance decisions remain owner-controlled;
- missing write primitives must be reported, not bypassed by manual `.p2p/` edits.

Agents should use `p2p_context` before broad file reads. The context packet tells
the agent what is relevant, what commands are allowed, and what not to scan.

Permission-gated MCP tools validate:

```text
consent_id
operation
target
actor_id
single-use status
expiry, when present
```

The tool consumes the receipt after successful execution and stores result
metadata. Consent receipts are auditable local project records, not strong
authentication. In cloud-backed projects, Git provider permissions, protected
branches, and token scopes remain the real enforcement layer for remote state.

## Tool Matrix

| Tool | Type | Mutates state? | Governance? | When to use |
| --- | --- | ---: | ---: | --- |
| `p2p_context` | read-only | no | no | First tool before broad reads. |
| `p2p_validate` | read-only | no | no | Check structural and semantic consistency. |
| `p2p_project_status` | read-only | no | no | Inspect deterministic project status. |
| `p2p_project_interaction_style_show` | read-only | no | no | Read effective project interaction style values and descriptions. |
| `p2p_project_interaction_style_set` | write-safe | yes | no | Set project-level interaction style values without governance side effects. |
| `p2p_next` | read-only | no | no | Show advisory next actions. |
| `p2p_next_add` | write-safe | yes | no | Add a curated next action to the operational board. |
| `p2p_next_complete` | write-safe | yes | no | Complete a curated next action and audit it in the next-action log. |
| `p2p_next_retire` | write-safe | yes | no | Retire a curated next action and audit it in the next-action log. |
| `p2p_next_refresh` | write-safe | yes | no | Normalize curated next actions and report generated action count. |
| `p2p_proposal_list` | read-only | no | no | List proposals, optionally by status. |
| `p2p_proposal_show` | read-only | no | no | Inspect one proposal summary; pass `full: true` for the owner review view. |
| `p2p_choice_list` | read-only | no | no | List project choices. |
| `p2p_choice_show` | read-only | no | no | Inspect one choice. |
| `p2p_governance_status` | read-only | no | no | Read governance mode and audit artifact counts. |
| `p2p_governance_validate` | read-only | no | no | Validate governance artifacts without changing them. |
| `p2p_choice_governance_preflight` | read-only | no | no | Preview owner-decision readiness for a choice without deciding it. |
| `p2p_vote_status` | read-only | no | no | Read proposal-local advisory vote counts. |
| `p2p_precedent_search` | read-only | no | no | Search deterministic explicit precedent matches without recording precedents. |
| `p2p_change_status` | read-only | no | no | List Change Set statuses. |
| `p2p_change_show` | read-only | no | no | Inspect one Change Set. |
| `p2p_change_tasks` | read-only | no | no | Inspect Change Set tasks and actions. |
| `p2p_work_list` | read-only | no | no | List Work manifests. |
| `p2p_work_status` | read-only | no | no | Show operational Work summaries. |
| `p2p_work_show` | read-only | no | no | Inspect one Work manifest. |
| `p2p_registry_status` | read-only | no | no | Check generated registry availability and freshness. |
| `p2p_registry_show` | read-only | no | no | Read a generated registry. |
| `p2p_project_show` | read-only | no | no | Read generated project sections or feature documents. |
| `p2p_project_remote_show` | read-only | no | no | Inspect local/cloud remote profile metadata. |
| `p2p_project_remote_configure` | write-safe | yes | no | Configure P2P remote profile metadata without provider side effects. |
| `p2p_permissions_show` | read-only | no | no | Read project-declared actors and role policy. |
| `p2p_consent_request` | write-safe | yes | no | Record a pending owner consent request; does not grant consent. |
| `p2p_consent_status` | read-only | no | no | List consent receipts without creating or consuming them. |
| `p2p_consent_show` | read-only | no | no | Inspect one consent receipt. |
| `p2p_sync_status` | read-only | no | no | Inspect managed Git sync readiness. |
| `p2p_sync_fetch` | managed sync | yes | no | Fetch configured remote refs without pull/push/merge. |
| `p2p_proposal_draft_commit` | managed branch | yes | no | Commit proposal draft changes before branching. |
| `p2p_proposal_branch` | managed branch | yes | no | Create and check out a managed proposal branch from an explicit base. |
| `p2p_proposal_branch_status` | read-only | no | no | Inspect one managed proposal branch. |
| `p2p_proposal_branch_scan` | read-oriented | yes | no | Scan local managed proposal branches and refresh the proposal branch registry. |
| `p2p_spec_status` | read-only | no | no | List generated P2P-native software specs. |
| `p2p_spec_show` | read-only | no | no | Read a generated software spec index. |
| `p2p_spec_export_status` | read-only | no | no | List generated downstream spec exports. |
| `p2p_spec_export_show` | read-only | no | no | Read the primary file for a spec export target. |
| `p2p_assess_show` | read-only | no | no | Show stored readiness assessment. |
| `p2p_project_rubrics_show` | read-only | no | no | Read configured maturity rubrics. |
| `p2p_maturity_show` | read-only | no | no | Show stored maturity assessment. |
| `p2p_intake_status` | read-only | no | no | List intake records and analysis state. |
| `p2p_project_brief_show` | read-only | no | no | Show imported operational brief, if present. |
| `p2p_conflict_status` | read-only | no | no | Read recorded project conflicts. |
| `p2p_init_project` | write-safe | yes | no | Bootstrap a P2P workspace and agent boundaries. |
| `p2p_agent_instructions_refresh` | write-safe | yes | no | Refresh agent instructions and policy. |
| `p2p_agent_list` | read-only | no | no | List supported and installed agent integrations. |
| `p2p_agent_show` | read-only | no | no | Show one agent integration, files, and drift state. |
| `p2p_agent_doctor` | read-only | no | no | Return structured agent integration health findings. |
| `p2p_agent_install` | write-safe | yes | no | Install project-local generated files for an agent adapter. |
| `p2p_agent_update` | write-safe | yes | no | Update generated agent files while preserving drift safety. |
| `p2p_agent_uninstall` | write-safe | yes | no | Remove only safe, managed, non-shared files for an adapter. |
| `p2p_registry_refresh` | write-safe | yes | no | Regenerate deterministic registries. |
| `p2p_assess_refresh` | write-safe | yes | no | Generate deterministic readiness assessment. |
| `p2p_project_rubrics_init` | write-safe | yes | no | Create or refresh project rubrics. |
| `p2p_maturity_refresh` | write-safe | yes | no | Generate deterministic maturity assessment. |
| `p2p_proposal_create` | write-safe | yes | no | Create a draft proposal. |
| `p2p_proposal_update` | write-safe | yes | no | Update structured draft/proposal sections. |
| `p2p_proposal_contribution_add` | write-safe | yes | no | Add a typed contribution to a proposal. |
| `p2p_proposal_contribution_list` | read-only | no | no | List contributions recorded for a proposal. |
| `p2p_proposal_readiness_get` | read-only | no | no | Read stored proposal readiness or `not_assessed`. |
| `p2p_proposal_readiness_init` | write-safe | yes | no | Bootstrap a conservative readiness assessment from proposal artifacts. |
| `p2p_proposal_readiness_refresh` | write-safe | yes | no | Recompute readiness score from stored criterion evidence. |
| `p2p_proposal_readiness_assess` | write-safe | yes | no | Evidence-aware readiness recalculation from current artifacts and structured question state when available. |
| `p2p_proposal_readiness_explain` | read-only | no | no | Explain readiness score, failed gates, gaps, next actions, and owner-question state evidence. |
| `p2p_proposal_readiness_list_gaps` | read-only | no | no | List readiness failed gates, missing criteria, next actions, and owner-question state evidence. |
| `p2p_proposal_readiness_review` | read-only | no | no | Review readiness gaps, owner questions, structured question categories, challenge points, and acceptance cautions. |
| `p2p_proposal_questions_status` | read-only | no | no | Read proposal question state or `not_initialized`. |
| `p2p_proposal_questions_init` | write-safe | yes | no | Initialize deterministic question state for a proposal. |
| `p2p_proposal_questions_add` | write-safe | yes | no | Add a readiness-linked owner question. |
| `p2p_proposal_questions_answer` | write-safe | yes | no | Record an answer for one proposal question. |
| `p2p_proposal_questions_next` | read-only | no | no | Return the next eligible proposal question. |
| `p2p_proposal_questions_apply` | write-safe | yes | no | Mark answered questions as applied and return an artifact-aware update plan. |
| `p2p_proposal_artifact_status` | read-only | no | no | Show proposal artifact coverage state plus the logical artifact catalog. |
| `p2p_proposal_artifact_init` | write-safe | yes | no | Initialize or refresh artifact-aware proposal state without deciding governance. |
| `p2p_proposal_artifact_set` | write-safe | yes | no | Set one artifact expectation/status/rationale without changing proposal decisions. |
| `p2p_proposal_artifact_confirm` | write-safe | yes | no | Record owner confirmation for one artifact state without accepting/rejecting the proposal. |
| `p2p_proposal_artifact_mark_legacy` | write-safe | yes | no | Mark artifact state as advisory `absent_legacy` for older proposals. |
| `p2p_explore_import` | write-safe | yes | no | Import exploration artifact content from a source path, direct content, or allowlisted artifact payloads. |
| `p2p_impact_import` | write-safe | yes | no | Import impact artifacts from a source path, direct content, or allowlisted YAML artifact payloads with validation. |
| `p2p_clarify_import` | write-safe | yes | no | Import clarification content into `clarifications.md`. |
| `p2p_synthesize_import` | write-safe | yes | no | Import synthesized proposal content into `proposal.md`. |
| `p2p_plan_import` | write-safe | yes | no | Import execution-plan content into `execution-plan.md`. |
| `p2p_tasks_import` | write-safe | yes | no | Import task YAML into `tasks.yml` with tasks validation. |
| `p2p_change_create` | write-safe | yes | no | Create a metadata-only Change Set from an accepted proposal. |
| `p2p_project_refresh` | write-safe | yes | no | Refresh generated project definition files. |
| `p2p_project_export` | write-safe | yes | no | Export the visible human-facing project definition to `outputs/latest/project.md`. |
| `p2p_project_export_status` | read-only | no | no | Read visible project definition export status and review snapshots. |
| `p2p_project_vertical_list` | read-only | no | no | List internal and project-local vertical packs plus active/fallback state. |
| `p2p_project_vertical_show` | read-only | no | no | Read one vertical pack, including inherited `base_project` sections. |
| `p2p_project_vertical_validate` | read-only | no | no | Validate a vertical ID, `vertical.yml`, or pack directory. |
| `p2p_project_vertical_propose` | advisory | no | no | Generate an importable custom vertical candidate from a project idea. |
| `p2p_project_vertical_add` | write-safe | yes | no | Add a project-local vertical pack without making governance decisions. |
| `p2p_project_vertical_select` | write-safe | yes | no | Select the active project vertical without accepting or changing proposals. |
| `p2p_project_vertical_lock_show` | read-only | no | no | Read vertical lock status without repair or fallback mutation. |
| `p2p_project_vertical_lock_repair` | write-safe | yes | no | Explicitly create or repair `vertical.lock.yml` from active vertical state. |
| `p2p_project_context` | read-only | no | no | Read active vertical, lock, rubric, definition summary, warnings, and next suggestion. |
| `p2p_project_sections` | read-only | no | no | List active or specified vertical sections. |
| `p2p_project_section_show` | read-only | no | no | Read one active or specified vertical section. |
| `p2p_project_definition_show` | read-only | no | no | Read durable project definition state. |
| `p2p_project_definition_update` | write-safe | yes | no | Apply a structured project definition patch file. |
| `p2p_project_readiness_review` | advisory/read-only | no | no | Review capisaldi coverage, unmapped proposals, and questions against a vertical. |
| `p2p_spec_refresh` | write-safe | yes | no | Generate a P2P-native software spec from a Change Set. |
| `p2p_spec_export` | write-safe | yes | no | Export spec outputs for `generic`, `openspec`, or `speckit`. |
| `p2p_spec_export_validate` | read-only | no | no | Validate an existing spec export. |
| `p2p_work_plan` | write-safe | yes | no | Create a Work manifest from a validated export. |
| `p2p_work_branch` | managed Work | yes | no | Create and check out the managed Work branch. |
| `p2p_work_submit` | managed Work | yes | no | Commit implementation changes on the managed Work branch. |
| `p2p_work_review` | managed Work | yes | no | Record local Work review readiness. |
| `p2p_work_publish` | permission-gated | yes | yes | Publish reviewed Work branch with `work_publish` consent. |
| `p2p_work_request_review` | permission-gated | yes | yes | Record provider-advisory Work review metadata with `work_request_review` consent. |
| `p2p_work_accept` | permission-gated | yes | yes | Merge published Work branch into its base branch with `work_accept` consent. |
| `p2p_work_finalize` | permission-gated | yes | yes | Push accepted Work base branch with `work_finalize` consent. |
| `p2p_work_cleanup` | permission-gated | yes | yes | Delete finalized Work branches with `work_cleanup` consent; remote deletion requires `delete_remote: true`. |
| `p2p_sync_pull` | permission-gated | yes | yes | Fast-forward pull current branch with `sync_pull` consent. |
| `p2p_sync_push` | permission-gated | yes | yes | Push current branch with `sync_push` consent. |
| `p2p_proposal_publish` | permission-gated | yes | yes | Publish current proposal branch with `proposal_publish` consent. |
| `p2p_proposal_request_review` | permission-gated | yes | yes | Record review handoff metadata with `proposal_request_review` consent. |
| `p2p_proposal_accept` | permission-gated | yes | yes | Accept a draft proposal with `proposal_accept` consent. |
| `p2p_proposal_reject` | permission-gated | yes | yes | Reject a draft proposal with `proposal_reject` consent. |
| `p2p_proposal_defer` | permission-gated | yes | yes | Defer a draft proposal with `proposal_defer` consent. |
| `p2p_proposal_accept_branch` | permission-gated | yes | yes | Record owner-controlled branch acceptance with `proposal_accept_branch` consent. |
| `p2p_proposal_reject_branch` | permission-gated | yes | yes | Record owner-controlled branch rejection with `proposal_reject_branch` consent. |
| `p2p_proposal_merge` | permission-gated | yes | yes | Merge proposal branch into base branch with `proposal_merge` consent. |
| `p2p_proposal_finalize` | permission-gated | yes | yes | Push finalized base branch with `proposal_finalize` consent. |
| `p2p_proposal_cleanup` | permission-gated | yes | yes | Delete finalized/rejected/retired proposal branches with `proposal_cleanup` consent. |
| `p2p_intake_prompt` | advisory/write-safe | yes | no | Create an intake prompt for a raw idea. |
| `p2p_project_brief_prompt` | advisory/write-safe | yes | no | Create project brief prompt artifacts. |
| `p2p_choice_discover` | advisory | no | no | Discover possible choices and blockers. |
| `p2p_explore_prompt` | advisory/write-safe | yes | no | Generate an exploration prompt for a proposal. |
| `p2p_digest_prompt` | advisory/write-safe | yes | no | Generate a digest prompt for a proposal. |
| `p2p_clarify_prompt` | advisory/write-safe | yes | no | Generate a clarification prompt for a proposal. |
| `p2p_synthesize_prompt` | advisory/write-safe | yes | no | Generate a synthesis prompt for a proposal. |
| `p2p_plan_prompt` | advisory/write-safe | yes | no | Generate a planning prompt for a proposal. |
| `p2p_tasks_prompt` | advisory/write-safe | yes | no | Generate a task prompt for a proposal. |
| `p2p_swot_prompt` | advisory/write-safe | yes | no | Generate a SWOT prompt for a proposal. |
| `p2p_impact_prompt` | advisory/write-safe | yes | no | Generate an impact-analysis prompt for a proposal. |
| `p2p_spec_prompt` | advisory/write-safe | yes | no | Generate a software-spec refinement prompt for a Change Set. |

## Proposal Artifact Content Imports

Proposal artifact import tools are write-safe content tools. They write only
fixed proposal artifact targets and never accept, reject, defer, publish,
merge, finalize, or otherwise decide a proposal.

Use exactly one input mode per call:

```text
source     existing file or directory path; relative paths resolve from project root
content    direct string payload for the primary target
artifacts  object mapping allowlisted filenames to string payloads
```

Primary `content` targets:

| Tool | Target |
| --- | --- |
| `p2p_explore_import` | `exploration.md` |
| `p2p_impact_import` | `impact-map.yml` |
| `p2p_clarify_import` | `clarifications.md` |
| `p2p_synthesize_import` | `proposal.md` |
| `p2p_plan_import` | `execution-plan.md` |
| `p2p_tasks_import` | `tasks.yml` |

`artifacts` mode is supported only for exploration and impact imports.

Exploration artifact filenames:

```text
exploration.md
findings.md
alternatives.md
open-questions.md
risks.md
assumptions.md
suggested-scope.md
```

These filenames are import targets, not guaranteed scaffold files. A newly
created proposal may omit narrative artifacts until an explicit import or
generation step materializes content. MCP clients should use contribution,
prompt, import, readiness, and artifact-state tools instead of writing arbitrary
files under `.p2p/`.

Impact artifact filenames and required top-level YAML keys:

```text
impact-map.yml          impact
related-proposals.yml   related_proposals
conflict-analysis.yml   conflicts
```

Example direct payload import:

```json
{
  "proposal_id": "PROP-001",
  "content": "tasks: []\n"
}
```

Example source-path import:

```json
{
  "proposal_id": "PROP-001",
  "source": "outputs/proposal-tasks.yml"
}
```

The import tools return `artifact_import` metadata with the proposal ID, import
kind, input mode, imported paths, filenames, validation flags, and
`artifact_state_updated: false`.

Artifact content import is separate from artifact coverage state. Use
`p2p_proposal_artifact_status`, `p2p_proposal_artifact_set`, and
`p2p_proposal_artifact_confirm` when the owner or agent needs to record whether
an artifact is required, satisfied, deferred, not applicable, or confirmed.
`p2p_proposal_artifact_status` also returns `artifact_status`, a read-only
logical catalog with expectation, status, materialization kind, source hint,
provenance confidence, evidence path when present, summary, and next action.

`p2p_proposal_show` accepts `full: true` for the owner-facing review payload.
The response keeps the compact `proposal` field and adds `proposal_view` with
core sections, decision, readiness, contributions, grouped question sources,
narrative/imported artifact summaries, artifact status, and next actions.
Returned paths are backing evidence or source hints, not direct edit targets.

Unsupported generic artifact writes remain unsupported. Agents should report the
missing primitive instead of writing arbitrary files under `.p2p/`.

MCP now exposes permission-gated draft proposal accept/reject/defer decisions.
It also exposes local MCP parity for the managed Work lifecycle through
domain-specific Work tools. It still does not expose choice decisions, spec
imports, conflict recording, voting, precedent recording, choice blocking, raw
Git shortcuts, provider PR/MR creation, remote HTTP MCP, or a hosted IAM model.

For end-to-end proposal collaboration, MCP can prepare the path but cannot grant
owner consent:

```text
p2p_proposal_create or p2p_proposal_update
p2p_proposal_draft_commit
p2p_proposal_branch with base_branch, usually main
p2p_consent_request
owner grants consent through CLI, UI, or authenticated cloud workflow
p2p_proposal_publish
p2p_proposal_request_review
```

`p2p_consent_request` creates a `requested` receipt. Permission-gated tools
still require a `granted` receipt, so a request cannot be reused as approval.

## Example Calls

The exact UI depends on the MCP client, but the payloads follow the same shape.

Read compact context:

```json
{
  "tool": "p2p_context",
  "arguments": {
    "root": "/path/to/project",
    "budget": "small"
  }
}
```

Create a draft proposal:

```json
{
  "tool": "p2p_proposal_create",
  "arguments": {
    "root": "/path/to/project",
    "title": "Document MCP safety boundaries",
    "problem": "Agents need clear rules for which MCP tools can mutate state.",
    "goals": ["Make tool safety understandable."],
    "non_goals": ["Allow agents to decide owner governance outcomes."],
    "proposal": "Document each MCP tool as read-only, write-safe, or advisory.",
    "acceptance_criteria": ["A reader can tell which tools mutate state."]
  }
}
```

Refresh registries after accepted project state changes:

```json
{
  "tool": "p2p_registry_refresh",
  "arguments": {
    "root": "/path/to/project"
  }
}
```

Review project vertical readiness:

```json
{
  "tool": "p2p_project_readiness_review",
  "arguments": {
    "root": "/path/to/project"
  }
}
```

Generate a custom vertical candidate without selecting it:

```json
{
  "tool": "p2p_project_vertical_propose",
  "arguments": {
    "root": "/path/to/project",
    "idea": "progettare attivita volte a migliorare l'impatto sociale di una banca"
  }
}
```

Use a permission-gated proposal operation:

```bash
p2p permissions actor add lorenzo --role contributor
p2p consent grant proposal_publish PROP-001 --actor lorenzo --approved-by owner
```

```json
{
  "tool": "p2p_proposal_publish",
  "arguments": {
    "root": "/path/to/project",
    "proposal_id": "PROP-001",
    "actor_id": "lorenzo",
    "consent_id": "CONSENT-001"
  }
}
```

Common consent operation to tool mapping:

```text
sync_pull                 -> p2p_sync_pull
sync_push                 -> p2p_sync_push
proposal_publish          -> p2p_proposal_publish
proposal_request_review   -> p2p_proposal_request_review
proposal_accept           -> p2p_proposal_accept
proposal_reject           -> p2p_proposal_reject
proposal_defer            -> p2p_proposal_defer
proposal_accept_branch    -> p2p_proposal_accept_branch
proposal_reject_branch    -> p2p_proposal_reject_branch
proposal_merge            -> p2p_proposal_merge
proposal_finalize         -> p2p_proposal_finalize
proposal_cleanup          -> p2p_proposal_cleanup
work_publish              -> p2p_work_publish
work_request_review       -> p2p_work_request_review
work_accept               -> p2p_work_accept
work_finalize             -> p2p_work_finalize
work_cleanup              -> p2p_work_cleanup
```

Local Work lifecycle flow:

```text
p2p_work_plan
p2p_work_branch
p2p_work_submit
p2p_work_review
p2p_work_publish with work_publish consent
p2p_work_request_review with work_request_review consent
p2p_work_accept with work_accept consent
p2p_work_finalize with work_finalize consent
p2p_work_cleanup with work_cleanup consent
```

`p2p_work_request_review` records provider-advisory metadata and suggested next
steps only. It does not open GitHub pull requests, GitLab merge requests, or any
provider-side review records.

The local MCP server runs in the caller's local execution context. Remote HTTP
MCP, Wavekit user authentication, client grants, strong receipts, hosted audit
retention, tenancy, billing, and rate limits belong in a gateway layer outside
the P2P Engine core. A gateway can call the same core lifecycle methods, but it
must enforce its own remote identity and authorization policy before invoking
these local operations.

## Troubleshooting

Server cannot start:

```bash
/path/to/project/.venv/bin/python -m p2p_engine.mcp.server --root /path/to/project
```

Agent is reading too much:

```text
Use p2p_context first and follow the "Do not read" guidance in the context packet.
```

Agent wants to perform a governance decision:

```text
Stop unless the owner has explicitly instructed the action and the MCP tool has
a matching consent receipt. Use CLI or explicit permission-gated MCP tools only.
```

Tool appears missing:

```bash
python -m p2p_engine.mcp.server --help
p2p --help
```
