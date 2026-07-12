# Clarifications

## Core Problem

PROP-084 addresses runtime version alignment for a cloned, copied, or extracted
P2P-managed project. The question is: which P2P Engine runtime should a
collaborator install or verify for this project?

The answer is a minimal project-local runtime contract plus project-local setup
guidance. The answer is not install automation.

## Runtime Contract Is Required

`.p2p/project/runtime.yml` remains the authoritative project-local declaration
of required P2P Engine compatibility. It records:

- contract schema version;
- compatible P2P Engine range;
- recommended P2P Engine runtime version.

It does not record release tags, wheel filenames, SHA-256 digests, source
descriptors, arbitrary URLs, repository coordinates, or installation commands.
Those fields belong to installer and release-integrity workflows, not to the
runtime alignment contract.

## Project-Local Setup Guidance

A collaborator who clones a project may not know P2P internals. New projects
should therefore include a project-root `P2P-SETUP.md` generated from
`runtime.yml`.

`P2P-SETUP.md` is a human and agent-facing view, not the source of truth. It
must point back to `.p2p/project/runtime.yml`, show the compatible range and
recommended runtime version, link or refer to existing installation guidance,
and tell users to run `p2p runtime status` after installation.

## Bootstrap Script Is Not Required

A mandatory bootstrap script is not required to solve runtime version alignment.
A generated helper script may be considered later as a separate ergonomic
feature, but it is not part of this proposal's required solution and must not
become a second source of truth.

## Install Manager Is Out Of Scope

This proposal does not add a runtime install, reconcile, upgrade, downgrade,
replacement, source-switch, virtualenv, resolver, download, or package
installation manager.

P2P may diagnose and explain a mismatch when it is available, but it must not
mutate the local environment.

## Contract-Aware Write Gate

PROP-084 should not introduce broad command blocking across all commands.
Read-only inspection, status, context, and validation remain available.

The required enforcement is narrower: governed writes must fail before mutation
when a project declares or requires a runtime contract and that contract is
incompatible, invalid, unsupported, or required but missing.

Existing projects without a marker requiring `runtime.yml` are
`legacy_undeclared`; compatibility must not be inferred from local package
state, but they remain warning-only for this proposal.

The gate is guaranteed by runtimes that implement PROP-084. Older runtimes that
do not know the contract may ignore it unless a separate project-format marker
causes them to reject the project.

## Missing Contract Versus Legacy

`legacy_undeclared` means no runtime contract exists and no project-level marker
requires one.

`missing_contract` means a project-level marker or format policy says a runtime
contract is required, but `.p2p/project/runtime.yml` is absent.

Without that external marker, a missing file must be treated as
`legacy_undeclared`, not `missing_contract`.

## Ownership Boundaries

PROP-084 owns the runtime contract, `P2P-SETUP.md`, runtime status,
validation findings, generated guidance, and the governed-write gate policy.

PROP-078 owns project-local installation mechanics.

PROP-080 owns release artifact publication and release integrity metadata.
PROP-084 may refer to official installation documentation, but it does not
depend on release wheel metadata to create or validate the runtime contract.
