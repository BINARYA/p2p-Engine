# P2P Engine Operational Brief

## Current Position

P2P Engine is operating with runtime `0.4.1`, a compatible runtime contract
(`>=0.4.0,<0.5.0`) and workspace schema v3. The workspace reports the current
layout, semantic alignment, a valid `software_project` vertical and no active
migration lock or recovery transaction. A repeated migration plan to v3 is a
read-only no-op.

The repository contains 102 proposals. The current project projection basis is
97 active committed proposals: 96 `accepted` and one
`accepted_with_changes`. Two proposals remain draft, one is deferred, one is
historically `split` and one is historically `superseded`. There are 70 Change
Sets: 68 are completed, while `CHANGE-068` and `CHANGE-069` remain
`implementation_ready`. Four Work manifests exist and are terminal (`retired`
or `cleaned`).

The v2 to v3 migration completed through transaction
`migration-6fc36d34399ec5c9`. It introduced append-only proposal decision
ledgers without rewriting dependent Change Sets, Work, specs, vertical evidence
or publication state. Six residual legacy authorities were reviewed by the
owner. The final distribution has no `unknown_legacy` proposal authority.

## Product And Governance Shape

P2P Engine remains a local, Git-native, file-backed Python system. Canonical
project intent is held in governed Markdown and YAML under `.p2p`; registries,
project projections, decision context, assessments, software specs and
publication artifacts are derived views.

The CLI is the reference local write surface. MCP provides bounded read tools
and explicitly authorized write-safe operations. Owner authority, project role
policy and consent gates remain mandatory. Agents must not replace governed
writes with direct `.p2p` edits or make proposal, choice, Change Set, Work,
merge, project-definition or publication decisions for the owner.

Proposal decisions are append-only governance events in schema v3. A proposal
that was never active may be rejected. A previously accepted proposal must be
revoked, superseded, split or merged through a typed event; its accepted history
must not be deleted or rewritten. Decision events report dependent impacts but
do not mutate those dependents automatically.

## Project Definition And Readiness

The active `software_project` vertical has 19 required sections. Definition
completeness remains 40/43 units (93.02%). Declared owner-confirmed proposal
evidence covers 13/19 sections (68.42%). The 433 heuristic matches remain
suggestions and are excluded from the declared-evidence numerator.

Three required sections are incomplete: `assumptions`, `decisions` and
`risks_alternatives_decisions`. Assumptions `A001` and `A002` still require
owner validation. One applicable owner question,
`PRQ-7070e7a631b1df44`, remains `to_answer` for
`risks_alternatives_decisions`; it has no answer or applied definition patch.
These are owner-input gaps, not migration defects.

The deterministic project assessment is 76/100 (`needs_review`, high
confidence), while rubric maturity remains 100/100 (`well_defined`). These
figures have different bases and must not be collapsed into one authoritative
readiness percentage.

## Decision Context And Derived State

The request-scoped decision-context index is complete and has no diagnostics.
The latest measured build contains 1,486 sources, 3,249 evidence records, 2,495
semantic records, 716 nodes and 1,019 valid relations.

Registries are current at 102 proposals, 102 decisions, 70 Change Sets, two
choices, 140 relations, 2,459 artifact records and 102 readiness records.
Project projections are current for the 97 active committed proposals.
Historical `PROP-007` is recorded as a split into `PROP-017` and `PROP-025`;
historical `PROP-008` is recorded as superseded by `PROP-091`. Both remain
ever-active but are excluded from the active projection basis.

Assessment, maturity, project brief context and managed next actions have been
rebuilt after migration and final `CHANGE-070` completion. There are 17
generated next actions and none targets completed `CHANGE-070`.

All 13 generated software specs are now semantically `current`. The 12 legacy
specs were refreshed individually only after a read-only comparison proved
that every non-provenance artifact was byte-identical to the current
deterministic candidate, every decision binding was active and every lifecycle
preflight was clear. The refreshes added schema-v3 decision bindings,
fingerprints and output digests without changing specification content or
Change Set state. The optional `CHANGE-012` refinement prompt was preserved.

## Delivery And Publication

`CHANGE-068` implements the Human Project Publication Pipeline from
`PROP-099`. `CHANGE-069` implements the Project Readiness Convergence Workflow
from `PROP-101`. `CHANGE-070` implements the Proposal Decision Revision and
Revocation Lifecycle from `PROP-102`; after technical review, the owner
confirmed its governed transitions from `in_progress` through `in_review` to
`completed` on 2026-07-20. The two remaining Change Set lifecycle states remain
separate from source implementation evidence and require normal
owner-controlled decisions.

The local source includes request-scoped freshness reuse and next-action
freshness corrections discovered during repository alignment. They prevent
decision remediations and project assessment from rebuilding the same snapshot
repeatedly, and prevent append-only next-action audit history from making a
fresh action set appear stale. Focused, public and full tests are clean.

The visible project export and downstream technical publication stages have
been rebuilt after final lifecycle and software-spec provenance alignment.
Publication review remains owner-controlled and no publication approval may be
inferred from preparation, curation, validation or rendering.

## Risks And Residual Work

- `PROP-063` and `PROP-098` remain drafts and require normal owner review.
- `CHANGE-068` and `CHANGE-069` remain `implementation_ready`.
- The unresolved project question and two assumptions remain owner input.
- Derived freshness is computationally expensive on this repository. Snapshot
  reuse removes repeated scans within one request, but a full graph build still
  needs final performance evidence.
- Publication curation, validation, rendering and owner review are separate
  stages. A later stage must not silently approve publication.

## Recommended Next Actions

1. Resolve or defer the remaining project question and validate assumptions
   `A001` and `A002` through the governed readiness workflow.
2. Review draft `PROP-063` and `PROP-098` without inferring owner decisions.
3. Complete or deliberately defer the owner-controlled lifecycle decisions for
   `CHANGE-068` and `CHANGE-069`.
4. Review the rendered publication separately; keep
   `approved_for_publication: false` until the owner explicitly approves it.
5. Measure full freshness rebuild cost before selecting any persistent-cache
   optimization.

Owner-controlled proposal, Change Set, Work, project-definition and publication
decisions remain outside this brief. `.p2p` remains the authoritative project
source of truth.
