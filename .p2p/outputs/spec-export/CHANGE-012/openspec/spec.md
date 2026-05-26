# OpenSpec-Oriented Specification

This file is generated from the P2P-native software spec. It keeps the original sections visible so exporter refinement can happen without losing provenance.

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

## Design

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

## Acceptance

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
