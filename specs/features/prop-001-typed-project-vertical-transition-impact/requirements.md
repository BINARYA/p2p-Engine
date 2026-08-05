# Requirements - Typed Project Vertical Transition Impact

## Origin

- Accepted P2P proposal: `PROP-001`, "Typed vertical transition impact and
  explicit migration decisions".
- Owner decision: accepted by `mrjungle` on 2026-08-05 without readiness
  override.
- Readiness at acceptance: `100`, `decision_ready`, high confidence, no failed
  gates.
- Historical gap: `PROP-103` R029 required complete migration impact, but the
  0.4.7 public model still exposes an unversioned `dict[str, object]`.
- Downstream driver: WaveKit `manage-versioned-project-verticals` task `7.8`
  cannot prove empty/populated classification or complete preservation and
  mapping behavior from the 0.4.7 preview contract.
- Baseline release: P2P Engine `0.4.7`.
- Target release: the next P2P Engine release, expected to be `0.4.8`.

## Goal

Expose one deterministic, bounded and versioned CLI contract that lets an owner
or strict external consumer understand and decide every material effect of
installing, adopting or migrating a project vertical without reading `.p2p`,
duplicating P2P semantics or receiving raw project evidence.

## Definitions

- **Transition impact contract**: the operation-level public contract
  `p2p-vertical-transition-impact/v1`, carried under the unchanged global
  `p2p-cli/v1` envelope.
- **Evidence classifier**: the single authoritative service that classifies a
  project definition as `empty` or `populated` from the evidence families in
  this specification.
- **Automatic preservation**: preservation that is safe without an owner
  choice because source and target have the same exact semantic identity.
- **Required decision**: a deterministic, stable-ID choice that must be
  supplied before apply can be allowed.
- **Exact map**: an explicit source-to-target association using exact typed
  references; similarity and fuzzy matching are forbidden.
- **Preserve as orphan**: an explicit choice to retain evidence in the owning
  memory family without letting it count as active target-vertical evidence.
- **Analysis fingerprint**: the SHA-256 identity of current relevant state,
  exact target identity, normalized structural analysis and contract version,
  excluding owner decisions.
- **Plan fingerprint**: the SHA-256 identity of the analysis fingerprint plus
  the complete normalized owner decision set.
- **Complete preview**: a preview in which no collection is silently omitted or
  truncated and every required decision is represented.

## In Scope

- Typed install, adoption and migration impact models.
- One shared empty/populated evidence classifier.
- Structured section, field, assumption, blocker, orphan, rubric, question,
  lock and governed-artifact effects.
- A canonical decision-plan document consumed by migration preview and apply.
- Explicit exact-map or preserve-as-orphan decisions.
- Deterministic bounded output with fail-closed completeness handling.
- Preview-token, idempotency fingerprint and receipt binding to the exact plan.
- Stable semantic postconditions for apply and replay.
- CLI contract, error and fixture updates.
- Maintained CLI/MCP documentation, capability inventory and generated agent
  guidance.
- Source-tree and immutable installed-wheel verification.
- A precise handoff contract sufficient for WaveKit to complete the remaining
  portion of task `7.8` after updating its runtime pin.

## Out Of Scope

- WaveKit Django, worker, Angular, MCP HTTP or database changes.
- Remote vertical registry, authentication, publication, moderation, lineage,
  counters or rewards.
- New MCP stdio mutation tools for install, adoption or migration.
- Fuzzy, text-similarity or AI-generated mappings.
- Raw evidence values, question answers, assumption text, blocker text or
  internal filesystem paths in transition impact.
- Wall-clock expiry for P2P preview tokens; downstream services may impose a
  shorter application-level expiry.
- A global `p2p-cli/v2` envelope change.
- Compatibility aliases for the undocumented generic 0.4.7 impact shape or
  implicit orphaning behavior.
- A workspace schema change or migration of discarded pre-current memory
  forms.

## Public Surface And MCP Impact

- CLI impact: breaking operation-payload change for vertical install/adopt/
  migrate preview and apply under the existing command paths and
  `p2p-cli/v1` envelope.
- CLI input impact: `--mapping` remains the path option on migrate preview and
  apply, but the file becomes the strict canonical transition-plan schema. The
  undocumented loose mapping forms are not retained as fallback contracts.
- MCP impact: preserve the current tool set. Vertical lifecycle mutation stays
  CLI-only; capability metadata and generated guidance must state the new
  decision workflow and the explicit omission rationale.
- Storage impact: no canonical project schema change. Vertical mutation
  receipts advance to their current typed result contract and reject obsolete
  receipt forms rather than adapting them.
- Agent-facing behavior: generated generic, Codex and Claude guidance explains
  classification, blocked decision previews, plan completion, re-preview and
  exact apply.
- Compatibility posture: `0.4.7` remains immutable. Consumers must pin the new
  engine release and assert the operation contract before parsing the new data.

## Functional Requirements

### Versioned Public Contract

- R001: Every successful install, adoption or migration preview SHALL expose
  `impact.contract_version == "p2p-vertical-transition-impact/v1"` under the
  existing `p2p-cli/v1` success envelope.
- R002: Install, adoption and migration SHALL use distinct typed domain models
  with an explicit operation discriminator; callers SHALL NOT infer the model
  from optional dictionary keys.
- R003: The contract SHALL define exact required fields, enum values,
  collection envelopes, nullability, deterministic ordering and bounds.
- R004: Serialization SHALL be generated from typed domain objects and SHALL
  reject unknown internal enum or evidence kinds before public output.
- R005: Impact SHALL identify the exact source vertical and lock when present,
  the exact target coordinate, semantic checksum, artifact checksum when
  available, profile, modules and dependency-lock identity.
- R006: Impact SHALL expose an `analysis_fingerprint_sha256`; a preview with a
  complete plan SHALL additionally expose `plan_fingerprint_sha256`.
- R007: The public vertical lifecycle payload SHALL contain no raw project
  evidence values, question answer values, free-form assumption/blocker text,
  credentials, per-file physical hashes, source preconditions, token context or
  internal filesystem paths. Exact public pack/checksum identities remain
  required. The opaque preview token SHALL appear only once in the bounded
  public preview summary required for apply.
- R008: Every impact collection SHALL report `total`, `returned`, `truncated`
  and deterministically ordered `items`. A truncated material collection SHALL
  block apply rather than hide unreviewed effects.

### Authoritative Evidence Classification

- R009: Adoption and migration SHALL call the same evidence classifier over
  one captured project snapshot.
- R010: The classifier SHALL count non-empty definition field values,
  assumptions, blockers and existing definition orphans.
- R011: The classifier SHALL count project questions with owner evidence,
  including answered, applied, deferred or muted questions and questions with
  answer or application records.
- R012: The classifier SHALL count rubric customization relative to the active
  locked vertical baseline, including changed enablement, changed semantic
  fields, added criteria and previously orphaned criteria.
- R013: Unanswered generated questions and unchanged vertical-default rubrics
  SHALL NOT by themselves make a project populated.
- R014: Classification SHALL be `empty` only when every approved evidence
  family has count zero; otherwise it SHALL be `populated`.
- R015: The public source-state result SHALL expose bounded typed evidence
  counts and stable evidence-family identifiers, not evidence content.

### Install, Adoption And Migration Analysis

- R016: Install impact SHALL report target identity, artifact and semantic
  checksums, verified dependency closure, install disposition, conflict state
  and bounded artifact-kind counts without exposing install paths or archive
  entry names.
- R017: Adoption preview SHALL report the authoritative source classification,
  `adoption_eligible` and `migration_required`; populated state SHALL return a
  structured migration-required blocker.
- R018: Migration preview SHALL require populated state and SHALL return a
  structured adoption-required diagnostic when the state is empty.
- R019: Transition analysis SHALL report added, removed and semantically
  changed sections and fields using exact stable section/field references and
  changed-attribute names.
- R020: Every meaningful definition field, assumption and blocker SHALL have
  one transition disposition: `preserved`, `mapped`, `decision_required` or
  `preserve_as_orphan`.
- R021: Exact same-identity evidence SHALL be preserved automatically with
  provenance; moved or renamed evidence SHALL never be preserved implicitly.
- R022: Existing explicit orphans SHALL be preserved and reported as existing
  orphan evidence without requiring the owner to decide the same orphan status
  again.
- R023: Lock impact SHALL report before/after coordinates and checksums,
  dependency additions/removals, profile changes and module changes.
- R024: Governed-artifact impact SHALL report semantic `create`, `update`,
  `no_change` or `remove` effects for active vertical, lock, definition,
  rubrics and project questions using artifact kinds rather than paths.
- R025: Question impact SHALL report preserved, revised, created, retired,
  superseded, inactive-owner-evidence and owner-review-required question IDs
  through bounded typed collections.
- R026: Rubric impact SHALL report preserved defaults, preserved
  customizations, mapped criteria, orphan-directed criteria, additions,
  removals and semantic collisions through structured entries.
- R027: Every resolvable problem SHALL appear as a typed blocker, warning or
  required decision with stable code, category, reference and recovery action;
  rubric collisions and question reconciliation conflicts SHALL NOT escape only
  as free-form exceptions.

### Explicit Transition Plan

- R028: Migration `--mapping` input SHALL accept one canonical
  `p2p-vertical-transition-plan/v1` document containing schema version,
  analysis fingerprint and a bounded list of decisions.
- R029: A migration preview without a complete plan SHALL remain read-only and
  SHALL return every required decision with a stable ID, evidence kind, source
  reference and allowed actions.
- R030: A `map` decision SHALL name one exact compatible target reference and
  SHALL reject unknown sources, unknown targets, kind mismatches and duplicate
  target ownership.
- R031: A `preserve_as_orphan` decision SHALL retain the evidence and provenance
  in its owning current memory family while excluding it from the active target
  baseline.
- R032: Missing, duplicate, contradictory, extra or reordered-semantic
  decisions SHALL be normalized deterministically or rejected with stable
  diagnostics; silent last-write-wins behavior is forbidden.
- R033: A plan SHALL be rejected as stale when its analysis fingerprint does
  not match the current source/target analysis.
- R034: The analyzer and materializer SHALL perform no fuzzy matching and SHALL
  not infer an owner decision from labels, titles or text similarity.
- R035: Candidate materialization SHALL begin only after the complete plan has
  validated and SHALL preserve every accepted evidence disposition exactly
  once.

### Preview, Apply, Atomicity And Receipts

- R036: Install, adoption and migration preview SHALL perform zero persistent
  writes, including on blocked, invalid, oversized or incomplete-plan paths.
- R037: `apply_allowed` SHALL be true only when classification permits the
  operation, impact is complete, every required decision is satisfied and no
  blocker remains.
- R038: The mutation preview token SHALL bind contract version, analysis
  fingerprint, plan fingerprint when applicable, actor, target identity,
  profile, modules, candidate semantics and all relevant source preconditions.
- R039: Any relevant change to definition, questions, rubrics, active vertical,
  lock, target checksum or normalized decisions SHALL invalidate the previous
  token or plan.
- R040: Apply SHALL re-run classification, analysis, plan validation and
  materialization before comparing the supplied preview token.
- R041: Apply SHALL atomically commit active vertical, lock, definition,
  rubrics, questions, history, derived-state inputs and the mutation receipt
  through the existing workspace transaction writer.
- R042: A successful receipt SHALL record the operation contract, analysis and
  plan fingerprints, normalized decision summary, exact target identity,
  semantic postconditions and internal physical postconditions without raw
  evidence. Physical project paths and per-file hashes SHALL NOT appear in
  public apply or mutation-status output.
- R043: Exact idempotent replay and `p2p mutation status` SHALL return the same
  typed operation identity and semantic postconditions through a safe public
  projection; changed plans or inputs SHALL produce
  `P2P_IDEMPOTENCY_CONFLICT`.
- R044: A classifier, analyzer, plan, validation, token, transaction or receipt
  failure SHALL leave the prior complete project state unchanged and SHALL
  provide stable recovery guidance.

### CLI, Agent And Consumer Handoff

- R045: Existing command paths for install/adopt/migrate preview and apply
  SHALL remain registered and SHALL emit the exact `p2p-cli/v1` operation IDs.
- R046: Text output SHALL summarize classification, apply eligibility,
  transition counts, required decisions, blockers and the next useful command;
  automation SHALL use JSON only.
- R047: Invalid plan, stale plan, decision required, mapping conflict,
  reconciliation conflict, impact limit and stale preview SHALL have stable
  error/blocker codes and documented exit classes.
- R048: Golden fixtures SHALL cover every operation-specific success shape and
  representative blocked/error shape and SHALL be validated against source and
  the built immutable wheel.
- R049: `docs/CLI-CONTRACT.md`, `docs/CLI-GUIDE.md`, the maintained primitive
  inventory and release notes SHALL define the exact impact and plan contracts,
  limits, retry rules and current-only compatibility posture.
- R050: Generic, Codex and Claude generated guidance SHALL teach the sequence:
  inspect classification, preview, satisfy exact decisions, re-preview, retain
  the new token and apply with one stable idempotency key.
- R051: The MCP capability catalog and MCP documentation SHALL continue to
  classify project vertical lifecycle mutation as owner-governed CLI-only and
  SHALL explain why no MCP mutation parity is added in this feature.
- R052: Released-wheel handoff evidence SHALL let WaveKit assert the exact
  engine version and impact contract, regenerate sanitized fixtures and test
  empty/populated classification plus preservation/mapping completeness without
  reading project files.

## Non-Functional Requirements

- N001: Analysis and serialization SHALL be deterministic for identical source
  state, target release, actor-independent semantics and normalized decisions.
- N002: Classification and transition analysis SHOULD be linear in the number
  of current and target evidence records and SHALL avoid repeated whole-project
  scans per item.
- N003: Public payload and receipt sizes SHALL remain below documented hard
  bounds; exceeding a completeness bound SHALL fail closed before apply.
- N004: Privacy tests SHALL prove that distinctive raw values and free-form
  owner text do not appear anywhere in JSON impact, warnings, blockers,
  persisted receipts, public receipt status or text output, and that internal
  project paths/per-file hashes appear only in the persisted internal
  postcondition record.
- N005: Domain analysis and materialization SHALL remain outside CLI and
  storage presentation layers and SHALL be reusable by current local adapters.
- N006: The implementation SHALL reuse current project-question reconciliation,
  exact vertical resolution, workspace transaction and receipt infrastructure
  instead of creating parallel authorities.
- N007: Source-tree and installed-wheel execution SHALL produce semantically
  identical contract fixtures and generated guidance.
- N008: Focused, public-contract, smoke/package and full-suite validation SHALL
  pass before release; a residual failure blocks the release rather than being
  documented as acceptable drift.

## Edge Cases And Errors

- Missing definition with adoption request: classify as empty and analyze the
  complete target candidate.
- Empty definition with migration request: return typed adoption-required
  diagnostic without writes.
- Non-empty field containing `0` or `false`: treat it as meaningful evidence;
  only `null`, empty text and empty collections are empty.
- Owner question evidence with otherwise empty definition: classify populated.
- Disabled or custom rubric with otherwise empty definition: classify
  populated.
- Existing unanswered generated questions and untouched default rubrics: do
  not classify populated.
- Same-ID field with incompatible target kind: require a decision or blocker;
  do not preserve solely by string identity.
- Two sources mapped to one target: reject unless a future accepted contract
  explicitly introduces a merge operation.
- Unknown or extra decision: reject; do not ignore it.
- Removed section containing fields, assumptions or blockers: require one
  disposition for every meaningful item.
- Question answer contract change that invalidates owner evidence: expose a
  structured reconciliation blocker/decision instead of leaking the answer or
  throwing an unclassified exception.
- Rubric semantic collision: expose a structured required decision.
- Previously orphaned evidence: retain and report it without duplicate orphan
  creation.
- Oversized transition: report deterministic totals and a limit blocker; do not
  issue an applicable token.
- Source mutation after analysis or preview: reject stale plan/token without
  writes.
- Exact apply retry after response loss: return `already_applied` with matching
  typed postconditions.
- Receipt/postcondition drift: fail with the existing controlled diagnostic and
  do not rerun the mutation blindly.
- Injected failure after candidates are staged: use existing transaction
  recovery and never expose a partially migrated project.

## Acceptance Criteria

- AC001: A project with no approved evidence family populated returns
  `classification=empty`, `adoption_eligible=true` and a complete typed adoption
  preview.
- AC002: Each evidence family independently changes classification to
  `populated`; adoption is blocked and migration is selected consistently.
- AC003: An incomplete migration preview lists every required decision and
  remains write-free and non-applicable.
- AC004: Supplying exact map and preserve-as-orphan decisions yields a complete
  applicable preview whose plan fingerprint changes when any decision changes.
- AC005: Apply preserves same-identity evidence and provenance, maps exact
  evidence once, retains explicit orphans once and loses no meaningful item.
- AC006: Rubric collisions and affected owner questions are fully represented
  by typed impact and no longer hidden behind a boolean or free-form exception.
- AC007: Section, field, question, rubric, lock and governed-artifact effects
  match post-apply inspection for representative fixtures.
- AC008: No public impact, error, text output, apply result or mutation-status
  result contains seeded secret values or internal paths, persisted receipts
  contain no seeded evidence values, and every collection obeys its documented
  bound.
- AC009: Changing project state, target content or one decision invalidates the
  prior analysis/preview and causes zero writes.
- AC010: A successful migration and its receipt commit atomically; injected
  failures leave the old state complete or enter the existing explicit
  transaction-recovery workflow.
- AC011: Exact replay, changed-input conflict, receipt lookup and postcondition
  drift preserve the current idempotency guarantees with typed result data.
- AC012: CLI success, blocker and error fixtures validate exact field sets,
  enums, operation IDs, exit classes and contract versions.
- AC013: Generated generic/Codex/Claude guidance and maintained CLI/MCP docs
  resolve to registered commands and accurately describe the CLI-only boundary.
- AC014: The built wheel reproduces empty/populated, incomplete-plan,
  complete-plan, apply and replay fixtures sufficient for WaveKit task `7.8`.
- AC015: Focused tests, public-contract tests, release artifact verification,
  installed-wheel smoke and the full suite pass.
