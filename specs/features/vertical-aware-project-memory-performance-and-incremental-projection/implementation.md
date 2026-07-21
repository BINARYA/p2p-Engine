# Implementation Evidence - Vertical-Aware Project Memory Performance And Incremental Projection

## Environment

- Git revision at start and final local verification: `8450c0d75d41b12717cfd18f1a54aeb5897731e2` plus the uncommitted feature diff.
- Development runtime: CPython `3.14.4` through `.venv/bin/python`.
- Package version: `0.4.1`.
- Source import: `src/p2p_engine/__init__.py`, asserted by the test and benchmark runners.
- Installed-artifact import: `/tmp/p2p-wheel-smoke-FIIron/venv/lib/python3.14/site-packages/p2p_engine/__init__.py`.
- Declared compatibility floor: Python `3.11`.
- Compatibility runtime: CPython `3.11.15` in the official
  `python:3.11-bookworm` container. The host checkout was mounted read-only and
  copied to container scratch before installation, tests, and builds.

The worktree contained unrelated owner and generated changes before this
feature started. They were preserved. No feature implementation step edited the
current repository `.p2p` workspace directly or through a write command.

## Baseline

The source behavior recorded in `requirements.md` was the comparison baseline:

| Operation | Baseline |
| --- | ---: |
| workspace status | 10.4 s |
| context small | 16.0 s |
| next without supplied context | 14.1 s |
| project progress | 2.2 s |

Profiling showed repeated complete schema/lifecycle scans, vertical-pack work,
registry reconstruction, validation, freshness, readiness, and decision-index
construction inside composite reads. Existing request snapshots reduced only a
subset of those repeated providers.

## Test Commands

- Source focused: `./scripts/test-focused.sh <selection>`
- Source public: `./scripts/test-public.sh -q`
- Source smoke: `./scripts/test-smoke.sh -q`
- Source full: `./scripts/test-full.sh -q`
- Python YAML fallback: `P2P_YAML_FORCE_PYTHON=1 ./scripts/test-full.sh -q`
- Installed smoke: temporary copied environment, local wheel installed with
  `--force-reinstall --no-deps`, then `python -m pytest -q -m smoke` with
  `PYTHONPATH` unset.
- Import proof: `.venv/bin/python scripts/import-provenance.py --expect-source --format json`
- Package: `.venv/bin/python -m build --no-isolation` and
  `.venv/bin/python scripts/verify-release-artifacts.py --version 0.4.1`.

## Slice Evidence

### P - Preparation

Source-test scripts now force `src`, while `scripts/test-installed.sh` keeps an
installed-package path. `scripts/import-provenance.py`, deterministic scale
fixtures, read counters, CLI/MCP benchmark harnesses, byte-digest helpers, and
this evidence set establish reproducible source and installed modes.

### A1 - Read Context And Source Capture

`WorkspaceDocumentStore` captures request-private bytes, physical hashes,
loader-specific parses, and deterministic directory snapshots. A
`WorkspaceReadContext` memoizes providers by arguments, exposes operation
counters, finalizes optimistic consistency, retries once, and rejects a second
revision. Diagnostic reads may observe a lock that was already present and
stable; ordinary reads still reject it.

Evidence: `test_workspace_document_store.py`,
`test_workspace_read_context.py`, `test_fast_read_paths.py`, and decision/readiness
source regressions.

### A2 - Schema And Lifecycle Batch

Schema preflight is separate from complete schema status. Lifecycle aggregation
uses one preflight, one proposal discovery, and at most one ledger parse per
selected proposal. Single lifecycle status delegates to the same semantic
engine, preserving schema v2 and schema v3 behavior.

Structural evidence at 100/1,000/10,000 proposals is exactly one preflight and
N ledger parses.

### A3 - Vertical Batch Processing

Active vertical state, pack, normalized section terms, coverage artifacts, and
heuristic inputs are batchable request snapshots. Authoritative progress does
not compute heuristic evidence by default and keeps definition completeness
separate from declared proposal evidence.

### A4 - Atomic Registry Bundle

Registries now have a versioned manifest, canonical source catalog, physical and
semantic fingerprints, output digests, owned paths, atomic refresh, failure
rollback, fast status, legacy classification, and canonical in-memory fallback.
Same-size/same-count changes are detected without rebuilding semantic records
for a current fast status.

### A5 - Fast Public Reads

Fast, targeted, and deep cost classes constrain providers. Status, proposal
list, progress, small context, and next reuse one request context and avoid
complete validation/freshness. Small context preserves the public
`derived_freshness` key with `verification: fast_checked`; complete freshness
remains explicitly `not_run`.

### A6 - YAML And Deep Paths

Project-owned Python/C safe loaders support arbitrary, mapping, sequence, and
unique-key contracts. Duplicate-key and malformed/multi-document behavior is
covered in both modes. Twenty-six specialized direct YAML calls remain and are
accounted for in `yaml-audit.md`; migration loaders and semantic clone/round-trip
boundaries were intentionally not replaced mechanically.

### B - Vertical Project Memory

The implementation adds immutable versioned contracts and a derived artifact
owned under `.p2p/project/vertical-memory/`. The full builder is deterministic,
vertical-complete, authority-aware, compact, and side-effect free. It separates
active, historical, unmapped, conflict, definition, assumption, question, and
blocker state without importing implementation status or granting authority.

The impact classifier and incremental builder broaden uncertain changes, reuse
validated unaffected section bytes, and produce candidates byte-identical to a
fresh full build. Materialization is atomic, checks source preconditions,
removes stale owned sections, supports rollback/recovery, and treats invalid or
unsupported prior generations as untrusted.

Public CLI/MCP status/show are bounded and read-only. `p2p project refresh`
materializes the derived memory. Supported proposal decisions, coverage,
definition convergence, question convergence, and vertical selection return an
additive derived-update result after canonical commit. Derived failure never
rolls back canonical authority.

### C - Consumer Convergence

Readiness and progress consume a pure snapshot adapted from vertical memory and
retain independent definition/evidence axes. The source fallback and
materialized paths are semantically equal. Readiness gap classification remains
independent of the memory builder, preventing a dependency cycle.

Small context is vertical-first and bounded; proposal-targeted context builds at
most one decision index and adds exact related sections. Next actions consume a
typed `NextActionInputs` snapshot, preserve active Change Sets and remediation
ordering, and add one stable memory-repair action when current structured memory
is unavailable.

Project rendering now organizes current direction by vertical section and
separates historical material, unmapped legacy context, conflicts, assumptions,
questions, blockers, and missing evidence. Rendered state remains derived and
does not imply implementation, governance, readiness, or publication approval.

Affected-section-only readiness reclassification was measured and deferred as
allowed by C1-T007: final readiness classification remains bounded and exact;
incremental vertical-memory generation is unaffected.

### X - Persistence Evaluation

`persistence-evaluation.md` selects `filesystem_sufficient`. Correctness does
not depend on a process cache. Current-workspace persistent reads are well below
the cold CLI results, structural work is linear, and the residual cold misses
are dominated by the approximately 0.84 s process/import floor.

## Public Behavior

- `p2p project memory status [--format text|json]` reports materialization,
  fingerprints, counts, reasons, and refresh guidance.
- `p2p project memory show [--section ID] [--include-history] [--limit N]
  [--cursor TOKEN] [--format text|json]` returns deterministic bounded pages.
- MCP exposes read-only `p2p_project_memory_status` and
  `p2p_project_memory_show` with matching contracts.
- Registry status includes additive manifest/source verification.
- Fast status/context/next payloads identify what was checked and what was not.
- `p2p project refresh` owns project projections and vertical memory without
  changing canonical proposal/decision authority.

## Verification Results

| Gate | Result |
| --- | --- |
| full source suite, C loader | `1332 passed` in 247.21 s |
| full source suite, forced Python loader | `1332 passed` in 413.20 s |
| public CLI/MCP | `262 passed`, 1,070 deselected |
| source smoke | `14 passed`, 1,318 deselected |
| installed wheel smoke | `14 passed`, 1,318 deselected |
| Python 3.11 full source suite | `1331 passed`, one optional-PDF skip, in 399.95 s |
| Python 3.11 wheel/sdist | version `0.4.1`; 238 wheel and 478 sdist members |
| Python 3.11 installed wheel smoke | `14 passed`, 1,318 deselected |
| version/release tests | `11 passed` |
| compile and Python 3.11 grammar | 193 files passed |
| wheel/sdist validation | version `0.4.1`; 238 wheel and 478 sdist members |
| diff whitespace | `git diff --check` passed |

`ruff`, `mypy`, and `pyright` are not installed and no repository configuration
declares them as a gate. No substitute result is claimed.

## Performance Results

Current-workspace cold CLI medians are 1.083 s status, 1.103 s proposal list,
1.070 s registry status, 1.137 s progress, 2.027 s small context, 2.867 s
targeted context, 1.826 s next, 1.918 s validate, and 3.030 s freshness. The
first four narrow misses are accepted under N016 because the fixed-path process
floor is 0.843 s and persistent-process equivalents are substantially faster.

At 10,000 proposals the final rerun measured one schema preflight, 10,000 ledger
parses, 0.217 s coverage, 47.900 s full build, 57.494 s materialization, 6.980 s
materialized load, 25.513 s small context, 46.074 s targeted context, and 24.743
s one-proposal incremental build. N015 explicitly excludes the structural
10,000 fixture from current-project interactive ceilings. Incremental candidates
remained byte-equivalent to full candidates.

## Compatibility And Recovery

- Existing public payload keys and text surfaces are preserved; new fields are
  additive.
- Schema v2 remains readable and schema v3 decision semantics are unchanged.
- Migration lock-protected replanning ignores only transient inspector errors
  caused by its own lock; source hashes still detect real lock-time drift.
- Status/context/next can report stable recovery locks, while ordinary reads and
  governed writes retain lock rejection.
- Registry and vertical-memory readers reject mixed or unsupported generations.
- Canonical fallback writes nothing and never labels stale content current.

## Residual Risks

- Cold startup leaves four current-workspace targets 1.4-10.3% above their
  reference ceilings; lazy CLI imports are a separate possible optimization.
- Very large synthetic context remains linear but non-interactive; aggregate
  serialization is a future evidence-triggered optimization.
- Downstream derived outputs intentionally remain outside the authorized M
  refresh scope: software specs, assessment, maturity, brief/export, managed
  next-action materialization, and publication stages report stale or
  owner-controlled state until their own supported lifecycle commands run.
- `hatchling 1.31.0` and its build dependencies were added only to the local
  `.venv` to execute package verification; P2P Engine itself was not reinstalled
  in the working environment.

## Final Results

The source feature, tests, package artifacts, persistence decision, and scoped
current-repository alignment are complete. Source behavior passed on Python
3.14 and was verified on Python 3.11. The only skipped 3.11 test was the
existing optional PDF render test guarded by `pytest.importorskip("weasyprint")`;
it passed on the host environment where the PDF extra is installed. No release,
commit, push, publication approval, or unrelated derived refresh is implied.

## Repository Alignment Preflight

M1-M3 completed read-only against the current repository using the source
runtime `0.4.1`:

- runtime contract `>=0.4.0,<0.5.0` is compatible;
- workspace schema v3, layout, and semantic alignment are current;
- no migration lock or recovery transaction exists;
- active `software_project` vertical and lock are valid at version `1.0.0`;
- project definition is valid with 16 complete, two partial, and one assumed
  section;
- existing registries are `legacy_unverifiable` because no bundle manifest
  exists;
- vertical project memory is `missing`, making project projections and their
  downstream freshness chain stale;
- no workspace-schema migration is required for the optional derived memory.

The no-write full candidate was byte-invariant over `.p2p` and produced 21
outputs for all 19 vertical sections from 689 selected sources. All 97 active
proposals are accounted for: 14 have declared mappings and 83 remain explicitly
legacy unmapped. There are 79 section contribution occurrences, ten mapped
conflicts, one current project question, and no historical contribution without
explicit section topology. The only aggregate warning is `CONFLICT-001`, which
has no declared vertical section. No candidate discrepancy blocks refresh.

The owner explicitly confirmed both generated writes. `p2p registry refresh`
then created registry manifest version 1 and a current atomic bundle with 102
proposals, 102 decisions, 70 changes, two choices, 140 relations, 2,459
artifacts, and 102 readiness records. Its source fingerprint is
`8957ff3bc338f89c061a22ababe03b5ae067fbab07c81db81f5d418027308932`.

`p2p project refresh` materialized the `software_project` vertical memory and
the existing project projections through their supported writer. The resulting
memory is current at source fingerprint
`c4e21758eaf09a9deecbbfb248f97c93aeddfd7fffe99853eb16a1892b4a3631`,
with all 19 active sections and 20 owned outputs (aggregate plus sections).
There are no changed paths or scopes relative to a fresh candidate. Bounded
show reports 83 legacy unmapped active proposals explicitly and paginates them;
it does not convert heuristic suggestions into declared evidence.

Post-refresh public checks report:

- schema v3 current/aligned and no migration recovery;
- validation clean with zero errors and zero warnings;
- definition completeness 40/43 (93.02%) and declared evidence coverage 13/19
  (68.42%), with two assumptions still to validate;
- three incomplete required-definition gaps, six optional evidence gaps, one
  informational legacy gap, and one currently answerable project question;
- untargeted and `PROP-102` targeted small contexts using current materialized
  vertical memory and current registries;
- stable generated next actions led by revoked-publication-source review and
  the `assumptions` and `decisions` definition gaps;
- publication not approved, source export and downstream publication stages
  stale, and publication review missing by owner control.

Complete freshness is therefore `attention_required`, while its central nodes
are current: canonical sources, decision context, registries, vertical project
memory, and project projections. Remaining stale nodes are documented rather
than silently refreshed: software specs, assessment, brief context/prompt,
maturity, visible export, publication packet/validation/render. Operational
brief, next-action materialization, curated publication, and publication review
remain owner-action surfaces.

Three-run warm-filesystem CLI medians after alignment were 0.849 s check, 1.098
s status, 1.116 s proposal list, 1.094 s registry status, 1.120 s progress,
2.073 s small context, 2.963 s targeted context, 1.832 s next, 1.939 s validate,
and 3.178 s freshness. Relative to the earlier current-workspace baseline, the
largest change is freshness at approximately +4.9%; no material regression was
observed.

Final diff review found no changes under `.p2p/proposals` and no changes to
canonical project definition, coverage, questions, runtime, vertical selection,
or vertical lock. Expected generated changes are confined to the registry
bundle/manifest and project projections/vertical memory. Existing owner changes
to Change Set, software-spec provenance, operational brief, publication output,
and other repository work remain present and were not reverted. `git diff
--check` passes.
