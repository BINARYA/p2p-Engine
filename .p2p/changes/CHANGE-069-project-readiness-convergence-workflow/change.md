---
change_id: CHANGE-069
title: Project Readiness Convergence Workflow
status: implementation_ready
created_at: '2026-07-16'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-101
  accepted_decisions: []
implementation_targets:
- local_cli
spec_targets:
- p2p_spec
export_targets:
- openspec
- speckit
plan_ref: execution-plan.md
tasks_ref: tasks.yml
---

# CHANGE-069 - Project Readiness Convergence Workflow

## Summary

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

## Rationale

Not provided.

## Scope

### Included

- Derived from accepted proposal scope.

### Excluded

- Automatic Git commits, branches, tags, or merges.

## Deliverables

- Change Set metadata.

## Acceptance Criteria

- Change Set metadata is present and reviewable.

## Dependencies

- None recorded.

## Risks

- Metadata may need manual refinement before implementation.

## Related Choices

- None recorded.
