# Requirements - PROP-097 Runtime Contract Adoption For Legacy Projects

## Scope

Implement accepted `PROP-097` as a local development feature.

The feature adds one explicit owner-controlled adoption path for projects that
pre-date runtime contracts and are currently reported as `legacy_undeclared`.
It does not install, upgrade, downgrade, reconcile, or otherwise mutate the
active P2P Engine runtime environment.

## Origin

- Source proposal: `PROP-097 - Runtime Contract Adoption For Legacy Projects`
- Decision: accepted
- Depends on:
  - `PROP-084 - Project Runtime Contract And Version Alignment`
  - `PROP-095 - Project Runtime Contract Update Lifecycle`
- Local quality policy:
  - `AGENTS-p2p-dev-specs.md`
  - `docs/DEVELOPMENT-GUIDELINES.md`
  - `specs/skills/ENGINEERING_QUALITY_SKILL.md`
  - `specs/skills/TEST_QUALITY_SKILL.md`

## In Scope

- `p2p runtime contract adopt`
- Adoption only from `legacy_undeclared`.
- Explicit proposed `requires` and `recommended` values.
- Owner authority check.
- Explicit confirmation before mutation.
- Runtime contract validation using the supported contract grammar.
- Managed `P2P-SETUP.md` generation or regeneration.
- Top-level `.p2p/project.yml` marker `runtime_contract.required: true`.
- Human and JSON CLI output.
- Focused service and CLI tests.

## Out Of Scope

- Runtime installation, upgrade, downgrade, source selection, package
  resolution, or environment reconciliation.
- Adopting from `missing_contract`, `invalid_contract`,
  `unsupported_contract`, `compatible`, or `incompatible`.
- Recovering a deleted required contract.
- Repairing invalid runtime contracts.
- Migrating unsupported runtime-contract schemas.
- Replacing, adopting, backing up, merging, or overwriting unmanaged
  `P2P-SETUP.md`.
- Updating an existing valid runtime contract; that remains `PROP-095`.
- MCP mutation parity in this feature.
- Git commit, branch, push, pull request, merge, or provider handoff automation.

## Public Surface And MCP Impact

- CLI impact: add `p2p runtime contract adopt`.
- CLI output impact: support text and JSON output.
- Storage impact: successful adoption writes:
  - `.p2p/project/runtime.yml`;
  - `P2P-SETUP.md`;
  - `.p2p/project.yml` marker `runtime_contract.required: true`.
- Validation impact: after successful adoption, `p2p runtime status` should
  report `compatible` when the active runtime satisfies the adopted contract,
  and `p2p validate` should no longer emit
  `P2P267_RUNTIME_CONTRACT_LEGACY_UNDECLARED`.
- Agent-facing behavior: agents may report adoption blockers and the exact
  proposed contract values, but adoption remains owner-authorized.
- MCP impact: no MCP mutation is added. A future MCP surface would need an
  explicit consent-gated design.

## Functional Requirements

### Command Surface

- R001: THE SYSTEM SHALL expose `p2p runtime contract adopt`.
- R002: THE COMMAND SHALL accept `--requires` and `--recommended`.
- R003: THE COMMAND SHALL require `--confirm` before performing any mutation.
- R004: THE COMMAND SHALL accept `--actor` for owner authority resolution.
- R005: THE COMMAND SHALL support `--format text` and `--format json`.
- R006: Invalid CLI options or unsupported output formats SHALL fail without
  mutation.

### Current State Handling

- R007: WHEN current runtime state is `legacy_undeclared`, THE SYSTEM MAY adopt
  a runtime contract subject to validation, authority, confirmation, and setup
  guide blockers.
- R008: WHEN current runtime state is not `legacy_undeclared`, THE SYSTEM SHALL
  block adoption without mutation.
- R009: Adoption SHALL NOT be used as missing-contract recovery, invalid
  contract repair, unsupported schema migration, or existing contract update.

### Proposed Contract Validation

- R010: THE SYSTEM SHALL require non-empty proposed `requires` and
  `recommended` values.
- R011: THE SYSTEM SHALL require the proposed `recommended` version to satisfy
  the proposed `requires` range.
- R012: THE SYSTEM SHALL use the same supported grammar as runtime contract
  update for adoption applicability:
  - `==VERSION`;
  - `>=LOWER,<UPPER`.
- R013: THE SYSTEM SHALL reject invalid PEP 440-compatible version strings.
- R014: Invalid proposed contracts SHALL return a structured blocked result and
  SHALL NOT write files.

### Authority And Confirmation

- R015: Adoption SHALL require project-owner authority.
- R016: If authority cannot be verified, THE SYSTEM SHALL block without
  mutation.
- R017: If `--confirm` is absent, THE SYSTEM SHALL block without mutation.
- R018: The default actor MAY be `owner` when no permissions file exists,
  matching the existing runtime update authority behavior.

### Setup Guide Handling

- R019: WHEN `P2P-SETUP.md` is missing, successful adoption SHALL generate a
  managed setup guide.
- R020: WHEN `P2P-SETUP.md` is managed, successful adoption SHALL regenerate it
  from the adopted contract.
- R021: WHEN `P2P-SETUP.md` exists without the stable managed marker, adoption
  SHALL block without mutation.
- R022: Adoption SHALL NOT expose an override flag for unmanaged setup guides.

### Write Behavior

- R023: Before the first write, THE SYSTEM SHALL validate current state,
  proposed contract, authority, confirmation, and setup-guide state.
- R024: Successful adoption SHALL write a runtime contract with schema version
  `1`.
- R025: Successful adoption SHALL add or preserve top-level
  `runtime_contract.required: true` in `.p2p/project.yml`.
- R026: Successful adoption SHALL preserve unrelated project manifest fields.
- R027: The marker update SHALL happen only after the runtime contract has been
  written.
- R028: Handled failures SHALL return the files changed before failure.

### Result Contract

- R029: JSON output SHALL include:
  - `status`;
  - `current_state`;
  - `proposed_contract`;
  - `files_changed`;
  - `blocked_reason`;
  - `message`;
  - `setup_guide`;
  - `authority`.
- R030: A successful adoption SHALL return status `adopted`.
- R031: A blocked adoption SHALL return status `blocked`.
- R032: A partial write failure SHALL return status `partial_failure`.

## Non-Functional Requirements

- N001: Runtime adoption logic SHALL live in `RuntimeContractService` or a
  directly owned service boundary.
- N002: `P2PWorkspace` SHALL only delegate to the service.
- N003: CLI handlers SHALL only parse options, call the facade, and render
  output.
- N004: Existing `p2p runtime status`, `p2p validate`, and `p2p runtime contract
  preview/apply` behavior SHALL remain compatible.
- N005: Persisted writes SHALL use existing atomic file helpers.
- N006: The implementation SHALL add focused service and CLI tests.

## Acceptance Criteria

- AC001: A legacy project can run `p2p runtime contract adopt --requires
  "==<current>" --recommended "<current>" --confirm` and become compatible.
- AC002: Adoption writes `.p2p/project/runtime.yml`,
  `P2P-SETUP.md`, and `runtime_contract.required: true`.
- AC003: Adoption blocks without `--confirm`.
- AC004: Adoption blocks when the actor is not owner-authorized.
- AC005: Adoption blocks when `P2P-SETUP.md` is unmanaged and leaves files
  unchanged.
- AC006: Adoption blocks for non-legacy states.
- AC007: Adoption rejects invalid proposed contracts.
- AC008: After adopting this repository's contract, `p2p validate` no longer
  reports `P2P267_RUNTIME_CONTRACT_LEGACY_UNDECLARED`.
