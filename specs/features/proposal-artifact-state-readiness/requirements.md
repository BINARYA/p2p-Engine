# Requirements - Proposal Artifact State Readiness

## Scope

Define implementation requirements for accepted `PROP-086`: artifact-aware
proposal readiness backed by a dedicated artifact state primitive. The feature
turns proposal artifact coverage into structured, CLI/MCP-managed state so
agents can identify missing proposal artifacts, ask focused owner questions, and
avoid direct `.p2p` file manipulation.

## Origin

- Source proposal: `PROP-086 - Artifact-aware Proposal Readiness And Agent Interview Orchestration`
- Decision: accepted by owner with explicit readiness override
- Related specs:
  - `specs/features/proposal-readiness-review-and-questions`
  - `specs/features/p2pworkspace-readiness-service-extraction`
  - `specs/features/mcp-tool-surface`
- Local quality policy:
  - `AGENTS-p2p-dev-specs.md`
  - `specs/skills/ENGINEERING_QUALITY_SKILL.md`
  - `docs/DEVELOPMENT-GUIDELINES.md`

## In Scope

- Proposal-scoped artifact state lifecycle and persisted state.
- CLI commands under `p2p proposal artifact ...`.
- Explicit MCP read/write-safe tools for artifact state operations.
- Default artifact coverage for newly created proposals.
- Advisory `absent_legacy` handling for older proposals.
- Graduated-by-risk artifact expectation policy.
- Readiness and context integration that consumes artifact state.
- Validation of present artifact state with non-blocking legacy absence.
- Agent instruction updates that require CLI/MCP-only mutation of P2P memory.
- Tests for service, CLI, MCP, readiness, context, validation, and agent
  instruction behavior.

## Out Of Scope

- Autonomous proposal acceptance, rejection, deferral, or owner override.
- Retroactive manual completion of all historical proposals.
- Direct `.p2p` artifact edits, temp-file copies into managed proposal
  artifacts, or filesystem workarounds as an accepted agent workflow.
- Replacing current exploration prompt/import features in the first slice.
- External AI calls or semantic classification beyond deterministic rule
  checks.
- Breaking existing readiness, proposal, MCP, validation, or registry behavior.

## Functional Requirements

- R001: WHEN a new proposal is created, THE SYSTEM SHALL initialize
  artifact-aware state for that proposal by default.
- R002: WHEN artifact state is initialized, THE SYSTEM SHALL create structured
  proposal-scoped state through the P2P engine write path only.
- R003: WHEN a proposal predates artifact-aware state, THE SYSTEM SHALL report or
  mark artifact state as `absent_legacy` without raising a validation error.
- R004: WHEN artifact state is shown, THE SYSTEM SHALL list each tracked
  artifact with artifact id, expectation, status, rationale, actor/source,
  timestamp, risk flags, and owner confirmation state when present.
- R005: WHEN an artifact status is set, THE SYSTEM SHALL validate artifact id,
  expectation, status, rationale requirements, actor/source, and allowed
  transitions before persisting state.
- R006: WHEN an artifact is marked `not_applicable`, THE SYSTEM SHALL require a
  non-empty concrete rationale.
- R007: WHEN an artifact is marked `deferred`, THE SYSTEM SHALL require a
  non-empty concrete rationale and keep the deferred gap visible in status,
  context, and readiness outputs.
- R008: WHEN an artifact is always-required or auto-required, THE SYSTEM SHALL
  keep agent-proposed `not_applicable` or `deferred` visible to the owner and
  SHALL NOT silently treat it as equivalent to `satisfied`.
- R009: WHEN the owner confirms an artifact state, THE SYSTEM SHALL record the
  confirmation separately from agent-proposed state.
- R010: WHEN artifact state is missing for an older proposal, THE SYSTEM SHALL
  allow read/status commands to return advisory `absent_legacy` state without
  forcing migration.
- R011: WHEN artifact-aware readiness evaluates a proposal, THE SYSTEM SHALL
  consume artifact state as the source of truth for artifact coverage.
- R012: WHEN readiness consumes artifact state, THE SYSTEM SHALL expose coverage
  states including `unknown`, `missing`, `weak`, `satisfied`, `deferred`,
  `not_applicable`, and `absent_legacy`.
- R013: WHEN compact context is generated for a proposal, THE SYSTEM SHALL
  surface applicable empty, weak, deferred, unknown, and missing artifacts as
  next-step gaps.
- R014: WHEN compact context sees `not_applicable` or `absent_legacy`, THE
  SYSTEM SHALL show the rationale or legacy advisory status rather than hiding
  the artifact.
- R015: WHEN risk triggers are detected, THE SYSTEM SHALL raise artifact
  expectations deterministically according to the graduated-by-risk policy.
- R016: WHEN a proposal touches governance, policy, public CLI, MCP, API,
  command behavior, storage schema, registry state, proposal layout, persistent
  state, compatibility, migration, permissions, consent, security, remote sync,
  provider behavior, destructive operations, source-of-truth rules, agent
  memory, artifact-writing behavior, user-visible workflows, docs/install/
  release, runtime dependencies, infrastructure assumptions, high uncertainty,
  multiple credible alternatives, or evidence-dependent claims, THEN THE SYSTEM
  SHALL auto-require `findings.md` and `impact-map.yml`.
- R017: WHEN multiple credible alternatives exist, uncertainty is high, or a
  proposal chooses between materially different designs, THEN THE SYSTEM SHALL
  require `exploration.md`.
- R018: WHEN owner answers correct, narrow, or change an assumption, THEN THE
  SYSTEM SHALL require `clarifications.md`.
- R019: WHEN unresolved owner decisions exist, THEN THE SYSTEM SHALL require
  `open-questions.md` and keep unresolved questions visible.
- R020: WHEN artifact state is initialized for a proposal without special risk
  triggers, THE SYSTEM SHALL still require `proposal.md`, `readiness.yml`, and
  `open-questions.md` for proposal maturity.
- R021: WHEN `p2p proposal artifact status PROP-XXX` is run, THE SYSTEM SHALL
  print artifact coverage, legacy state if applicable, and suggested next
  commands.
- R022: WHEN `p2p proposal artifact init PROP-XXX` is run, THE SYSTEM SHALL
  initialize or refresh default artifact state without changing proposal
  decision status.
- R023: WHEN `p2p proposal artifact set PROP-XXX ARTIFACT ...` is run, THE
  SYSTEM SHALL persist the requested state change and return the updated record.
- R024: WHEN `p2p proposal artifact mark-legacy PROP-XXX` is run, THE SYSTEM
  SHALL record advisory legacy absence without changing proposal decision
  status or computed readiness score by itself.
- R025: WHEN MCP artifact tools are exposed, THE SYSTEM SHALL label read-only
  and write-safe behavior explicitly in tool descriptions and schemas.
- R026: WHEN an MCP write-safe artifact tool mutates state, THE SYSTEM SHALL use
  the same P2P engine service/write path as the CLI.
- R027: WHEN an agent-facing instruction set is generated, THE SYSTEM SHALL tell
  agents to inspect artifact coverage before claiming proposal maturity.
- R028: WHEN an agent needs to update P2P artifact state, THE SYSTEM SHALL
  instruct the agent to use only the P2P CLI or explicit write-safe MCP tools.
- R029: WHEN no public CLI/MCP primitive exists for a requested P2P memory
  mutation, THE SYSTEM SHALL require the agent to stop and report the missing
  primitive instead of writing files directly.
- R030: WHEN large generated text must be imported into a proposal artifact, THE
  SYSTEM SHALL require a dedicated CLI/MCP import/update primitive rather than
  copying a prepared temporary file into `.p2p`.
- R031: WHEN validation inspects artifact state, THE SYSTEM SHALL reject
  malformed present state with actionable diagnostics and SHALL accept absent
  legacy state as non-error advisory state.
- R032: WHEN registries or context include artifact information, THE SYSTEM
  SHALL avoid broad proposal scans unless the command explicitly requires them.
- R033: WHEN artifact state changes, THE SYSTEM SHALL preserve audit metadata
  and avoid losing prior status/rationale history needed for owner review.
- R034: WHEN readiness or context detects agent-proposed `not_applicable` or
  `deferred` on an always-required or auto-required artifact, THE SYSTEM SHALL
  emit owner-visible caution text.

## Non-Functional Requirements

- N001: THE SYSTEM SHALL preserve public CLI and MCP compatibility for existing
  commands and tools.
- N002: THE SYSTEM SHALL keep domain lifecycle behavior in core models and
  services; CLI and MCP handlers SHALL remain presentation/transport layers.
- N003: THE SYSTEM SHALL keep `P2PWorkspace` as the compatibility facade and add
  only facade delegation or compatibility glue there.
- N004: THE SYSTEM SHALL not add unrelated domain behavior directly to
  `src/p2p_engine/cli.py`, `src/p2p_engine/storage/filesystem.py`, or
  `src/p2p_engine/mcp/tools.py`.
- N005: THE SYSTEM SHALL use typed statuses/enums for expectations, lifecycle
  states, confirmation state, and risk triggers.
- N006: THE SYSTEM SHALL use atomic writes for persisted artifact state.
- N007: THE SYSTEM SHALL emit diagnostic errors with recovery commands for
  unknown proposals, unknown artifacts, invalid states, missing rationales, and
  malformed state.
- N008: THE SYSTEM SHALL avoid hidden side effects from read-only commands and
  read-only MCP tools.
- N009: THE SYSTEM SHALL not falsify computed readiness scores when owner or
  advisory overrides exist.
- N010: THE SYSTEM SHALL keep artifact state schema versioned and
  backward-compatible.

## Edge Cases And Errors

- E001: Unknown proposal IDs produce an actionable error naming the proposal.
- E002: Unknown artifact IDs produce an actionable error with allowed artifact
  ids and a recovery hint.
- E003: Invalid expectation, status, confirmation state, or risk trigger values
  produce validation errors.
- E004: `not_applicable` without rationale is rejected.
- E005: `deferred` without rationale is rejected.
- E006: Agent-proposed `not_applicable` for an auto-required artifact remains
  visible and cautionary until owner-confirmed or revised.
- E007: Missing artifact state on a legacy proposal returns `absent_legacy`
  advisory status.
- E008: Missing artifact state on a newly created proposal is reported as
  `unknown` or `missing`, not silently treated as legacy.
- E009: Malformed artifact state YAML is a validation finding with path, field,
  severity, and suggested recovery command.
- E010: Read-only MCP artifact tools must not mutate state.
- E011: Write-safe MCP artifact tools must not accept governance decision
  operations.
- E012: Large generated artifact content must not be imported by copying local
  temp files into `.p2p`; absence of an import primitive is a missing primitive
  error.
- E013: Registry refresh must not fail only because older proposals lack
  artifact-aware state.
- E014: Readiness refresh must remain conservative when artifact evidence is
  incomplete or unknown.

## Acceptance Criteria

- AC001: New proposal creation initializes artifact state by default and focused
  tests prove the state is visible through CLI status.
- AC002: Service tests cover lifecycle states, expectations, rationale
  requirements, owner confirmation, audit metadata, and invalid transitions.
- AC003: CLI tests cover `proposal artifact status`, `init`, `set`, and
  `mark-legacy` normal and error paths.
- AC004: MCP catalog and handler tests prove artifact tools are read-only or
  write-safe as described and use workspace/service operations.
- AC005: Validation tests prove malformed present state is rejected while absent
  legacy state is advisory and non-blocking.
- AC006: Readiness tests prove artifact state is consumed and reports coverage
  states without replacing computed readiness with owner judgment.
- AC007: Context tests prove artifact gaps, `not_applicable` rationale,
  `deferred` rationale, `unknown`, and `absent_legacy` appear in compact
  proposal context.
- AC008: Risk trigger tests prove `findings.md` and `impact-map.yml` become
  auto-required for cross-cutting, governance, CLI, MCP, storage, compatibility,
  permission, remote-sync, source-of-truth, or evidence-dependent proposals.
- AC009: Agent instruction tests prove agents are told to use only CLI/MCP
  write-safe primitives and to refuse direct `.p2p` writes or temp-file copy
  workarounds.
- AC010: Tests or documented scenarios prove no public workflow requires
  manually copying a prepared file into a managed proposal artifact.
- AC011: Existing proposal, readiness, question, registry, validation, and MCP
  compatibility tests remain passing.
- AC012: Documentation covers artifact state lifecycle, commands, MCP tools,
  legacy advisory behavior, and agent mutation boundaries.
