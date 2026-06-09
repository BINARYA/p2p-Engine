# Requirements - Pluggable Project Verticals And Readiness Orchestration

## Scope

Define local development requirements for the accepted PROP-085 direction:
pluggable pure-data project vertical packs, `base_project`, project-local custom
verticals, project readiness review, agent orchestration guidance, and
proposal-to-vertical traceability.

## Origin

- Source proposal: PROP-085 - Pluggable Project Verticals And Readiness Orchestration
- Decision: accepted
- Readiness at acceptance: `100 / decision_ready`, confidence `high`
- Related proposals: PROP-054, PROP-056, PROP-057, PROP-071, PROP-082, PROP-083

## In Scope

- Pure-data vertical pack schema using `.yml`/`.yaml` and optional `.md`.
- Internal default pack loading, including concrete `base_project`.
- One complete demonstration vertical.
- Project-local custom vertical pack add/select/override behavior.
- CLI and MCP surfaces to list, show, validate, propose, add, and select
  verticals.
- Project readiness review through `p2p project readiness review`.
- Traceability between vertical sections/capisaldi and proposals.
- Generated agent/project instructions for proactive project initialization and
  custom vertical candidate handling.
- Backward compatibility for existing projects that only have project domain and
  rubrics.

## Out Of Scope

- Remote REST registry implementation.
- Executable vertical plugins.
- Full five-vertical catalog implementation in the first slice.
- Full V1 default catalog implementation.
- Publishing project-local custom verticals to a shared registry.
- Replacing existing project rubrics or project maturity/readiness.
- Autonomous governance decisions by agents.

## Functional Requirements

- R001: THE SYSTEM SHALL define a versioned pure-data vertical pack schema.
- R002: THE SYSTEM SHALL validate required vertical metadata: id, name, version,
  description, and optional base/extends relationship.
- R003: THE SYSTEM SHALL validate required vertical sections/capisaldi with
  stable IDs, titles, purposes, and required flags.
- R004: THE SYSTEM SHALL validate required minimal readiness rubrics mapped to
  vertical sections or cross-domain project criteria.
- R005: THE SYSTEM SHALL validate required initial blocking questions mapped to
  vertical sections.
- R006: THE SYSTEM SHALL validate expected or suggested artifacts mapped to the
  vertical or individual sections.
- R007: THE SYSTEM SHALL allow optional examples, profiles, compatible modules,
  and rich output templates without requiring them for MVP validity.
- R008: THE SYSTEM SHALL provide `base_project` as a concrete internal vertical
  foundation, not only a conceptual fallback.
- R009: `base_project` SHALL include default sections for vision, objective,
  owner/stakeholders, target/users/beneficiaries, scope/non-goals, constraints,
  assumptions, risks, decisions/open questions, milestones/next actions,
  definition of done/readiness criteria, expected artifacts, and maturity status.
- R010: WHEN internal default packs are loaded, THE SYSTEM SHALL expose
  `base_project` and the MVP demonstration vertical through the same service
  APIs as project-local packs.
- R011: WHEN project-local packs exist, THE SYSTEM SHALL prefer them over
  internal defaults with the same vertical ID.
- R012: WHEN no suitable vertical is selected or available, THE SYSTEM SHALL
  degrade to `base_project` and report actionable guidance rather than failing.
- R013: WHEN a vertical is selected for a project, THE SYSTEM SHALL persist the
  active vertical ID and source through a supported service/CLI write path.
- R014: WHEN a custom vertical candidate is requested, THE SYSTEM SHALL generate
  a structured candidate from a project idea without automatically activating it.
- R015: A custom vertical candidate SHALL include a candidate id/name, proposed
  sections, minimal rubrics, blocking questions, expected artifacts, and
  rationale explaining what extends `base_project`.
- R016: WHEN adding a project-local vertical pack, THE SYSTEM SHALL validate it
  before persisting it and SHALL reject invalid packs with actionable diagnostics.
- R017: WHEN a project-local vertical pack is added successfully, THE SYSTEM
  SHALL make it available to list/show/validate/select/review commands.
- R018: WHEN `p2p project vertical list` is run, THE SYSTEM SHALL list available
  verticals with id, name, source, version, and active status.
- R019: WHEN `p2p project vertical show <vertical-id>` is run, THE SYSTEM SHALL
  show metadata, sections, rubrics, questions, artifacts, profiles, modules, and
  source.
- R020: WHEN `p2p project vertical validate <path-or-id>` is run, THE SYSTEM
  SHALL validate either an available vertical ID or a filesystem pack path.
- R021: WHEN `p2p project vertical propose "<project idea>"` is run, THE SYSTEM
  SHALL return a candidate pack proposal without mutating project governance or
  active vertical state.
- R022: WHEN `p2p project vertical add <path>` is run, THE SYSTEM SHALL persist a
  validated pack under project-local vertical state and SHALL not activate it
  unless an explicit activation option or follow-up select command is used.
- R023: WHEN `p2p project vertical select <vertical-id>` is run, THE SYSTEM SHALL
  set the project active vertical after validating that the vertical can be
  loaded.
- R024: WHEN `p2p project readiness review` is run, THE SYSTEM SHALL read project
  context, existing project rubrics/maturity, active vertical, project-local
  custom verticals, proposal summaries, decisions, and available traceability
  evidence.
- R025: Project readiness review SHALL produce a vertical skeleton summary with
  every section/caposaldo and its coverage status.
- R026: Project readiness review SHALL identify missing capisaldi, weak rubric
  coverage, missing initial questions, missing expected artifacts, and suggested
  next actions.
- R027: Project readiness review SHALL generate prioritized project-definition
  questions when initialization, capisaldi, or vertical coverage is incomplete.
- R028: Project readiness review SHALL reuse existing project rubrics and
  maturity/readiness artifacts rather than replacing them with a parallel engine.
- R029: THE SYSTEM SHALL support proposal-to-vertical traceability through a
  structured proposal coverage artifact or equivalent supported import/update
  path.
- R030: WHEN a proposal declares vertical coverage, THE SYSTEM SHALL preserve
  proposal ID, vertical ID, section IDs, relevance, rationale, and source.
- R031: WHEN project readiness review evaluates proposals, THE SYSTEM SHALL show
  relevant proposals, accepted decisions, gaps, risks, and open questions per
  vertical section.
- R032: Project readiness review SHALL identify vertical sections with no
  proposal coverage.
- R033: Project readiness review SHALL identify proposals that affect the
  project but are not mapped to any active vertical section.
- R034: Generated agent/project instructions SHALL tell agents to treat missing
  initialization, capisaldi, active vertical, or initial questions as priority
  context work.
- R035: Generated agent/project instructions SHALL describe how to propose,
  confirm, add, select, and review project-local custom verticals without making
  owner-controlled governance decisions.
- R036: THE SYSTEM SHALL keep existing project domain/rubrics commands
  functional for projects that do not use vertical packs.
- R037: THE SYSTEM SHALL keep the vertical pack schema registry-ready by
  preserving pack identity, version, source, and loader boundaries, without
  implementing remote registry behavior in this slice.
- R038: MCP parity SHALL be provided for public vertical and project readiness
  review operations where existing project MCP surfaces expose comparable CLI
  behavior.

## Non-Functional Requirements

- N001: THE SYSTEM SHALL keep domain behavior in services; CLI and MCP handlers
  SHALL remain thin orchestration and presentation layers.
- N002: THE SYSTEM SHALL not add unrelated domain behavior directly to
  `src/p2p_engine/cli.py`, `src/p2p_engine/storage/filesystem.py`, or
  `src/p2p_engine/mcp/tools.py`.
- N003: THE SYSTEM SHALL use deterministic, structured, human-readable persisted
  data for project-local vertical state.
- N004: THE SYSTEM SHALL use atomic writes for project-local vertical state and
  proposal vertical coverage state.
- N005: THE SYSTEM SHALL provide actionable validation errors that name the pack,
  field, and recovery action.
- N006: THE SYSTEM SHALL preserve compatibility for existing `.p2p/project`
  domain, rubrics, maturity, and init files.
- N007: THE SYSTEM SHALL avoid network access for registry lookup in the MVP.
- N008: THE SYSTEM SHALL include internal default pack resources in built wheel
  artifacts.
- N009: THE SYSTEM SHALL avoid broad proposal scans except in explicit project
  readiness review or traceability commands.
- N010: THE SYSTEM SHALL keep owner governance boundaries explicit in CLI, MCP,
  and agent guidance.

## Edge Cases And Errors

- E001: Missing vertical state falls back to `base_project` and reports guidance.
- E002: Unknown vertical IDs produce an actionable error and suggest
  `p2p project vertical list`.
- E003: Duplicate project-local vertical IDs override internal defaults but
  duplicate IDs within the same source are rejected.
- E004: Invalid pack schema rejects add/select/review operations that require
  that pack.
- E005: Missing required section IDs, rubric links, question links, or artifact
  links are validation errors.
- E006: Project-local pack directories with extra unknown files are accepted only
  if required files validate.
- E007: Proposal coverage for an unknown vertical section is reported as invalid
  or unmapped.
- E008: Project readiness review with no proposals still returns the vertical
  skeleton, missing coverage, and initial project questions.
- E009: Project readiness review with many proposals may truncate detail but
  SHALL report counts and a recovery command or option for full output.
- E010: Registry source configuration, if encountered before registry support,
  is reported as unsupported without failing local/internal loading.

## Acceptance Criteria

- AC001: Service tests prove internal `base_project` and the demonstration
  vertical can be loaded from package resources.
- AC002: Service tests prove project-local packs override internal defaults.
- AC003: Validation tests prove required pack fields, section references,
  rubric references, question references, and artifact references are checked.
- AC004: CLI tests prove `project vertical list/show/validate/propose/add/select`
  behavior.
- AC005: CLI tests prove invalid project-local packs fail with actionable
  diagnostics and do not mutate active vertical state.
- AC006: Tests prove missing vertical state falls back to `base_project` without
  breaking existing project rubrics/maturity.
- AC007: Tests prove `p2p project readiness review` emits vertical skeleton,
  coverage status, missing capisaldi, questions, and next actions.
- AC008: Tests prove proposal-to-vertical coverage is read and reflected in
  project readiness review.
- AC009: Tests prove unmapped proposals and uncovered vertical sections are
  reported.
- AC010: Tests prove generated agent instructions include proactive vertical
  orchestration and custom vertical candidate behavior.
- AC011: MCP tests prove vertical tools and project readiness review tools have
  explicit read/write descriptions and preserve owner governance boundaries.
- AC012: Documentation describes vertical pack structure, CLI usage, fallback,
  project-local override order, and registry deferral.
- AC013: Packaging tests or build checks prove default pack resources are present
  in the wheel/installable package.
- AC014: Existing project init, rubrics, maturity, proposal readiness, export,
  MCP registry, and validation tests remain passing.
- AC015: `.venv/bin/p2p validate` passes after implementation.
