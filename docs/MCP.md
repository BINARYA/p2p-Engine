# P2P MCP Server

This document describes how agents can access P2P Engine through the local MCP
server. The MCP server is a local stdio bridge to P2P project state; it is not a
hosted product and it does not replace the CLI as the source of truth.

## Server

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

## Codex Example

```bash
codex mcp add p2p-my-project -- \
  /path/to/p2p-Engine/.venv/bin/python \
  -m p2p_engine.mcp.server \
  --root /path/to/my-project
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
- governance decisions remain owner-controlled;
- missing write primitives must be reported, not bypassed by manual `.p2p/` edits.

Agents should use `p2p_context` before broad file reads. The context packet tells
the agent what is relevant, what commands are allowed, and what not to scan.

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
| `p2p_work_status` | read-only | no | no | Show operational Work summaries. |
| `p2p_registry_show` | read-only | no | no | Read a generated registry. |
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
| `p2p_intake_prompt` | advisory/write-safe | yes | no | Create an intake prompt for a raw idea. |
| `p2p_project_brief_prompt` | advisory/write-safe | yes | no | Create project brief prompt artifacts. |
| `p2p_choice_discover` | advisory | no | no | Discover possible choices and blockers. |
| `p2p_impact_prompt` | advisory/write-safe | yes | no | Generate an impact-analysis prompt for a proposal. |

No current MCP tool accepts, rejects, defers, merges, finalizes, or decides
project governance outcomes. Use CLI commands for owner-directed governance
actions.

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
Stop. Governance decisions require explicit owner instruction and CLI support.
Use MCP only for read-only, write-safe, or advisory steps.
```

Tool appears missing:

```bash
python -m p2p_engine.mcp.server --help
p2p --help
```
