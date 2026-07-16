# Design - Project Readiness Convergence Workflow

## Requirements Covered

- F1: convergence snapshot, typed gaps and priority.
- F2: workspace schema v2, transition handlers and operation gate.
- F3: project-question artifact and legacy migration.
- F4: question selection, answers, lifecycle and authority.
- F5: candidate rendering and atomic convergence apply.
- F6: retry, concurrency and vertical reconciliation.
- F7: next actions, progress, freshness and decision context.
- F8: CLI, pagination, MCP and diagnostics.
- F9: release, repository migration and artifact alignment.
- N001-N020: architecture, compatibility, side effects, determinism, test and
  deployment quality.

## Design Goals

- Close one project-readiness gap without reconstructing project history in chat.
- Keep question evidence, applied definition truth and governance decisions
  distinct.
- Make schema v2 a real adjacent migration, not a metadata-only registry entry.
- Preserve every v1-valid operation under the v2-capable runtime.
- Use one multi-target transaction for definition/question convergence.
- Keep old public facades and commands stable where the proposal did not approve
  a behavior change.
- Keep MCP read-only in the initial release and record write deferral explicitly.
- Make rollback/retry/concurrency behavior observable and testable.
- Roll out the runtime before migrating workspaces.
- Decide artifact alignment from freshness and ownership evidence instead of
  rebuilding everything.

## Key Decisions

- D001: Use separate core and service modules for project gaps/questions and
  convergence.
  Rationale: `core/project_verticals.py` and `services/project_verticals.py`
  already own vertical/definition concerns and should not absorb lifecycle,
  migration, ranking and transaction orchestration.

- D002: Keep `P2PWorkspace` as a delegating compatibility facade.
  Rationale: CLI, MCP and tests already depend on it; domain logic belongs in
  injected services.

- D003: Store project questions in `.p2p/project/questions.yml` under
  `project_questions`, artifact schema version `1`.
  Rationale: project scope is distinct from proposal-local `questions.yml`, and
  workspace schema v2 can own the cross-artifact authority transition without a
  database.

- D004: Keep `project_definition.schema_version` at `1` in this feature.
  Rationale: the definition value schema does not otherwise change. Workspace
  schema v2 governs the cross-artifact rule that definition `open_questions`
  must be empty and no longer authoritative.

- D005: Extract legacy-to-v1 planning into a handler before adding v1-to-v2.
  Rationale: structural extraction and behavior change receive separate gates,
  preventing accidental legacy bootstrap drift.

- D006: Use a transition-handler registry over candidate overlays.
  Rationale: there are now two adjacent transitions and future transitions must
  not add more version-specific branches to `WorkspaceCompatibilityService`.

- D007: Use an explicit operation schema requirement registry and fail unknown
  governed writes closed.
  Rationale: v1 compatibility cannot depend on scattered CLI checks or a default
  that silently enables future writes.

- D008: Require owner-role CLI writes for answer/defer/mute/reopen/apply in v1
  of the feature.
  Rationale: delegated/agent writes require a separately designed consent
  receipt contract. Caller-provided actor/source text is insufficient.

- D009: Treat reopen as an event back to `to_answer`, not a persisted state.
  Rationale: it aligns with the established proposal-question approach while
  preserving explicit audit history.

- D010: Bind answers through declarative answer contracts.
  Rationale: converting arbitrary prose to definition operations would reinsert
  agent inference at the authority boundary.

- D011: Require explicit question ids for convergence preview/apply.
  Rationale: an owner must know which answered evidence is being synthesized;
  a command must not opportunistically apply every answer in the workspace.

- D012: Reuse pure definition rendering/validation but bypass the existing
  single-target commit for convergence.
  Rationale: definition and question applied state must share one transaction.

- D013: Extend `AtomicMutationWriter` with non-target read preconditions and an
  under-lock candidate validator using backward-compatible optional parameters.
  Rationale: lock, permissions and workspace schema affect authorization and
  candidate meaning even though they are not mutation targets.

- D014: Add optional token-binding context rather than changing all existing
  preview tokens.
  Rationale: convergence needs actor/policy binding, but existing preview
  consumers should keep token semantics unless separately migrated.

- D015: Implement exact replay through persisted application references.
  Rationale: after commit, source hashes change; stored token/result identity is
  the only reliable way to distinguish response-loss retry from divergent reuse.

- D016: Keep time expiry out of the first release.
  Rationale: deterministic stateless tokens do not provide an honest issued/
  consumed lifecycle. Source staleness and exact replay are sufficient here.

- D017: Make vertical reconciliation explicit when prior evidence exists.
  Rationale: no automatic process may copy owner answers to a changed target.

- D018: Add project questions to decision context as inactive quality/pending
  evidence only.
  Rationale: project definition remains the semantic authority after apply.

- D019: Update MCP with bounded reads only; defer writes.
  Rationale: this meets the accepted delivery boundary and avoids a second
  permission/mutation implementation before CLI semantics stabilize.

- D020: Deploy runtime first, migrate workspace second, align derived artifacts
  third.
  Rationale: a v2 workspace cannot safely run on a v1-only runtime, and derived
  refresh should follow canonical migration rather than precede it.

- D021: Use a read-only artifact alignment report before any final refresh.
  Rationale: canonical, deterministic, curated and owner-review artifacts have
  different owners and cannot share a blanket rebuild policy.

## Current-System Constraints

- `ProjectVerticalService` owns vertical parsing, lock validation, definition
  reading, definition patch rendering and the current readiness review.
- `WorkspaceSchemaService` reads/writes the workspace schema envelope and
  validates migration history.
- `WorkspaceCompatibilityService` currently performs one-pass inventory and
  legacy candidate construction in the same class.
- `WorkspaceMigrationRegistry` validates adjacent metadata but does not own
  candidate handlers.
- `WorkspaceMigrationService` already owns durable transaction journal,
  schema-last commit, rollback, resume and recovery.
- `AtomicMutationWriter` already handles a generic target set, but only target
  preconditions are validated in its replacement loop.
- `MutationPreviewService` centralizes canonical semantic hashing and preview
  serialization.
- `PermissionsService` exposes project-declared identities/roles.
- `NextActionService` owns generated/curated next action merge and deduplication.
- `ProjectProgressService` owns definition and declared-evidence axes.
- `DerivedFreshnessService` owns the dependency graph and rebuild actions.
- `DecisionContextSourceService` and topology/extractor services own source
  classification and activation.
- `project_ops.py` and `mcp/handlers/project.py` are already large; new domain
  behavior must not be implemented there.

## Proposed Module Boundaries

### Core Contracts

`src/p2p_engine/core/project_readiness.py`

- `ProjectReadinessSnapshotIdentity`
- `ProjectReadinessGapKind`
- `ProjectReadinessGapSeverity`
- `ProjectReadinessGap`
- `ProjectReadinessPolicy`
- `ProjectReadinessResult`
- `ProjectReadinessPage`
- `ProjectReadinessCursor`
- `ProjectReadinessDiagnostic`

`src/p2p_engine/core/project_questions.py`

- `ProjectQuestionState`
- `ProjectQuestionApplicability`
- `ProjectQuestionSourceType`
- `ProjectQuestionTarget`
- `ProjectQuestionAnswerContract`
- `ProjectQuestionAnswerRevision`
- `ProjectQuestionRevision`
- `ProjectQuestionTransition`
- `ProjectQuestionApplication`
- `ProjectQuestion`
- `ProjectQuestionGroup`
- `ProjectQuestionArtifact`
- question operation result/preview types

Existing `core/project_verticals.py` gains only optional question target/answer
metadata needed to parse a backward-compatible vertical pack.

### Snapshot And Gap Service

`src/p2p_engine/services/project_readiness.py`

- `ProjectReadinessSnapshotBuilder` captures one immutable request snapshot.
- `ProjectReadinessGapService` classifies and ranks gaps.
- `ProjectReadinessPaginationService` encodes/decodes snapshot-bound cursors.

No collaborator retains source bytes across requests. `P2PWorkspace` may memoize
stateless service objects, not snapshots or results.

### Project Question State Service

`src/p2p_engine/services/project_questions.py`

- Owns path, parser, validator, serializer and semantic payload.
- Selects declared/fallback questions from a supplied snapshot.
- Validates answer contracts and lifecycle transitions.
- Writes answer/defer/mute/reopen changes through `AtomicMutationWriter`.
- Renders reconciliation candidates without committing them.
- Resolves exact application records by preview token.

It does not render definition candidates and does not rank project gaps.

### Convergence Service

`src/p2p_engine/services/project_readiness_convergence.py`

- Composes snapshot, gap, question, definition, permissions, preview and
  transaction collaborators.
- Produces convergence/reconciliation previews.
- Rechecks authority and source preconditions under lock.
- Commits definition/question candidates together.
- Returns post-commit gaps and rebuild plan without executing it.

### Operation Compatibility Gate

`src/p2p_engine/services/workspace_operation_compatibility.py`

- Versioned registry of operation id -> min/max workspace schema.
- Common read/write preflight result and diagnostic.
- Fail-closed unknown operation behavior.
- Validation helper proving every governed-write id used by facade services is
  classified.

`P2PWorkspace._ensure_runtime_write_allowed()` is either renamed internally to
a governed-write preflight delegate or composes this service while preserving
existing facade methods and public errors.

### Migration Handlers

`src/p2p_engine/services/workspace_migration_handlers.py`

- `WorkspaceMigrationTransitionHandler` protocol.
- `LegacyUndeclaredToV1Handler`, extracted with no behavior drift.
- `WorkspaceV1ToV2ProjectQuestionsHandler`.
- `TransitionPlanFragment` with operations, candidates, findings, owner inputs,
  validators and source-access evidence.

`WorkspaceMigrationRegistry` stores/validates handlers and resolves adjacent
paths. `WorkspaceCompatibilityService` performs inventory and orchestrates
handlers over `CandidateWorkspaceView`; it no longer owns transition-specific
candidate logic.

### Presentation

`src/p2p_engine/cli_commands/project_readiness.py`

- Registers readiness review/gap/question/reconcile/convergence commands.
- Converts service results to text/JSON only.

`src/p2p_engine/mcp/catalog/project_readiness.py`

- Declares read-only tool schemas.

`src/p2p_engine/mcp/handlers/project_readiness.py`

- Delegates tools and wraps results with `mutation_performed: false`.

Existing project CLI/MCP registration receives minimal wiring only.

## Convergence Snapshot

### Captured Inputs

The builder captures:

```text
workspace schema state and schema file bytes/hash
active vertical id/version/profile/modules
vertical lock bytes/hash/checksum
resolved vertical pack semantic checksum
definition bytes/hash and parsed state
project-question bytes/hash and parsed state when schema v2
permissions bytes/hash and resolved actor role when requested
proposal summaries
declared vertical coverage bytes/hash
heuristic suggestions, separately marked
policy versions: gap, identity, fallback, lifecycle, answer binding,
                  preview, cursor, decision-context source
```

Decision context may enrich read output after core gap construction, but it is
not a candidate-definition source. Derived retrieval data therefore cannot
silently affect an apply token or definition mutation.

### Snapshot Fingerprint

Fingerprint payload uses canonical JSON over semantic values and physical hashes
for persisted sources. It excludes absolute root, mtimes, current time and
generated display fields. Source order is sorted by root-relative path.

### Source Access Budget

- one proposal-directory discovery pass;
- one read/hash/parse per included source;
- zero reads after snapshot creation;
- default review top detail: `10` records per large collection;
- default page size: `20`;
- maximum page size: `100`;
- default structured readiness payload ceiling: `64 KiB`, excluding an explicit
  detail page requested by the caller.

If a full record would exceed the page/payload ceiling, the result reports
truncation and requires a smaller/filter-specific request; it does not silently
drop required identity/authority fields.

## Gap Identity And Priority

Stable gap identity payload:

```yaml
vertical_id: software_project
section_id: decisions
kind: incomplete_required_definition
target_kind: section
target_id: decisions
policy_major: 1
```

ID is `PGAP-` plus the first 16 lowercase hexadecimal characters of SHA-256 over
canonical identity JSON. Full digest remains available for collision detection.
Wording, evidence count and snapshot checksum are not part of stable identity.

Priority tuple:

```text
(class_rank, vertical_section_priority, stable_gap_or_question_id)
```

Class ranks are the six accepted classes. Assumption dependency impact is a
declared secondary value within class 4; absent impact uses neutral rank.

## Project-Question Artifact Contract

### YAML Shape

```yaml
project_questions:
  schema_version: 1
  project_id: p2p-engine
  vertical:
    id: software_project
    version: 1.0.0
    lock_checksum: sha256...
  policy_versions:
    identity: project-question-identity-v1
    fallback: project-question-fallback-v1
    lifecycle: project-question-lifecycle-v1
    answer_binding: project-question-answer-v1
  groups:
    - id: PRG-0123abcd...
      gap_id: PGAP-0123abcd...
      section_id: decisions
      question_ids: [PRQ-0123abcd...]
  questions:
    - id: PRQ-0123abcd...
      identity_sha256: full-digest
      revision: 1
      wording_sha256: full-digest
      state: to_answer
      applicability: active
      section_id: decisions
      gap_id: PGAP-0123abcd...
      target:
        kind: field
        id: summary
      source:
        kind: vertical_declared
        question_id: software-decisions
        vertical_version: 1.0.0
        lock_checksum: sha256...
      answer_contract:
        kind: field_value
        required_fields: [value]
        allowed_definition_operations: [set_field]
      revisions: []
      answers: []
      applications: []
      transitions: []
  audit:
    created_at: 2026-01-01T00:00:00Z
    created_by: system
    updated_at: 2026-01-01T00:00:00Z
    updated_by: system
```

All examples are schema illustrations, not repository-specific owner answers.

### Stable Question Identity

Identity payload:

```text
vertical id
section id
gap kind
target kind/id
declared question id OR fallback template key
identity policy major version
```

ID is `PRQ-` plus a 16-character digest prefix; the full digest is persisted and
validated for collisions. Group id uses the same rule over gap/section scope.

Revision changes when wording, vertical version/checksum, fallback template,
answer contract or completion meaning changes. A semantic target/completion
change creates a new stable identity and supersession relation.

### Answer Contracts

Supported initial kinds:

| Kind | Required owner input | Allowed definition operation |
| --- | --- | --- |
| `field_value` | `value`, optional evidence refs | `set_field` |
| `section_disposition` | one of `complete`, `partial`, `blocked`, `not_applicable`; rationale | `set_section_status`, subject to completion rules |
| `assumption_resolution` | assumption id, `validated` or `rejected`, rationale/evidence | `update_assumption_status` |
| `blocker_resolution` | blocker id, clear/retain plus rationale | `clear_blocker` or no-op |
| `owner_decision_reference` | existing governed decision/choice reference and bounded field target | `set_field`; never decides the referenced object |
| `informational` | value | no apply until a separately validated target contract exists |

A vertical-declared question may include optional target and contract metadata.
Legacy packs without metadata use deterministic binding only when exactly one
safe target exists. Fallback policy may produce:

- one missing field -> `field_value`;
- one unresolved assumption -> `assumption_resolution`;
- one blocker -> `blocker_resolution`;
- section with no missing fields but incomplete completion state ->
  `section_disposition` only when completion criteria are declarative;
- otherwise -> `no_safe_question`.

### Answer Input

Scalar `field_value` may be supplied by `--value`. Other contracts use a safe
root-resolved YAML input:

```yaml
project_question_answer:
  schema_version: 1
  question_id: PRQ-...
  expected_revision: 1
  values:
    outcome: validated
    rationale: Evidence reviewed by the owner.
  evidence_refs: []
```

The service derives `provided_by` and `recorded_by` from the authorized direct
owner actor; those fields are not trusted from the input file.

## Lifecycle And Authority

### Transition Matrix

| From | Operation | To | Authority | Reason |
| --- | --- | --- | --- | --- |
| absent | initialize/reconcile | `to_answer` | deterministic system write | generated provenance |
| `to_answer` | answer | `answered` | owner | answer contract |
| `answered` | replace answer | `answered` new answer revision | owner | replace flag + expected revision |
| `to_answer`/`answered` | defer | `deferred` | owner | required |
| `to_answer`/`answered` | mute | `muted` | owner | required |
| `deferred`/`muted` | reopen | `to_answer` | owner | required |
| `deferred` | declared trigger | `to_answer` | deterministic system write | trigger evidence |
| `answered` | convergence apply | `applied` | owner-confirmed transaction | application reference |
| active unanswered | target removed | `retired` | deterministic reconcile | old/new lock evidence |
| active | semantic replacement | `superseded` | deterministic reconcile preview/apply | `superseded_by` |

Applied, retired and superseded revisions are terminal. Reverted definition
content produces a new gap/question; history is not rewritten.

### Authority Matrix

| Operation | Readonly/known actor | Owner | Agent delegation |
| --- | --- | --- | --- |
| review/list/show/next | allowed | allowed | read-only MCP allowed |
| initialize generated state | write-safe known actor through supported command | allowed | no owner content |
| answer/replace | denied | allowed | deferred |
| defer/mute/reopen | denied | allowed | deferred |
| reconcile preview | allowed | allowed | read-only |
| reconcile apply affecting no prior answer | write-safe known actor if policy permits | allowed | no content inference |
| reconcile apply affecting answered/applied evidence | denied | allowed | deferred |
| convergence preview | allowed | allowed | read-only |
| convergence apply | denied | allowed | deferred |

The exact permission result includes actor id, role, operation and reason. A
caller cannot select its own authority label.

## Definition Candidate Rendering

Add a typed `ProjectDefinitionCandidate` returned by a pure method on the
definition-owning service. Inputs are current parsed state, explicit operations,
actor and an injected audit value. Output includes semantic payload, serialized
candidate bytes, semantic hash, changed targets and validation issues.

Existing definition preview/apply reuses the same method. Under workspace v2,
the operation gate rejects `add_open_question` and `close_open_question` before
candidate rendering.

Convergence maps each selected answered question through its answer contract to
an operation list. Operations are sorted by question id then target identity;
conflicting operations to the same target are a blocker unless they are
semantically identical.

## Convergence Preview And Apply

### Preview Flow

```text
CLI/service request with explicit question ids + actor
  -> operation/schema preflight
  -> immutable convergence snapshot
  -> owner role and question revision validation
  -> answer contract -> allowlisted definition operations
  -> pure definition candidate
  -> project-question candidate with pending application refs
  -> cross-artifact candidate validation
  -> semantic diff + freshness impact
  -> MutationPreviewService.build(token_context=...)
  -> no write
```

Token context includes actor, selected question ids/revisions, schema/lock/
permissions hashes, policy versions and both candidate hashes. Existing preview
callers that omit token context retain current token behavior.

### Atomic Writer Extension

Backward-compatible optional inputs:

```python
AtomicMutationWriter.apply(
    operation_id=...,
    candidates=...,
    sources=...,                  # target and non-target preconditions
    preview_token=...,
    actor=...,
    candidate_validator=...,      # optional, invoked under lock before replace
)
```

Under lock the writer:

1. validates every source precondition, including non-target schema/lock/
   permissions files;
2. snapshots all targets;
3. stages all candidates;
4. invokes the validator against a candidate workspace overlay;
5. writes the journal;
6. replaces targets in deterministic order;
7. records committed state and final hashes;
8. rolls back/reports recovery using existing rules on failure.

The generic writer does not import project-question types. Domain candidate
validation is injected by the convergence service.

### Apply And Exact Retry

Before recomputing a preview, apply looks up an application record by token:

- same actor, operation, question ids and candidate hashes -> return stored
  `already_applied` result;
- token exists with mismatched request -> `P2P346_PREVIEW_REPLAY_MISMATCH`;
- token absent -> recompute and compare fresh preview;
- recovery required -> block with migration/mutation recovery command.

Successful candidate state appends application data:

```yaml
token: sha256...
operation_id: project-readiness-convergence
actor: mrjungle
question_ids: [PRQ-...]
definition_candidate_sha256: sha256...
question_candidate_sha256: sha256...
final_physical_hashes: {}
applied_at: 2026-01-01T00:00:00Z
```

Final physical hashes can be completed in the returned result and persisted
when they are deterministically known before replacement. If physical audit
values are injected at commit, the application record stores semantic hashes
and the transaction result stores physical hashes; exact retry resolves both
through the committed journal/application reference contract.

## Vertical Reconciliation

Reconciliation compares stable semantic identities from old question state and
the new locked vertical:

- same identity, wording/checksum changed -> append revision, keep state/answers;
- semantic target/completion changed -> old superseded, replacement `to_answer`;
- section removed/not required -> unanswered retired; answered/applied retained
  inactive with reason;
- new target -> new `to_answer` or `no_safe_question`;
- declared alias -> explicit mapping only;
- no fuzzy/text similarity remap.

The active lock change invalidates every old preview immediately. If no prior
question evidence exists, fresh vertical selection may initialize question state
in the vertical selection candidate. Otherwise selection leaves a typed
`reconciliation_required` condition and prints the preview command.

## Workspace Schema And Migration Design

### Version Constants

- `CURRENT_WORKSPACE_SCHEMA_VERSION = 2`.
- Keep `WORKSPACE_SCHEMA_CONTRACT_VERSION = 1` if the envelope remains unchanged.
- Increment workspace schema policy/layout versions used in fingerprints.
- Add `LAYOUT_UPGRADEABLE` and status `upgrade_available` or equivalent.
- `migration_required` is context-sensitive for v2-only operations; status
  still reports v1 as valid for legacy-safe operation.

### Runtime Support Matrix

| Runtime | Workspace v0 | Workspace v1 | Workspace v2 |
| --- | --- | --- | --- |
| `0.2.x` v1-only runtime | inspect/plan/apply v0->v1 | current | ahead/blocked |
| `0.3.x` v2-capable runtime | inspect/plan/apply v0->v1->v2 | valid, upgrade available, v1-safe writes | current/full feature |

The owner-approved release is `0.3.0`. Legacy-to-v1 remains available in
`>=0.2.0,<0.4.0`; v1-to-v2 inspect/plan/apply require
`>=0.3.0,<0.4.0`. Transition metadata and tests encode these exact ranges.

### Transition Handler Protocol

```python
class WorkspaceMigrationTransitionHandler(Protocol):
    transition: MigrationTransition
    owned_targets: frozenset[str]

    def plan(
        self,
        snapshot: CompatibilitySnapshot,
        overlay: CandidateWorkspaceView,
        owner_inputs: Mapping[str, object],
    ) -> TransitionPlanFragment: ...

    def validate(self, view: CandidateWorkspaceView) -> None: ...
```

Registry validation requires one handler per adjacent source version, unique
migration id, non-overlapping ambiguous ownership, declared dependencies and a
path to current. Handler output is validated against `owned_targets`.

### V1-To-V2 Owned Targets

```text
.p2p/project/questions.yml
.p2p/project/definition.yml       only to normalize open_questions
.p2p/project/workspace-schema.yml schema/history, committed last
```

Unknown files and every unrelated canonical artifact are preserved.

### Legacy Mapping

For every definition section:

1. capture open questions in source order but identify by section/id/target;
2. match declared vertical question and field only when unique;
3. apply explicit owner-input bindings when the source is otherwise ambiguous;
4. map valid question to `to_answer` with `migrated_legacy` provenance;
5. generate a declared/fallback question for an incomplete required section
   that still has none;
6. leave complete/not-applicable sections without generated questions;
7. validate one-to-one source coverage;
8. set definition `open_questions` to `[]`;
9. create schema/history candidate.

Optional owner input shape for ambiguous binding:

```yaml
project_questions:
  legacy_bindings:
    assumptions/Q001:
      target_kind: assumption
      target_id: A001
      answer_contract: assumption_resolution
```

This input binds a target only; it cannot supply an answer or lifecycle outcome.

### Candidate Validation And Commit

- Validate project-question schema and semantic identities.
- Validate definition against active vertical and v2 empty-question rule.
- Validate every migrated source question has one target record.
- Validate schema history appends `workspace-v1-to-v2`, source 1, target 2.
- Commit question/definition before workspace schema.
- Preserve existing journal, schema-last, rollback/resume and recovery behavior.

## Operation Schema Gate

Requirements use a versioned data map, for example:

```python
OPERATION_SCHEMA_REQUIREMENTS = {
    "project_question_answer": Requirement(min_version=2),
    "project_readiness_convergence_apply": Requirement(min_version=2),
    "project_definition_add_open_question": Requirement(min_version=1, max_version=1),
    "proposal_decision_record": Requirement(min_version=1),
    # every existing governed write id is listed explicitly
}
```

The preparation slice inventories every operation passed to current write
preflight. A validation/unit test fails when a new operation is not classified.
Read-only v2-specific tools return a capability diagnostic on v1 rather than
performing a write or inventing empty state.

## Managed Next Actions

Add a generated action source that consumes only `ProjectReadinessResult`.
Suggested kind/target identities:

```text
project_schema_migration / workspace-schema-v2
project_question_answer / PRQ-...
project_question_reconcile / active-vertical
project_question_apply / PRQ-... or deterministic batch id
project_definition_gap / PGAP-...
```

Existing recovery and migration blockers retain higher precedence. Readiness
actions outrank optional legacy evidence but do not override curated owner
actions. Dedup uses kind/target semantic equivalence, not display text.

## Progress And Freshness

Question counts are descriptive:

```text
to_answer, answered, applied, deferred, muted, retired, superseded,
no_safe_question, reconciliation_required
```

They do not alter definition/evidence ratios directly.

Freshness source classes added/refined:

| Source change | Derived nodes potentially affected | Explicitly unaffected |
| --- | --- | --- |
| question answer/lifecycle | readiness/next, decision-context pending evidence, brief/export only if their declared inputs include project questions | generated proposal feature projections, unrelated software specs |
| question reconcile | readiness/next, decision context, any output exposing open questions | accepted proposal/decision registries unless artifact catalog changes |
| definition apply | project progress, readiness/next, decision context, assessment/maturity, brief/export/publication inputs and explicitly definition-dependent specs | unrelated historical artifacts |
| schema migration only | workspace status, artifact registry, agent instructions/docs and schema-aware derived nodes | owner publication approval |

`FreshnessNodeDefinition` gains explicit source classes/paths where needed so a
question-only change does not fall back to one global canonical fingerprint for
every node.

## Decision-Context Integration

- Add `SourceKind.PROJECT_QUESTIONS`.
- Catalog `.p2p/project/questions.yml` only when present/required by workspace
  schema.
- Classify as `QUALITY_METADATA`.
- Extract question id, section, state, target and bounded answer/apply summary.
- Set `Activation.INACTIVE` for every project-question record.
- Do not emit topology relations from question targets/applications.
- Definition records remain `PROJECT_DEFINITION_CONSTRAINT` authority.
- Bump source/extractor/authority policy versions only where payload semantics
  change and include them in freshness.

## CLI Contract

Exact initial commands:

```text
p2p project readiness review [--vertical ID] [--format text|json] [--limit N]
p2p project readiness gaps [--kind KIND] [--severity LEVEL] [--limit N] [--cursor C] [--format text|json]
p2p project readiness gap GAP_ID [--format text|json]

p2p project readiness questions status [--state STATE] [--limit N] [--cursor C] [--format text|json]
p2p project readiness questions next [--format text|json]
p2p project readiness questions answer QUESTION_ID (--value TEXT | --input PATH) --actor ACTOR [--replace] [--expected-revision N]
p2p project readiness questions defer QUESTION_ID --reason TEXT --actor ACTOR --expected-revision N
p2p project readiness questions mute QUESTION_ID --reason TEXT --actor ACTOR --expected-revision N
p2p project readiness questions reopen QUESTION_ID --reason TEXT --actor ACTOR --expected-revision N
p2p project readiness questions reconcile-preview --actor ACTOR [--format text|json]
p2p project readiness questions reconcile-apply --preview-token TOKEN --actor ACTOR --confirm [--format text|json]

p2p project readiness preview --question QUESTION_ID... --actor ACTOR [--format text|json]
p2p project readiness apply --question QUESTION_ID... --preview-token TOKEN --actor ACTOR --confirm [--format text|json]
```

Command registration may adjust singular command spelling only before public
implementation if Typer constraints require it; any adjustment must be updated
consistently in requirements, docs and tests before coding proceeds.

Structured wrappers:

```text
project_readiness
project_readiness_page
project_readiness_gap
project_questions
project_question
project_question_reconciliation
project_readiness_preview
project_readiness_apply
```

Every mutation result includes `mutation_performed`, status, operation id,
actor, changed paths, token/reference and recovery guidance.

## MCP Contract

Read-only tools:

```text
p2p_project_readiness_review          existing, payload extended compatibly
p2p_project_readiness_gaps            new, limit/cursor/filter
p2p_project_readiness_gap_show        new
p2p_project_questions_status          new, limit/cursor/filter
p2p_project_questions_next            new
```

All return `mutation_performed: false`. No answer/defer/mute/reopen/reconcile/
preview-apply mutation tools are registered. Documentation contains a follow-up
statement: write parity requires an explicit consent-gated proposal after CLI
contract stability and usage evidence.

## Diagnostics Contract

Reserve project-readiness diagnostics in the current workspace/migration range:

| Code | Meaning |
| --- | --- |
| `P2P340_PROJECT_QUESTIONS_INVALID` | artifact schema/semantic validation failed |
| `P2P341_PROJECT_QUESTION_NOT_FOUND` | stable id absent |
| `P2P342_PROJECT_QUESTION_TRANSITION_INVALID` | lifecycle transition rejected |
| `P2P343_PROJECT_QUESTION_OWNER_REQUIRED` | actor lacks owner authority |
| `P2P344_PROJECT_QUESTION_NO_SAFE_FALLBACK` | no deterministic question/binding |
| `P2P345_PROJECT_READINESS_STALE_PREVIEW` | source/policy/lock changed |
| `P2P346_PREVIEW_REPLAY_MISMATCH` | committed token reused with different request |
| `P2P347_PROJECT_QUESTION_RECONCILIATION_REQUIRED` | lock/semantic target drift |
| `P2P348_WORKSPACE_OPERATION_SCHEMA_REQUIRED` | operation unavailable at current schema |
| `P2P349_PROJECT_READINESS_CURSOR_STALE` | page cursor snapshot changed |

Adjacent implementation diagnostics are reserved for migration/payload cases
that are not runtime lifecycle failures: `P2P350_AMBIGUOUS_LEGACY_QUESTION`,
`P2P351_PROJECT_QUESTION_AUTHORITY_CONFLICT`,
`P2P352_LEGACY_DEFINITION_QUESTION_OPERATION`,
`P2P353_READINESS_PAYLOAD_LIMIT` and
`P2P354_LEGACY_PROJECT_QUESTIONS_PRESENT`.

If these codes collide during implementation, reserve an adjacent unused range
and update all spec/docs/tests before merging; do not silently use generic
`ValueError("invalid")` messages.

## Pagination Cursor

Cursor is URL-safe base64 of canonical JSON plus checksum:

```json
{
  "schema": 1,
  "collection": "gaps",
  "policy": "project-readiness-cursor-v1",
  "snapshot": "sha256...",
  "last_key": [3, 120, "PGAP-..."]
}
```

Checksum detects corruption/accidental tampering; the cursor grants no write
authority and does not require a secret. Source drift returns stale cursor.

## Validation Integration

Global validation adds:

- workspace v2 requires valid question artifact;
- workspace v1 treats missing question artifact as expected;
- v2 definition open questions must be empty;
- question vertical/section/target refs must match active lock/pack or carry
  explicit stale/reconciliation status;
- application references must be internally complete;
- schema history/handler ids must be registered and contiguous;
- operation schema registry must cover every governed-write id;
- no active migration/mutation recovery can be hidden.

Readiness review itself remains diagnostic and does not auto-fix these findings.

## Test Strategy

### Unit And Table Tests

- Gap identity, taxonomy, class order and tie-break.
- Question identity/revision/collision.
- Answer contracts and allowed operation mapping.
- Lifecycle/authority matrices.
- Cursor encode/decode/stale/corrupt.
- Operation schema requirement matrix.
- Transition registry/path/ownership.
- Semantic hash audit exclusions.

### Service Tests

- One immutable source snapshot and access counts.
- Declared/fallback/no-safe selection.
- Owner/non-owner lifecycle writes and byte invariants.
- Pure definition candidate rendering.
- Convergence preview/apply/exact retry.
- Vertical reconciliation for all states.
- Next/progress/freshness integration.
- Decision-context inactive metadata extraction.

### Migration And Transaction Tests

- Legacy-to-v1 regression after handler extraction.
- Fresh/empty/current/ahead/invalid/recovery status.
- V1-to-v2 with no questions, repeated local ids, mapped/unmapped targets,
  ambiguous input and incomplete sections.
- Multi-step v0->v1->v2 overlay.
- Schema-last ordering and candidate ownership.
- Failure injection before/after every target replacement.
- Rollback, resume, external edit and two-process locking.
- Idempotent no-op and no downgrade.

### Public Tests

- CLI command names/options/text/JSON/exit codes.
- Existing review compatibility and truncation.
- MCP tool schemas and semantic read parity.
- Explicit absence of MCP write tools.
- Global validation and agent instruction text.
- Version/build/setup/changelog consistency.

### Scale And Metamorphic Tests

- 100 proposals, large unmapped set and long question history.
- Reverse source order and inject clocks.
- One discovery/read/hash/parse and zero post-snapshot reads.
- Payload/page ceilings and stable pagination.

## Release And Deployment Design

### Gate 1 - Governed Delivery Setup

- Create/identify Change Set from accepted `PROP-101`.
- Run software-spec lifecycle preflight.
- Record target package version and runtime/schema support matrix.
- Capture baseline tests and public payloads.

### Gate 2 - Incremental Implementation

- Deliver S1-S8 with focused tests after each slice.
- Do not introduce v1-to-v2 behavior until legacy handler extraction gate passes.
- Do not add public write commands until service authority/atomicity gates pass.
- Do not add MCP reads until CLI JSON stabilizes.

### Gate 3 - Engine Completion

- Focused feature suites.
- Public CLI/MCP suite.
- Full suite.
- `p2p validate` on fixtures and repository.
- Version consistency, docs, templates and build artifacts.
- Clean temporary environment smoke.

### Gate 4 - Runtime Deployment

- Before changing source/package version, preview and owner-apply a transitional
  repository runtime contract that accepts both the installed v1-capable line
  and the candidate v2-capable line while recommending the candidate.
- Set `workspace-v1-to-v2` inspect/plan/apply requirements to the first runtime
  version that actually contains the handler; never advertise published
  `0.2.0` as v2-capable.
- Build wheel/sdist with `python -m build`, the build primitive documented by
  `release-how-to.md` and the release workflow.
- Install/test the exact artifact intended for release.
- Publish/distribute only through owner-approved release process.
- Verify the released runtime can inspect/operate v1 before any migration.

### Gate 5 - Repository V1-To-V2 Pilot

- Freeze baseline and ensure clean recovery state.
- Generate reviewed dry-run target 2.
- Obtain owner confirmation.
- Apply through migration CLI.
- Validate schema/questions/definition and exercise read workflow.
- After validation, preview and owner-apply the final runtime contract requiring
  the v2-capable release line so an old runtime cannot appear compatible.
- Keep owner answers as separate later steps.

### Gate 6 - Artifact Alignment

Run read-only checks first:

```text
p2p runtime status --format json
p2p workspace schema status --format json
p2p workspace migrate recovery status --format json
p2p project context --format json
p2p project definition show --format json
p2p project readiness review --format json
p2p project progress --format json
p2p project freshness --format json
p2p registry status
p2p next
p2p validate
```

Then classify and route:

| Artifact class | Examples | Alignment rule |
| --- | --- | --- |
| canonical | schema, questions, definition, lock, proposal/decision/change/work state | only owning preview/apply/import/migration primitive; owner confirmation where required |
| deterministic derived | registries, project projections, next actions, assessment/maturity, decision-context materialization, generated specs/exports | refresh only if stale/divergent and owning command exists |
| agent curated | operational brief content, curated project publication | regenerate/import only through existing prompt/import or curator lifecycle |
| owner reviewed | publication review, governance decisions, question answers | never infer or auto-approve |
| legacy | v1 question representation, optional historical outputs | preserve, normalize or retire only under declared migration/ownership |
| unaffected | artifacts whose source contract excludes schema/questions/definition change | do not rewrite |

Expected owning commands include `registry refresh`, `project refresh`,
`next refresh`, assessment/maturity refresh, `spec lifecycle/refresh`, project
brief prompt/import, project export/publication prepare and agent instruction
refresh. The final task list requires rechecking actual command support before
executing any write.

### Gate 7 - Final Comparison And Handoff

- Compare baseline/post hashes, counts, diagnostics and freshness.
- Explain every generated diff.
- Keep publication approval false unless separately owner-approved.
- Record missing primitives as follow-up rather than manual repair.
- Run full tests and validation again.
- Review Git status/diff and produce implementation evidence.

## Rollback And Recovery

- Before migration commit: normal code rollback remains possible while v1 is
  still current.
- During migration: use transaction recovery status, resume or rollback.
- After successful v2 migration: workspace downgrade is unsupported. A runtime
  regression requires a v2-compatible corrective release; deploying the old
  v1-only runtime is not a valid rollback.
- Canonical question/definition apply failure uses the same lock/journal
  recovery contract.
- Deterministic derived refresh failure does not rollback a successful canonical
  migration/apply; it remains stale with an actionable rebuild plan.
- Curated/owner stages remain independently pending and never block canonical
  rollback semantics by pretending to be current.

## Risks And Mitigations

- Handler extraction changes v0->v1 behavior.
  Mitigation: structural slice and golden candidate regression before v2 work.
- Workspace v1 is globally blocked by current-version comparison.
  Mitigation: explicit upgradeable state and operation-level gate.
- Question/definition sources compete.
  Mitigation: migration empties legacy fields and v2 validation rejects return.
- Free text becomes owner decision.
  Mitigation: answer contracts and allowlisted operations only.
- Agent spoofs owner.
  Mitigation: owner role resolution; delegated write out of scope.
- Preview validates before lock only.
  Mitigation: non-target preconditions and validator under lock.
- Retry looks stale after successful commit.
  Mitigation: persisted application reference and exact `already_applied` path.
- Vertical wording change reopens work.
  Mitigation: semantic identity/revision separation.
- Question metadata gains decision authority.
  Mitigation: inactive SourceKind and no topology edges.
- Global freshness over-invalidates everything.
  Mitigation: explicit source classes per node.
- MCP write omission becomes accidental.
  Mitigation: explicit deferred decision, docs and absence test.
- Repository alignment rewrites curated outputs.
  Mitigation: classify ownership before write and honor lifecycle stages.
- Runtime rollback after migration becomes impossible.
  Mitigation: release-first ordering and v2-compatible corrective release plan.

## Out Of Scope Follow-Ups

- Consent-gated MCP/project-question writes after CLI usage evidence.
- Durable time-expiring preview receipts.
- Remote/fleet workspace migration orchestration.
- Persistent readiness cache based on measured need.
- Rich multi-answer interview sessions beyond explicit question ids.
- Automated artifact-alignment execution beyond current freshness primitives.
- Workspace downgrade tooling.
