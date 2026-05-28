# P2P Engine

P2P Engine is a deterministic project governance and specification engine for human/AI collaboration.

It turns ideas, discussions, proposals, decisions, choices, Change Sets, work branches, specs, and assessment criteria into versioned project state under `.p2p/`.

The goal is not to let AI decide for the owner. The goal is to make project intent explicit, inspectable, exportable, and usable by humans, agents, CLIs, MCP clients, and future product interfaces.

## Principles

```text
AI is expensive.
CLI is cheap.
Git is memory.
.p2p is governance.
Owner decides.
Agents work in bounded sessions.
```

P2P Engine is token-aware by design: agents should ask the engine for compact context before reading broad project files.

```bash
p2p context --budget small
p2p next --top 1
```

## Architecture

P2P Engine uses a five-layer architecture:

```text
Level 1 - P2P Core
Deterministic Python library for .p2p state, proposals, choices, Change Sets,
work manifests, registries, validation, context, assessment, rubrics, and specs.

Level 2 - P2P CLI
Terminal interface over the core for users, scripts, local automation, and agents.

Level 3 - Skill / MCP / Agent Interfaces
Agent-facing instructions and MCP tools. Codex skill, generic AGENTS.md,
Claude instructions, and an MCP stdio server exist in MVP form.

Level 4 - P2P Mediator
Future optional assistant layer. It should help users and agents formulate
proposals, understand overlap, and suggest actions while using Core/CLI/MCP as
the source of truth.

Level 5 - P2P Web
Future product UI for contribution, review, discussion, governance, and
collaboration.
```

Current status:

```text
Core: MVP+
CLI: MVP+
Skill/MCP/Agent Interfaces: MVP
Mediator: not implemented
Web: not implemented
```

## Installation

The current installation method is from source with a Python virtual environment.

Packaged or compiled CLI distribution is future work.

See [docs/INSTALL.md](docs/INSTALL.md).

## Quick Start

Clone and install from source:

```bash
git clone git@github.com:BINARYA/p2p-Engine.git
cd p2p-Engine
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
p2p --help
```

Initialize a new P2P-managed project:

```bash
mkdir my-project
cd my-project
p2p init
```

The interactive wizard asks for:

```text
Project name
Initial agent profile: generic, codex, claude, all
Repository mode: local, cloud
Project domain: generic, software, grant_document, board_game
Rubric criteria selection
MCP setup hint
```

After initialization:

```bash
p2p context --budget small
p2p validate
p2p registry refresh
p2p next
p2p assess refresh
p2p assess show
p2p project rubrics show
p2p assess maturity refresh
p2p assess maturity show
```

## Core Workflow

Create a draft proposal:

```bash
p2p proposal create "Define onboarding flow" \
  --problem "New users need a clear first-run path." \
  --goal "Make the first project setup understandable." \
  --proposal "Use a guided init wizard with project-domain rubrics." \
  --acceptance "A new user can initialize a project without editing .p2p by hand."
```

Inspect and decide proposals:

```bash
p2p proposal list
p2p proposal show PROP-001
p2p proposal accept PROP-001 --reason "Ready to implement."
p2p proposal reject PROP-002 --reason "Out of current scope."
p2p proposal defer PROP-003 --reason "Needs more context."
```

Create and progress a Change Set:

```bash
p2p change create --from PROP-001
p2p change status
p2p change show CHANGE-001
p2p change set-status CHANGE-001 planned
p2p change tasks CHANGE-001
```

Governance decisions remain owner-controlled. Agents may draft, analyze, compare, and suggest actions, but they must not accept, reject, defer, decide, merge, finalize, or cleanup unless the owner explicitly instructs the exact action.

## Agent Context

Use compact context before broad reads:

```bash
p2p context --budget small
p2p context --target PROP-001 --budget small
p2p context --target CHANGE-001 --budget medium
p2p context --format yaml
```

Context packets include:

```text
current state
next actions
relevant artifacts
allowed commands
do-not-read guidance
bounded next step
```

This is intended to reduce token usage for Codex, Claude, MCP clients, and future mediator/web layers.

## Assessment

P2P Engine separates structural readiness from project definition maturity.

Structural readiness:

```bash
p2p validate
p2p assess refresh
p2p assess show
```

This checks project-state quality: validation errors, stale registries, draft proposals, accepted proposals, choices, Change Sets, Work items, and operational brief availability.

Project definition maturity:

```bash
p2p project rubrics show
p2p assess maturity refresh
p2p assess maturity show
```

This checks whether enabled rubric topics are covered by P2P proposals, decisions, and Change Sets. It measures how well the project has been defined for export or implementation, not whether implementation is complete.

Rubrics are stored as editable project state:

```text
.p2p/project/rubrics.yml
```

Supported MVP domains:

```text
generic
software
grant_document
board_game
```

## MCP

P2P Engine includes a local stdio MCP server:

```bash
p2p-mcp-server --root /path/to/project
```

Tool coverage includes project status, next actions, proposal reads and draft writes, proposal refinement, contributions, validation, compact context, rubrics, maturity assessment, choice discovery, conflicts, impact prompts, registries, and basic status views.

Example Codex registration:

```bash
codex mcp add p2p-my-project -- p2p-mcp-server --root /path/to/my-project
```

If `p2p-mcp-server` is not on `PATH`, use the source checkout Python:

```bash
codex mcp add p2p-my-project -- \
  /path/to/p2p-Engine/.venv/bin/python \
  -m p2p_engine.mcp.server \
  --root /path/to/my-project
```

## Specs And Export

P2P Engine includes MVP commands for generating and validating project specs for downstream tools.

```bash
p2p spec refresh --change CHANGE-001
p2p spec prompt --change CHANGE-001
p2p spec import CHANGE-001 spec-output/
p2p spec export --change CHANGE-001 --target openspec
p2p spec export --change CHANGE-001 --target speckit
p2p spec export-validate CHANGE-001 --target speckit
```

The current exporter is still an MVP. The long-term direction is to make P2P project state suitable for downstream code generators, spec tools, and implementation agents.

## Managed Work

P2P Engine has an MVP managed-work lifecycle for Git-backed implementation work:

```bash
p2p work create --change CHANGE-001
p2p work status
p2p work submit WORK-001
p2p work review WORK-001
p2p work publish WORK-001
p2p work accept WORK-001
p2p work finalize WORK-001
p2p work cleanup WORK-001
```

The goal is eventually managed Git under the hood, with owner-controlled accept/merge behavior.

## Current Limits

```text
Installation is source/venv based.
Compiled or packaged CLI distribution is future work.
MCP should still be verified across more real clients.
Mediator and Web layers are not implemented.
Rubric maturity scoring is deterministic and keyword/evidence based in the MVP.
Advanced token estimation is deferred.
```

## Development

Run tests:

```bash
. .venv/bin/activate
python -m pytest -q
```

Validate project state:

```bash
p2p validate
p2p context --budget small
p2p assess show
p2p assess maturity show
```

