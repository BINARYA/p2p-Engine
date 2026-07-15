# P2P Engine Operational Brief

## Current Position

P2P Engine is operating on runtime `0.2.0` with a compatible runtime contract
(`>=0.2.0,<0.3.0`) and workspace schema v1. The workspace reports
`layout_current`, semantic alignment, a valid `software_project` vertical and no
active migration lock or recovery transaction.

The repository contains 100 proposals. The committed project projection basis
is 95 proposals: 94 `accepted` and one `accepted_with_changes`. Two proposals
remain draft, two are superseded and one is deferred. There are 68 Change Sets;
`CHANGE-068` is `implementation_ready` and is the only active Change Set. Four
Work manifests exist and are terminal (`retired` or `cleaned`).

The workspace migration has completed M1 through M4. Runtime/schema alignment,
project definition, historical relation curation and the first selective
vertical-coverage batch are applied. M5 is rebuilding and comparing derived
state before the final migration gate.

## Product And Governance Shape

P2P Engine remains a local, Git-native, file-backed Python system. Canonical
project intent is held in governed Markdown and YAML under `.p2p`; registries,
project projections, decision context, assessments, software specs and
publication artifacts are derived views.

The CLI is the reference local write surface. MCP provides bounded read tools
and explicitly authorized write-safe operations. Owner authority, project role
policy and consent gates remain mandatory. Agents must not replace governed
writes with direct `.p2p` edits or make proposal, choice, Work, merge or
publication decisions for the owner.

## Project Definition And Evidence

The active software vertical has 19 required sections. Definition completeness
is 40/43 units (93.02%). Declared owner-confirmed proposal evidence covers 13/19
sections (68.42%); 390 heuristic matches are excluded from that numerator.

The first coverage batch contains 12 owner-confirmed proposals. The other 88
proposals remain intentionally legacy and unmapped. Six definition-complete
sections intentionally have no proposal evidence and must not be treated as
missing definition. Two operating assumptions still require validation; there
are no open project-definition questions.

The request-scoped decision-context index is partial but usable: it has 1,353
sources, 2,944 evidence records, 2,218 semantic records, 544 nodes and 667 valid
relations. Invalid, ambiguous and unsupported relation diagnostics are zero.
The only source diagnostics are two intentional authority/status divergences
for draft `PROP-063` and `PROP-098`. Bounded retrieval remains explainable and
reports truncation explicitly.

## Current Delivery And Publication Work

`CHANGE-068` implements the accepted Human Project Publication Pipeline from
`PROP-099`. Its P2P software spec is generated and current. The intended stages
remain separate: deterministic project export, publication packet preparation,
agent curation, validation, neutral PDF render and explicit owner review.

Existing publication outputs are stale relative to current governed sources.
No publication approval exists and none should be inferred from a generated,
curated, validated or rendered artifact. The owner review stage remains
missing by design.

## Derived-State Rebuild Status

The following layers have been reconciled during M5:

- registries are current at 100 proposals, 100 decisions, 68 changes, 2 choices,
  136 relations, 2,293 artifact records and 100 readiness records;
- project projections are current at 95 decision-map entries and 95 generated
  feature directories, with an explicit 291-path ownership manifest;
- decision context is current and request-scoped;
- readiness assessment, rubric maturity and project progress expose separate
  bases rather than one authoritative percentage;
- brief context and prompt are current;
- 11 software specs are generated and current, including `CHANGE-068`.

Operational brief import is complete. Managed next actions, visible export and
publication stages still need the remaining supported lifecycle steps. The
legacy `spec-refine.prompt.md` for `CHANGE-012` is preserved as an optional
prompt and is not part of the current software-spec refresh contract.

## Risks And Residual Work

- `PROP-063` and `PROP-098` remain drafts and require normal owner review; their
  pending authority is intentionally not normalized by migration.
- `CHANGE-068` remains active even though its generated spec and implementation
  surface exist; completion requires its own governed lifecycle decision.
- The 88 unmapped proposals and optional legacy artifacts must not be mistaken
  for current declared vertical evidence.
- Two project assumptions remain `to_validate`.
- Assessment and maturity artifacts still use explicit legacy content/mtime
  freshness fallback; the authoritative project-definition and evidence axes
  remain the project progress result.
- Publication curation, validation, rendering and owner review are separate
  stages. A later stage must not silently mark an earlier stale stage current.

## Recommended Next Actions

1. Refresh managed next actions with `p2p next refresh` and verify they no
   longer recommend already-completed projection work.
2. Refresh the visible project export with `p2p project export`.
3. Prepare the publication packet with `p2p project publish prepare`.
4. Run the project-curator import, publication validation and neutral render
   through their existing commands, while leaving owner review unapproved.
5. Complete M5 focused and full tests, baseline comparison, residual-state
   recording and final diff review.

Owner-controlled proposal, Change Set, Work and publication decisions remain
outside this brief. `.p2p` remains the authoritative project source of truth.
