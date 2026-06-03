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

Run the stdio server from an installed environment:

```bash
p2p-mcp-server --root /path/to/project
```

Robust source-checkout form:

```bash
/path/to/p2p-Engine/.venv/bin/python \
  -m p2p_engine.mcp.server \
  --root /path/to/project
```

## Verified Client Setup

The exact setup differs by client. Do not assume MCP configuration files are
portable across all clients without adaptation.

### Codex CLI

```bash
codex mcp add p2p-my-project -- \
  /path/to/p2p-Engine/.venv/bin/python \
  -m p2p_engine.mcp.server \
  --root /path/to/my-project
```

Codex CLI and the Codex IDE extension share MCP configuration through
`config.toml`. Use `codex mcp --help` to inspect available management commands,
and use `/mcp` inside the Codex terminal UI to inspect active servers.

### Claude Code

```bash
claude mcp add --transport stdio p2p-my-project -- \
  /path/to/p2p-Engine/.venv/bin/python \
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
      "command": "/path/to/p2p-Engine/.venv/bin/python",
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
      "command": "/path/to/p2p-Engine/.venv/bin/python",
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
| `p2p_next` | read-only | no | no | Show advisory next actions. |
| `p2p_proposal_list` | read-only | no | no | List proposals, optionally by status. |
| `p2p_proposal_show` | read-only | no | no | Inspect one proposal summary. |
| `p2p_choice_list` | read-only | no | no | List project choices. |
| `p2p_choice_show` | read-only | no | no | Inspect one choice. |
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
| `p2p_registry_refresh` | write-safe | yes | no | Regenerate deterministic registries. |
| `p2p_assess_refresh` | write-safe | yes | no | Generate deterministic readiness assessment. |
| `p2p_project_rubrics_init` | write-safe | yes | no | Create or refresh project rubrics. |
| `p2p_maturity_refresh` | write-safe | yes | no | Generate deterministic maturity assessment. |
| `p2p_proposal_create` | write-safe | yes | no | Create a draft proposal. |
| `p2p_proposal_update` | write-safe | yes | no | Update structured draft/proposal sections. |
| `p2p_proposal_contribution_add` | write-safe | yes | no | Add a typed contribution to a proposal. |
| `p2p_change_create` | write-safe | yes | no | Create a metadata-only Change Set from an accepted proposal. |
| `p2p_project_refresh` | write-safe | yes | no | Refresh generated project definition files. |
| `p2p_spec_refresh` | write-safe | yes | no | Generate a P2P-native software spec from a Change Set. |
| `p2p_spec_export` | write-safe | yes | no | Export spec outputs for `generic`, `openspec`, or `speckit`. |
| `p2p_spec_export_validate` | read-only | no | no | Validate an existing spec export. |
| `p2p_work_plan` | write-safe | yes | no | Create a Work manifest from a validated export. |
| `p2p_sync_pull` | permission-gated | yes | yes | Fast-forward pull current branch with `sync_pull` consent. |
| `p2p_sync_push` | permission-gated | yes | yes | Push current branch with `sync_push` consent. |
| `p2p_proposal_publish` | permission-gated | yes | yes | Publish current proposal branch with `proposal_publish` consent. |
| `p2p_proposal_request_review` | permission-gated | yes | yes | Record review handoff metadata with `proposal_request_review` consent. |
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

MCP still does not expose proposal accept/reject/defer decisions, choice
decisions, spec imports, conflict recording, voting, precedent recording, choice
blocking, Work branch creation, Work submission, Work review, Work publishing,
Work acceptance, Work finalization, Work cleanup, provider PR/MR creation, or a
hosted IAM model.

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
proposal_accept_branch    -> p2p_proposal_accept_branch
proposal_reject_branch    -> p2p_proposal_reject_branch
proposal_merge            -> p2p_proposal_merge
proposal_finalize         -> p2p_proposal_finalize
proposal_cleanup          -> p2p_proposal_cleanup
```

## Troubleshooting

Server cannot start:

```bash
/path/to/p2p-Engine/.venv/bin/python -m p2p_engine.mcp.server --root /path/to/project
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
