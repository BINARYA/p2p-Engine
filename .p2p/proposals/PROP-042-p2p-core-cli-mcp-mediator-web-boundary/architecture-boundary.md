# Architecture Boundary - PROP-042

## Layer Model

### Level 1 - P2P Core

Deterministic Python library.

Responsibilities:

- own domain models for proposals, choices, decisions, Change Sets, work, registries and project state;
- read and write `.p2p/` memory;
- validate state transitions and project invariants;
- remain provider-neutral and usable without AI, MCP, web infrastructure, or hosted services.

Non-responsibilities:

- direct AI invocation;
- web collaboration UI;
- conversational mediation;
- provider-specific authentication;
- autonomous governance decisions.

### Level 2 - P2P CLI

Terminal interface over P2P Core.

Responsibilities:

- expose deterministic operations to humans, agents, scripts and local automation;
- keep local/open-source usage complete without hosted infrastructure;
- provide the reference operational UX for proposal, choice, change, spec, work and registry flows.

Non-responsibilities:

- own business logic that belongs in Core;
- hide governance decisions behind implicit automation;
- require AI or web services.

### Level 3 - Skill / MCP / Agent Interfaces

Agent-facing access layer.

Responsibilities:

- let Codex, Claude, generic agents, IDEs and other tools use P2P safely;
- expose Core/CLI capabilities through stable tools or instructions;
- keep agent behavior advisory by default;
- make the source-of-truth operations explicit and auditable.

MCP boundary:

```text
MCP server = tool interface to P2P Core
MCP server != P2P Mediator
```

The MCP server should expose deterministic tools such as:

```text
proposal.create
proposal.show
choice.list
change.status
work.status
project.next
registry.show
```

### Level 4 - P2P Mediator

Optional intelligent assistant layer.

Responsibilities:

- help contributors formulate ideas, proposals, alternatives and risks;
- detect overlaps and suggest next actions;
- translate user/agent intent into safe P2P operations;
- use Core/CLI/MCP as source of truth.

Non-responsibilities:

- replace the Core;
- own `.p2p/` memory directly when a Core/CLI/MCP operation exists;
- decide governance outcomes by default.

### Level 5 - P2P Web

Product UI over the same source-of-truth operations.

Responsibilities:

- make contribution, review, discussion, governance and collaboration easier;
- support human and AI contributors through a product interface;
- consume Core/API/MCP operations rather than becoming a separate source of truth.

Non-responsibilities:

- fork the project model away from `.p2p/`;
- require hosted infrastructure for local/open-source usage.

## Governance Boundary

Default rule:

```text
AI suggests.
Owner decides.
P2P Core validates and records.
```

Owner-controlled by default:

- proposal accept/reject/defer;
- choice decide;
- governance policy changes;
- work accept/merge;
- remote branch deletion;
- irreversible publication or cleanup steps.

Potentially automatable only under future explicit policy:

- classify intake;
- add low-risk draft contributions;
- suggest relations;
- generate summaries;
- prepare review requests.

## Product Strategy

P2P Engine must remain useful as:

- an open local CLI tool;
- an agent-native project memory system;
- a future MCP-backed tool server;
- a future mediator-assisted workflow;
- a future collaborative web product.

The lower layers must not depend on the higher layers.

```text
Core <- CLI <- MCP/Skills <- Mediator <- Web
```

Higher layers may use lower layers. Lower layers must remain independently usable.
