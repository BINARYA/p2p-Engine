# Design

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
