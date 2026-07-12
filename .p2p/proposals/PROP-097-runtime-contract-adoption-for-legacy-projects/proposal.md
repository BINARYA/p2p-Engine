# PROP-097 - Runtime Contract Adoption For Legacy Projects

## Status

`accepted`

## Problem

Projects created before the runtime contract feature can remain in
`legacy_undeclared` state. They have no `.p2p/project/runtime.yml` and no
`runtime_contract.required` marker, so `p2p validate` keeps warning that
compatibility cannot be inferred. Manually editing `.p2p` would solve one
repository once, but it would bypass the P2P write boundary and would not
provide a reusable safe path for other legacy projects.

## Context

PROP-084 introduced a minimal runtime contract for new projects and made
`legacy_undeclared` a non-blocking warning for older projects. PROP-095 added a
governed update lifecycle, but deliberately does not apply when the current
state is untrusted or undeclared. The missing capability is therefore adoption:
turning a legacy project into a declared contract project through a supported
owner-controlled command.

## Goals

- Provide an explicit owner-controlled adoption lifecycle for
  `legacy_undeclared` projects.
- Create the initial `.p2p/project/runtime.yml`, the
  `runtime_contract.required: true` marker, and a managed `P2P-SETUP.md`.
- Keep adoption separate from runtime installation, upgrade, package download,
  environment reconciliation, and contract update.
- Make the operation previewable, confirmable, testable, and repeatable for
  this repository and other legacy projects.

## Non-Goals

- Do not install, upgrade, downgrade, or select a P2P Engine runtime.
- Do not recover a missing required contract; recovery remains distinct from
  adoption.
- Do not repair invalid or unsupported contracts.
- Do not overwrite an unmanaged human-owned `P2P-SETUP.md` implicitly.
- Do not make `p2p init` a recovery or adoption shortcut.

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

## Alternatives

- Manual one-time repair: fast for this repository, but violates the normal P2P
  write boundary and leaves no reusable command for other legacy projects.
- Reuse `p2p init`: rejected because initialization must not regenerate or
  infer runtime contracts for existing projects.
- Extend PROP-095 apply to `legacy_undeclared`: rejected because update and
  adoption have different trust assumptions and write sets.
- Do nothing: preserves the warning forever and weakens the usefulness of the
  runtime contract model on older repositories.

## Impacts

- CLI: add a narrow adoption command or preview/apply pair under
  `p2p runtime contract`.
- Storage: write `.p2p/project/runtime.yml`, update `.p2p/project.yml`, and
  create managed `P2P-SETUP.md`.
- Validation: legacy warning disappears after successful adoption and normal
  runtime status/preflight behavior applies.
- MCP: no mutation parity is required in the first implementation; future MCP
  parity should be consent-gated if added.
- Documentation: installation and agent guidance should describe adoption as
  distinct from installation and update.

## Risks

- The owner could adopt the wrong version if defaults are hidden. Mitigation:
  require explicit displayed `requires` and `recommended` values plus
  confirmation.
- Adoption could overwrite human setup notes. Mitigation: unmanaged
  `P2P-SETUP.md` blocks adoption unless a separate future adoption/replacement
  workflow is introduced.
- The command could blur adoption and recovery. Mitigation: allow only
  `legacy_undeclared`; keep `missing_contract`, invalid, and unsupported states
  blocked.

## Open Questions

- Should the first implementation be a single `adopt` command or a separate
  `adopt preview` / `adopt apply` pair matching PROP-095?
- Should adoption require a structured `--reason`, or is owner confirmation
  enough for exact active-runtime adoption?
- Should MCP parity be explicitly deferred or should a consent-gated MCP tool be
  included later?

## Acceptance Criteria

- A `legacy_undeclared` project can adopt a runtime contract through a supported
  CLI primitive.
- Adoption writes `.p2p/project/runtime.yml`, adds
  `runtime_contract.required: true`, and creates a managed `P2P-SETUP.md`.
- `p2p runtime status` reports `compatible` after adopting the active runtime.
- `p2p validate` no longer reports
  `P2P267_RUNTIME_CONTRACT_LEGACY_UNDECLARED`.
- Adoption is blocked for `missing_contract`, invalid, unsupported, and already
  declared projects.
- An unmanaged `P2P-SETUP.md` is not overwritten implicitly.
- No runtime installation, package resolution, network operation, Git
  automation, or environment mutation is performed.

## Decision

Pending.
