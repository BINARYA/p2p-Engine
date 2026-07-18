# Requirements - Proposal Decision Revision And Revocation Lifecycle

## Scope

Implement the accepted `PROP-102` decision lifecycle through `CHANGE-070`.
Replace the current overwrite-only proposal decision model with an append-only,
versioned decision-event ledger, while retaining `proposal.md` and
`decision.md` as compatible human-readable projections.

The feature must distinguish a proposal that was never adopted from one whose
accepted authority was later revoked or replaced. It must preserve history,
validate owner authority, make revisions transactional and source-bound, expose
revocation impact without changing dependent lifecycles, and move the workspace
from schema v2 to schema v3 through the existing migration framework.

## Origin And Delivery State

- Governed source: accepted `PROP-102`.
- Delivery container: `CHANGE-070`, currently `planned`.
- P2P-native software spec:
  `.p2p/outputs/software-spec/CHANGE-070`.
- Local implementation specification: this feature directory.
- Current runtime baseline: P2P Engine `0.3.1`.
- Current workspace baseline: schema v2.
- Target workspace schema: v3.
- Target runtime line: `0.4.x`, with explicit v2 read compatibility and a
  registered v2-to-v3 migration.

The proposal and Change Set remain the governed source. These local
requirements refine implementation details without replacing P2P authority.

## Current-System Baseline

- `ProposalDecisionService.record()` overwrites `decision.md` and the `Status`
  section in `proposal.md`.
- `DecisionOutcome` has no `withdrawn`, `revoked`, `reinstated` or
  `unknown_legacy` representation.
- A second decision write has no previous-state validation, event identity,
  predecessor link, exact-retry contract or queryable history.
- CLI `proposal accept`, `proposal reject`, `proposal defer` and `decision
  record` are one-step writes.
- MCP proposal decision tools validate consent but delegate to the same
  overwrite path.
- Several services read `proposal.md` status or `decision.md` directly,
  including proposal views, registries, validation, Change Set creation,
  software-spec preflight, decision context, project projections, vertical
  evidence, maturity, progress, assessment, exports and freshness.
- The current lifecycle authority policy treats only accepted,
  accepted-with-changes and replacement outcomes as committed, and does not
  represent active intervals or prior authority.
- The workspace migration registry has adjacent transitions from legacy to v1
  and v1 to v2 only.
- `AtomicMutationWriter`, source-bound mutation previews, permission resolution,
  operation-schema gates, durable migration transactions and consent receipts
  already exist and must be reused.
- Managed proposal branch acceptance/rejection is a separate collaboration
  lifecycle and must remain separate from proposal decision events.

## In Scope

- A versioned canonical decision-event ledger for every schema-v3 proposal.
- A strict parser, serializer, validator and integrity chain for that ledger.
- A single lifecycle-authority read model for current and historical proposal
  decision state.
- A complete transition matrix for initial decisions, deferral, withdrawal,
  rejection, revocation, supersession, split, merge and exact reinstatement.
- Owner-authorized, stateless preview/apply decision mutations.
- Exact retry, stale preview, reused operation identity, concurrent head and
  interrupted transaction behavior.
- Human-readable current projections in `proposal.md` and `decision.md`.
- Revocation/replacement impact discovery and generated remediation next
  actions.
- Read-compatible schema-v2 behavior and blocked event-dependent writes until
  migration.
- A registered, forward-only, atomic and loss-aware v2-to-v3 migration.
- Explicit owner curation for ambiguous legacy authority.
- Explicit projection repair and reviewed ledger recovery primitives.
- Convergence of all current proposal-decision consumers.
- CLI and permission-gated MCP parity over the same domain services.
- Validation, diagnostics, documentation, release compatibility and
  repository dogfooding.

## Out Of Scope

- Deleting proposal history or rewriting valid prior decision events.
- Using Git history, Git author metadata, filesystem mtimes or file ownership
  to infer owner authority, rationale or decision dates.
- Automatically reverting code, closing Change Sets, retiring Work, deleting
  specs, removing vertical evidence or changing publication approval.
- Treating downstream `deprecated` state as a proposal decision outcome.
- Reconsidering a rejected or withdrawn proposal in place; changed intent
  requires a new linked proposal.
- Reinstating changed proposal content, conditions or constraints.
- Automatically restoring technical effects when a decision is reinstated.
- A database, background daemon, remote event service or persistent decision
  cache.
- The future thematic compaction or consolidation of decision memory. This
  feature supplies the event-head and authority-interval contract that such a
  feature must consume.
- Changing choice decision semantics or managed branch accept/reject semantics.
- Publishing a release, changing the repository runtime contract or migrating
  this repository without a separate owner-confirmed deployment step.

## Public Surface And Compatibility

| Surface | Required change | Compatibility rule |
| --- | --- | --- |
| Proposal creation | Add an empty schema-v3 ledger | Existing proposal files and IDs remain |
| Proposal show/list/full view | Read the lifecycle authority view | Existing fields remain; event-head/history fields are additive |
| `p2p decision` | Add status, history, preview, apply and repair/legacy-resolution operations | Existing command group remains |
| Proposal decision shortcuts | Route through the shared preview/apply service | Command names remain; one-step mutation is intentionally removed |
| MCP reads | Add status/history/impact-preview parity | Payload fields match CLI JSON semantics |
| MCP writes | Use token-bound consent and the same apply service | No direct handler-side decision logic |
| Storage | Add `decision-events.yml`; retain projection files | Ledger is canonical in v3; projections are derived compatibility views |
| Workspace schema | Add adjacent v2-to-v3 transition | v2 remains readable; decision writes require v3 |
| Registries and exports | Add event-head and authority metadata | Existing record identities remain stable |
| Decision context | Extract ledger history and current authority | Historical rationale remains retrievable but inactive |
| Change/Work/spec flows | Detect inactive or unresolved source decisions | Existing dependent objects are not automatically mutated |
| Agent guidance | Explain rejection, revocation, replacement and reinstatement | Owner authority remains mandatory |

Changing the old decision commands from an immediate write to a two-phase
preview/apply contract is an intentional governance safety change authorized by
`PROP-102`. The command names must not silently preserve the unsafe one-step
write behavior.

## Terminology

- **Decision event**: one immutable, owner-authorized lifecycle fact.
- **Ledger**: the ordered, validated collection of decision events and
  loss-aware legacy evidence for one proposal.
- **Head**: the latest valid event controlling current effective state.
- **Effective state**: current proposal decision state derived from the ledger.
- **Active authority**: an accepted or conditionally accepted decision that
  currently constrains the project.
- **Previously active**: authority that was active before revocation or
  replacement.
- **Projection**: engine-owned current-state rendering in `proposal.md` or
  `decision.md`.
- **Legacy evidence**: preserved schema-v2 values that cannot safely become a
  decision event without owner curation.
- **Exact retry**: replay of the same operation identity and complete semantic
  request against the same source event.
- **Reconsideration**: a new linked proposal after rejection or withdrawal.
- **Reinstatement**: reactivation of the exact decision fingerprint referenced
  by a prior revocation.
- **Remediation action**: a generated instruction to review a dependent object;
  it is not proof that the dependency was changed.

## Functional Requirements

### F1 - Canonical Ledger And Projection Contract

- R-F1-001: EACH proposal created in a schema-v3 workspace SHALL contain exactly
  one canonical `decision-events.yml` ledger.
- R-F1-002: THE ledger root SHALL identify its contract version, proposal ID,
  effective state, authority-resolution state, head event and ordered events.
- R-F1-003: EACH event SHALL contain an event schema version, stable event ID,
  idempotency operation key, proposal ID, event type, resulting effective
  state, rationale, structured decision conditions where applicable, canonical
  decision date, authority evidence, predecessor identity, predecessor hash,
  proposal semantic fingerprint, affected decision fingerprint where
  applicable, optional readiness-override binding, preview binding and event
  integrity hash.
- R-F1-004: OPTIONAL lineage SHALL use typed fields for replacement, split and
  merge targets; empty, self, duplicate and unknown targets SHALL be rejected.
- R-F1-005: OPTIONAL migration provenance SHALL identify the registered
  migration, source paths, preserved source values and source digests without
  manufacturing missing values.
- R-F1-006: EVENT ordering SHALL be deterministic and SHALL match predecessor
  links; the declared head SHALL be the final valid event.
- R-F1-007: EVENT IDs and integrity hashes SHALL be derived from a versioned
  canonical semantic payload and SHALL NOT depend on absolute checkout path,
  mtime, observation time or YAML key order.
- R-F1-008: THE event integrity hash SHALL cover all semantic event fields and
  the predecessor binding; modifying a prior event SHALL invalidate that event
  and every successor.
- R-F1-009: THE decision semantic fingerprint SHALL bind the accepted proposal
  semantics, accepted outcome and decision qualifiers that are being activated,
  revoked, replaced or reinstated.
- R-F1-010: THE proposal semantic fingerprint SHALL use an explicit,
  versioned normalization of governed proposal content and SHALL ignore
  projection-only status text.
- R-F1-011: `proposal.md` status and `decision.md` current decision SHALL be
  deterministic projections of the validated ledger head in schema v3.
- R-F1-012: `decision.md` SHALL expose at least event type, effective state,
  rationale, decision date, owner authority, head event ID, active decision
  fingerprint, lineage and ledger path when applicable.
- R-F1-013: A projection mismatch SHALL be reported as stale or invalid and
  SHALL NOT override a valid ledger.
- R-F1-014: A missing or invalid v3 ledger SHALL make decision authority
  unresolved and SHALL NOT silently fall back to projection files.
- R-F1-015: THE ledger parser SHALL reject unknown required structures,
  duplicate YAML keys, duplicate event IDs, duplicate operation keys, invalid
  hashes, invalid dates, proposal-ID mismatch and unsupported future schema
  versions with stable diagnostics.
- R-F1-016: READ operations SHALL preserve unknown legacy evidence as data but
  SHALL fail closed on unknown event semantics.
- R-F1-017: PROPOSAL artifact catalogs and source inventories SHALL classify
  the ledger as canonical and the two current-state files as projections.
- R-F1-018: A fresh schema-v3 proposal with no event SHALL derive
  `effective_state=undecided`, retain proposal status `draft`, and expose no
  active decision authority.
- R-F1-019: THE lifecycle view SHALL compare the current proposal semantic
  fingerprint with the proposal fingerprint bound to the controlling event and
  expose `current`, `diverged` or `unavailable` binding status.
- R-F1-020: PROPOSAL semantic divergence SHALL NOT rewrite or implicitly revoke
  a valid decision event, but current changed proposal claims SHALL NOT be
  presented as accepted authority.
- R-F1-021: CANONICAL event dates SHALL be non-decreasing along the predecessor
  chain; equal dates are allowed, but a successor earlier than its predecessor
  SHALL be rejected.
- R-F1-022: RATIONALE, conditions, lineage targets, ledger bytes, legacy scalar
  evidence and repair candidates SHALL have documented deterministic limits;
  oversize input SHALL fail before hashing/writing or be preserved as an
  explicit digest-plus-truncation legacy record.

### F2 - Lifecycle Authority, Transitions And Lineage

- R-F2-001: ONE lifecycle-authority service SHALL derive current state,
  committed state, active projection, ever-active state, prior active
  intervals, current decision fingerprint, lineage and diagnostics for every
  consumer.
- R-F2-002: THE public event vocabulary SHALL include `accepted`,
  `accepted_with_changes`, `deferred`, `withdrawn`, `rejected`, `revoked`,
  `superseded`, `split`, `merged_into_other` and `reinstated`.
- R-F2-003: `deprecated` SHALL be rejected as a proposal decision event.
- R-F2-004: FROM undecided, the system SHALL allow accepted,
  accepted-with-changes, deferred, withdrawn, rejected, split or
  merge-into-other decisions.
- R-F2-005: FROM deferred, the system SHALL allow accepted,
  accepted-with-changes, withdrawn, rejected, split or merge-into-other
  decisions.
- R-F2-006: FROM accepted or accepted-with-changes, the system SHALL allow only
  revocation, supersession, split or merge-into-other, apart from exact retry.
- R-F2-007: FROM revoked, the system SHALL allow only exact reinstatement of the
  referenced prior active decision, apart from exact retry.
- R-F2-008: REJECTED, withdrawn, superseded, split and merged-into-other states
  SHALL be terminal within the same proposal, apart from exact retry.
- R-F2-009: RECONSIDERATION after rejection or withdrawal SHALL require a new
  linked proposal and SHALL preserve the original proposal as historical.
- R-F2-010: REINSTATEMENT SHALL reference the revocation event and the exact
  prior active event, SHALL match its decision semantic fingerprint and SHALL
  require a current impact preview.
- R-F2-011: REINSTATEMENT SHALL restore the referenced active outcome
  (`accepted` or `accepted_with_changes`) as effective state while retaining
  `reinstated` as the head event type.
- R-F2-012: A proposal semantic change after revocation SHALL make
  reinstatement invalid and SHALL direct the owner to create a linked proposal.
- R-F2-013: SUPERSESSION SHALL require exactly one valid replacement proposal
  and a reciprocal or otherwise validated lineage assertion.
- R-F2-014: SPLIT SHALL require at least two distinct valid target proposals.
- R-F2-015: MERGE-INTO-OTHER SHALL require exactly one valid target proposal.
- R-F2-016: ACTIVE-to-inactive events SHALL preserve a closed authority interval
  and the prior active decision fingerprint.
- R-F2-017: DEFERRED SHALL be unresolved, not historical rejection and not
  active project authority.
- R-F2-018: WITHDRAWN and rejected SHALL both be never-active historical states
  with distinct reasons and retrieval semantics.
- R-F2-019: REVOKED SHALL be a previously-active historical state and SHALL not
  be presented as never accepted.
- R-F2-020: THE complete state/event matrix SHALL be table-tested, including
  required lineage, impact and exact-retry preconditions for every cell.
- R-F2-021: A new `accepted_with_changes` event SHALL contain at least one
  non-empty structured condition with stable identity; free-form rationale
  alone SHALL NOT satisfy the condition contract.
- R-F2-022: SEMANTIC proposal updates SHALL be allowed in place only while
  authority is undecided or deferred. For active or terminal decision states,
  only normalization-equivalent edits are allowed; changed intent requires a
  new linked proposal.

### F3 - Governed Preview, Apply, Retry And Recovery

- R-F3-001: EVERY decision write SHALL use one application service shared by
  CLI, MCP and the `P2PWorkspace` compatibility facade.
- R-F3-002: PREVIEW SHALL be read-only and SHALL capture one immutable request
  snapshot containing proposal bytes, ledger/head, both projections,
  permissions, lineage targets and all impact sources relevant to the event.
- R-F3-003: PREVIEW SHALL validate workspace compatibility, ledger integrity,
  transition legality, lineage, semantic fingerprints and owner authority
  before returning an applicable token.
- R-F3-004: CLI preview SHALL require an actor that resolves to the project
  owner.
- R-F3-005: MCP preview MAY be requested by an agent or contributor, but apply
  SHALL require a single-use consent receipt approved by the current owner and
  bound to the proposal, event request and preview token.
- R-F3-006: THE preview token SHALL bind operation key, actor/executor,
  validated owner, permission-policy fingerprint, proposal semantic
  fingerprint, source head, all source preconditions, lineage, impact
  fingerprint, decision date and candidate semantics.
- R-F3-007: APPLY SHALL require the same semantic request, operation key,
  preview token and explicit confirmation used by preview.
- R-F3-008: APPLY SHALL revalidate owner authority, permission bytes, proposal
  semantics, ledger head, projection bytes, lineage targets and impact sources
  under the mutation lock.
- R-F3-009: APPLY SHALL atomically commit the ledger, `proposal.md` and
  `decision.md` candidates through `AtomicMutationWriter`, plus the readiness
  candidate when the accepted request includes an owner readiness override.
- R-F3-010: A failure before or during replacement SHALL leave all three live
  artifacts at the old valid state or return a durable recovery-required
  transaction; partial authority SHALL never be reported as committed.
- R-F3-011: APPLY SHALL return `already_applied` when the ledger contains the
  same operation key, preview binding and complete request fingerprint.
- R-F3-012: REUSING an operation key with different event semantics, actor,
  authority, lineage, date or source head SHALL fail with an idempotency
  conflict and perform no write.
- R-F3-013: APPLY against a changed source or head SHALL fail as stale or
  concurrent-head conflict and SHALL perform no write.
- R-F3-014: TWO concurrent applies against one source head SHALL result in one
  committed event and one deterministic already-applied or conflict result.
- R-F3-015: RESPONSE-loss retry SHALL be safe without a persistent preview
  cache because the committed event stores the operation and preview bindings.
- R-F3-016: THE operation compatibility registry SHALL require schema v3 for
  all proposal decision event writes and legacy-authority resolution writes.
- R-F3-017: THE old `proposal_decision_record` operation SHALL not remain an
  unclassified bypass; it SHALL route to the v3 service or fail with an
  actionable preview-required/schema-required diagnostic.
- R-F3-018: MANAGED branch accept/reject operations SHALL remain separate and
  SHALL not append proposal decision events.
- R-F3-019: AUTHORITY validation SHALL record the owner identity separately
  from an MCP executor identity and consent evidence.
- R-F3-020: AUDIT-only timestamps MAY be returned or logged, but SHALL NOT
  affect event identity, transition semantics or exact-retry matching.
- R-F3-021: AN MCP retry MAY reuse a consumed consent receipt only when the
  receipt's recorded result binds the same proposal, operation key, preview
  token and committed event; every other consumed-receipt use SHALL fail.
- R-F3-022: REVOCATION, supersession, split or merge SHALL remain possible when
  current proposal semantics diverge from the affected active event only after
  explicit owner acknowledgement of the drift; acceptance and reinstatement
  SHALL remain blocked by that divergence.
- R-F3-023: AN acceptance readiness override SHALL be previewed, source-bound
  and committed in the same transaction as the decision event; preview or
  failed apply SHALL not leave an orphaned readiness override.

### F4 - Revocation Impact And Remediation

- R-F4-001: PREVIEW for revoked, superseded, split, merged-into-other and
  reinstated events SHALL include a complete internal impact snapshot.
- R-F4-002: THE impact snapshot SHALL inspect direct and transitive dependent
  Change Sets, Work items, software specs, vertical coverage, project
  projections, decision-context records, relations, conflicts, freshness nodes
  and publication/export state.
- R-F4-003: DEPENDENCIES SHALL be classified by lifecycle status and whether
  they are active, completed, historical, generated or owner-controlled.
- R-F4-004: IMPACT discovery SHALL use bounded source access and deterministic
  ordering; it SHALL not perform a nested full-workspace scan per dependency.
- R-F4-005: PREVIEW output SHALL include total counts and truncation metadata.
  Presentation limits SHALL not remove hidden dependencies from the token
  fingerprint or apply preconditions.
- R-F4-006: AN incomplete or invalid impact snapshot SHALL block
  authority-changing apply rather than under-report dependencies.
- R-F4-007: REVOCATION SHALL remain owner-available when dependencies exist;
  dependencies create warnings and remediation, not a prohibition.
- R-F4-008: APPLY SHALL change only proposal decision authority and its
  projections. It SHALL NOT mutate Change Set, Work, spec, vertical, code,
  publication or Git lifecycle state.
- R-F4-009: AFTER an active decision becomes inactive, `p2p next` SHALL derive
  stable remediation actions for affected non-terminal and completed
  dependents.
- R-F4-010: REMEDIATION action identity SHALL be a deterministic function of
  proposal, head event, dependency kind and dependency ID; ordering SHALL use
  explicit kind/status rank followed by stable ID.
- R-F4-011: GENERATED remediation actions SHALL deduplicate against earlier
  curated actions by the established `(kind, target)` rule.
- R-F4-012: REMEDIATION reasons SHALL state that the source decision is revoked
  or replaced and SHALL not claim rollback or review completion.
- R-F4-013: REINSTATEMENT SHALL generate review actions for previously affected
  dependents but SHALL not remove evidence of prior remediation or restore
  technical state automatically.
- R-F4-014: IMPACT status and detail reads SHALL be side-effect free.

### F5 - Workspace Schema V3, Legacy Migration And Repair

- R-F5-001: `CURRENT_WORKSPACE_SCHEMA_VERSION` SHALL become 3 and the migration
  registry SHALL contain exactly one adjacent `workspace-v2-to-v3` transition.
- R-F5-002: THE default registry SHALL continue to resolve legacy-to-v1,
  v1-to-v2 and v2-to-v3 as one forward-only composed path.
- R-F5-003: RUNTIME support metadata SHALL declare which `0.4.x` runtimes can
  inspect, plan and apply v2-to-v3, while retaining supported older transition
  paths.
- R-F5-004: A schema-v2 workspace SHALL remain readable through an explicit
  legacy lifecycle adapter.
- R-F5-005: SCHEMA-v2 proposal decision writes SHALL fail closed with a command
  to plan migration to v3; unrelated operations whose declared minimum is v1
  or v2 SHALL remain available when otherwise safe.
- R-F5-006: THE v2-to-v3 planner SHALL produce one ledger candidate and
  matching engine-owned proposal/decision projection candidates for every valid
  proposal directory, and SHALL update workspace schema/history last.
- R-F5-007: AN aligned decided proposal with all required authority fields SHALL
  become one initial ledger event preserving every usable decision value and
  recording migration provenance.
- R-F5-008: A draft or pending proposal with no effective decision SHALL receive
  an empty ledger and remain undecided.
- R-F5-009: MISSING, malformed or unusable legacy values SHALL be retained in
  loss-aware `legacy_evidence` with `authority_resolution=unknown_legacy`.
- R-F5-010: PROPOSAL/decision status divergence SHALL be diagnosed. Migration
  SHALL not choose the active authority merely because one source has a
  preferred filename.
- R-F5-011: MIGRATION SHALL NOT infer owner, date or rationale from Git,
  filesystem mtime, current process user or unrelated project metadata.
- R-F5-012: AMBIGUOUS authority SHALL block normal decision revision until an
  owner runs the explicit legacy-resolution preview/apply primitive.
- R-F5-013: LEGACY resolution SHALL preserve the original evidence, record a
  current owner decision and SHALL not invent an earlier event date or active
  interval start.
- R-F5-014: MIGRATION planning SHALL be stateless, deterministic and byte
  invariant; apply SHALL reuse existing locking, candidate overlay, validation,
  journal, rollback, resume and idempotence behavior.
- R-F5-015: THE v2-to-v3 handler SHALL own only each proposal's ledger,
  `proposal.md` status projection, `decision.md` current projection and the
  workspace schema candidate. Before normalizing a projection, every usable
  legacy value SHALL be preserved in the ledger event or `legacy_evidence`.
- R-F5-016: CANDIDATE validation SHALL validate every ledger and its legacy
  source binding before schema v3 is committed.
- R-F5-017: A migration failure after any replacement SHALL restore exact v2
  bytes or expose recovery-required state.
- R-F5-018: REPEATED v2-to-v3 plan/apply after success SHALL be a no-op.
- R-F5-019: GLOBAL validation SHALL distinguish missing ledger, invalid ledger,
  chain corruption, unresolved legacy authority and projection drift.
- R-F5-020: PROJECTION repair SHALL regenerate only engine-owned projections
  from a valid ledger through owner preview/apply.
- R-F5-021: LEDGER repair SHALL require an explicit reviewed candidate source,
  preserve every validated event prefix and reject deletion, reordering or
  semantic rewriting of valid events.
- R-F5-022: UNSAFE ledger corruption without a valid recoverable candidate SHALL
  remain blocked and SHALL direct the owner to transaction recovery or reviewed
  repair; no automatic truncation is allowed.
- R-F5-023: FRESH schema-v3 initialization, proposal creation, workspace
  validation, migration fixtures and operation-gate fixtures SHALL all use the
  same version constants and artifact contract.

### F6 - Consumer Convergence And Derived State

- R-F6-001: NO schema-v3 consumer SHALL establish proposal authority by parsing
  `proposal.md` status or `decision.md` independently of the lifecycle service.
- R-F6-002: PROPOSAL show/list/status/full-view SHALL expose effective state,
  head event type, head event ID, event count, authority resolution,
  ever-active status and active decision fingerprint additively.
- R-F6-003: REGISTRY proposal and decision records SHALL retain existing IDs and
  fields while adding event-head, authority, history count, lineage and
  fingerprint metadata.
- R-F6-004: THE decision registry SHALL represent current effective state once
  per proposal; full event history SHALL remain in the ledger and history API,
  not duplicated as an unbounded registry payload.
- R-F6-005: CHANGE Set creation SHALL accept active `accepted` and
  `accepted_with_changes` authority, bind included decisions to head event and
  decision fingerprint, and reject inactive or unresolved sources.
- R-F6-006: EXISTING Change Sets and Work that depend on a later-inactive
  decision SHALL remain intact and SHALL expose source-authority diagnostics.
- R-F6-007: NEW Work planning and normal implementation-spec generation SHALL
  fail or require explicit remediation review when a governing source decision
  is inactive or unresolved, according to lifecycle status.
- R-F6-008: COMPLETED dependent lifecycle objects SHALL be reported as impact,
  not silently reclassified or reopened.
- R-F6-009: PROJECT projections, project status, progress, maturity and
  assessment SHALL count only currently active proposal authority on their
  active axes and SHALL preserve historical counts separately where useful.
- R-F6-010: VERTICAL declared evidence SHALL be active only when its proposal
  decision authority is active; historical mappings SHALL remain inspectable
  and SHALL not be deleted.
- R-F6-011: PROJECT definition completeness SHALL remain independent of proposal
  evidence activation.
- R-F6-012: SOFTWARE-spec source fingerprints SHALL include the bound decision
  head/fingerprint so revocation, replacement or reinstatement marks affected
  specs stale or blocked without relying on mtime.
- R-F6-013: DERIVED freshness source policies SHALL include ledger contract and
  lifecycle-authority policy versions.
- R-F6-014: VISIBLE export and publication inputs SHALL distinguish active,
  previously active, rejected/withdrawn and unresolved decisions.
- R-F6-015: INACTIVE decisions SHALL remain available as historical rationale
  and alternatives but SHALL not be rendered as current constraints.
- R-F6-016: RELATION and conflict consumers SHALL validate split, merge and
  supersession lineage against the ledger and quarantine incompatible active
  assertions.
- R-F6-017: PROPOSAL artifact status and publication source manifests SHALL
  include the ledger in canonical source ownership and avoid double-counting
  `decision.md`.
- R-F6-018: ALL changed consumers SHALL receive the lifecycle service through
  constructor injection or the workspace facade; lifecycle policy SHALL not be
  copied into each module.
- R-F6-019: A consumer that needs accepted proposal claims SHALL require a
  current proposal-to-event binding; on divergence it SHALL emit a blocker or
  stale result rather than use changed claims or silently classify the decision
  as revoked.

### F7 - Decision Context, Retrieval And Future Memory Binding

- R-F7-001: IN schema v3, the decision-context source catalog SHALL classify
  `decision-events.yml` as canonical decision semantics and `decision.md` as a
  derived compatibility projection.
- R-F7-002: IN schema v2, the source catalog SHALL continue to parse current
  proposal and decision files through the legacy adapter.
- R-F7-003: EXTRACTION SHALL create stable evidence and records for each valid
  decision event without reopening a source path more than once per request.
- R-F7-004: CURRENT active event records SHALL receive active accepted authority;
  prior active, rejected, withdrawn, revoked and replaced events SHALL receive
  historical authority.
- R-F7-005: REINSTATEMENT SHALL create a new active authority interval while
  retaining the revoked interval and event relations.
- R-F7-006: TOPOLOGY SHALL expose typed event lineage and proposal lineage
  without generating duplicate or contradictory relations from projection
  files.
- R-F7-007: RETRIEVAL SHALL be able to return inactive rationale when relevant,
  but SHALL label it historical and SHALL rank current active authority above
  otherwise equal historical evidence.
- R-F7-008: RETRIEVAL and context packets SHALL include head event ID,
  authority interval, lineage and decision fingerprint for material decision
  claims.
- R-F7-009: REVOCATION or reinstatement SHALL change the semantic decision
  context fingerprint and invalidate stale summaries bound to the former head.
- R-F7-010: FUTURE consolidated decision-memory records SHALL be able to bind to
  proposal ID, event head, authority interval, lineage and source fingerprint;
  this feature SHALL expose those fields without implementing compaction.
- R-F7-011: DECISION-context source, extractor, authority and topology policy
  versions SHALL be bumped when ledger semantics become active.
- R-F7-012: SCALE and determinism tests SHALL cover at least 100 proposals with
  multi-event histories and prove bounded source access and stable ordering.

### F8 - CLI, MCP, Diagnostics And Documentation

- R-F8-001: CLI SHALL provide read-only decision status and bounded history in
  text and JSON formats.
- R-F8-002: CLI SHALL provide one generic decision preview/apply contract for all
  supported event types, including explicit actor, reason, decision date,
  operation key, structured conditions, lineage and required references.
- R-F8-003: CLI SHALL provide bounded impact detail and shall display total
  counts, omitted counts, blockers, warnings, source head and apply command
  ingredients.
- R-F8-004: CLI SHALL provide explicit projection-repair preview/apply, reviewed
  ledger-repair preview/apply and legacy-authority-resolution preview/apply.
- R-F8-005: EXISTING `proposal accept`, `proposal reject`, `proposal defer` and
  `decision record` names SHALL remain documented compatibility entry points
  that use the shared two-phase service or emit an actionable
  preview-required result; they SHALL not call the old overwrite path.
- R-F8-017: EXISTING `proposal accept --override-readiness` semantics SHALL be
  preserved through the shared request, but the readiness artifact SHALL be
  written only by a confirmed matching apply.
- R-F8-006: CLI mutations SHALL return nonzero on schema, authority, transition,
  stale, replay mismatch, impact, integrity, recovery or confirmation failure.
- R-F8-007: MCP SHALL expose decision status, history and preview using the same
  serialized core results as CLI JSON.
- R-F8-008: MCP decision apply SHALL require a token-bound owner-approved
  consent receipt and SHALL consume or mark it with error using existing audit
  rules.
- R-F8-009: EXISTING MCP accept/reject/defer tool names SHALL remain as
  compatibility aliases or return a structured migration instruction; no tool
  may bypass preview/apply or owner consent.
- R-F8-010: MCP handlers SHALL contain argument parsing, consent routing and
  serialization only; transition, impact, authority and mutation logic SHALL
  remain in services.
- R-F8-011: TEXT and JSON outputs SHALL use stable reason/diagnostic codes and
  repository-relative paths.
- R-F8-012: THE feature SHALL reserve and document a non-conflicting diagnostic
  range for ledger, transition, preview, authority, impact, migration and repair
  failures.
- R-F8-013: GLOBAL validation, doctor, compact context and `p2p next` SHALL
  expose schema-v3 decision diagnostics and recovery commands consistently.
- R-F8-014: CLI guide, MCP guide, glossary, development guidance, migration
  documentation and agent templates SHALL explain the new lifecycle and the
  branch-operation boundary.
- R-F8-015: GENERATED agent instructions SHALL be refreshed through the normal
  agent lifecycle and tested for source/generated drift.
- R-F8-016: PUBLIC serialization changes SHALL be additive except for the
  explicitly approved removal of unsafe one-step decision writes.

### F9 - Release, Repository Migration And Alignment

- R-F9-001: THE implementation SHALL declare the package/runtime version and
  schema/runtime support matrix consistently across code, package metadata,
  templates and documentation.
- R-F9-002: BUILT wheel and sdist artifacts SHALL include every new module,
  template and migration resource and SHALL pass installed-artifact smoke tests.
- R-F9-003: PUBLIC and full suites SHALL pass on the supported Python matrix
  before release or repository migration.
- R-F9-004: NO repository `.p2p` migration SHALL begin until schema-v3 code,
  v2 read compatibility, v2-to-v3 plan/apply, recovery and consumer convergence
  have passed focused and full gates.
- R-F9-005: THE repository migration SHALL start with read-only schema status,
  validation, registry/freshness baseline and a reviewed v2-to-v3 dry-run.
- R-F9-006: THE migration plan SHALL enumerate all proposal ledgers, ambiguous
  legacy evidence, owned targets, derived refresh actions and candidate
  validation results.
- R-F9-007: OWNER input SHALL be requested only for proposals whose legacy
  authority cannot be established safely; aligned proposals SHALL not require
  redundant confirmation.
- R-F9-008: APPLY SHALL use the released or explicitly verified target runtime,
  matching project runtime contract and owner confirmation.
- R-F9-009: AFTER migration, validation SHALL report schema v3, no missing
  ledgers, no invalid event chains and no unexplained projection divergence.
- R-F9-010: REGISTRIES, project projections, decision context, progress,
  maturity, assessment, freshness, software specs, next actions, visible export
  and publication status SHALL be reviewed for rebuild or staleness in
  dependency order.
- R-F9-011: GENERATED artifacts SHALL be refreshed only through their owning
  commands; owner-reviewed or agent-curated artifacts SHALL remain pending
  until their own lifecycle step.
- R-F9-012: THE final comparison SHALL reconcile proposal/decision counts,
  current active counts, historical states, Change/Work/spec impacts,
  unresolved legacy authority and derived freshness against the pre-migration
  baseline.
- R-F9-013: PUBLICATION approval SHALL remain owner-controlled and SHALL not be
  changed by migration or derived refresh.
- R-F9-014: ANY residual manual repository curation SHALL be listed explicitly
  with owning primitive, target, evidence and owner decision; direct `.p2p`
  edits remain forbidden.

## Non-Functional Requirements

- N001: Domain rules SHALL live in typed core models and cohesive services, not
  in CLI, MCP handlers, exporters or `P2PWorkspace`.
- N002: `P2PWorkspace` SHALL remain a compatibility facade with thin
  delegation.
- N003: The ledger parser/serializer, transition policy, authority policy,
  fingerprint policy and diagnostic vocabulary SHALL be independently
  versioned where semantic drift matters.
- N004: Read-only operations SHALL perform zero persistent writes.
- N005: All ordering, identity and hashing SHALL be deterministic across
  filesystem enumeration order, YAML key order, clocks and absolute roots.
- N006: Canonical writes SHALL be atomic, process-safe, recoverable and
  idempotent.
- N007: Failed preconditions SHALL leave canonical and derived files byte
  invariant.
- N008: Source access SHALL be request-scoped and bounded; no consumer may
  rediscover all proposal files once per record.
- N009: Error text SHALL be actionable, while stable codes and typed fields
  carry machine semantics.
- N010: Existing v2 workspaces SHALL remain inspectable without migration.
- N011: Existing compatible JSON fields and record IDs SHALL remain stable
  unless this specification explicitly approves a behavior change.
- N012: New YAML SHALL use strict structured parsing and established dump
  helpers; no ad hoc text parsing of the ledger is allowed.
- N013: Test coverage SHALL scale from pure transition tables to service,
  transaction, migration, CLI, MCP, consumer, installed-artifact and repository
  dogfood tests.
- N014: Failure injection SHALL cover every multi-target replacement boundary.
- N015: Concurrency tests SHALL use separate processes or equivalent
  lock-contending writers, not only sequential mocks.
- N016: No test SHALL rely on real Git history, network access, current user,
  local timezone or mtime to establish decision semantics.
- N017: The requirement-to-design-to-task-to-test/evidence matrix SHALL be
  initialized before implementation and updated at every slice exit.
- N018: Each implementation slice SHALL end with focused tests and a reviewed
  compatibility diff before the next slice begins.
- N019: No implementation or migration task may edit `.p2p` by hand.
- N020: Release, Git publication and repository migration remain separate
  owner-confirmed operations.

## Edge Cases And Failure Semantics

- E001: A proposal has `accepted` in `proposal.md` and `rejected` in
  `decision.md` during v2 migration.
- E002: A legacy decision has a valid outcome but missing approver, date or
  reason.
- E003: A legacy decision contains an unsupported outcome token.
- E004: A schema-v3 ledger is missing while projections appear valid.
- E005: A ledger head does not equal the final event.
- E006: A predecessor ID matches but its stored hash does not.
- E007: Two events reuse one operation key with different semantics.
- E008: A projection was manually changed after a valid event commit.
- E009: Proposal governed content changes between preview and apply.
- E010: Permissions change between preview and apply.
- E011: A lineage target is deleted, duplicated, self-referential or changes
  state before apply.
- E012: A dependency appears beyond the visible impact page.
- E013: Impact discovery sees an invalid Change Set or Work manifest.
- E014: Two processes apply the same event and token concurrently.
- E015: Two processes apply different events from the same head.
- E016: The transaction fails after ledger replacement but before projection
  replacement.
- E017: A response is lost after commit and the client retries on a later date.
- E018: A rejected proposal is passed to reinstatement.
- E019: A revoked proposal changed one acceptance condition before
  reinstatement.
- E020: A conditional acceptance is revoked and exactly reinstated.
- E021: A split has one target, duplicate targets or a terminal target.
- E022: A supersession target does not refer back through supported lineage
  evidence.
- E023: A dependent Change Set is completed and its generated spec is modified.
- E024: A migrated proposal has unknown legacy authority and normal apply is
  attempted.
- E025: A reviewed ledger repair candidate removes a valid historical event.
- E026: A newer runtime opens a valid v2 workspace and performs an unrelated
  v2-safe write.
- E027: An older runtime opens a schema-v3 workspace.
- E028: An MCP consent is approved by a non-owner, targets a different preview
  token or is replayed.
- E029: Decision-context extraction sees both a ledger and a divergent
  `decision.md`.
- E030: A future ledger schema or unknown event type is encountered.

## Acceptance Criteria

- AC001: A fresh schema-v3 proposal has one valid empty ledger and compatible
  draft/pending projections.
- AC002: Parser and serializer tests round-trip every event type and reject all
  integrity, identity, schema and duplicate-key failures.
- AC003: A complete transition-matrix test covers every current state/event
  pair, exact retries and required lineage/impact fields.
- AC004: An accepted proposal can be revoked without erasing acceptance history;
  status becomes revoked, `ever_active` remains true and prior rationale remains
  retrievable.
- AC005: A rejected or withdrawn proposal cannot be revised in place and emits
  a linked-proposal recovery instruction.
- AC006: Exact reinstatement restores the original active outcome and rejects
  any changed proposal or decision fingerprint.
- AC007: Owner authority tests cover CLI owner, MCP executor with
  owner-approved token-bound consent, non-owner denial and permission changes.
- AC008: Preview/apply tests prove stale proposal, head, projection,
  permissions, lineage and impact sources produce no writes.
- AC009: Failure injection at every target replacement proves all-old,
  all-new or recovery-required state, never mixed authority.
- AC010: Separate-process tests prove one-winner behavior for same and
  conflicting head operations.
- AC011: Response-loss retry returns `already_applied`; operation-key reuse with
  changed inputs returns the stable replay-mismatch diagnostic.
- AC012: Revocation impact fixtures cover active and completed Change Sets,
  Work, specs, vertical evidence, context, conflicts and publication/freshness.
- AC013: Revocation changes no dependent lifecycle file and produces stable,
  correctly ordered remediation next actions.
- AC014: A v2 workspace remains readable and all event-dependent writes are
  blocked with a v3 migration command.
- AC015: v2-to-v3 dry-run is byte invariant, deterministic and owns exactly the
  declared ledger/schema targets.
- AC016: Aligned, pending, malformed, missing and divergent legacy proposal
  fixtures migrate loss-aware without Git or mtime inference.
- AC017: Migration failure, rollback, recovery, resume, exact no-op and composed
  legacy-to-v3 paths pass.
- AC018: Projection repair fixes drift from a valid ledger; unsafe ledger repair
  attempts cannot remove or rewrite valid history.
- AC019: Proposal views, registries, Change/Work/spec preflight, project
  projections, vertical evidence, progress, maturity, assessment, freshness,
  export and publication all consume the same lifecycle authority, and reject
  current proposal claims whose semantic binding diverges from the controlling
  event.
- AC020: Decision-context tests expose current and historical event authority,
  lineage, active intervals and head-bound fingerprints without double-counting
  projections.
- AC021: Retrieval ranks active authority over equal historical evidence while
  retaining revoked/rejected rationale with explicit historical labels.
- AC022: CLI text, CLI JSON and MCP payloads agree on stable semantic fields for
  status, history, preview, apply, impact and repair.
- AC023: Legacy decision shortcuts and MCP aliases cannot execute the old
  overwrite path, and readiness override preview/failure leaves
  `readiness.yml` unchanged.
- AC024: Global validation and doctor emit stable, actionable schema-v3 ledger
  and projection diagnostics.
- AC025: A 100-proposal multi-event fixture passes deterministic, bounded-access
  and payload-limit gates.
- AC026: Focused service, transaction, migration, CLI, MCP, consumer and
  performance suites pass.
- AC027: Public and full repository test suites pass on the supported Python
  matrix.
- AC028: Built wheel/sdist verification and isolated installed-runtime smoke
  tests pass.
- AC029: The repository v2-to-v3 migration is separately owner-confirmed,
  validated and compared with its baseline before derived artifacts are
  refreshed.
- AC030: Final alignment reports no unexplained ledger/projection divergence,
  no missing schema-v3 ledgers and no automatic publication approval.
