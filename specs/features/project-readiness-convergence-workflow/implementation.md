# Implementation Evidence - Project Readiness Convergence Workflow

## Delivery Identity

- Source proposal: `PROP-101`, accepted.
- Change Set: `CHANGE-069`.
- Governed software spec: `.p2p/outputs/software-spec/CHANGE-069`.
- Local feature spec: `specs/features/project-readiness-convergence-workflow`.
- Owner-approved package version: `0.3.0`.
- Workspace support target: inspect and operate valid v1 where the operation is
  v1-safe; plan/apply v0->v1 and v1->v2; operate v2 fully; reject writes to a
  workspace ahead of the runtime.

## Baseline

| Evidence | Result |
| --- | --- |
| Git baseline | Existing feature specs untracked; no pre-existing source/test changes |
| Workspace schema | v1, upgradeable under runtime 0.3.0 after transitional contract adoption |
| P2P validation | 0 errors, 0 warnings |
| Full test suite | `841 passed in 150.99s` |
| Existing migration path | `workspace-legacy-to-v1` only |
| Existing readiness surface | CLI/MCP `project readiness review` only |

## Live Traceability Matrix

This matrix is updated at every slice exit. `G-T008` and `F-T002` consolidate
it; they are not its creation point.

| Requirement scope | Design coverage | Task coverage | Planned test/evidence | Current evidence |
| --- | --- | --- | --- | --- |
| R-F1-001..015 | Snapshot, gap identity/priority, source budget, pagination | S1-T001..016, S8-T002..003 | project readiness core/service, vertical regression, scale/access tests | S1 complete: 53 focused tests; 174 extended CLI/service tests |
| R-F2-001..020 | schema constants/status, transition protocol, operation gate | S2A-T001..008, S2B-T001..016 | workspace schema/compatibility/migration/facade tests | complete: adjacent handler dispatch, candidate overlay, ownership and fail-closed operation coverage |
| R-F3-001..020 | question artifact, identity, validation, v1->v2 mapping | S3-T001..022 | project-question state, initialization, migration/recovery tests | complete: strict nested validation, schema-last migration, repeated local ids, ambiguous mapping and rollback fixtures |
| R-F4-001..022 | selection, answer contracts, lifecycle, authority | S4-T001..019 | core transition tables, permission and state service tests | complete: all fallback kinds, no-safe outcome, owner lifecycle, triggers and byte invariants |
| R-F5-001..018 | pure definition candidate, preview, atomic multi-target apply | S5-T001..017 | definition, preview, transaction/failure-injection tests | complete: two-target preview/apply, non-target preconditions, under-lock validator and every replacement rollback |
| R-F6-001..014 | exact replay, concurrency, vertical reconciliation | S6-T001..017 | replay, two-process and vertical drift tests | complete: exact replay/mismatch, audit-clock metamorphism, one-commit concurrency, target/alias/module reconciliation |
| R-F7-001..017 | next, progress, freshness and decision-context adapters | S7-T001..017 | focused consumer/source/topology/retrieval tests | complete: concrete actions, residual counts, explicit freshness impact and inactive question traceability without definition double-count |
| R-F8-001..015 | CLI, bounded JSON/text, MCP reads, diagnostics | S8-T001..020 | CLI, MCP catalog/handler/registry and help/docs tests | complete: CLI writes, bounded read parity, safe answer files, stable diagnostics and explicit MCP write absence |
| R-F9-001..034 | release, environment provenance, restart-safe repository migration and artifact alignment | G, D1, M1, A1, F | build/smoke/published-artifact/pilot/process/alignment/full validation evidence | G complete; D1 commit/push complete but tag/release/published-artifact selection pending; M1/A1 remain gated |
| N001..N020 | module boundaries, compatibility, atomicity, determinism, scale | P, S1..S8, G | architecture review plus focused/public/full suites | release-candidate gate complete: public 252; full 943; repository validation clean except expected upgrade info |
| E001..E036 | malformed, stale, concurrent, release, migration and alignment edges | S1..S8, D1, M1, A1 | table, failure-injection, fixture, artifact and pilot tests | engine edge cases complete; release/pilot/alignment cases pending |
| AC001..AC055 | all feature and rollout acceptance gates | G-T001..015, D1, M1, A1, F | requirement-specific evidence plus final suites and restart/environment provenance | engine evidence complete; rollout evidence pending |

## P Gate Evidence

| Task | Evidence |
| --- | --- |
| P-T001 | Accepted proposal, local feature and related architecture inspected |
| P-T002 | `CHANGE-069` created through `p2p change create` |
| P-T003 | Lifecycle preflight has no blockers/advisories; governed spec refreshed |
| P-T004 | Candidate 0.3.0 and v0/v1/v2 support policy recorded above |
| P-T005 | Facade write-operation inventory started from `_ensure_runtime_write_allowed` callers |
| P-T006 | Current schema/status/registry/planner baseline inspected |
| P-T007 | Existing readiness CLI/MCP and repository 100-proposal shape inspected |
| P-T008 | Existing definition patch operations and callers inventoried for S3/S5 |
| P-T009 | Preview and atomic-writer callers inventoried before optional API extension |
| P-T010 | Freshness owners and outputs inventoried for S7/A1 |
| P-T011 | MCP reads included; project-question/convergence writes deferred |
| P-T012 | Test ownership is assigned per slice in the live matrix |
| P-T013 | Focused/public/full commands and this live matrix initialized |
| P-T014 | Baseline full suite is clean: 841 tests |
| P-T015 | No unresolved persistence, authority, compatibility or public-contract decision blocks S1 |

## Implementation Notes

- Keep `P2PWorkspace` as a delegating facade.
- Keep all readiness snapshots request-scoped.
- Preserve schema-v1 behavior until the explicit migration step.
- Do not add MCP writes in this feature.
- Do not migrate this repository or align generated artifacts while engine
  implementation slices are incomplete.
- Before the `0.3.0` source-version bump, preview/apply an owner-approved
  transitional runtime contract that permits both the installed `0.2.x` line
  and the candidate `0.3.x` line. After schema-v2 migration, narrow the contract
  to `>=0.3.0,<0.4.0` so a v1-only runtime cannot appear compatible.
- Do not mark a slice complete until its matrix row points to direct tests and
  observed results.

## Slice Evidence

### S1 - Snapshot, Typed Gaps And Bounded Review

- Added immutable snapshot, typed gap, priority, cursor/page and diagnostic
  contracts.
- Added request-scoped source capture with one-read caching and explicit access
  counts.
- Added stable `PGAP-*` identities with full-digest collision rejection.
- Refactored the existing readiness review to consume the new result while
  preserving section/missing/question semantics and reporting truncation.
- Added default/max page limits, snapshot-bound cursors and a 64 KiB payload
  ceiling.
- Proved classification and pagination perform no read after snapshot creation.
- Focused result: `53 passed in 16.76s`.
- Extended S1 public/service result: `174 passed in 77.50s`.

### S2A-S3 - Workspace Schema And Project-Question Authority

- Extracted both adjacent migration planners into registered handlers and
  composed them generically through `CandidateWorkspaceView`.
- Added schema-v2 status and operation-level compatibility without globally
  blocking valid schema-v1 workspaces.
- Added strict project-question persistence, fresh-v2 initialization and
  schema-last v1-to-v2 migration with exact rollback/recovery behavior.
- Latest migration/schema focused result: `51 passed in 19.00s`; subsequent
  parser/migration regression result: `53 passed in 27.50s`.

### S4-S6 - Lifecycle, Convergence And Reconciliation

- Added declared/multi-target/fallback/no-safe question selection and complete
  owner lifecycle with deterministic deferred triggers.
- Added pure definition candidates and one atomic definition/question apply,
  source-bound previews, exact replay and divergent-token rejection.
- Added explicit target/alias/module reconciliation, terminal revision
  reactivation, no answer copying and a two-process one-commit assertion.
- Focused convergence/transaction/lifecycle result: `41 passed in 12.82s`;
  expanded critical regression result: `53 passed in 27.50s`.

### S7-S8 - Consumers And Public Surfaces

- Integrated concrete readiness actions, descriptive residual question counts,
  source-specific freshness and project-question decision-context metadata.
- Corrected project-definition extraction so applied values receive active
  semantic authority exactly once while question trace records stay inactive.
- Added dedicated CLI and MCP readiness modules, safe structured answer input,
  stable JSON errors, bounded parity and no MCP mutation tools.
- Public gate: `252 passed, 689 deselected in 110.62s`.

### G - Engine Gate

- `git diff --check`: clean.
- Version/import consistency: `15 passed in 0.61s`.
- Engine-gate public result before release refinements: `252 passed, 689
  deselected in 110.62s`.
- Engine-gate full result before release refinements: `941 passed in 221.67s`.
- Repository `p2p validate`: 0 errors, 0 warnings, one expected
  `P2P308_WORKSPACE_SCHEMA_UPGRADE_AVAILABLE` info.
- Registry refresh completed through CLI; status is current at 101 proposals,
  101 decisions, 69 changes, 2 choices, 138 relations, 2,325 artifacts and 101
  readiness records.
- Migration recovery is clear and no mutation lock/transaction is active.
- Owner confirmed release `0.3.0`, actor `mrjungle`, transitional contract
  `>=0.2.0,<0.4.0` and final post-v2 contract `>=0.3.0,<0.4.0`.
- Governed runtime preview returned token
  `runtime-contract-update-v1:8b45e9045a3f81ea2629b9b5776a4edee691ae0ef42285f1ad8bc955bbc4bdf4`;
  owner-confirmed apply updated `.p2p/project/runtime.yml` and regenerated
  `P2P-SETUP.md`.
- Post-apply runtime status is compatible on `0.2.0`; repository validation is
  0 errors, 0 warnings and the expected schema-v2 upgrade info.

### D1 - Runtime Build And Deployment

- Source/package/MCP version is `0.3.0` and the owner-approved transitional
  repository contract remains `>=0.2.0,<0.4.0`, recommended `0.3.0`.
- Transition metadata keeps legacy-to-v1 on `>=0.2.0,<0.4.0` and restricts
  v1-to-v2 inspect/plan/apply to `>=0.3.0,<0.4.0`; a direct matrix regression
  test prevents the `0.2.x` line from advertising v2 support.
- Version/schema/compatibility focused result: `46 passed in 15.49s`.
- Runtime status under source `0.3.0` is compatible and repository schema v1 is
  `upgrade_available`, aligned and free of migration recovery state.
- Initial sdist inspection found repository `.p2p` state and derived `outputs`;
  Hatch exclusions now remove governed/local/derived roots and the release
  workflow runs `scripts/verify-release-artifacts.py` as a permanent gate.
- An intermediate clean rebuild produced a 184-file wheel and 738-file sdist. The verifier
  confirmed required readiness/question/migration modules, vertical resources,
  version metadata and absence of forbidden roots/cache/bytecode.
- Final candidate checksums are captured after the post-suite rebuild below;
  delivery specs are excluded from sdist to avoid checksum self-reference.
- Installed the exact wheel into isolated
  `/tmp/p2p-engine-0.3.0-smoke-eRZLtd/venv`; import resolves from its
  `site-packages`, reports `0.3.0`, and both CLI and MCP entry points load.
- Minimal fresh init creates schema v2, exact runtime contract `==0.3.0` and an
  empty valid project-question collection. After registry refresh, validation
  reports 0 errors, 0 warnings and 0 infos. A separate software-vertical init
  correctly materializes 14 applicable unanswered questions.
- A copied 101-proposal schema-v1 fixture remained valid and accepted a v1-safe
  registry refresh; a question defer was blocked without mutation by
  `P2P348_WORKSPACE_OPERATION_SCHEMA_REQUIRED`.
- Two v1-to-v2 plans produced fingerprint
  `ced57c2c45f15df4fe172e001cb6d65398517fc53d06e42501499db1470be40e`,
  no owner inputs and only question/schema canonical targets. Apply completed,
  recovery cleared, validation became clean, one applicable section question
  remained unanswered and exact retry returned `no_op` with no changed paths.
- The release smoke exposed and fixed an ahead-layout gate gap: write
  compatibility now requires a current/upgradeable layout, while schema-
  independent legacy operations remain available. Source and installed-wheel
  fixtures prove schema v2 ahead blocks even a normally v1-safe write.
- Rollback policy is explicit: after schema v2, deploy only a v2-compatible
  corrective runtime; never downgrade to `0.2.x`.
- Final release-candidate public gate: `252 passed, 691 deselected in 113.93s`.
- Final release-candidate full gate: `943 passed in 220.21s`.
- Repository validation remains 0 errors, 0 warnings and the expected
  `P2P308_WORKSPACE_SCHEMA_UPGRADE_AVAILABLE` info.
- Final verified artifacts: 184-file wheel
  `dist/p2p_engine-0.3.0-py3-none-any.whl` with SHA-256
  `1b72fb4f6053ec18a2ec7e679f28a53e71837a4aef01c5d06412a17fe98acc46`;
  392-file sdist `dist/p2p_engine-0.3.0.tar.gz` with SHA-256
  `511cd9389d2ed3ac4227ea4b8fda990dcbe6215ff88a796dfc0f80a01737475a`.

### D1 Restart Audit And Operational Refinement

- Commit `ea55fa6` is present on synchronized `main`/`origin/main`; the worktree
  was clean at the restart audit. No local `v0.3.0` tag, published release,
  active release/migration process, migration lock or recovery transaction was
  present, so tag publication and M1 remain incomplete rather than failed or
  implicitly completed.
- The system and development `.venv` both use Python `3.14.4`; Python 3.11 was
  not installed or used locally. The release workflow intentionally targets
  Python 3.11 as the declared minimum-support gate; the published wheel must be
  smoke-tested separately on local Python 3.14.
- The development environment is editable. Import resolves from
  `src/p2p_engine`, reports `0.3.0` and provides current behavior, while
  `pip show p2p-engine` still reports historical metadata `0.1.9`. This is an
  explicit environment advisory, not evidence of a runtime downgrade; no
  reinstall or interpreter change was performed or is authorized implicitly.
- The prior isolated `/tmp/p2p-engine-0.3.0-smoke-eRZLtd` environment was
  disposable and was absent after interruption. Its local-wheel results remain
  development evidence only. D1/M1 must recreate an isolated environment from
  the downloaded published wheel and bind the pilot to that artifact's URL and
  SHA-256.
- Current repository state before D1 completion remains schema v1
  `upgrade_available`, semantically aligned and recovery-free. Validation has
  0 errors/0 warnings; registries, project projections, request-scoped decision
  context and agent integrations are current.
- The pre-migration freshness graph reports assessment, brief prompt,
  maturity/progress, aggregate software specs, visible export and deterministic
  publication stages stale. Operational brief, next actions, curated
  publication and publication review require agent/owner action. These are the
  observed A1 baseline classes, not authorization for a blanket rebuild.
- The remaining rollout now has explicit checkpoints for immutable tag/release,
  Python 3.11 CI, published-asset verification, Python 3.14 isolated smoke,
  scratch evidence, plan digest binding, foreground apply completion and
  selective per-owner artifact reconciliation.
