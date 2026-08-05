# Design - Typed Project Vertical Transition Impact

## Requirements Covered

- R001-R052
- N001-N008
- AC001-AC015

## Decision Summary

Implement accepted `PROP-001` as a typed operation-level contract under the
existing `p2p-cli/v1` envelope. Keep lifecycle orchestration in
`VerticalLifecycleService`, but move evidence classification, transition
analysis and candidate materialization into focused services. A migration is a
two-preview decision loop: an incomplete preview identifies required owner
decisions; a complete canonical plan is then re-previewed to obtain the only
token eligible for apply.

The implementation is current-only. It does not preserve the generic 0.4.7
impact shape or implicit orphaning behavior. P2P Engine remains the only reader
and writer of project memory. WaveKit and standalone agents consume the CLI
contract.

## Key Decisions

### D001 - Version The Domain Payload, Not The Global Envelope

`p2p-cli/v1` remains unchanged because its six-field success/error envelope and
exit model do not change. Each vertical lifecycle payload contains:

```text
impact.contract_version = p2p-vertical-transition-impact/v1
```

Typed install, adoption and migration classes share small value objects but do
not rely on optional keys to distinguish operations.

Rationale: a global `p2p-cli/v2` would force unrelated commands to migrate and
would not improve this domain contract.

### D002 - One Captured Snapshot And One Evidence Classifier

`VerticalEvidenceClassifier` receives one immutable snapshot containing:

- active vertical and lock identity;
- parsed definition state;
- parsed project questions;
- parsed rubrics;
- the resolved current vertical baseline.

It returns one `VerticalSourceState` used by both adoption and migration. CLI,
filesystem facade and lifecycle orchestration cannot implement their own
empty/populated test.

Rationale: routing drift between adoption and migration is more dangerous than
the individual missing fields.

### D003 - Separate Analysis From Materialization

`VerticalTransitionAnalysisService` compares source state with an exact target
pack and produces typed impact plus required decisions. It performs no writes
and does not need to create a mutation candidate for unresolved decisions.

`VerticalTransitionMaterializationService` accepts only a validated complete
plan and creates the candidate definition, questions, rubrics, active vertical
and lock artifacts. `VerticalLifecycleService` validates those candidates,
builds the state-bound mutation preview and owns apply/receipt orchestration.

Rationale: the current implementation implicitly decides orphaning while it is
constructing candidate files, making it impossible to explain missing owner
decisions first.

### D004 - Keep The CLI Option, Replace Its Loose Document Contract

The migrate command retains `--mapping FILE` so command vectors and allowlists
do not change gratuitously. The file is no longer a loose field/rubric map. It
must contain the strict `p2p-vertical-transition-plan/v1` document defined
below.

No compatibility parser accepts the old dictionary/list variants. The help,
docs and errors call the file a transition decision plan despite the retained
option spelling.

Rationale: this preserves a stable command path while removing the ambiguous
payload that caused the gap.

### D005 - Exact Identity Determines Automatic Preservation

Automatic preservation requires the same evidence kind and exact semantic
identity:

- definition field: exact section and field IDs with compatible target field
  contract;
- assumption/blocker: same section and current typed identity;
- rubric: same ID and compatible target rubric semantics;
- question: reconciliation reports exact identity and a compatible answer
  contract;
- existing orphan: already carries an explicit orphan disposition.

Everything else is either a required exact `map` or explicit
`preserve_as_orphan` decision. Titles, wording and similarity never establish
identity.

### D006 - Reuse Question Reconciliation As A Dry-Run Contract

The current `ProjectQuestionStateService.reconcile_candidate` contains the
authoritative identity and owner-evidence rules. Extract or extend a read-only
analysis path that returns its preservation/revision/retirement/supersession
sets and structured conflicts without materializing changes.

When owner evidence would become inactive, superseded or incompatible, the
transition plan must select an exact target question or explicit orphan-style
historical preservation. Evidence remains in the project-question artifact;
it is not copied into definition orphans.

Rationale: each memory family preserves its own evidence and provenance.

### D007 - Rubric Analysis Precedes Rubric Rendering

Split current rubric handling into:

1. baseline comparison and typed analysis;
2. decision validation;
3. candidate rendering.

A semantic collision becomes a typed required decision instead of an immediate
free-form `ValueError`. Existing customization remains attached to an exact
target rubric only after compatible identity or explicit mapping. Orphaned
rubrics remain in `rubrics.yml` with their current non-baseline semantics.

### D008 - Bounded Completeness Fails Closed

All public collections use a common envelope:

```json
{
  "total": 3,
  "returned": 3,
  "truncated": false,
  "items": []
}
```

Implementation constants cap transition entries, questions, rubrics,
dependencies, warnings, blockers and decisions. The complete internal analysis
computes totals first. If a material collection exceeds its public bound,
preview reports deterministic totals and a typed impact-limit blocker, omits
an applicable token and performs no writes.

Rationale: allowing apply after hiding decisions would violate explicit owner
control. Pagination is not introduced in this feature.

### D009 - Keep Generic Preview Internals Behind A Safe Public Projection

Do not broaden generic `MutationPreview` across every mutation domain. The
vertical impact contains typed blockers with code, category, reference and
recovery. The internal generic preview may retain target paths, source
preconditions, candidate hashes, token context and stable blocker codes for
token construction and `apply_allowed` computation.

`VerticalLifecyclePreview.to_dict()` must not delegate to the full generic
`MutationPreview.to_dict()`. It publishes only the bounded fields needed by a
caller: operation ID, actor, authority, confirmation requirement, policy
version, apply eligibility and the opaque preview token. Vertical apply and
mutation-status serializers likewise publish typed semantic postconditions,
not changed paths or physical hashes.

Rationale: the domain needs richer diagnostics and a path-free public contract,
but an unrelated global mutation-preview redesign is outside scope.

### D010 - Plan And Impact Are Bound To Preview And Receipt

The first analysis yields `analysis_fingerprint_sha256`. A supplied plan names
that fingerprint and is normalized by decision ID before hashing. A complete
preview binds:

- impact contract version;
- analysis fingerprint;
- plan fingerprint;
- exact source and target identities;
- actor, profile and modules;
- all candidate semantics and source preconditions.

Apply recomputes the same values. The receipt stores the fingerprints, bounded
decision summary, target identity and semantic postconditions alongside current
physical postconditions.

Vertical mutation receipts advance to the current typed receipt result shape.
Obsolete receipt forms are rejected; no runtime adapter is added.

### D011 - MCP Mutation Parity Remains Explicitly Deferred

No install/adopt/migrate MCP write tools are added. These operations access
local artifacts, owner-confirmed workspace mutation and user-local credential
or cache contexts already classified as CLI-only. The MCP capability catalog,
MCP docs and generated skills must describe the CLI workflow accurately.

WaveKit's public MCP server continues to authorize and enqueue its own use cases
and invokes the P2P CLI inside the single writer; it does not need a local P2P
MCP mutation tool.

## Components And Ownership

### New Modules

- `src/p2p_engine/core/vertical_transition_impact.py`
  - contract constants;
  - enums and typed identifiers;
  - source-state, collection, transition, issue, lock, artifact and operation
    impact dataclasses;
  - strict deterministic `to_dict()` methods.
- `src/p2p_engine/core/vertical_transition_plan.py`
  - plan schema constants;
  - typed decision/action models;
  - normalized plan and fingerprint representation.
- `src/p2p_engine/services/vertical_evidence_classifier.py`
  - one source snapshot reader/classifier;
  - definition, question and rubric evidence counts;
  - no presentation or mutation.
- `src/p2p_engine/services/vertical_transition_analysis.py`
  - install/adoption/migration analysis;
  - structural diff, required decisions, blockers, warnings and bounds;
  - analysis fingerprint.
- `src/p2p_engine/services/vertical_transition_materialization.py`
  - plan validation against analysis;
  - definition/rubric/question disposition;
  - complete candidate artifact construction.

The implementation may consolidate the two small core modules only if typed
ownership remains clear and tests do not need private implementation imports.

### Existing Modules Updated

- `core/portable_verticals.py`
  - replace generic impact typing with operation-specific impact protocol;
  - add safe public preview projection, typed apply result and semantic
    postconditions.
- `core/mutation_receipts.py`
  - advance the current receipt result schema and typed validation.
- `services/vertical_lifecycle.py`
  - orchestrate classifier, analyzer, materializer, preview, apply and replay;
  - remove `_has_meaningful_evidence`, `_migrated_definition` and loose mapping
    parsing after their behavior moves to the new services.
- `services/project_verticals.py`
  - expose pure target baseline/candidate helpers;
  - separate rubric analysis from rendering;
  - keep exact pack resolution and candidate validation authoritative.
- `services/project_questions.py`
  - expose read-only reconciliation analysis and decision-aware candidate
    rendering while retaining current question identity rules.
- `services/mutation_receipts.py`
  - validate/store typed transition metadata, retain physical postconditions
    internally and reconstruct path-free public replay/status results.
- `storage/filesystem.py`
  - keep facade method names and delegate typed plan/results without domain
    logic.
- `cli_commands/project_ops.py`
  - strictly load the transition plan through `--mapping`;
  - render typed text summaries and unchanged global JSON envelopes.
- `services/agent_capabilities.py` and `services/agent_templates.py`
  - update capability semantics and generated guidance.

### Test And Documentation Ownership

- `tests/test_vertical_evidence_classifier.py`: evidence-family routing.
- `tests/test_vertical_transition_impact.py`: pure analysis and plan behavior.
- `tests/test_portable_verticals.py`: lifecycle, atomicity and receipt
  integration.
- `tests/test_cli_contract.py` and a focused vertical CLI contract module:
  exact envelope, payload, exits and fixtures.
- `tests/test_project_questions_service.py`: dry-run reconciliation and
  decision-aware preservation.
- `tests/test_agent_*`: generated guidance and capability resolution.
- `tests/fixtures/vertical_transition/`: versioned sanitized golden payloads
  and plan documents.
- `docs/CLI-CONTRACT.md`, `docs/CLI-GUIDE.md`, `docs/MCP.md`,
  `docs/AGENT-INTEGRATION.md`, development primitive inventory and
  `CHANGELOG.md`: maintained public behavior.

## Data And Contracts

### Typed Evidence References

Public references are domain identifiers, never physical paths:

```text
definition_field:<section-id>.<field-id>
definition_assumption:<section-id>/<assumption-id>
definition_blocker:<section-id>/<blocker-id>
definition_orphan:<orphan-id>
rubric:<rubric-id>
question:<question-id>
artifact:<vertical|lock|definition|rubrics|questions>
```

Each reference has a separate `kind` field. Parsers validate the kind-specific
syntax and exact target existence. Opaque hashes may supplement identity but
do not replace the stable reference needed for an owner decision.

### Source Classification

The classifier returns:

```json
{
  "classification": "populated",
  "adoption_eligible": false,
  "migration_required": true,
  "evidence": {
    "definition_fields": 3,
    "assumptions": 1,
    "blockers": 0,
    "definition_orphans": 1,
    "owner_question_evidence": 2,
    "rubric_customizations": 1,
    "total": 8
  }
}
```

For definition values, `0` and `false` are meaningful. `null`, empty strings
after normalization and empty collections are empty. Existing definition
orphans are always meaningful. Question evidence uses the current
`has_owner_evidence` semantics. Rubric customization is measured against the
exact active locked pack, not against a generic default.

### Impact Payload Shape

The exact field-level schema is frozen in golden fixtures before service
implementation. The conceptual migration form is:

```json
{
  "contract_version": "p2p-vertical-transition-impact/v1",
  "operation": "migrate",
  "analysis_fingerprint_sha256": "<sha256>",
  "plan_fingerprint_sha256": null,
  "source_state": {
    "classification": "populated",
    "adoption_eligible": false,
    "migration_required": true,
    "evidence": {}
  },
  "source": {
    "coordinate": "example/software@1.0.0",
    "semantic_checksum": "<sha256>",
    "artifact_checksum": "<sha256>"
  },
  "target": {
    "coordinate": "example/software@2.0.0",
    "semantic_checksum": "<sha256>",
    "artifact_checksum": "<sha256>"
  },
  "sections": {"total": 0, "returned": 0, "truncated": false, "items": []},
  "evidence_transitions": {"total": 0, "returned": 0, "truncated": false, "items": []},
  "rubrics": {"total": 0, "returned": 0, "truncated": false, "items": []},
  "questions": {
    "preserved": {"total": 0, "returned": 0, "truncated": false, "items": []},
    "revised": {"total": 0, "returned": 0, "truncated": false, "items": []},
    "created": {"total": 0, "returned": 0, "truncated": false, "items": []},
    "retired": {"total": 0, "returned": 0, "truncated": false, "items": []},
    "superseded": {"total": 0, "returned": 0, "truncated": false, "items": []},
    "inactive_owner_evidence": {"total": 0, "returned": 0, "truncated": false, "items": []}
  },
  "lock": {},
  "artifacts": {"total": 0, "returned": 0, "truncated": false, "items": []},
  "required_decisions": {"total": 0, "returned": 0, "truncated": false, "items": []},
  "blockers": {"total": 0, "returned": 0, "truncated": false, "items": []},
  "warnings": {"total": 0, "returned": 0, "truncated": false, "items": []}
}
```

Install and adoption use their own typed subsets. They retain the shared
contract, identity, collection and issue objects but do not emit meaningless
migration-only keys.

### Evidence Transition

```json
{
  "source": {
    "kind": "definition_field",
    "ref": "definition_field:legacy.constraints"
  },
  "target": null,
  "disposition": "decision_required",
  "value_present": true,
  "provenance_present": true,
  "decision_id": "VTD-<stable-hash>"
}
```

No value or free-form provenance is serialized. After a complete plan,
`disposition` becomes `mapped` or `preserve_as_orphan` and the exact target is
shown when applicable.

### Required Decision

```json
{
  "id": "VTD-<stable-hash>",
  "kind": "evidence_destination",
  "source": {
    "kind": "definition_field",
    "ref": "definition_field:legacy.constraints"
  },
  "allowed_actions": ["map", "preserve_as_orphan"],
  "compatible_target_kinds": ["definition_field"]
}
```

Decision IDs are hashes of contract version, exact source identity, target
vertical identity and decision kind. They do not include raw evidence values.

### Canonical Transition Plan

```yaml
vertical_transition_plan:
  schema_version: 1
  contract_version: p2p-vertical-transition-plan/v1
  analysis_fingerprint_sha256: <sha256-from-analysis>
  decisions:
    - id: VTD-<stable-hash>
      action: map
      source:
        kind: definition_field
        ref: definition_field:legacy.constraints
      target:
        kind: definition_field
        ref: definition_field:constraints.summary
    - id: VTD-<stable-hash>
      action: preserve_as_orphan
      source:
        kind: rubric
        ref: rubric:legacy_delivery
```

Strict parsing rules:

- one root and no unknown fields;
- exact schema and contract versions;
- lowercase SHA-256 analysis fingerprint;
- one entry for every required decision and no extras;
- IDs and source references must match the analysis;
- `map` requires one exact compatible target;
- `preserve_as_orphan` forbids a target;
- duplicate IDs, sources or exclusive targets fail;
- decision order is normalized by ID before hashing;
- YAML duplicate keys fail through the current unique-loader contract.

### Question And Rubric Dispositions

Question analysis reuses current identities and reports:

- `preserved`: exact identity and compatible answer contract;
- `revised`: same identity with a non-destructive revision;
- `created`: new target question;
- `retired`: unanswered source question removed from target;
- `superseded`: exact declared replacement/alias;
- `inactive_owner_evidence`: owner evidence would no longer be active;
- `owner_review_required`: an explicit map/orphan-style decision is required.

Preserve-as-orphan for a question means retaining it as inactive historical
question evidence with current transitions and provenance. It does not create a
definition orphan.

Rubric analysis compares current persisted criteria with both current and
target pack semantics. Preserve-as-orphan retains the criterion with
`counts_toward_active_baseline: false`; exact mapping transfers allowed owner
customization to the target criterion.

### Lock And Artifact Impact

Lock impact contains semantic identities only:

- before/after coordinate;
- semantic and artifact checksums;
- dependency coordinate/checksum additions and removals;
- profile and module additions/removals.

Artifact impact uses stable kinds and before/candidate semantic hashes. It does
not expose `.p2p` paths. The internal generic mutation preview continues to
hold target paths and physical preconditions for token validation, but the
vertical public serializer never emits those fields. WaveKit's documented
contract is the typed impact, safe preview summary and typed semantic
postconditions.

### Apply Result And Receipt

`VerticalLifecycleResult` adds:

```json
{
  "impact_contract": "p2p-vertical-transition-impact/v1",
  "operation": "migrate",
  "coordinate": "example/software@2.0.0",
  "analysis_fingerprint_sha256": "<sha256>",
  "plan_fingerprint_sha256": "<sha256>",
  "postconditions": {
    "active_coordinate": "example/software@2.0.0",
    "lock_semantic_checksum": "<sha256>",
    "lock_artifact_checksum": "<sha256>",
    "definition_semantic_sha256": "<sha256>",
    "questions_semantic_sha256": "<sha256>",
    "rubrics_semantic_sha256": "<sha256>"
  },
  "mutation": {
    "status": "applied",
    "operation_id": "project-vertical-migrate:example-software-2-0-0",
    "actor": "owner",
    "recovery_required": false
  }
}
```

The receipt stores the same fingerprints, postconditions and bounded normalized
decision summary. Existing physical postconditions remain internal and
authoritative for receipt drift detection. They are not returned by vertical
apply or `p2p mutation status`. Replay reconstructs the same public semantic
result with mutation status `already_applied`.

Install uses a distinct semantic postcondition shape with
`installed_coordinate`, `installed_semantic_checksum` and
`installed_artifact_checksum`. It never reports an `active_coordinate`, because
installing a pack does not select it for the project.

## Workflow

### Adoption

```text
capture current snapshot
  -> classify evidence
  -> analyze target baseline
  -> empty: build candidate and applicable preview
  -> populated: return migration_required blocker, no applicable token
```

### Migration Without A Plan

```text
capture current snapshot
  -> classify populated
  -> analyze target and every evidence disposition
  -> compute analysis fingerprint
  -> return complete required_decisions
  -> apply_allowed=false when any decision remains
  -> zero writes
```

### Migration With A Complete Plan

```text
capture and re-analyze
  -> verify analysis fingerprint
  -> normalize and validate every decision
  -> materialize definition/rubric/question/lock candidates
  -> validate complete candidate set
  -> bind analysis + plan + candidates to preview token
  -> return apply_allowed=true
```

### Apply And Replay

```text
recompute complete preview from exact inputs
  -> compare token
  -> prepare typed receipt + physical postconditions
  -> atomic workspace transaction
  -> typed result

same idempotency key + exact request
  -> verify physical postconditions
  -> reconstruct same typed semantic result as already_applied
```

## Error Handling

New stable domain codes include:

- `P2P_VERTICAL_TRANSITION_PLAN_INVALID` - malformed or unknown plan content;
- `P2P_VERTICAL_TRANSITION_PLAN_STALE` - analysis fingerprint mismatch;
- `P2P_VERTICAL_DECISION_REQUIRED` - complete explicit disposition is missing;
- `P2P_VERTICAL_DECISION_CONFLICT` - duplicate, incompatible or contradictory
  decision;
- `P2P_VERTICAL_IMPACT_LIMIT_EXCEEDED` - complete impact cannot fit the public
  contract bound;
- `P2P_VERTICAL_QUESTION_RECONCILIATION_BLOCKED` - owner question evidence has
  no valid disposition;
- `P2P_VERTICAL_RUBRIC_RECONCILIATION_BLOCKED` - rubric customization has no
  valid disposition.

Existing codes remain for invalid exact coordinates/checksums, adoption versus
migration routing, stale mutation preview, missing confirmation, project busy,
idempotency conflict, postcondition drift and transaction recovery.

Blocked analysis is a successful read-only CLI response with
`apply_allowed=false` when the caller needs to make a decision. Malformed input
or invalid current state is a failed envelope with the appropriate exit class.
This distinction is frozen in golden tests.

## Migration And Compatibility

- No global CLI envelope version change.
- No workspace schema change.
- No definition, question or rubric schema change is required unless
  implementation proves that current artifacts cannot preserve the accepted
  disposition. Any such discovery requires a design update before coding that
  schema change.
- Vertical mutation receipt result schema advances to the new current form;
  obsolete receipt forms are rejected, not migrated.
- The old generic `impact` key set and implicit orphaning are unsupported in the
  new release.
- The `--mapping` option remains, but only the canonical plan document is
  accepted.
- P2P Engine 0.4.7 remains unchanged. WaveKit must update its exact pin and
  fixtures only after the new wheel is released.

## Public Surface And MCP Parity

- CLI contract: changed domain payload on six existing preview/apply commands;
  exact command paths and global envelope remain.
- MCP contract: no new tool and no payload change. Capability inventory and
  documentation explicitly retain owner-governed CLI-only classification.
- Storage contract: typed current receipt result; canonical project artifacts
  remain current.
- Documentation contract: exact schemas, bounds, examples, retry/re-preview
  rules and compatibility statement.
- Test contract: pure model/classifier/analyzer tests, service and transaction
  tests, CLI golden contracts, agent-template checks, source/wheel parity and
  full suite.

## WaveKit 7.8 Closure Handoff

The P2P release must provide sanitized installed-wheel fixtures for:

| Fixture | WaveKit behavior it unlocks |
| --- | --- |
| empty adoption preview | exact empty classification and adoption routing |
| owner-question-only adoption blocker | populated classification outside definition fields |
| custom-rubric-only adoption blocker | populated classification from rubric evidence |
| migration with automatic preservation | complete same-ID preservation parsing |
| migration with unresolved field/rubric/question decisions | complete required-mapping UI and parser |
| migration with a complete mixed plan | exact map and orphan preservation tests |
| stale plan and stale preview | state/decision binding tests |
| migration apply and exact replay | receipt/postcondition and duplicate-delivery tests |
| bounded-impact blocker | output-limit and no-hidden-decision tests |

WaveKit still owns owner transfer, supporter denial, application-level token
expiry, PostgreSQL project serialization, cross-project parallelism, queue
delivery, crash reconciliation and post-apply validation. Those portions of
task `7.8` are not moved into P2P Engine.

## Test Strategy

Following `specs/skills/TEST_QUALITY_SKILL.md`:

1. pure model tests freeze exact serialization, enums, ordering and bounds;
2. classifier service tests vary one evidence family at a time;
3. analyzer tests prove every transition and required decision without writes;
4. materializer tests prove preservation, mapping and orphan disposition;
5. question/rubric tests protect their distinct memory-family behavior;
6. lifecycle tests prove token binding, apply, receipt, replay and atomicity;
7. CLI tests protect operation IDs, envelopes, exit classes and text summaries;
8. privacy tests seed recognizable secret strings and assert absence from every
   public/receipt surface;
9. installed-wheel tests execute the exact WaveKit handoff matrix without
   importing source-tree modules;
10. public and full suites catch unrelated CLI/MCP/template regressions.

Do not repeat every service scenario through CLI. CLI tests protect the public
shape and representative failures; lower-layer tests own the combinatorial
evidence matrix.

## Risks And Tradeoffs

- **Breaking consumer payload**: necessary to replace an undocumented and
  incomplete shape. Mitigated by operation contract, exact release pin and
  wheel fixtures.
- **More explicit owner steps**: migration may need two previews. This is the
  intended cost of removing hidden orphan decisions.
- **Payload growth**: bounded collections may block unusually large
  transitions. This is safer than silently hiding decisions; pagination can be
  proposed separately if real projects hit the bound.
- **Question complexity**: reuse current reconciliation identity and evidence
  rules to avoid a second lifecycle.
- **Receipt size**: store hashes and bounded decision metadata, never evidence
  values; choose limits that fit the current receipt file maximum.
- **Scope expansion**: do not redesign generic mutation preview, remote
  registry, WaveKit or all persisted memory families in this feature.

## Out Of Scope

- Server-side WaveKit implementation and tests.
- New MCP mutation tools.
- Fuzzy or AI-assisted mapping.
- Pagination for oversized transition impact.
- Generic mutation-preview redesign.
- Project-management or implementation-repository behavior.
