# P2P Engine Project Definition

This document is synthesized from accepted P2P memory. It is the canonical generic project export. Draft or undecided material is listed only as pending or missing information.

## Executive Summary

Add p2p spec refresh/status/show/prompt/import. The refresh command deterministically generates a minimal software spec from a Change Set. The prompt command generates an AI/human refinement prompt from the deterministic spec and source context. The import command validates and imports refined spec artifacts.

## Vision

Organize confused, distributed, and discontinuous project intent into a governed project definition that agents can use without rediscovering context from scratch.

## Domain

software

## Problem

- **PROP-001 CLI Foundation**: P2P Engine does not exist yet as an executable tool. The project has a solid foundation document, but no CLI, no generated `.p2p/` structure, no automated proposal workflow, and no prompt generation.

Without a first working CLI, every proposal must be created manually. That is acceptable for the bootstrap phase, but it must become automated quickly so the project can start using its own method.
- **PROP-004 Prompt-only Import Workflow**: P2P Engine genera prompt per varie fasi, ma non importa ancora in modo uniforme gli output prodotti da AI o agenti esterni.
- **PROP-005 Codex Skill Integration**: Codex oggi non ha istruzioni formali per usare P2P Engine come metodo operativo e rischia di lasciare decisioni e interlocuzioni solo nella chat.
- **PROP-009 Governance CLI Commands**: P2P Engine ha un modello di governance file-based, ma non ha ancora comandi CLI per inizializzare governance, generare SWOT, registrare voti, mostrare risultati e registrare precedenti decisionali.
- **PROP-010 P2P Project State Model**: Accepted P2P proposals are not yet transformed into a single rationalized project state that can guide implementation, feature tracking, task planning, or downstream export.
- **PROP-011 Project Refresh MVP**: P2P Engine has accepted the .p2p/project state model, but the CLI cannot yet generate or inspect that rationalized project layer.
- **PROP-012 Impact Map and Conflict Memory**: P2P Engine can generate a rationalized project state, but it does not yet capture what a proposal touches or whether it overlaps, depends on, supersedes, or conflicts with other proposals.
- **PROP-013 Managed Git Adapter and Change Set Model**: P2P Engine distinguishes proposals from project state, but it does not yet define how accepted decisions become operational change sets or how Git operations should be managed under the hood without exposing branch/commit/merge complexity to users.

## Goals

- **PROP-001 CLI Foundation**: - Implement a minimal `p2p` CLI.
- Generate the `.p2p/` project structure with `p2p init`.
- Create proposal folders and baseline artifacts with `p2p proposal create`.
- Add structured contributions with `p2p contribution add`.
- Record decisions with `p2p decision record`.
- Generate prompt files for digest, clarify, plan, and tasks.
- Keep AI invocation optional and out of scope for the first implementation.
- Preserve compatibility with future OpenSpec and Spec Kit exports.
- **PROP-004 Prompt-only Import Workflow**: - Aggiungere import per clarify, synthesize, plan e tasks.
- Rendere il workflow prompt-only end-to-end testabile.
- **PROP-005 Codex Skill Integration**: - Creare una skill Codex che guidi l'uso della CLI P2P e degli artefatti .p2p.
- Stabilire regole per trasformare conversazioni in proposal, exploration, decisioni, piani e task versionati.
- **PROP-009 Governance CLI Commands**: - Implementare p2p governance init/status.
- Implementare p2p swot prompt per alternative contrapposte.
- Implementare p2p vote record/status.
- Implementare p2p precedent record.
- **PROP-010 P2P Project State Model**: - Define a P2P-native project state generated from accepted proposals.
- Create a dedicated `.p2p/project/` area for rationalized project artifacts.
- Specify how accepted proposals update project state.
- Keep OpenSpec and Spec Kit as downstream exporters, not the source of truth.
- **PROP-011 Project Refresh MVP**: - Implement p2p project refresh to generate the first .p2p/project artifacts.
- Implement p2p project status to inspect generated project state.
- Implement p2p project show to read generated project sections.
- **PROP-012 Impact Map and Conflict Memory**: - Define proposal-level impact-map artifacts.
- Define conflict memory in .p2p/project/conflicts.yml.
- Add prompt-only analysis for impact, overlap, dependencies, and conflicts.
- Add CLI commands to record and inspect conflicts.
- **PROP-013 Managed Git Adapter and Change Set Model**: - Define Change Set as the operational unit after proposal decision.
- Define Git as an internal adapter for persistence, audit, collaboration, and synchronization.
- Hide branch, commit, merge, and tag details from the default user experience.
- Reduce discretion in branch decisions through configurable Git policy.
- Preserve proposal and decision history in .p2p artifacts even when Git branches are removed.

## Non-Goals / Exclusions

- **PROP-001 CLI Foundation**: - No web app.
- No users, accounts, permissions, billing, or dashboard.
- No managed AI provider.
- No MCP server.
- No full OpenSpec or Spec Kit exporter in the first slice.
- No automatic code implementation.
- No advanced governance engine.
- **PROP-004 Prompt-only Import Workflow**: - Non invocare provider AI direttamente.
- Non introdurre MCP.
- Non aggiungere web app o database.
- **PROP-005 Codex Skill Integration**: - Non introdurre MCP in questa fase.
- Non invocare direttamente provider AI dalla CLI.
- Non sostituire la CLI come sorgente di verita.
- **PROP-009 Governance CLI Commands**: - Implementare enforcement reale dei permessi applicativi.
- Integrare branch protection, CODEOWNERS o required approvals.
- Chiudere automaticamente votazioni o decisioni complesse.
- **PROP-010 P2P Project State Model**: - Implement a full OpenSpec or Spec Kit exporter in this proposal.
- Replace proposal, decision, plan, or task artifacts.
- **PROP-011 Project Refresh MVP**: - Implement OpenSpec or Spec Kit export.
- Implement automatic refresh after decision record.
- **PROP-012 Impact Map and Conflict Memory**: - Automatically reject proposals without human decision.
- Implement full AI agent invocation.
- **PROP-013 Managed Git Adapter and Change Set Model**: - Implement full Git branch automation in this proposal.
- Require users to understand or manually manage Git branches.
- Let AI agents bypass P2P CLI by manipulating Git directly.

## Stakeholders / Users

- Humans supervise outputs and make governance decisions.
- AI agents use P2P memory and exports as structured project cognition.
- Downstream tools receive initialization prompts or documents, not synthetic ownership of P2P state.

## Workflows

- Capture rough ideas as intake, proposals, or contributions.
- Decide accepted direction through owner-controlled P2P governance.
- Derive Change Sets and exports from accepted memory.
- Use target-specific outputs to initialize downstream agent workflows.

## Accepted Decisions

- **PROP-001 CLI Foundation**: # Decision — PROP-001 CLI Foundation

## Status

`accepted`

## Outcome

Build the first P2P Engine CLI as a local, Git-native, prompt-only Python application.

## Reason

The project needs a minimal executable workflow before adding AI adapters, exporters, MCP, or a web interface. Automating the manually bootstrapped `.p2p/` structure is the shortest path to dogfooding.

## Conditions

- Keep the MVP file-based.
- Do not add direct AI provider integration yet.
- Do not add a web app yet.
- Prefer explicit, inspectable artifacts over hidden state.
- Make generated files easy to edit manually.

## Date

2026-05-19

## Approver

bootstrap maintainer
- **PROP-004 Prompt-only Import Workflow**: # Decision - PROP-004

## Status

`accepted`

## Outcome

accepted

## Reason

Il workflow prompt-only deve essere completo: ogni fase che genera prompt deve poter importare l'output prodotto da AI, agenti esterni o dall'utente.

## Date

2026-05-19

## Approver

bootstrap maintainer
- **PROP-005 Codex Skill Integration**: # Decision - PROP-005

## Status

`accepted`

## Outcome

accepted

## Reason

P2P Engine now has enough CLI workflow surface for Codex to use it as a structured method. A local skill makes the expected behavior explicit and reduces the risk of leaving decisions only in chat.

## Date

2026-05-19

## Approver

bootstrap maintainer
- **PROP-009 Governance CLI Commands**: # Decision - PROP-009

## Status

`accepted`

## Outcome

accepted

## Reason

PROP-008 ha definito il modello di governance, ma senza comandi CLI il workflow resta solo documentale. I comandi governance, swot, vote e precedent rendono il modello provabile nel repository senza introdurre ancora un sistema di privilegi applicativi.

## Scope

- Inizializzare governance.yml, roles.yml e decision-precedents.yml.
- Generare prompt SWOT per alternative contrapposte.
- Registrare voti in votes.yml e mostrare conteggi.
- Registrare precedenti decisionali riutilizzabili.

## Constraints

- La governance MVP e audit-only.
- La decisione resta umana o governance-defined.
- Git resta il layer di audit e permessi reali fino a una fase successiva.
- **PROP-010 P2P Project State Model**: # Decision - PROP-010

## Status

`accepted`

## Outcome

accepted

## Reason

P2P Engine needs an internal rationalized project state before exporting to OpenSpec, Spec Kit, or task systems. Raw proposal folders contain discussion, governance, alternatives, and decision history; they should not be treated directly as implementation specifications.

## Decision

Create a versioned `.p2p/project/` layer.

The official `.p2p/project/` state lives on `main`. Proposal branches may contain preview changes. When a proposal is accepted and merged, the corresponding project-state changes become official.

## Initial Model

```text
.p2p/project/
  overview.md
  problem.md
  scope.md
  project-swot.md
  features/
    <feature-id>/
      feature.md
      tasks.yml
      actions.yml
  decisions-map.yml
  conflicts.yml
  exports/
    markdown/
    openspec/
    speckit/
```

## Refresh Policy

The MVP uses explicit refresh:

```bash
p2p project refresh
```

Automatic refresh after accepted decisions can be added later as an opt-in behavior.
- **PROP-011 Project Refresh MVP**: # Decision - PROP-011

## Status

`accepted`

## Outcome

accepted

## Reason

Project refresh MVP is implemented with deterministic .p2p/project generation and CLI inspection commands.

## Date

2026-05-19

## Approver

local
- **PROP-012 Impact Map and Conflict Memory**: # Decision - PROP-012

## Status

`accepted`

## Outcome

accepted

## Reason

Impact analysis and conflict memory are implemented as prompt-only impact artifacts plus persistent .p2p/project/conflicts.yml commands.

## Date

2026-05-20

## Approver

local
- **PROP-013 Managed Git Adapter and Change Set Model**: # Decision - PROP-013

## Status

`accepted`

## Outcome

accepted

## Decision

Adopt Alternative D - Managed Git Under The Hood.

## Reason

P2P Engine should expose proposal, choice, decision, change, and task concepts to users. Git remains the internal layer for persistence, audit, synchronization, and collaboration, but users should not need to reason about branches, commits, merges, or tags during normal workflows.

## MVP Policy

```yaml
git_policy:
  mode: managed
  operation_level: metadata_only
  expose_git_details: false
  commits:
    auto_commit: false
  branches:
    auto_create: false
  tags:
    auto_create: false
```

## Change Set Policy

- Change Sets can be created only from accepted proposals or accepted decisions.
- Draft proposals can be referenced as non-binding context.
- Change Sets are multi-domain.
- `.p2p/project/features/` is a derived project view.
- Future internal branches require `implementation_ready`, accepted source, plan, tasks, doctor OK, safe worktree or snapshot, recovery strategy, and explicit command or enabled policy.
- **PROP-014 Change Set Metadata MVP**: # Decision - PROP-014

## Status

`accepted`

## Outcome

accepted

## Reason

Change Set metadata MVP is implemented with create/status/policy commands and metadata-only managed Git policy.

## Date

2026-05-20

## Approver

local
- **PROP-015 Change Set Lifecycle and Task Tracking**: # Decision - PROP-015

## Status

`accepted`

## Outcome

accepted

## Reason

Change Set lifecycle transitions and task/action inspection are implemented with validated status changes and metadata-only behavior.

## Date

2026-05-20

## Approver

local
- **PROP-016 Project Registries MVP**: # Decision - PROP-016

## Status

`accepted`

## Outcome

accepted

## Reason

Accepted as the next MVP step to introduce generated project registries for proposals, decisions, changes, choices, relations and artifacts.

## Date

2026-05-20

## Approver

local
- **PROP-017 Proposal Intake and Context Analysis MVP**: # Decision - PROP-017

## Status

`accepted`

## Outcome

accepted

## Reason

Accepted to add registry-backed proposal intake and context analysis as the next usability layer for multi-user and multi-agent P2P workflows.

## Date

2026-05-20

## Approver

local

## Requirements

## Functional Requirements

### R001 - Deterministic Spec Generation

The CLI must provide `p2p spec refresh --change CHANGE-XXX` to generate a P2P-native software spec for the selected Change Set.

The command must:

- read the Change Set metadata and source references;
- include accepted proposal context from the Change Set source;
- include implementation, spec, and export targets when available;
- write the required spec artifacts under `.p2p/outputs/software-spec/CHANGE-XXX/`;
- preserve provenance to the source Change Set, proposals, decisions, and source files;
- avoid inventing requirements not supported by accepted P2P artifacts.

### R002 - Spec Status

The CLI must provide `p2p spec status` to list generated software specs and their current availability.

The command must show at least:

- Change Set id;
- spec generation/import state;
- Change Set title when available.

### R003 - Spec Show

The CLI must provide `p2p spec show CHANGE-XXX` to inspect the generated or imported spec for a Change Set.

The command must print the human-facing `index.md` artifact for the selected Change Set.

### R004 - Refinement Prompt

The CLI must provide `p2p spec prompt --change CHANGE-XXX` to generate a refinement prompt from the deterministic spec and source context.

The prompt must:

- explain the governance boundary;
- list the exact required output artifacts;
- include enough deterministic spec context to support refinement;
- instruct the refiner to mark missing information as open questions instead of inventing unsupported requirements.

### R005 - Refined Spec Import

The CLI must provide `p2p spec import CHANGE-XXX spec-output/` to import a refined spec directory.

The command must:

- verify that all required artifact files are present;
- parse YAML artifacts before import;
- validate required YAML top-level keys;
- fail without replacing the official spec when validation fails;
- copy the validated refined artifacts into `.p2p/outputs/software-spec/CHANGE-XXX/`.

### R006 - Skill And Test Coverage

The P2P skill must document the spec refresh, prompt, and import workflow. Tests must cover deterministic generation, prompt creation, status/show, and import validation.

## Non-Goals / Exclusions

- Do not implement OpenSpec export in this MVP.
- Do not implement Spec Kit export in this MVP.
- Do not invoke AI directly from the CLI.
- Do not create automatic Git commits, branches, tags, or merges.
- Do not treat raw proposal discussion as implementation requirements without accepted scope.

## Constraints

- The Change Set is the operational unit for spec generation.
- Generated specs must remain deterministic from P2P artifacts.
- Refined imports may improve structure and clarity, but must not expand scope beyond accepted sources.
- Import validation is structural; it does not decide project governance or approve new requirements.

## Open Questions

- Should future exporter-specific fields live in the P2P-native spec or only in OpenSpec/Spec Kit exporter layers?
- Should imported specs preserve a separate imported timestamp or author metadata beyond the existing provenance file?
- Should `p2p spec show` eventually support selecting individual artifacts instead of always showing `index.md`?

## Constraints

- Exports must not invent requirements unsupported by accepted P2P artifacts.
- Missing information must be marked as NEEDS CLARIFICATION.
- Draft proposals must not be treated as accepted project truth.

## Assumptions

- Accepted P2P proposals and decisions are authoritative project memory.
- Target-specific exports are initialization artifacts for agents or downstream tools.

## Dependencies

- Source Change Set: `CHANGE-012` P2P Software Spec Generator MVP
- P2P software spec artifacts generated before export.
- Downstream tools, if used, run outside P2P export.

## Operating Model / Architecture

## Implementation Targets

- `local_cli`

## Data Flow

### Refresh Flow

1. The user runs `p2p spec refresh --change CHANGE-XXX`.
2. The CLI resolves the Change Set from `.p2p/changes/`.
3. The CLI reads Change Set metadata, task metadata, accepted proposal references, accepted decisions when present, and source files.
4. The CLI renders the deterministic P2P-native spec artifacts.
5. The CLI writes the artifacts to `.p2p/outputs/software-spec/CHANGE-XXX/`.
6. `provenance.yml` records the source Change Set, included proposals, accepted decisions, and generated-from file paths.

### Prompt Flow

1. The user runs `p2p spec prompt --change CHANGE-XXX`.
2. The CLI reads the current deterministic or imported spec artifacts.
3. The CLI writes `spec-refine.prompt.md` beside the spec artifacts.
4. The prompt asks a human or AI refiner to return the required artifact set without expanding project scope.

### Import Flow

1. The user creates or receives a refined spec directory.
2. The user runs `p2p spec import CHANGE-XXX spec-output/`.
3. The CLI checks that every required artifact exists.
4. The CLI parses YAML artifacts and checks required top-level keys.
5. If validation passes, the CLI imports the refined artifacts into the official Change Set spec directory.
6. If validation fails, the CLI reports the issue and does not replace the official artifacts.

### Inspection Flow

1. `p2p spec status` scans `.p2p/outputs/software-spec/`.
2. `p2p spec show CHANGE-XXX` prints the selected Change Set's `index.md`.

## CLI/API Surface

The MVP exposes a top-level `p2p spec` command group.

### `p2p spec refresh --change CHANGE-XXX`

Generates or regenerates deterministic spec artifacts for a Change Set.

Expected behavior:

- requires an existing Change Set id;
- creates the target output directory when needed;
- overwrites generated artifacts for the selected Change Set;
- preserves deterministic output based on current P2P source artifacts.

### `p2p spec status`

Lists available software spec outputs.

Expected behavior:

- scans generated spec directories;
- reports the Change Set id and title when known;
- remains read-only.

### `p2p spec show CHANGE-XXX`

Shows the main human-readable spec entry point.

Expected behavior:

- requires an existing spec directory;
- prints `index.md`;
- remains read-only.

### `p2p spec prompt --change CHANGE-XXX`

Generates a refinement prompt for the selected spec.

Expected behavior:

- requires an existing generated or imported spec;
- writes `spec-refine.prompt.md`;
- includes governance boundary and required output shape.

### `p2p spec import CHANGE-XXX spec-output/`

Validates and imports a refined spec directory.

Expected behavior:

- requires the exact required artifact set;
- validates YAML syntax and required top-level keys;
- imports only after validation succeeds;
- does not make governance decisions.

## Storage / Artifacts

Official spec artifacts are stored under:

```text
.p2p/outputs/software-spec/CHANGE-XXX/
```

Required files:

- `index.md`: summary, sources, targets, artifact contract, boundary
- `requirements.md`: functional requirements, non-goals, constraints, open questions
- `design.md`: data flow, CLI surface, storage model
- `commands.yml`: structured CLI command contract
- `data-model.yml`: structured entities used by the spec workflow
- `acceptance.md`: acceptance criteria and verification scenarios
- `provenance.yml`: source and generated-from references

Optional generated helper:

- `spec-refine.prompt.md`: prompt used to refine the deterministic spec

## Validation Strategy

The import command validates structure before mutation:

- required files must exist;
- YAML files must parse successfully;
- `commands.yml` must contain `commands`;
- `data-model.yml` must contain `entities`;
- `provenance.yml` must contain `source`.

Semantic governance remains outside import validation. New requirements or decisions must still be represented through normal P2P proposal, choice, decision, and Change Set flows.

## Data / Knowledge Model

```yaml
entities:
  - name: ChangeSet
    kind: source
    description: Operational package derived from accepted P2P project intent and used as the source unit for spec generation.
    key_fields:
      - change_id
      - title
      - status
      - execution_domains
      - implementation_targets
      - spec_targets
      - export_targets
      - source

  - name: Proposal
    kind: source
    description: Accepted project proposal included by the Change Set source metadata.
    key_fields:
      - proposal_id
      - status
      - problem
      - goals
      - proposal
      - acceptance_criteria

  - name: SoftwareSpec
    kind: output
    description: P2P-native normalized implementation-facing specification generated or imported for a Change Set.
    key_fields:
      - change_id
      - artifacts
      - provenance
      - targets

  - name: SpecArtifact
    kind: output
    description: One required file in the P2P-native software spec directory.
    key_fields:
      - path
      - format
      - required
      - validation_rules

  - name: RefinementPrompt
    kind: helper_output
    description: Prompt artifact used by a human or AI assistant to refine the deterministic spec without expanding accepted scope.
    key_fields:
      - change_id
      - governance_boundary
      - required_output
      - deterministic_context

  - name: ImportedSpec
    kind: input
    description: External refined spec directory submitted to `p2p spec import` for validation and import.
    key_fields:
      - source_directory
      - required_files
      - yaml_artifacts
      - validation_result

  - name: SpecValidator
    kind: process
    description: Structural validation performed before importing refined spec artifacts.
    key_fields:
      - required_files
      - yaml_parse_result
      - required_top_level_keys

  - name: Provenance
    kind: output
    description: Trace from generated or imported spec artifacts back to P2P source artifacts.
    key_fields:
      - source.change
      - source.included_proposals
      - source.accepted_decisions
      - generated_from

  - name: ExportTarget
    kind: future_target
    description: Downstream target declared by the Change Set but not implemented by this MVP.
    allowed_values:
      - openspec
      - speckit

```

## Priorities

- Preserve accepted project intent and governance first.
- Produce small agent-consumable outputs instead of downstream-shaped folders.
- Keep target-specific exports derived from this project definition.

## Success Criteria

## Criteria

- `p2p spec refresh --change CHANGE-XXX` generates `index.md`, `requirements.md`, `design.md`, `commands.yml`, `data-model.yml`, `acceptance.md`, and `provenance.yml` under `.p2p/outputs/software-spec/CHANGE-XXX/`.
- Generated specs preserve provenance to the Change Set, included proposals, accepted decisions when present, and source files.
- `p2p spec status` lists available generated or imported specs.
- `p2p spec show CHANGE-XXX` prints the selected spec `index.md`.
- `p2p spec prompt --change CHANGE-XXX` writes `spec-refine.prompt.md` using current spec context and the governance boundary.
- `p2p spec import CHANGE-XXX spec-output/` validates the required artifact set before importing.
- Import validation rejects missing required files.
- Import validation rejects YAML artifacts that fail to parse.
- Import validation rejects YAML artifacts missing required top-level keys.
- Tests cover deterministic generation, status/show, prompt creation, and import validation.

## Verification Scenarios

### T001 - Generate deterministic software spec

Run:

```bash
p2p spec refresh --change CHANGE-XXX
```

Expected result:

- required artifacts are created under `.p2p/outputs/software-spec/CHANGE-XXX/`;
- `provenance.yml` references the source Change Set and included proposals.

### T002 - Inspect generated software specs

Run:

```bash
p2p spec status
p2p spec show CHANGE-XXX
```

Expected result:

- status lists the generated spec;
- show prints the selected `index.md`.

### T003 - Generate refinement prompt

Run:

```bash
p2p spec prompt --change CHANGE-XXX
```

Expected result:

- `spec-refine.prompt.md` is written beside the spec artifacts;
- the prompt lists required output files and warns against unsupported requirements.

### T004 - Import refined software spec

Run:

```bash
p2p spec import CHANGE-XXX spec-output/
```

Expected result:

- valid refined artifacts are imported into the official spec directory;
- invalid refined artifacts fail before replacing official files.

### T005 - Update skill and tests

Expected result:

- the P2P skill documents refresh, prompt, and import usage;
- automated tests verify the implemented command behavior.

## Completion State

The Change Set tasks are marked completed. This refined spec clarifies the software contract and keeps future exporter implementation outside the MVP boundary.

## Validation / Evaluation Method

- Validate required export files exist.
- Validate required project definition sections exist.
- Validate source traceability is present.

## Risks And Tradeoffs

- Removing folder-shaped exports may surprise users of the previous MVP export layout.
- Agent-first documents require clear traceability to avoid over-synthesis.

## Open Questions

- Which legacy bundle outputs, if any, should remain available behind an explicit compatibility flag?

## Pending Proposals

- `PROP-002` Exploration Phase
- `PROP-006` Multi-Agent Integration Model
- `PROP-007` Proposal Intake and Overlap Analysis
- `PROP-008` Governance Model
- `PROP-059` P2PWorkspace Modular Refactoring Plan
- `PROP-060` Real Test Coverage Reporting
- `PROP-063` Public Documentation Gap Closure

## Software Domain Extension

### Technical Architecture

## Implementation Targets

- `local_cli`

## Data Flow

### Refresh Flow

1. The user runs `p2p spec refresh --change CHANGE-XXX`.
2. The CLI resolves the Change Set from `.p2p/changes/`.
3. The CLI reads Change Set metadata, task metadata, accepted proposal references, accepted decisions when present, and source files.
4. The CLI renders the deterministic P2P-native spec artifacts.
5. The CLI writes the artifacts to `.p2p/outputs/software-spec/CHANGE-XXX/`.
6. `provenance.yml` records the source Change Set, included proposals, accepted decisions, and generated-from file paths.

### Prompt Flow

1. The user runs `p2p spec prompt --change CHANGE-XXX`.
2. The CLI reads the current deterministic or imported spec artifacts.
3. The CLI writes `spec-refine.prompt.md` beside the spec artifacts.
4. The prompt asks a human or AI refiner to return the required artifact set without expanding project scope.

### Import Flow

1. The user creates or receives a refined spec directory.
2. The user runs `p2p spec import CHANGE-XXX spec-output/`.
3. The CLI checks that every required artifact exists.
4. The CLI parses YAML artifacts and checks required top-level keys.
5. If validation passes, the CLI imports the refined artifacts into the official Change Set spec directory.
6. If validation fails, the CLI reports the issue and does not replace the official artifacts.

### Inspection Flow

1. `p2p spec status` scans `.p2p/outputs/software-spec/`.
2. `p2p spec show CHANGE-XXX` prints the selected Change Set's `index.md`.

## CLI/API Surface

The MVP exposes a top-level `p2p spec` command group.

### `p2p spec refresh --change CHANGE-XXX`

Generates or regenerates deterministic spec artifacts for a Change Set.

Expected behavior:

- requires an existing Change Set id;
- creates the target output directory when needed;
- overwrites generated artifacts for the selected Change Set;
- preserves deterministic output based on current P2P source artifacts.

### `p2p spec status`

Lists available software spec outputs.

Expected behavior:

- scans generated spec directories;
- reports the Change Set id and title when known;
- remains read-only.

### `p2p spec show CHANGE-XXX`

Shows the main human-readable spec entry point.

Expected behavior:

- requires an existing spec directory;
- prints `index.md`;
- remains read-only.

### `p2p spec prompt --change CHANGE-XXX`

Generates a refinement prompt for the selected spec.

Expected behavior:

- requires an existing generated or imported spec;
- writes `spec-refine.prompt.md`;
- includes governance boundary and required output shape.

### `p2p spec import CHANGE-XXX spec-output/`

Validates and imports a refined spec directory.

Expected behavior:

- requires the exact required artifact set;
- validates YAML syntax and required top-level keys;
- imports only after validation succeeds;
- does not make governance decisions.

## Storage / Artifacts

Official spec artifacts are stored under:

```text
.p2p/outputs/software-spec/CHANGE-XXX/
```

Required files:

- `index.md`: summary, sources, targets, artifact contract, boundary
- `requirements.md`: functional requirements, non-goals, constraints, open questions
- `design.md`: data flow, CLI surface, storage model
- `commands.yml`: structured CLI command contract
- `data-model.yml`: structured entities used by the spec workflow
- `acceptance.md`: acceptance criteria and verification scenarios
- `provenance.yml`: source and generated-from references

Optional generated helper:

- `spec-refine.prompt.md`: prompt used to refine the deterministic spec

## Validation Strategy

The import command validates structure before mutation:

- required files must exist;
- YAML files must parse successfully;
- `commands.yml` must contain `commands`;
- `data-model.yml` must contain `entities`;
- `provenance.yml` must contain `source`.

Semantic governance remains outside import validation. New requirements or decisions must still be represented through normal P2P proposal, choice, decision, and Change Set flows.

### CLI/API/UI Surface

```yaml
commands:
  - name: p2p spec refresh
    status: completed
    purpose: Generate deterministic P2P-native software spec artifacts from a Change Set.
    invocation: "p2p spec refresh --change CHANGE-XXX"
    inputs:
      - name: change
        required: true
        description: Existing Change Set id to use as the source of truth.
    outputs:
      - ".p2p/outputs/software-spec/CHANGE-XXX/index.md"
      - ".p2p/outputs/software-spec/CHANGE-XXX/requirements.md"
      - ".p2p/outputs/software-spec/CHANGE-XXX/design.md"
      - ".p2p/outputs/software-spec/CHANGE-XXX/commands.yml"
      - ".p2p/outputs/software-spec/CHANGE-XXX/data-model.yml"
      - ".p2p/outputs/software-spec/CHANGE-XXX/acceptance.md"
      - ".p2p/outputs/software-spec/CHANGE-XXX/provenance.yml"
    validation:
      - Change Set exists.
      - Source proposal and decision references are read from P2P artifacts when available.
    errors:
      - Unknown Change Set id.
      - Missing source artifact required for generation.

  - name: p2p spec status
    status: completed
    purpose: List generated or imported P2P-native software specs.
    invocation: "p2p spec status"
    inputs: []
    outputs:
      - Human-readable list of software spec directories keyed by Change Set id.
    validation:
      - Output directory scan is read-only.
    errors: []

  - name: p2p spec show
    status: completed
    purpose: Print the main human-readable spec entry point for a Change Set.
    invocation: "p2p spec show CHANGE-XXX"
    inputs:
      - name: change
        required: true
        description: "Change Set id whose index.md should be printed."
    outputs:
      - "Contents of .p2p/outputs/software-spec/CHANGE-XXX/index.md."
    validation:
      - Spec directory exists.
      - "index.md exists."
    errors:
      - Unknown or missing spec for the requested Change Set.

  - name: p2p spec prompt
    status: completed
    purpose: Generate a refinement prompt from the current deterministic or imported spec.
    invocation: "p2p spec prompt --change CHANGE-XXX"
    inputs:
      - name: change
        required: true
        description: Change Set id whose spec should be refined.
    outputs:
      - ".p2p/outputs/software-spec/CHANGE-XXX/spec-refine.prompt.md"
    validation:
      - Existing spec artifacts are available for context.
    errors:
      - Missing spec artifacts for the requested Change Set.

  - name: p2p spec import
    status: completed
    purpose: Validate and import a refined software spec directory.
    invocation: "p2p spec import CHANGE-XXX spec-output/"
    inputs:
      - name: change
        required: true
        description: Change Set id that will receive the refined artifacts.
      - name: spec_output
        required: true
        description: Directory containing the refined required artifact set.
    outputs:
      - "Updated .p2p/outputs/software-spec/CHANGE-XXX/ artifact files after validation succeeds."
    validation:
      - Required Markdown and YAML files are present.
      - YAML files parse successfully.
      - "commands.yml contains top-level commands."
      - "data-model.yml contains top-level entities."
      - "provenance.yml contains top-level source."
    errors:
      - Missing required artifact.
      - Invalid YAML.
      - Missing required YAML top-level key.

```

### Testing Strategy

## Criteria

- `p2p spec refresh --change CHANGE-XXX` generates `index.md`, `requirements.md`, `design.md`, `commands.yml`, `data-model.yml`, `acceptance.md`, and `provenance.yml` under `.p2p/outputs/software-spec/CHANGE-XXX/`.
- Generated specs preserve provenance to the Change Set, included proposals, accepted decisions when present, and source files.
- `p2p spec status` lists available generated or imported specs.
- `p2p spec show CHANGE-XXX` prints the selected spec `index.md`.
- `p2p spec prompt --change CHANGE-XXX` writes `spec-refine.prompt.md` using current spec context and the governance boundary.
- `p2p spec import CHANGE-XXX spec-output/` validates the required artifact set before importing.
- Import validation rejects missing required files.
- Import validation rejects YAML artifacts that fail to parse.
- Import validation rejects YAML artifacts missing required top-level keys.
- Tests cover deterministic generation, status/show, prompt creation, and import validation.

## Verification Scenarios

### T001 - Generate deterministic software spec

Run:

```bash
p2p spec refresh --change CHANGE-XXX
```

Expected result:

- required artifacts are created under `.p2p/outputs/software-spec/CHANGE-XXX/`;
- `provenance.yml` references the source Change Set and included proposals.

### T002 - Inspect generated software specs

Run:

```bash
p2p spec status
p2p spec show CHANGE-XXX
```

Expected result:

- status lists the generated spec;
- show prints the selected `index.md`.

### T003 - Generate refinement prompt

Run:

```bash
p2p spec prompt --change CHANGE-XXX
```

Expected result:

- `spec-refine.prompt.md` is written beside the spec artifacts;
- the prompt lists required output files and warns against unsupported requirements.

### T004 - Import refined software spec

Run:

```bash
p2p spec import CHANGE-XXX spec-output/
```

Expected result:

- valid refined artifacts are imported into the official spec directory;
- invalid refined artifacts fail before replacing official files.

### T005 - Update skill and tests

Expected result:

- the P2P skill documents refresh, prompt, and import usage;
- automated tests verify the implemented command behavior.

## Completion State

The Change Set tasks are marked completed. This refined spec clarifies the software contract and keeps future exporter implementation outside the MVP boundary.

### Deployment / Operations

NEEDS CLARIFICATION

### Integration Boundaries

- Implementation targets: local_cli
- Spec targets: p2p_spec
- Export targets: openspec, speckit


## Source Traceability

- Source Change Set: `CHANGE-012` P2P Software Spec Generator MVP
- `PROP-001` CLI Foundation — `.p2p/proposals/PROP-001-cli-foundation`
- `PROP-004` Prompt-only Import Workflow — `.p2p/proposals/PROP-004-prompt-only-import-workflow`
- `PROP-005` Codex Skill Integration — `.p2p/proposals/PROP-005-codex-skill-integration`
- `PROP-009` Governance CLI Commands — `.p2p/proposals/PROP-009-governance-cli-commands`
- `PROP-010` P2P Project State Model — `.p2p/proposals/PROP-010-p2p-software-specification-model`
- `PROP-011` Project Refresh MVP — `.p2p/proposals/PROP-011-project-refresh-mvp`
- `PROP-012` Impact Map and Conflict Memory — `.p2p/proposals/PROP-012-impact-map-and-conflict-memory`
- `PROP-013` Managed Git Adapter and Change Set Model — `.p2p/proposals/PROP-013-change-set-and-git-branch-model`
- `PROP-014` Change Set Metadata MVP — `.p2p/proposals/PROP-014-change-set-metadata-mvp`
- `PROP-015` Change Set Lifecycle and Task Tracking — `.p2p/proposals/PROP-015-change-set-lifecycle-and-task-tracking`
- `PROP-016` Project Registries MVP — `.p2p/proposals/PROP-016-project-registries-mvp`
- `PROP-017` Proposal Intake and Context Analysis MVP — `.p2p/proposals/PROP-017-proposal-intake-and-context-analysis-mvp`
- `PROP-018` Choice Management CLI MVP — `.p2p/proposals/PROP-018-choice-management-cli-mvp`
- `PROP-019` Proposal Decision Shortcut Commands — `.p2p/proposals/PROP-019-proposal-decision-shortcut-commands`
- `PROP-020` Proposal Inspection CLI MVP — `.p2p/proposals/PROP-020-proposal-inspection-cli-mvp`
- `PROP-021` Agent Skill Real Commands Update — `.p2p/proposals/PROP-021-agent-skill-real-commands-update`
- `PROP-022` Operational Brief Prompt Workflow — `.p2p/proposals/PROP-022-operational-brief-prompt-workflow`
- `PROP-023` Next Action Recommender MVP — `.p2p/proposals/PROP-023-next-action-recommender-mvp`
- `PROP-024` Choice Blocking and Discovery MVP — `.p2p/proposals/PROP-024-choice-blocking-and-discovery-mvp`
- `PROP-025` Controlled Intake Apply Workflow — `.p2p/proposals/PROP-025-controlled-intake-apply-workflow`
- `PROP-026` P2P Software Spec Generator MVP — `.p2p/proposals/PROP-026-p2p-software-spec-generator-mvp`
- `PROP-027` Software Spec Exporter MVP — `.p2p/proposals/PROP-027-software-spec-exporter-mvp`
- `PROP-028` Spec Kit Export Mapping MVP — `.p2p/proposals/PROP-028-spec-kit-export-mapping-mvp`
- `PROP-029` Spec Export Validation MVP — `.p2p/proposals/PROP-029-spec-export-validation-mvp`
- `PROP-030` Managed Work and Multi-Branch Visibility Policy — `.p2p/proposals/PROP-030-managed-work-and-multi-branch-visibility-policy`
- `PROP-031` Multi-Branch Work Scan MVP — `.p2p/proposals/PROP-031-multi-branch-work-scan-mvp`
- `PROP-032` Managed Work Branch Creation MVP — `.p2p/proposals/PROP-032-managed-work-branch-creation-mvp`
- `PROP-033` Managed Work Submit MVP — `.p2p/proposals/PROP-033-managed-work-submit-mvp`
- `PROP-034` Managed Work Review MVP — `.p2p/proposals/PROP-034-managed-work-review-mvp`
- `PROP-035` Managed Work Publish MVP — `.p2p/proposals/PROP-035-managed-work-publish-mvp`
- `PROP-036` Managed Work Accept MVP — `.p2p/proposals/PROP-036-managed-work-accept-mvp`
- `PROP-037` Managed Work Status Summary MVP — `.p2p/proposals/PROP-037-managed-work-status-summary-mvp`
- `PROP-038` Managed Work Merge Conflict Guidance MVP — `.p2p/proposals/PROP-038-managed-work-merge-conflict-guidance-mvp`
- `PROP-039` Managed Work Finalize MVP — `.p2p/proposals/PROP-039-managed-work-finalize-mvp`
- `PROP-040` Managed Work Cleanup MVP — `.p2p/proposals/PROP-040-managed-work-cleanup-mvp`
- `PROP-041` Remote Project Profile and Review Request Policy — `.p2p/proposals/PROP-041-remote-project-profile-and-review-request-policy`
- `PROP-042` P2P Core CLI MCP Mediator Web Boundary — `.p2p/proposals/PROP-042-p2p-core-cli-mcp-mediator-web-boundary`
- `PROP-043` Managed Work Retire MVP — `.p2p/proposals/PROP-043-managed-work-retire-mvp`
- `PROP-044` P2P MCP Server MVP — `.p2p/proposals/PROP-044-p2p-mcp-server-mvp`
- `PROP-045` Agent-Safe Project Bootstrap MVP — `.p2p/proposals/PROP-045-agent-safe-project-bootstrap-mvp`
- `PROP-046` MCP Write-Safe Bootstrap Tools MVP — `.p2p/proposals/PROP-046-mcp-write-safe-bootstrap-tools-mvp`
- `PROP-047` Guided Init Wizard MVP — `.p2p/proposals/PROP-047-guided-init-wizard-mvp`
- `PROP-048` MCP Level 3 Proposal and Intake Draft Tools — `.p2p/proposals/PROP-048-mcp-level-3-proposal-and-intake-draft-tools`
- `PROP-049` MCP Level 4A Proposal Refinement Tools — `.p2p/proposals/PROP-049-mcp-level-4a-proposal-refinement-tools`
- `PROP-050` MCP Level 4B Choice Conflict Impact Advisory Tools — `.p2p/proposals/PROP-050-mcp-level-4b-choice-conflict-impact-advisory-tools`
- `PROP-051` Draft Proposal Next Action and Agent Explanation Guard — `.p2p/proposals/PROP-051-draft-proposal-next-action-and-agent-explanation-guard`
- `PROP-052` MCP Proposal Contribution Tool — `.p2p/proposals/PROP-052-mcp-proposal-contribution-tool`
- `PROP-053` Core Validation Layer MVP — `.p2p/proposals/PROP-053-core-validation-layer-mvp`
- `PROP-054` Project Readiness and Maturity Assessment — `.p2p/proposals/PROP-054-project-readiness-and-maturity-assessment`
- `PROP-055` Agent Token Budget and Context Discipline — `.p2p/proposals/PROP-055-agent-token-budget-and-context-discipline`
- `PROP-056` Project Definition Maturity Rubrics — `.p2p/proposals/PROP-056-project-definition-maturity-rubrics`
- `PROP-057` Guided Rubric Selection During Init — `.p2p/proposals/PROP-057-guided-rubric-selection-during-init`
- `PROP-058` Project README and Installation Guide — `.p2p/proposals/PROP-058-project-readme-and-installation-guide`
- `PROP-061` Focused README and Documentation Map — `.p2p/proposals/PROP-061-focused-readme-and-documentation-map`
- `PROP-062` README Product Landing Page Refinement — `.p2p/proposals/PROP-062-readme-product-landing-page-refinement`
- `PROP-064` Spec Kit Three-Prompt Export Model — `.p2p/proposals/PROP-064-spec-kit-three-prompt-export-model`
