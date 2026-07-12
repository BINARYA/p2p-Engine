# Requirements - PROP-084 Project Runtime Contract And Version Alignment

## Scope

Implement the corrected production scope for accepted `PROP-084`.

The feature solves one problem: after a P2P-managed project is cloned, copied,
or extracted, humans and agents must know which P2P Engine runtime version is
compatible with that project and which version is recommended.

This feature is contract-first. It does not automate installation.

## Origin

- Source proposal: `PROP-084 - Project-Local Runtime Bootstrap And Upgrade Flow`
- Decision: accepted with changes
- Third review correction:
  - runtime contract is required;
  - mandatory scripts, install/reconcile managers, release resolvers, wheel
    metadata, digests, source descriptors, and environment mutation are not
    required for the version-alignment problem;
  - governed writes should be gated when a declared or required contract cannot
    be trusted;
  - legacy projects without a contract remain warning-only.
- Related accepted proposals:
  - `PROP-078 - Project-Local Wheel Installation and Upgrade Model`
  - `PROP-080 - Automated GitHub Release Wheel Publishing`
- Local quality policy:
  - `AGENTS-p2p-dev-specs.md`
  - `docs/DEVELOPMENT-GUIDELINES.md`
  - `specs/skills/ENGINEERING_QUALITY_SKILL.md`
  - `specs/skills/TEST_QUALITY_SKILL.md`

## In Scope

- Authoritative runtime contract at `.p2p/project/runtime.yml`.
- Runtime contract schema, typed model, parser, serializer, and semantic
  validator.
- Compatible runtime range and recommended P2P Engine runtime version.
- Initial strict compatibility policy: generated contracts use
  `requires: "==<active-version>"` until a separate compatibility policy
  explicitly allows broader ranges.
- Required-contract marker in existing `.p2p/project.yml`.
- Project-root `P2P-SETUP.md` generated from the runtime contract for humans
  and agents.
- Runtime status diagnostics when P2P Engine is already installed.
- `p2p validate` findings for malformed or semantically invalid runtime
  contracts.
- Project initialization support for writing a minimal runtime contract and
  setup guide.
- Contract-aware gate for governed writes when a declared or required runtime
  contract is incompatible, invalid, unsupported, or required but missing.
- Public documentation and generated agent guidance explaining the contract
  without mutating environments.

## Out Of Scope

- Mandatory script-based setup.
- Runtime install manager.
- Runtime reconcile manager.
- Automatic install, upgrade, downgrade, replacement, source switch, or
  environment mutation.
- Virtual environment lifecycle management.
- Package resolver or package download behavior.
- Release tag, wheel filename, SHA-256 digest, source descriptor, repository
  coordinate, or URL fields in the required runtime contract.
- Release workflow changes for wheel metadata.
- Automatic fallback from an online source to a repository-local wheel.
- Arbitrary project-declared download URLs.
- Arbitrary GitHub repositories.
- Project-supplied install commands.
- PyPI resolution, generic mirrors, source checkout installs, and editable
  installs.
- Broad command blocking across read-only commands.
- Full Windows installation support. Path and schema validation should still be
  platform-conscious.
- Moving release publication or wheel building ownership from PROP-080.
- Moving project-local installation mechanics from PROP-078.

## Public Surface And MCP Impact

- CLI impact: additive read-only command `p2p runtime status`.
- CLI output impact: `p2p runtime status` must support human-readable output
  and machine-readable JSON output.
- MCP impact: no MCP runtime tools are required in this feature. The decision is
  explicit because runtime status is agent-facing; MCP parity is deferred until
  a separate read-only MCP surface is designed.
- Storage impact: new compatible persisted artifact
  `.p2p/project/runtime.yml`.
- Project-root documentation impact: generated `P2P-SETUP.md`.
- Validation impact: `p2p validate` reports runtime contract errors when the
  contract exists or is required by project policy.
- Validation impact: `p2p validate` reports generated setup-guide drift when
  `P2P-SETUP.md` no longer matches `runtime.yml`.
- Governed-write impact: mutating P2P operations must run a runtime contract
  preflight before mutation when a runtime contract is declared or required.
- Agent-facing behavior: generated guidance tells agents to read the contract,
  report mismatches, and ask for explicit owner action before environment
  mutation.

## Functional Requirements

### Runtime Contract

- R001: THE SYSTEM SHALL define `.p2p/project/runtime.yml` as the authoritative
  project-local declaration of required P2P Engine runtime compatibility.
- R002: THE SYSTEM SHALL define a versioned schema for the runtime contract.
- R003: THE SYSTEM SHALL record a compatible P2P Engine runtime range.
- R004: THE SYSTEM SHALL record a recommended P2P Engine runtime version.
- R005: THE SYSTEM SHALL keep compatible range and recommended version as
  separate fields.
- R006: THE SYSTEM SHALL use strict initial compatibility for generated
  contracts: `requires` SHALL equal `==<recommended-version>`.
- R007: THE SYSTEM SHALL NOT generate broader compatible ranges until a separate
  compatibility policy explicitly declares those ranges safe.
- R008: THE SYSTEM SHALL reject a contract whose recommended version does not
  satisfy the compatible runtime range.
- R009: THE SYSTEM SHALL reject unsupported runtime contract schema versions.
- R010: THE SYSTEM SHALL reject missing required fields.
- R011: THE SYSTEM SHALL reject invalid version strings.
- R012: THE SYSTEM SHALL reject or report as invalid any required-contract field
  that attempts to declare install sources, release tags, wheel filenames,
  digests, URLs, repository coordinates, or project-supplied install commands.
- R013: THE SYSTEM SHALL NOT infer project compatibility from local package
  state when `runtime.yml` is missing.
- R014: THE SYSTEM SHALL report `legacy_undeclared` when no runtime contract
  exists and `.p2p/project.yml` does not declare
  `runtime_contract.required: true`.
- R015: THE SYSTEM SHALL use `.p2p/project.yml` as the required-contract marker
  location.
- R016: `.p2p/project.yml` SHALL declare a required runtime contract with
  top-level `runtime_contract.required: true`.
- R017: THE SYSTEM SHALL report `missing_contract` when
  `.p2p/project.yml` declares `runtime_contract.required: true` and
  `.p2p/project/runtime.yml` is absent.
- R018: THE SYSTEM SHALL treat `legacy_undeclared` and `missing_contract` as
  distinct states.

### Runtime Status

- R019: WHEN P2P Engine is installed, THE SYSTEM SHALL provide a runtime status
  view for the current project.
- R020: Runtime status SHALL report contract path, contract state, declared
  compatible range, declared recommended version, current runtime version, and
  compatibility verdict.
- R021: Runtime status SHALL distinguish at least these states:
  `compatible`, `incompatible`, `invalid_contract`, `unsupported_contract`,
  `missing_contract`, and `legacy_undeclared`.
- R022: Runtime status SHALL be read-only.
- R023: Runtime status SHALL NOT create, modify, install, upgrade, downgrade,
  replace, or reconcile anything.
- R024: Runtime status SHALL suggest existing documented install or
  verification steps rather than executing them.
- R025: Runtime status SHALL expose stable finding/status codes for tests,
  JSON output, docs, and future MCP reuse.

### Project Initialization And Setup Guide

- R026: WHEN a new P2P project is initialized, THE SYSTEM SHALL create
  `.p2p/project/runtime.yml` using the active P2P Engine runtime version and
  strict initial compatibility.
- R027: New project initialization SHALL set
  `.p2p/project.yml` top-level `runtime_contract.required: true`.
- R028: Runtime contract creation SHALL NOT require release metadata, wheel
  metadata, digest metadata, network access, or package resolution.
- R029: Runtime contract creation SHALL NOT write placeholder release, wheel, or
  digest values.
- R030: THE SYSTEM SHALL preserve an existing `runtime.yml` during repeated
  initialization and SHALL NOT regenerate a missing required contract during
  ordinary initialization of an existing project; recovery requires restoration
  from authoritative project history or a separate explicit contract-recovery
  operation outside this feature.
- R031: WHEN a new P2P project is initialized, THE SYSTEM SHALL create
  project-root `P2P-SETUP.md` from the runtime contract.
- R032: Generated `P2P-SETUP.md` SHALL contain a stable P2P-managed marker.
- R033: `P2P-SETUP.md` SHALL show the compatible range and recommended runtime
  version.
- R034: `P2P-SETUP.md` SHALL point to `.p2p/project/runtime.yml` as the source
  of truth.
- R035: `P2P-SETUP.md` SHALL tell users to install the recommended P2P Engine
  version through existing official installation guidance and then run
  `p2p runtime status`.
- R036: THE SYSTEM SHALL preserve an existing `P2P-SETUP.md` during repeated
  initialization unless an explicit refresh command is implemented.
- R037: WHEN a managed `P2P-SETUP.md` exists, THE SYSTEM SHALL validate it by
  rendering the expected deterministic setup guide from
  `.p2p/project/runtime.yml` and comparing the full managed file content,
  normalizing only newline representation.
- R038: WHEN an unmarked `P2P-SETUP.md` exists, THE SYSTEM SHALL NOT overwrite
  it during initialization and SHALL report actionable guidance rather than
  treating it as managed.

### Validation

- R039: WHEN `.p2p/project/runtime.yml` exists, `p2p validate` SHALL validate
  its YAML shape and semantic contract.
- R040: WHEN `.p2p/project.yml` declares `runtime_contract.required: true` and
  `runtime.yml` is absent,
  `p2p validate` SHALL report `missing_contract`.
- R041: WHEN `runtime.yml` is absent and `.p2p/project.yml` does not declare
  `runtime_contract.required: true`, `p2p validate` SHALL report deterministic
  non-blocking warning `P2P267_RUNTIME_CONTRACT_LEGACY_UNDECLARED`.
- R042: Validation SHALL report deterministic findings for unsupported schema,
  missing fields, invalid versions, and recommended-version/range mismatch.
- R043: Validation SHALL report deterministic findings for installer/source
  fields that are not part of the required contract.
- R044: Validation SHALL report deterministic finding
  `P2P268_RUNTIME_SETUP_GUIDE_DRIFT` when managed `P2P-SETUP.md` full content
  differs from the deterministic setup guide rendered from `runtime.yml`,
  normalizing only newline representation.
- R045: Validation SHALL report deterministic guidance when an unmarked
  `P2P-SETUP.md` prevents generation of the managed setup guide.
- R046: Validation SHALL NOT attempt network access.
- R047: Validation SHALL NOT install or modify runtime environments.

### Governed Write Gate

- R048: THE SYSTEM SHALL define a runtime contract preflight for governed
  writes.
- R049: Governed writes SHALL include mutations of P2P-managed project state
  such as proposal, decision, choice, change, work, governance, permission,
  consent, managed sync, and managed branch state.
- R050: THE SYSTEM SHALL inventory every public CLI, service, and MCP entry
  point that can mutate P2P-managed project state before implementing the gate.
- R051: The write-path inventory SHALL classify each mutating entry point as
  guarded in this feature, read-only/non-mutating, or explicitly deferred with
  reason.
- R052: Governed writes SHALL run the runtime preflight before mutation where
  they pass through implemented P2P Engine command, service, or MCP write paths.
- R053: Governed writes SHALL proceed when runtime status is `compatible`.
- R054: Governed writes SHALL fail before mutation when runtime status is
  `incompatible`, `invalid_contract`, `unsupported_contract`, or
  `missing_contract`.
- R055: Governed writes SHALL NOT fail solely because runtime status is
  `legacy_undeclared`.
- R056: Read-only commands SHALL remain available for diagnosis, context, status,
  validation, and guidance.
- R057: THE SYSTEM SHALL report an actionable preflight error when a governed
  write is blocked.
- R058: THE SYSTEM SHALL document that this gate is guaranteed only by runtimes
  that implement PROP-084; older runtimes may ignore `runtime.yml` unless a
  separate project-format marker causes them to reject the project.

### CLI, Docs, And Agent Guidance

- R059: THE SYSTEM SHALL add `p2p runtime status` as a read-only CLI command.
- R060: `p2p runtime status` SHALL support machine-readable JSON output.
- R061: Public install documentation SHALL explain how a collaborator reads the
  runtime contract and installs the recommended version through existing
  official installation guidance.
- R062: Public CLI documentation SHALL describe runtime status diagnostics.
- R063: Generated agent instructions SHALL state that runtime environment
  mutation requires explicit owner action outside this feature.
- R064: Generated agent instructions SHALL tell agents not to infer
  compatibility when a project is `legacy_undeclared`.

## Non-Functional Requirements

- N001: New runtime contract behavior SHALL live in cohesive core/service
  modules behind `P2PWorkspace`.
- N002: `src/p2p_engine/cli.py` SHALL receive registration glue only.
- N003: `src/p2p_engine/storage/filesystem.py` SHALL receive facade delegation
  only.
- N004: Runtime contract reads and writes SHALL derive paths from the supplied
  project root.
- N005: Runtime contract and setup-guide writes SHALL use existing atomic write
  helpers where available.
- N006: Runtime diagnostics SHALL use stable codes and actionable text.
- N007: Governed-write preflight SHALL be centralized enough that new write
  paths can reuse it without duplicating policy.
- N008: Tests SHALL use temporary roots and deterministic version fixtures.
- N009: Tests SHALL NOT depend on network availability, local user paths, real
  GitHub Releases, or ambient Git state.
- N010: Public CLI, validation, persisted-contract, setup-guide, and write-gate
  behavior SHALL be covered by focused and public-contract tests.
- N011: The write-path inventory SHALL be maintained as a local implementation
  artifact under this feature or as a test fixture, not as unmanaged `.p2p`
  governance state.

## Edge Cases And Errors

- E001: Missing `runtime.yml` with no marker requiring it reports
  `legacy_undeclared`.
- E002: Missing `runtime.yml` with a marker requiring it reports
  `missing_contract`.
- E003: Empty or non-mapping `runtime.yml` reports `invalid_contract`.
- E004: Unsupported schema reports `unsupported_contract`.
- E005: Missing compatible range reports `invalid_contract`.
- E006: Missing recommended version reports `invalid_contract`.
- E007: Recommended version outside compatible range reports
  `invalid_contract`.
- E008: Generated contract for runtime `0.1.9` uses
  `requires: "==0.1.9"` and `recommended: "0.1.9"`.
- E009: Installer/source fields in the required contract report
  `invalid_contract`.
- E010: Re-running initialization preserves existing runtime contract.
- E011: Re-running initialization preserves existing managed `P2P-SETUP.md`.
- E012: Managed `P2P-SETUP.md` drift reports
  `P2P268_RUNTIME_SETUP_GUIDE_DRIFT`.
- E013: Unmarked `P2P-SETUP.md` is preserved and reported with guidance.
- E014: Incompatible installed runtime reports `incompatible` with guidance.
- E015: Runtime status never mutates project state or environment.
- E016: Governed write blocked by runtime preflight leaves target state
  unchanged.
- E017: Legacy project without runtime contract can still run governed writes,
  subject to existing non-runtime policies.
- E018: Existing project with `.p2p/project.yml`
  `runtime_contract.required: true` and missing `runtime.yml` remains
  `missing_contract` after ordinary initialization; no contract is regenerated
  from the active local runtime.

## Acceptance Criteria

- AC001: New or explicitly initialized projects can declare
  `.p2p/project/runtime.yml` with schema version, compatible runtime range, and
  recommended P2P Engine runtime version.
- AC002: Runtime contract validation rejects unsupported schema, missing
  fields, invalid versions, recommended/range mismatch, and installer/source
  fields.
- AC003: New project initialization creates `P2P-SETUP.md` from the runtime
  contract and preserves existing setup files on idempotent init.
- AC004: Generated runtime contracts use strict initial compatibility:
  `requires` equals `==<recommended-version>`.
- AC005: `p2p runtime status` reports declared runtime requirements and current
  compatibility without mutation.
- AC006: `p2p runtime status --format json` exposes stable machine-readable
  status data.
- AC007: `p2p validate` reports runtime contract errors when the contract
  exists or is required by project policy.
- AC008: `p2p validate` reports managed `P2P-SETUP.md` drift from the runtime
  contract with `P2P268_RUNTIME_SETUP_GUIDE_DRIFT`.
- AC009: Existing projects without `runtime.yml` are reported as
  `legacy_undeclared`, not inferred from the installed package and not blocked
  solely by absence of a contract.
- AC010: Governed writes are blocked before mutation when a declared or
  required runtime contract is incompatible, invalid, unsupported, or missing.
- AC011: The implementation includes and tests a complete inventory of public
  CLI, service, and MCP entry points that mutate P2P-managed state, classified
  as guarded, read-only/non-mutating, or deferred with reason.
- AC012: Public docs, `P2P-SETUP.md`, and generated agent guidance explain the
  contract-first workflow and the explicit owner boundary for environment
  mutation.
- AC013: The implementation does not add a mandatory script, install manager,
  reconcile manager, release resolver, source selector, digest verifier,
  automatic installation, automatic upgrade, automatic downgrade, or automatic
  offline fallback.
- AC014: Ordinary initialization cannot recover or recreate a missing required
  runtime contract from the active local runtime.
