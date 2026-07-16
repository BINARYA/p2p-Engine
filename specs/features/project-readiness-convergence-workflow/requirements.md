# Requirements - Project Readiness Convergence Workflow

## Scope

Implement the software improvement approved by `PROP-101`: turn project
readiness from a diagnostic report into a deterministic, persistent and
owner-governed convergence workflow.

The feature introduces typed readiness gaps, project-scoped question state,
safe question selection, structured owner answers, a coordinated definition
and question apply, managed-next integration and an explicit workspace schema
v1-to-v2 migration. It also defines the package rollout and the later migration
and artifact-alignment procedure for this repository.

This specification is a local implementation aid under `specs/`. It does not
replace the accepted proposal, create a Change Set, authorize implementation,
approve a package release or authorize migration of any workspace.

## Origin And Delivery State

- Source proposal: `PROP-101 - Project Readiness Convergence Workflow`.
- Source decision: `accepted` by `mrjungle`.
- Proposal readiness at specification start: `100`, `decision_ready`, high
  confidence, no failed gates or unanswered owner questions.
- Related accepted directions: `PROP-079`, `PROP-085`, `PROP-089`, `PROP-090`,
  `PROP-091`, `PROP-095`, `PROP-096`, `PROP-097` and `PROP-100`.
- Local implementation state: specification only.
- Governed implementation prerequisite: create or identify a Change Set sourced
  from `PROP-101` and pass the P2P software-spec lifecycle preflight before
  modifying runtime behavior.
- Repository rollout prerequisite: the v2-capable runtime must be built,
  validated and available before this repository is migrated from workspace
  schema v1 to v2.

## Current-System Baseline

- `CURRENT_WORKSPACE_SCHEMA_VERSION` is `1`.
- The migration registry contains only `workspace-legacy-to-v1`.
- `WorkspaceCompatibilityService.plan()` renders legacy bootstrap operations
  directly instead of dispatching transition-specific handlers.
- `WorkspaceSchemaService` distinguishes undeclared legacy, current, ahead and
  incomplete layouts, but a valid older declared version is not represented as
  an independently operable upgradeable state.
- `ProjectVerticalService.project_readiness_review()` scans proposal coverage,
  reports every unmapped proposal and emits only vertical-declared questions.
- The current repository has incomplete `assumptions`, `decisions` and
  `risks_alternatives_decisions` definition sections.
- Project-definition `open_questions` are embedded in `definition.yml`; there is
  no dedicated project-question lifecycle artifact.
- The existing definition preview/apply writes only `definition.yml`.
- `AtomicMutationWriter` supports multi-target replacement and rollback, but its
  current preimage loop is target-oriented and does not yet provide a generic
  under-lock validation hook for non-target source dependencies.
- `MutationPreviewService` produces deterministic source-bound tokens but does
  not yet define explicit actor binding or exact `already_applied` replay.
- `NextActionService`, `ProjectProgressService`, `DerivedFreshnessService` and
  decision-context source/topology services already provide the consumers that
  must receive convergence results without duplicating domain logic.
- CLI exposes `p2p project readiness review`; MCP exposes the equivalent
  read-only review tool. No project-question write surface exists.

## In Scope

- Immutable request-scoped convergence snapshots and source-access accounting.
- Typed, versioned and explainable readiness gap records.
- Six-class priority and stable gap/question identity.
- A schema-v2 project-question artifact at
  `.p2p/project/questions.yml`, with root key `project_questions` and artifact
  schema version `1`.
- A project-question lifecycle distinct from proposal questions.
- Optional backward-compatible vertical question target/answer-contract
  metadata.
- Deterministic declared-question selection, fallback generation and
  `no_safe_question` diagnostics.
- Owner-only answer, replace, defer, mute and reopen mutations in the first
  release.
- Deterministic question reconciliation after vertical, profile or module
  changes.
- Pure project-definition candidate rendering reused by a coordinated
  definition/question transaction.
- Actor-bound preview tokens, stale-source checks, exact committed retry and
  concurrency protection.
- A common operation-to-workspace-schema compatibility gate.
- Workspace schema v2 status, fresh-workspace initialization and registered
  v1-to-v2 migration.
- Transition-specific migration planning over candidate overlays.
- Atomic migration of legacy definition questions into the dedicated artifact,
  with definition `open_questions` normalized to empty.
- Managed next actions, progress, freshness and decision-context integration.
- Backward-compatible bounded CLI behavior and read-only MCP parity.
- Focused, public, migration, failure-injection, concurrency, performance and
  full-suite tests.
- Release preparation, clean-environment smoke checks and deployment ordering.
- A repository pilot and a final evidence-based artifact-alignment phase.
- Documentation, generated agent-template updates and implementation evidence.

## Out Of Scope

- MCP tools that answer, defer, mute, reopen, reconcile or apply project
  questions. These require a later consent-gated proposal/slice after the CLI
  write contract is stable.
- Agent-created owner answers or a free-form `source=owner` authority shortcut.
- Implicit workspace migration from validation, status, readiness, init of an
  unrelated artifact or an ordinary governed write.
- Workspace schema downgrade after a successful v2 migration.
- Database persistence, persistent index cache, hosted orchestration or remote
  fleet migration.
- Automatic proposal vertical-coverage declarations from heuristic evidence.
- Automatic refresh of every derived artifact after canonical apply.
- Automatic operational-brief import, project curation, publication approval or
  owner review.
- Changing proposal-question persistence or lifecycle semantics.
- Broad refactoring of `P2PWorkspace`, CLI modules, MCP registries or unrelated
  migration behavior.
- Releasing a package, pushing Git state or migrating this repository without
  the explicit owner-controlled gate required at that stage.

## Public Surface And MCP Impact

| Surface | Initial decision | Contract |
| --- | --- | --- |
| CLI readiness review | additive and bounded behavior change | Preserve command name and existing summary concepts; add text/JSON structured gaps, counts and truncation metadata. |
| CLI project questions | new owner-governed write workflow | Add status, next, answer, defer, mute, reopen and reconcile operations with explicit actor/reason/revision semantics. |
| CLI convergence apply | new owner-governed write workflow | Add preview/apply over explicit question IDs and a matching actor-bound token. |
| CLI workspace migration | compatible extension | Preserve existing commands; add v1 upgradeable status and v1-to-v2 plan/apply behavior. |
| MCP readiness reads | updated read-only parity | Update existing review and add bounded gap/question read tools after core/CLI payload stabilization. |
| MCP question writes | explicitly deferred | No write tools in this feature; document the missing parity and follow-up gate. |
| Storage | compatible v1 plus explicit v2 | Add `.p2p/project/questions.yml`; migrate only through the workspace migration engine. |
| Project definition | workspace-version-dependent compatibility | Keep `project_definition.schema_version: 1`; in v2 require `open_questions` to be empty and reject legacy add/close operations. |
| Decision context | additive metadata source | Add project questions as inactive quality/pending evidence; applied definition remains semantic authority. |
| Next/progress/freshness | additive derived behavior | Consume one convergence result; do not create competing readiness engines. |
| Agent-facing instructions | updated | Explain schema gate, question authority, preview/apply and MCP write deferral. |

## Terminology

- **Convergence snapshot**: immutable captured inputs used by one readiness
  request, including canonical hashes and policy versions.
- **Gap**: typed difference between current project state and a vertical or
  compatibility requirement.
- **Question identity**: stable semantic key independent from wording, checksum
  revision and audit timestamps.
- **Question revision**: version of wording, source lock and answer contract for
  one stable identity.
- **Answer contract**: declarative schema that validates owner input and maps it
  to an allowed candidate-definition operation without generative inference.
- **Question state converged**: the active question is answered, deferred or
  muted according to policy; this does not imply definition completion.
- **Definition converged**: the owner-confirmed candidate was committed and the
  remaining definition gap was recomputed.
- **Upgradeable v1**: valid workspace schema v1 operated by a v2-capable runtime
  with legacy-safe operations still available and v2 operations gated.
- **Artifact alignment**: evidence-based reconciliation of canonical,
  deterministic-derived, curated and owner-reviewed artifacts after rollout.

## Functional Requirements

### F1 - Convergence Snapshot And Typed Gaps

- R-F1-001: WHEN project readiness is requested, THE SYSTEM SHALL build one
  immutable convergence snapshot for that request.
- R-F1-002: THE snapshot SHALL include workspace schema state, active vertical
  identity, vertical lock checksum, project-definition bytes/hash, project
  question bytes/hash when present, permission-policy hash, declared proposal
  coverage, proposal lifecycle summaries and all policy versions used by gap
  classification or candidate rendering.
- R-F1-003: THE snapshot SHALL capture and hash the same source bytes and SHALL
  NOT reread a selected source during classification, sorting, pagination or
  serialization.
- R-F1-004: THE snapshot fingerprint SHALL exclude absolute root, filesystem
  mtime, generated observation time and audit-only timestamps.
- R-F1-005: THE readiness service SHALL return typed gaps with stable id,
  snapshot fingerprint, vertical/section identity, kind, severity,
  applicability, definition status, missing fields, evidence basis, required
  authority, current question reference, next operation and rationale.
- R-F1-006: THE gap taxonomy SHALL distinguish integrity/compatibility/authority
  blockers, owner-decision blockers, answered-not-applied questions, incomplete
  required definition, assumptions to validate, optional declared evidence and
  informational legacy/heuristic state.
- R-F1-007: THE system SHALL keep declared proposal evidence and heuristic
  suggestions in separate fields and SHALL NOT increase declared coverage from
  heuristic matches.
- R-F1-008: THE priority policy SHALL order: blockers; answered-not-applied;
  incomplete required definition; assumptions by declared dependency impact;
  optional declared evidence; informational legacy state.
- R-F1-009: WITHIN one priority class, THE SYSTEM SHALL tie-break by vertical
  section priority and stable gap/question id.
- R-F1-010: EVERY returned priority SHALL expose class, policy version,
  rationale and tie-break inputs.
- R-F1-011: IF dependency-impact metadata is absent, THE SYSTEM SHALL use a
  documented neutral value and SHALL NOT infer dependency impact from prose.
- R-F1-012: IF the active vertical or definition is missing/invalid, THE SYSTEM
  SHALL return typed initialization/integrity gaps and actionable commands
  instead of fabricating section readiness.
- R-F1-013: THE convergence result SHALL be the only readiness input consumed by
  next-action, progress and freshness adapters introduced by this feature.
- R-F1-014: READ-ONLY snapshot, review, list, show and pagination operations
  SHALL perform no persistent write, prompt generation or artifact refresh.
- R-F1-015: THE existing `review` command SHALL preserve its high-level section,
  missing-capisaldi, question and next-action semantics while bounding detailed
  lists and reporting truncation.

### F2 - Workspace Schema v2 And Transition Dispatch

- R-F2-001: THE v2-capable runtime SHALL set the current workspace schema target
  to `2` while preserving the workspace-schema envelope contract unless a
  separately justified envelope change is required.
- R-F2-002: THE workspace schema status SHALL distinguish undeclared v0, valid
  upgradeable v1, current v2, ahead-of-runtime, invalid, incomplete and
  recovery-required states.
- R-F2-003: A valid v1 workspace SHALL remain aligned for v1-safe operations and
  SHALL report `upgrade_available` or an equivalent explicit state, transition
  path, runtime support and exact plan command.
- R-F2-004: THE status field `migration_required` SHALL be true for a requested
  v2-only operation on v1, without claiming that every v1 operation is blocked.
- R-F2-005: THE migration registry SHALL resolve adjacent forward-only handlers
  rather than transition metadata without behavior ownership.
- R-F2-006: EVERY transition handler SHALL declare source/target versions,
  runtime support, capabilities, owner inputs, owned candidate targets,
  validators and dependencies.
- R-F2-007: MULTI-STEP planning SHALL execute handlers in version order over a
  candidate workspace overlay.
- R-F2-008: THE legacy-to-v1 behavior SHALL first be extracted behind its own
  handler with no public or candidate drift.
- R-F2-009: THE v1-to-v2 handler SHALL NOT emit domain, permission, metadata,
  vertical or rubric bootstrap operations owned by legacy-to-v1.
- R-F2-010: AN operation-schema requirement registry SHALL classify every
  governed write by minimum and optional maximum workspace schema version.
- R-F2-011: AN unknown governed-write operation id SHALL fail closed until it is
  classified.
- R-F2-012: THE common write preflight SHALL enforce runtime compatibility,
  migration lock/recovery state and operation schema compatibility before any
  write-specific service mutates state.
- R-F2-013: A schema-gated operation SHALL return current/required versions,
  operation id, reason, recoverability and exact status/plan command.
- R-F2-014: Existing v1 definition, proposal, choice, Change Set, Work,
  registry, assessment, sync and other v1-valid operations SHALL remain
  available under the v2-capable runtime.
- R-F2-015: V2-only question/convergence writes SHALL fail before mutation on
  v1.
- R-F2-016: In v2, legacy definition operations `add_open_question` and
  `close_open_question` SHALL fail with the supported project-question command.
- R-F2-017: Fresh workspace initialization under the v2-capable runtime SHALL
  create schema v2 and a valid empty project-question artifact before committing
  workspace schema state last.
- R-F2-018: AN old runtime that supports only schema v1 SHALL treat a v2
  workspace as ahead and SHALL block governed writes.
- R-F2-019: Planning, status and validation SHALL never migrate implicitly.
- R-F2-020: A successfully migrated v2 workspace SHALL not advertise an
  automatic downgrade path.

### F3 - Project-Question Artifact And Legacy Migration

- R-F3-001: Workspace schema v2 SHALL own exactly one canonical project-question
  artifact at `.p2p/project/questions.yml` with root key `project_questions` and
  artifact schema version `1`.
- R-F3-002: THE project-question parser SHALL reject unknown top-level fields,
  duplicate ids, invalid transitions, malformed authority, invalid target
  references and unsupported artifact schema versions with structured
  diagnostics.
- R-F3-003: EVERY question SHALL preserve stable id/key, revision, wording hash,
  group/gap, section, target, priority, rationale, source type, vertical
  identity/checksum, answer contract, lifecycle state, applicability, answer
  history, provided-by, recorded-by, timestamps, apply references, transition
  history and supersession links.
- R-F3-004: Stable identity SHALL include vertical id, section id, gap kind,
  semantic target and declared question id or fallback key; it SHALL exclude
  wording, lock checksum, audit timestamps and physical path.
- R-F3-005: A question id SHALL be deterministic from stable identity and SHALL
  detect collisions rather than silently merging distinct identities.
- R-F3-006: Wording/checksum/policy changes SHALL create a new revision without
  changing stable identity when semantic target and completion meaning are
  unchanged.
- R-F3-007: THE artifact semantic hash SHALL exclude audit-only timestamps while
  retaining every lifecycle, answer, target, authority and apply value.
- R-F3-008: THE v1-to-v2 migration SHALL copy every valid legacy definition open
  question exactly once into project-question state.
- R-F3-009: A migrated legacy question SHALL start `to_answer` unless explicit
  source data proves another supported state; absence SHALL NOT imply answered,
  applied, deferred, muted or retired.
- R-F3-010: Local legacy ids such as `Q001` SHALL NOT be treated as globally
  unique without the section/target identity.
- R-F3-011: Matching declared question ids and field targets SHALL be used only
  when unambiguous.
- R-F3-012: Duplicate ids, unknown sections/fields, conflicting texts, invalid
  statuses or ambiguous target mappings SHALL block lossy migration and report
  owner/repository input required.
- R-F3-013: Incomplete required sections without a legacy question SHALL receive
  a declared/fallback `to_answer` record or `no_safe_question` diagnostic during
  candidate generation.
- R-F3-014: Complete or not-applicable sections SHALL NOT receive questions only
  because a generic vertical question exists.
- R-F3-015: THE migration candidate SHALL normalize every definition
  `open_questions` list to empty in the same transaction that creates the new
  artifact.
- R-F3-016: Candidate validation SHALL prove one-to-one preservation of every
  migrated legacy question before replacement.
- R-F3-017: AFTER migration, validation SHALL reject non-empty definition
  `open_questions` in v2 and SHALL NOT maintain a writable compatibility shadow.
- R-F3-018: Migration planning SHALL preserve unknown durable artifacts and
  create no answer, owner decision, assumption validation or section-completion
  content.
- R-F3-019: Repeating v1-to-v2 apply after a committed migration SHALL return the
  existing no-op/idempotent result without duplicate questions.
- R-F3-020: Interrupted migration SHALL use the existing lock, journal,
  rollback/resume and recovery semantics and SHALL restore exact v1 bytes when
  rollback succeeds.

### F4 - Question Selection, Answers, Lifecycle And Authority

- R-F4-001: THE engine SHALL select an applicable question declared by the
  active locked vertical before considering a fallback.
- R-F4-002: Vertical question schema SHALL support optional target and answer
  contract metadata without invalidating existing v1 vertical packs.
- R-F4-003: IF declared target metadata is absent, THE engine SHALL bind only
  when one target is deterministically unambiguous under the versioned binding
  policy.
- R-F4-004: A fallback SHALL derive only from declarative section purpose,
  missing required field, assumption/blocker identity, completion criteria or
  a safe section-disposition contract.
- R-F4-005: A fallback SHALL NOT use an LLM, free-text inference, decision
  context or heuristic proposal matching to create owner content.
- R-F4-006: IF no safe binding exists, THE engine SHALL emit
  `no_safe_question` and SHALL NOT persist an invented question.
- R-F4-007: The first artifact lifecycle SHALL use steady states `to_answer`,
  `answered`, `applied`, `deferred`, `muted`, `retired` and `superseded`.
- R-F4-008: `reopen` SHALL be an audited transition to `to_answer`, not a stored
  steady state.
- R-F4-009: EVERY transition SHALL validate source state, target state, role,
  required reason, expected revision, provenance and side-effect policy.
- R-F4-010: Deterministic initialization/reconciliation MAY create `to_answer`,
  retire unanswered inapplicable records or supersede changed semantic targets,
  but SHALL NOT create owner answers or delete answer history.
- R-F4-011: The first release SHALL require an actor with project role `owner`
  to answer, replace, defer, mute or explicitly reopen a question.
- R-F4-012: THE first release SHALL NOT accept an agent-provided
  `provided_by=owner` or consent shortcut; delegated answer writes are deferred.
- R-F4-013: THE persisted answer SHALL distinguish `provided_by` from
  `recorded_by`; for direct owner CLI writes both SHALL resolve to the authorized
  owner identity.
- R-F4-014: Answer replacement SHALL be explicit, revision-checked and preserve
  the previous answer in append-only history.
- R-F4-015: Defer and mute SHALL require a non-empty reason, actor, time and
  provenance and SHALL leave the underlying gap visible.
- R-F4-016: Deferred questions SHALL become eligible only through explicit owner
  reopen or a declared machine-evaluable trigger.
- R-F4-017: Muted questions SHALL never be automatically re-asked.
- R-F4-018: Applied, retired and superseded revisions SHALL be terminal; later
  drift SHALL produce a replacement gap/question.
- R-F4-019: A question answer SHALL conform to its answer contract before it is
  recorded.
- R-F4-020: Supported answer contracts SHALL map only to allowlisted definition
  operations such as field value, section disposition, assumption resolution,
  blocker resolution or explicit owner-decision reference.
- R-F4-021: Recording an answer SHALL NOT update definition, resolve an owner
  decision, validate an assumption or mark a section complete.
- R-F4-022: A question without a deterministic allowed operation SHALL remain
  non-applicable for convergence apply and return an actionable diagnostic.

### F5 - Candidate Rendering And Atomic Convergence Apply

- R-F5-001: Convergence preview SHALL require an explicit non-empty set of
  answered question ids; it SHALL NOT silently apply every answer.
- R-F5-002: THE system SHALL render project-definition and project-question
  candidates from the same immutable snapshot.
- R-F5-003: Definition candidate rendering and validation SHALL be reusable pure
  logic separated from the existing single-target commit method.
- R-F5-004: THE candidate renderer SHALL map only validated answer contracts to
  existing allowlisted definition operations.
- R-F5-005: THE preview SHALL expose semantic diff, question ids/revisions,
  changed sections/fields/assumptions/blockers, before/candidate hashes, affected
  gaps, expected progress effect and downstream freshness plan.
- R-F5-006: THE preview SHALL perform no write and SHALL NOT mark a question
  applied.
- R-F5-007: THE preview token SHALL bind operation id, actor, target paths,
  workspace-schema hash, definition hash, question-state hash, permissions hash,
  vertical lock checksum, both candidate hashes and relevant policy versions.
- R-F5-008: Audit timestamps and generated observation times SHALL NOT make two
  otherwise identical previews produce different semantic tokens.
- R-F5-009: Apply SHALL require the same explicit question ids, actor, preview
  token and owner confirmation.
- R-F5-010: Apply SHALL recheck every target and non-target source precondition
  after acquiring the workspace mutation lock.
- R-F5-011: `AtomicMutationWriter` or its compatible successor SHALL support
  read-only source preconditions in addition to candidate targets.
- R-F5-012: Cross-artifact candidate validation SHALL run under lock before the
  first replacement.
- R-F5-013: Definition and question candidates SHALL be committed by one
  multi-target transaction; calling definition apply and then writing question
  state is forbidden.
- R-F5-014: An `applied` question candidate SHALL reference the exact definition
  candidate/operation committed in the same transaction.
- R-F5-015: Failure before replacement SHALL leave all canonical bytes unchanged.
- R-F5-016: Failure after any replacement SHALL rollback exact originals or
  return explicit recovery-required state with preserved evidence.
- R-F5-017: A canonical apply success SHALL return changed paths, final hashes,
  applied question ids and deterministic rebuild plan; it SHALL NOT execute the
  rebuild.
- R-F5-018: A successful apply SHALL not automatically refresh registries,
  project projections, decision context, assessments, briefs, exports,
  publication or software specs.

### F6 - Retry, Concurrency And Vertical Reconciliation

- R-F6-001: A retry with the same committed token, actor, question ids and
  candidate identity SHALL return `already_applied` with the original apply
  reference and final hashes.
- R-F6-002: A reused token with changed actor, source, question revision,
  candidate, vertical lock or policy SHALL be rejected as stale/mismatched.
- R-F6-003: Concurrent applies SHALL be serialized by the workspace lock and
  SHALL produce at most one canonical commit.
- R-F6-004: A token associated with a rolled-back transaction MAY be retried only
  after recovery is clear and every original precondition still matches.
- R-F6-005: The first release SHALL NOT claim clock expiry; introducing expiry
  requires a separately specified durable preview-receipt lifecycle.
- R-F6-006: A changed vertical lock SHALL invalidate outstanding answer-apply and
  reconciliation previews.
- R-F6-007: Question reconciliation SHALL be an explicit preview/apply workflow
  after vertical/profile/module change when question state contains prior
  evidence.
- R-F6-008: Wording-only question changes SHALL preserve stable id, answer and
  lifecycle while appending a revision.
- R-F6-009: Changed semantic target/completion meaning SHALL supersede the old
  question and create a replacement without copying the answer.
- R-F6-010: Removed/no-longer-required sections SHALL retire unanswered
  questions and preserve answered/applied history as inactive.
- R-F6-011: Newly required fields/sections SHALL create new gaps and
  declared/fallback questions.
- R-F6-012: Section aliases/remapping SHALL require explicit declarative mapping;
  fuzzy text remapping is forbidden.
- R-F6-013: Reconciliation SHALL NOT validate assumptions, complete sections or
  rewrite applied definition content.
- R-F6-014: Fresh v2 vertical selection with no prior evidence MAY initialize
  questions deterministically; any selection affecting prior answers SHALL
  report reconciliation required rather than silently rewriting them.

### F7 - Next Actions, Progress, Freshness And Decision Context

- R-F7-001: `NextActionService` SHALL consume the typed convergence result
  through one adapter and SHALL NOT duplicate gap ranking.
- R-F7-002: Generated readiness actions SHALL use stable kind/target identity and
  deduplicate against generated and curated actions.
- R-F7-003: A blocker, answered-not-applied or required-definition action SHALL
  not be displaced by bulk optional legacy evidence work.
- R-F7-004: The sole next action SHALL NOT be `readiness review` when a concrete
  migration, question, reconcile, preview or apply operation exists.
- R-F7-005: Deferred/muted questions SHALL suppress re-ask according to policy
  while residual gaps remain visible.
- R-F7-006: Publication review SHALL remain independent and SHALL NOT be
  recommended merely to make freshness current.
- R-F7-007: Project progress SHALL preserve independent definition-completeness
  and declared-evidence axes.
- R-F7-008: Question lifecycle MAY be reported as counts but SHALL NOT create an
  authoritative aggregate readiness percentage.
- R-F7-009: Question-only changes and definition-apply changes SHALL have
  different freshness source sets and downstream nodes.
- R-F7-010: Question-only changes SHALL NOT stale unrelated generated feature
  projections or software specs unless an explicit dependency is documented.
- R-F7-011: Definition apply SHALL stale only the graph nodes whose source
  contracts include changed definition values.
- R-F7-012: The freshness service SHALL return topologically ordered rebuild
  actions without automatically running deterministic, curated or owner stages.
- R-F7-013: Decision context SHALL add a dedicated `PROJECT_QUESTIONS` source
  kind classified as quality metadata or inactive pending evidence.
- R-F7-014: Project-question records SHALL never create active decisions,
  constraints or relations regardless of answered/applied state.
- R-F7-015: Applied definition content SHALL remain the semantic authority and
  question history SHALL retain traceability without double-counting.
- R-F7-016: On schema v1, absence of `.p2p/project/questions.yml` SHALL be an
  expected compatibility condition, not a source-catalog error.
- R-F7-017: Policy/source changes SHALL increment decision-context source,
  extractor and authority versions as required by their public contracts.

### F8 - CLI, Pagination, MCP And Diagnostics

- R-F8-001: `p2p project readiness review` SHALL remain available and SHALL gain
  `--format text|json` plus bounded summary/truncation metadata.
- R-F8-002: Default text review SHALL print counts and a bounded top list rather
  than all unmapped proposals or heuristic suggestions.
- R-F8-003: CLI SHALL expose gap list/detail, project-question status/next,
  owner answer/replace, defer, mute, reopen, reconciliation preview/apply and
  convergence preview/apply through the project-readiness command family.
- R-F8-004: CLI write commands SHALL expose actor, expected revision, reason,
  confirmation and preview token where their contracts require them.
- R-F8-005: Structured answer input SHALL support a safe root-resolved file for
  non-scalar answer contracts; scalar input SHALL still be validated against
  the question contract.
- R-F8-006: CLI output SHALL use stable operation/status/error fields in JSON and
  actionable concise text for humans.
- R-F8-007: List/history endpoints SHALL enforce documented default and maximum
  page sizes.
- R-F8-008: Pagination cursor SHALL bind schema version, collection, ordering
  policy, snapshot fingerprint and last stable key.
- R-F8-009: A cursor used after source drift SHALL return `stale_cursor` and a
  restart instruction rather than skip/duplicate records.
- R-F8-010: MCP SHALL update the existing readiness review and add read-only
  convergence/gap/question status/next tools after CLI payload stabilization.
- R-F8-011: CLI and MCP shared read payloads SHALL be semantically equivalent and
  covered by contract tests.
- R-F8-012: MCP SHALL expose no project-question or convergence mutation tool in
  the initial release.
- R-F8-013: MCP handlers SHALL delegate to facade/service methods and SHALL NOT
  contain ranking, lifecycle, authority or mutation logic.
- R-F8-014: Global validation SHALL report malformed project-question state,
  v2 legacy-question reintroduction, stale lock/question binding, missing
  operation schema classifications and invalid migration history.
- R-F8-015: Machine-facing failures SHALL include stable code, operation,
  current/requested state, recoverability and suggested command.

### F9 - Release, Repository Migration And Artifact Alignment

- R-F9-001: Before implementation, THE delivery SHALL create/identify a Change
  Set sourced from accepted `PROP-101` and record the target runtime release and
  compatibility matrix.
- R-F9-002: The release version, package metadata, runtime requirements,
  changelog and setup documentation SHALL be updated consistently before build.
- R-F9-003: THE v2-capable package SHALL pass focused, public and full tests,
  `p2p validate`, version-consistency checks and wheel/sdist build checks.
- R-F9-004: A clean-environment smoke SHALL prove fresh v2 init, valid v1 status,
  deterministic v1-to-v2 plan, blocked v2 operation before migration and normal
  v2 operation after migration.
- R-F9-005: Before the release-version bump makes the current checkout report
  the new runtime version, THE repository SHALL use the supported runtime
  contract preview/apply workflow to adopt an owner-reviewed transitional range
  that permits the current v1-capable runtime and the new v2-capable runtime,
  recommends the new version, and allows deployment before schema migration.
- R-F9-006: Rollback planning SHALL recognize that a successfully migrated v2
  workspace cannot run on a v1-only runtime; immediately after validated v2
  migration, THE repository SHALL narrow its runtime contract to the v2-capable
  release line, and runtime rollback SHALL use a v2-compatible corrective
  release rather than an unsupported downgrade.
- R-F9-007: Before migrating this repository, THE operator SHALL capture a
  baseline of runtime/schema status, recovery state, definition/questions,
  vertical lock, progress, next actions, freshness, decision-context counts,
  validation, tests and Git diff.
- R-F9-008: Repository v1-to-v2 planning SHALL be read-only, produce stable
  fingerprint/candidate ownership and receive explicit owner review before
  apply.
- R-F9-009: Repository migration SHALL use `p2p workspace migrate apply` with
  owner actor, reviewed fingerprint and explicit confirmation; direct `.p2p`
  edits are forbidden.
- R-F9-010: Immediately after apply, THE operator SHALL inspect transaction,
  recovery, schema v2, question artifact, empty definition open questions,
  vertical binding and global validation before any question answer.
- R-F9-011: The repository pilot SHALL confirm the current assumptions,
  decisions and risks/alternatives/decisions gaps are represented by supported
  questions or explicit diagnostics without fabricating answers.
- R-F9-012: Owner answer/apply or defer/mute during the pilot SHALL remain a
  separate explicit owner step and SHALL NOT be implied by successful migration.
- R-F9-013: Final artifact alignment SHALL begin with a read-only drift and
  freshness audit, not a blanket rebuild.
- R-F9-014: Every potentially affected artifact SHALL be classified as
  canonical, deterministic-derived, agent-curated, owner-reviewed, legacy or
  unaffected before an alignment write is selected.
- R-F9-015: Canonical alignment SHALL use only owning P2P CLI/MCP primitives and
  SHALL never be performed by manual `.p2p` edits.
- R-F9-016: Deterministic-derived artifacts SHALL be refreshed only when their
  source/policy contract reports them stale or their owning validation proves
  divergence.
- R-F9-017: Agent-curated and owner-reviewed artifacts SHALL never be marked
  current by deterministic rebuild alone; they require their existing lifecycle
  and explicit owner/curator decision.
- R-F9-018: Alignment SHALL evaluate at least registries, project projections,
  decision context, assessments/maturity/progress, next actions, freshness,
  operational brief, software specs, visible export, publication packet,
  curated publication, agent instructions and repository documentation.
- R-F9-019: Software specs SHALL be refreshed only for Change Sets whose
  lifecycle/source fingerprint requires it; all historical specs SHALL NOT be
  regenerated indiscriminately.
- R-F9-020: Publication review/approval SHALL remain unchanged unless separately
  recorded by the owner.
- R-F9-021: The alignment phase SHALL compare pre/post counts, hashes,
  diagnostics, freshness nodes and residual legacy state and explain every
  changed artifact class.
- R-F9-022: Feature completion SHALL record implementation evidence in a local
  `implementation.md` or equivalent non-canonical report with commands, results,
  residual risks and deferred MCP writes.
- R-F9-023: Final handoff SHALL require clean migration recovery state, clean
  validation, passing full suite, reviewed Git diff and no unexplained generated
  drift.
- R-F9-024: Runtime evidence SHALL distinguish the source/imported engine
  version, package metadata version, Python interpreter version, editable
  development environment and isolated release-artifact environment; none SHALL
  be treated as interchangeable without recorded evidence.
- R-F9-025: The delivery SHALL NOT replace, reinstall, downgrade or otherwise
  mutate the development Python environment merely to run the repository pilot;
  environment normalization requires a separate explicit owner action.
- R-F9-026: M1 SHALL use the exact wheel downloaded from the owner-approved
  published release, record its SHA-256 and verify its version/content; a local
  pre-release build SHALL NOT satisfy runtime-availability or pilot provenance.
- R-F9-027: Release evidence SHALL cover the declared minimum Python version in
  clean CI and the active local Python version in an isolated smoke environment,
  without downgrading the local interpreter.
- R-F9-028: Release/tag and migration execution SHALL be restart-safe: each
  external or governed step SHALL record a completed checkpoint, and after an
  interruption the operator SHALL re-inspect process, Git, tag, release, lock
  and recovery state before retrying any side effect.
- R-F9-029: Baseline, full migration plans and command transcripts SHALL be
  stored only in an explicit local scratch directory outside durable project
  memory until summarized into the implementation evidence; no new repository
  output path SHALL be invented for raw operational logs.
- R-F9-030: A large migration plan SHALL retain its complete JSON and expose a
  deterministic review digest containing source/target versions, runtime
  artifact hash, Git commit, canonical fingerprint, migration ids, operation
  counts, non-preserve operations, write targets, finding counts, owner inputs
  and plan fingerprint.
- R-F9-031: The reviewed migration plan SHALL be invalidated and regenerated
  when the selected runtime artifact, Git commit, owner input or canonical source
  fingerprint changes, even if a previous plan fingerprint remains available.
- R-F9-032: Migration apply SHALL run as one observed foreground process with
  captured session/process identity, exit status, stdout and stderr. A live apply
  lock SHALL NOT be classified as interrupted recovery until that process is
  confirmed terminated.
- R-F9-033: Post-migration verification SHALL inspect question actor, revision,
  source/provenance, vertical lock checksum and answer/application emptiness and
  SHALL accept either an applicable question or an explicit no-safe diagnostic
  for each pilot gap according to the implemented fallback contract.
- R-F9-034: Artifact alignment SHALL preserve nodes already reported current,
  evaluate aggregate stale states such as software specs at their owning item
  granularity, and treat a missing optional durable primitive as non-blocking
  when the supported request-scoped view is current.

## Non-Functional Requirements

- N001: THE implementation SHALL keep `P2PWorkspace` as a delegating facade and
  SHALL NOT add project-readiness domain logic directly to it.
- N002: THE implementation SHALL place new readiness CLI registration outside
  the already large `project_ops.py` except for minimal compatibility wiring.
- N003: THE implementation SHALL place MCP read logic in thin catalog/handler
  modules and SHALL NOT extend presentation layers with domain decisions.
- N004: THE implementation SHALL reuse existing YAML/filesystem, permission,
  mutation-preview, transaction, candidate-workspace, next-action, progress,
  freshness and decision-context primitives before adding new abstractions.
- N005: Structural extraction of legacy migration behavior SHALL precede v1-to-
  v2 behavior and SHALL have regression tests proving no v0-to-v1 drift.
- N006: THE implementation SHALL use typed dataclasses/enums and deterministic
  JSON-ready serialization for public and persisted contracts.
- N007: All persisted paths SHALL derive from the injected project root and
  SHALL reject traversal, symlink escape and repository-external targets.
- N008: Read-only operations SHALL be byte-for-byte mutation-free across the
  workspace outside explicitly allowed transient test/scratch locations.
- N009: Multi-file writes SHALL use durable same-filesystem staging, lock,
  preimage checks, candidate validation, atomic replacement and rollback/recovery.
- N010: Every error that blocks owner action SHALL be actionable for humans and
  structured for agents.
- N011: Public CLI/MCP/storage behavior SHALL remain compatible unless the
  accepted proposal explicitly authorizes the additive/bounded change.
- N012: One 100-proposal readiness snapshot SHALL perform one discovery pass and
  at most one read/hash/parse per included source.
- N013: Post-snapshot ranking, pagination and serialization SHALL perform zero
  source filesystem reads.
- N014: Default review output, page size and serialized payload SHALL have
  explicit tested maxima defined in design constants.
- N015: Determinism tests SHALL reverse source order and injected clocks and
  SHALL receive identical semantic identities, ordering, tokens and plans.
- N016: Tests SHALL use temporary roots, injected clocks/failure points and no
  local username, absolute checkout path, branch or ambient Git configuration.
- N017: The implementation SHALL add no network dependency to runtime, planning,
  migration, readiness or repository alignment.
- N018: Every slice SHALL have focused tests at the lowest useful layer and
  public tests only where CLI/MCP/storage contracts change.
- N019: The full repository suite SHALL pass before commit, push, release and
  repository migration gates unless the owner explicitly accepts residual risk.
- N020: No task SHALL mark implementation complete based only on generated
  specs, proposal artifacts or self-reported status; code/test/CLI evidence is
  required.

## Edge Cases And Failure Semantics

- E001: Workspace v1 is valid but project questions are requested.
- E002: Workspace schema is ahead of runtime.
- E003: Migration registry has duplicate/non-adjacent/missing handler.
- E004: Multi-step handler reads a pre-transition physical source instead of
  candidate overlay.
- E005: Legacy question ids repeat in different sections.
- E006: Legacy question references an unknown field or removed section.
- E007: Incomplete section has no declared question and insufficient fallback
  metadata.
- E008: Multiple missing fields make fallback target ambiguous.
- E009: Question wording changes but semantic target does not.
- E010: Semantic target changes while an unanswered, answered or applied record
  exists.
- E011: Answer does not conform to scalar/enum/assumption/disposition contract.
- E012: Non-owner attempts answer, defer, mute, reopen or apply.
- E013: Owner replaces an answer without expected revision.
- E014: Definition, question, permission, schema or lock changes after preview.
- E015: Apply crashes before staging, after journal, before first replace,
  between targets or before lock cleanup.
- E016: Two processes apply the same preview concurrently.
- E017: Client loses successful apply response and retries the same token.
- E018: Token is reused for another actor or candidate.
- E019: Cursor is reused after snapshot drift.
- E020: Deferred trigger is absent, malformed or no longer applicable.
- E021: Question state exists on v2 but lock binding is stale.
- E022: Definition `open_questions` are reintroduced on v2.
- E023: Decision-context source sees answered/applied question content.
- E024: Next actions contain curated action equivalent to generated gap action.
- E025: Freshness audit reports only curated/owner node stale.
- E026: Release runtime is rolled back after workspace migration.
- E027: Repository migration succeeds but deterministic outputs remain stale.
- E028: Deterministic refresh succeeds while curator/publication review remains
  stale by design.
- E029: Active software spec is stale but historical specs are unchanged.
- E030: Alignment discovers an artifact without an owning primitive.
- E031: Editable source import/version is current while installed package
  metadata reports a historical version or location.
- E032: Execution stops after immutable tag publication but before release
  workflow completion or published-asset verification.
- E033: A downloaded release asset has an unexpected hash/content or a local
  build shadows the selected published runtime.
- E034: Tool orchestration is interrupted while migration apply is still alive
  and owns the workspace lock.
- E035: Git commit, runtime artifact, owner input or canonical fingerprint
  changes after plan review and before apply.
- E036: An aggregate artifact class is stale while some owned items remain
  current and must stay byte-stable.

## Acceptance Criteria

- AC001: Typed gap tests cover every class, priority and deterministic tie-break.
- AC002: Snapshot tests prove one capture/read/hash/parse per source and no
  post-snapshot reads.
- AC003: Existing readiness review remains callable and default output is
  bounded with explicit truncation.
- AC004: Every incomplete required section yields a declared/fallback question
  or `no_safe_question`.
- AC005: Project-question identity survives wording/audit drift and changes on
  semantic-target replacement only through supersession.
- AC006: Lifecycle tests cover every allowed/rejected transition and authority.
- AC007: Non-owner and free-form owner-source attempts produce no write.
- AC008: Answer tests prove no definition, assumption, decision or completion
  mutation occurs.
- AC009: Candidate preview is read-only and includes both target candidates and
  every relevant source/policy fingerprint.
- AC010: Failure injection at every replacement proves no partial applied state.
- AC011: Exact committed retry returns `already_applied`; divergent reuse fails.
- AC012: Concurrency tests produce at most one commit.
- AC013: Reconciliation tests cover wording, target, section, profile/module and
  lock changes without answer copying.
- AC014: Next actions surface the highest actionable gap and avoid self-loops.
- AC015: Progress keeps independent definition/evidence axes and no aggregate
  question percentage.
- AC016: Freshness distinguishes question-only from definition-apply impact.
- AC017: Decision-context tests prove project questions are always inactive
  metadata/evidence and definition is not double-counted.
- AC018: CLI text/JSON and MCP read tools are semantically equivalent where
  shared.
- AC019: MCP catalog and handlers contain no project-question write tool.
- AC020: Cursor tests prove stable pages and explicit `stale_cursor`.
- AC021: Workspace status distinguishes v0, upgradeable v1, v2, ahead, invalid
  and recovery-required.
- AC022: Legacy-to-v1 regression fixtures remain byte/semantically stable after
  handler extraction.
- AC023: V1-to-v2 plans never contain legacy bootstrap-owned operations.
- AC024: Operation registry tests prove every governed write is classified and
  unknown writes fail closed.
- AC025: V1-safe writes work under the v2 runtime while v2-only writes fail
  before migration.
- AC026: Fresh initialization creates valid schema v2 and empty question state.
- AC027: Migration preserves every valid legacy question exactly once and never
  infers a closed state from absence.
- AC028: Ambiguous legacy mapping blocks without partial write.
- AC029: Migration atomically creates questions, empties definition open
  questions and commits schema v2 last.
- AC030: Migration apply/retry/rollback/resume/recovery fixtures pass.
- AC031: V2 validation rejects legacy question reintroduction and unsupported
  definition question patch operations.
- AC032: 100-proposal access and payload budgets pass without network/cache.
- AC033: Focused service, migration, CLI and MCP suites pass.
- AC034: `./scripts/test-public.sh` and `./scripts/test-full.sh` pass.
- AC035: `p2p validate` and version-consistency/build gates pass.
- AC036: Clean-environment smoke proves fresh v2 and upgradeable v1 workflows.
- AC037: Release/deploy order makes v2-capable runtime available before any
  workspace migration.
- AC038: Repository baseline and reviewed v1-to-v2 dry run are recorded before
  apply.
- AC039: Repository migration uses supported owner-confirmed CLI and leaves no
  active lock/recovery transaction.
- AC040: Repository pilot exposes assumptions, decisions and
  risks/alternatives/decisions without fabricated answers.
- AC041: Read-only artifact-alignment audit classifies all material artifacts and
  identifies owning primitive or explicit missing primitive.
- AC042: Only stale deterministic artifacts are refreshed; curated/owner stages
  remain independently stale until their lifecycle runs.
- AC043: Agent instructions and public docs match implemented schema, authority,
  CLI, MCP and migration behavior.
- AC044: Post-alignment comparison explains changed hashes/counts/diagnostics and
  residual legacy/owner-controlled state.
- AC045: Final Git diff contains no manual `.p2p` repair, unexplained generated
  drift or unsupported output placement.
- AC046: A local implementation evidence report records design choice,
  compatibility impact, behavior/files/tests, release/migration results, risks
  and deferred work.
- AC047: Release evidence proves the same `0.3.0` source on clean Python 3.11 CI
  and an isolated Python 3.14 published-wheel smoke without changing the local
  interpreter.
- AC048: M1 records and uses the downloaded published-wheel hash; a local build
  path or stale editable metadata cannot silently select the pilot runtime.
- AC049: An interrupted release or migration resumes from inspected checkpoints
  without duplicate tag publication, duplicate apply or manual lock deletion.
- AC050: Two unchanged full plans produce the same fingerprint and deterministic
  digest bound to Git commit, runtime hash and canonical fingerprint.
- AC051: Apply evidence includes process/session identity and exit status; post-
  apply validation starts only after process completion and recovery is clear or
  explicitly owned by a supported recovery command.
- AC052: Post-v2 question evidence proves actor/revision/provenance/lock binding,
  no fabricated answer/application and the expected question-or-no-safe outcome
  for all three repository pilot gaps.
- AC053: Alignment leaves pre/post current nodes byte-stable unless a changed
  source contract makes them stale, and evaluates aggregate software-spec state
  per Change Set.
- AC054: Source version, imported runtime version, package metadata and Python
  interpreter are either consistent or recorded as an explicit non-blocking
  advisory; no environment reinstall is performed implicitly.
- AC055: Final handoff identifies the exact published release artifact, runtime
  contract, workspace schema and remaining intentionally owner-controlled or
  optional stale nodes without ambiguous readiness claims.
