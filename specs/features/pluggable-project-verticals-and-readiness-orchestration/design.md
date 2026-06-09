# Design - Pluggable Project Verticals And Readiness Orchestration

## Requirements Covered

- R001-R038
- N001-N010
- E001-E010

## Key Decisions

- D001: Add a dedicated project vertical domain service.
  Rationale: loading, validation, source precedence, project-local persistence,
  candidate generation, and review integration are cohesive domain behavior.
  CLI, MCP handlers, and `P2PWorkspace` should delegate to this service.

- D002: Model verticals as pure data resources.
  Rationale: PROP-085 explicitly excludes executable plugin code in the MVP.
  YAML/Markdown resources are inspectable, testable, versionable, and safe to
  override locally.

- D003: Treat `base_project` as a concrete required internal pack.
  Rationale: fallback behavior must be useful even when no specific vertical is
  selected. A conceptual fallback is too vague for readiness review.

- D004: Use explicit source precedence.
  Rationale: project-local customization must win over internal defaults while
  preserving deterministic behavior:
  project-local packs -> internal defaults -> future registry sources ->
  `base_project` fallback.

- D005: Add active vertical project state.
  Rationale: readiness review needs to know which vertical should define the
  project skeleton. This state must be managed through CLI/service write paths.

- D006: Add proposal-to-vertical traceability as structured proposal evidence.
  Rationale: verticals should not be static templates detached from governance.
  The project must show which proposals cover each vertical caposaldo and which
  vertical areas remain uncovered.

- D007: Keep project rubrics/maturity as the scoring foundation.
  Rationale: PROP-085 extends existing rubrics and maturity/readiness. It must
  not introduce a parallel maturity engine.

- D008: Keep candidate generation deterministic and non-governing.
  Rationale: `project vertical propose` should produce a candidate pack for owner
  review. It should not activate or persist governance-relevant state unless the
  owner runs an explicit add/select command.

- D009: Keep remote registry deferred behind loader boundaries.
  Rationale: REST registry behavior is out of scope, but the data model should
  keep pack identity, version, and source so a future registry can be added
  without changing project-local pack semantics.

## Components

- `src/p2p_engine/core/project_verticals.py`
  - Dataclasses/enums for vertical packs, sections, rubrics, questions,
    artifacts, profiles, modules, sources, validation issues, active vertical
    state, custom candidate results, and review summaries.

- `src/p2p_engine/services/project_verticals.py`
  - Owns internal/project-local loading, source precedence, schema validation,
    list/show/validate/propose/add/select behavior, active vertical state, and
    pack serialization helpers.

- `src/p2p_engine/services/project_readiness_review.py`
  - Builds project readiness review output from project context, maturity,
    rubrics, active vertical, proposal summaries, proposal coverage, decisions,
    and missing coverage.
  - May be a separate service or a focused helper used by project maturity
    services if implementation remains small. Do not bury review assembly in CLI
    output code.

- `src/p2p_engine/services/proposal_vertical_coverage.py`
  - Owns optional proposal coverage read/write/validation if coverage is stored
    as a dedicated proposal artifact.
  - If coverage is instead stored in an existing impact artifact, this service
    should still provide a typed boundary so review logic does not parse YAML
    ad hoc.

- `src/p2p_engine/services/project_maturity.py`
  - Continues to own project rubric and maturity computation.
  - Receives vertical-derived criteria only through explicit service calls or
    persisted rubric inputs.

- `src/p2p_engine/services/project_initialization.py`
  - Keeps `p2p init` deterministic.
  - May initialize empty/unresolved active vertical state when appropriate.
  - Must not run agent-like custom vertical interviews.

- `src/p2p_engine/services/agent_templates.py`
  - Adds project orchestrator guidance for uninitialized projects, missing
    capisaldi, custom vertical candidate flow, and project readiness review.

- `src/p2p_engine/storage/filesystem.py`
  - Adds `P2PWorkspace` facade delegation only. No new vertical domain logic
    should live here.

- `src/p2p_engine/cli_commands/project_verticals.py`
  - Registers `p2p project vertical ...` commands.
  - Handles Typer options and output formatting only.

- `src/p2p_engine/cli_commands/project_ops.py`
  - Registers the vertical sub-app and `p2p project readiness review` command
    wiring if this remains the project command module boundary.

- `src/p2p_engine/mcp/catalog/project.py`
  - Adds project vertical and project readiness review tool schemas.

- `src/p2p_engine/mcp/handlers/project.py`
  - Thin dispatch to workspace facade methods.

- `src/p2p_engine/mcp/registry.py`
  - Adds new MCP tool names.

- `src/p2p_engine/services/validation.py`
  - Validates active vertical state, project-local packs, and proposal coverage
    artifacts when present.

- `src/p2p_engine/services/visible_project_export.py`
  - Optional first-slice integration: include vertical coverage summary when
    available without breaking current exports.

## Data And Contracts

### Internal Resource Layout

Preferred internal resource root:

```text
src/p2p_engine/resources/verticals/
  base_project/
    vertical.yml
    sections/
    rubrics.yml
    artifacts.yml
    questions.yml
  <demo_vertical>/
    vertical.yml
    sections/
    rubrics.yml
    artifacts.yml
    questions.yml
    examples/
```

The exact directory name may change during implementation if packaging tests
show a better Hatch-compatible resource path, but resources must be importable
from installed wheels.

### Project-Local Layout

Preferred project-local state:

```text
.p2p/project/verticals/
  <vertical-id>/
    vertical.yml
    sections/
    rubrics.yml
    artifacts.yml
    questions.yml
.p2p/project/vertical.yml
```

`vertical.yml` stores active state:

```yaml
project_vertical:
  schema_version: 1
  active_vertical_id: social_impact_program_design
  active_source: project_local
  selected_at: "2026-06-09"
  selected_by: owner
  fallback_used: false
```

If no active vertical exists, service reads should return a normal unresolved or
fallback state instead of failing.

### Vertical Pack Schema

Minimum pack:

```yaml
vertical:
  schema_version: 1
  id: base_project
  name: Base Project
  version: 1.0.0
  description: Cross-domain project foundation.
  extends: null
  sections:
    - id: vision
      title: Vision
      purpose: Why the project exists and what change it should create.
      required: true
      priority: 10
  rubrics:
    - id: vision_clarity
      title: Vision clarity
      section_id: vision
      required: true
      keywords: [vision, purpose, change]
  questions:
    - id: vision_main
      section_id: vision
      priority: high
      question: What change should this project create?
      rationale: Needed to anchor project readiness.
  artifacts:
    - id: project_brief
      title: Project brief
      section_ids: [vision, objective]
      required: true
```

The service may support split files under `sections/` for maintainability, but
the loaded contract should be normalized into one typed model.

### Custom Vertical Candidate

Candidate output should be structured and importable:

```yaml
vertical_candidate:
  schema_version: 1
  source_idea: "progettare la scatola perfetta"
  candidate:
    id: packaging_or_physical_product_design
    name: Packaging Or Physical Product Design
    extends: base_project
    sections: []
    rubrics: []
    questions: []
    artifacts: []
  rationale:
    base_project_sections_reused: []
    vertical_specific_additions: []
```

### Proposal Coverage Artifact

Preferred proposal-local artifact:

```yaml
vertical_coverage:
  schema_version: 1
  proposal_id: PROP-XXX
  vertical_id: social_impact_program_design
  sections:
    - id: theory_of_change
      relevance: direct
      source: declared
      rationale: Defines how initiatives create measurable impact.
```

Allowed relevance values:

- `direct`
- `indirect`
- `context`
- `unknown`

### Project Review Summary

Review output should be typed before rendering:

```yaml
project_readiness_review:
  active_vertical_id: social_impact_program_design
  vertical_source: project_local
  sections:
    - id: social_impact_vision
      title: Social Impact Vision
      status: covered
      proposals: [PROP-101]
      accepted_decisions: []
      gaps: []
      risks: []
      questions: []
    - id: measurement_and_reporting
      title: Measurement And Reporting
      status: missing
      proposals: []
      gaps: [missing_proposal_coverage]
      questions:
        - Which outcome metrics will prove real impact?
  unmapped_proposals:
    - PROP-110
```

Allowed section coverage statuses:

- `covered`
- `partial`
- `missing`
- `not_applicable`

## CLI Surface

Target commands:

```bash
p2p project vertical list
p2p project vertical show <vertical-id>
p2p project vertical validate <path-or-id>
p2p project vertical propose "<project idea>"
p2p project vertical add <path>
p2p project vertical select <vertical-id>
p2p project readiness review
```

Optional flags to evaluate during implementation:

```bash
p2p project vertical list --include-internal --include-project-local
p2p project vertical add <path> --activate
p2p project readiness review --vertical <vertical-id>
p2p project readiness review --format text|yaml
```

Avoid adding network/registry flags in the first slice.

## MCP Surface

Target MCP tools:

- `p2p_project_vertical_list`
- `p2p_project_vertical_show`
- `p2p_project_vertical_validate`
- `p2p_project_vertical_propose`
- `p2p_project_vertical_add`
- `p2p_project_vertical_select`
- `p2p_project_readiness_review`

Tool descriptions must state read/write behavior. Add/select are write-safe
project setup tools, not governance decision tools.

## Project Readiness Review Flow

1. Read project context and current project domain/rubrics/maturity.
2. Load active vertical state.
3. If active vertical is missing, load `base_project` fallback and report the
   fallback as guidance.
4. Load internal and project-local vertical definitions.
5. Validate active vertical.
6. Read proposal list/summaries and accepted decisions through existing services.
7. Read optional proposal vertical coverage artifacts.
8. For each active vertical section:
   - collect mapped proposals;
   - collect accepted decisions if available;
   - compute coverage status;
   - list missing artifacts/questions/rubrics;
   - generate focused project-definition questions.
9. Report unmapped proposals.
10. Emit suggested next commands.

## Custom Candidate Flow

`p2p project vertical propose "<idea>"` should:

1. start from `base_project`;
2. normalize a candidate ID;
3. propose section IDs/titles/purposes;
4. propose minimal rubrics;
5. propose blocking questions;
6. propose expected artifacts;
7. explain what is inherited from `base_project`;
8. render the candidate in a format that can be saved and then passed to
   `p2p project vertical add`.

This command should not activate the candidate. Activation requires
`p2p project vertical select` or `p2p project vertical add --activate`.

## Agent Guidance Contract

Generated instructions should tell agents:

- inspect project vertical/readiness state before deep proposal work;
- if the project is uninitialized or lacks capisaldi, prioritize project
  definition work;
- use `p2p project vertical list/show` to inspect available verticals;
- use `p2p project vertical propose` when no suitable vertical exists;
- ask the owner to confirm or modify a custom vertical candidate;
- use `p2p project vertical add` and `select` only after owner confirmation;
- run `p2p project readiness review` to identify missing vertical coverage;
- map proposals to vertical sections when discussing proposal impact;
- avoid making owner governance decisions.

## Error Handling

- Missing active vertical: report fallback to `base_project`.
- Unknown vertical ID: suggest `p2p project vertical list`.
- Invalid pack path: report missing file/path and expected layout.
- Invalid schema: report field path and accepted values.
- Unknown section in proposal coverage: report unmapped/invalid coverage.
- Invalid active state: report recovery command to select a valid vertical.
- Package resource load failure: report installation/build diagnostic.
- Review truncation: report counts and command/flag for full output if added.

## Migration And Compatibility

- Existing projects with only `.p2p/project/domain.yml` and `rubrics.yml` remain
  valid.
- Missing `.p2p/project/vertical.yml` is not an error.
- Project maturity commands keep existing behavior.
- `p2p init` remains deterministic and does not run agent interviews.
- Existing proposal readiness and proposal question behavior remains unchanged.
- Existing visible project exports remain valid; vertical summaries are additive.

## Testing Strategy

- Unit tests for pack schema validation and loader source precedence.
- Service tests for active state, project-local add/select, and candidate
  generation.
- CLI tests for each new command.
- MCP tests for tool schema and handler dispatch.
- Validation tests for malformed project-local packs and proposal coverage.
- Agent-template tests for project orchestrator guidance.
- Review service tests for coverage statuses, unmapped proposals, fallback, and
  question generation.
- Packaging/build test or wheel inspection for internal resources.
- Regression tests for existing project rubrics, maturity, init, export, and
  proposal readiness behavior.

## Out Of Scope Technical Notes

- Do not implement REST registry calls in this feature.
- Do not support executable plugin hooks.
- Do not make `p2p init` perform agent-like interviews.
- Do not mark implementation tasks complete from these specs alone.
