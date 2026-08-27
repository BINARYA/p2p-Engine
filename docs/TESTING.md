# Testing

This repository keeps the full pytest suite as the final confidence gate, but
uses markers and scripts to make local feedback cheaper during implementation.

## Validation Tiers

Focused validation is for day-to-day implementation:

```bash
./scripts/test-focused.sh
```

By default this runs service, unit, and adapter tests while excluding `slow`
tests. For a narrow change, pass exact pytest targets instead:

```bash
./scripts/test-focused.sh tests/test_readiness_service.py
./scripts/test-focused.sh tests/test_readiness_service.py::test_readiness_service_refresh_and_initialize_scoring
```

Public-contract validation is for externally observed behavior:

```bash
./scripts/test-public.sh
```

Run it when a change can affect CLI output, MCP payloads, persisted contracts,
validation findings, filesystem behavior, generated artifacts, or compatibility
facades.

Smoke validation is a small broad-confidence check:

```bash
./scripts/test-smoke.sh
```

Full validation is the final gate:

```bash
./scripts/test-full.sh
```

Run the full suite before commit, push, release, merge, or after broad
refactors.

## Coverage Diagnostics

Coverage is an optional maintainer diagnostic. It shows which
`src/p2p_engine` files and lines were exercised by a chosen pytest run, but it
does not measure test quality and does not decide which tests are required after
a change. Test impact routing is a separate concern.

Use terminal missing-lines output when coverage visibility is useful, especially
around refactors or newly introduced runtime areas:

```bash
./scripts/test-smoke.sh --cov=src/p2p_engine --cov-report=term-missing
```

For focused diagnostics, keep the focused marker expression explicit:

```bash
.venv/bin/pytest -m "(unit or service or adapter) and not slow" --cov=src/p2p_engine --cov-report=term-missing
```

For broad diagnostics, add coverage options to the full-suite command:

```bash
./scripts/test-full.sh --cov=src/p2p_engine --cov-report=term-missing
```

The first coverage slice is advisory and non-blocking. It intentionally does not
introduce a fail-under threshold, CI gate, HTML report, XML report, or generated
coverage artifact. It also does not assess user project evidence coverage.

## Markers

- `unit`: pure or near-pure behavior with no public CLI/MCP boundary.
- `service`: domain or application service behavior.
- `adapter`: filesystem, serialization, or integration adapter
  behavior.
- `cli`: observable CLI command behavior, output, exit behavior, or side effects.
- `mcp`: observable MCP tool schema, payload, error, or permission behavior.
- `integration`: workflow crossing multiple application boundaries.
- `slow`: materially broader or slower than normal focused feedback.
- `smoke`: minimal broad confidence checks.

Markers are assigned centrally during pytest collection in `tests/conftest.py`.
This keeps test metadata consistent while avoiding mechanical edits across every
test file.

## Useful Pytest Expressions

```bash
.venv/bin/pytest -m "service and not slow"
.venv/bin/pytest -m "unit or adapter"
.venv/bin/pytest -m "cli or mcp"
.venv/bin/pytest -m "smoke"
```

## Test Authoring Policy

Read `specs/skills/TEST_QUALITY_SKILL.md` before adding or reorganizing
non-trivial tests.

The short version:

- add the lowest-layer test that proves the behavior;
- add CLI tests when command behavior or output changes;
- add MCP tests when tool schemas, payloads, permissions, or errors change;
- do not duplicate the same scenario across layers unless each layer has a
  separate contract;
- mark broad, integration, or slow tests explicitly;
- report focused, public-contract, and full-suite validation in implementation
  summaries when relevant.
