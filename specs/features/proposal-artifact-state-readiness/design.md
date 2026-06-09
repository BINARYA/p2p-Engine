# Design - Proposal Artifact State Readiness

## Requirements Covered

- R001-R034
- N001-N010
- E001-E014
- AC001-AC012

## Key Decisions

- D001: Add a dedicated artifact state domain model and service.
  Rationale: `PROP-086` requires artifact coverage to be a first-class state
  primitive. Keeping lifecycle rules in a service preserves the `P2PWorkspace`
  compatibility facade and avoids adding domain logic to CLI, MCP, or raw
  filesystem code. This follows `ENGINEERING_QUALITY_SKILL.md` guidance on
  clear responsibilities, explicit side effects, typed statuses, and testable
  domain behavior.

- D002: Keep artifact state separate from existing prompt/import artifact
  behavior.
  Rationale: `src/p2p_engine/services/proposal_artifacts.py` currently owns
  prompt generation, exploration status, and local file imports. Artifact state
  is a governance-adjacent coverage model, not an import helper. A separate
  `ProposalArtifactStateService` avoids mixing import side effects with
  readiness lifecycle state.

- D003: Treat CLI/MCP as the only public mutation surface for P2P memory.
  Rationale: local agents and future remote MCP clients must use the same
  boundary. Direct `.p2p` writes, reverse-engineered layouts, and temp-file copy
  workarounds break remote compatibility and violate the project source-of-truth
  policy.

- D004: Make artifact-aware state default for new proposals and advisory for
  older proposals.
  Rationale: future work gets full coverage without forcing a review of
  historical proposals. `absent_legacy` provides deterministic visibility while
  preserving compatibility.

- D005: Use graduated-by-risk expectations instead of making all artifacts
  mandatory.
  Rationale: simple proposals should stay lightweight, but governance,
  architecture, storage, CLI/MCP, compatibility, source-of-truth, and
  high-uncertainty proposals need stronger evidence by default.

- D006: Readiness and context consume artifact state; they do not own it.
  Rationale: readiness is scoring/explanation, context is operational summary,
  and validation is structural checking. Artifact state remains the source of
  truth for coverage and lifecycle.

- D007: Keep owner authority explicit.
  Rationale: agents may propose `not_applicable`, `deferred`, or `satisfied`,
  but owner-controlled governance decisions remain outside agent autonomy.
  Always-required and auto-required exceptions must stay owner-visible.

## Components

- `src/p2p_engine/core/proposal_artifact_state.py`
  - Enums/dataclasses for artifact ids, expectations, lifecycle states,
    confirmation states, risk flags, state records, state views, operation
    results, and validation summaries.

- `src/p2p_engine/services/proposal_artifact_state.py`
  - Owns artifact state read/write, schema validation, initialization, legacy
    marking, status calculation, risk trigger application, state transitions,
    owner confirmation, audit metadata, and next-command suggestions.

- `src/p2p_engine/services/proposals.py`
  - Calls artifact state initialization during proposal creation for new
    proposals, through a service dependency or workspace orchestration. It does
    not duplicate artifact policy.

- `src/p2p_engine/services/readiness.py`
  - Consumes artifact state during `assess` and review/explain flows.
  - Keeps `refresh` conservative unless existing behavior already supports
    additive guidance.
  - Emits owner-visible cautions for agent-proposed `not_applicable` or
    `deferred` on always-required or auto-required artifacts.

- `src/p2p_engine/services/context_packets.py`
  - Adds artifact coverage summaries for targeted proposal context.
  - Avoids broad proposal scans unless target context or an explicit command
    requires them.

- `src/p2p_engine/services/validation.py`
  - Validates present artifact state.
  - Treats missing artifact state on existing proposals as advisory
    `absent_legacy`, not as an error.

- `src/p2p_engine/services/registry_records.py` and
  `src/p2p_engine/services/registries.py`
  - Optionally include artifact state metadata only when needed by context or
    registry consumers. Registry refresh must not require state for every
    historical proposal.

- `src/p2p_engine/storage/filesystem.py`
  - Adds `P2PWorkspace` facade methods that delegate to
    `ProposalArtifactStateService`.
  - Does not own artifact lifecycle rules.

- `src/p2p_engine/cli_commands/proposal_artifacts.py` or
  `src/p2p_engine/cli_commands/proposal_artifact_state.py`
  - Registers `p2p proposal artifact ...` commands.
  - Handles Typer options and output only.

- `src/p2p_engine/cli_commands/proposals.py`
  - Registers the artifact command group under `proposal`.

- `src/p2p_engine/mcp/catalog/proposals.py`
  - Adds read-only and write-safe artifact state tool definitions with explicit
    schemas and descriptions.

- `src/p2p_engine/mcp/handlers/proposals.py`
  - Dispatches artifact state tools to workspace facade methods.
  - Does not implement lifecycle rules.

- `src/p2p_engine/services/agent_templates.py`
  - Adds generated instruction text requiring artifact coverage checks and
    CLI/MCP-only mutation of P2P memory.

- `docs/`
  - Documents public CLI/MCP behavior and agent mutation boundaries when the
    feature is implemented.

## Data And Contracts

Artifact state should be versioned and proposal-scoped. The concrete storage
path is owned by the service. A candidate shape is:

```yaml
proposal_artifacts:
  schema_version: 1
  proposal_id: PROP-XXX
  initialized_at: "2026-06-09T10:00:00Z"
  updated_at: "2026-06-09T10:00:00Z"
  status: active
  legacy:
    state: ""
    reason: ""
  artifacts:
    - id: proposal
      filename: proposal.md
      expectation: required
      status: satisfied
      reason: "Structured proposal body exists."
      source: system
      actor: local
      confirmation: system
      confirmed_by: ""
      risk_flags: []
      created_at: "2026-06-09T10:00:00Z"
      updated_at: "2026-06-09T10:00:00Z"
      history: []
    - id: impact_map
      filename: impact-map.yml
      expectation: required_when_applicable
      status: unknown
      reason: ""
      source: system
      actor: local
      confirmation: unconfirmed
      confirmed_by: ""
      risk_flags: []
      created_at: "2026-06-09T10:00:00Z"
      updated_at: "2026-06-09T10:00:00Z"
      history: []
```

Allowed expectations:

- `required`
- `required_when_applicable`
- `optional_memory`
- `not_expected`

Allowed lifecycle states:

- `unknown`: new proposal artifact has not been assessed yet.
- `missing`: artifact is applicable but absent or empty.
- `weak`: artifact exists but is insufficient.
- `satisfied`: artifact is adequate for the current readiness profile.
- `deferred`: known gap is intentionally postponed and remains visible.
- `not_applicable`: artifact is explicitly not applicable and has a rationale.
- `absent_legacy`: proposal predates artifact-aware state; advisory only.

Allowed confirmation states:

- `system`
- `agent_proposed`
- `owner_confirmed`
- `unconfirmed`

Initial tracked artifacts:

- `proposal.md`
- `readiness.yml`
- `open-questions.md`
- `clarifications.md`
- `findings.md`
- `exploration.md`
- `impact-map.yml`

The service may include existing related artifacts such as `alternatives.md`,
`risks.md`, `assumptions.md`, and `suggested-scope.md` as optional memory or
future extension points, but the first implementation must not expand the
required policy beyond `PROP-086` without a new decision.

## Graduated-By-Risk Policy

Always required for proposal maturity:

- `proposal.md`
- `readiness.yml`
- `open-questions.md`

Required when applicable:

- `clarifications.md`
- `findings.md`
- `exploration.md`
- `impact-map.yml`

Auto-required `findings.md` and `impact-map.yml` risk triggers:

- governance or policy changes;
- public CLI, MCP, API, or command behavior changes;
- storage schema, registry, proposal layout, or persistent state changes;
- compatibility or migration impact;
- cross-module, shared-service, facade, or core workflow impact;
- permission, consent, security, remote sync, provider, or destructive-operation
  concerns;
- source-of-truth, agent instruction, memory, or artifact-writing behavior
  changes;
- user-visible workflow, docs, install, or release impact;
- new dependency, runtime, infrastructure, or environment assumptions;
- high uncertainty, multiple credible alternatives, or claims that require
  technical evidence.

`exploration.md` is required when:

- multiple credible alternatives exist;
- uncertainty is high;
- the proposal chooses between materially different designs.

`clarifications.md` is required when:

- owner answers correct an assumption;
- owner answers narrow scope;
- owner answers change a requirement or direction.

## CLI Surface

Initial command target:

```bash
p2p proposal artifact init PROP-XXX
p2p proposal artifact status PROP-XXX
p2p proposal artifact set PROP-XXX ARTIFACT \
  --expectation required_when_applicable \
  --status not_applicable \
  --reason "..."
p2p proposal artifact confirm PROP-XXX ARTIFACT --actor owner
p2p proposal artifact mark-legacy PROP-XXX --reason "created before artifact-aware state"
```

Naming may change during implementation if the project already has a stronger
CLI convention, but the command family must remain proposal-scoped and public.

Read commands must not mutate state. Write commands must print enough
information for agents to continue without inspecting managed files directly.

## MCP Surface

Initial MCP tool target:

- `p2p_proposal_artifact_status`
  - Read-only.
  - Shows artifact coverage or `absent_legacy`.

- `p2p_proposal_artifact_init`
  - Write-safe.
  - Initializes artifact state for a proposal.
  - Does not decide governance.

- `p2p_proposal_artifact_set`
  - Write-safe.
  - Sets expectation/status/rationale/risk flags.
  - Does not decide governance.

- `p2p_proposal_artifact_confirm`
  - Write-safe.
  - Records owner confirmation of an artifact state.
  - Does not accept/reject/defer the proposal.

- `p2p_proposal_artifact_mark_legacy`
  - Write-safe.
  - Records advisory legacy absence.
  - Does not block or decide the proposal.

MCP handlers must call the same workspace/service methods as CLI commands. Tool
descriptions must identify read-only versus write-safe behavior.

## Main Flows

### New Proposal Creation

1. Existing proposal create flow creates the proposal scaffold.
2. Artifact state service initializes default artifact records.
3. Service applies graduated-by-risk defaults from available proposal content.
4. Command output includes the next artifact/status command when useful.
5. Proposal decision status remains draft/pending as before.

### Artifact Coverage Review

1. Read proposal state and artifact state.
2. If state is absent on a legacy proposal, return `absent_legacy` advisory.
3. If state is absent on a new proposal, return `unknown` or initialize through
   explicit write command.
4. Evaluate artifact file presence/content only as evidence for status, not as a
   substitute for persisted state when a state record exists.
5. Emit suggested next commands for missing, weak, deferred, and unknown
   artifacts.

### Readiness Integration

1. `refresh` remains conservative and additive.
2. `assess` consumes artifact state plus current artifacts and question state.
3. Missing, weak, unknown, and deferred required artifacts lower maturity or
   confidence.
4. `not_applicable` with rationale may satisfy required-when-applicable
   artifacts unless auto-required and unconfirmed.
5. `absent_legacy` is advisory and non-blocking.
6. Owner override metadata remains separate from computed score.

### Context Integration

1. Targeted proposal context includes artifact coverage summary.
2. Context highlights next action for high-priority artifact gaps.
3. Context shows reasons for `not_applicable`, `deferred`, and `absent_legacy`.
4. Context does not scan all proposals unless explicitly asked.

### Agent Instruction Flow

1. Before calling a proposal mature, agent runs readiness and artifact coverage
   inspection.
2. Agent asks one focused owner question for the highest-priority artifact gap.
3. Agent records artifact state changes through CLI/MCP only.
4. Agent refuses direct `.p2p` writes and temp-file copy workarounds.
5. If a needed primitive is missing, agent reports the missing primitive.

## Error Handling

- Unknown proposal: reuse existing proposal lookup errors and include recovery
  command.
- Unknown artifact: list allowed artifact ids.
- Invalid enum value: report field, invalid value, allowed values.
- Missing rationale for `not_applicable` or `deferred`: reject with a command
  example.
- Malformed state: validation finding with path, field, severity, and suggested
  command.
- Read-only MCP mutation attempt: tool schema prevents it; handler must not
  mutate state.
- Missing primitive: generated agent instructions and local policy require
  stopping instead of direct file edits.

## Migration And Compatibility

- Existing proposals do not require manual artifact state completion.
- Missing state on older proposals is `absent_legacy` advisory behavior.
- Validation must not fail only because a historical proposal lacks artifact
  state.
- Registry refresh must remain valid for mixed old/new proposals.
- Existing readiness files remain valid.
- Existing `proposal readiness show/init/refresh/explain/assess/review`
  commands remain compatible except for additive artifact guidance.
- Existing `proposal questions` behavior remains compatible.
- Existing MCP tools remain compatible; new artifact tools are additive.

## Risks And Tradeoffs

- Risk: Added CLI/MCP surface increases maintenance.
  Mitigation: centralize lifecycle behavior in `ProposalArtifactStateService`
  and keep presentation layers thin.

- Risk: Artifact expectations can become noisy for simple proposals.
  Mitigation: graduated-by-risk defaults and explicit `not_applicable` rationale.

- Risk: Agents may mark artifacts `not_applicable` too aggressively.
  Mitigation: owner-visible confirmation state and cautions for required or
  auto-required artifacts.

- Risk: Existing import helpers normalize temp-file copy patterns.
  Mitigation: artifact state feature does not use direct copy workflows, and
  generated agent instructions require public CLI/MCP primitives for managed
  memory mutation.

- Risk: Readiness scoring can drift from artifact state.
  Mitigation: readiness consumes artifact state and tests assert coverage-state
  behavior.

## Out Of Scope

- Rewriting all proposal exploration import workflows in the first slice.
- Automatically generating high-quality artifact content.
- Semantic AI risk classification.
- Bulk migration of all historical proposals.
- Provider-hosted review automation.
