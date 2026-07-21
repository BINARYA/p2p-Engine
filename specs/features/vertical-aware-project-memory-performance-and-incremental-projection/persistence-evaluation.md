# Persistence Evaluation

## Outcome

`filesystem_sufficient`

The correctness and structural-complexity gates pass without a database or a
process-persistent cache. Four cold-process reference ceilings are missed by
1.4-10.3% on this run, but the measured floor for starting the CLI and executing
the fixed-path `check` command is already 0.84 seconds. Persistent MCP results
show that the remaining workspace operations are substantially below the same
targets. A persistent index would not remove Python and CLI import startup, so
these misses are accepted under the N016 platform-tolerance rule rather than
used to justify SQLite.

## Provenance

| Field | Value |
| --- | --- |
| Git revision at measurement | `8450c0d75d41b12717cfd18f1a54aeb5897731e2` plus the uncommitted feature diff |
| Package version | `0.4.1` |
| Module | `/home/davide/dati/60_lavoro/060_p2p_engine/src/p2p_engine/__init__.py` |
| Python executable | `/usr/bin/python3.14` through `.venv/bin/python` |
| Python | CPython 3.14.4 |
| Import mode | source checkout, enforced by each harness |
| Process cache | empty per CLI sample; request-private for MCP |
| Filesystem cache | warm filesystem |

The source-tree check was
`env PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 .venv/bin/python
scripts/import-provenance.py --expect-source --format json`.

## Environment

| Field | Value |
| --- | --- |
| Host | `davide-MA14250` |
| OS/kernel | Ubuntu Linux, `7.0.0-27-generic`, x86_64 |
| CPU | Intel Core Ultra 7 265H, 16 logical CPUs, 0.4-5.3 GHz |
| Memory | approximately 61 GiB |
| Filesystem | ext4 on NVMe (`/dev/nvme0n1p6`) |

Python 3.11 is not installed on the host. Compatibility was verified separately
with CPython 3.11.15 in the official `python:3.11-bookworm` container against a
read-only host checkout copied into container scratch.

## Datasets And Artifacts

The current-workspace benchmark used a disposable copy at
`/tmp/p2p-vertical-memory-benchmark`. The copy was refreshed only through the
source CLI. The repository's current `.p2p` was not written.

| Dataset | Proposals | Source files/records | Derived output |
| --- | ---: | ---: | ---: |
| disposable current workspace | 102 | 3,016 files; 1,418 YAML files; 7,254,187 logical bytes | registry bundle 973,810 bytes; vertical memory 21 files/1,506,464 bytes |
| deterministic small | 100 | 439 vertical-memory sources | 21 files/241,028 bytes |
| deterministic medium | 1,000 | 3,139 vertical-memory sources | 21 files/1,689,143 bytes |
| deterministic structural | 10,000 | 30,139 vertical-memory sources | 21 files/16,333,958 bytes |

The deterministic builder supports schema v2 compatibility reads, schema v3
multi-event ledgers, mixed lifecycle states, declared and unmapped coverage,
choices, conflicts, Change Sets, questions, and reversed enumeration.

## Cold CLI Results

Command:

```text
env PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 .venv/bin/python \
  scripts/benchmark-read-paths.py \
  --root /tmp/p2p-vertical-memory-benchmark --mode cli --runs 3
```

Each sample starts a separate CLI process. Values are seconds.

| Operation | Median | p95 | Reference | Result |
| --- | ---: | ---: | ---: | --- |
| check | 0.843 | 0.854 | diagnostic floor | measured |
| status | 1.083 | 1.101 | <1.0 | tolerated +8.3% |
| proposal list | 1.103 | 1.111 | <1.0 | tolerated +10.3% |
| decision status | 0.847 | 0.864 | targeted | pass |
| registry status | 1.070 | 1.072 | <1.0 | tolerated +7.0% |
| registry show | 1.112 | 1.126 | informational | measured |
| memory status | 1.001 | 1.035 | informational | measured |
| memory show | 1.087 | 1.095 | informational | measured |
| project progress | 1.137 | 1.145 | <2.0 | pass |
| context small | 2.027 | 2.034 | <2.0 | tolerated +1.4% |
| targeted context small | 2.867 | 2.887 | <3.0 | pass |
| next top 3 | 1.826 | 1.930 | <2.0 | pass |
| validate | 1.918 | 1.928 | <5.0 | pass |
| project freshness | 3.030 | 3.032 | <5.0 | pass |

The dominant residual for the narrow operations is process startup and import,
not data access. Before the final relative-path optimization, proposal list was
1.23 seconds; the source catalog and consistency scan improvement reduced it to
1.10 seconds without weakening source fingerprint checks.

## Persistent MCP Results

Command:

```text
env PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 .venv/bin/python \
  scripts/benchmark-mcp-read-paths.py \
  --root /tmp/p2p-vertical-memory-benchmark --runs 3 --workers 2
```

| Operation | First | Steady median | Steady p95 |
| --- | ---: | ---: | ---: |
| context small | 1.186 | 1.155 | 1.157 |
| targeted context | 2.021 | 1.987 | 2.020 |
| next top 3 | 0.849 | 1.061 | 1.064 |
| project progress | 0.285 | 0.282 | 0.283 |
| registry status | 0.213 | 0.205 | 0.217 |
| memory status | 0.159 | 0.158 | 0.159 |
| memory show | 0.236 | 0.233 | 0.234 |

Two concurrent context reads completed successfully in 7.41 seconds total. This
is CPU-bound Python work and is slower under thread contention, but correctness
does not depend on a shared process cache. A source mutation between payload
construction and read-context finalization caused exactly one retry: two
attempts, 2.30 seconds, and a current second result. A stale proposal mutation
caused canonical fallback and a 4.95-5.41 second next context read, as intended.

## Structural Scale Results

Command:

```text
env PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 .venv/bin/python \
  scripts/benchmark-project-memory-scale.py
```

| Proposals | Lifecycle | Preflights | Ledger parses | Coverage | Full build | Materialize | Load | One-proposal incremental |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 100 | 0.045 s | 1 | 100 | 0.004 s | 0.403 s | 0.942 s | 0.117 s | 0.392 s |
| 1,000 | 0.920 s | 1 | 1,000 | 0.044 s | 5.430 s | 7.318 s | 0.773 s | 2.668 s |
| 10,000 | 9.171 s | 1 | 10,000 | 0.322 s | 56.963 s | 68.189 s | 8.887 s | 26.818 s |

Every incremental candidate was byte-equivalent to a full build after the same
mutation. Proposal processing, ledger parsing, artifact bytes, and build time
grow linearly. The 10,000-proposal incremental case remains intentionally
non-interactive because aggregate output and source fingerprints must still be
rebuilt; it does not affect materialized read latency at current scale.

The benchmark was extended to include both context modes. Separate deterministic
runs measured:

| Proposals | Context small | Targeted context |
| ---: | ---: | ---: |
| 100 | 0.363 s | 0.633 s |
| 1,000 | 3.129 s | 5.261 s |
| 10,000 | 25.513 s | 46.074 s |

The final 10,000 rerun also measured 6.527 s lifecycle, exactly one preflight
and 10,000 ledger parses, 0.217 s coverage, 47.900 s full build, 57.494 s
materialization, 6.980 s materialized load, and 24.743 s one-proposal
incremental work. The incremental candidate remained byte-equivalent to a fresh
full candidate. N015 explicitly excludes this structural fixture from the
current-project interactive ceilings; the measurements are retained as a
linear-growth baseline rather than hidden behind a relaxed target.

## Peak Memory

`tracemalloc` was enabled for separate 100 and 1,000 proposal runs. It adds
substantial timing overhead, so those timings are not used as performance gates.

| Operation | 100 proposals | 1,000 proposals | Growth |
| --- | ---: | ---: | ---: |
| lifecycle batch | 1.08 MB | 10.53 MB | 9.7x |
| coverage batch | 0.23 MB | 1.82 MB | 7.9x |
| full build | 4.01 MB | 26.90 MB | 6.7x |
| materialize | 3.73 MB | 26.60 MB | 7.1x |
| materialized load | 2.94 MB | 20.39 MB | 6.9x |
| one-proposal incremental | 3.05 MB | 20.96 MB | 6.9x |

Memory and output therefore grow linearly or better over this range.

## Operation Counts And Correctness Gates

- One schema preflight is used for each lifecycle aggregation.
- At most one ledger is parsed per selected proposal.
- The active vertical pack is loaded once per request key.
- Authoritative progress does not compute heuristic coverage.
- Fast status, context, next, list, and progress do not invoke complete
  validation or complete freshness.
- Full and incremental vertical-memory candidates are byte-equivalent.
- Reversed enumeration is byte-invariant.
- Registry and vertical-memory mixed generations are rejected.
- Same-count and same-size canonical changes are detected by physical hashes.
- Read-context finalization retries one concurrent revision and rejects a second.
- Materialized state is optional; missing, stale, invalid, and unsupported
  states use canonical fallback or return an explicit unavailable diagnostic.

## Bottleneck Attribution

| Area | Evidence | Decision |
| --- | --- | --- |
| cold CLI startup | fixed-path check is 0.84 s; persistent operations are much faster | optimize import topology separately only if cold CLI startup becomes a product priority |
| current workspace file reads | registry 0.20 s and memory status 0.16 s in persistent process | sufficient |
| YAML parsing | validate 1.92 s and Python/C parity passes | sufficient |
| source discovery | linear at 100/1,000/10,000 after relative-path optimization | sufficient |
| vertical full build | 0.40 s at 100, 56.96 s at 10,000 | sufficient for explicit rebuild; not an ordinary read |
| one-proposal incremental | 0.39 s at 100, 26.82 s at 10,000 | acceptable at current scale; aggregate recomputation is a future optimization candidate |
| concurrent MCP reads | successful but CPU-bound under Python threads | monitor; no correctness or current-scale latency need for a database |
| post-mutation fallback | 4.95-5.41 s until explicit refresh | expected safe fallback; post-commit hooks minimize its frequency |

## Persistence Decision

File-backed canonical state plus versioned atomic read models is sufficient for
the current product and measured scale. No SQLite, database package, persistent
cache directory, cache migration, cleanup command, daemon, or cache-dependent
correctness was added.

Potential future work remains evidence-triggered:

- reduce cold CLI imports through command-module lazy loading;
- reduce large-scale incremental aggregate serialization while retaining byte
  equivalence and atomic manifests;
- evaluate a persistent index only if concurrent server workloads or much
  larger real workspaces make source hashing or bounded retrieval the measured
  bottleneck.

None of those items blocks this feature or changes the selected outcome.

## Package And Suite Verification

- Full source suite with the C loader: `1332 passed` in 247.21 seconds.
- Full source suite with forced Python fallback: `1332 passed` in 413.20 seconds.
- Public CLI/MCP suite: `262 passed`.
- Local wheel/sdist `0.4.1`: 238 wheel members and 478 sdist members validated.
- Installed wheel smoke in a temporary copied environment: `14 passed`, with
  `p2p_engine` imported from temporary `site-packages` and no `PYTHONPATH=src`.
- Python 3.11.15 full source suite: `1331 passed`, with one expected skip for
  optional `weasyprint`; Python 3.11 wheel/sdist verification and installed
  wheel smoke (`14 passed`) also passed.
