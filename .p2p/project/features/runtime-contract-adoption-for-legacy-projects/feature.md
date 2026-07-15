# Runtime Contract Adoption For Legacy Projects

## Provenance

- Proposal: PROP-097
- Source: .p2p/proposals/PROP-097-runtime-contract-adoption-for-legacy-projects

## Problem

Projects created before the runtime contract feature can remain in
`legacy_undeclared` state. They have no `.p2p/project/runtime.yml` and no
`runtime_contract.required` marker, so `p2p validate` keeps warning that
compatibility cannot be inferred. Manually editing `.p2p` would solve one
repository once, but it would bypass the P2P write boundary and would not
provide a reusable safe path for other legacy projects.

## Proposal

Add a runtime contract adoption primitive for legacy projects, exposed as
`p2p runtime contract adopt` or an equivalent explicit preview/apply pair. The
operation is allowed only when the current runtime state is
`legacy_undeclared`. It requires owner confirmation and proposed values for
`requires` and `recommended`; the CLI may offer exact active-runtime defaults,
but those values must still be visible and explicitly confirmed.

On successful apply, the operation writes `.p2p/project/runtime.yml`, adds
`runtime_contract.required: true` to `.p2p/project.yml`, and generates a managed
`P2P-SETUP.md`. After adoption, `p2p runtime status` should report
`compatible` for the adopted runtime and `p2p validate` should no longer emit
`P2P267_RUNTIME_CONTRACT_LEGACY_UNDECLARED`.

## Decision

# Decision - PROP-097

## Status

`accepted`

## Outcome

accepted

## Reason

Owner accepted runtime contract adoption for legacy projects to close the undeclared contract state without manual .p2p edits.

## Date

2026-07-13

## Approver

owner
