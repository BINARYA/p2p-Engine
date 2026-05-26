# Feature Specification: P2P Software Spec Generator MVP

**Feature Branch**: `change-012-p2p-software-spec-generator-mvp`  
**Created**: NEEDS CLARIFICATION  
**Status**: Draft  
**Input**: P2P software spec from `CHANGE-012`

## User Scenarios & Testing

### Primary User Story

As a P2P operator, I can export a governed P2P-native software spec into a Spec Kit-oriented feature directory so that downstream Spec Kit workflows can start from structured artifacts instead of raw proposal folders.

### Acceptance Scenarios

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

## Key Entities

See `data-model.md` for the entity mapping derived from the P2P software spec.

## Governance Boundary

This file is exported from accepted P2P artifacts. Missing implementation details are marked as NEEDS CLARIFICATION and must be resolved through P2P governance before implementation.