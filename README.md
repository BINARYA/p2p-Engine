# P2P Engine

Turn messy project intent into versioned proposals, decisions, specs, and agent-ready context.

P2P Engine is a local CLI/core/MCP toolkit for preserving project intent in Git. It helps humans and AI agents move from rough ideas to explicit proposals, owner decisions, Change Sets, project rubrics, and downstream specification artifacts.

## Why

Project intent is easy to lose.

- Discussions spread across chats, issues, branches, and notes.
- AI agents need bounded context, not a full repository dump.
- Decisions need traceability: who decided what, why, and what changed.
- Downstream tools need structured project definition, not only prose.

P2P Engine keeps the working memory of a project in `.p2p/`, backed by Git.

## What It Does

- captures rough ideas and proposal drafts;
- creates structured proposals with goals, non-goals, acceptance criteria, and context;
- compares alternatives through choices, conflicts, and impact prompts;
- records owner decisions;
- derives Change Sets from accepted proposals;
- manages work metadata for branch-based implementation flows;
- generates compact context packets for agents;
- validates P2P project state;
- assesses project readiness and definition maturity;
- generates and exports project specs for downstream tools.

## Who It Is For

- solo developers using Codex, Claude, or other AI agents;
- small technical teams that want Git-native project memory;
- maintainers who want decisions and tradeoffs to remain auditable;
- people experimenting with proposal-to-plan workflows;
- projects that need structured intent before implementation or code generation.

## Status

```text
Status: Alpha / MVP+
Install: from source with Python virtualenv
CLI: usable
MCP: local stdio MVP
Hosted product: not included in this repository
Packaged binary: not yet available
```

Current implementation includes proposal lifecycle, decisions, choices, Change Sets, Work metadata, registries, validation, compact context, rubrics, maturity assessment, spec/export MVP, and a guided init wizard.

## 5-Minute Demo

Install from source:

```bash
git clone https://github.com/BINARYA/p2p-Engine.git
cd p2p-Engine
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
```

Create a new P2P project:

```bash
mkdir /tmp/p2p-demo
cd /tmp/p2p-demo
p2p init "Demo Project" --agent codex --repository local --domain software
```

Expected output:

```text
P2P workspace initialized.
  created .p2p/project.yml
  created .p2p/project/rubrics.yml
  created AGENTS.md
  created .p2p/agent-policy.yml
Next steps:
  1. p2p registry refresh
  2. p2p status
  3. p2p next
```

Ask for compact context:

```bash
p2p context --budget small
```

Expected output:

```text
P2P compact context
  budget: small
Current state:
  validation:
    ok: True
Next actions:
  ...
Do not read:
  - Do not scan all .p2p/ directories.
```

Create a proposal:

```bash
p2p proposal create "First direction" \
  --problem "The project needs an explicit first direction." \
  --goal "Define the initial scope." \
  --proposal "Start with a small owner-reviewed proposal." \
  --acceptance "The owner can review and decide it."
```

Inspect and decide:

```bash
p2p proposal show PROP-001
p2p proposal accept PROP-001 --reason "This is the initial direction."
```

Refresh and assess:

```bash
p2p registry refresh
p2p validate
p2p assess refresh
p2p assess show
p2p assess maturity refresh
p2p assess maturity show
```

## Install

Current install method:

```text
source checkout + Python virtualenv
```

See [docs/INSTALL.md](docs/INSTALL.md) for full installation, verification, and MCP setup.

## Use With Codex Or Claude

P2P Engine can generate agent-facing instructions during `p2p init`.

For Codex:

```bash
p2p init "My Project" --agent codex --repository local --domain software --mcp-hint
```

For Claude:

```bash
p2p init "My Project" --agent claude --repository local --domain software --mcp-hint
```

Local MCP setup example:

```bash
codex mcp add p2p-my-project -- \
  /path/to/p2p-Engine/.venv/bin/python \
  -m p2p_engine.mcp.server \
  --root /path/to/my-project
```

Agent rule:

```text
Use p2p_context first.
Use CLI/MCP primitives for P2P writes.
Do not edit .p2p by hand.
If a primitive is missing, stop and report what is missing.
```

## Core Concepts

```text
Proposal
  A structured project idea with problem, context, goals, proposal text, and acceptance criteria.

Decision
  Owner-controlled outcome for a proposal or choice.

Choice
  Explicit set of alternatives that needs a decision.

Change Set
  Operational package derived from accepted project intent.

Work
  Managed metadata for implementation or handoff work.

Registry
  Generated index over P2P artifacts.

Context Packet
  Compact, token-aware project summary for agents.

Rubric
  Project-domain checklist used to assess whether the project definition is complete enough.

Maturity Assessment
  Deterministic evaluation of project definition coverage. It is not implementation completeness.
```

## Documentation

Stable:

- [docs/INSTALL.md](docs/INSTALL.md)  
  Install from source, initialize a project, verify the CLI, and configure local MCP.

- [docs/TUTORIAL.md](docs/TUTORIAL.md)  
  End-to-end walkthrough from rough idea to proposal, owner decision, Change Set, and agent context.

- [docs/GLOSSARY.md](docs/GLOSSARY.md)  
  Short definitions for core P2P concepts.

- [docs/CONCEPTS.md](docs/CONCEPTS.md)  
  Short operational model: proposals, decisions, choices, Change Sets, registries, and agent context.

- [docs/CLI-GUIDE.md](docs/CLI-GUIDE.md)  
  Practical CLI workflows, expected output shapes, and recovery patterns.

- [docs/MCP.md](docs/MCP.md)  
  Local MCP server setup, tool matrix, safety boundaries, and example calls.

Examples:

- [examples/minimal-software-project](examples/minimal-software-project)  
  Small software-domain project with an accepted proposal and Change Set.

- [examples/board-game-project](examples/board-game-project)  
  Board-game-domain project showing P2P outside software-only workflows.

Work in progress:

- [docs/AGENT-INTEGRATION.md](docs/AGENT-INTEGRATION.md)  
  How Codex, Claude, and other agents should use P2P Engine safely and efficiently.

- [docs/API.md](docs/API.md)  
  Contributor-facing Python API reference. End-user agents should prefer CLI and MCP.

Vision / design notes:

- [docs/vision/p2p-engine-foundation.md](docs/vision/p2p-engine-foundation.md)  
  Long-form design rationale. Contains implemented, planned, and exploratory ideas.

- [docs/vision/p2p-engine-landscape-and-positioning.md](docs/vision/p2p-engine-landscape-and-positioning.md)  
  Long-form positioning against adjacent tools and workflows.

## Roadmap

Short-term:

- expand CLI guide and MCP tool reference;
- add real coverage reporting;
- document agent integration patterns;
- plan modular refactor of the large `P2PWorkspace` facade;
- validate MCP behavior with more real clients.

Later:

- packaged or compiled CLI distribution;
- stronger spec/export workflows;
- clearer extension points for project-domain rubrics.

Hosted mediator or web products are outside this repository's current scope.

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
