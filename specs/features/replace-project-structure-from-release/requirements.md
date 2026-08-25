# Requirements - Replace Project Structure From Release

## Scope

Replace the active project structure with a detached copy of one exact vertical
release through a governed compare, impact-resolution and atomic apply workflow.
Replacement never subscribes the project to future vertical updates.

## Origin

- Source: owner-approved advanced structure-change workflow.
- Depends on: project-owned structure, explicit memory scope, retirement impact
  resolution, structure-based readiness and
  `support-typed-authority-context-in-governed-mutations`.
- Target train: P2P Engine `0.5.0`, implemented only after the P1-P5 structural
  core passes its focused stability checkpoint and before the final 0.5.0
  convergence/tag gate.

## In Scope

- Exact release resolution and normalized target structure.
- Structural comparison and reuse of typed retirement/reference impact.
- Explicit dispositions for active project memory.
- Atomic replacement, origin event and receipt.
- Post-apply readiness and classification identity.
- CLI and documented agent workflow.

## Out Of Scope

- Automatic updates when a source release changes.
- Selective merge of individual sections.
- Restore of an arbitrary historical revision.
- Remote registry authentication changes.
- WaveKit catalog selection and confirmation UI.

## Public Surface And MCP Impact

- CLI impact: additive preview/apply/status replacement commands.
- MCP impact: exact-release inspection and comparison preview are read-only;
  replacement apply remains CLI-only in this feature.
- Storage impact: one new structure revision, origin/replacement event, memory
  dispositions and receipt.
- Agent-facing behavior: replacement must be described as a detached copy and
  never as following or upgrading a vertical.

## Functional Requirements

- R001: Replacement SHALL resolve one exact validated release and checksum
  before comparison.
- R002: The target effective pack SHALL be normalized into a candidate
  project-owned structure without changing the source release.
- R003: Preview SHALL compare stable IDs and semantic contracts and SHALL not
  infer identity from labels or text similarity.
- R004: Preview SHALL classify preserved, added, retired and conflicting
  structural elements.
- R005: Preview SHALL reuse the complete governed-reference impact model and
  report required active-memory dispositions.
- R006: Preview SHALL expose projected readiness and memory-classification
  impact as separate objects.
- R007: Truncated, unknown or unresolved impact SHALL not yield an apply token.
- R008: Apply SHALL require typed authority context, operation key, exact target
  identity, expected structure and memory revisions, complete plan, current
  token and explicit confirmation.
- R009: Apply SHALL atomically publish the detached target structure, supported
  dispositions, replacement event and receipt.
- R010: Replacement SHALL preserve prior structure revisions and retired
  element identity needed for historical references.
- R011: Successful replacement SHALL set a new current structure origin event
  without rewriting the immutable initial-origin history.
- R012: Future target release publication SHALL not modify the project.
- R013: Exact replay and mutation status SHALL recover lost responses without a
  second replacement.
- R014: A changed target artifact, source project or authority context SHALL
  invalidate apply.
- R015: Post-apply validation SHALL prove structure checksum, active IDs,
  readiness source identity and classification source identity.
- R016: Replacement apply SHALL declare capability
  `project.structure.replace` and bind the exact typed authority context to
  comparison preview, disposition preview, apply, event and receipt.
- R017: Local policy SHALL preserve standalone owner control while hosted
  delegability remains external-provider policy and SHALL NOT be inferred from
  access to the target release.
- R018: MCP SHALL expose exact-release inspection and read-only replacement
  comparison only; it SHALL NOT expose replacement apply or acquire a missing
  release implicitly.

## Non-Functional Requirements

- N001: Replacement SHALL reuse current pack validation, retirement impact,
  atomic transaction and receipt services.
- N002: Public impact SHALL be bounded, deterministic and path-free.
- N003: No fuzzy matching or silent orphaning SHALL occur.
- N004: The workflow SHALL operate with bundled, local or cached exact releases
  and remain independent from a mandatory registry.

## Edge Cases And Errors

- Target equals current origin but current structure has diverged.
- Target has colliding IDs with incompatible semantics.
- Target removes all active criteria or sections.
- Active memory requires unsupported disposition.
- Target changes between preview and apply.
- Current structure or memory changes after preview.
- Interrupted transaction or lost response.
- Private/cached release unavailable in standalone mode.

## Acceptance Criteria

- AC001: Exact replacement produces one detached structure revision and one
  replacement event.
- AC002: No future source release change affects the project.
- AC003: Every active reference is preserved through an explicit valid
  disposition or apply remains blocked.
- AC004: Historical structure and references remain interpretable.
- AC005: Project readiness and classification after apply match previewed source
  identities and semantics.
- AC006: Stale, truncated and fuzzy-only plans never apply.
- AC007: Replay and recovery do not duplicate the replacement.
- AC008: The workflow works offline with an exact local pack.
- AC009: Replacement requires `project.structure.replace`; target-release
  access and simple edit authority do not satisfy that capability.
- AC010: MCP inspection/comparison causes no project, cache or receipt mutation
  and replacement apply is absent from the MCP catalog.
