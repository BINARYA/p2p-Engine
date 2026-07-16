# P2P Engine Operational Brief

## Current Position

P2P Engine is operating on the published runtime `0.3.1` with the compatible
runtime contract `>=0.3.0,<0.4.0` and workspace schema v2. The workspace reports
the current layout, semantic alignment, a valid `software_project` vertical and
no active migration lock or recovery transaction.

The repository contains 101 proposals. The committed project projection basis
is 96 proposals: 95 `accepted` and one `accepted_with_changes`. Two proposals
remain draft, two are superseded and one is deferred. There are 69 Change Sets:
67 are completed, while `CHANGE-068` and `CHANGE-069` are
`implementation_ready`. Four Work manifests exist and are terminal (`retired`
or `cleaned`).

The schema v1 to v2 migration completed successfully through transaction
`migration-cb645638ac307b25`. The applied plan preserved 179 unknown legacy
artifacts, created the canonical project-question store and updated the schema
contract without changing the project definition. A repeated plan and apply are
no-ops, and runtime, schema, recovery and validation checks are clean.

The selected artifact-alignment pass is complete. Canonical sources,
registries, projections, decision context, assessment, maturity, operational
brief and publication outputs have been evaluated through their owning
contracts. Final focused, public and full test gates are clean.

## Product And Governance Shape

P2P Engine remains a local, Git-native, file-backed Python system. Canonical
project intent is held in governed Markdown and YAML under `.p2p`; registries,
project projections, decision context, assessments, software specs and
publication artifacts are derived views.

The CLI is the reference local write surface. MCP provides bounded read tools
and explicitly authorized write-safe operations. Owner authority, project role
policy and consent gates remain mandatory. Agents must not replace governed
writes with direct `.p2p` edits or make proposal, choice, Work, merge,
project-definition or publication decisions for the owner.

## Project Definition And Readiness

The active `software_project` vertical has 19 required sections. Definition
completeness remains 40/43 units (93.02%). Declared owner-confirmed proposal
evidence covers 13/19 sections (68.42%). Heuristic matches remain suggestions
and are excluded from the declared-evidence numerator.

Three required sections are incomplete: `assumptions`, `decisions` and
`risks_alternatives_decisions`. Assumptions `A001` and `A002` still require
owner validation. Schema v2 persists one applicable owner question,
`PRQ-7070e7a631b1df44`, for `risks_alternatives_decisions`. It is unanswered and
has not produced a candidate patch. The migration correctly recorded
`no_safe_question` for `assumptions` and `decisions` rather than inventing owner
input.

The first vertical-coverage batch contains 12 owner-confirmed proposals. The
other 88 proposals remain intentionally legacy and unmapped. Six
definition-complete sections intentionally have no declared proposal evidence;
that optional evidence gap must not be treated as missing definition.

## Decision Context And Derived State

The request-scoped decision-context index is partial but usable. The current
full diagnostic build has 1,369 sources, 3,187 evidence records, 2,327 semantic
records, 588 nodes and 800 valid relations. There are no fatal, invalid,
ambiguous or unsupported relation diagnostics. The two source diagnostics are
the intentional authority/status divergences for draft `PROP-063` and
`PROP-098`. The new unanswered project question is indexed as inactive system
state, not as an accepted decision.

Registries are current at 101 proposals, 101 decisions, 69 changes, two
choices, 138 relations, 2,325 artifact records and 101 readiness records.
Project projections are current at 96 decision-map entries and 96 generated
feature directories. Readiness assessment, rubric maturity, brief context and
brief prompt have been rebuilt after migration.

All 12 generated software specs are byte-equivalent to fresh isolated
candidates, including the active `CHANGE-068` and `CHANGE-069` specs. The
aggregate software-spec freshness node still reports a legacy mtime fallback;
this is a known diagnostic limitation, not evidence of a differing required
spec file. The optional legacy `spec-refine.prompt.md` for `CHANGE-012` remains
outside the current refresh contract.

## Delivery And Publication

`CHANGE-068` implements the accepted Human Project Publication Pipeline from
`PROP-099`. `CHANGE-069` implements the accepted Project Readiness Convergence
Workflow from `PROP-101`. Both are implementation-ready but still require their
normal owner-controlled Change Set lifecycle decisions.

The visible export, publication packet, curated Markdown, validation and PDF
have been regenerated and are current under the publication manifest. No
publication approval exists. Generated, curated, validated or rendered output
must not imply approval; the owner review stage remains intentionally missing
and `approved_for_publication` remains false.

## Risks And Residual Work

- `PROP-063` and `PROP-098` remain drafts; migration must not normalize their
  pending authority.
- The owner question `PRQ-7070e7a631b1df44` and assumptions `A001` and `A002`
  remain unresolved owner input, not migration defects.
- The 88 unmapped proposals and optional legacy artifacts must not be mistaken
  for current declared vertical evidence.
- Assessment, maturity and aggregate software-spec freshness retain explicit
  legacy fallback diagnostics; semantic and candidate comparisons remain the
  controlling evidence for this alignment pass.
- The global freshness graph propagates aggregate software-spec mtime staleness
  to otherwise current downstream outputs. Per-spec candidate comparison and
  the publication manifest are the controlling evidence; historical specs were
  not rewritten only to update mtimes.
- The generated next-action fallback currently shows `CHANGE-068` but omits the
  second active Change Set, `CHANGE-069`; readiness gap actions remain present
  and correctly bounded.
- Publication curation, validation, rendering and owner review are separate
  stages. A later stage must not silently approve publication.

## Recommended Next Actions

1. Present the unresolved project question and assumptions to the owner only
   through the governed readiness workflow; do not infer an answer.
2. Review the normal owner-controlled lifecycle state of `CHANGE-068` and
   `CHANGE-069` separately from implementation evidence.
3. Decide separately whether to address the aggregate software-spec freshness
   diagnostic and the missing `CHANGE-069` fallback action in a future change.
4. Perform publication review only through the explicit owner command when the
   owner intends to approve or reject the current draft.
5. Review and publish the repository migration/alignment diff through the
   normal owner-controlled Git handoff.

Owner-controlled proposal, Change Set, Work, project-definition and publication
decisions remain outside this brief. `.p2p` remains the authoritative project
source of truth.
