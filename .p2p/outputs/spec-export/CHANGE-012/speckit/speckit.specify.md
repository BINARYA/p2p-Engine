# Spec Kit Specify Prompt

Use this content with `/speckit.specify`. Focus on what and why; do not select a tech stack here.

## What To Build

- **PROP-001 CLI Foundation**: Build the first P2P Engine CLI using Python and Typer.

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
- **PROP-004 Prompt-only Import Workflow**: Implementare comandi import uniformi per le fasi successive a explore e aggiungere synthesize prompt/import.
- **PROP-005 Codex Skill Integration**: Aggiungere una skill locale .codex/skills/p2p-engine/SKILL.md che istruisca Codex a usare P2P Engine come sorgente di verita operativa.
- **PROP-009 Governance CLI Commands**: Aggiungere comandi governance file-based per rendere operativo il modello di PROP-008, mantenendo Git come audit layer e rimandando enforcement permessi a fasi future.
- **PROP-010 P2P Project State Model**: Add a P2P project state model that turns accepted proposals into versioned project artifacts under `.p2p/project/`. The MVP uses explicit refresh via `p2p project refresh`; automatic refresh after acceptance can be added later.
- **PROP-011 Project Refresh MVP**: Add deterministic project-state generation from accepted proposals, starting with overview, problem, scope, project SWOT placeholder, features, decisions-map, and conflicts.
- **PROP-012 Impact Map and Conflict Memory**: Add impact and conflict artifacts that allow P2P Engine to understand which project areas a proposal touches and preserve memory of competing or mutually exclusive alternatives.
- **PROP-013 Managed Git Adapter and Change Set Model**: Adopt a managed Git model: proposals and change sets are the public P2P concepts, while Git branches, commits, merges, and tags are internal operations selected by a configurable policy. Git details are visible only in verbose/debug modes.

## Why

- **PROP-001 CLI Foundation**: P2P Engine does not exist yet as an executable tool. The project has a solid foundation document, but no CLI, no generated `.p2p/` structure, no automated proposal workflow, and no prompt generation.

Without a first working CLI, every proposal must be created manually. That is acceptable for the bootstrap phase, but it must become automated quickly so the project can start using its own method.
- **PROP-004 Prompt-only Import Workflow**: P2P Engine genera prompt per varie fasi, ma non importa ancora in modo uniforme gli output prodotti da AI o agenti esterni.
- **PROP-005 Codex Skill Integration**: Codex oggi non ha istruzioni formali per usare P2P Engine come metodo operativo e rischia di lasciare decisioni e interlocuzioni solo nella chat.
- **PROP-009 Governance CLI Commands**: P2P Engine ha un modello di governance file-based, ma non ha ancora comandi CLI per inizializzare governance, generare SWOT, registrare voti, mostrare risultati e registrare precedenti decisionali.
- **PROP-010 P2P Project State Model**: Accepted P2P proposals are not yet transformed into a single rationalized project state that can guide implementation, feature tracking, task planning, or downstream export.
- **PROP-011 Project Refresh MVP**: P2P Engine has accepted the .p2p/project state model, but the CLI cannot yet generate or inspect that rationalized project layer.
- **PROP-012 Impact Map and Conflict Memory**: P2P Engine can generate a rationalized project state, but it does not yet capture what a proposal touches or whether it overlaps, depends on, supersedes, or conflicts with other proposals.
- **PROP-013 Managed Git Adapter and Change Set Model**: P2P Engine distinguishes proposals from project state, but it does not yet define how accepted decisions become operational change sets or how Git operations should be managed under the hood without exposing branch/commit/merge complexity to users.

## Users And Workflows

- Humans supervise and decide.
- Agents use P2P memory to preserve project context and propose bounded changes.

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
