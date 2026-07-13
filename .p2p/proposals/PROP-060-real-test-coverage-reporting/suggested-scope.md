# Suggested Scope - PROP-060

## Include

- Add a standard development-only coverage integration such as `pytest-cov`.
- Document a terminal command that reports missing lines for `src/p2p_engine`.
- State that coverage is optional, diagnostic, and non-blocking.
- Preserve existing marker-based validation tiers and scripts.
- Verify that existing smoke and focused validation scripts still pass.

## Exclude

- Deterministic test impact routing.
- User-facing project evidence coverage.
- HTML coverage reports.
- Generated coverage artifacts.
- Initial CI fail-under threshold.
- Mandatory per-change coverage execution.
- Runtime dependencies for P2P Engine users.

## Next Step After Acceptance

Create an implementation Change Set that updates development dependencies and testing documentation, then validates with smoke and focused tests.
