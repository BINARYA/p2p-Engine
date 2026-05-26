# Tasks

Input: Design documents from `specs/change-012-*/`

## Phase 1: Verification

- [ ] T001 Review exported `spec.md` for unsupported requirements.
- [ ] T002 Review `plan.md` and resolve NEEDS CLARIFICATION markers.
- [ ] T003 Confirm `data-model.md` matches P2P provenance.
- [ ] T004 Confirm `contracts/README.md` accurately describes available contracts.

## Phase 2: Implementation Readiness

- [ ] T005 Convert verified Spec Kit artifacts into implementation tasks in the target project.
- [ ] T006 Run project tests after implementation.

## P2P Acceptance Source

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
