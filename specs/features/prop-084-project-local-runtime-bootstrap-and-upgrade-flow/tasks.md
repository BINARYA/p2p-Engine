# Tasks - PROP-084 Project Runtime Contract And Version Alignment

## Status

`implemented`

## Implementation Rules

- Do not add a mandatory script-based setup flow.
- Do not add install, reconcile, upgrade, downgrade, replacement, source
  switch, virtualenv, resolver, download, or package installation behavior.
- Do not add release tag, wheel filename, digest, source descriptor, URL, or
  repository coordinate fields to the required runtime contract.
- Do not modify release workflows for this feature.
- Do not mutate runtime environments from runtime status, validation, docs, or
  generated agent guidance.
- Generated runtime contracts use strict initial compatibility:
  `requires: "==<active-version>"` and `recommended: "<active-version>"`.
- New projects mark the runtime contract as required in `.p2p/project.yml` with
  top-level `runtime_contract.required: true`.
- Gate only governed writes when a declared or required runtime contract cannot
  be trusted; do not block legacy projects solely because `runtime.yml` is
  absent.
- Do not protect only a sample of write paths. Inventory public CLI, service,
  and MCP write entry points, classify each one, and test the guarded set.
- Keep new domain behavior in core/service modules behind `P2PWorkspace`.
- Keep `src/p2p_engine/cli.py`, `src/p2p_engine/storage/filesystem.py`, and MCP
  transport files as registration/facade/presentation glue only.
- Follow `specs/skills/ENGINEERING_QUALITY_SKILL.md` and
  `specs/skills/TEST_QUALITY_SKILL.md`.

## Tasks

- [x] T001. Re-read accepted-with-changes `PROP-084`, third-review
      clarification artifacts, this feature spec, and local quality policies
      before coding.
      - Covers: R001-R064, N001-N011
      - Output: implementation notes in final summary, not `.p2p/`.

- [x] T002. Inspect current project initialization, validation, CLI, public
      service/facade write paths, MCP write tools, docs, and generated-agent
      tests before coding.
      - Covers: N001-N011
      - Expected files:
        `src/p2p_engine/services/project_initialization.py`,
        `src/p2p_engine/services/validation.py`,
        `src/p2p_engine/cli.py`,
        `src/p2p_engine/cli_commands/`,
        `src/p2p_engine/storage/filesystem.py`,
        `src/p2p_engine/services/agent_templates.py`,
        proposal/decision/choice/change/work/governance/permission/consent
        services,
        sync and managed-branch services,
        MCP tool modules,
        `tests/test_project_initialization_service.py`,
        `tests/test_validation_service.py`,
        `tests/test_cli.py`,
        `tests/test_agent_instructions_service.py`.

- [x] T003. Finalize the runtime contract YAML shape, exact initial
      compatibility policy, `.p2p/project.yml` required-contract marker,
      `legacy_undeclared` versus `missing_contract` rule, managed
      `P2P-SETUP.md` marker, missing-contract recovery rule, deterministic
      legacy warning, setup-guide drift comparison rule, and governed-write gate
      placement.
      - Covers: R001-R018, R026-R038, R048-R058
      - Completion: implementation summary records the exact fields, marker
        shape, setup marker, and gate boundary before code changes.

- [x] T004. Add core runtime contract records, stable status values, finding
      codes, setup-guide drift codes, and write-preflight records.
      - Covers: R001-R025, R039-R058, N006-N007
      - Expected file: `src/p2p_engine/core/runtime_contract.py`.
      - Test layer: unit.

- [x] T005. Add core tests for stable statuses, finding codes, JSON-ready
      status payloads, setup-guide drift finding data, and write-preflight
      outcomes.
      - Covers: R019-R025, R039-R058
      - Implemented in: `tests/test_runtime_contract_service.py`.

- [x] T006. Implement `RuntimeContractService` for locating, reading, parsing,
      validating, status reporting, setup-guide rendering data, marker-state
      evaluation, and preflight evaluation.
      - Covers: R001-R025, R031-R047, R048-R058, N001, N004, N007
      - Expected file: `src/p2p_engine/services/runtime_contract.py`.

- [x] T007. Add service tests for valid contract, empty YAML, non-mapping YAML,
      missing fields, unsupported schema, invalid version, recommended/range
      mismatch, installer/source fields, missing required contract, and
      legacy undeclared.
      - Covers: R001-R018, E001-E009
      - Test layer: service.

- [x] T008. Add PEP 440-compatible compatible-range checking while preserving
      exact generated compatibility as the default.
      - Covers: R003-R008, R019-R025
      - If a dependency such as `packaging` is added, update `pyproject.toml`
        and test dependency/version behavior.

- [x] T009. Add compatibility tests for exact match, lower runtime, upper
      runtime, malformed runtime version, missing required contract, and legacy
      project without a contract.
      - Covers: R003-R008, R014-R025, E001-E008, E014-E017
      - Test layer: service.

- [x] T010. Extend project initialization to create `.p2p/project/runtime.yml`
      and set `.p2p/project.yml` top-level `runtime_contract.required: true`
      for new projects.
      - Covers: R026-R030, R014-R018, N004-N005
      - Completion: generated `requires` equals `==<active-version>`, generated
        `recommended` equals `<active-version>`, and no release, wheel, digest,
        URL, repository, or install command fields are written.

- [x] T011. Add project initialization tests proving runtime contract creation,
      exact generated compatibility, project marker creation, preservation of
      existing `runtime.yml`, and no regeneration when an existing project has
      `runtime_contract.required: true` but `runtime.yml` is missing.
      - Covers: R026-R030, E008, E010, E018
      - Suggested validation:
        `./scripts/test-focused.sh tests/test_project_initialization_service.py -k "runtime"`.

- [x] T012. Implement deterministic managed `P2P-SETUP.md` rendering and
      generation during new project initialization.
      - Covers: R031-R038, N005
      - Completion: file contains the stable P2P-managed marker, points to
        `runtime.yml`, shows range and recommended version, contains no
        machine-specific paths or installer-owned commands, and does not
        overwrite unmarked existing setup files.

- [x] T013. Add setup-guide tests proving generation from contract data,
      managed marker presence, preservation of existing managed setup files on
      idempotent init, preservation with guidance for unmarked setup files, and
      full deterministic rendered-content drift detection normalized only for
      newlines.
      - Covers: R031-R038, E011-E013
      - Suggested validation:
        `./scripts/test-focused.sh tests/test_project_initialization_service.py -k "setup or runtime"`.

- [x] T014. Add `P2PWorkspace` facade delegation for runtime status, runtime
      validation data, setup-guide rendering data, and runtime write preflight.
      - Covers: N001-N003, R019-R025, R039-R058
      - Expected file: `src/p2p_engine/storage/filesystem.py`.

- [x] T015. Add facade/service tests proving facade methods delegate without
      adding domain logic to `P2PWorkspace`.
      - Covers: N001-N003
      - Test layer: service/facade.

- [x] T016. Add `p2p runtime` CLI registration and `p2p runtime status` text
      and JSON output.
      - Covers: R019-R025, R059-R060
      - Expected files:
        `src/p2p_engine/cli.py`,
        `src/p2p_engine/cli_commands/runtime.py`.
      - Completion: command is read-only and reports compatibility state.

- [x] T017. Add CLI tests for runtime status on compatible, incompatible,
      invalid-contract, unsupported-contract, missing-contract, and
      legacy-undeclared projects.
      - Covers: R019-R025, R059-R060, E001-E007, E014-E015
      - Suggested validation:
        `./scripts/test-public.sh tests/test_cli.py -k "runtime"`.

- [x] T018. Extend `ValidationService` with runtime contract semantic findings,
      required-contract missing detection, legacy guidance, managed
      `P2P-SETUP.md` drift detection, and unmarked setup-guide guidance.
      - Covers: R039-R047, R037-R038
      - Expected file: `src/p2p_engine/services/validation.py`.

- [x] T019. Add validation tests for runtime contract findings, missing
      required contract, deterministic non-blocking
      `P2P267_RUNTIME_CONTRACT_LEGACY_UNDECLARED`, installer/source fields,
      full-render `P2P268_RUNTIME_SETUP_GUIDE_DRIFT`, and unmarked setup-guide
      guidance.
      - Covers: R039-R047, E001-E013
      - Suggested validation:
        `./scripts/test-focused.sh tests/test_validation_service.py -k "runtime or setup"`.

- [x] T020. Create the public write-path inventory as a local implementation
      artifact or test fixture.
      - Covers: R048-R052, N011
      - Expected file:
        `specs/features/prop-084-project-local-runtime-bootstrap-and-upgrade-flow/write-path-inventory.md`
        or an equivalent test fixture.
      - Required classification for each public CLI, service, and MCP entry:
        guarded, read-only/non-mutating, or deferred with reason.
      - Required domains: proposal, decision, choice, change, work,
        governance, permission, consent, managed sync, managed branch, new
        project initialization, and existing-project initialization where the
        required runtime contract is missing.

- [x] T021. Implement centralized runtime preflight for all guarded governed
      writes identified by the inventory.
      - Covers: R048-R058, N007
      - Completion: guarded paths call the same preflight before mutation;
        read-only paths do not; deferred paths are documented with residual
        risk.

- [x] T022. Add write-gate tests proving compatible contracts allow writes,
      incompatible/invalid/unsupported/missing required contracts block before
      mutation, and `legacy_undeclared` does not block solely by absence of
      `runtime.yml`.
      - Covers: R048-R058, E016-E017, N011, AC011
      - Expected file: `tests/test_runtime_write_gate.py` or focused service
        tests near the guarded writers.
      - Completion: tests cover the inventory classes, not only one
        sampled write path.

- [x] T023. Update generated agent templates with runtime contract guidance,
      `P2P-SETUP.md` guidance, legacy-undeclared guidance, and explicit owner
      boundary for environment mutation.
      - Covers: R061-R064
      - Expected file: `src/p2p_engine/services/agent_templates.py`.

- [x] T024. Add generated instruction tests proving runtime guidance appears
      and existing persistence/governance safety blocks remain present.
      - Covers: R061-R064
      - Suggested validation:
        `./scripts/test-focused.sh tests/test_agent_instructions_service.py`.

- [x] T025. Update public docs for runtime contract, managed `P2P-SETUP.md`,
      runtime status, required-contract marker, exact initial compatibility,
      and the governed-write gate.
      - Covers: R061-R064
      - Expected files:
        `docs/INSTALL.md`,
        `docs/CLI-GUIDE.md`,
        `docs/AGENT-INTEGRATION.md`.

- [x] T026. Record MCP impact as explicitly deferred for runtime status parity
      and verify no MCP install, reconcile, resolver, or runtime mutation tool
      is added.
      - Covers: Public Surface And MCP Impact
      - Completion: implementation summary explains why CLI JSON is the current
        agent-facing surface and what a future read-only MCP surface would
        reuse.

- [x] T027. Add focused docs tests only where wording is treated as public
      contract.
      - Covers: R061-R064, N010
      - If no docs text test is useful, record the reason in the implementation
        summary.

- [x] T028. Add copied-directory, extracted-archive, and Git-independent tests
      proving runtime contract behavior does not depend on Git metadata.
      - Covers: R001-R018, R026-R038, N008-N009
      - Test layer: service or initialization.

- [x] T029. Run focused runtime core and service validation.
      - Covers: R001-R025
      - Suggested command:
        `.venv/bin/pytest tests/test_runtime_contract_service.py`.

- [x] T030. Run focused initialization and validation tests.
      - Covers: R026-R047
      - Suggested command:
        `./scripts/test-focused.sh tests/test_project_initialization_service.py tests/test_validation_service.py -k "runtime or setup"`.

- [x] T031. Run focused write-inventory and write-gate validation.
      - Covers: R048-R058, N011
      - Suggested command:
        `./scripts/test-focused.sh tests/test_runtime_write_gate.py`.

- [x] T032. Run public CLI tests.
      - Covers: R059-R060
      - Suggested command:
        `./scripts/test-public.sh tests/test_cli.py -k "runtime"`.

- [x] T033. Run generated-agent guidance tests.
      - Covers: R061-R064
      - Suggested command:
        `./scripts/test-focused.sh tests/test_agent_instructions_service.py`.

- [x] T034. Run final validation before handoff.
      - Covers: N001-N011, AC001-AC014
      - Required commands:
        `git diff --check`
        `./scripts/test-full.sh`.

- [x] T035. Record implementation summary and validation evidence in this file
      after implementation is complete.
      - Covers: quality policy completion reporting
      - Include design choice, compatibility impact, behavior changes, files
        changed, tests added/updated, risks, follow-up, and commands run.

## Completion Criteria

- Runtime version alignment is represented by `.p2p/project/runtime.yml`.
- Generated runtime contracts use exact initial compatibility until a separate
  compatibility policy permits broader ranges.
- New projects mark the runtime contract as required in `.p2p/project.yml`.
- The runtime contract declares compatible range and recommended P2P Engine
  version only.
- Managed `P2P-SETUP.md` renders runtime setup guidance from the contract and
  includes a stable P2P-managed marker.
- Ordinary initialization does not recreate a missing required runtime contract
  from the active local runtime.
- `p2p validate` detects runtime contract errors, missing required contracts,
  deterministic legacy-undeclared warnings, managed setup-guide drift, and
  unmarked setup-guide conflicts.
- Runtime status reports compatibility and guidance without mutation.
- Governed writes are gated only when a declared or required runtime contract
  cannot be trusted.
- The governed-write gate is backed by an inventory of public mutating CLI,
  service, and MCP entry points.
- Documentation and generated agent guidance explain the contract-first flow.
- No mandatory script, install manager, reconcile manager, release resolver,
  source selector, digest verifier, automatic installation, automatic
  upgrade/downgrade, or automatic fallback is added.

## Implementation Summary

Implemented outside P2P governance state.

Delivered behavior:

- Added `.p2p/project/runtime.yml` runtime contract model, parser, semantic
  validation, status model, setup-guide renderer, and write preflight.
- New projects now receive exact initial compatibility:
  `requires: "==<active-version>"` and `recommended: "<active-version>"`.
- New projects mark `.p2p/project.yml` with top-level
  `runtime_contract.required: true`.
- New projects receive managed `P2P-SETUP.md` generated from the runtime
  contract.
- Existing projects with required marker and missing `runtime.yml` remain
  `missing_contract`; ordinary initialization does not regenerate the contract
  from the active local runtime.
- `p2p runtime status` and `p2p runtime status --format json` report read-only
  runtime compatibility status.
- `p2p validate` reports deterministic runtime contract findings, including
  `P2P267_RUNTIME_CONTRACT_LEGACY_UNDECLARED` and
  `P2P268_RUNTIME_SETUP_GUIDE_DRIFT`.
- Managed `P2P-SETUP.md` drift is detected by full deterministic rendered
  content comparison, normalizing only newlines.
- Governed writes through `P2PWorkspace` run centralized runtime preflight
  before mutation.
- Generated agent guidance and public docs describe the runtime contract,
  legacy/missing states, and explicit owner boundary for environment mutation.
- MCP runtime status tools remain deferred; existing MCP write handlers are
  covered through the shared `P2PWorkspace` write preflight.

## Validation Evidence

- `git diff --check`
- `.venv/bin/pytest tests/test_runtime_contract_service.py tests/test_runtime_write_gate.py`
- `.venv/bin/pytest tests/test_project_initialization_service.py -k "runtime or initialization"`
- `.venv/bin/pytest tests/test_validation_service.py -k "runtime or valid_refreshed"`
- `.venv/bin/pytest tests/test_cli.py -k "runtime_status or init_status_create"`
- `.venv/bin/pytest tests/test_agent_instructions_service.py -k "refreshes_codex"`
- `.venv/bin/pytest tests/test_project_initialization_service.py tests/test_validation_service.py tests/test_runtime_contract_service.py tests/test_runtime_write_gate.py`
- `.venv/bin/pytest tests/test_cli.py`
- `.venv/bin/pytest tests/test_mcp_project_handler.py tests/test_mcp_proposal_handler.py tests/test_mcp_work_spec_handler.py tests/test_mcp_maintenance_handler.py`
- `.venv/bin/pytest tests/test_agent_instructions_service.py`
- `.venv/bin/pytest tests/test_runtime_contract_service.py` -> 9 passed
- `.venv/bin/pytest tests/test_runtime_contract_service.py tests/test_runtime_write_gate.py` -> 14 passed
- `./scripts/test-full.sh` -> 593 passed
