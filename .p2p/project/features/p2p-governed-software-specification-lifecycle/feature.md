# P2P-Governed Software Specification Lifecycle

## Provenance

- Proposal: PROP-094
- Source: .p2p/proposals/PROP-094-p2p-governed-software-specification-lifecycle

## Problem

In software projects, an owner may legitimately ask an agent to produce system specifications before the project is fully defined. If the agent responds by creating a standalone spec file immediately, that file can become the effective source of truth while the P2P project definition remains incomplete or bypassed.

This is a methodological failure, not a file-placement issue alone. The problem is not that specs are unnecessary or always premature. The problem is that the software vertical should guide the definition of the parts that make a useful specification, and those parts should be captured through P2P proposals, decisions, choices, readiness, and Change Sets before a durable spec file is treated as authoritative.

Without that lifecycle, the owner receives a useful-looking document, but future agents, readiness checks, Change Sets, exports, and project status may not be able to explain which governed decisions the spec reflects, which assumptions remain unresolved, or whether the file is only an exploratory draft.

## Proposal

Define a software-specific specification lifecycle policy and supporting guidance.

### Core rule

In software projects, a request for "specs" should normally activate the software vertical and P2P proposal flow. The final spec file is a downstream artifact. It is not the primary project definition and should not be created as independent durable memory by default.

The software vertical should make specification readiness visible by tracking the parts that a useful spec needs, including:

- product or system objective;
- intended users and actors;
- scope and MVP boundaries;
- core use cases and workflows;
- domain concepts and data model;
- integrations and external dependencies;
- constraints, non-functional requirements, and operating assumptions;
- acceptance criteria and validation strategy;
- unresolved risks, alternatives, and owner decisions.

These parts may be defined through one proposal or through multiple proposals. For example, one proposal may define the MVP boundary, another may define the data model, another may settle an integration strategy, and another may define agent/MCP behavior. A software spec should be able to derive from that set of accepted or explicitly provisional P2P artifacts.

### Lifecycle

When the owner asks for specs, the agent should classify the request and route it:

| Owner request | Agent routing | Persistent artifact |
| --- | --- | --- |
| "Let's think through the specs" | Discuss in chat and identify missing vertical fields | None, unless owner asks to persist |
| "Help me define the system" | Capture project-definition gaps and create/update proposals | P2P proposal/exploration/question artifacts |
| "Compare possible architectures" | Create alternatives, choices, or competing proposals | P2P proposal/choice artifacts |
| "Prepare implementation specs" | Identify accepted direction and create/update a Change Set | Change Set, then P2P-native spec |
| "Export specs for a tool" | Generate/export from P2P-native spec | Generated export |
| "Create this exact file" | Preview write and explain governance status | Stable documentation or explicit external file |

For exploratory or requirements-level work, readiness is advisory. The agent may draft a provisional outline in chat or P2P exploration material while clearly marking unresolved decisions.

For implementation-oriented specs or downstream exports, readiness should be stricter: there should be a sufficiently accepted direction, resolved blocking choices, and a relevant Change Set before generating a P2P-native spec or export bundle. If that state is missing, the agent should guide the owner to define or accept the missing proposals first.

### Agent behavior

Generated agent instructions should include a concrete routing rule:

- If the owner asks for "specs" but the software vertical is incomplete, use the vertical to identify missing spec ingredients and ask focused questions or create/update P2P proposals.
- If the required spec content spans multiple concerns, split it into multiple proposals or choices instead of forcing everything into one monolithic file.
- If the owner asks for implementation specs, identify the accepted proposal set and relevant Change Set before generating a P2P-native software spec.
- If the owner asks for a file export, explain whether the file is a generated export, stable documentation, or temporary scratch.
- If the owner explicitly asks to operate outside P2P, respect that boundary while making clear that the resulting file will not be P2P-governed unless later registered or imported.

Persistent writes must follow PROP-093: preview the operation, target, artifact kind, write class, and reason unless the owner explicitly requested the exact artifact.

## Decision

# Decision - PROP-094

## Status

`accepted`

## Outcome

accepted

## Reason

Owner accepted after review; readiness is decision_ready with no missing gates or blocking questions.

## Date

2026-07-12

## Approver

owner
