# Exploration - PROP-060

PROP-060 should remain a small internal maintenance proposal for P2P Engine code coverage diagnostics.

The codebase already has a mature marker-based pytest strategy with focused, public, smoke, and full validation tiers. The missing capability is not test organization and not deterministic test selection. The missing capability is an occasional, terminal-only way for maintainers to inspect which `src/p2p_engine` files and lines are not exercised by a selected test run.

The important design boundary is that code coverage reports observations about executed code after tests have been selected. It must not decide which tests to run after a change. Deterministic test selection belongs to `PROP-098`.

## Hidden Decisions

- Whether coverage should be advisory or blocking: first slice should be advisory.
- Whether coverage should produce durable artifacts: first slice should not create HTML reports or generated coverage artifacts.
- Whether coverage should run on every change: first slice should not change default agent validation behavior.
- Whether coverage applies to user projects: it does not; project evidence coverage is a separate product concern.

## Tradeoff

The preferred approach trades enforcement for low-cost visibility. Maintainers gain a way to find untested modules or branches, especially around refactors, without creating a misleading global quality score or slowing every small change.

The cost is that this proposal will not solve under-selection or over-selection of tests. That is acceptable because `PROP-098` is scoped to deterministic test impact and validation routing.

## Execution Domain

Execution domain is software development maintenance. Expected implementation areas are development dependencies, testing documentation, and verification that existing smoke and focused scripts still pass.
