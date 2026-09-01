# P2P Engine

Turn messy project intent into versioned proposals, decisions, specs, and agent-ready context.

P2P Engine is a local CLI/core/MCP toolkit for preserving structured project
intent. It helps humans and AI agents move from rough ideas to explicit
proposals, owner decisions, Change Sets, project rubrics, and downstream
specification artifacts.

P2P Engine is an operating substrate for coding and planning agents, not a traditional developer productivity CLI. Humans remain in charge of supervision and decisions; agents use P2P to structure project intent, memory, and execution context.

## Why

Project intent is easy to lose.

- Discussions spread across chats, issues, branches, and notes.
- AI agents need bounded context, not a full repository dump.
- Decisions need traceability: who decided what, why, and what changed.
- Downstream tools need structured project definition, not only prose.

P2P Engine keeps the working memory of a project inside `.p2p/`. The current
filesystem adapter is selected by a replica-local storage manifest, while CLI,
MCP and the logical project model use a storage-neutral application boundary.
Source-control and delivery systems may version or reference project state, but
remain external integrations rather than P2P runtime lifecycle primitives.

That memory also has a storage-neutral canonical contract. Deterministic
`.p2pbundle` archives move logical project state and managed blobs without
copying replica-local state, credentials, generated integrations, or a live
database; separately verified `.p2pbackup` archives support local recovery.

## What It Does

- captures rough ideas and proposal drafts;
- creates structured proposals with goals, non-goals, acceptance criteria, and context;
- compares alternatives through choices, conflicts, and impact prompts;
- records owner decisions;
- derives Change Sets from accepted proposals;
- manages logical Work planning and handoff metadata;
- generates compact context packets for agents;
- assigns a stable project UUID distinct from names, paths, local replicas and remote IDs;
- resolves exactly one writable local storage adapter per project without
  exposing its layout to agents, CLI consumers or MCP clients;
- derives compact vertical-aware project memory for bounded retrieval;
- keeps a detached project-owned structure that can be edited, retired,
  exported as a portable vertical, or replaced from one exact release;
- discovers portable verticals through provider-neutral registry-v2 domain
  metadata;
- validates P2P project state;
- assesses project readiness and definition maturity;
- converges owner-answered project questions into definition state through an
  atomic preview/apply workflow;
- prepares complete vertical-aware evidence for autonomous, multilingual human
  project publications;
- generates and exports project specs for downstream tools.

## Who It Is For

- AI coding and planning agents that need structured project memory;
- humans supervising agent-driven project workflows;
- solo developers using Codex, Claude, or other AI agents;
- small technical teams that want structured project intent and decision history;
- maintainers who want decisions and tradeoffs to remain auditable;
- people experimenting with proposal-to-plan workflows.

## Human / Agent Model

Humans do not need to operate P2P Engine manually for every step. The intended model is agent-mediated: AI agents use the CLI or MCP server as a structured project cognition layer, while humans supervise outputs and make governance decisions.

## Status

```text
Status: Alpha / MVP+
Source version: 0.6.0
Install: uv-managed user tool from the exact GitHub Release wheel
CLI: usable
MCP: local stdio MVP
Hosted product: not included in this repository
Python wheel and sdist: reproducible release automation implemented
Standalone compiled binary: not available
Future package target: public package registry, e.g. PyPI
```

Current implementation includes proposal lifecycle, decisions, choices, Change Sets, Work metadata, registries, validation, compact context, rubrics, maturity assessment, spec/export MVP, and a guided init wizard.

The internal storage architecture and compatibility boundary are documented in
[`docs/PROJECT-STORAGE-PORTS.md`](docs/PROJECT-STORAGE-PORTS.md).

## 5-Minute Agent Setup

The recommended local workflow installs P2P Engine once as an isolated uv user
tool. uv obtains its own compatible Python, so target projects do not need a
Python installation or `.venv`. GitHub Release wheels are the current
distribution channel; public-index installation remains a future option.

```text
Target project
  The project that gets `.p2p/` state and agent instructions. The P2P runtime
  remains in uv's user-level tool directory outside this project.

Agent client
  Codex, Claude, or another MCP/CLI-capable agent that uses P2P primitives.
```

Install the pinned uv release using its official owner-run bootstrap (choose
one command), then install the exact P2P Engine 0.6.0 wheel:

```bash
# Linux and macOS
curl -LsSf https://astral.sh/uv/0.12.6/install.sh | sh

# Windows PowerShell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/0.12.6/install.ps1 | iex"

uv tool install --managed-python --python 3.12 --no-config \
  https://github.com/BINARYA/p2p-Engine/releases/download/v0.6.0/p2p_engine-0.6.0-py3-none-any.whl
uv tool update-shell  # only if uv reports that its tool bin is not on PATH

mkdir /tmp/my-project
cd /tmp/my-project
```

Installing uv, its managed Python, or P2P Engine changes the host environment
and is always an explicit owner action. P2P commands, MCP and generated agents
never run these installation commands automatically. See
[docs/INSTALL.md](docs/INSTALL.md) for verified downloads, lifecycle,
offline/proxy behavior, Windows details and the pip/virtualenv fallback.

Initialize P2P inside the target project:

```bash
p2p init "My Project" \
  --agent codex \
  --domain software \
  --vertical binarya/software_project@2.0.0 \
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
  draft/refinement tools, and selected permission-gated governance operations.
```

With either mode, ask the agent to start from compact P2P context:

```text
Use P2P for this project.
Start with p2p_context or `p2p context --budget small`.
Create a draft proposal for the first project direction.
Do not edit .p2p files by hand.
```

The agent should use P2P through MCP or CLI primitives, while you supervise and decide outcomes.

Workspace schema 4 distinguishes the project authority, the authorized subject
and the actual client or agent executor. Standalone projects keep the local
owner policy. Hosted integrations may supply a typed external attestation for
implemented governed mutations, but P2P neither stores provider credentials
nor verifies hosted grants online. See
[docs/AUTHORITY-CONTEXT.md](docs/AUTHORITY-CONTEXT.md).

Current MCP access is agent-safe but not unlimited. Permission-gated tools can
apply supported governance decisions only with matching authority and consent
evidence. MCP does not create branches, commits, provider PR/MR resources,
releases, or other source-delivery artifacts.

See [docs/INSTALL.md](docs/INSTALL.md) for uv-first install, upgrade, rollback,
uninstall and new-project setup. See [docs/MCP.md](docs/MCP.md) for MCP client
setup, `stdio` behavior, and tool boundaries.

### Optional Manual CLI Trial

You can try P2P manually through the CLI to understand the model, debug setup,
or recover from agent/client issues. This is not the intended primary workflow
for normal use.

```bash
p2p context --budget small
p2p proposal create "First direction" \
  --problem "The project needs an explicit first direction." \
  --goal "Define the initial scope." \
  --proposal "Start with a small owner-reviewed proposal." \
  --acceptance "The owner can review and decide it."
p2p proposal readiness assess PROP-001
p2p proposal show PROP-001 --format json
```

Proposal detail reports whether stored readiness is `current`, `stale`, or
`not_assessed`. Deterministic server workers can request an atomic,
receipt-backed recalculation with `--format json --operation-key <key>` and
recover uncertain responses through `p2p mutation status`.

For full manual workflows, use [docs/CLI-GUIDE.md](docs/CLI-GUIDE.md).

### Human Project Publication

Publication is a derived reader output, not a governance report. English is the
default and other normalized language editions can coexist without overwriting
one another:

```bash
p2p project publish prepare --language en --output-name project
p2p project publish list
```

Prepare emits a bounded curator packet plus exact Markdown, project-model, and
evidence-accounting candidate paths. Import validates and atomically commits all
three before validation, optional PDF rendering, and separate owner review. See
[the publication workflow](docs/CLI-GUIDE.md#10-publish-human-project-editions).

## Install

Recommended local install method:

```text
uv-managed Python user tool + exact GitHub Release wheel
```

See [docs/INSTALL.md](docs/INSTALL.md) for installing P2P Engine and setting up a new target project.

## Use With Agents

P2P Engine can generate project-local agent instructions during `p2p init`.
By default a new project gets the generic baseline plus all built-in
project-local adapters: Codex, Claude, Cursor, Copilot, Gemini, and OpenCode.

For a new project, use the default when multiple collaborators may use
different agents:

```bash
p2p init "My Project" --domain software --vertical binarya/software_project@2.0.0 --mcp-hint
```

You can also narrow the generated adapters:

```bash
p2p init "My Project" --agent codex --domain software --vertical binarya/software_project@2.0.0 --mcp-hint
p2p init "My Project" --agent codex --agent claude --domain software --vertical binarya/software_project@2.0.0 --mcp-hint
```

The `generic` baseline is always created and cannot be uninstalled.
Installed integrations are tracked in `.p2p/agent-integrations.yml`.
Their runtime/access-profile lifecycle is versioned independently from the
agent adapter choice. The current release implements the `standalone` profile;
`linked-local` and `remote-only` are reported but cannot be rendered yet.

Useful lifecycle commands:

```bash
p2p integration status --format json
p2p integration refresh --profile standalone --format json
p2p agent list
p2p agent show codex
p2p agent install cursor
p2p agent update all
p2p agent doctor all
p2p agent uninstall cursor
```

P2P initialization is source-control neutral. If a project is also stored in a
Git repository or delivered through a hosting provider, configure and operate
that system with its own tooling. Repository, issue, pull-request, commit and
release identifiers may be recorded only as inert traceability references.

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

Project Memory Scope
  Explicit section, project-global, or unassigned organization for classifiable memory.

Memory Classification
  Revision-bound organization status kept separate from project readiness.

Choice
  Explicit set of alternatives that needs a decision.

Change Set
  Operational package derived from accepted project intent.

Work
  Managed metadata for implementation or handoff work.

Registry
  Generated compatibility projection over P2P artifacts. Registry files are not
  read back as decision-context semantics.

Context Packet
  Compact, token-aware project summary for agents. Proposal-target packets add
  an explainable, evidence-linked nearby decision neighborhood.

Prompt Neighborhood
  Intake selects nearby memory from idea text; explore, impact, and synthesize
  select phase-specific proposal context without applying or deciding anything.

Rubric
  Project-domain checklist used to assess whether the project definition is complete enough.

Maturity Assessment
  Deterministic evaluation of project definition coverage. It is not implementation completeness.
```

## Documentation

Stable:

- [docs/INSTALL.md](docs/INSTALL.md)  
  Install a published release wheel, initialize a project, verify the CLI, and
  configure local MCP.

- [docs/TUTORIAL.md](docs/TUTORIAL.md)  
  End-to-end walkthrough from rough idea to proposal, owner decision, Change Set, and agent context.

- [docs/GLOSSARY.md](docs/GLOSSARY.md)  
  Short definitions for core P2P concepts.

- [docs/CONCEPTS.md](docs/CONCEPTS.md)  
  Short operational model: proposals, decisions, choices, Change Sets, registries, and agent context.

- [docs/CLI-GUIDE.md](docs/CLI-GUIDE.md)  
  Practical CLI workflows, expected output shapes, and recovery patterns.

- [docs/CLI-CONTRACT.md](docs/CLI-CONTRACT.md)
  Versioned JSON envelope, operation identifiers, exit classes, WaveKit worker commands, and consumer migration.

- [docs/WORKSPACE-SCHEMA.md](docs/WORKSPACE-SCHEMA.md)
  Current workspace schema contract, unsupported-schema behavior, and atomic transaction recovery.

- [docs/PROJECT-IDENTITY.md](docs/PROJECT-IDENTITY.md)
  Stable project UUID, local replica identity, copy intent, adoption, derivation and CLI/MCP contracts.

- [docs/AUTHORITY-CONTEXT.md](docs/AUTHORITY-CONTEXT.md)
  Project authority, subject/executor separation, capabilities, external attestations and rotation.

- [docs/VERTICAL-REGISTRY.md](docs/VERTICAL-REGISTRY.md)
  Provider-neutral registry protocol, secure login, immutable cache, pull, and offline init behavior.

- [docs/VERTICAL-DRAFTS.md](docs/VERTICAL-DRAFTS.md)
  Normalized draft contract, materialization, validation, local add, publication, and WaveKit boundary.

- [docs/MCP.md](docs/MCP.md)  
  Local MCP server setup, tool matrix, safety boundaries, and example calls.

- [docs/CANONICAL-MEMORY-AND-BUNDLES.md](docs/CANONICAL-MEMORY-AND-BUNDLES.md)
  Storage-neutral logical memory, deterministic bundles, physical backups, and governed restore.

Local demos:

- [examples/README.md](examples/README.md)
  Create disposable examples with the current runtime instead of relying on
  checked-in project snapshots.

Work in progress:

- [docs/AGENT-INTEGRATION.md](docs/AGENT-INTEGRATION.md)  
- [docs/PROJECT-INTEGRATION-ARTIFACTS.md](docs/PROJECT-INTEGRATION-ARTIFACTS.md)
  How Codex, Claude, and other agents should use P2P Engine safely and efficiently.

- [docs/API.md](docs/API.md)  
  Contributor-facing Python API reference. End-user agents should prefer CLI and MCP.

## Roadmap

Short-term:

- validate the 0.6.0 release across downstream integrations;
- validate MCP behavior with more real clients;
- continue hardening validation and recovery paths;
- measure the filesystem adapter behind the new application/storage ports
  against the frozen pre-port baseline.

Later:

- publish through a public Python package registry;
- optionally investigate a standalone compiled executable;
- strengthen spec/export workflows and extension points.

Hosted mediator or web products are outside this repository's current scope.

## Development

Run tests:

```bash
. .venv/bin/activate
python -m pytest -q
```

Validate an explicitly separate P2P project-state repository when governance
evidence is needed for P2P Engine development:

```bash
p2p context --budget small --root ../projects/p2p-engine-project
p2p validate --root ../projects/p2p-engine-project
```

## License

P2P Engine is licensed under the GNU General Public License version 3 or later
(`GPL-3.0-or-later`). Copyright © 2026 mrjungle and contributors. See
[LICENSE](LICENSE) for the complete license text.
