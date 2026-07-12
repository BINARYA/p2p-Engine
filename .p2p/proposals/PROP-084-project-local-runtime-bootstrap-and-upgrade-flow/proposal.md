# PROP-084 - Project-Local Runtime Bootstrap And Upgrade Flow

## Status

`accepted_with_changes`

## Problem

A shared P2P-managed project must declare which P2P Engine runtime version is expected after clone, copy, or archive extraction. The problem is runtime version alignment: a human or agent must be able to determine the compatible runtime range and the recommended runtime version from project-local data, without relying on chat history, local machine state, Git history, or a separate P2P Engine source checkout.

## Context

This amendment applies the third owner review of PROP-084. The runtime contract remains necessary, but it must not carry installer-specific data. Wheel filenames, release tags, digests, source descriptors, package resolution, and environment mutation belong to release and installation concerns outside this proposal. PROP-084 is narrowed to a minimal project-local runtime contract, project-local setup guidance, read-only diagnostics, validation, and a contract-aware gate for governed writes when a declared contract is incompatible, invalid, unsupported, or required but missing. Legacy projects without a contract remain warning-only so existing repositories are not disrupted.

## Goals

- Define .p2p/project/runtime.yml as the authoritative project-local declaration of P2P Engine runtime compatibility.
- Record a compatible runtime range and one recommended P2P Engine runtime version, without release source descriptors, wheel filenames, or digests.
- Generate project-local setup guidance, such as P2P-SETUP.md, so a collaborator who cloned or copied a project can find the required runtime information without knowing P2P internals.
- Provide read-only runtime status diagnostics and validation findings that tell humans and agents whether the installed runtime matches the project contract.
- Block governed writes only when a project declares or requires a runtime contract and the contract is incompatible, invalid, unsupported, or missing under that declared policy.
- Keep ownership boundaries clear: PROP-084 owns runtime contract, setup guidance, diagnostics, validation, and write-gate policy; PROP-078 owns installation mechanics; PROP-080 owns release artifact publication and integrity metadata.

## Non-Goals

- Do not make a mandatory bootstrap script central to the proposal.
- Do not add an install, reconcile, upgrade, downgrade, replacement, source-switch, virtualenv, package-resolution, or download manager in this scope.
- Do not put release tags, wheel filenames, SHA-256 digests, source descriptors, arbitrary URLs, arbitrary repositories, PyPI resolution, mirrors, source checkout installs, editable installs, or offline wheel behavior in the required runtime contract.
- Do not block legacy projects solely because they lack runtime.yml; report legacy_undeclared with guidance instead.
- Do not add broad command blocking across all commands; enforcement is limited to governed writes when a declared or required contract cannot be trusted.
- Do not make Git required for P2P Core or introduce separate runtime-contract formats for standalone, local Git, and remote Git contexts.

## Proposal

Refocus PROP-084 on a minimal Project Runtime Contract and Runtime Version Alignment. Each P2P-managed project may declare .p2p/project/runtime.yml with a schema version, a compatible P2P Engine range, and a recommended P2P Engine runtime version. The contract tells a collaborator which runtime is expected and gives an installed runtime enough information to verify compatibility. New projects should receive both runtime.yml and a project-local P2P-SETUP.md that renders the same facts for humans and agents. When P2P Engine is available, runtime status reports compatible, incompatible, invalid_contract, unsupported_contract, missing_contract, or legacy_undeclared states with actionable guidance. Projects without any marker requiring runtime.yml are legacy_undeclared and warning-only. Projects that declare or require a runtime contract but are incompatible, invalid, unsupported, or missing the required contract must block governed writes before mutation. The proposal does not require a bootstrap script, does not add an install manager, does not perform runtime mutation, and does not depend on release wheel metadata.

## Acceptance Criteria

- A P2P project can declare .p2p/project/runtime.yml with schema version, compatible runtime range, and recommended P2P Engine runtime version.
- New project initialization creates runtime.yml and project-local P2P-SETUP.md using the active runtime version and configured compatibility policy, while preserving existing files during idempotent initialization.
- Runtime status can report declared requirements, current runtime version, compatibility verdict, and actionable guidance without mutating project state or the runtime environment.
- Runtime contract validation rejects unsupported schema versions, missing required fields, invalid version strings, and recommended-version/range mismatches.
- missing_contract and legacy_undeclared are distinct: legacy projects without a marker requiring runtime.yml remain warning-only, while projects that require runtime.yml but lack it report missing_contract.
- Governed writes are blocked before mutation when a declared or required runtime contract is incompatible, invalid, unsupported, or missing; legacy_undeclared projects are not blocked solely by absence of runtime.yml.
- Public and project-local documentation explain how a collaborator reads the contract, installs the recommended P2P Engine version through existing installation guidance, and verifies with runtime status.
- The implementation does not add a mandatory bootstrap script, install manager, reconcile manager, automatic installation, automatic upgrade, automatic downgrade, release resolver, digest verifier, source selector, or automatic offline fallback.
- PROP-084 records that release wheel publication and digest metadata remain owned by PROP-080, and project-local installation mechanics remain owned by PROP-078, but neither is a blocking dependency for creating the runtime contract.

## Decision

Pending.
