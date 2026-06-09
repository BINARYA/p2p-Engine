# Requirements - Project Interaction Style

## Scope

Define implementation requirements for accepted `PROP-087`: a project-level
interaction style model for agents and mediators that communicate with the
owner. The feature gives every participant a shared default style through
validated project configuration, public CLI commands, MCP tools, generated
agent instructions, and compact context.

The style model affects owner-facing communication and follow-up behavior only.
It must not change governance authority, readiness truth, validation outcomes,
permissions, consent, proposal state, or factual evidence.

## Origin

- Source proposal: `PROP-087 - Agent Personality Model For Decision Mediation`
- Decision: accepted by owner after readiness reached decision-ready state
- Accepted public namespace: `p2p project interaction-style`
- Accepted default scope: project-level default shared by all agents and
  mediators
- Accepted scales:
  - `technical_verbosity`: integer `0..5`, default `2`
  - `formality`: integer `0..5`, default `2`
  - `assertiveness`: integer `0..5`, default `0`
- Local quality policy:
  - `AGENTS-p2p-dev-specs.md`
  - `specs/skills/ENGINEERING_QUALITY_SKILL.md`
  - `docs/DEVELOPMENT-GUIDELINES.md`

## In Scope

- Project-level persisted `interaction_style` configuration.
- Deterministic defaults for missing configuration.
- Validation for present malformed configuration.
- CLI commands under `p2p project interaction-style ...`.
- MCP read and write-safe tools for the same behavior.
- Generated `AGENTS.md`, project skills, adapter instructions, and
  `.p2p/agent-policy.yml` guidance.
- Compact context exposure so agents can discover the current style before
  broad reads.
- Tests for service, CLI, MCP, validation, context, and generated instructions.
- Documentation for CLI/MCP usage and source-of-truth boundaries.

## Out Of Scope

- Per-agent, per-mediator, per-user, or per-session overrides.
- Persisted named presets or role labels as source-of-truth configuration.
- Autonomous adaptation from conversation sentiment or user profiling.
- Changing proposal readiness scores, readiness gates, artifact state,
  permissions, consent, governance decisions, or validation truth.
- Rewriting current proposal readiness `assertiveness_guidance`; the new
  project `assertiveness` scale may influence wording, but must remain distinct
  from readiness-derived guidance.
- Direct manual edits to `.p2p/` as an accepted user or agent workflow.

## Functional Requirements

- R001: WHEN interaction style configuration is absent, THE SYSTEM SHALL return
  the defaults `technical_verbosity=2`, `formality=2`, and `assertiveness=0`
  without writing project state during read-only operations.
- R002: WHEN interaction style configuration is persisted, THE SYSTEM SHALL
  store it as project-scoped P2P state through the engine write path only.
- R003: WHEN interaction style configuration is shown, THE SYSTEM SHALL return
  the numeric values, default/configured source, project scope, storage path,
  schema version, and human-readable descriptions for each scale.
- R004: WHEN a scale value is accepted from CLI, MCP, or internal service calls,
  THE SYSTEM SHALL validate that it is an integer from `0` through `5`.
- R005: WHEN a scale value is missing from a set/update request, THE SYSTEM
  SHALL keep the current value for that scale.
- R006: WHEN no persisted configuration exists and a partial set/update request
  is made, THE SYSTEM SHALL apply the provided values over the default values
  before persisting.
- R007: WHEN an invalid scale name, non-integer value, out-of-range value, or
  malformed payload is provided, THE SYSTEM SHALL reject the change with an
  actionable diagnostic and SHALL NOT partially write state.
- R008: WHEN `p2p project interaction-style show` is run, THE SYSTEM SHALL
  print the effective project interaction style and identify whether defaults
  or persisted values are being used.
- R009: WHEN `p2p project interaction-style set` is run with one or more scale
  options, THE SYSTEM SHALL persist the updated project-level interaction style
  and print the resulting effective values.
- R010: WHEN `p2p project interaction-style set` is run without any scale
  option, THE SYSTEM SHALL fail with a clear message requiring at least one
  value to change.
- R011: WHEN MCP exposes interaction style tools, THE SYSTEM SHALL provide a
  read-only show tool and a write-safe set/update tool with explicit schemas and
  descriptions.
- R012: WHEN an MCP write-safe interaction style tool mutates state, THE SYSTEM
  SHALL use the same workspace facade and service path as the CLI.
- R013: WHEN generated agent instructions are refreshed, THE SYSTEM SHALL
  include how to inspect the project style through CLI and MCP, how to apply the
  three scales, and the rule that `.p2p` must not be edited directly.
- R014: WHEN generated `.p2p/agent-policy.yml` is refreshed, THE SYSTEM SHALL
  include the effective interaction style model, defaults, scale descriptions,
  CLI commands, and MCP tool names.
- R015: WHEN compact context is generated, THE SYSTEM SHALL include the
  effective interaction style values and a bounded command for changing them.
- R016: WHEN style guidance is consumed by generated instructions or context,
  THE SYSTEM SHALL state that style changes presentation and proactivity only,
  not source-of-truth, owner authority, validation, readiness, permissions, or
  factual claims.
- R017: WHEN the project has malformed persisted interaction style state, THE
  SYSTEM SHALL report validation findings with path, field, severity, message,
  and suggested recovery command.
- R018: WHEN interaction style state is missing in old or new projects, THE
  SYSTEM SHALL treat the absence as non-error default fallback.
- R019: WHEN project status or context reports interaction style, THE SYSTEM
  SHALL avoid broad proposal, registry, Git, or source-code scans.
- R020: WHEN future style dimensions are added, THE SYSTEM SHALL allow the data
  model and rendering helpers to extend without introducing required named
  presets.

## Scale Semantics

- R021: WHEN `technical_verbosity=0`, THE SYSTEM SHALL instruct agents to avoid
  engine and technical workflow terms in owner-facing messages unless required
  for correctness.
- R022: WHEN `technical_verbosity=5`, THE SYSTEM SHALL allow agents to detail
  relevant commands, files, state transitions, and verification steps.
- R023: WHEN `formality=0`, THE SYSTEM SHALL instruct agents to use a very
  informal, colloquial tone while still respecting project and safety rules.
- R024: WHEN `formality=5`, THE SYSTEM SHALL instruct agents to use a highly
  formal, detached, professional tone.
- R025: WHEN `assertiveness=0`, THE SYSTEM SHALL preserve the current baseline:
  agents may identify gaps, but they should not intensify follow-up beyond
  existing proposal/readiness rules.
- R026: WHEN `assertiveness=5`, THE SYSTEM SHALL instruct agents to persistently
  surface unresolved gaps, weak evidence, missing ordering, and next required
  questions until the owner explicitly stops, defers, mutes, or decides.
- R027: WHEN readiness-derived stepped assertiveness guidance conflicts with
  project interaction assertiveness, THE SYSTEM SHALL preserve readiness safety
  guidance and use project style only to adjust wording and follow-up framing.

## Non-Functional Requirements

- N001: THE SYSTEM SHALL preserve existing public CLI, MCP, storage, validation,
  and generated instruction behavior unless the accepted proposal requires a
  compatible additive change.
- N002: THE SYSTEM SHALL keep domain normalization and validation in core models
  or services; CLI and MCP handlers SHALL remain presentation and transport
  layers.
- N003: THE SYSTEM SHALL keep `P2PWorkspace` as a compatibility facade and add
  only service construction plus delegation there.
- N004: THE SYSTEM SHALL not add unrelated domain behavior directly to
  `src/p2p_engine/cli.py`, `src/p2p_engine/storage/filesystem.py`, or
  `src/p2p_engine/mcp/tools.py`.
- N005: THE SYSTEM SHALL use typed dataclasses or value objects for effective
  style, persisted state, scale descriptors, update requests, and validation
  results.
- N006: THE SYSTEM SHALL use atomic writes for persisted interaction style
  state.
- N007: THE SYSTEM SHALL keep read-only CLI/MCP operations free of hidden write
  side effects.
- N008: THE SYSTEM SHALL keep persisted schema versioned and
  backward-compatible.
- N009: THE SYSTEM SHALL use ASCII-safe generated text and YAML unless existing
  file conventions require otherwise.
- N010: THE SYSTEM SHALL provide focused tests for each touched public surface.

## Edge Cases And Errors

- E001: Missing persisted style state returns effective defaults with
  `configured=false`.
- E002: Persisted style state with one missing scale is malformed and produces
  validation diagnostics; read behavior may still return a conservative
  effective fallback if the service can do so without hiding the error.
- E003: Values `-1`, `6`, floats, booleans, strings that are not integer
  literals, and null values are rejected.
- E004: Unknown persisted keys are preserved only if the chosen service design
  explicitly supports forward-compatible metadata; otherwise they produce a
  warning or error documented by the implementation.
- E005: Partial updates preserve existing or default values for omitted scales.
- E006: Set/update commands without any scale option fail without writing.
- E007: Malformed YAML is reported by validation and by show/set commands with a
  clear recovery hint.
- E008: Read-only MCP show must not create the default file.
- E009: Write-safe MCP set must not perform governance decisions or permission
  bypasses.
- E010: Generated instructions must not tell agents to copy temp files into
  managed `.p2p` paths.

## Acceptance Criteria

- AC001: Service tests prove default fallback, full update, partial update,
  invalid value rejection, malformed state diagnostics, and atomic persistence.
- AC002: CLI tests prove `project interaction-style show` and `set` normal and
  error paths, including default fallback and partial updates.
- AC003: MCP tests prove read-only and write-safe tool schemas, dispatch,
  payload shapes, and no mutation from the read-only tool.
- AC004: Validation tests prove missing state is non-error while malformed
  present state is reported with actionable diagnostics.
- AC005: Context tests prove effective interaction style values and allowed
  commands are present without broad scans.
- AC006: Generated instruction tests prove `AGENTS.md`, Codex project skills,
  other adapter instructions, and `.p2p/agent-policy.yml` include CLI/MCP-only
  style inspection and update guidance.
- AC007: Tests or documented scenarios prove style settings do not change
  readiness scores, owner-controlled governance decisions, permissions,
  consent, or validation truth.
- AC008: Existing CLI, MCP, validation, context, agent instruction, and
  readiness compatibility tests continue to pass.
