# Execution Plan - PROP-084

## Implementation Slices

1. Define the project runtime contract schema for
   `.p2p/project/runtime.yml`.
   The schema records contract version, compatible runtime range, and
   recommended P2P Engine runtime version.

2. Add a runtime contract service that can read, normalize, and validate the
   contract.
   The service reports structured states such as `compatible`,
   `incompatible`, `invalid_contract`, `unsupported_contract`,
   `missing_contract`, and `legacy_undeclared`.

3. Extend project initialization so new projects receive both
   `.p2p/project/runtime.yml` and project-root `P2P-SETUP.md`.
   Repeated initialization must preserve existing files unless an explicit
   refresh path is implemented.

4. Add `p2p runtime status` with human-readable and machine-readable output.
   The command explains active runtime version, declared compatibility range,
   recommended version, contract validity, and next human action.

5. Extend validation so `p2p validate` reports runtime contract shape and
   semantic errors.
   Validation does not access the network, install packages, or mutate
   runtime environments.

6. Add a contract-aware governed-write gate.
   Read-only commands remain available. Governed writes fail before mutation
   when a declared or required runtime contract is incompatible, invalid,
   unsupported, or required but missing. `legacy_undeclared` projects remain
   warning-only.

7. Update public documentation, project-local setup guidance, and generated
   agent guidance.
   The guidance explains how to read the contract, install the recommended
   version through existing official installation instructions, verify
   compatibility, and handle `legacy_undeclared` projects.

## Explicitly Removed From This Scope

- Mandatory bootstrap script.
- Runtime install manager.
- Runtime reconcile manager.
- Automatic install, upgrade, downgrade, replacement, or source switch.
- Virtualenv or package resolver lifecycle.
- Release tag, wheel filename, digest, source descriptor, or repository-local
  wheel fields in the required runtime contract.
- Automatic repository-local wheel fallback.
- Broad command blocking outside governed writes.
- Release workflow changes for wheel metadata.
- MCP mutation tools.

## Validation Plan

- Unit tests cover contract parsing, schema validation, version relationships,
  status values, and finding codes.
- Service tests cover runtime status output for compatible, incompatible,
  invalid, unsupported, missing, and legacy contracts.
- Initialization tests prove runtime contract and `P2P-SETUP.md` creation and
  idempotent preservation.
- Validation tests cover semantic runtime contract findings.
- Write-gate tests prove legacy projects remain warning-only while incompatible
  or invalid declared contracts block governed writes before mutation.
- CLI tests cover `p2p runtime status` text and JSON output.
- Documentation and generated-instruction tests cover stable, agent-facing
  guidance.

## Acceptance Evidence

- `.p2p/project/runtime.yml` is the source of truth for runtime version
  alignment.
- The project declares both a compatible runtime range and a recommended
  P2P Engine runtime version.
- Project-root `P2P-SETUP.md` renders the contract for humans and agents.
- Humans and agents can determine which P2P Engine version to install from
  project-local data and documentation.
- Installed P2P runtimes can diagnose whether they match the project contract.
- Governed writes are blocked before mutation only when a declared or required
  runtime contract is incompatible, invalid, unsupported, or missing under a
  declared policy.
- The implementation does not add a mandatory bootstrap script, install
  manager, release resolver, source selector, digest verifier, or automatic
  fallback.
