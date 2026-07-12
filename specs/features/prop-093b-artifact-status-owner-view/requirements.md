# PROP-093B Artifact Status And Owner View Requirements

## Status

`draft`

## Traceability

- P2P proposal: `PROP-093 - Agent Persistence Boundaries And Proposal Authoring Flow`
- Accepted slice: `093-B - Artifact Status And Owner View`
- Related local specs:
  - `specs/features/prop-093a-canonical-proposal-authoring/`
  - `specs/features/proposal-artifact-state-readiness/`

## Problem

Physical files inside proposal directories are not a reliable user interface for
understanding proposal completeness. Some artifacts are required, some are
optional, some are only applicable in specific contexts, and some may be
generated or imported later.

If users or agents infer completeness from the filesystem, they can reach the
wrong conclusion: proposals with fewer files may be valid, and proposals with
more files may still be incomplete.

P2P needs a deterministic logical artifact view that explains expected proposal
components without forcing every proposal directory to contain every possible
file.

## Goals

- Provide a stable logical artifact catalog for proposals.
- Make missing, optional, deferred, generated, imported, legacy, and
  not-applicable artifact states understandable.
- Give owners a complete proposal view before governance decisions.
- Keep default proposal display behavior stable while adding an explicit full
  view.
- Disambiguate structured owner questions, analytical open-question
  contributions, and legacy narrative question artifacts.
- Expose read-only MCP parity for artifact status and full proposal review.

## Non-Goals

- Do not reintroduce empty placeholder files for uniformity.
- Do not change readiness scoring semantics.
- Do not implement persistent-write action previews; that belongs to a later
  `PROP-093C` slice.
- Do not change init defaults or agent integration lifecycle.
- Do not solve software-specific specs lifecycle; that is handled by `PROP-094`.
- Do not create, accept, reject, or decide proposals from the owner view.

## Scope

In scope:

- logical proposal artifact catalog;
- artifact state rendering for CLI and MCP;
- owner-facing full proposal view;
- question-source grouping in the full view;
- lazy compatibility for legacy proposals;
- tests and docs for the difference between logical artifact status and
  physical files.

Out of scope:

- changing existing proposal IDs or directory names;
- modifying existing proposal content;
- remote collaboration or provider PR/MR behavior;
- generic repository document management.

## Requirements

### R001: Artifact status is logical and deterministic

P2P shall expose a deterministic artifact catalog for each proposal. The catalog
shall list standard logical artifact slots even when the backing file is absent.

The catalog shall not require every logical artifact to have a physical file.

### R002: Missing files are not automatically corruption

When an optional or conditionally applicable artifact is absent, P2P shall
report that state explicitly instead of treating the proposal as malformed.

Missing required artifacts may still be reported as problems.

### R003: Artifact status explains expectation and materialization

For each artifact slot, P2P shall report:

- artifact key;
- human-readable label;
- expectation, such as required, required when applicable, optional memory, or
  not expected;
- status, such as satisfied, missing, weak, deferred, not applicable, or
  absent legacy;
- materialization or provenance when inferable, such as canonical, generated,
  imported, legacy, or not materialized;
- source hint when useful, such as `proposal.md`, `contributions.yml`,
  `questions.yml`, a narrative artifact filename, or no backing source;
- provenance confidence when useful, such as explicit, inferred, or unknown;
- concise guidance for the next useful action when relevant.

The implementation may use existing enums where they fit and add a renderer or
view model for materialization/provenance where status alone is insufficient.
The implementation shall avoid duplicating existing expectation semantics in
status values when an existing expectation plus status pair can express the
state.

### R004: Legacy proposals derive artifact state lazily

Proposals created before this feature shall not require a migration before they
can be shown.

When explicit artifact state is missing, P2P shall derive a conservative view
from current proposal files and existing services.

### R005: Owner full view is explicit

P2P shall provide an explicit owner-facing full proposal view. The preferred CLI
surface is an additive flag such as:

```bash
p2p proposal show PROP-XXX --full
```

The default `p2p proposal show PROP-XXX` output shall remain stable unless a
small compatibility-safe clarification is needed.

### R006: Full view includes decision-relevant context

The full owner view shall include:

- proposal identity and status;
- core proposal sections;
- decision state;
- readiness summary when available;
- structured contributions;
- narrative/imported artifacts when present;
- logical artifact status summary;
- grouped questions or unresolved items;
- suggested next actions.

The view shall not make owner decisions.

### R011: Question sources are disambiguated

When the full view includes questions or unresolved items, P2P shall distinguish
at least these sources:

- structured owner questions from `questions.yml`;
- analytical open-question contributions from `contributions.yml`;
- legacy or imported narrative question artifacts such as `open-questions.md`.

No source shall overwrite or implicitly resolve another source.

### R007: MCP exposes read-only parity

MCP shall expose the logical artifact status and full proposal view as read-only
data.

This may be implemented by adding a `full` argument to an existing proposal show
tool or by adding a dedicated read-only tool.

MCP shall return structured JSON-compatible fields for the full view and
artifact catalog, including stable machine-facing values for expectation,
status, materialization/provenance, question groups, and next actions.

### R008: Views do not create files just to render output

Rendering artifact status or the owner full view shall not create, update, or
delete proposal files.

Tests shall prove this with file-list preservation and, for existing files,
content preservation or an equivalent non-mutation check.

### R009: Output is useful to agents without encouraging direct file edits

Guidance in the artifact catalog and full view shall point to P2P commands or
explicit write-safe MCP tools, not manual edits under `.p2p/`.

Displayed paths shall be presented as backing evidence or source hints, not as
edit targets.

### R010: Tests cover current, reduced, and legacy file footprints

Tests shall cover:

- a newly created proposal after `PROP-093A`;
- a legacy proposal with narrative files;
- a proposal with imported artifacts;
- absent optional artifacts;
- missing required artifacts where applicable.
- separate structured owner questions, open-question contributions, and legacy
  `open-questions.md` artifacts;
- artifact status and readiness diverging without either overriding the other;
- long narrative artifacts being summarized or clipped in owner-facing output.

## Public Surface Impact

### CLI

- Add explicit full proposal view surface.
- Preserve default proposal show behavior.
- Keep artifact status output deterministic.

### MCP

- Add or extend read-only proposal view/status tools.
- Preserve existing MCP write boundaries.
- Return structured data suitable for agent reasoning.

### Storage

- Prefer derived view models over migration.
- Do not materialize missing files during read operations.

## Compatibility

This slice is intended to be backward compatible. Existing proposal directories
with different file footprints remain valid. Newer reduced-footprint proposals
from `PROP-093A` should look complete or incomplete based on logical status, not
on file count.

## Risks

- A too-large full view can become noisy for owners and agents.
- Materialization/provenance fields may be partially inferable for legacy
  proposals.
- CLI and MCP outputs can diverge if they use separate render paths.
- Artifact status could duplicate readiness if boundaries are unclear.

## Acceptance Criteria

- `p2p proposal show PROP-XXX --full` or equivalent explicit CLI surface exists.
- Default proposal show remains compatible.
- Logical artifact status lists expected artifact slots even when files are
  absent.
- Optional absent artifacts are not reported as corruption.
- Full view includes proposal, decision, readiness, contribution, artifact, and
  next-action context.
- MCP exposes read-only parity for logical artifact status and full proposal
  view.
- Rendering the view does not mutate `.p2p/`.
- The full view separates structured owner questions, analytical open-question
  contributions, and legacy narrative question artifacts.
- MCP payloads expose structured fields and stable public values rather than
  CLI-formatted text only.
- Displayed file paths are documented as evidence/source hints, not direct edit
  targets.
- Focused tests cover reduced-footprint, legacy, imported, optional, and missing
  required artifact scenarios.
