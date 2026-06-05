# Project Output Binding Method

This method binds a generated generic project export to local software
development specs.

It is a local repository method. It does not mutate P2P governance state and it
does not decide proposal outcomes.

## Purpose

Use this method when an agent or maintainer needs to turn a generated
`generic/project.md` plus `propose.md` into:

- updated `specs/steering/*` context;
- feature specs under `specs/features/<feature>/`;
- implementation tasks with evidence-based completion state;
- a gap report between the theoretical project definition and code in `src/`.

## Inputs

Required:

- latest generic export `project.md`;
- accompanying generic `propose.md`;
- existing `specs/steering/*`;
- existing `specs/features/*`;
- source tree under `src/`;
- tests under `tests/`;
- maintained docs under `docs/` when public behavior is involved.

Optional:

- CLI help output;
- focused test output;
- previous binding report.

## Core Rule

Never mark implementation work as complete from project output alone.

Completion requires direct evidence from at least one implementation surface:

- code in `src/`;
- tests in `tests/`;
- public docs in `docs/` for documented behavior;
- command output from the local CLI when behavior is externally visible.

## Phase 1 - Classify The Export

Read `project.md` and split content into four buckets:

1. **Steering Context**
   Stable project-wide facts: vision, domain, users, boundaries, architecture,
   invariants, operating model, non-goals.

2. **Feature Candidates**
   Distinct capabilities, usually traceable to accepted proposals or source
   sections.

3. **Current Export Focus**
   Material specific to the Change Set or export that produced the file. This
   must not be blindly promoted to global steering.

4. **Open Questions And Gaps**
   Missing information, `NEEDS CLARIFICATION`, pending proposals, risks, weak
   assumptions, or unsupported generated claims.

For `CHANGE-065/generic/project.md`, the executive summary and functional
requirements are focused on the Agent Integration Registry MVP, while the
vision, domain, workflows, decisions, and source traceability contain broader
project context.

## Phase 2 - Update Steering

Update steering only with stable, cross-feature information.

Mapping:

- `Vision`, stakeholders, product purpose -> `specs/steering/product.md`
- `Domain`, vocabulary, invariants -> `specs/steering/domain.md`
- architecture, component ownership, source layout -> `specs/steering/structure.md`
- runtime, entry points, test strategy -> `specs/steering/tech.md`

Do not put feature-specific requirements, task lists, or Change Set status in
steering.

## Phase 3 - Derive Feature Specs

Create or update `specs/features/<feature-name>/` for each feature candidate.

Each feature must contain:

- `requirements.md`
- `design.md`
- `tasks.md`

Recommended feature extraction sources:

- explicit feature sections in the export;
- accepted proposal IDs in `Source Traceability`;
- named capabilities in goals and workflows;
- current export focus when it represents a real implementation feature.

Do not create a feature for every proposal automatically. Merge proposals into
one feature when they describe the same implemented capability.

## Phase 4 - Normalize Requirements

Convert project statements into testable requirements.

Use normative format:

- `WHEN <trigger>, THE SYSTEM SHALL <observable behavior>.`
- `IF <condition>, THEN THE SYSTEM SHALL <observable behavior>.`
- `THE SYSTEM SHALL <always-true constraint>.`

Every requirement needs:

- stable ID, such as `R001`;
- source reference, such as `project.md#Source Traceability` or proposal ID;
- acceptance criterion;
- implementation status placeholder.

## Phase 5 - Design From Code Boundaries

Populate `design.md` from actual repository structure, not only from generated
project theory.

For each design decision, include:

- covered requirements;
- components involved;
- rationale;
- data contracts;
- error behavior;
- compatibility and migration concerns.

Design must identify where behavior belongs:

- CLI surface: `src/p2p_engine/cli.py`
- workspace behavior: `src/p2p_engine/storage/filesystem.py`
- MCP tools: `src/p2p_engine/mcp/tools.py`
- tests: `tests/test_cli.py`, `tests/test_mcp.py`
- docs: `docs/`

## Phase 6 - Bind Implementation Evidence

Create a binding table before marking task completion.

Use this evidence format:

```text
Requirement | Expected Behavior | Evidence | Status | Notes
R001        | ...               | src/...  | ...    | ...
```

Allowed statuses:

- `implemented`: code and tests prove the behavior.
- `partially_implemented`: some code exists but behavior is incomplete or tests
  are missing.
- `not_implemented`: no relevant implementation evidence found.
- `docs_only`: docs mention it but code/tests do not prove it.
- `obsolete`: export/project theory has been superseded locally.
- `unknown`: evidence search was insufficient.

Evidence should include file paths and line numbers when practical.

## Phase 7 - Populate Tasks

Tasks are derived from the gap between requirements/design and implementation
evidence.

Rules:

- Mark `- [x]` only when implementation evidence is present.
- Leave `- [ ]` for missing, partial, or unverified work.
- Each task must mention the requirement it satisfies.
- Each task must state the completion criterion.
- Each task should point to expected files or test surfaces.

Example:

```text
- [ ] T003: Implement R002 domain gating in CLI export handling; completion is
  focused CLI tests proving non-software projects reject OpenSpec and Spec Kit.
```

## Phase 8 - Produce A Binding Report

For significant sync work, create a report under:

```text
specs/bindings/<feature-or-export-id>.md
```

The report should include:

- input export paths;
- steering updates made or proposed;
- features created or updated;
- requirement-to-evidence matrix;
- tasks marked complete and why;
- gaps requiring implementation;
- questions for the owner.

## Phase 9 - Validate

Before finishing:

- verify specs are internally consistent;
- verify every checked task has evidence;
- run focused tests if code changed;
- report any tests not run.

## Anti-Patterns

- Copying the whole generated `project.md` into steering.
- Treating `propose.md` as requirements.
- Creating one feature per proposal without considering actual product
  capability boundaries.
- Marking tasks complete because the export says the capability exists.
- Reading `.p2p/outputs` as implementation state.
- Updating only `tasks.md` when requirements or design changed.
