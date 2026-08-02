# Implementation Note - Portable Vertical Resolution Convergence 0.4.5

## Status

Implemented and verified for version `0.4.5` on 2026-08-02. This corrective
feature closes the exact-resolution conformance gap recorded after the `0.4.4`
delivery of `PROP-103`.

## Delivered

- Exact portable-coordinate lookup that preserves publisher, hyphenated ID and
  semantic version without legacy normalization.
- Exact-first bare-ID lookup with explicit
  `P2P_VERTICAL_AMBIGUOUS_REFERENCE` failure for multiple portable versions.
- Detection of conflicting source copies through
  `P2P_VERTICAL_COORDINATE_CONFLICT`, while equivalent copies retain existing
  source precedence.
- One lock-aware active-pack resolver shared by sections, definition, context,
  readiness, coverage and workspace validation.
- Fail-closed active, lock and definition identity checks for ID, coordinate,
  version and semantic checksum drift.
- Complete candidate identity validation before governed vertical writes.
- Schema-v2 canonical directory validation through the same portable
  inheritance rules used for `.p2pv` archives.
- Stable JSON error envelopes for corrected machine-facing show failures.
- Version metadata, installation documentation, CLI guide and primitive
  inventory updated to `0.4.5`.

## Requirement Evidence

- R001-R007: hyphenated IDs, exact coordinates, side-by-side versions,
  equivalent copies, conflicting copies and legacy precedence are covered by
  `tests/test_portable_verticals.py` and the unchanged
  `tests/test_project_verticals.py` compatibility matrix.
- R008-R013: immediate post-init/adopt/migrate reads, active/lock drift,
  definition drift, readiness and workspace validation are covered by the
  portable convergence tests.
- R014-R018: candidate rejection before write, stale preview, confirmation,
  rollback and complete post-operation state are covered by portable lifecycle
  and existing atomic vertical mutation tests.
- R019-R022: exact inherited schema-v2 directory/archive validation, stable CLI
  errors and read-only failure behavior are covered by CLI and service tests.
- AC008: existing MCP list, context, sections and definition reads are exercised
  against a hyphenated exact portable vertical with a no-mutation assertion.

## Validation Evidence

- Corrective service, CLI and MCP selection: `55 passed`, `63 deselected`.
- Public CLI/MCP suite: `269 passed`, `1203 deselected`.
- Focused repository gate: `1142 passed`, `3 skipped`, `326 deselected`.
- Full repository suite: `1468 passed`, `3 skipped`; the final CLI-only
  regression addition then passed its targeted three-test run.
- Wheel and sdist build: `p2p_engine-0.4.5-py3-none-any.whl` and
  `p2p_engine-0.4.5.tar.gz` created successfully.
- Release artifact verification: version `0.4.5`, wheel `244` files, sdist
  `496` files.
- Final rebuilt-wheel smoke in an isolated install: `4 passed`, `18 deselected`.

## Compatibility And Boundary

No persisted-state migration, remote registry access or new MCP mutation tool
was added. Existing schema-v1 and bundled-pack precedence remains compatible.
WaveKit continues to own catalog access, authorization, artifact download and
delivery; P2P Engine receives local immutable artifacts plus expected
checksums and governs their project-local lifecycle.

## Deviations

No requirement or ownership-boundary deviation was introduced. The resolver
implementation was centralized in `ProjectVerticalService`; no change was
needed in the public portable storage schema or MCP catalog.
