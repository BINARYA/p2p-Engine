# P2P Engine

P2P Engine is a local project-governance engine for turning ideas into versioned project intent.

It provides a deterministic core, a CLI, and an MCP server for managing:

- proposals and owner decisions;
- choices and alternatives;
- Change Sets and managed work metadata;
- project registries and validation;
- compact context for agents;
- project definition rubrics and maturity assessment;
- software spec generation and export metadata.

P2P Engine stores project state under `.p2p/`. Git keeps the history. The owner keeps governance authority.

## What This Repository Contains

This repository is the P2P Engine implementation.

```text
src/p2p_engine/
  core/data models and prompt helpers
  storage/filesystem-backed P2P workspace logic
  cli.py command-line interface
  mcp/ local stdio MCP server

.codex/skills/p2p-engine/
  Codex skill for working on P2P Engine itself

.p2p/
  P2P project state for this repository

docs/
  installation, CLI, MCP, agent, API, and conceptual documentation

tests/
  CLI, MCP, storage, and workflow tests
```

Out-of-scope for this repository:

- a hosted P2P web product;
- a mediator assistant service;
- provider-specific AI infrastructure.

Those may use P2P Engine later, but they should be designed as separate layers or repositories.

## Install

Current installation is from source with a Python virtual environment.

```bash
git clone git@github.com:BINARYA/p2p-Engine.git
cd p2p-Engine
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
p2p --help
```

Detailed install instructions are in [docs/INSTALL.md](docs/INSTALL.md).

## Quick Start

Create a new P2P-managed project:

```bash
mkdir my-project
cd my-project
p2p init
```

The wizard asks for:

```text
Project name
Initial agent profile
Repository mode
Project domain
Rubric criteria
MCP setup hint
```

Inspect compact project context:

```bash
p2p context --budget small
```

Create a proposal:

```bash
p2p proposal create "First direction" \
  --problem "The project needs an explicit first direction." \
  --goal "Define the initial scope." \
  --proposal "Start with a small owner-reviewed proposal." \
  --acceptance "The owner can review and decide it."
```

Review and decide:

```bash
p2p proposal show PROP-001
p2p proposal accept PROP-001 --reason "This is the initial direction."
```

Check project state:

```bash
p2p validate
p2p registry refresh
p2p next
p2p assess refresh
p2p assess show
p2p assess maturity refresh
p2p assess maturity show
```

## Using P2P Engine With Agents

Agents should use P2P through CLI or MCP primitives. They should not edit `.p2p/` by hand.

Start with compact context:

```bash
p2p context --budget small
```

With MCP, configure the local server:

```bash
codex mcp add p2p-my-project -- \
  /path/to/p2p-Engine/.venv/bin/python \
  -m p2p_engine.mcp.server \
  --root /path/to/my-project
```

Then ask the agent to use `p2p_context` before broad file reads.

Agent rule:

```text
If a CLI command or explicit MCP write tool cannot perform a P2P mutation,
stop and report the missing primitive. Do not invent .p2p files.
```

## Documentation

- [docs/INSTALL.md](docs/INSTALL.md)  
  How to install from source, initialize a project, verify the CLI, and configure MCP locally.

- [docs/CLI-GUIDE.md](docs/CLI-GUIDE.md)  
  CLI workflows and command groups. This is the place for command-by-command examples and expected outputs.

- [docs/MCP.md](docs/MCP.md)  
  MCP server setup, tool categories, safety boundaries, and example agent calls.

- [docs/AGENT-INTEGRATION.md](docs/AGENT-INTEGRATION.md)  
  How Codex, Claude, and other agents should use P2P Engine without wasting context or bypassing governance.

- [docs/API.md](docs/API.md)  
  Contributor-facing reference for the core Python API. This is not the primary interface for end-user agents.

- [docs/p2p-engine-foundation.md](docs/p2p-engine-foundation.md)  
  Conceptual foundation and design rationale.

- [docs/p2p-engine-landscape-and-positioning.md](docs/p2p-engine-landscape-and-positioning.md)  
  Positioning against adjacent tools and workflows.

## Current Status

Implemented MVP+:

- deterministic filesystem-backed core;
- CLI;
- local stdio MCP server;
- proposal, decision, choice, Change Set, Work, registry, validation workflows;
- compact context packets for agents;
- project definition rubrics and maturity assessment;
- guided init wizard;
- spec/export MVP;
- managed work lifecycle MVP.

Current limits:

- source/venv install only;
- MCP needs broader real-client validation;
- rubric maturity is deterministic and evidence/keyword based;
- coverage reporting is planned but not yet implemented;
- large internal `P2PWorkspace` refactor is planned but not started.

## Development

Run tests:

```bash
. .venv/bin/activate
python -m pytest -q
```

Validate this repository's P2P state:

```bash
p2p context --budget small
p2p validate
p2p assess show
p2p assess maturity show
```

## License

See [LICENSE](LICENSE).

