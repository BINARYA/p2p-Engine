# Real Test Coverage Reporting

## Provenance

- Proposal: PROP-060
- Source: .p2p/proposals/PROP-060-real-test-coverage-reporting

## Problem

P2P Engine has a mature marker-based pytest suite, but it still lacks an occasional code coverage diagnostic. Maintainers cannot easily see which runtime modules or branches are never exercised by a chosen validation tier. This is an internal software-maintenance observability gap for P2P Engine itself, not a project-design evidence gap for users designing non-software projects with P2P Engine.

## Proposal

Introduce a small code coverage diagnostic for P2P Engine maintainers. Add pytest-cov, or an equivalent standard integration, as a development dependency and document a terminal missing-lines report for src/p2p_engine. The preferred first command is a simple terminal report such as pytest --cov=src/p2p_engine --cov-report=term-missing, optionally aligned with the existing focused and full validation tiers. The first slice is advisory only: no fail-under threshold, no HTML report, no generated artifact requirement, and no CI gate. Coverage output should be used occasionally, especially before or after refactors or when a new runtime area appears, to identify places where focused tests should be improved.

## Decision

# Decision - PROP-060

## Status

`accepted`

## Outcome

accepted

## Reason

Accepted as Advisory Code Coverage Diagnostics: optional, non-blocking code coverage diagnostics for P2P Engine maintainers. No initial CI gate, fail-under threshold, HTML artifact, default per-change run, test impact routing, or user-facing project evidence coverage is included; deterministic validation routing remains in PROP-098.

## Date

2026-07-13

## Approver

owner
