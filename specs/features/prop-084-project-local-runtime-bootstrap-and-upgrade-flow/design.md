# Design - PROP-084 Project Runtime Contract And Version Alignment

## Requirements Covered

- R001-R064
- N001-N011
- E001-E018
- AC001-AC014

## Current Baseline

Relevant existing boundaries:

- `src/p2p_engine/services/project_initialization.py` owns deterministic
  project setup file creation.
- `src/p2p_engine/storage/filesystem.py` exposes `P2PWorkspace` as the stable
  compatibility facade.
- `src/p2p_engine/cli.py` registers Typer command groups.
- `src/p2p_engine/services/validation.py` aggregates validation findings.
- `src/p2p_engine/foundation/files.py` provides YAML and atomic write helpers.
- P2P write behavior is spread across proposal, decision, choice, change, work,
  governance, permission, consent, sync, and managed-branch services.

## Key Decisions

- D001: Implement the feature as runtime contract plus status diagnostics.
  Rationale: this directly solves version alignment after clone, copy, or
  archive extraction.

- D002: Keep the runtime contract minimal.
  Rationale: `requires` and `recommended` solve the version-alignment problem;
  release tags, wheel filenames, digests, and source descriptors solve a
  different installer-integrity problem.

- D003: Generate project-local setup guidance.
  Rationale: a collaborator who has just cloned a repository may not know P2P
  internals. `P2P-SETUP.md` gives humans and agents an obvious entry point while
  keeping `runtime.yml` as the source of truth.

- D004: Do not implement install or reconcile automation.
  Rationale: environment mutation is separate from declaring and verifying the
  required runtime. Existing installation guidance remains the path for humans.

- D005: Add a contract-aware governed-write gate.
  Rationale: if a project declares a runtime contract, the contract must have
  normative force before state mutation. The gate is limited to governed writes
  so legacy projects and read-only diagnostics are not disrupted.

- D006: Keep release artifact integrity with PROP-080.
  Rationale: this feature does not build, publish, resolve, or verify release
  wheels.

- D007: Keep installation mechanics with PROP-078.
  Rationale: this feature tells users which runtime version is required; it
  does not install it.

- D008: Defer MCP runtime tools.
  Rationale: runtime status is agent-facing, but this feature can expose stable
  JSON through CLI and keep MCP parity as an explicit later read-only surface.

- D009: Use typed core records for status and diagnostics.
  Rationale: CLI, validation, docs, and future MCP clients need one shared
  contract, not duplicated dictionaries.

- D010: Generated contracts use exact initial compatibility.
  Rationale: until P2P Engine owns an explicit compatibility policy, generating
  broader ranges would create an unsupported promise. New contracts therefore
  use `requires: "==<active-version>"` and `recommended: "<active-version>"`.

- D011: Use the existing mandatory project manifest as the required-contract
  marker.
  Rationale: `.p2p/project.yml` is already created during project
  initialization. A top-level `runtime_contract.required: true` marker lets the
  runtime distinguish a legacy project that never declared a contract from a
  newer project whose contract was deleted or omitted.

- D012: Treat `P2P-SETUP.md` as generated guidance only when it contains a
  stable P2P-managed marker.
  Rationale: root-level setup files are visible to collaborators and can be
  edited by humans. The marker prevents silent overwrite of user-owned docs and
  allows validation to detect drift when the file is managed by P2P.

- D013: Gate governed writes from a complete public write-path inventory.
  Rationale: sample-based coverage is too weak for a governance engine.
  Implementation must enumerate public CLI, service, and MCP write entry points
  and classify each path before relying on the preflight guarantee.

- D014: Ordinary project initialization is not contract recovery.
  Rationale: if a required runtime contract is missing in an existing project,
  regenerating it from the currently installed runtime would rewrite the
  project requirement without knowing the original contract. Recovery must come
  from authoritative project history or a separate explicit recovery operation.

- D015: Validation emits a deterministic legacy warning.
  Rationale: `legacy_undeclared` must be visible and testable without blocking
  legacy projects. `p2p validate` therefore reports a stable non-blocking
  `P2P267_RUNTIME_CONTRACT_LEGACY_UNDECLARED` warning instead of leaving output
  optional.

## Component Plan

### Core Model

Add `src/p2p_engine/core/runtime_contract.py`.

Suggested records:

- `RuntimeContract`
- `P2PRuntimeRequirement`
- `RuntimeStatus`
- `RuntimeFinding`
- `RuntimeDiagnosticCode`
- `RuntimeCompatibility`
- `RuntimeContractValidation`
- `RuntimeWritePreflight`

Stable status values:

```text
compatible
incompatible
invalid_contract
unsupported_contract
missing_contract
legacy_undeclared
```

Finding codes should be stable enough for tests, JSON output, docs, and future
MCP reuse.

### Contract Shape

Preferred schema:

```yaml
runtime_contract:
  schema_version: 1
runtime:
  p2p:
    requires: "==0.1.9"
    recommended: "0.1.9"
```

Notes:

- `requires` answers which installed runtimes can operate the project.
- `recommended` answers which exact version a fresh collaborator should install
  when setting up the project.
- Generated contracts initially set `requires` to the exact recommended
  version. Broader ranges require a separate compatibility policy before they
  can be generated.
- The required contract has no install source fields.
- Arbitrary URLs, repository coordinates, release tags, wheel filenames,
  digests, and install commands are not part of the contract.

### Required-Contract Marker

New project initialization should add this top-level block to
`.p2p/project.yml`:

```yaml
runtime_contract:
  required: true
```

Interpretation:

- `runtime.yml` absent and marker absent: `legacy_undeclared`;
- `runtime.yml` absent and marker present with `required: true`:
  `missing_contract`;
- `runtime.yml` present: validate the contract regardless of marker state.

The marker is not a substitute for `runtime.yml`; it only disambiguates legacy
state from required-but-missing state.

### Runtime Contract Service

Add `src/p2p_engine/services/runtime_contract.py`.

Responsibilities:

- locate `.p2p/project/runtime.yml`;
- parse YAML through foundation helpers;
- normalize into core records;
- validate schema and semantics;
- read current installed P2P Engine version;
- compare current version with declared compatible range;
- distinguish `legacy_undeclared` from `missing_contract` using project-level
  `.p2p/project.yml` marker state;
- produce runtime status;
- expose validation findings for `ValidationService`;
- render setup-guide data for `P2P-SETUP.md`;
- provide a preflight result for governed writes.

No method in this service should install packages, invoke pip, download wheels,
resolve release metadata, or modify virtual environments.

### Version Handling

Installed runtime compatibility should use PEP 440-compatible parsing. If the
project adds a dependency such as `packaging`, the dependency must be justified
and tested. This feature has no pre-install script, so there is no need for a
separate standard-library-only parser.

### Project Initialization

`ProjectInitializationService` should create `.p2p/project/runtime.yml` for new
projects.

Initial values:

- `runtime_contract.schema_version`: `1`;
- `runtime.p2p.requires`: `==<active P2P Engine version>`;
- `runtime.p2p.recommended`: the active P2P Engine version.
- `.p2p/project.yml` top-level `runtime_contract.required`: `true`.

Rules:

- never write release tag, wheel filename, digest, source descriptor, URL,
  repository coordinate, or install command fields;
- never overwrite an existing runtime contract during idempotent init;
- never regenerate a missing required runtime contract during ordinary
  initialization of an existing project;
- when `.p2p/project.yml` declares `runtime_contract.required: true` and
  `.p2p/project/runtime.yml` is absent, keep the project in `missing_contract`;
- recover a missing required contract only by restoring authoritative project
  history or through a future explicit contract-recovery operation outside this
  feature;
- keep existing init behavior compatible for other generated files;
- do not generate broader compatibility ranges until a separate policy defines
  when they are safe.

### Project-Local Setup Guide

Generate project-root `P2P-SETUP.md` from `runtime.yml`.

Required content:

- stable managed marker, suggested literal:
  `<!-- P2P: generated-runtime-setup schema=1 source=.p2p/project/runtime.yml -->`;
- plain title identifying that the project expects P2P Engine;
- compatible runtime range;
- recommended runtime version;
- pointer to `.p2p/project/runtime.yml` as source of truth;
- pointer to existing official installation guidance;
- instruction to run `p2p runtime status` after installing.

Rules:

- keep the file deterministic;
- do not include machine-specific paths;
- do not include shell-specific install commands that duplicate installer
  ownership;
- preserve an existing managed file on idempotent init unless an explicit
  refresh path is implemented;
- never overwrite an unmarked existing `P2P-SETUP.md`; report guidance instead;
- validate managed-file drift against `runtime.yml` through `p2p validate`;
- detect managed-file drift by rendering the expected deterministic
  `P2P-SETUP.md` from the current runtime contract and comparing full file
  content after normalizing only newline representation.

### CLI

Add a `runtime` command group with:

```bash
p2p runtime status
p2p runtime status --format json
```

Properties:

- read-only;
- no install options;
- no reconcile options;
- no source-switch options;
- no environment mutation;
- stable text output for humans;
- JSON-ready payload for tests and agents.

`runtime doctor` is not required in this feature. If later added, it should
reuse the same service model instead of inventing separate diagnostics.

### Validation

Extend `ValidationService` with runtime contract checks.

Potential finding codes:

- `P2P260_RUNTIME_CONTRACT_INVALID`
- `P2P261_RUNTIME_CONTRACT_UNSUPPORTED`
- `P2P262_RUNTIME_CONTRACT_MISSING_FIELD`
- `P2P263_RUNTIME_CONTRACT_INVALID_VERSION`
- `P2P264_RUNTIME_CONTRACT_RECOMMENDED_OUT_OF_RANGE`
- `P2P265_RUNTIME_CONTRACT_INSTALLER_FIELD`
- `P2P266_RUNTIME_CONTRACT_MISSING`
- `P2P267_RUNTIME_CONTRACT_LEGACY_UNDECLARED`
- `P2P268_RUNTIME_SETUP_GUIDE_DRIFT`
- `P2P269_RUNTIME_SETUP_GUIDE_UNMANAGED`

Missing `runtime.yml` should not make `p2p validate` fail by itself unless a
`.p2p/project.yml` marker says the contract is required. When the marker is
absent, validation should emit non-blocking warning
`P2P267_RUNTIME_CONTRACT_LEGACY_UNDECLARED`.

Managed setup-guide drift should be detected only when `P2P-SETUP.md` contains
the P2P-managed marker. An unmarked root setup file is user-owned and should be
preserved, with deterministic guidance if it prevents generation of the managed
guide. For managed files, drift detection should compare the full deterministic
rendered content, normalizing only newline representation.

### Governed-Write Gate

Add a reusable preflight, preferably in the runtime contract service or a small
guard service that depends on it.

Preflight result:

- `allowed: true` for `compatible`;
- `allowed: true` with warning guidance for `legacy_undeclared`;
- `allowed: false` for `incompatible`, `invalid_contract`,
  `unsupported_contract`, and `missing_contract`.

Implementation should place the guard at shared service or facade boundaries
used by mutating commands and MCP write tools. Avoid scattering runtime checks
through unrelated command handlers.

Before implementation, complete
`specs/features/prop-084-project-local-runtime-bootstrap-and-upgrade-flow/write-path-inventory.md`
or an equivalent test fixture covering public CLI commands,
service/facade methods, and MCP tools that can mutate P2P-managed project
state. Each entry must be classified as:

- `guarded`: the PROP-084 runtime preflight runs before mutation;
- `read_only`: the path does not mutate P2P-managed state;
- `deferred`: the path is intentionally outside this implementation, with a
  reason and residual risk.

The inventory should cover at least proposal, decision, choice, change, work,
governance, permission, consent, managed sync, and managed branch operations.
Tests should derive from this matrix or assert equivalent coverage.

Read-only commands remain available, including:

- `p2p runtime status`;
- `p2p validate`;
- context/status/doctor-style inspection commands that do not mutate state.

The guarantee applies to runtimes that implement PROP-084. Older runtimes may
ignore `runtime.yml` unless a separate project-format marker causes them to
reject the project.

### MCP

No MCP runtime tool is required in this feature.

If runtime MCP parity is later introduced, it should be read-only and reuse the
same `RuntimeStatus` payload as `p2p runtime status --format json`. No MCP
install, reconcile, resolver, or environment mutation tool is added here.

### Docs And Agent Guidance

Update:

- project-root `P2P-SETUP.md` generation;
- `docs/INSTALL.md`;
- `docs/CLI-GUIDE.md`;
- `docs/AGENT-INTEGRATION.md`;
- generated agent templates in `src/p2p_engine/services/agent_templates.py`;
- generated instruction tests.

The documentation should say:

- read `.p2p/project/runtime.yml`;
- use `P2P-SETUP.md` as the visible project-local guide;
- install the recommended version using official installation guidance;
- run `p2p runtime status` after installation;
- `legacy_undeclared` means no compatibility can be inferred and the project is
  warning-only under this feature;
- `missing_contract` means the project declares that the runtime contract is
  required but the file is absent;
- agents must ask for explicit owner action before environment mutation.

## Error Handling

Runtime diagnostics should contain:

- stable code;
- severity;
- contract path;
- declared version/range when available;
- current runtime version when available;
- message;
- documentation pointer or suggested non-mutating command.

Write-gate failures should report:

- the blocked operation class;
- the runtime status that caused the block;
- the contract path;
- the next safe diagnostic step.

Do not convert invalid contracts into silent compatibility success.

## Migration And Compatibility

- Existing projects without `runtime.yml` are `legacy_undeclared` unless a
  `.p2p/project.yml` marker says the contract is required.
- `legacy_undeclared` does not block governed writes.
- `missing_contract` blocks governed writes.
- Missing `runtime.yml` does not trigger automatic contract creation outside
  new project initialization.
- Existing projects with `runtime_contract.required: true` and missing
  `runtime.yml` remain `missing_contract`; ordinary initialization does not
  recreate the contract from the local runtime.
- Recovery from `missing_contract` requires restoration from authoritative
  project history or a future explicit recovery operation.
- New projects receive `runtime.yml`, `.p2p/project.yml` marker state, and
  managed `P2P-SETUP.md`.
- Existing CLI command names remain stable.
- The only required new public CLI surface is `p2p runtime status`.

## Test Strategy

- Unit tests for core records and stable statuses.
- Service tests for valid contract, invalid contract, unsupported contract,
  missing contract, legacy-undeclared, compatible runtime, and incompatible
  runtime.
- Service tests proving installer/source fields are rejected or reported as
  invalid contract data.
- Initialization tests for `runtime.yml` and `P2P-SETUP.md` creation and
  idempotent preservation.
- Initialization tests proving `runtime.yml` uses exact initial compatibility
  and `.p2p/project.yml` records `runtime_contract.required: true`.
- Initialization tests proving an existing project with required marker and
  missing `runtime.yml` remains `missing_contract` and does not regenerate a
  contract from the active local runtime.
- Validation tests for runtime contract semantic findings and managed
  `P2P-SETUP.md` drift.
- Validation tests proving `legacy_undeclared` emits deterministic non-blocking
  warning `P2P267_RUNTIME_CONTRACT_LEGACY_UNDECLARED`.
- Validation tests proving managed setup-guide drift compares full
  deterministic render, not only version fields.
- Setup-guide tests proving unmarked `P2P-SETUP.md` is preserved and reported
  with guidance.
- Write-path inventory tests proving every public mutating path is classified.
- Write-gate tests proving blocked writes leave target state unchanged for each
  guarded path or operation class in the inventory.
- CLI tests for runtime status text and JSON output.
- Generated agent instruction tests for runtime guidance.
- Docs checks only where text is treated as a stable public contract.

Suggested validation:

```bash
.venv/bin/pytest tests/test_runtime_contract_service.py
./scripts/test-focused.sh tests/test_project_initialization_service.py tests/test_validation_service.py -k "runtime"
./scripts/test-focused.sh tests/test_runtime_write_gate.py
./scripts/test-public.sh tests/test_cli.py -k "runtime"
./scripts/test-focused.sh tests/test_agent_instructions_service.py
git diff --check
./scripts/test-full.sh
```

## Risks And Tradeoffs

- The marker location could drift if future project manifest schema changes.
  Mitigation: keep the marker in `.p2p/project.yml`, validate it through typed
  project metadata handling, and cover legacy/missing cases in tests.

- Older runtimes may ignore `runtime.yml`.
  Mitigation: document the guarantee boundary and consider a separate proposal
  for project-format rejection by older runtimes if stronger guarantees are
  required.

- Adding a write gate can create scattered checks.
  Mitigation: centralize the preflight behind services/facades and maintain a
  public write-path inventory instead of relying on sampled path coverage.

- A generated root `P2P-SETUP.md` can drift from `runtime.yml`.
  Mitigation: include a stable managed marker and validate drift with
  `P2P268_RUNTIME_SETUP_GUIDE_DRIFT` using full deterministic rendered-content
  comparison.

- Ordinary initialization could accidentally recreate a deleted contract using
  the wrong local runtime version.
  Mitigation: treat required-but-missing contracts as `missing_contract` and
  require authoritative restoration or a separate explicit recovery operation.

- A future script helper may still be useful.
  Mitigation: leave it outside this feature and require a separate design.

- Adding version-range parsing may require a dependency.
  Mitigation: justify and test the dependency.

## Out Of Scope

- Script-based setup.
- Install/reconcile commands.
- Environment mutation.
- Release resolver or digest verifier.
- Automatic fallback.
- Package registry resolution.
- Source checkout installation.
- Runtime MCP tools.
