# Requirements - PROP-095 Project Runtime Contract Update Lifecycle

## Scope

Implement accepted `PROP-095` as a local development feature.

The feature adds an explicit owner-controlled lifecycle for changing an existing
valid project runtime contract after initialization. It does not install,
upgrade, downgrade, select, reconcile, or otherwise mutate the active P2P Engine
runtime environment.

## Origin

- Source proposal: `PROP-095 - Project Runtime Contract Update Lifecycle`
- Decision: accepted
- Depends on: implemented `PROP-084 - Project Runtime Contract And Version Alignment`
- Local quality policy:
  - `AGENTS-p2p-dev-specs.md`
  - `docs/DEVELOPMENT-GUIDELINES.md`
  - `specs/skills/ENGINEERING_QUALITY_SKILL.md`
  - `specs/skills/TEST_QUALITY_SKILL.md`

## In Scope

- `p2p runtime contract preview`
- `p2p runtime contract apply`
- Read-only preview for owners, agents, and non-owner collaborators.
- Owner-authorized apply with explicit confirmation.
- Deterministic stateless expected-state token.
- Runtime contract validation for proposed `requires` and `recommended`.
- Supported range grammar for update impact classification:
  - `==VERSION`
  - `>=LOWER,<UPPER`
- Stable impact labels:
  - `recommended_only`
  - `range_widening`
  - `range_tightening`
  - `runtime_line_change`
  - `current_runtime_excluded`
- Setup-guide state handling for missing, managed aligned, managed drifted, and
  unmanaged `P2P-SETUP.md`.
- Coordinated writes to managed `P2P-SETUP.md` and `.p2p/project/runtime.yml`.
- Contract-last write order.
- Best-effort release availability diagnostics from local or packaged metadata.
- Human and JSON CLI output.
- Docs and agent guidance for no-install boundary and next actions.

## Out Of Scope

- Runtime installation, upgrade, downgrade, source switch, environment selection,
  or reconciliation.
- Network release lookup, GitHub query, package resolution, wheel download, or
  package installation.
- Mandatory linked P2P decision for every update.
- Automatic proposal or decision creation.
- Unmanaged `P2P-SETUP.md` adoption, replacement, backup, merge, or overwrite.
- Invalid contract repair.
- Unsupported contract schema migration.
- Missing required contract recovery.
- Legacy undeclared contract adoption.
- MCP mutation parity in the first implementation.
- Git commit, branch, push, pull request, merge, or provider handoff automation.
- Broad project validation as an automatic post-apply side effect when the active
  runtime becomes incompatible.

## Public Surface And MCP Impact

- CLI impact: add `p2p runtime contract preview` and
  `p2p runtime contract apply`.
- CLI output impact: both commands must support human-readable and JSON output.
- Storage impact: coordinated updates may write `.p2p/project/runtime.yml` and
  managed `P2P-SETUP.md`.
- Validation impact: existing `p2p runtime status` and `p2p validate` remain the
  diagnostic surfaces after a contract update.
- Agent-facing behavior: agents may run preview and pass token/output to an
  owner; agents must not treat the token as authority.
- MCP impact: no MCP mutation is added in this feature. A future MCP mutation
  surface must be consent-gated separately.

## Functional Requirements

### Command Surface

- R001: THE SYSTEM SHALL expose `p2p runtime contract preview`.
- R002: THE SYSTEM SHALL expose `p2p runtime contract apply`.
- R003: `preview` SHALL be read-only and SHALL NOT mutate project, governance,
  audit, token, consent, permission, or environment state.
- R004: `apply` SHALL be the only mutating runtime contract update command.
- R005: THE FIRST IMPLEMENTATION SHALL NOT provide a single-command
  preview-and-apply mode.
- R006: Both commands SHALL support stable JSON output for agent and script use.
- R007: Invalid CLI options or unsupported output formats SHALL fail without
  mutation.

### Proposed Contract Validation

- R008: THE SYSTEM SHALL accept proposed `requires` and `recommended` values.
- R009: THE SYSTEM SHALL require the proposed `recommended` version to satisfy
  the proposed `requires` range.
- R010: THE SYSTEM SHALL support update impact classification for `==VERSION`
  and `>=LOWER,<UPPER`.
- R011: THE SYSTEM SHALL reject proposed ranges outside the supported update
  grammar for applicable updates.
- R012: THE SYSTEM SHALL reject invalid PEP 440-compatible version strings.
- R013: THE SYSTEM SHALL fail closed without an applicable token when the
  proposed contract is invalid.
- R014: WHEN `requires` and `recommended` are unchanged, THE SYSTEM SHALL return
  `no_change`, no applicable token, no apply operation, and no file changes.
- R015: WHEN only `recommended` changes and it satisfies unchanged `requires`,
  THE SYSTEM SHALL classify the update as `recommended_only` unless other
  independent labels apply.

### Current State Handling

- R016: WHEN the current contract state is `compatible`, THE SYSTEM SHALL allow
  applicable preview subject to proposed contract validation and structural
  blockers.
- R017: WHEN the current contract state is `incompatible` only because the active
  runtime is outside a valid supported old range, THE SYSTEM SHALL allow the
  limited runtime-contract update exception.
- R018: WHEN the current state is `invalid_contract`, `unsupported_contract`,
  `missing_contract`, or `legacy_undeclared`, THE SYSTEM SHALL return
  diagnostic-only preview and SHALL NOT return an applicable token.
- R019: For untrusted current states, THE SYSTEM MAY validate proposed values and
  MAY report whether the active runtime would satisfy the proposed range as a
  hypothetical diagnostic.
- R020: For untrusted current states, THE SYSTEM SHALL NOT produce transition
  impact labels, mutation plans, apply commands, or `apply_allowed: true`.
- R021: For untrusted current states, THE SYSTEM SHALL report the required
  separate workflow: repair, schema migration, recovery, or adoption.
- R022: `apply` SHALL remain blocked for untrusted current states.

### Impact Classification

- R023: THE SYSTEM SHALL classify range changes by accepted version sets, not by
  textual string differences.
- R024: THE SYSTEM SHALL add `range_widening` when the proposed range accepts at
  least one version not accepted by the current range.
- R025: THE SYSTEM SHALL add `range_tightening` when the current range accepts at
  least one version not accepted by the proposed range.
- R026: THE SYSTEM SHALL add both `range_widening` and `range_tightening` for
  partially overlapping ranges that each contain versions excluded by the other.
- R027: THE SYSTEM SHALL add both `range_widening` and `range_tightening` for
  disjoint ranges and SHALL report that ranges do not overlap.
- R028: THE SYSTEM SHALL add `runtime_line_change` when the normalized
  `major.minor` line of the recommended version changes.
- R029: THE SYSTEM SHALL add `current_runtime_excluded` when the active runtime
  will not satisfy the proposed range during an applicable transition.
- R030: THE SYSTEM SHALL require a structured reason when `range_tightening`,
  `runtime_line_change`, or `current_runtime_excluded` is present.
- R031: THE SYSTEM SHALL NOT add `recommended_only` when the compatible range
  changes.

### Authority, Confirmation, Decision Link, And Reason

- R032: `preview` SHALL NOT require owner authority.
- R033: `preview` SHALL report whether authority is required for apply.
- R034: `preview` SHALL report whether the current actor appears authorized
  without exposing unnecessary permission details.
- R035: `apply` SHALL perform a fresh binding authority check.
- R036: `apply` SHALL fail without mutation when owner authority cannot be
  verified.
- R037: `apply` SHALL require explicit confirmation for every non-no-op update.
- R038: `apply` SHALL fail without mutation when explicit confirmation is absent.
- R039: THE SYSTEM SHALL allow an optional linked existing P2P decision for
  traceability.
- R040: THE SYSTEM SHALL NOT create a P2P decision automatically.
- R041: THE SYSTEM SHALL NOT block solely because no linked decision is supplied.
- R042: THE SYSTEM SHALL bind any supplied decision identifier into the
  expected-state token.
- R043: THE SYSTEM SHALL bind structured reason text into the expected-state
  token.
- R044: WHEN no generic governed audit primitive is available, THE SYSTEM SHALL
  report `reason_persisted: false` and `audit_mode: external`.

### Expected-State Token

- R045: Applicable preview SHALL return a deterministic stateless
  `expected_state_token`.
- R046: THE TOKEN SHALL bind operation identifier, token format version, current
  runtime-contract content or digest, setup-guide state/content digest, marker
  state, proposed values, reason, optional decision, impact algorithm version,
  and impact labels.
- R047: THE TOKEN SHALL NOT be treated as authority, confirmation, consent,
  audit, secret bearer capability, or persisted operation intent.
- R048: THE TOKEN SHALL NOT be persisted, consumed, marked used, expired, or
  actor-bound in the first implementation.
- R049: `apply` SHALL recompute the token from current state and supplied values
  before mutation.
- R050: A token mismatch SHALL fail as `stale_preview` without file changes.
- R051: THE SYSTEM SHALL NOT return an applicable token for invalid proposals,
  untrusted current contracts, unmanaged setup guides, structural blockers, or
  no-op updates.

### Setup Guide Handling

- R052: THE SYSTEM SHALL classify `P2P-SETUP.md` as missing, managed aligned,
  managed drifted, or unmanaged.
- R053: WHEN setup guide is missing and update is otherwise applicable, THE
  SYSTEM SHALL plan and generate a managed setup guide.
- R054: WHEN setup guide is managed aligned and contract changes, THE SYSTEM
  SHALL plan and regenerate it from the proposed contract.
- R055: WHEN setup guide is managed drifted and contract changes, THE SYSTEM
  SHALL report `drift_repair: true`, bind the current guide content or digest in
  the token, and regenerate the guide during apply.
- R056: Managed-guide drift SHALL NOT add a runtime-contract impact label.
- R057: WHEN only managed-guide drift exists and the contract is unchanged, THE
  SYSTEM SHALL report `no_change` plus a drift finding and SHALL NOT perform
  repair-only mutation.
- R058: WHEN setup guide is present but unmanaged, THE SYSTEM SHALL block apply
  before mutation and SHALL NOT return an applicable token.
- R059: THE SYSTEM SHALL NOT expose an override flag that replaces unmanaged
  setup guides.

### Coordinated Write And Post-Update Behavior

- R060: BEFORE the first write, `apply` SHALL validate token, authority,
  confirmation, reason, proposed contract, and setup-guide plan.
- R061: THE SYSTEM SHALL prepare runtime contract and setup guide content in
  memory before writing.
- R062: THE SYSTEM SHALL replace managed `P2P-SETUP.md` before replacing
  `.p2p/project/runtime.yml`.
- R063: THE SYSTEM SHALL replace `.p2p/project/runtime.yml` last.
- R064: WHEN setup guide replacement fails, THE SYSTEM SHALL leave
  `.p2p/project/runtime.yml` unchanged.
- R065: WHEN handled failure occurs, THE SYSTEM SHALL report failure and changed
  files without claiming crash-proof cross-file transactions.
- R066: WHEN the new contract excludes the active runtime, THE SYSTEM SHALL
  perform no further governed mutations after final contract replacement.
- R067: After active runtime exclusion, THE SYSTEM SHALL NOT refresh registries,
  write proposals/contributions/changes/work/governance state, sync, migrate,
  reconcile, audit after activation, or invoke Git automation.
- R068: After active runtime exclusion, THE SYSTEM MAY perform narrowly scoped
  read-only verification of files just written.
- R069: The final result SHALL report final compatibility, files changed,
  whether subsequent governed writes are blocked, whether full validation is
  deferred, and recommended next action.

### Release Availability

- R070: THE SYSTEM SHALL NOT require network access, package resolution,
  installation, or remote release lookup to update the contract.
- R071: WHEN trusted local or packaged release metadata confirms the recommended
  version, THE SYSTEM MAY report `release_availability: verified_available`.
- R072: WHEN authoritative local metadata is unavailable, THE SYSTEM SHALL allow
  an otherwise valid update with `release_availability: unverified`.
- R073: THE SYSTEM SHALL NOT treat absence from stale, incomplete, or optional
  metadata as proof that a release does not exist.

## Non-Functional Requirements

- N001: Runtime contract domain logic SHALL live in core/service modules, not in
  CLI presentation code.
- N002: `P2PWorkspace` SHALL remain a compatibility facade and delegate runtime
  contract update behavior to cohesive services.
- N003: Read-only operations SHALL have no project-state side effects.
- N004: Persisted writes SHALL use existing atomic write helpers where possible.
- N005: Error results SHALL include stable status or blocker fields suitable for
  tests and JSON consumers.
- N006: Tests SHALL protect service behavior before CLI behavior unless the CLI
  output is the public contract being tested.

## Acceptance Criteria

- AC001: `p2p runtime contract preview` is read-only and returns human and JSON
  preview output for applicable updates.
- AC002: `p2p runtime contract apply` requires owner authority, explicit
  confirmation, and matching token before mutation.
- AC003: Invalid proposed contracts, untrusted current contracts, unmanaged setup
  guides, and stale previews fail without mutation.
- AC004: Impact labels match set-based range semantics, including partial
  overlap and disjoint ranges.
- AC005: `recommended_only` updates update contract and managed setup guide
  without changing compatible range semantics.
- AC006: Managed setup-guide drift is repaired during a true contract update and
  drift-only no-op does not mutate files.
- AC007: When a new contract excludes the active runtime, `runtime.yml` is
  replaced last and no subsequent governed writes occur.
- AC008: Focused service tests, CLI tests, and validation tests cover success,
  no-op, blockers, stale state, and post-update exclusion behavior.
