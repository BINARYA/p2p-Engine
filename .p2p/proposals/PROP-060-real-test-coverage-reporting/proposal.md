# PROP-060 - Real Test Coverage Reporting

## Status

`draft`

## Problem

The test suite passes, but the project does not currently report real coverage. Without coverage visibility, it is hard to know which core areas are under-tested and whether refactoring or new features are protected.

## Context

The project has many tests and currently passes the suite, but coverage metrics are not part of the normal verification workflow. Adding coverage reporting should improve confidence without changing runtime behavior.

## Goals

- Add real test coverage reporting for the P2P Engine codebase.
- Identify coverage gaps in core lifecycle areas.
- Define an initial coverage target and reporting command.

## Non-Goals

- Do not rewrite tests broadly in this proposal.
- Do not block development on a high coverage threshold immediately.

## Proposal

Introduce pytest coverage reporting, likely via pytest-cov, and document a standard command such as python -m pytest --cov=src/p2p_engine tests/. Use the first report to identify gaps in proposal lifecycle, governance decisions, Change Sets, Work lifecycle, validation, assessment, MCP tools, and file I/O resilience. Define an initial target after measuring the baseline.

## Acceptance Criteria

- Coverage tooling is selected and documented.
- A coverage command can be run locally.
- The baseline coverage percentage is recorded.
- Priority coverage gaps are listed for future work.

## Decision

Pending.
