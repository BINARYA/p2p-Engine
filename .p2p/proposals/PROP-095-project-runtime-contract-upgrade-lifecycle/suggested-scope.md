## In scope

- CLI `p2p runtime contract update` or equivalent explicit operation.
- Preview-first behavior.
- Human and JSON preview/result output.
- Validation that `recommended` satisfies `requires`.
- Deterministic impact classification for `==VERSION` and `>=LOWER,<UPPER`.
- Stable labels: `recommended_only`, `range_widening`, `range_tightening`, `runtime_line_change`, `current_runtime_excluded`.
- Valid upgrade, downgrade, range widening, range tightening, and recommended-only updates.
- Owner-role authority plus explicit confirmation.
- Limited write-gate exception for valid current contracts with active-runtime range incompatibility.
- Digest-based stale-preview protection for `runtime.yml` and `P2P-SETUP.md`.
- Managed-error coordinated update of `runtime.yml` and managed `P2P-SETUP.md`, writing `runtime.yml` last.
- Explicit handling for managed aligned, managed drifted, absent, and unmanaged setup guide states.
- No-op result handling.
- Final diagnostic result, including local incompatibility if the active runtime is excluded.
- Update to the PROP-084 write-path inventory.

## Out of scope

- Runtime installation, selection, upgrade, downgrade, or reconciliation.
- Virtualenv creation or mutation.
- Package download, wheel resolution, package index resolution, release availability verification, or source checkout.
- Automatic contract mutation after a local runtime upgrade.
- Invalid-contract repair.
- Unsupported schema migration.
- Missing-contract recovery.
- Legacy contract adoption.
- User-owned setup guide overwrite.
- First-implementation MCP mutation.
- Automatic commit, branch, push, or pull request creation.
- Mandatory P2P proposal/decision for every ordinary runtime contract update.
- Runtime-specific audit file.
