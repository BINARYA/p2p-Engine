# PROP-060 - Real Test Coverage Reporting

## Status

`accepted`

## Problem

P2P Engine has a mature marker-based pytest suite, but it still lacks an occasional code coverage diagnostic. Maintainers cannot easily see which runtime modules or branches are never exercised by a chosen validation tier. This is an internal software-maintenance observability gap for P2P Engine itself, not a project-design evidence gap for users designing non-software projects with P2P Engine.

## Context

Code coverage, test impact routing, and project evidence coverage are separate concerns. PROP-060 is limited to code coverage diagnostics for P2P Engine maintainers. PROP-098 owns deterministic test impact and validation routing. Future project evidence coverage for user projects, such as checking whether a packaging design has enough evidence for materials, logistics, risk, and acceptance criteria, is also a separate product concern.

## Goals

- Add optional, non-blocking code coverage observability for P2P Engine runtime code.
- Use terminal coverage output to identify internal modules or branches that need better focused tests.
- Keep coverage separate from deterministic test routing, project evidence coverage, and release gating.

## Non-Goals

- Do not implement test impact routing in this proposal; that belongs to PROP-098.
- Do not measure project-design completeness or evidence coverage for P2P Engine user projects.
- Do not introduce HTML coverage reports, generated coverage artifacts, or an initial CI fail-under gate.
- Do not run coverage after every small code change as the default agent behavior.

## Proposal

Introduce a small code coverage diagnostic for P2P Engine maintainers. Add pytest-cov, or an equivalent standard integration, as a development dependency and document a terminal missing-lines report for src/p2p_engine. The preferred first command is a simple terminal report such as pytest --cov=src/p2p_engine --cov-report=term-missing, optionally aligned with the existing focused and full validation tiers. The first slice is advisory only: no fail-under threshold, no HTML report, no generated artifact requirement, and no CI gate. Coverage output should be used occasionally, especially before or after refactors or when a new runtime area appears, to identify places where focused tests should be improved.

## Acceptance Criteria

- pytest accepts the chosen coverage options locally through the development dependency.
- A documented terminal command produces a missing-lines coverage report for src/p2p_engine.
- The documentation states that coverage is diagnostic, optional, and non-blocking in the first slice.
- No initial fail-under threshold, HTML report, generated coverage artifact, or CI gate is introduced.
- The proposal explicitly points test impact routing to PROP-098 and does not claim to solve validation selection.
- Existing smoke and focused validation scripts continue to pass.

## Decision

Pending.
