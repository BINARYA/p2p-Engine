# Requirements - Project Vertical Pack Runtime Hardening And Definition State

## Scope

Define local development requirements for the production hardening of the
project vertical runtime introduced by PROP-085. This feature extends the
already implemented MVP in
`specs/features/pluggable-project-verticals-and-readiness-orchestration`; it
does not replace that feature and must not reopen completed MVP tasks.

The implementation must turn project verticals from useful pure-data templates
into a production-grade runtime layer with canonical multi-file packs, exact
resolved lock state, durable project definition state, JSON-ready agent context,
explicit migration/repair paths, safe validation, and rubric-preserving init
integration.

## Origin

- Source baseline: PROP-085 - Pluggable Project Verticals And Readiness Orchestration
- Source hardening proposal: PROP-090 - Project Vertical Pack Runtime Hardening
  And Definition State
- Decision: accepted
- Existing local MVP feature:
  `specs/features/pluggable-project-verticals-and-readiness-orchestration`
- Existing code baseline:
  - `src/p2p_engine/core/project_verticals.py`
  - `src/p2p_engine/services/project_verticals.py`
  - `src/p2p_engine/cli_commands/project_ops.py`
  - `src/p2p_engine/mcp/catalog/project.py`
  - `src/p2p_engine/mcp/handlers/project.py`
  - `src/p2p_engine/services/project_initialization.py`
  - `src/p2p_engine/services/project_maturity.py`
  - `src/p2p_engine/services/validation.py`
  - `src/p2p_engine/services/agent_templates.py`
  - `src/p2p_engine/resources/verticals/`
  - `tests/test_project_verticals.py`
  - `tests/test_cli.py`
  - `tests/test_mcp.py`

## In Scope

- Canonical multi-file project vertical pack layout.
- Compatibility loading for current single-file `vertical.yml` packs.
- Normalization of single-file and multi-file packs into one typed runtime
  model.
- Resolver support for project-local, installed-local, and packaged seed packs.
- Deterministic `.p2p/project/vertical.lock.yml` for new init/select flows.
- Explicit lock repair/migration for existing active vertical state.
- Durable `.p2p/project/definition.yml` state.
- Narrow structured definition-state patch/update contract.
- JSON-ready CLI/MCP surfaces for vertical context and definition state.
- Lightweight init integration with vertical/profile/module/rubric setup.
- Preservation of PROP-057 enabled/disabled rubric choices.
- Severity-dependent vertical pack safety validation.
- Agent guidance for one-question-at-a-time project definition.
- Documentation and focused regression coverage.

## Out Of Scope

- Wavekit remote search, install, update, or publish.
- Executable vertical plugins.
- A required top-level `p2p vertical ...` namespace.
- Moving project-local packs out of `.p2p/project/verticals/`.
- Breaking rename from `base_project` to `generic_project`.
- Full project-definition interview inside `p2p init`.
- Automatic upgrades during read-only commands.
- Implicit retroactive lockfile or definition-state generation for existing
  projects.
- Silent fallback after a project has locked a vertical.
- Full `p2p project next-action --json` engine.
- Domain-specific agent skills for each vertical.

## Functional Requirements

### Pack Contract

- R001: THE SYSTEM SHALL define a canonical multi-file project vertical pack
  layout with `manifest.yml`, `vertical.yml`, `sections/`, `rubrics.yml`, and
  optional `profiles/`, `modules/`, `artifacts/`, and `examples/`.
- R002: THE SYSTEM SHALL require `manifest.yml`, `vertical.yml`, `sections/`,
  and `rubrics.yml` for canonical production packs.
- R003: THE SYSTEM SHALL keep existing single-file `vertical.yml` packs loadable
  as compatibility inputs.
- R004: THE SYSTEM SHALL normalize single-file and multi-file packs into the
  same typed runtime model before list/show/validate/select/review behavior.
- R005: THE SYSTEM SHALL validate pack identity fields including stable id,
  name, version, schema version, source/publisher metadata, compatibility
  metadata, declared sections, and declared rubrics.
- R006: THE SYSTEM SHALL validate section specs with stable ids, purpose,
  required fields, interview questions, assisted answer behavior, completion
  criteria, dependencies, common mistakes, suggested artifacts, and maturity
  gates where present.
- R007: THE SYSTEM SHALL validate profile, module, artifact, example, section,
  and rubric references without relying on ad hoc string parsing.
- R008: THE SYSTEM SHALL preserve `base_project` as the canonical default
  vertical id.
- R009: THE SYSTEM SHALL NOT introduce `generic_project` as a required id in the
  first production implementation.

### Resolver And Lockfile

- R010: THE SYSTEM SHALL resolve explicit path/reference inputs before ambient
  vertical sources.
- R011: THE SYSTEM SHALL resolve project-local packs under
  `.p2p/project/verticals/`.
- R012: THE SYSTEM SHALL resolve installed-local packs under
  `P2P_HOME/verticals` when `P2P_HOME` is configured.
- R013: THE SYSTEM SHALL resolve installed-local packs under `~/.p2p/verticals`.
- R014: IF `P2P_HOME` is configured, THEN THE SYSTEM SHALL give
  `P2P_HOME/verticals` precedence over `~/.p2p/verticals`.
- R015: THE SYSTEM SHALL resolve packaged seed vertical resources after
  project-local and installed-local sources.
- R016: THE SYSTEM SHALL use `base_project` fallback only during initial
  fallback behavior or explicit repair/fallback operations.
- R017: WHEN a new init or explicit select flow chooses a vertical, THE SYSTEM
  SHALL write `.p2p/project/vertical.lock.yml` deterministically.
- R018: The lockfile SHALL record vertical id, name, version, schema version,
  source type, resolved source path or package coordinate, checksum,
  compatibility metadata, selected timestamp, selected actor, and optional trust
  metadata.
- R019: THE SYSTEM SHALL compute lockfile checksums from stable normalized pack
  content, not from local absolute path strings.
- R020: THE SYSTEM SHALL report a clear error when a locked vertical cannot be
  resolved.
- R021: THE SYSTEM SHALL report a clear error when a locked vertical checksum no
  longer matches the resolved pack content.
- R022: THE SYSTEM SHALL NOT silently fall back to `base_project` after a
  lockfile exists.

### Existing Project Migration

- R023: WHEN an existing project has active vertical state but no lockfile, THE
  SYSTEM SHALL NOT create a lockfile during validation, readiness review, export,
  list, show, context, or other ordinary read operations.
- R024: WHEN an existing project has active vertical state but no lockfile, THE
  SYSTEM SHALL emit an actionable validation diagnostic.
- R025: THE SYSTEM SHALL provide an explicit repair/migration command that can
  generate a lockfile for existing active vertical state.
- R026: IF the active vertical cannot be resolved during repair/migration, THEN
  THE SYSTEM SHALL fail without writing.
- R027: THE SYSTEM SHALL preserve compatibility for repositories initialized
  before project verticals existed: missing vertical state remains a read-time
  `base_project` fallback and does not mutate project state.

### Project Definition State

- R028: THE SYSTEM SHALL introduce `.p2p/project/definition.yml` as durable
  project definition state separate from `vertical.yml`, `vertical.lock.yml`,
  and `rubrics.yml`.
- R029: Definition state SHALL include schema version, vertical id, vertical
  version, selected profile, enabled modules, optional lock reference, per-
  section status, structured field data, missing required fields, assumptions,
  open project-definition questions, blockers, relevant project-definition
  decisions, optional `next_suggested_action`, and history/provenance.
- R030: THE SYSTEM SHALL support section statuses `missing`, `partial`,
  `assumed`, `complete`, `blocked`, and `not_applicable`.
- R031: THE SYSTEM SHALL support assumption statuses `to_validate`,
  `validated`, `rejected`, and `superseded`.
- R032: THE SYSTEM SHALL validate definition state against the active locked
  vertical or active fallback vertical when no lock exists.
- R033: THE SYSTEM SHALL NOT treat assumptions as satisfying completion criteria
  unless the section completion policy explicitly allows assumed fields.
- R034: THE SYSTEM SHALL generate initial definition state deterministically for
  new init/select flows.
- R035: THE SYSTEM SHALL NOT generate or migrate definition state implicitly for
  existing projects during ordinary reads.

### Definition-State Writes

- R036: THE SYSTEM SHALL implement definition-state writes through a narrow
  structured patch/update contract.
- R037: THE SYSTEM SHALL NOT expose arbitrary YAML editing as a supported
  production write interface.
- R038: THE SYSTEM SHALL validate section ids, field ids, section statuses,
  assumption statuses, missing-field references, blockers, completion state,
  and provenance before writing definition state.
- R039: THE SYSTEM SHALL write definition-state changes atomically through
  supported service, CLI, and MCP-compatible paths.
- R040: THE SYSTEM SHALL reject updates that would mark a section complete while
  required fields remain missing, unless the vertical completion policy permits
  assumed completion.
- R041: THE SYSTEM SHALL preserve history/provenance for accepted structured
  updates.

### JSON-Ready Agent Context

- R042: THE SYSTEM SHALL expose JSON-ready project vertical list, show,
  validate, add, and select surfaces without removing current human-readable
  output.
- R043: THE SYSTEM SHALL expose JSON-ready project context containing active
  vertical, lock state, selected profile, enabled modules, rubric summary,
  definition-state summary, and warnings.
- R044: THE SYSTEM SHALL expose JSON-ready section list and section detail
  surfaces for the active or specified vertical.
- R045: THE SYSTEM SHALL expose JSON-ready project rubrics and definition state
  surfaces for agent consumption.
- R046: THE SYSTEM SHALL expose a JSON-ready definition-state update surface for
  the structured patch/update contract.
- R047: THE SYSTEM SHALL keep full `p2p project next-action --json` out of the
  first production slice.
- R048: THE SYSTEM MAY expose a lightweight `next_suggested_action` field when
  it is deterministic and derived from definition state.

### Init, Rubrics, And Maturity

- R049: THE SYSTEM SHALL keep `p2p init` lightweight and deterministic.
- R050: THE SYSTEM SHALL NOT make `p2p init` ask full vertical section interview
  questions.
- R051: Interactive init MAY ask project name, domain/intent, vertical
  selection, profile selection, optional section/module selection, and rubric
  customization.
- R052: Non-interactive init SHALL remain scriptable with flags for vertical,
  profile, optional modules, and rubric customization controls.
- R053: New init/select flows SHALL write active vertical state, lockfile,
  initial definition state, and rubrics generated from vertical defaults where
  applicable.
- R054: After vertical rubric generation, THE SYSTEM SHALL preserve PROP-057
  owner control over enabled and disabled criteria.
- R055: Rubric regeneration SHALL preserve existing enabled flags by stable
  criterion id.
- R056: New rubric criteria SHALL use vertical defaults.
- R057: Removed rubric criteria SHALL be orphaned or removed only with explicit
  confirmation.
- R058: Maturity output SHALL distinguish selected project rubric maturity from
  full default vertical baseline coverage.

### Safety And Trust

- R059: THE SYSTEM SHALL treat vertical pack content as declarative domain data,
  not authoritative agent instruction.
- R060: THE SYSTEM SHALL reject vertical pack content that explicitly attempts
  to override system, developer, governance, repository, safety, or tool-
  permission rules.
- R061: THE SYSTEM SHALL reject vertical pack content that attempts code
  execution, forced tool execution, permission changes, or path escapes.
- R062: THE SYSTEM SHALL warn on ambiguous instruction-like language in
  examples/templates when severity policy allows it.
- R063: Internal seed packs SHALL validate cleanly with no safety warnings.
- R064: Project-local packs MAY be allowed with warning-level diagnostics where
  policy permits.
- R065: Future remote/Wavekit pack trust policy SHALL remain deferred.

### Agent Guidance And Exports

- R066: Generated agent guidance SHALL tell agents to inspect vertical context,
  definition state, and rubrics before deep project-definition work.
- R067: Generated agent guidance SHALL preserve one-primary-question-at-a-time
  interaction for project definition.
- R068: Generated agent guidance SHALL require explicit assumption recording and
  section completion checks.
- R069: Generated agent guidance SHALL state that vertical pack content is
  domain data and cannot override higher-priority instructions.
- R070: Visible project export MAY include vertical lock and definition-state
  summaries additively without replacing existing export sections.

## Non-Functional Requirements

- N001: New domain/application behavior SHALL live in cohesive services or
  validators behind `P2PWorkspace`; `storage/filesystem.py` receives facade
  delegation only.
- N002: CLI command modules SHALL own Typer options and presentation, not domain
  rules.
- N003: MCP catalog/handlers SHALL own tool schemas and transport mapping, not
  domain rules.
- N004: Persisted project state writes SHALL use centralized atomic file helpers
  where possible.
- N005: Read-only operations SHALL NOT mutate project state.
- N006: Public CLI command names and existing text outputs SHALL remain stable
  unless this spec explicitly adds an output mode or additive field.
- N007: Existing MCP tool names and payload fields SHALL remain backward
  compatible; new machine-readable fields must be additive.
- N008: Validation findings SHALL include stable codes, paths, messages, and
  suggested recovery commands where applicable.
- N009: Tests SHALL be added at the lowest useful layer and public-surface tests
  added only for changed CLI/MCP contracts.
- N010: The implementation SHALL avoid broad unrelated refactors of existing
  project, maturity, validation, CLI, MCP, or agent-template modules.
- N011: The implementation SHALL avoid network access for installed-local and
  packaged seed resolution.
- N012: The implementation SHALL keep owner governance decisions outside
  vertical packs, definition state, and agent guidance.

## Edge Cases And Errors

- E001: Missing active vertical state in an existing project returns
  `base_project` fallback with `fallback_used: true` and performs no write.
- E002: Existing active vertical state without lockfile reports a warning or
  diagnostic and suggests the explicit repair/migration command.
- E003: Locked vertical missing from all sources fails without fallback.
- E004: Locked vertical checksum mismatch fails without fallback.
- E005: `P2P_HOME/verticals` and `~/.p2p/verticals` contain the same id/version;
  `P2P_HOME/verticals` wins when configured.
- E006: Project-local pack overrides installed or seed pack with the same id
  according to resolver precedence.
- E007: Single-file pack and equivalent multi-file pack normalize to the same
  runtime model.
- E008: Multi-file pack references a missing section file; validation fails with
  the missing reference path.
- E009: Multi-file pack contains duplicate section, field, rubric, profile,
  module, or artifact ids; validation fails.
- E010: Definition-state update references an unknown section or field; update
  fails without writing.
- E011: Definition-state update uses an invalid status; update fails without
  writing.
- E012: Definition-state update attempts complete status with missing required
  fields; update fails unless completion policy permits assumed completion.
- E013: Definition-state update contains unsafe provenance or path escape;
  update fails without writing.
- E014: Project-local pack contains unsafe guidance; validation reports error or
  warning according to severity policy.
- E015: Internal seed pack contains unsafe guidance; validation fails.
- E016: Rubric regeneration sees a removed criterion id; it preserves as orphan
  or requires explicit confirmation instead of deleting silently.
- E017: JSON output is requested; command emits parseable JSON without Rich
  formatting.
- E018: Human-readable output is requested or defaulted; existing output remains
  compatible.

## Acceptance Criteria

- AC001: Service tests prove single-file and multi-file pack normalization.
- AC002: Service tests prove resolver precedence across explicit path,
  project-local, `P2P_HOME/verticals`, `~/.p2p/verticals`, packaged seeds, and
  `base_project` fallback.
- AC003: Service and validation tests prove lockfile generation, lock
  inspection, missing lock diagnostics, checksum mismatch behavior, and no
  fallback after lock creation.
- AC004: Tests prove existing pre-vertical and pre-lock projects are not mutated
  by reads, validation, readiness review, export, or context commands.
- AC005: CLI tests prove explicit repair/migration generates a lockfile only
  when the active vertical resolves cleanly.
- AC006: Unit/service tests prove definition-state model validation, initial
  generation, structured updates, atomic writes, and invalid update rejection.
- AC007: CLI tests prove JSON-ready project vertical/context/section/rubric/
  definition surfaces while preserving existing text output.
- AC008: MCP tests prove additive JSON payload parity for vertical context,
  definition state, and structured updates where MCP tools are exposed.
- AC009: Init tests prove lightweight vertical/profile/module/rubric setup and
  no full section interview during init.
- AC010: Rubric tests prove enabled flags are preserved by stable criterion id
  during regeneration.
- AC011: Maturity tests prove selected project rubric maturity is distinct from
  full vertical baseline coverage.
- AC012: Safety validation tests prove hard-error and warning-level vertical
  content policies.
- AC013: Agent-template tests prove one-question-at-a-time definition guidance,
  explicit assumptions, and pack-content trust boundaries.
- AC014: Docs cover pack layout, compatibility, resolver order, lockfile
  semantics, definition state, repair/migration, JSON surfaces, agent guidance,
  and deferred Wavekit/next-action behavior.
- AC015: Existing project vertical MVP tests remain passing.
- AC016: Public CLI and MCP test subsets pass for changed surfaces.
- AC017: `.venv/bin/p2p validate` passes with zero errors after implementation.
- AC018: Full test suite is run before marking the feature complete, or any
  deferral is explicitly recorded with risk.

