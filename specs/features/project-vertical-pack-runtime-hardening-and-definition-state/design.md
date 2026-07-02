# Design - Project Vertical Pack Runtime Hardening And Definition State

## Requirements Covered

- R001-R070
- N001-N012
- E001-E018

## Current Baseline

The MVP vertical runtime already exists and must remain the baseline:

- `src/p2p_engine/core/project_verticals.py` defines the current typed vertical
  records.
- `src/p2p_engine/services/project_verticals.py` owns loading, validation,
  project-local add/select, active vertical fallback, proposal vertical coverage,
  and project readiness review.
- `src/p2p_engine/cli_commands/project_ops.py` owns the current `p2p project
  vertical ...` and `p2p project readiness review` CLI wiring.
- `src/p2p_engine/mcp/catalog/project.py` and
  `src/p2p_engine/mcp/handlers/project.py` expose MCP parity.
- `P2PWorkspace` in `src/p2p_engine/storage/filesystem.py` is the compatibility
  facade and should continue to delegate.
- `src/p2p_engine/services/project_initialization.py` owns deterministic init.
- `src/p2p_engine/services/project_maturity.py` owns rubrics and maturity.
- `src/p2p_engine/services/validation.py` owns semantic validation aggregation.
- `src/p2p_engine/foundation/files.py` provides reusable YAML and atomic write
  helpers.

The production hardening should extend these boundaries. It must not introduce
a second vertical runtime or move behavior into `cli.py`, `filesystem.py`, or
`mcp/tools.py`.

## Key Decisions

- D001: Implement this as a follow-up feature, not by reopening the completed
  PROP-085 MVP spec.
  Rationale: the existing MVP has implementation evidence and completed tasks.
  Hardening introduces new persisted contracts and should be tracked separately.

- D002: Keep `ProjectVerticalService` as the main application boundary, but
  split focused helpers when responsibilities become large.
  Rationale: the service already owns the vertical domain. Pack parsing,
  resolving, locking, definition-state updates, and safety validation are
  related but large enough to justify helper modules or collaborators.

- D003: Add richer core dataclasses before changing behavior.
  Rationale: lockfiles, multi-file packs, definition state, and JSON surfaces
  need stable typed contracts so CLI/MCP do not parse dictionaries directly.

- D004: Preserve `P2PWorkspace` as a facade.
  Rationale: CLI, MCP, tests, and callers already use facade methods. New
  methods may be added as delegation, but domain logic stays in services.

- D005: Preserve the existing CLI namespace.
  Rationale: PROP-090 explicitly keeps `p2p project vertical ...` as the
  production path. A top-level alias is out of scope.

- D006: Use the existing `--format json` style as the preferred CLI JSON
  convention, while allowing `--json` aliases only where they can be added
  cleanly and tested.
  Rationale: `p2p validate --format json` is the current CLI precedent. PROP-090
  asks for JSON-ready surfaces; local implementation should minimize divergent
  option styles.

- D007: Treat lock creation as a write operation only.
  Rationale: read-only commands must not mutate existing projects. New init and
  explicit select/repair flows may write lock state.

- D008: Store definition state as project-definition memory, not governance
  memory.
  Rationale: proposal decisions remain in P2P governance artifacts. Definition
  state captures owner answers, assumptions, fields, and section progress.

- D009: Keep pack content declarative and non-authoritative.
  Rationale: vertical packs can suggest domain questions and examples, but
  cannot instruct agents to override system, developer, governance, repository,
  safety, or permission rules.

- D010: Defer full next-action computation.
  Rationale: definition-state semantics must stabilize before a standalone next
  action engine is reliable. A deterministic `next_suggested_action` field is
  acceptable when derived from validated state.

## Component Plan

### Core Models

Extend `src/p2p_engine/core/project_verticals.py` with additive records:

- `VerticalManifest`
- `VerticalProfile`
- `VerticalModule`
- `VerticalField`
- `VerticalCompletionPolicy`
- `VerticalPackSource`
- `ResolvedVerticalPack`
- `VerticalLock`
- `VerticalLockStatus`
- `ProjectDefinitionState`
- `ProjectDefinitionSectionState`
- `ProjectDefinitionFieldValue`
- `ProjectDefinitionAssumption`
- `ProjectDefinitionQuestion`
- `ProjectDefinitionBlocker`
- `ProjectDefinitionHistoryEntry`
- `ProjectDefinitionPatch`
- `ProjectDefinitionPatchResult`
- `ProjectVerticalContext`

Existing dataclasses remain compatible. New fields should be optional or added
through new records rather than breaking current constructor use.

### Pack Loading And Normalization

Keep the current single-file loader as a compatibility path. Add canonical
multi-file loading as a separate parse path that returns the same normalized
`VerticalPack`/extended model.

Recommended service/module boundaries:

- `ProjectVerticalService`
  - public application methods and facade delegation target;
  - list/show/validate/add/select/review orchestration.
- `project_vertical_pack_loader.py` or service-private helper
  - single-file and multi-file parsing;
  - split-file assembly;
  - normalization.
- `project_vertical_validation.py` or service-private helper
  - schema and cross-reference validation;
  - safety validation;
  - reusable issue construction.

If helper files are not introduced, keep helpers private and cohesive inside
`services/project_verticals.py` until size/duplication justifies extraction.

### Canonical Pack Layout

Canonical pack:

```text
<pack-root>/
  manifest.yml
  vertical.yml
  sections/
    <section-id>.yml
  rubrics.yml
  profiles/
    <profile-id>.yml
  modules/
    <module-id>.yml
  artifacts/
    <artifact-id>.yml
  examples/
    <example-id>.md
```

Minimum production pack:

```text
manifest.yml
vertical.yml
sections/
rubrics.yml
```

Current single-file compatibility input:

```text
vertical.yml
```

The loader should detect canonical vs single-file shape by checking for
`manifest.yml` and split directories. A single-file pack remains valid when it
contains the current top-level `vertical` mapping.

### Resolver

Introduce a resolver that returns a resolved pack plus source metadata:

```text
explicit path/reference
project-local .p2p/project/verticals/
P2P_HOME/verticals when configured
~/.p2p/verticals
packaged seed resources
future registry/Wavekit source (deferred)
base_project fallback only when explicitly allowed
```

Resolver source records should include:

- source type: `explicit`, `project_local`, `installed_p2p_home`,
  `installed_user`, `internal`, `future_registry`, `fallback`;
- source path or package coordinate;
- vertical id;
- version;
- schema version;
- checksum input summary.

### Lockfile

Path:

```text
.p2p/project/vertical.lock.yml
```

Shape:

```yaml
project_vertical_lock:
  schema_version: 1
  vertical_id: social_impact_program_design
  name: Social Impact Program Design
  version: 1.0.0
  pack_schema_version: 1
  source:
    type: internal
    resolved_from: p2p_engine.resources.verticals/social_impact_program_design
    package: p2p_engine
  checksum:
    algorithm: sha256
    value: "<stable-normalized-pack-checksum>"
  compatibility:
    p2p_min_version: "0.0.0"
  selected:
    at: "YYYY-MM-DD"
    by: owner
  trust:
    signed: false
```

Lockfile creation is allowed only in:

- new init flow;
- explicit vertical select flow;
- explicit lock repair/migration flow.

Validation/readiness/export/context/list/show must not create or repair a
lockfile.

### Existing Project Migration

Cases:

1. No `.p2p/project/vertical.yml`:
   - read-time fallback to `base_project`;
   - no write;
   - no lock warning unless a command explicitly requires a locked selection.

2. `.p2p/project/vertical.yml` exists and lockfile missing:
   - validation diagnostic with suggested explicit repair command;
   - read-only commands continue where compatible;
   - no automatic lock creation.

3. Lockfile exists and resolves:
   - use locked source/version/checksum as authoritative for selected vertical.

4. Lockfile exists but missing/mismatch:
   - fail closed for commands that depend on active vertical correctness;
   - suggest repair/reselect/review command;
   - no fallback to `base_project`.

### Definition State

Path:

```text
.p2p/project/definition.yml
```

Shape:

```yaml
project_definition:
  schema_version: 1
  vertical_id: social_impact_program_design
  vertical_version: 1.0.0
  profile: default
  modules: []
  lock:
    checksum: "<lock-checksum>"
  sections:
    - id: theory_of_change
      status: partial
      fields:
        target_beneficiaries:
          value: "..."
          source: owner
          updated_at: "YYYY-MM-DD"
      missing_required_fields:
        - outcome_chain
      assumptions:
        - id: A001
          status: to_validate
          text: "..."
      open_questions:
        - id: Q001
          field_id: outcome_chain
          question: "..."
      blockers: []
  next_suggested_action:
    kind: ask_question
    section_id: theory_of_change
    question_id: Q001
  history:
    - at: "YYYY-MM-DD"
      actor: owner
      operation: update_fields
      section_id: theory_of_change
```

Definition state validates against the active resolved vertical. The first slice
does not need sophisticated text merge behavior; patch operations should replace
or set explicit fields.

### Structured Patch Contract

Patch shape:

```yaml
project_definition_patch:
  schema_version: 1
  actor: owner
  operations:
    - op: set_field
      section_id: theory_of_change
      field_id: target_beneficiaries
      value: "..."
      provenance:
        source: owner_answer
    - op: set_section_status
      section_id: theory_of_change
      status: partial
    - op: add_assumption
      section_id: theory_of_change
      text: "..."
      status: to_validate
    - op: add_open_question
      section_id: theory_of_change
      field_id: outcome_chain
      question: "..."
```

Supported first-slice operations:

- `set_field`
- `clear_field`
- `set_section_status`
- `set_missing_required_fields`
- `add_assumption`
- `update_assumption_status`
- `add_open_question`
- `close_open_question`
- `add_blocker`
- `clear_blocker`
- `set_next_suggested_action`

Unsupported first-slice behavior:

- arbitrary YAML path patches;
- free-form mutation of history;
- complex long-answer merge;
- auto-completion without validation;
- domain-specific inference that bypasses owner input.

### CLI Surface

Keep existing commands and add output modes/commands additively.

Existing commands to preserve:

```bash
p2p project vertical list
p2p project vertical show <vertical-id>
p2p project vertical validate <path-or-id>
p2p project vertical propose "<project idea>"
p2p project vertical add <path>
p2p project vertical select <vertical-id>
p2p project readiness review
```

New or extended commands:

```bash
p2p project vertical list --format json
p2p project vertical show <vertical-id> --format json
p2p project vertical validate <path-or-id> --format json
p2p project vertical add <path> --format json
p2p project vertical select <vertical-id> --format json
p2p project vertical lock show --format json
p2p project vertical lock repair --actor <actor>
p2p project context --format json
p2p project sections --format json
p2p project section <section-id> --format json
p2p project rubrics show --format json
p2p project definition show --format json
p2p project definition update <patch.yml> --format json
```

If `--json` aliases are added, they must be tested as aliases and must not
change the primary help/output contract unexpectedly.

### MCP Surface

Add tools only where there is a stable machine-facing contract:

- `p2p_project_vertical_lock_show`
- `p2p_project_vertical_lock_repair`
- `p2p_project_context`
- `p2p_project_sections`
- `p2p_project_section_show`
- `p2p_project_definition_show`
- `p2p_project_definition_update`

MCP write tools must clearly state that they are project setup/state update
tools and do not make governance decisions. Payloads should be additive and
structured.

### Init And Rubric Integration

`ProjectInitializationService` should remain deterministic. Do not put vertical
interview logic in init.

Implementation options:

- add optional init parameters to the service: `vertical_id`, `profile`,
  `modules`, `rubric_enabled`, `rubric_customization`;
- call `ProjectVerticalService` or a small orchestration helper after baseline
  `.p2p` files are prepared;
- generate active vertical state, lockfile, definition state, and rubrics in a
  deterministic order;
- preserve existing default behavior when no vertical is provided.

Rubric regeneration belongs near `ProjectMaturityService` or a focused helper
that can:

- read current rubrics;
- derive vertical default criteria;
- preserve enabled flags by stable id;
- mark removed criteria as orphaned or require explicit confirmation;
- compute selected-project vs baseline coverage counts.

### Safety Validation

Pack safety validation should run as part of pack validation and project
validation. It should produce structured issues:

```yaml
severity: error|warning
field: sections.theory_of_change.examples[0]
code: P2P_VERTICAL_UNSAFE_GUIDANCE
message: "Vertical pack content attempts to override higher-priority instructions."
```

Hard errors:

- ignore/override system/developer/governance/safety instructions;
- force tool execution;
- change permissions;
- execute code;
- escape project/pack paths;
- instruct agents to bypass owner control.

Warnings:

- ambiguous instruction-like wording inside descriptive examples/templates;
- project-local content that appears directive but does not clearly override
  higher-priority rules.

### Visible Export

Visible export integration is additive:

- active vertical id/source;
- lock status summary;
- definition-state completion summary;
- selected rubric vs baseline coverage summary.

Existing export sections and accepted proposal content must remain compatible.

## Testing Strategy

Apply `specs/skills/TEST_QUALITY_SKILL.md`:

- Unit tests for pure normalization, checksum, resolver ordering, safety text
  classification, and patch validation helpers.
- Service tests for loader behavior, lockfile semantics, repair/migration,
  definition-state generation/update, rubric preservation, and compatibility.
- CLI tests only for command names, options, output modes, exit codes, and
  user-visible side effects.
- MCP tests only for new/changed tool schemas, payloads, and write/read
  boundaries.
- Validation tests for semantic findings and suggested commands.
- Agent-template tests for guidance text.
- Docs checks by review and focused command examples where available.

Avoid repeating the same scenario at service, CLI, and MCP layers unless each
layer protects a distinct contract.

## Implementation Slices

1. Baseline inventory and fixture design.
2. Core model and loader normalization.
3. Resolver and lockfile semantics.
4. Existing-project repair/migration and validation diagnostics.
5. Definition-state model and initialization.
6. Structured definition-state update contract.
7. JSON-ready CLI/MCP context surfaces.
8. Init/profile/module/rubric integration.
9. Safety validation and agent guidance.
10. Documentation, export summary, and regression validation.

Each slice should be independently testable and should avoid combining broad
refactoring with behavior changes unless the task explicitly calls for it.

## Deferred Technical Work

- Full `p2p project next-action --json` engine.
- Advanced definition-state migrations.
- Sophisticated long-answer merge.
- Remote/Wavekit install/search/publish.
- Executable vertical plugins.
- Top-level `p2p vertical ...` alias.
- Domain-specific vertical skills.

