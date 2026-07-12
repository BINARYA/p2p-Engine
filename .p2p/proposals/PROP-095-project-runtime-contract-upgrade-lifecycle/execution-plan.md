# Execution Plan - PROP-095

## Implementation Sequence

1. Extend the runtime contract domain model with proposed update input, preview
   result, apply result, impact labels, setup-guide state, release availability,
   authority diagnostics, and expected-state token fields.
2. Implement proposed contract validation for the supported grammar:
   `==VERSION` and `>=LOWER,<UPPER`, with PEP 440-compatible version semantics
   and `recommended in requires` enforcement.
3. Add set-based range comparison and stable impact classification for
   `recommended_only`, `range_widening`, `range_tightening`,
   `runtime_line_change`, and `current_runtime_excluded`.
4. Implement current-state trust classification by consuming PROP-084 runtime
   states. Applicable previews are allowed only for valid supported current
   contracts. Invalid, unsupported, missing, and legacy-undeclared states return
   diagnostic-only previews without applicable tokens.
5. Implement setup-guide state classification for missing, managed aligned,
   managed drifted, and unmanaged `P2P-SETUP.md`.
6. Implement deterministic stateless expected-state token generation over the
   versioned token payload: operation id, token format, current contract digest,
   setup-guide state/content digest, marker state, proposed values, reason,
   optional decision, impact algorithm version, and impact labels.
7. Add the read-only `p2p runtime contract preview` command and JSON output. It
   must not mutate project, governance, audit, token, consent, or environment
   state and must not require owner authority.
8. Add the mutating `p2p runtime contract apply` command. It must re-read
   current state, revalidate the proposal, recompute impact and token, verify
   owner authority, enforce explicit confirmation, enforce reason requirements,
   and fail without mutation on any blocker.
9. Implement coordinated write behavior: prepare all content before writing,
   replace managed `P2P-SETUP.md` before replacing `.p2p/project/runtime.yml`,
   write the normative runtime contract last, and avoid broad post-update
   validation or governed mutation after the active runtime becomes incompatible.
10. Integrate release availability as best-effort local diagnostics only.
11. Update CLI and agent documentation to explain preview/apply, no-install
    boundary, token semantics, unmanaged setup-guide blocking, and collaborator
    next actions.
12. Add focused tests at the lowest useful layer: domain classification tests,
    token tests, setup-guide state tests, service preview/apply tests, CLI JSON
    tests, write-order/stale-state tests, and regression tests for no-op and
    active-runtime exclusion behavior.

## Validation Evidence Required

- Unit tests cover proposed contract validation, range classification, token
  determinism, and setup-guide state classification.
- Service tests prove preview is read-only and apply fails before mutation when
  authority, token, confirmation, reason, current state, or setup-guide state is
  invalid.
- CLI tests verify stable human and JSON output for preview, apply success,
  no-op, blocked diagnostics, and stale preview.
- Mutation-order tests prove `P2P-SETUP.md` is replaced before
  `.p2p/project/runtime.yml`, and that no further governed mutation occurs after
  a contract that excludes the active runtime is activated.
- Documentation tests or validation checks confirm the public command names and
  no-install boundary remain consistent across proposal, CLI guide, and agent
  guidance.

## Delivery Boundary

The implementation is complete only when the lifecycle updates the project
runtime contract and managed setup guide safely, without introducing runtime
installation, package resolution, unmanaged guide adoption, MCP mutation,
contract repair, schema migration, missing-contract recovery, Git automation, or
post-update governed side effects.
