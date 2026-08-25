# Requirements - Retire Structure Elements With Impact Resolution

## Scope

Allow authorized subjects to remove structural elements from the active project
structure without destroying history or leaving invalid references. Removal is
modeled as retirement, preceded by a complete typed impact preview and followed
by one atomic disposition-and-structure mutation.

## Origin

- Source: owner-approved governed permissive-removal decision.
- Target train: P2P Engine `0.5.0`.
- Depends on: `introduce-project-owned-structure` and
  `classify-project-memory-against-structure` plus
  `support-typed-authority-context-in-governed-mutations`.

## In Scope

- Retirement of canonical sections and supported nested structural elements.
- Complete bounded impact preview across governed memory families.
- Explicit dispositions for active references.
- Historical references retained against retired stable IDs.
- Readiness and memory-classification impact projection.
- Receipt-backed atomic apply, status, replay and recovery.
- Active and retired structure/history reads.

## Out Of Scope

- Physical purge as a normal user operation.
- Automatic semantic or fuzzy remapping.
- Full structure replacement, merge or restore.
- WaveKit dialogs and authorization policy.
- Destructive deletion of proposal, decision or evidence history.

## Public Surface And MCP Impact

- CLI impact: new preview/apply/status contracts for structure retirement.
- MCP impact: read preview plus capability- and consent-gated apply parity is
  required for standalone project agents; WaveKit continues to invoke CLI.
- Storage impact: lifecycle transition events and atomic cross-memory scope
  updates in workspace schema 4.
- Agent-facing behavior: agents must resolve every active blocker and must not
  interpret retirement as deletion.

## Functional Requirements

### Retirement Semantics

- R001: Removing a canonical structural element from the active structure SHALL
  change its lifecycle to `retired` rather than physically delete its identity.
- R002: Retired elements SHALL be excluded from active structure, readiness
  denominators and new active section assignment.
- R003: Retired stable IDs SHALL remain reserved and queryable in bounded
  history.
- R004: A canonical physical purge SHALL NOT be exposed by normal CLI or MCP
  project-structure workflows.
- R005: A draft-only element that has never entered canonical project state MAY
  be deleted by the caller's draft workflow without creating a retirement.

### Impact Preview

- R006: Retirement SHALL require a read-only preview bound to current structure
  revision, memory revision, typed authority context and exact target IDs.
- R007: Preview SHALL inspect proposals, formal questions, decisions, evidence,
  artifact instances, outputs and every other supported governed reference.
- R008: Impact collections SHALL distinguish historical references, active
  references, already-retired references and unknown or invalid references.
- R009: Preview SHALL report complete bounded totals and SHALL set
  `apply_allowed=false` when any material collection is truncated or unknown.
- R010: Preview SHALL report required disposition IDs and allowed actions by
  memory kind without exposing physical paths.
- R011: Preview SHALL report projected active criteria, readiness status/score
  where calculable and memory-classification count deltas.
- R012: Preview SHALL perform no persistent write.

### Dispositions

- R013: Historical references SHALL remain linked to the retired element unless
  an explicit supported historical migration is separately requested.
- R014: Active pending proposals MAY be reassigned to active sections, made
  project-global or moved to unassigned scope.
- R015: Active authoritative proposals SHALL be reassigned to active sections or
  made explicitly project-global before retirement applies.
- R016: Open formal questions SHALL be reassigned, made global where supported,
  or closed through an explicit typed disposition.
- R017: Active evidence and artifact instances SHALL be reassigned or archived
  according to their supported lifecycle; they SHALL NOT disappear silently.
- R018: A disposition target SHALL be validated against the same current
  structure snapshot and SHALL not target another retiring or retired element.
- R019: Unsupported active reference kinds SHALL block apply with a stable
  remediation code.

### Apply, Replay And Recovery

- R020: Apply SHALL require typed authority context, operation key, expected
  structure revision, expected memory revision, exact preview token and
  explicit confirmation.
- R021: Apply SHALL reject changed source state or a disposition plan that does
  not resolve every required decision.
- R022: Structure lifecycle, memory dispositions, event evidence and receipt
  SHALL commit in one atomic workspace transaction.
- R023: Successful apply SHALL advance structure revision once and memory
  revision according to the canonical mutation policy.
- R024: Exact retry SHALL return the original result; divergent retry SHALL fail
  without another mutation.
- R025: Lost response and interrupted apply SHALL be recoverable through
  mutation and workspace-transaction status.

### Read And Publication Behavior

- R026: Active structure reads SHALL omit retired elements by default and SHALL
  expose a bounded opt-in retired/history view.
- R027: Publications SHALL preserve historical context needed to explain
  decisions while distinguishing active from retired structure.
- R028: Retirement SHALL not automatically revoke, reject or rewrite a proposal
  decision.

### Governed Capability Contract

- R029: Retirement apply SHALL declare capability
  `project.structure.retire` and bind the exact authority context to both
  previews, disposition plan, apply, event and receipt.
- R030: P2P local policy SHALL retain standalone owner control; hosted policy
  MAY keep the capability root-only without that provider rule being encoded in
  the retirement service.

## Non-Functional Requirements

- N001: Impact analysis SHALL fail closed when reference completeness cannot be
  proven.
- N002: Preview and apply SHALL be deterministic for the same source snapshot.
- N003: Public impact collections SHALL be bounded and path-safe.
- N004: Apply SHALL use existing atomic transaction, lock and receipt services.
- N005: Reference analysis SHALL have bounded linear behavior over indexed
  project memory and avoid repeated full scans per element.

## Edge Cases And Errors

- Retirement of an unknown, already retired or duplicate target.
- Nested criterion or artifact targeted while its parent section also retires.
- Active proposal references multiple retiring and surviving sections.
- Historical accepted/revoked proposal on the retiring section.
- Open question with no supported global scope.
- Active artifact that cannot be archived.
- Truncated or stale reference index.
- Readiness becomes not configured after the last active criterion retires.
- Source changes after preview or response is lost after commit.

## Acceptance Criteria

- AC001: A referenced section can be retired after every active reference has a
  valid explicit disposition.
- AC002: Historical references remain readable against the retired stable ID.
- AC003: No retired criterion contributes to readiness and projected impact
  matches the post-apply read.
- AC004: Unassigned/reassignment counts match the post-apply classification
  snapshot.
- AC005: Truncated, unknown, stale or incomplete impact never yields an
  applicable token.
- AC006: Apply is atomic across structure, scopes, events and receipt.
- AC007: No public purge or silent fuzzy mapping path exists.
- AC008: CLI and MCP preview/apply expose equivalent domain semantics and safe
  replay behavior.
- AC009: Retirement apply requires `project.structure.retire` and rejects
  authority drift between preview, disposition confirmation and apply.
