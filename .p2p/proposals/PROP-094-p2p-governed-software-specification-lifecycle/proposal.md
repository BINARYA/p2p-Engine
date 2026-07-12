# PROP-094 - P2P-Governed Software Specification Lifecycle

## Status

`draft`

## Problem

In software projects, an owner may legitimately ask an agent to produce system specifications before the project is fully defined. If the agent responds by creating a standalone spec file immediately, that file can become the effective source of truth while the P2P project definition remains incomplete or bypassed.

This is a methodological failure, not a file-placement issue alone. The problem is not that specs are unnecessary or always premature. The problem is that the software vertical should guide the definition of the parts that make a useful specification, and those parts should be captured through P2P proposals, decisions, choices, readiness, and Change Sets before a durable spec file is treated as authoritative.

Without that lifecycle, the owner receives a useful-looking document, but future agents, readiness checks, Change Sets, exports, and project status may not be able to explain which governed decisions the spec reflects, which assumptions remain unresolved, or whether the file is only an exploratory draft.

## Context

A colleague test showed that an agent created its own specification file on user request. The need was legitimate because the project had a strong software-specification requirement, but the sequence was weak: P2P should guide the user through project definition first, then generate specs as governed or exported artifacts derived from P2P state.

P2P Engine already has relevant primitives: vertical/domain project definition, proposals, readiness, questions, choices, Change Sets, P2P-native software specs, and downstream spec exports. The missing piece is agent-facing guidance that explains when to use each layer and how to respond when the owner asks for specs before enough project state exists.

This proposal complements PROP-093. PROP-093 defines write consent, write classes, and P2P-first persistence. This proposal defines the software-specific handoff from project definition to specifications.

## Goals

- Treat the need for specs as a first-class part of the software vertical.
- Make specification content emerge from P2P-governed project definition, one or more proposals, decisions, and Change Sets.
- Teach generated agent instructions to route "make specs" requests through the software vertical and P2P state instead of creating an independent durable file by default.
- Clarify when a spec request should produce chat discussion, project-definition questions, proposal work, choices, a Change Set, a P2P-native spec, a generated export, or stable documentation.
- Allow early exploratory spec outlines, but prevent them from becoming primary project memory unless they are captured or exported through P2P.
- Keep user intent respected: if the owner explicitly requests a concrete file outside the P2P flow, the agent may create it after previewing the write and explaining its relationship to P2P state.
- Reuse existing P2P primitives instead of inventing a parallel specification workflow.

## Non-Goals

- Do not prohibit users from explicitly requesting a concrete spec file.
- Do not replace existing P2P proposal, Change Set, spec refresh, or export primitives.
- Do not implement external artifact registration unless explicitly accepted in a separate proposal.
- Do not require all non-software projects to follow a software-spec lifecycle.
- Do not require agents to complete every possible project-definition question before drafting any useful provisional outline.
- Do not make generated specs authoritative when they contain unresolved questions, inferred details, or unaccepted alternatives.

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

## Alternatives

- Rely on PROP-093 only. This covers write consent and artifact visibility but does not teach agents the software-specific sequence.
- Always create a spec file when asked. This is responsive, but it lets external files become primary project truth.
- Block all spec drafting until every project-definition topic is complete. This is too rigid and would make early software design awkward.
- Require specs to be generated only from accepted Change Sets. This is clean for implementation specs, but too late for exploratory and requirements-level specification work.
- Create a separate spec assistant outside P2P. This would fragment the method and duplicate primitives that already exist.
- Put all specification concerns into a single proposal. This is simple for small projects, but it does not scale when the spec depends on separate decisions about data, architecture, integrations, UX, governance, or delivery.

## Impacts

- Vertical model: the `software` domain should describe specification ingredients explicitly enough that agents can guide project definition toward a future spec.
- Agent templates: add a "when the owner asks for specs" routing table and require agents to distinguish exploratory outlines from P2P-native specs and generated exports.
- Project skills: explain the difference between project definition, proposals, Change Sets, P2P-native specs, generated exports, stable documentation, and scratch notes.
- CLI and services: the first implementation slice should reuse existing `proposal`, `readiness`, `choice`, `change`, `spec`, and `spec export` commands; new primitives are not required unless implementation discovers a concrete gap.
- Documentation: add a software-project flow from vertical definition to proposals, Change Sets, P2P-native specs, and downstream exports.
- Tests: verify generated instructions and docs include the lifecycle and do not encourage standalone untracked specs as primary memory.
- User workflow: agents should guide owners toward spec-ready project definition instead of asking generic questions or writing ungrounded standalone files.

## Risks

- The guidance may feel too formal if the user just wants a quick sketch.
- Agents may over-ask questions instead of producing a useful provisional outline.
- The boundary between stable documentation and generated export may remain ambiguous without examples.
- Existing docs may already mention specs in different terms and need harmonization.
- If implementation-oriented specs depend too heavily on accepted Change Sets, legitimate early requirements analysis may feel blocked.
- If specs can derive from multiple proposals, agents need clear synthesis guidance to avoid losing traceability.

## Assumptions

- P2P Engine remains generic, but the `software` vertical can provide domain-specific guidance for specs.
- Existing P2P-native spec and export primitives are the preferred downstream path for implementation-oriented software specs.
- Early exploratory spec outlines are allowed in chat or P2P exploration material, but they must not become stable project truth without P2P visibility.
- Readiness is advisory for early exploration and stricter for implementation-oriented specs and downstream exports.
- The owner may explicitly choose to work outside P2P; in that case, the agent should respect the request and state the governance tradeoff.

## Resolved Questions

- Lifecycle scope: enable this as software-domain guidance. General P2P persistence and write-consent rules remain covered by PROP-093.
- Readiness: use readiness as advisory for exploration, but require accepted direction, resolved blocking choices, and a relevant Change Set for implementation-oriented specs and downstream exports.
- Preliminary specs: keep them in chat or P2P exploration/proposal material until the owner requests a durable export or stable document.
- Operational guidance: include a command-oriented routing table in generated instructions and documentation.

## Acceptance Criteria

- WHEN a project is initialized or refreshed with the software domain, THE SYSTEM SHALL generate agent guidance that treats specs as a downstream capability of the software vertical, not as an immediate standalone file-writing shortcut.
- WHEN an owner asks an agent for specs in a software project, THE GENERATED GUIDANCE SHALL instruct the agent to classify the request as exploration, project definition, proposal/choice work, Change Set preparation, P2P-native spec generation, export, or explicit stable documentation.
- WHEN the software vertical is incomplete and the owner asks for specs, THE GENERATED GUIDANCE SHALL instruct the agent to identify missing spec ingredients and route them into P2P project-definition questions, proposal updates, new proposals, or choices before creating durable implementation spec files.
- WHEN spec content spans multiple concerns, THE GENERATED GUIDANCE SHALL allow and recommend multiple P2P proposals or choices rather than forcing all specification content into one monolithic document.
- WHEN the owner asks for exploratory or requirements-level spec thinking, THE GENERATED GUIDANCE SHALL allow chat or P2P exploration/proposal material without requiring full readiness, while requiring unresolved assumptions and decisions to be marked clearly.
- WHEN the owner asks for implementation-oriented specs or downstream exports, THE GENERATED GUIDANCE SHALL require a sufficiently accepted direction, resolved blocking choices, and a relevant Change Set before generating P2P-native specs or export bundles.
- WHEN the owner explicitly asks for a concrete external spec file, THE GENERATED GUIDANCE SHALL allow the write only with PROP-093 action preview and with a clear statement whether the file is stable documentation, generated export, temporary scratch, or outside P2P governance.
- Documentation SHALL explain the software-project flow from vertical definition to one or more proposals, choices, accepted direction, Change Set, P2P-native spec, and downstream export.
- Tests SHALL verify generated guidance and documentation for spec requests, including the routing table, multi-proposal source model, readiness split, and the rule that standalone spec files are not primary untracked project memory.
- The first implementation slice SHALL reuse existing proposal, readiness, choice, change, spec, and spec export primitives unless a later accepted proposal adds external artifact registration or new spec lifecycle commands.

## Decision

Pending.
