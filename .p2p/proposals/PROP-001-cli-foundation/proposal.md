# PROP-001 — CLI Foundation

## Status

`accepted`

## Problem

P2P Engine does not exist yet as an executable tool. The project has a solid foundation document, but no CLI, no generated `.p2p/` structure, no automated proposal workflow, and no prompt generation.

Without a first working CLI, every proposal must be created manually. That is acceptable for the bootstrap phase, but it must become automated quickly so the project can start using its own method.

## Context

The current repository is being bootstrapped manually. The manual `.p2p/` structure defines the file format that the first CLI must later generate.

The first useful milestone is not a web app, AI billing, MCP server, or complete exporter set. The first useful milestone is a local Git-native CLI that can create the same structure currently being created by hand.

## Goals

- Implement a minimal `p2p` CLI.
- Generate the `.p2p/` project structure with `p2p init`.
- Create proposal folders and baseline artifacts with `p2p proposal create`.
- Add structured contributions with `p2p contribution add`.
- Record decisions with `p2p decision record`.
- Generate prompt files for digest, clarify, plan, and tasks.
- Keep AI invocation optional and out of scope for the first implementation.
- Preserve compatibility with future OpenSpec and Spec Kit exports.

## Non-Goals

- No web app.
- No users, accounts, permissions, billing, or dashboard.
- No managed AI provider.
- No MCP server.
- No full OpenSpec or Spec Kit exporter in the first slice.
- No automatic code implementation.
- No advanced governance engine.

## Proposal

Build the first P2P Engine CLI using Python and Typer.

The CLI should focus on local file generation and workflow guidance:

```text
p2p init
p2p proposal create
p2p contribution add
p2p digest prompt
p2p clarify prompt
p2p decision record
p2p plan prompt
p2p tasks prompt
p2p status
```

The first version should implement prompt generation instead of direct AI integration. A command such as:

```bash
p2p digest prompt PROP-001
```

should generate:

```text
.p2p/prompts/PROP-001/digest.prompt.md
```

The user can then provide that prompt to Codex, ChatGPT, Claude, Llama, or another model manually and paste the output into the correct artifact.

## Alternatives

### Start With Web App

Rejected for the MVP. It introduces users, auth, persistence, collaboration, AI cost, deployment, and security problems before the core workflow is proven.

### Start With AI Adapter

Deferred. Direct AI invocation is useful later, but prompt generation validates the workflow with much less complexity.

### Start With OpenSpec Export

Deferred. Export becomes meaningful once proposal, decision, plan, and task artifacts are stable.

### Start With TypeScript

Possible, but Python is preferred for the first CLI because it is simple, readable, strong for local file workflows, and aligns well with a future FastAPI backend.

## Impacts

- Establishes the first executable version of P2P Engine.
- Turns the manual bootstrap into repeatable CLI behavior.
- Enables dogfooding from `PROP-002` onward.
- Creates a stable boundary before adding AI adapters, exporters, or a web layer.

## Risks

- The CLI may overfit to the manually created bootstrap structure.
- The command tree may become too broad too early.
- YAML schemas may drift without validation.
- Prompt output may be inconsistent until artifact contracts are clearer.

## Open Questions

- Should `p2p init` initialize Git if the directory is not already a repository?
- Should `p2p proposal create` create a Git branch by default in MVP 1?
- Should contribution entry be interactive, flag-based, or both?
- Should proposal IDs be allocated from existing folders or from a central counter in `project.yml`?
- Should prompt templates live as package resources or generated project templates?

## Acceptance Criteria

- A user can install or run the CLI locally.
- `p2p init` creates the baseline `.p2p/` structure.
- `p2p proposal create "CLI Foundation"` creates a proposal folder and baseline artifacts.
- `p2p contribution add PROP-001` appends a valid YAML contribution.
- `p2p decision record PROP-001 --outcome accepted` records a decision artifact.
- Prompt commands generate prompt files under `.p2p/prompts/<proposal-id>/`.
- `p2p status` shows project and proposal state.
- No direct AI provider is required.

## Decision

Accepted. See `decision.md`.

