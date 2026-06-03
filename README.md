# P2P Engine

Turn messy project intent into versioned proposals, decisions, specs, and agent-ready context.

P2P Engine is a local CLI/core/MCP toolkit for preserving project intent in Git. It helps humans and AI agents move from rough ideas to explicit proposals, owner decisions, Change Sets, project rubrics, and downstream specification artifacts.

P2P Engine is an operating substrate for coding and planning agents, not a traditional developer productivity CLI. Humans remain in charge of supervision and decisions; agents use P2P to structure project intent, memory, and execution context.

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

- AI coding and planning agents that need structured project memory;
- humans supervising agent-driven project workflows;
- solo developers using Codex, Claude, or other AI agents;
- small technical teams that want Git-native project intent and decision history;
- maintainers who want decisions and tradeoffs to remain auditable;
- people experimenting with proposal-to-plan workflows.

## Human / Agent Model

Humans do not need to operate P2P Engine manually for every step. The intended model is agent-mediated: AI agents use the CLI or MCP server as a structured project cognition layer, while humans supervise outputs and make governance decisions.

## Status

```text
Status: Alpha / MVP+
Install: project-local virtualenv from GitHub Release wheel
CLI: usable
MCP: local stdio MVP
Hosted product: not included in this repository
Packaged binary: not yet available
Future package target: public package registry, e.g. PyPI
```

Current implementation includes proposal lifecycle, decisions, choices, Change Sets, Work metadata, registries, validation, compact context, rubrics, maturity assessment, spec/export MVP, and a guided init wizard.

## 5-Minute Agent Setup

The normal workflow is to install P2P Engine into the target project's own
virtualenv. GitHub Release wheels are the transitional distribution channel.
The future target is a public package registry where setup becomes
`python -m pip install p2p-engine`.

```text
Target project
  The project that gets `.p2p/` state, agent instructions, and a local `.venv`
  containing the `p2p` runtime.

Agent client
  Codex, Claude, or another MCP/CLI-capable agent that uses P2P primitives.
```

Create a project and install P2P Engine into that project-local virtualenv:

```bash
mkdir /tmp/my-project
cd /tmp/my-project
python3 -m venv .venv
.venv/bin/python -m pip install \
  https://github.com/BINARYA/p2p-Engine/releases/download/v0.1.0/p2p_engine-0.1.0-py3-none-any.whl
```

Initialize P2P inside the target project:

```bash
.venv/bin/p2p init "My Project" \
  --agent codex \
  --repository local \
  --domain software \
  --mcp-hint
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

Connect your agent to the target project in one of two ways:

```text
CLI access
  The agent can run P2P CLI commands from the target project.
  This gives access to the full local command surface when the owner explicitly authorizes actions.

MCP access
  The agent uses structured P2P MCP tools.
  This is the recommended structured integration. It includes read/status tools,
  draft/refinement tools, and selected permission-gated Git/proposal operations.
```

With either mode, ask the agent to start from compact P2P context:

```text
Use P2P for this project.
Start with p2p_context or `p2p context --budget small`.
Create a draft proposal for the first project direction.
Do not edit .p2p files by hand.
```

The agent should use P2P through MCP or CLI primitives, while you supervise and decide outcomes.

Current MCP access is agent-safe but not unlimited. Permission-gated tools can
publish, request review, accept/reject proposal branches, merge, finalize, and
cleanup proposal branches only with matching consent receipts. MCP still does
not create provider PR/MR resources, decide choices, import specs, or expose the
full Work lifecycle as permission-gated tools.

See [docs/INSTALL.md](docs/INSTALL.md) for project-local install, upgrade, and new-project setup. See [docs/MCP.md](docs/MCP.md) for MCP client setup, `stdio` behavior, and tool boundaries.

### Optional Manual CLI Trial

You can try P2P manually through the CLI to understand the model, debug setup,
or recover from agent/client issues. This is not the intended primary workflow
for normal use.

```bash
.venv/bin/p2p context --budget small
.venv/bin/p2p proposal create "First direction" \
  --problem "The project needs an explicit first direction." \
  --goal "Define the initial scope." \
  --proposal "Start with a small owner-reviewed proposal." \
  --acceptance "The owner can review and decide it."
```

For full manual workflows, use [docs/CLI-GUIDE.md](docs/CLI-GUIDE.md).

## Install

Current install method:

```text
project-local Python virtualenv + GitHub Release wheel
```

See [docs/INSTALL.md](docs/INSTALL.md) for installing P2P Engine and setting up a new target project.

## Use With Agents

P2P Engine can generate project-local agent instructions during `p2p init`.

For a new project, choose the profile that matches the agent environment you
intend to use:

```bash
.venv/bin/p2p init "My Project" --agent codex --repository local --domain software --mcp-hint
.venv/bin/p2p init "My Project" --agent claude --repository local --domain software --mcp-hint
.venv/bin/p2p init "My Project" --agent all --repository local --domain software --mcp-hint
```

For a remote-backed project, initialize the P2P project as cloud-backed, then
record the remote profile and verify sync readiness:

```bash
.venv/bin/p2p init "My Project" --agent codex --repository cloud --domain software --owner matteo --mcp-hint
git remote add origin git@github.com:ORG/REPO.git
.venv/bin/p2p project remote configure --mode remote --provider github --remote origin --url git@github.com:ORG/REPO.git
.venv/bin/p2p sync status
```

`p2p init --repository cloud` records project intent; it does not create a
GitHub/GitLab repository or configure SSH credentials. Proposal `PROP-073`
tracks future ergonomic improvements for one-step remote initialization.

Core agent rule:

```text
Use p2p_context first.
Use CLI/MCP primitives for P2P writes.
Do not edit .p2p by hand.
If a primitive is missing, stop and report what is missing.
```

If you want to contribute to P2P Engine itself with an agent, use the contributor
workflow in [CONTRIBUTING.md](CONTRIBUTING.md). The README intentionally does not
show repository-contributor setup commands because they are different from the
normal new-project setup.

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
