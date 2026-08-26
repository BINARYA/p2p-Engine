# Inventory - Project Memory And Structural References

## Purpose

This inventory records the schema-4 memory families reviewed before replacing
proposal vertical coverage with explicit project-memory scope. Canonical state,
derived projections and inherited references are kept distinct.

## Applicability Matrix

| Memory family | Canonical source | Structural behavior in this feature |
| --- | --- | --- |
| Proposal | `proposal.md` plus `decision-events.yml` | Full independent `sections`, `project_global` or `unassigned` scope. Active proposals may target multiple active sections. |
| Proposal decision | `decision-events.yml` | Inherits the proposal scope at decision time. Authority-creating events require an explicit valid scope; historical events retain their explanation through the proposal scope ledger. |
| Project formal question | `project/questions.yml` | Existing section reference is classified against `ProjectStructure`. Active references to retired or unknown sections require reassignment. No second scope artifact is created. |
| Proposal-local question | proposal `questions.yml` | Inherits proposal identity and scope. It is not counted as an independent project-memory object. |
| Proposal contribution | `contributions.yml` | Inherits proposal identity and scope. It is not independently classifiable. |
| Proposal evidence and uncertainty files | proposal-owned Markdown/YAML | Inherit proposal identity and scope. They remain publication evidence but do not create independent classification debt. |
| Proposal artifact state | `artifact-state.yml` and proposal artifacts | Inherits proposal identity and scope. Expected artifact declarations in `ProjectStructure` are structure, not produced memory. |
| Project definition | `project/definition.yml` | Structured project state consumed by readiness; not a classifiable memory object in this feature. |
| Choice, Change Set and Work | their existing canonical files | Explicitly unchanged. They are process/governance families and are not silently reclassified as structural project memory. |
| Publication | `project/publications/**` | Derived output. It preserves the classification snapshot and scope kind of included proposal evidence but is not itself classification input. |

## Existing Contract Being Replaced

Proposal structural mapping currently uses:

```text
.p2p/proposals/<proposal>/vertical-coverage.yml
```

That artifact binds a proposal to a selected vertical release and treats
missing coverage as ambiguous. The new canonical artifact is:

```text
.p2p/proposals/<proposal>/memory-scope.yml
.p2p/proposals/<proposal>/memory-scope-events.yml
```

It binds the proposal to the project-owned structure and distinguishes absence
of completed organization (`unassigned`) from deliberate project-wide scope
(`project_global`). The schema-4 runtime does not derive global scope from a
missing file or an empty section list.

## Active And Historical Policy

- `undecided`, `deferred`, `accepted` and `accepted_with_changes` proposals are
  active classifiable memory.
- `withdrawn`, `rejected`, `revoked`, `superseded`, `split` and
  `merged_into_other` proposals remain readable history and do not create
  current classification debt.
- Active project questions are section-classified. Applied, retired and
  superseded questions are historical.
- An active object that references a retired or unknown section is
  `requires_reassignment`; reads never rewrite it.

## Revision Inputs

The project-memory revision is an opaque SHA-256 identity over bounded
classifiable canonical inputs: project questions and each proposal's narrative,
decision ledger, scope and scope-event ledger. Receipts and derived projections
are excluded. Scope writes additionally bind the exact project-structure
revision and checksum.

## Deliberate Exclusions

- No AI or heuristic classifier becomes authoritative.
- No classification count changes readiness.
- No generic free-form tag model is introduced.
- No WaveKit role, grant or persistence concept enters P2P Engine.
- Section retirement and disposition remain owned by the next feature.
