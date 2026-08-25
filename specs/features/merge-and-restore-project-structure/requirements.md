# Requirements - Merge And Restore Project Structure

## Scope

Provide advanced, explicitly requested workflows for selectively importing
structural elements from an exact release and restoring a prior project
structure revision. This feature is intentionally deferred until replacement
and structure history have production-quality evidence.

## Origin

- Source: owner-approved future extension of project-structure control.
- Depends on: all project-owned structure, classification, retirement,
  readiness and replacement features plus
  `support-typed-authority-context-in-governed-mutations`.
- Delivery: post-0.5.0; not a release blocker for the structural core.

## In Scope

- Read-only comparison with an exact release.
- Selective section/element import through an explicit merge plan.
- Stable-ID collision resolution without fuzzy automatic mapping.
- Restore preview for an exact retained structure revision.
- Reuse of impact dispositions, readiness/classification projection, receipts
  and recovery.

## Out Of Scope

- Textual three-way merge.
- Automatic synchronization with a vertical release.
- Restore of deleted project memory or proposal decision history.
- Arbitrary edits to internal historical artifacts.
- WaveKit implementation in the initial 0.5.0 train.

## Public Surface And MCP Impact

- CLI impact: future advanced compare/merge/restore preview/apply commands.
- MCP impact: read-only merge comparison and retained-revision inspection ship
  with implementation; merge/restore apply remains explicitly deferred.
- Storage impact: new structure revisions and merge/restore events only.
- Agent-facing behavior: generated guidance must not advertise the feature
  before implementation evidence exists.

## Functional Requirements

- R001: Merge SHALL resolve one exact source release and one exact current
  project-structure snapshot.
- R002: Merge SHALL require an explicit list of imported structural IDs and
  target placement/order.
- R003: Compatible absent IDs MAY be imported directly; collisions SHALL require
  explicit keep-current, replace-with-impact or import-as-new-ID decisions.
- R004: Merge SHALL never infer semantic identity from titles or similarity.
- R005: Merge preview SHALL report dependency closure, nested elements,
  conflicts, active-memory impact, readiness impact and classification impact.
- R006: Restore SHALL name one retained project-structure revision and SHALL
  treat differences from current state as a normal governed transition.
- R007: Restore SHALL not rewind proposal, decision, evidence or audit history.
- R008: Merge and restore SHALL reuse complete disposition planning for active
  references and fail closed on unknown/truncated impact.
- R009: Apply SHALL require current revisions, exact plan, token, typed
  authority context, operation key and confirmation.
- R010: Apply SHALL atomically publish one new current structure revision, event
  and receipt rather than rewrite historical revisions.
- R011: Exact replay/status/recovery SHALL use the shared mutation contracts.
- R012: No operation SHALL subscribe the project to future release updates.
- R013: Merge apply SHALL declare `project.structure.merge`; restore apply SHALL
  declare `project.structure.restore`; each SHALL bind the exact typed authority
  context to preview, plan, apply, event and receipt.
- R014: Local policy SHALL preserve standalone owner control while hosted
  delegability remains external-provider policy and deferred MCP apply SHALL
  not imply that either capability is available.
- R015: MCP SHALL expose side-effect-free merge comparison and retained-revision
  inspection only and SHALL NOT expose merge or restore apply.

## Non-Functional Requirements

- N001: The feature SHALL reuse existing comparators, impact analyzers,
  validators and transaction services.
- N002: Public plans and impacts SHALL be bounded and path-free.
- N003: Historical revision retention requirements SHALL be configurable but
  explicit before restore is advertised.
- N004: Deferred status SHALL be visible in specs and agent capability output.

## Edge Cases And Errors

- Source dependency closure imports an unselected required element.
- Stable ID collision with incompatible nested schema.
- Restore target has been pruned by retention policy.
- Current active memory cannot be represented by restored structure.
- Concurrent change after preview.
- Merge plan is incomplete, cyclic or truncated.

## Acceptance Criteria

- AC001: Selective merge imports only selected elements plus required declared
  dependencies.
- AC002: ID collisions never resolve through fuzzy matching.
- AC003: Restore creates a new revision and preserves all project-memory history.
- AC004: Active references require explicit valid dispositions.
- AC005: Readiness/classification impact matches post-apply reads.
- AC006: Replay and recovery are safe.
- AC007: The feature remains unavailable in CLI/MCP until all required tests and
  retention decisions are complete.
- AC008: Once enabled, merge and restore require their distinct capabilities
  and reject authority drift between preview and apply.
- AC009: MCP comparison/inspection is byte-invariant and the MCP catalog contains
  no merge/restore apply tool.
