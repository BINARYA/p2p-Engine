# Tasks - Project Readiness Convergence Workflow

## Source And Task-State Rule

- Source: accepted `PROP-101`.
- Specification state: prepared for implementation planning.
- All tasks are unchecked because no implementation evidence for this feature
  exists yet.
- A task may be checked only with direct evidence from code, tests, CLI/MCP
  behavior, migration output, build output or an owner-controlled result.
- Creating these files does not authorize implementation, release, workspace
  migration, artifact refresh, publication or Git publication.

## Stable Delivery Order

```text
P
-> S1
-> S2A
-> S2B
-> S3
-> S4
-> S5
-> S6
-> S7
-> S8
-> G
-> D1
-> M1
-> A1
-> F
```

- `P`: governed delivery/pre-implementation baseline.
- `S1`: immutable snapshot, gaps and bounded review.
- `S2A`: structural extraction of existing migration handler.
- `S2B`: schema v2 status, operation gate and handler dispatch.
- `S3`: project-question artifact and v1-to-v2 migration.
- `S4`: question selection, lifecycle and authority.
- `S5`: atomic convergence preview/apply.
- `S6`: retry, concurrency and vertical reconciliation.
- `S7`: next, progress, freshness and decision context.
- `S8`: CLI, MCP reads, diagnostics and docs.
- `G`: engine completion gate.
- `D1`: runtime build/release deployment.
- `M1`: this repository v1-to-v2 pilot.
- `A1`: evidence-based artifact alignment.
- `F`: final comparison and handoff.

Do not begin `M1` before `D1` proves the exact v2-capable runtime artifact is
available. Do not begin alignment writes before `A1` produces the read-only
classification. Do not run curated or owner stages merely because a
deterministic dependency is stale.

## Requirement Coverage

| Slice | Primary requirements |
| --- | --- |
| P | origin/delivery state, N001-N020 |
| S1 | R-F1-001..015, R-F8-001..002, N012-N015 |
| S2A | R-F2-005..009, N005 |
| S2B | R-F2-001..020, operation compatibility |
| S3 | R-F3-001..020, fresh v2 and migration |
| S4 | R-F4-001..022, lifecycle and authority |
| S5 | R-F5-001..018, atomic apply |
| S6 | R-F6-001..014, replay/concurrency/reconcile |
| S7 | R-F7-001..017, derived consumers |
| S8 | R-F8-001..015, CLI/MCP/diagnostics |
| G | AC001-AC034, engine quality/readiness |
| D1 | R-F9-001..006, R-F9-024..028, AC035-AC037, AC047-AC049, AC054 |
| M1 | R-F9-007..012, R-F9-026, R-F9-028..033, AC038-AC040, AC048-AC052 |
| A1 | R-F9-013..021, R-F9-034, AC041-AC045, AC053 |
| F | R-F9-022..034, AC046-AC055 |

## Implementation Rules

- Follow `AGENTS-p2p-dev-specs.md`,
  `specs/skills/ENGINEERING_QUALITY_SKILL.md` and
  `specs/skills/TEST_QUALITY_SKILL.md`.
- Keep `P2PWorkspace` as delegation only.
- Keep domain/ranking/authority logic out of CLI and MCP handlers.
- Extract existing behavior before changing it when a slice mixes structure and
  behavior.
- Use `apply_patch` for manual source/spec edits.
- Never edit `.p2p` by hand; use supported `p2p` primitives.
- Test at the lowest useful layer; add CLI/MCP tests only for their distinct
  public contracts.
- Use injected roots, clocks, failure points and access counters.
- Preserve v1-safe public behavior unless a requirement explicitly changes it.
- Stop and record a missing primitive instead of performing manual repair.
- Record focused commands and results in the later implementation evidence
  file; do not put execution status into the accepted proposal.

## Traceability Maintenance Warning

> **Implementation warning:** `G-T008` and `F-T002` are final consolidation
> gates, not the first point at which the complete requirement -> design ->
> task -> test/evidence matrix is created. Initialize the matrix during `P` and
> update it as part of every slice exit gate. A slice is not complete while its
> implemented requirements, design decisions, tasks or test evidence remain
> unmapped.

The matrix may live in the later local `implementation.md` or another explicitly
declared non-canonical implementation-evidence file. It must remain reviewable
throughout implementation and must not be reconstructed only at `G` or `F`.

## P - Governed Delivery And Baseline

- [x] P-T001: Re-read accepted `PROP-101`, this feature and related specs for
  workspace migration, vertical/definition state, proposal questions,
  decision-context index and managed next actions; completion is a written
  implementation boundary with no unresolved owner-policy conflict.
- [x] P-T002: Create or identify the Change Set sourced from `PROP-101` through
  `p2p change create` or the applicable existing Change Set; completion is a
  governed Change Set id without manual `.p2p` edits.
- [x] P-T003: Run `p2p spec lifecycle --intent implementation_spec --change
  <CHANGE-ID>`; completion is a non-blocked lifecycle result or an explicit stop
  with diagnostics.
- [x] P-T004: Record the target package/runtime version and the exact runtime
  ranges for inspecting/planning/applying workspace v0->v1 and v1->v2;
  completion is one reviewed compatibility matrix used by code/docs/tests.
- [x] P-T005: Inventory every operation id passed to the current governed-write
  preflight; completion is a versioned operation list with current owning facade
  and minimum schema behavior.
- [x] P-T006: Inventory current workspace status values, transition registry
  entries, legacy plan operations, candidate ownership and validation codes;
  completion is a baseline fixture/golden summary.
- [x] P-T007: Capture current `project readiness review` text output, current MCP
  payload and the 100-proposal source-access baseline; completion is golden
  compatibility evidence.
- [x] P-T008: Inventory current project-definition patch operations and identify
  every caller of `add_open_question` and `close_open_question`; completion is a
  v1/v2 compatibility disposition for each caller.
- [x] P-T009: Inventory mutation-preview and atomic-writer callers before API
  extension; completion is a compatibility checklist proving optional
  parameters can preserve existing tokens/results.
- [x] P-T010: Inventory freshness node source ownership and outputs, especially
  registries, project projections, next actions, briefs, decision context,
  software specs and publication; completion is an initial source-impact map.
- [x] P-T011: Confirm MCP decision: update shared reads, add bounded read tools,
  add no write tool; completion is the decision copied into Change Set/software
  spec and public docs plan.
- [x] P-T012: Create planned test files/fixtures and markers without production
  behavior; completion is importable empty/scaffolded test ownership or a
  documented decision to add each file with its slice.
- [x] P-T013: Define focused commands for S1-S8 and broad commands
  `./scripts/test-public.sh -q` and `./scripts/test-full.sh -q`; completion is a
  live requirement -> design -> task -> planned test/evidence matrix mapped to
  changed contracts, initialized before S1 and maintained at every slice exit.
- [x] P-T014: Run baseline `p2p validate` and full suite before behavior changes;
  completion is recorded clean evidence or an explicitly separated pre-existing
  failure.
- [x] P-T015: P exit gate. Confirm no more than two unresolved technical design
  questions remain and none affects persistence, authority, compatibility or
  public behavior; otherwise stop and update design before S1.

## S1 - Snapshot, Typed Gaps And Bounded Review

- [x] S1-T001: Add `core/project_readiness.py` enums/dataclasses for gap kind,
  severity, diagnostic, result, page, cursor and policy versions; completion is
  deterministic JSON-ready serialization tests for R-F1-005..010.
- [x] S1-T002: Implement stable `PGAP-*` identity/full-digest collision checks;
  completion is unit coverage proving wording/order/time/root changes do not
  change identity.
- [x] S1-T003: Implement the six-class priority tuple and neutral assumption
  dependency fallback; completion is table tests for every class and tie-break.
- [x] S1-T004: Add a request-scoped snapshot builder that captures schema,
  vertical/lock, definition, question state if available, permissions, proposal
  summaries and declared coverage from the same bytes; completion is a typed
  immutable snapshot.
- [x] S1-T005: Add injected source-access counting and enforce one discovery and
  one read/hash/parse per included source; completion is deterministic access
  assertions on small and 100-proposal fixtures.
- [x] S1-T006: Prove no source read occurs during gap classification, sorting,
  pagination or serialization after snapshot construction.
- [x] S1-T007: Implement typed integrity, compatibility, authority,
  answered-not-applied, definition, assumption, evidence and legacy gaps;
  completion is focused service tests for every class and next operation.
- [x] S1-T008: Preserve declared and heuristic evidence in separate fields and
  add regression proving heuristic-only coverage never increases declared
  progress.
- [x] S1-T009: Implement bounded page/cursor core with default 20, max 100,
  review top 10 and 64 KiB default structured payload budget; completion is page
  and payload limit tests.
- [x] S1-T010: Implement cursor checksum, collection/policy/snapshot/last-key
  binding and stale/corrupt diagnostics; completion is round-trip and source
  drift tests.
- [x] S1-T011: Refactor `ProjectVerticalService.project_readiness_review()` to
  consume the gap/snapshot service while preserving section/missing/question/
  next semantics; completion is existing readiness tests plus new bounded tests.
- [x] S1-T012: Keep service snapshots request-scoped behind `P2PWorkspace` thin
  delegation; completion is a same-workspace source-change regression proving
  no stale memoized snapshot.
- [x] S1-T013: Add read-only byte-invariant tests for review/gaps/detail/cursor
  operations.
- [x] S1-T014: Add 100-proposal scale fixture with 88+ unmapped items and long
  heuristic lists; completion is access/payload budgets without wall-clock-only
  assertions.
- [x] S1-T015: Run focused project readiness, vertical, progress and snapshot
  tests.
- [x] S1-T016: S1 exit gate. Confirm deterministic typed gaps, bounded output,
  independent evidence and zero read-only mutation before schema changes.

## S2A - Extract Existing Legacy Migration Handler Without Behavior Drift

- [x] S2A-T001: Add transition handler/fragment contracts without changing the
  default registry path or candidates; completion is registry serialization and
  validation tests.
- [x] S2A-T002: Move existing domain/permission/metadata/vertical/bootstrap plan
  logic from `WorkspaceCompatibilityService` into
  `LegacyUndeclaredToV1Handler` without semantic edits.
- [x] S2A-T003: Keep inventory, owner-input normalization and final plan
  fingerprint orchestration in `WorkspaceCompatibilityService`; completion is a
  clear responsibility boundary with no duplicate planning logic.
- [x] S2A-T004: Make the registry resolve handler instances and validate one
  adjacent handler per source version, unique id/capabilities/dependencies and
  path to current schema 1.
- [x] S2A-T005: Enforce handler candidate target ownership and reject a handler
  that writes an undeclared path.
- [x] S2A-T006: Compare pre/post legacy plan operations, semantic candidate
  hashes, owner-input findings and source-access counts on golden fixtures;
  completion is exact or explicitly audit-neutral equivalence.
- [x] S2A-T007: Run existing workspace schema, compatibility, migration, CLI and
  MCP plan tests before adding schema v2.
- [x] S2A-T008: S2A exit gate. Confirm v0->v1 plan/apply/recovery public behavior
  and byte restoration did not drift.

## S2B - Workspace Schema V2, Handler Dispatch And Operation Gate

- [x] S2B-T001: Set current workspace schema target to 2 and add versioned
  upgradeable layout/status constants without changing the envelope contract
  unless tests prove a required change.
- [x] S2B-T002: Extend schema parsing/status so v0, upgradeable v1, current v2,
  ahead, invalid, incomplete and recovery-required are distinguishable.
- [x] S2B-T003: Make `migration_required` operation-aware while keeping valid v1
  aligned for v1-safe reads/writes.
- [x] S2B-T004: Add runtime support matrix for v0->v1 and v1->v2 to registry,
  status, CLI/MCP payloads and docs constants.
- [x] S2B-T005: Implement candidate-overlay handler composition for multi-step
  v0->v1->v2 plans; completion is a test proving the second handler reads first
  handler candidates, never stale physical sources.
- [x] S2B-T006: Add `workspace_operation_compatibility.py` with explicit
  min/max-schema requirement records and structured preflight results.
- [x] S2B-T007: Populate the operation registry from P-T005; completion is every
  existing governed write classified as v1-safe or explicitly version-limited.
- [x] S2B-T008: Integrate runtime, migration lock/recovery and schema requirement
  checks in one facade/service preflight without domain logic in
  `P2PWorkspace`.
- [x] S2B-T009: Fail unknown write operation ids closed and add a test that
  adding an unclassified operation breaks validation/contract coverage.
- [x] S2B-T010: Add v1-only maximum-schema entries for legacy definition
  add/close-open-question operations.
- [x] S2B-T011: Add v2 minimum-schema entries for project-question/convergence
  mutations and typed read capability diagnostics on v1.
- [x] S2B-T012: Extend schema status/doctor/context/next summaries additively with
  upgradeable state and exact plan command.
- [x] S2B-T013: Add old-runtime/new-workspace ahead tests and explicit no
  downgrade tests.
- [x] S2B-T014: Add read-only status/plan byte-invariant tests for v1 and v2.
- [x] S2B-T015: Run focused workspace schema, compatibility, operation gate,
  status, doctor, context, CLI and MCP read tests.
- [x] S2B-T016: S2B exit gate. Confirm v1-safe writes remain available, v2-only
  writes fail before mutation and multi-step planning is handler-owned.

## S3 - Project-Question Artifact And V1-To-V2 Migration

- [x] S3-T001: Add `core/project_questions.py` typed states, targets, answer
  contracts, revisions, answers, transitions, applications, groups and artifact
  result types.
- [x] S3-T002: Implement deterministic `PRQ-*`/`PRG-*` identity and full-digest
  collision validation independent from wording, lock, time and root.
- [x] S3-T003: Implement strict `.p2p/project/questions.yml` parser/serializer,
  schema version 1 and audit-neutral semantic payload.
- [x] S3-T004: Add `ProjectQuestionStateService` with injected root, vertical,
  permissions, clock and atomic writer; completion is no direct scattered write.
- [x] S3-T005: Add global validation for v2 question artifact presence/schema,
  unique identity, refs, lifecycle, applications and lock/applicability state.
- [x] S3-T006: Add v2 validation requiring every definition `open_questions`
  list empty; preserve v1 behavior before migration.
- [x] S3-T007: Extend fresh project initialization to create an empty project-
  question artifact and commit schema v2 last.
- [x] S3-T008: Extend vertical question parsing with optional target/answer
  contract metadata while preserving every existing vertical fixture.
- [x] S3-T009: Implement deterministic legacy mapping for section-local ids,
  declared question match, target binding and migrated provenance.
- [x] S3-T010: Implement owner-input binding parser for ambiguous legacy targets;
  prove it cannot contain an answer or lifecycle outcome.
- [x] S3-T011: Generate declared/fallback/no-safe outcomes for incomplete
  required sections with no legacy question; exclude complete/not-applicable.
- [x] S3-T012: Implement one-to-one source-question preservation validation and
  blocking diagnostics for duplicate/unknown/conflicting mappings.
- [x] S3-T013: Implement `WorkspaceV1ToV2ProjectQuestionsHandler` owning only
  question artifact, definition normalization and workspace schema/history.
- [x] S3-T014: Add registry metadata/capabilities/runtime requirements for
  `workspace-v1-to-v2` and update contiguous history validation.
- [x] S3-T015: Ensure migration candidate empties definition open questions in
  the same transaction and schema target is ordered last.
- [x] S3-T016: Add v1-to-v2 fixtures: no open questions, repeated local ids,
  unambiguous/ambiguous fields, missing section, invalid status, current repo
  shape and 100 proposals.
- [x] S3-T017: Add multi-step v0->v1->v2 candidate/validation/apply fixture.
- [x] S3-T018: Add failure injection before staging, candidate validation and
  each target replacement; completion is exact rollback or recovery evidence.
- [x] S3-T019: Add idempotent post-migration no-op, rollback, resume, external
  edit and two-process lock tests.
- [x] S3-T020: Add CLI/MCP status/plan tests proving v1-to-v2 details are
  visible and planning is mutation-free.
- [x] S3-T021: Run focused project question schema, initialization, validation,
  migration, transaction, CLI and MCP plan tests.
- [x] S3-T022: S3 exit gate. Confirm every valid legacy question is preserved
  exactly once, no owner state is invented and v2 has one authority.

## S4 - Question Selection, Lifecycle And Owner Authority

- [x] S4-T001: Implement declared-question selection against the active locked
  vertical and answer-contract binding metadata.
- [x] S4-T002: Implement unambiguous legacy binding for exactly one safe target;
  return no-safe instead of first-field guessing when multiple targets exist.
- [x] S4-T003: Implement deterministic fallback templates for field value,
  section disposition, assumption resolution and blocker resolution.
- [x] S4-T004: Prove fallback uses no LLM, decision-context inference, heuristic
  proposal content or unversioned text matching.
- [x] S4-T005: Persist only applicable declared/fallback questions; expose
  `no_safe_question` as a gap diagnostic without invented content.
- [x] S4-T006: Implement the steady-state transition matrix and audited reopen
  event with expected-revision checks.
- [x] S4-T007: Resolve owner authority from `PermissionsService`; reject actor or
  source text that does not resolve to owner role.
- [x] S4-T008: Implement direct owner answer for scalar and structured safe input
  with answer-contract validation and provided-by/recorded-by derivation.
- [x] S4-T009: Implement explicit answer replacement preserving prior answer and
  requiring expected question revision.
- [x] S4-T010: Implement owner defer/mute/reopen with mandatory reason,
  provenance, time and residual gap.
- [x] S4-T011: Implement declared deferred trigger evaluation as versioned
  deterministic data; malformed/absent triggers never reopen automatically.
- [x] S4-T012: Keep muted questions excluded from automatic next selection.
- [x] S4-T013: Keep applied/retired/superseded revisions terminal and create new
  gaps rather than rewriting history.
- [x] S4-T014: Write question lifecycle changes through atomic single-target
  mutation with source precondition and migration-lock preflight.
- [x] S4-T015: Add byte-invariant tests for failed contract, authority, revision
  and transition checks.
- [x] S4-T016: Add next-question ordering tests across class, section priority,
  deferred/muted and no-safe conditions.
- [x] S4-T017: Add temporary-root service tests for all states and answer
  contracts; avoid duplicating CLI tests for domain rules.
- [x] S4-T018: Run focused question selection, lifecycle, permissions and state
  persistence tests.
- [x] S4-T019: S4 exit gate. Confirm no non-owner can create owner evidence and
  an answer alone never changes definition/progress truth.

## S5 - Definition Candidate And Atomic Convergence Apply

- [x] S5-T001: Add typed `ProjectDefinitionCandidate` and extract pure candidate
  rendering/validation from current definition patch apply without public drift.
- [x] S5-T002: Make existing definition preview/apply reuse the extracted
  renderer; completion is all current definition tests unchanged or intentionally
  updated only for v2 operation gating.
- [x] S5-T003: Implement answer-contract to allowlisted definition-operation
  mapping with conflict detection for multiple selected questions.
- [x] S5-T004: Require explicit answered question ids and eligible revisions for
  convergence preview; no implicit all-answer selection.
- [x] S5-T005: Render definition and question candidates from one immutable
  snapshot and validate cross-artifact application references.
- [x] S5-T006: Extend `MutationPreviewService` with optional token context so
  convergence binds actor/questions/schema/lock/permissions/policies without
  changing existing caller tokens.
- [x] S5-T007: Extend `AtomicMutationWriter` to validate non-target source
  preconditions under lock while preserving existing target-only callers.
- [x] S5-T008: Add optional under-lock candidate validator over
  `CandidateWorkspaceView`; keep generic transaction code domain-agnostic.
- [x] S5-T009: Include semantic diff, before/candidate hashes, affected gaps,
  progress effect and freshness plan in preview result.
- [x] S5-T010: Implement owner-confirmed apply with same question ids, actor,
  token and confirmation; reject changed inputs before replacement.
- [x] S5-T011: Commit definition and question state in one multi-target writer
  call and prohibit sequential use of definition apply.
- [x] S5-T012: Record application token, operation, actor, question revisions and
  semantic candidate hashes in the committed question candidate.
- [x] S5-T013: Return final changed paths/hashes and deterministic rebuild plan
  without executing refreshes.
- [x] S5-T014: Add failure injection before/after journal, source recheck,
  validator and every replacement; prove no partial applied state.
- [x] S5-T015: Add permission/schema/lock/question/definition stale preview tests
  and exact no-write assertions.
- [x] S5-T016: Run focused definition, preview, transaction, convergence and
  recovery tests.
- [x] S5-T017: S5 exit gate. Confirm one transaction owns both canonical targets
  and no successful result can represent partial convergence.

## S6 - Exact Retry, Concurrency And Vertical Reconciliation

- [x] S6-T001: Implement application lookup by preview token before fresh apply
  recomputation.
- [x] S6-T002: Return `already_applied` only when actor, operation, question ids,
  revisions and candidate identity match the committed application.
- [x] S6-T003: Return replay-mismatch diagnostic for a stored token with any
  divergent request value.
- [x] S6-T004: Define retry behavior for rolled-back and recovery-required
  transactions and test every state.
- [x] S6-T005: Add two-process convergence apply test proving one commit and one
  non-committing `already_applied`, stale-precondition or explicit active-lock
  result; no second application record or partial target set may exist.
- [x] S6-T006: Add injected-clock and audit-date metamorphic tests proving stable
  semantic preview/retry identity.
- [x] S6-T007: Implement vertical reconciliation diff by stable identity,
  question revision and target/completion semantics.
- [x] S6-T008: Preserve state/answers for wording-only revisions and append
  revision provenance.
- [x] S6-T009: Supersede semantic replacements and create new unanswered target
  without answer copying.
- [x] S6-T010: Retire removed/no-longer-required unanswered questions and retain
  answered/applied history inactive.
- [x] S6-T011: Add explicit declarative alias mapping and reject fuzzy/text
  remapping.
- [x] S6-T012: Render reconciliation preview with affected evidence and require
  owner apply when answered/applied records are affected.
- [x] S6-T013: Allow deterministic write-safe initialization only when no prior
  owner evidence can be altered.
- [x] S6-T014: Integrate vertical selection output with
  `reconciliation_required` guidance and immediate old-preview invalidation.
- [x] S6-T015: Test section add/remove/rename, question wording/target,
  profile/module and lock-only drift for every lifecycle state.
- [x] S6-T016: Run focused retry, concurrency, vertical selection and reconcile
  tests.
- [x] S6-T017: S6 exit gate. Confirm response-loss retry is safe and vertical
  drift never silently moves owner evidence.

## S7 - Next Actions, Progress, Freshness And Decision Context

- [x] S7-T001: Add a convergence-result adapter to `NextActionService` with no
  ranking logic in the adapter.
- [x] S7-T002: Define stable action kind/target ids for schema migration,
  question answer/reconcile/apply and definition gaps.
- [x] S7-T003: Implement dedup against generated/curated actions by semantic
  kind/target, not display text.
- [x] S7-T004: Preserve recovery/migration precedence and prevent optional
  legacy evidence from displacing blockers/answered/required definition work.
- [x] S7-T005: Remove review self-loop when a concrete next operation exists;
  preserve publication review independence.
- [x] S7-T006: Extend progress output with descriptive question counts and
  residual states without a third aggregate percentage.
- [x] S7-T007: Add explicit question-state and definition source classes/paths to
  freshness node definitions.
- [x] S7-T008: Test question-only changes do not stale unrelated generated
  feature projections or software specs.
- [x] S7-T009: Test definition apply stales only explicitly definition-dependent
  nodes and returns topological actions without executing them.
- [x] S7-T010: Add `SourceKind.PROJECT_QUESTIONS` and conditional source catalog
  descriptor for schema v2/present artifact.
- [x] S7-T011: Extract bounded project-question quality/pending records with
  `Activation.INACTIVE` for every state.
- [x] S7-T012: Prohibit topology relation generation and semantic project
  constraints from question state; retain definition authority.
- [x] S7-T013: Prevent applied answer/definition double-counting and test
  evidence traceability.
- [x] S7-T014: Bump decision-context source/extractor/authority policy versions
  only where observable semantics change and update freshness tests.
- [x] S7-T015: Add schema-v1 source catalog regression proving missing project
  questions is expected, not a diagnostic.
- [x] S7-T016: Run focused next, progress, freshness, decision-context source,
  topology and retrieval tests.
- [x] S7-T017: S7 exit gate. Confirm one convergence truth feeds all consumers
  and pending question state never gains semantic authority.

## S8 - CLI, MCP Read Parity, Diagnostics And Documentation

- [x] S8-T001: Add dedicated `cli_commands/project_readiness.py` and minimal
  app wiring; do not place domain logic in `project_ops.py`.
- [x] S8-T002: Extend readiness review with format/limit, bounded text, counts
  and truncation while preserving command name/high-level headings.
- [x] S8-T003: Add gap list/detail text/JSON commands with filters,
  limit/cursor and stable error exits.
- [x] S8-T004: Add question status/next text/JSON commands with bounded paging.
- [x] S8-T005: Add owner answer/replace command with scalar or safe answer-file
  input, actor and expected revision.
- [x] S8-T006: Add owner defer/mute/reopen commands with reason, actor and
  expected revision.
- [x] S8-T007: Add reconciliation preview/apply commands with actor, token and
  confirmation.
- [x] S8-T008: Add convergence preview/apply commands with repeated explicit
  question ids, actor, token and confirmation.
- [x] S8-T009: Ensure every CLI mutation returns nonzero on blocked/stale/
  recovery state and prints actionable status/plan/recovery commands.
- [x] S8-T010: Add dedicated MCP project-readiness catalog and handler modules
  for existing review plus gaps/detail/questions status/next reads.
- [x] S8-T011: Add MCP registry schemas for limit/cursor/filter and
  `mutation_performed: false`; add no write tool.
- [x] S8-T012: Add CLI/MCP semantic payload parity tests at stable public fields,
  avoiding duplicated domain assertions.
- [x] S8-T013: Add explicit MCP write-absence test and documentation rationale/
  follow-up.
- [x] S8-T014: Implement P2P340-P2P349 diagnostics or reserve/update an adjacent
  collision-free range consistently across code/docs/tests.
- [x] S8-T015: Integrate global validation findings and structured JSON error
  payloads for malformed questions, schema gate, stale reconcile and cursor.
- [x] S8-T016: Update `docs/CLI-GUIDE.md`, `docs/MCP.md`,
  `docs/WORKSPACE-MIGRATION.md`, README/setup guidance and command help.
- [x] S8-T017: Update agent templates with schema-v2 questions, authority,
  preview/apply, missing-primitive and MCP write-deferral guidance.
- [x] S8-T018: Add template/generated instruction drift tests and run agent
  doctor/instruction-focused tests.
- [x] S8-T019: Run focused CLI project readiness, workspace migration, MCP
  project handler/catalog/registry, validation and docs-help tests.
- [x] S8-T020: S8 exit gate. Confirm public writes exist only in CLI, all shared
  reads have parity and presentation layers remain thin.

## G - Engine Completion Gate

- [x] G-T001: Run all focused S1-S8 tests together and resolve ordering/shared
  fixture issues without weakening assertions.
- [x] G-T002: Run `./scripts/test-public.sh -q`; completion is clean CLI/MCP
  contract evidence.
- [x] G-T003: Run `./scripts/test-full.sh -q`; completion is a clean full suite.
- [x] G-T004: Run `p2p validate` on fresh v2, upgradeable v1, migrated v2,
  malformed question and recovery-required fixtures.
- [x] G-T005: Run 100-proposal access/payload/metamorphic tests and record actual
  counts plus useful wall time.
- [x] G-T006: Run failure injection and two-process concurrency tests in an
  isolated environment.
- [x] G-T007: Run version consistency and package import checks for all public
  constants/payload schema versions.
- [x] G-T008: Review every changed CLI/MCP/storage/error contract against
  requirements and accepted proposal; completion is a traceability matrix with
  no orphan behavior.
- [x] G-T009: Review every task/test for redundant public-layer coverage and
  remove duplication that does not protect a distinct contract.
- [x] G-T010: Run `git diff --check` and inspect source/spec/docs changes for
  unrelated refactors, direct `.p2p` writes or hardcoded local values.
- [x] G-T011: Verify no MCP question/convergence write tool exists and no handler
  bypasses permission/transaction services.
- [x] G-T012: Verify all v1-valid operations in P-T005 remain available under the
  v2-capable runtime through representative contract tests.
- [x] G-T013: Verify migration/recovery/status/readiness read-only operations are
  byte-invariant.
- [x] G-T014: Update changelog/release notes and support matrix only after
  observed behavior and target version are final.
- [x] G-T015: G exit gate. Request the D1 owner decision only when AC001-AC034
  have direct engine evidence, the candidate version/runtime-range policy is
  explicit, no recovery state exists and residual risks are recorded. AC035-AC037
  are D1 release/build/smoke gates and cannot be prerequisites for authorizing
  D1 itself.

## D1 - Runtime Build And Deployment

- [x] D1-T001: Confirm owner-approved release/version, transitional runtime
  range and clean intended branch; completion is no unrelated worktree state in
  the release artifact and an explicit old/new runtime compatibility policy.
- [x] D1-T002: While the installed runtime is still compatible with the current
  contract, run `p2p runtime contract preview` and owner-confirmed `apply` for a
  transitional range accepting the current v1-capable line and candidate
  v2-capable line, with the candidate as recommended; never edit runtime state
  manually.
- [x] D1-T003: Update `pyproject.toml`, package `__version__`, runtime transition
  ranges, changelog and setup docs consistently.
- [x] D1-T004: Run version-consistency tests and import the package version from
  the source tree.
- [x] D1-T005: Build wheel/sdist with `python -m build` as documented in
  `release-how-to.md`; completion is a clean build using repository policy.
- [x] D1-T006: Inspect built artifact contents for project question modules,
  vertical resources, templates, docs metadata and absence of local/test scratch.
- [x] D1-T007: Create a clean temporary virtual environment and install the
  exact built artifact without relying on the editable source checkout.
- [x] D1-T008: Smoke fresh initialization and prove schema v2 plus empty project
  questions are created and validate.
- [x] D1-T009: Smoke a schema-v1 fixture: status is upgradeable, v1-safe write
  works, v2 question write blocks, plan target 2 is deterministic/read-only.
- [x] D1-T010: Smoke migration apply/recovery/no-op and post-v2 question read in
  the clean environment.
- [x] D1-T011: Prove a v1-only runtime/fixture reports schema v2 ahead and does
  not write; completion is compatibility evidence, not an attempted downgrade.
- [x] D1-T012: Re-run public and full suites against release-candidate source/
  artifact as defined by repository release policy.
- [x] D1-T013: Publish/distribute the runtime only through the owner-approved
  release process; completion is exact artifact/version availability.
- [x] D1-T013A: After the interrupted publication attempt, re-inspect active
  processes, worktree/remote divergence, local/remote tag, release, schema lock
  and recovery state; completion is a clean synchronized `main`, no active
  process, no `v0.3.0` tag/release and no migration/recovery side effect.
- [x] D1-T013B: Record development-environment provenance without mutation:
  Python `3.14.4`, editable source import `0.3.0`, stale package metadata
  `0.1.9`; classify the metadata difference as an explicit advisory and do not
  reinstall/downgrade implicitly.
- [x] D1-T013C: Re-run immutable-tag preflight immediately before publication:
  exact reviewed commit on `origin/main`, clean worktree and absent local/remote
  `v0.3.0` plus absent release/assets; any existing or ambiguous publication
  state blocks creation until reconciled.
- [x] D1-T013D: Create and push annotated `v0.3.0` only after owner confirmation;
  record the resolved commit and never move/reuse the tag after publication.
- [x] D1-T013E: For the owner-approved corrective tag, wait for the workflow and
  record clean Python 3.11 install, version/tag match, full tests, P2P validation,
  build and artifact-verifier results; the failed `v0.3.0` workflow is not
  runtime availability.
- [x] D1-T013F: Download the published wheel/sdist, record URL/size/SHA-256 and
  run `scripts/verify-release-artifacts.py`; do not substitute the earlier local
  build or an editable checkout.
- [x] D1-T013G: Install the downloaded wheel in a new `/tmp` virtual environment
  using the active local Python 3.14 and repeat CLI/MCP/fresh-v2/upgradeable-v1
  smoke without importing from the source checkout.
- [x] D1-T013H: Record one restart-safe release checkpoint after each external
  side effect; after interruption re-inspect state before retrying and never
  infer tag/release completion from a previously approved command.
- [x] D1-T013I: Record `v0.3.0` as an immutable failed checkpoint: workflow run
  `29533701609` failed on Python 3.11 prompt parsing before build/publication,
  produced no release assets and must not be moved or reused.
- [x] D1-T013J: Remove Python 3.12+-only f-string expressions from all affected
  prompt renderers and prove unchanged behavior with focused tests, Python 3.11
  compilation and full suites on Python 3.11 and 3.14.
- [x] D1-T013K: Keep source `0.3.1` as an unpublished corrective candidate until
  implementation review is complete and the owner separately approves its
  remote push and immutable release tag.
- [x] D1-T014: Verify collaborators can obtain the v2-capable runtime before any
  workspace migration is approved.
- [x] D1-T015: Record corrective-release rollback plan: after v2 migration, do
  not deploy a v1-only runtime.
- [x] D1-T016: D1 exit gate. Owner confirms the exact runtime artifact is the one
  to use for repository pilot M1, identified by published URL and SHA-256, with
  Python 3.11 CI and Python 3.14 isolated-smoke evidence.

## M1 - Repository V1-To-V2 Pilot

- [x] M1-T001: Confirm repository branch/worktree and use the released/project-
  local v2-capable runtime selected in D1.
- [x] M1-T001A: Before every pilot command, prove the selected executable imports
  from the isolated published-wheel environment, reports the owner-approved
  corrective version and matches the D1 SHA-256; do not use stale editable
  metadata as runtime selection evidence.
- [x] M1-T002: Capture baseline runtime status, schema status, recovery state and
  global validation in text/JSON.
- [x] M1-T003: Capture active vertical/profile/modules/lock checksum and
  definition semantic/physical hashes, including all legacy open-question
  counts.
- [x] M1-T004: Capture project readiness gaps/questions, progress axes, next
  actions and freshness graph before migration.
- [x] M1-T005: Capture registry counts, project projection count/manifest,
  decision-context source/record/node/relation/diagnostic counts, assessment,
  maturity, brief/export/publication/spec status and Git diff.
- [x] M1-T005A: Create one explicit `/tmp` scratch root for baseline JSON, full
  plan JSON and command transcripts; record its disposable status and do not
  invent a repository output path or treat it as canonical memory.
- [x] M1-T006: Confirm migration lock/recovery is clear and no unrelated
  governed write is in progress.
- [x] M1-T006A: Confirm no prior P2P/migration process or tool session remains
  active and record the process/session identity that will own apply; a live
  process with an active lock is not interrupted recovery.
- [x] M1-T007: Run `p2p workspace migrate plan --to 2 --format json`
  without writes and archive the reviewed fingerprint/operations as local
  implementation evidence, not canonical state.
- [x] M1-T007A: Preserve the complete plan JSON and build a deterministic review
  digest with Git commit, published-wheel hash/imported version, canonical
  fingerprint, source/target schema, migration ids, operation/finding counts,
  owner inputs, every non-preserve operation/write target and plan fingerprint.
- [x] M1-T008: Review candidate ownership: only project questions, definition
  normalization and workspace schema/history may be canonical targets for v1->v2.
- [x] M1-T008A: Classify all `preserve_legacy` and `derived-state` operations
  separately from canonical writes; unexpected non-preserve targets block apply
  even when the overall plan reports applicable.
- [x] M1-T009: Review legacy mapping/question seeding for assumptions, decisions
  and risks/alternatives/decisions; confirm no answer or completion is invented.
- [x] M1-T010: If plan requests only target bindings, obtain explicit owner input
  and rerun plan; never include an answer in migration input.
- [x] M1-T011: Re-run plan after any input/source change and confirm stable
  fingerprint plus no unexplained operation.
- [x] M1-T011A: Invalidate and regenerate both plans when Git commit, published
  runtime hash, canonical source fingerprint or owner input changes; compare
  full digest equality, not only the final fingerprint string.
- [x] M1-T012: Obtain owner confirmation for the exact plan fingerprint, actor
  and apply operation.
- [x] M1-T013: Apply target 2 through `p2p workspace migrate apply` with reviewed
  fingerprint, owner actor and explicit confirmation.
- [x] M1-T013A: Run apply as one foreground process and capture start time,
  session/PID, exact command, stdout, stderr and exit status. Do not start a
  duplicate apply or interpret asynchronous tool completion as process exit.
- [x] M1-T014: Immediately inspect apply result, transaction id, changed paths,
  final hashes, schema status and recovery status before any further write.
- [x] M1-T014A: Wait for confirmed process termination before classifying the
  final lock/journal state. If recovery remains, use only supported status,
  resume or rollback commands; never delete lock, journal or candidate files.
- [x] M1-T015: Verify `.p2p/project/questions.yml` through supported show/status,
  definition open questions are empty, lock binding is current and schema is 2.
- [x] M1-T015A: Verify every migrated/seeded question's actor, revision,
  source/provenance, vertical lock checksum, applicability and empty answers/
  applications; no timestamp/status may imply owner evidence.
- [x] M1-T016: Run `p2p validate`; stop before question answers if any error,
  warning or recovery condition was introduced.
- [x] M1-T017: Run readiness review/gaps/questions status/next and verify the
  three repository pilot gaps are represented or have explicit no-safe
  diagnostics.
- [x] M1-T017A: Record the repository-specific result separately for
  `assumptions`, `decisions` and `risks_alternatives_decisions`; an applicable
  fallback question or explicit `no_safe_question` is valid, while invented
  owner truth or a silently missing gap is not.
- [x] M1-T018: Confirm migration did not change definition completeness,
  declared evidence coverage, owner decisions, assumptions or publication review.
- [x] M1-T019: Run exact migration plan/apply again and verify idempotent no-op.
- [x] M1-T020: Exercise one read-only convergence preview only if an eligible
  owner answer already exists; otherwise record not applicable without creating
  an answer.
- [x] M1-T021: Keep any answer/apply/defer/mute action as a separate owner-
  confirmed step and record its own preview/result evidence.
- [x] M1-T022: After schema-v2 validation, preview and owner-apply the final
  repository runtime contract requiring the v2-capable release line and
  recommending the exact deployed version; verify a v1-only runtime is then
  incompatible without attempting a downgrade.
- [x] M1-T022A: Review the final runtime-contract preview changed-path set and
  verify only the canonical contract plus its managed setup guide change; after
  apply, confirm source/imported/runtime-contract versions and published artifact
  provenance remain coherent.
- [x] M1-T023: M1 exit gate. Schema v2 is valid, recovery is clear, no owner truth
  was inferred and canonical migration diff is understood.

## A1 - Artifact Alignment Audit And Selective Reconciliation

- [x] A1-T001: Freeze post-migration pre-alignment hashes/counts and run
  read-only runtime, schema, recovery, context, definition, readiness, progress,
  freshness, registry status, next and global validation commands.
- [x] A1-T001A: Compare the post-migration graph with the observed pre-migration
  baseline where canonical sources, request-scoped decision context, registries,
  project projections and agent integrations were current; do not refresh these
  layers unless their own contract now reports staleness/divergence.
- [x] A1-T002: Build an alignment table for every material artifact with path/
  id, class, canonicality, owner service, source fingerprint, current/stale
  state, required authority, owning command and recommended action.
- [x] A1-T003: Classify canonical state first: workspace schema/questions,
  definition, vertical lock, permissions, proposals/decisions/choices/changes/
  work and publication review; completion is no unexplained canonical drift.
- [x] A1-T004: If any canonical inconsistency lacks a supported primitive, stop
  and record the missing primitive; do not repair `.p2p` manually.
- [x] A1-T005: Evaluate registries against source counts/hashes; run
  `p2p registry refresh` only if stale, then verify proposals, decisions,
  changes, choices, relations, artifacts and readiness counts.
- [x] A1-T006: Evaluate project projection/manifest against accepted basis and
  definition source contract; run `p2p project refresh` only if stale and verify
  exact owned-path reconciliation.
- [x] A1-T007: Rebuild/read decision context as supported and compare source,
  evidence, record, node, relation and diagnostic counts; verify project
  questions are inactive and applied definition is not double-counted.
- [x] A1-T007A: Treat a current request-scoped decision context with a missing
  optional durable-snapshot primitive as non-blocking; record the optional
  primitive without manufacturing a persistent cache or refresh command.
- [x] A1-T008: Evaluate assessment, maturity and project progress separately;
  refresh only stale persisted assessments and verify basis/freshness labels.
- [x] A1-T009: Evaluate managed next actions after convergence integration; run
  `p2p next refresh` only if stale and verify no self-loop, duplicate or
  publication-approval shortcut.
- [x] A1-T010: Evaluate derived freshness again after each deterministic batch;
  continue in topological order and stop on a failed refresh without pretending
  downstream nodes are current.
- [x] A1-T011: Evaluate generated agent instructions/templates; if source
  templates changed, refresh installed adapters through `p2p agent instructions
  refresh` and run agent doctor/drift tests.
- [x] A1-T012: Evaluate the active Change Set software spec with `p2p spec
  lifecycle`; refresh only when its accepted proposal/source fingerprints make
  it stale, and do not bulk-regenerate historical specs.
- [x] A1-T012A: When the freshness graph reports aggregate `software_specs`
  staleness, inspect every generated spec by Change Set/source fingerprint and
  refresh only the stale owned items; aggregate status alone never authorizes a
  historical bulk rebuild.
- [x] A1-T013: Evaluate operational brief freshness. Generate prompt/context only
  through `p2p project brief prompt`; import revised narrative only after the
  required agent/owner review and supported import primitive.
- [x] A1-T014: Evaluate visible project export; run `p2p project export` only if
  its source contract includes changed schema/question/definition state.
- [x] A1-T015: Evaluate publication packet, curated Markdown, validation and PDF
  independently. Prepare/recurate/revalidate/render only if stale and explicitly
  in rollout scope.
- [x] A1-T015A: Preserve stage order and authority: deterministic publication
  stages may follow current upstreams, curator import remains agent-controlled
  and `publication_review` remains false/pending unless the owner makes a new
  separate decision.
- [x] A1-T016: Confirm publication owner review remains unchanged/false unless
  separately decided by the owner; deterministic stages cannot approve it.
- [x] A1-T017: Classify review snapshots, optional legacy outputs and old v1
  question representations as preserve/retire/unaffected according to an owning
  contract; do not delete merely to make freshness green.
- [x] A1-T018: Update repository docs and this feature's later
  `implementation.md` with actual command/version/migration behavior; do not
  copy local specs into runtime/release surfaces automatically.
- [x] A1-T019: Compare baseline, post-migration and post-alignment hashes, counts,
  diagnostics, progress axes, freshness nodes and residual legacy/owner state.
- [x] A1-T020: Review Git diff and explain every canonical/generated/curated
  change; revert no user work and leave unaffected artifacts byte-stable.
- [x] A1-T021: Run focused alignment/freshness/projection/context tests and full
  `p2p validate` after final selected refresh.
- [x] A1-T022: A1 exit gate. Every material artifact is current, intentionally
  stale/pending, preserved legacy or blocked by an explicit missing primitive;
  no ambiguous state remains.

## F - Final Verification And Handoff

- [x] F-T001: Create/update local `implementation.md` with design choice,
  compatibility impact, behavior changes, files, tests, release artifact,
  migration result, alignment result, risks and follow-ups.
- [x] F-T002: Build a requirement -> design -> task -> test/evidence matrix for
  R-F1 through R-F9 (including R-F9-024..034), E001-E036 and AC001-AC055;
  completion is no orphan requirement/task/edge case and the matrix has been
  maintained at each remaining D1/M1/A1 checkpoint rather than reconstructed
  only here.
- [x] F-T003: Run final focused feature suites.
- [x] F-T004: Run `./scripts/test-public.sh -q`.
- [x] F-T005: Run `./scripts/test-full.sh -q`.
- [x] F-T005A: Record clean release CI on declared-minimum Python 3.11 and clean
  isolated published-wheel smoke on active local Python 3.14; neither result may
  be inferred from the other and no local interpreter downgrade is permitted.
- [x] F-T006: Run final `p2p runtime status`, workspace schema/recovery status,
  project readiness/progress/freshness, `p2p validate` and agent doctor.
- [x] F-T006A: Record `pyproject` version, source `__version__`, imported runtime
  version/path, Python interpreter and installed package metadata/editable
  location. Resolve a mismatch only through explicit owner-approved environment
  action or retain it as a named advisory; never reinstall silently.
- [x] F-T007: Confirm migration/mutation transaction scratch and locks are absent
  or explicitly recovery-owned.
- [x] F-T007A: Confirm no release/build/test/migration process or tool session is
  still running and that disposable `/tmp` evidence is either intentionally
  retained for the active handoff or safely irrelevant to project truth.
- [x] F-T008: Confirm MCP write deferral is visible in specs/docs and no write
  tool was accidentally registered.
- [x] F-T009: Confirm all owner-controlled outcomes remain explicitly recorded
  and no generated artifact implies publication/question/governance approval.
- [x] F-T010: Run `git diff --check`, inspect status/diff and verify no hardcoded
  local path, unrelated refactor, manual `.p2p` repair or unexplained binary/
  generated drift exists.
- [x] F-T010A: Verify the published tag resolves to the recorded commit, the
  downloaded runtime hash is recorded without committing local wheel/venv paths,
  and no restart checkpoint is mistaken for canonical project state.
- [x] F-T011: Record residual risks and follow-up candidates without bundling
  unrelated cleanup.
- [x] F-T012: Obtain owner review for commit/push/release or any remaining
  owner-controlled handoff; do not infer authorization from completed tests.
- [x] F-T013: F final gate. Mark feature delivered only when implementation,
  runtime deployment, repository migration and selected artifact alignment each
  have direct evidence and the workspace remains operable through supported
  commands.

## Deferred Follow-Up Candidates

- [ ] X-T001: Propose consent-gated MCP answer/defer/mute/reopen/reconcile/apply
  only after CLI payload stability and usage evidence.
- [ ] X-T002: Propose durable expiring preview receipts only if source-bound
  staleness and exact retry are insufficient.
- [ ] X-T003: Evaluate persistent readiness cache only after measured snapshot
  cost exceeds accepted budgets.
- [ ] X-T004: Evaluate remote/fleet migration orchestration separately from local
  workspace migration.
- [ ] X-T005: Evaluate automated artifact-alignment orchestration only after
  ownership/freshness coverage can prove no curated or owner stage is bypassed.
- [ ] X-T006: Evaluate workspace downgrade only as a separate proposal with an
  explicit loss/authority model; it remains unsupported here.
- [ ] X-T007: Evaluate a permanent automated CI matrix for the declared-minimum
  Python and the active/latest supported Python as a separate delivery change.
  The immediate release may combine clean Python 3.11 release CI with isolated
  Python 3.14 published-wheel smoke, but that evidence does not silently change
  the repository's long-term Python support or CI policy.
