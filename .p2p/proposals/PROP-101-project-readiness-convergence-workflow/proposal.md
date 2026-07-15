# PROP-101 - Project Readiness Convergence Workflow

## Status

`accepted`

## Problem

P2P Engine can diagnose project readiness but cannot yet drive a project from a diagnosed vertical gap to an auditable owner-reviewed update. The current review identifies incomplete capisaldi, declared evidence and unmapped proposals, but its convergence behavior is incomplete:

- it returns generic advice to complete the definition and rerun the review;
- some required incomplete sections have no applicable generated question;
- there is no persistent project-level question lifecycle equivalent to the proposal-question workflow;
- owner answers are not connected to a governed candidate project-definition patch;
- project-definition gaps are not coherently prioritized in managed next actions;
- large legacy proposal lists are emitted without bounded detail or prioritization;
- progress, readiness and freshness expose useful but separate states without an orchestration contract that closes the loop.

The result is a system that knows what is incomplete but still depends on an agent or owner to reconstruct the next workflow manually across multiple commands and sessions.

The implementation risk is broader than question generation. A naive implementation could create competing authority between project-question state, project definition, decision context, managed next actions and workspace migration state. It could also reuse the existing single-file definition apply in a way that leaves question and definition state partially committed, or register a v1-to-v2 migration while still executing the current legacy-to-v1 bootstrap planner.

## Current Evidence

The current repository is aligned to workspace schema v1 and uses the locked `software_project` vertical. Its durable project definition contains 19 required sections: 16 are complete, `assumptions` is assumed, and `decisions` plus `risks_alternatives_decisions` are partial. There are no missing required structured fields, but the three non-complete section states remain readiness gaps.

The current review produces one broad owner question for `risks_alternatives_decisions`, but no section-specific question for `assumptions` or `decisions`. It also reports 88 intentionally legacy unmapped proposals. Managed next actions currently prioritize publication review, an active Change Set and draft-proposal work rather than the incomplete project definition.

The code contains capabilities that can be composed, but not all final contracts:

- vertical packs, locks and readiness review from `PROP-085` and `PROP-090`;
- durable project definition plus structured preview/apply from `PROP-090`;
- question authority and answered-versus-applied semantics from `PROP-089` and `PROP-096`;
- generated and curated next actions from `PROP-079`;
- independent definition/evidence progress axes and derived freshness;
- authority-aware decision context from `PROP-100`;
- forward-only transactional workspace migration primitives.

The current definition apply writes only the project-definition target. Atomic convergence therefore requires a coordinated multi-target apply above its pure rendering and validation logic, not two sequential service writes. The current workspace compatibility planner is also specialized around the undeclared-legacy-to-v1 bootstrap. Schema v2 requires transition-specific planning and candidate ownership rather than only adding a registry entry.

## Goals

- Model project-readiness gaps as typed, prioritized and explainable records.
- Give each actionable required-section gap a declared question, a safe deterministic fallback or an explicit no-question diagnostic.
- Persist project-question lifecycle state, revisions, authority and provenance across sessions.
- Keep question answers distinct from applied project definition and owner decisions.
- Render owner-reviewable candidate definition patches and commit definition plus question state through one transaction.
- Integrate the highest-priority project gap into managed next actions.
- Preserve independent definition completeness and declared evidence coverage.
- Keep CLI and MCP contracts deterministic, bounded and semantically aligned.
- Preserve schema-v1 valid operations and provide a real transition-specific v1-to-v2 migration.
- Reconcile project questions safely across vertical revisions without re-opening or losing owner evidence.
- Preserve `PROP-100` authority by keeping unapplied question state non-semantic.
- Validate generic behavior against this repository without embedding repository-specific policy.

## Non-Goals

- Agents do not make owner decisions, fabricate owner answers, validate assumptions, complete sections, accept proposals or approve publication.
- This proposal does not replace proposal readiness or proposal questions.
- It does not create a second project definition, maturity, progress, next-action, decision-context or freshness engine.
- It does not automatically declare vertical coverage for legacy proposals.
- Heuristic matches never become owner-declared evidence automatically.
- It does not introduce database-backed persistence, a remote registry or hosted orchestration.
- It does not perform automatic agent curation, publication review or vertical upgrades.
- It does not remove schema-v1 compatibility, migrate implicitly or bypass the workspace migration lifecycle.
- It does not use clock-based preview expiry without an explicit durable preview-receipt contract.
- It does not treat migration absence of a legacy question as evidence that a question was answered or applied.

## Proposal

Introduce a `Project Readiness Convergence` application service above the project vertical, definition, question-state, permission, migration, next-action, progress, freshness and decision-context services. It owns orchestration and result composition, while existing services retain authority over their canonical data.

The convergence service must be request-scoped or explicitly invalidated. It must load one immutable source snapshot and must not retain stale definition, lock, question, evidence or schema state through the memoized workspace service facade.

### Contract 1 - Typed Gap Inventory

A gap record must include at least:

- stable gap id and policy version;
- snapshot fingerprint;
- vertical id, version, lock checksum and section id;
- gap kind, severity, applicability and lifecycle condition;
- definition status and missing fields;
- declared evidence references and separately labelled heuristic suggestions;
- assumption, blocker or owner-decision state when applicable;
- required authority and whether owner input is needed;
- current question reference and revision, if any;
- deterministic next operation and explanation;
- source hashes needed for stale detection.

Initial gap classes must distinguish:

- blocked required section;
- unresolved owner decision;
- incomplete required project definition;
- assumption requiring validation;
- answered question not yet applied;
- stale or incompatible question/definition state;
- optional declared-evidence curation;
- informational legacy or heuristic state.

Priority is versioned, deterministic and explainable. The order confirmed in Q004 is:

1. integrity, compatibility and authority blockers plus explicit owner-decision blockers;
2. owner answers already received but not yet applied;
3. incomplete required definition sections;
4. assumptions to validate ordered by declared dependency impact;
5. optional declared-evidence curation;
6. informational legacy state.

Within one class, vertical section priority and stable gap or question id provide tie-breaking. Results expose class, rationale and tie-break inputs instead of an opaque aggregate score. Missing dependency metadata must use a documented neutral fallback and must not be inferred from free text.

### Contract 2 - Project-Question Persistence And Identity

Project questions are distinct from proposal questions. They are linked to active vertical sections and project-definition gaps, not to proposal readiness criteria.

Workspace schema v2 owns one registered project-question artifact contract at a deterministic engine-managed location. The exact path, root key and artifact schema version must be declared in feature specifications and owned by one `ProjectQuestionStateService`; callers and adapters may not derive alternate paths.

Each record preserves:

- stable question id and stable identity key;
- question revision and presentation-text hash;
- group and gap id;
- vertical section and target field, assumption, blocker or owner-decision reference;
- priority and rationale;
- declared, deterministic-fallback or migrated-legacy source type;
- source vertical id/version/checksum and fallback policy version;
- current lifecycle state and applicability;
- answer revisions, provided-by authority, recorded-by actor and provenance;
- created, updated, answered, applied and terminal timestamps;
- apply operation, preview and definition references;
- transition history and supersession links.

Stable identity is based on semantic target, not wording or audit timestamps. It includes vertical id, section id, gap kind, target field or domain object, and declared question id or deterministic fallback key. Vertical checksum, wording hash and policy version identify a revision but do not by themselves create a new identity.

Wording-only changes preserve identity, answer and lifecycle state while appending a revision. A changed semantic target creates a replacement and supersedes the old question. Reassessment cannot reopen closed work merely because wording, ordering or audit metadata changes.

### Contract 3 - Lifecycle And Transition Matrix

Steady lifecycle states are:

- `to_answer`;
- `answered`;
- `applied`;
- `deferred`;
- `muted`;
- `retired`;
- `superseded`.

`reopen` is an audited transition back to `to_answer`, not a transient steady state. Compatibility or vertical drift is represented by applicability and diagnostics until explicit reconciliation retires or supersedes the affected record.

Required transitions are:

- deterministic initialization or reconciliation may create `to_answer` records without owner content;
- `to_answer` may become `answered`, `deferred`, `muted`, `retired` or `superseded`;
- `answered` may become `applied`, `deferred`, `muted`, `retired` or `superseded`;
- `deferred` may return to `to_answer` only through explicit owner reopen or a declared machine-evaluable trigger;
- `muted` may return to `to_answer` only through explicit owner action;
- `applied`, `retired` and `superseded` are terminal for that revision;
- later definition drift creates a new gap or replacement question rather than rewriting applied history.

Every transition has a source-state allowlist, target-state allowlist, required role, consent class, reason requirement, provenance requirement and side-effect policy. Invalid transitions fail before writes.

Authority is explicit:

- system reconciliation may create questions and deterministically retire or supersede inapplicable records, but it cannot create owner answers or erase answer history;
- owner authority is required to provide or replace an answer, defer, mute, explicitly reopen, validate an assumption, resolve an owner decision and confirm apply;
- an agent or client may record a verbatim owner-provided answer only through an explicit authorized write path that distinguishes `provided_by` from `recorded_by` and preserves the owner evidence or consent receipt;
- a free-form `source=owner` or caller-supplied actor string is not sufficient authority;
- read, next-question and preview operations may be available to non-owner known actors because they do not mutate owner truth;
- MCP write tools remain deferred and, when introduced, delegate to the same authority matrix.

### Contract 4 - Declared And Fallback Question Selection

Question resolution first uses an applicable question declared by the active locked vertical. When a required incomplete section has none, the engine may generate only a conservative deterministic fallback from declarative metadata such as section purpose, target field, missing required fields and completion criteria.

Fallback policy, template key and identity algorithm are versioned. A fallback remains a question and cannot answer owner input, validate assumptions, resolve decisions or complete a section. If safe generation is impossible, the engine emits a machine-readable `no_safe_question` diagnostic and does not invent content.

One gap may have multiple declared questions only when the vertical explicitly models independent semantic targets. Reassessment deduplicates by stable identity and never creates an unbounded sequence of fallback questions for the same target.

### Contract 5 - Answered Versus Applied Authority

Recording an answer must never update project definition, resolve an owner decision, validate an assumption or mark a section complete. An answer is received owner evidence pending a separate synthesis and apply decision.

Application is a separate workflow:

1. load one immutable convergence snapshot;
2. select answered questions eligible for application;
3. render a structured project-definition candidate using pure definition rendering and validation functions;
4. render the matching project-question candidate with apply references;
5. validate section ids, field ids, status transitions, assumptions, provenance and complete candidate closure;
6. show semantic diff, affected gaps and expected downstream freshness changes;
7. issue a preview token bound to operation, actor, both source preimages, question-state hash, definition hash, vertical lock checksum, both candidate hashes and all relevant policy versions;
8. require explicit owner-confirmed apply;
9. commit definition and project-question candidates in one lock-protected multi-target transaction;
10. return commit hashes, resulting gap state and downstream rebuild plan.

The existing project-definition service remains authoritative for definition parsing, pure candidate rendering and validation. Its current single-target apply endpoint must not be called followed by a second question-state write. The convergence service must submit both validated candidates to one `AtomicMutationWriter` operation. Compensating rollback between independent commits is not an accepted normal design.

Failure before commit changes nothing. Failure during replacement must use the durable transaction rollback/recovery mechanism. `applied` question state is present only in the same committed candidate set as the corresponding definition change.

### Contract 6 - Preview Token, Retry And Concurrency

The initial contract uses source-bound deterministic previews, not undefined clock expiry. Preview identity includes actor explicitly; audit timestamps and generated observation times are excluded from semantic candidate hashes.

Apply behavior is:

- changed actor, lock, definition, question state, candidate or policy returns a typed stale or mismatched-preview result;
- concurrent apply is serialized by the workspace mutation lock and rechecks physical preimages under lock;
- a retry of the same successfully committed operation, token, actor and candidate returns `already_applied` with the original apply reference and hashes;
- reuse of a token against different source state, actor or candidate is rejected;
- a token from a rolled-back transaction may be retried only after recovery status is clear and all original preconditions still match;
- introducing time-based expiry later requires an explicit preview-receipt contract with issued-at, expires-at, persistence and cleanup semantics.

This contract avoids treating an apply response lost after commit as an unsafe replay while still preventing a token from authorizing different state.

### Contract 7 - Vertical Change Reconciliation

Question records remain bound to the vertical identity that generated them. A changed lock invalidates outstanding previews immediately. Question reconciliation is a separate deterministic operation after an explicit vertical selection or upgrade.

Reconciliation rules are:

- unchanged semantic identity with wording-only changes preserves state and appends a revision;
- changed target field, gap kind or completion semantics supersedes the old question and creates a replacement without copying an answer automatically;
- removed or no-longer-required sections retire unanswered questions and preserve answered/applied history;
- answered questions made inapplicable remain visible and cannot be applied;
- newly required fields or sections produce new gaps and declared/fallback questions;
- section aliases or remapping require an explicit declarative migration rule; fuzzy or text-based remapping is forbidden;
- no vertical change validates assumptions, completes sections or rewrites applied definition content automatically.

Tests must cover section add/remove/rename, question wording change, semantic question change, lock-only drift, profile/module changes and unanswered/answered/applied records.

### Contract 8 - Managed Next Actions

The convergence result becomes a generated input to the existing managed next-action service. It must not create a second next-action file or bypass curated action history.

Generated readiness actions have stable kind/target identities and deduplicate against existing generated or curated work. A true blocker or required project-definition gap cannot be displaced by bulk legacy evidence curation. The only recommended action must not be to rerun the same readiness review when a specific next question, migration, reconcile or preview operation is available.

Deferred and muted questions are respected without hiding the residual gap. Owner-controlled publication review remains separate. The feature must not recommend approval merely to make freshness green.

### Contract 9 - Progress, Freshness And Decision Context

Definition completeness and declared proposal-evidence coverage remain separate axes. Question progress may be reported as descriptive counts, but it must not become a third percentage that silently overrides either axis.

A successful convergence apply updates only the directly involved canonical definition and question state. Freshness is determined from source and policy fingerprints; the apply result reports dependent derived nodes as stale and returns their deterministic topological rebuild plan. It does not automatically run deterministic refreshes, agent-curated stages, publication stages or owner-review actions.

The project-question artifact is registered in the decision-context Source Catalog with a dedicated source kind. Unapplied answers, lifecycle state and question history are quality metadata or inactive governed evidence. They may be retrieved with explicit pending authority but cannot create active decisions, constraints, relations or project-definition claims. Only content committed to project definition receives existing project-definition semantic authority. Applied questions retain traceability links without double-counting the same content.

The freshness graph must distinguish question-only mutations from definition apply. An answer can stale readiness/next projections without making semantic project projections authoritative; a definition apply stales every dependent definition-derived node.

### Contract 10 - Bounded CLI And MCP Surfaces

The existing `p2p project readiness review` remains backward-compatible while gaining structured gap summaries. Candidate CLI capabilities include gap list/detail, question status/next/answer/defer/mute/reopen, reconcile, preview/apply and schema-gate diagnostics under the project-readiness namespace. Exact command names are implementation-spec decisions and must preserve existing public commands.

Default text output shows counts and a bounded top-action list. Full unmapped proposals, heuristic suggestions and question history require explicit detail, limit and cursor. Ordering is stable.

Pagination cursors are opaque and bind collection kind, ordering policy, last stable key and convergence snapshot fingerprint. A cursor used after source drift returns `stale_cursor` and a restart instruction rather than silently skipping or duplicating records. Feature specifications define default and maximum page sizes.

MCP initially receives read parity only after core service and CLI payloads stabilize. Project-question answer/apply MCP tools are deferred to a later gated slice. Any later write tool is an explicit write-safe adapter over the same permission checks, preview token, source preconditions, stale detection, authority rules, atomic transaction and result serialization used by CLI. MCP handlers contain no independent domain, ranking or mutation logic.

### Contract 11 - Workspace Schema v1/v2 Compatibility

Schema v2 is an explicit upgrade target and schema-v1 workspaces remain backward-compatible and migratable.

A v2-capable runtime must distinguish:

- undeclared legacy workspace v0;
- declared schema v1 that is valid and upgradeable;
- current schema v2;
- schema ahead of the runtime;
- invalid, incomplete and recovery-required state.

Declared v1 must report an actionable upgrade status rather than being conflated with incomplete legacy bootstrap. The status includes current/target versions, transition path, runtime inspect/plan/apply support and the exact plan command.

Migration architecture must dispatch each adjacent transition to a registered transition handler. A handler owns inventory interpretation, owner-input requirements, candidate rendering, validators and allowed targets for that transition. Multi-step planning composes handlers over a candidate workspace overlay in order. Adding `workspace-v1-to-v2` must not execute domain, permissions, metadata or vertical bootstrap operations owned by `workspace-legacy-to-v1`.

The v1-to-v2 transition is forward-only, dry-run plannable, transactionally applicable, idempotent and recoverable. It owns only schema-v2 question-state initialization, any explicitly declared definition cleanup required to remove competing question authority, workspace schema/history updates and required derived-staleness reporting. Unknown artifacts are preserved.

Migration of legacy definition questions obeys Contract 12. Migration never occurs through validation, readiness, status, ordinary definition writes or unrelated artifact initialization.

Every read and governed write whose canonical contract remains valid under v1 stays available. Only v2-dependent operations are blocked before migration. The common governed-write boundary, not individual CLI handlers, classifies operations by minimum schema version and returns current/required version, reason and migration plan command with no partial write.

Feature specifications must define the v1/v2 runtime support matrix, fresh-workspace behavior, transition-handler protocol, migration fixtures and operation-level minimum-schema classification.

### Contract 12 - Legacy Question Migration

The v1-to-v2 migration treats `definition.yml` open questions as legacy source evidence, not as complete lifecycle history.

Deterministic mapping rules are:

- every valid open legacy question maps to a v2 question record with migrated provenance and initial `to_answer` state unless explicit v1 data proves a stronger state;
- absence from `open_questions` never implies answered, applied, deferred, muted or retired;
- no answer, owner decision, assumption validation or completion state is invented;
- stable v2 identity is section-scoped and does not reuse local `Q001`-style ids as globally unique ids;
- matching declared vertical question ids and target fields are used when unambiguous;
- duplicate ids, unknown sections/fields, conflicting texts and malformed statuses produce typed diagnostics and block lossy migration;
- incomplete required sections with no legacy question are evaluated through the declared/fallback policy and receive `to_answer` records or `no_safe_question` diagnostics;
- completed or not-applicable sections do not receive new questions solely because the vertical contains a generic declared question;
- migration candidate validation proves one-to-one preservation of every migrated legacy question.

The v1-to-v2 transaction copies every valid legacy question into the dedicated artifact and normalizes `definition.yml` `open_questions` lists to empty in the same commit. Transaction originals preserve rollback evidence; no writable compatibility shadow remains. In a v2 workspace, validation rejects non-empty legacy definition questions and the legacy definition patch operations `add_open_question` and `close_open_question` are unavailable with an actionable project-question command. Those operations remain available in valid v1 workspaces until explicit migration. Last-write-wins or bidirectional synchronization is forbidden.

Fresh v2 workspaces create a valid empty question-state contract during initialization and seed/reconcile project questions only when an active vertical and definition snapshot are available.

### Contract 13 - Performance And Snapshot Discipline

One readiness request builds one source snapshot. Gap classification, question selection, next-action projection and pagination operate from that snapshot without reopening proposal or decision files.

Performance acceptance is based primarily on deterministic access budgets:

- one discovery pass per source class;
- at most one read/hash/parse per included source per snapshot;
- zero filesystem reads during sorting, pagination and serialization after snapshot construction;
- bounded default payload and bounded question/unmapped detail;
- no repeated full decision-context rebuild when only readiness inputs are required.

Wall-clock ceilings may supplement but not replace access-count and payload-size assertions. The representative fixture contains at least 100 proposals and adversarial legacy, heuristic and question-history volume.

### Contract 14 - Repository Pilot

The current `assumptions`, `decisions` and `risks_alternatives_decisions` gaps form the first end-to-end pilot. The pilot must demonstrate supported question selection, owner answer recording, preview, apply or explicit defer/mute, progress recomputation, next-action convergence and freshness reporting.

An explicit governed `deferred` or `muted` outcome may converge question state when evidence is unavailable or the owner declines the question for now. The transition records actor, reason, timestamp and provenance and remains reopenable under Contract 3. Neither outcome completes a section, resolves the underlying gap, validates an assumption or increases definition/evidence progress. Pilot results distinguish `question_state_converged` from `definition_complete` and continue exposing residual partial, assumed or blocked state.

Before the pilot, this repository is upgraded from schema v1 to v2 using only supported plan/apply/recovery commands. The migration plan and post-migration validation become pilot evidence. Repository-specific content is evidence only. Generic priority, fallback, migration and completion rules are also tested with synthetic verticals, an uninitialized workspace, a v1 fixture and a workspace with no proposal coverage.

## Alternatives Considered

### Stateless Review Improvements

Improving messages without persistence is smaller but cannot preserve owner answers or answered-versus-applied state across sessions. It does not solve convergence.

### Questions Embedded In Project Definition

This provides one file but couples frequent interview transitions to definition writes and preview hashes. It also makes unanswered evidence appear alongside applied definition truth. The owner selected dedicated state instead.

### Synthetic Project Proposal

Reusing proposal questions through a synthetic proposal would conflate project definition and proposal governance.

### Sequential Definition Then Question Writes

This could reuse existing endpoints unchanged but cannot prove atomic answered-to-applied convergence. It is rejected in favor of one multi-target transaction.

### Generic Registry Entry Without Transition Handler

Adding only v1-to-v2 metadata would route schema v2 through a planner currently specialized for legacy bootstrap. It is rejected in favor of transition-specific handlers and candidate overlays.

### Single-Use Tokens With No Retry Result

Blindly rejecting every repeated token makes an apply response lost after commit indistinguishable from an attack. The selected contract returns `already_applied` only for an exact committed operation and rejects divergent reuse.

### Agent-Only Orchestration Or Automatic Apply

Agent guidance lacks deterministic cross-session state, while automatic apply collapses evidence, synthesis and owner confirmation. Both are excluded.

## Trade-Off Analysis

A durable project-question lifecycle adds state and validation complexity but eliminates conversational reconstruction and supports multi-agent continuity. Separating question state from definition state improves authority clarity but requires coordinated transactions and an explicit migration. Transition-specific migration handlers require refactoring current legacy planning but prevent future schema upgrades from replaying unrelated bootstrap behavior. Idempotent retry requires apply references in question history but is safer than ambiguous token reuse. Bounded cursor contracts and access budgets add API detail but prevent unstable pagination and repeated scans. Deferring MCP writes reduces initial surface area but keeps one canonical mutation path.

## Risks And Mitigations

- Competing question and definition sources: field authority, one-way apply, v2 migration cleanup and divergence diagnostics.
- Unauthorized owner evidence: operation-level authority matrix, distinct provided-by/recorded-by and no free-form owner source assertion.
- Stale application: bind preview to actor, all canonical source preimages, lock, candidates and policy versions.
- Partial writes: one durable multi-target transaction; sequential commits are forbidden.
- Ambiguous retry: exact committed replay returns `already_applied`; divergent reuse is rejected.
- Legacy migration loss: one-to-one mapping validation, preserve unknowns and block ambiguous transformations.
- Migration planner leakage: adjacent transition handlers own disjoint candidate targets and validators.
- Question loops: stable semantic identity, revisions, transition guards and deterministic deduplication.
- Vertical drift: explicit reconciliation with retirement/supersession and no automatic answer copying.
- Priority distortion: separate blocker, definition and evidence classes.
- Unbounded output: snapshot-bound cursor, explicit limits and maximum page size.
- Decision-context authority leakage: pending questions remain inactive metadata until definition apply.
- Cross-service duplication: one convergence result consumed by thin adapters.
- Performance regression: one immutable request snapshot and deterministic source-access budgets.
- Pilot overfitting: synthetic cross-vertical, v1 migration and empty-workspace fixtures.

## Assumptions And Constraints

Assumptions to validate in feature design:

- pure definition rendering/validation can be extracted without changing current definition semantics;
- managed next actions can consume one additional generated action source without breaking curated/generated deduplication;
- transition handlers can compose through the existing candidate workspace abstraction without weakening recovery;
- the freshness graph can classify question-only and definition-apply changes separately.

Established constraints:

- active vertical section ids and lock identity are the section reference basis;
- proposal and project questions remain separate scopes;
- Markdown and YAML remain sufficient canonical storage;
- heuristic mappings remain advisory;
- owner and agent-curated actions are never automatic side effects;
- all `.p2p` writes use CLI or explicit write-safe MCP primitives;
- workspace migrations are forward-only and preserve unknown artifacts;
- schema-v1 valid operations remain available until explicit migration;
- question/definition apply is one canonical transaction and rebuild remains separate.

## Owner Decisions Recorded

- Q001: use dedicated project-question lifecycle state as authority for status, owner answers and history; definition remains authoritative only for applied content.
- Q002: preserve schema-v1 compatibility and define explicit, planned, owner-confirmed, transactional and recoverable v1-to-v2 migration.
- Q008: keep every v1-valid read and governed write available; block only v2-dependent operations before migration.
- Q003: use locked-vertical questions first, deterministic metadata-derived fallback second, and `no_safe_question` when neither is safe.
- Q004: use the six-class priority policy with answered-not-applied work before new definition gaps.
- Q005: atomically update canonical definition/question state, then report stale derived nodes without rebuilding them automatically.
- Q006: stabilize core/CLI and MCP read parity first; defer MCP writes to a later canonical-path gate.
- Q007: allow governed defer/mute to converge interview state while preserving residual definition truth.
- Post-definition owner instruction: incorporate the code-audit refinements needed for robust migration dispatch, legacy mapping, atomic apply, operation authority, replay handling, vertical reconciliation, decision-context authority and bounded pagination.

## Remaining Owner Questions

None. Implementation specifications must resolve named technical contracts without weakening the recorded owner policies. A new owner question is required only if implementation evidence demonstrates a genuine policy choice not covered here.

## Impact And Overlap

This proposal depends on and extends `PROP-085` and `PROP-090`; it does not reopen their accepted MVP and hardening decisions. It reuses semantics from `PROP-089` and `PROP-096`, integrates with `PROP-079`, preserves governance from `PROP-091`, uses migration infrastructure from `PROP-095` and `PROP-097`, and extends `PROP-100` Source Catalog/freshness classifications without making the derived index canonical.

Expected implementation impact includes project vertical and question core models, pure definition candidate rendering, convergence orchestration, permissions and lifecycle authority, mutation preview, atomic transactions, workspace schema/status, migration registry/handlers/planner, candidate workspace validation, project progress, managed next actions, freshness, decision-context source classification, CLI project operations, MCP read handlers/catalog, filesystem facade, validation, agent templates, documentation and tests.

No mutually exclusive accepted proposal has been identified. The principal overlap risk is implementation duplication, controlled by one owner per canonical state and thin adapters over a single convergence result.

## Delivery Slices And Exit Gates

### S1 - Gap Contracts, Snapshot And Priority

Implement immutable snapshot, typed gaps, policy versions, stable identity, deterministic ordering, evidence separation and bounded serialization. Exit when representative ordering, source-access and definition/evidence independence tests pass.

### S2 - Schema Status And Transition Handler Architecture

Refactor workspace status and migration planning to distinguish v0/v1/v2 and dispatch adjacent transition handlers over candidate overlays. Exit when a synthetic v1-to-v2 handler cannot invoke legacy-to-v1 operations and multi-step plans remain deterministic.

### S3 - Project-Question Artifact And Legacy Migration

Implement the v2 artifact contract, lifecycle parser/validator, stable identity/revisions, fresh-workspace behavior and deterministic legacy question mapping. Exit when ambiguous migration blocks without loss and every valid legacy question is preserved exactly once.

### S4 - Question Selection, Lifecycle And Authority

Implement declared/fallback selection, transition matrix, provided-by/recorded-by authority, defer/mute/reopen and vertical reconciliation. Exit when no required incomplete section disappears silently and unauthorized actors cannot create owner evidence.

### S5 - Governed Multi-Target Convergence

Extract pure definition candidate rendering, build definition/question candidates, bind previews and commit through one transaction. Exit when failure injection at every replacement point proves no partial applied state.

### S6 - Retry, Concurrency And Semantic Hashing

Implement actor-bound tokens, audit-neutral semantic hashes, exact `already_applied` retry and divergent replay rejection. Exit when response-loss, concurrent apply, rollback and recovery scenarios are deterministic.

### S7 - Operational And Decision-Context Integration

Integrate one convergence result into next actions, progress, freshness and decision-context source classification. Exit when pending answers cannot acquire semantic authority and no review loop or automatic owner/curator side effect exists.

### S8 - CLI, Pagination And MCP Reads

Stabilize backward-compatible CLI text/JSON, snapshot-bound cursors, detail limits and MCP read parity. Exit when stale cursors fail explicitly and default outputs remain bounded.

### S9 - Compatibility Matrix, Robustness And Pilot

Complete operation-level schema gates, migration/failure/vertical/adversarial fixtures and access-budget tests, then upgrade and exercise this repository through supported commands. Exit with global validation, no manual `.p2p` edits and explicit residual-state reporting.

## Acceptance Criteria

1. Readiness returns deterministic typed gaps with explicit kind, severity, authority, evidence basis, snapshot fingerprint and next operation.
2. Blockers, definition gaps, assumptions, answered-not-applied work, optional evidence and informational legacy state remain distinguishable.
3. Every required incomplete section produces an applicable declared/fallback question or `no_safe_question` diagnostic.
4. Project-question state persists lifecycle, revision, provenance, authority and history without conflation with proposal questions.
5. Stable identity excludes wording and audit timestamps; wording-only reassessment cannot reopen or duplicate work.
6. A documented transition matrix rejects invalid states before writes and defines authority for every mutation.
7. Caller-controlled `source=owner` or actor strings cannot create owner-confirmed answer authority by themselves.
8. Answers do not change definition, validate assumptions or resolve owner decisions by themselves.
9. Candidate preview includes semantic diff, affected gaps, both candidate hashes and all canonical source preconditions without writing state.
10. Apply requires owner authority and a token bound to actor, definition, question state, vertical lock, both candidates and policy versions.
11. Definition and question state commit through one multi-target transaction; sequential canonical commits are not used.
12. Failure injection proves no committed definition can reference an unapplied question and no applied question can lack its definition commit.
13. Exact retry after a successful commit returns `already_applied`; divergent token reuse, changed locks and changed sources are rejected.
14. Audit timestamps and generated observation times do not destabilize semantic hashes or retries.
15. Vertical reconciliation preserves wording-only revisions, supersedes semantic changes, retires removed targets and never copies answers automatically.
16. Managed next actions surface the highest-priority actionable project gap with stable deduplication and no self-loop when a concrete operation exists.
17. Deferred and muted questions suppress re-ask according to policy without hiding residual project gaps.
18. Definition completeness and declared evidence coverage remain independent; question counts do not become an aggregate readiness percentage.
19. Freshness reports downstream impact and never auto-runs refresh, curation, publication or owner review.
20. Project-question sources are cataloged as inactive metadata/evidence until definition apply and cannot create active decisions or duplicate applied content.
21. Default CLI/MCP output is bounded; full legacy/history detail requires explicit limit and snapshot-bound pagination.
22. A cursor used against a changed snapshot returns `stale_cursor` rather than inconsistent continuation.
23. A v2 runtime distinguishes undeclared v0, upgradeable v1, current v2, ahead, invalid and recovery-required workspaces.
24. Migration planning dispatches transition-specific handlers; v1-to-v2 never executes legacy-to-v1 bootstrap ownership.
25. The v1-to-v2 transition is registered, forward-only, dry-run plannable, transactional, idempotent and recoverable.
26. Every valid legacy open question is preserved once with section-scoped identity; absence never fabricates an answered/applied state.
27. Ambiguous legacy ids, sections, fields, statuses or texts produce typed blocking diagnostics without partial migration.
28. The v1-to-v2 transaction copies legacy questions and normalizes definition `open_questions` to empty atomically; v2 validation rejects their reintroduction and only the dedicated artifact remains authoritative.
29. Every v1-valid read/write remains available and each v2-dependent operation is blocked centrally before writes with actionable migration diagnostics.
30. Fresh v2 workspace initialization and later vertical selection create/reconcile valid question state without implicit owner content.
31. CLI and MCP read payloads are semantically equivalent; any later MCP write uses the complete canonical permission and transaction path.
32. Access-count tests prove one discovery/read/hash/parse per included source and zero post-snapshot filesystem reads for ordering/pagination.
33. The representative 100-proposal fixture remains within declared payload and source-access budgets.
34. The repository pilot migrates v1-to-v2 and can answer/apply or defer/mute its three current gaps through supported commands.
35. Global validation completes without introduced errors or warnings, with migration recovery clear and residual state explicit.
36. Public documentation, migration guidance and generated agent instructions describe authority, retry, lifecycle, compatibility and source-of-truth behavior accurately.

## Decision

Pending owner review. Q001-Q008 and the post-definition robustness refinements are incorporated. This does not authorize implementation, migration, proposal acceptance or publication approval.
