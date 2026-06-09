# Design - Project Interaction Style

## Requirements Covered

- R001-R027
- N001-N010
- E001-E010
- AC001-AC008

## Key Decisions

- D001: Add a dedicated interaction style model and service.
  Rationale: the feature spans persisted project state, CLI, MCP, generated
  instructions, validation, and context. A service keeps normalization,
  defaults, validation, and persistence out of Typer commands and MCP handlers,
  and follows the local quality policy for explicit side effects and testable
  domain behavior.

- D002: Store project-level style in a versioned project file.
  Rationale: the accepted scope is a project default shared by all agents and
  mediators. A file under `.p2p/project/` keeps it with other project-scoped
  configuration, while missing state remains backward-compatible.

- D003: Do not use persisted named presets.
  Rationale: the owner rejected preset labels as source-of-truth because future
  dimensions make combinations hard to maintain. Descriptive labels may appear
  in output, but only numeric scale values are authoritative.

- D004: Keep style advisory and presentation-facing.
  Rationale: style affects how agents speak and how strongly they follow up. It
  must not alter governance authority, readiness scores, permissions, consent,
  validation truth, proposal decisions, or factual claims.

- D005: Use CLI/MCP as the only mutation surface for P2P memory.
  Rationale: local filesystem access is an implementation detail. Future remote
  MCP deployments may expose only tool methods backed by the P2P engine, so
  generated guidance must never rely on direct `.p2p` edits or temp-file copy
  workarounds.

- D006: Make context and generated instructions consumers, not owners.
  Rationale: context and templates should render the effective style returned
  by the service. They should not duplicate parsing or default logic.

- D007: Preserve existing readiness assertiveness semantics.
  Rationale: `readiness.assertiveness_guidance` is risk and evidence guidance.
  Project `interaction_style.assertiveness` is a communication preference. The
  implementation should distinguish the two and keep readiness safety
  conservative.

## Components

- `src/p2p_engine/core/interaction_style.py`
  - Dataclasses/value objects for:
    - `InteractionStyle`
    - `InteractionStyleScale`
    - `InteractionStyleDescriptor`
    - `InteractionStyleUpdate`
    - `InteractionStyleView`
  - Constants for allowed scale range and default values.
  - Pure validation and rendering helpers for scale descriptions.

- `src/p2p_engine/services/project_interaction_style.py`
  - Owns default fallback, read, show view, set/update, payload validation,
    schema validation, persistence, and atomic writes.
  - Exposes diagnostics usable by validation and command error handling.
  - Does not inspect proposals, registries, Git state, or readiness internals.

- `src/p2p_engine/storage/filesystem.py`
  - Adds a cached `ProjectInteractionStyleService` instance.
  - Adds facade methods such as:
    - `project_interaction_style()`
    - `set_project_interaction_style(...)`
    - `validate_project_interaction_style_findings()`
  - Contains no scale semantics beyond service construction and delegation.

- `src/p2p_engine/cli.py`
  - Adds a Typer sub-application under `project` named `interaction-style`.
  - The change is command-group wiring only.

- `src/p2p_engine/cli_commands/project_ops.py`
  - Registers `show` and `set` commands for the interaction style group, or
    delegates to a new `cli_commands/project_interaction_style.py` module if
    the implementation keeps project operations slimmer.
  - Owns option parsing, console output, and exit behavior only.

- `src/p2p_engine/mcp/catalog/project.py`
  - Adds tool definitions:
    - `p2p_project_interaction_style_show`
    - `p2p_project_interaction_style_set`
  - Tool descriptions must explicitly identify read-only vs write-safe
    behavior.

- `src/p2p_engine/mcp/handlers/project.py`
  - Dispatches the new MCP tools to workspace facade methods.
  - Contains no style validation logic beyond required argument extraction.

- `src/p2p_engine/mcp/registry.py`
  - Adds the new tool names to the ordered registry and preserves duplicate,
    missing, and unexpected tool checks.

- `src/p2p_engine/services/validation.py`
  - Validates present interaction style state.
  - Treats missing state as non-error default fallback.
  - Emits actionable findings for malformed present state.

- `src/p2p_engine/services/context_packets.py`
  - Adds effective interaction style values and allowed commands to compact
    context.
  - Uses an injected callback from `P2PWorkspace` to avoid direct state parsing.

- `src/p2p_engine/services/agent_templates.py`
  - Adds an `INTERACTION_STYLE_BLOCK` used by generated agent instructions.
  - Adds interaction style data to `.p2p/agent-policy.yml`.
  - Describes CLI/MCP inspection and update commands.
  - States that direct `.p2p` edits and temp-file copy workarounds are not an
    accepted mutation path.

- `docs/`
  - Documents CLI and MCP usage when the feature is implemented.

## Data Contract

Candidate persisted file:

```text
.p2p/project/interaction-style.yml
```

Candidate YAML shape:

```yaml
interaction_style:
  schema_version: 1
  scope: project
  technical_verbosity: 2
  formality: 2
  assertiveness: 0
  updated_at: "2026-06-09T10:00:00Z"
  updated_by: local
```

Effective read view:

```yaml
interaction_style:
  schema_version: 1
  scope: project
  configured: false
  source: defaults
  path: .p2p/project/interaction-style.yml
  technical_verbosity:
    value: 2
    label: balanced
    description: Light engine vocabulary when useful.
  formality:
    value: 2
    label: direct
    description: Direct, human, and professional enough for project work.
  assertiveness:
    value: 0
    label: baseline
    description: Current baseline follow-up behavior.
```

The labels in views are non-authoritative helper text. Persisted state stores
numeric scale values, not preset names.

## Scale Descriptors

`technical_verbosity`:

- `0`: no engine or technical workflow terms in owner-facing text unless
  required for correctness.
- `1`: minimal operational terms, with plain-language summaries first.
- `2`: light engine vocabulary when useful; default.
- `3`: include relevant commands, artifacts, and state names when they clarify
  the work.
- `4`: usually name commands, files, artifacts, and verification steps.
- `5`: detailed command-by-command and file/state level explanation.

`formality`:

- `0`: highly informal and colloquial, while staying respectful.
- `1`: casual and direct.
- `2`: direct, human, and professional enough for normal project work; default.
- `3`: clearly professional and measured.
- `4`: formal and reserved.
- `5`: highly formal, detached, and precise.

`assertiveness`:

- `0`: current baseline behavior; do not intensify beyond existing rules.
- `1`: light nudges for important gaps.
- `2`: regular follow-up on missing evidence and unclear decisions.
- `3`: proactive challenge of weak assumptions and incomplete artifacts.
- `4`: strict ordering, explicit missing evidence, and repeated next-question
  pressure until owner stops, defers, mutes, or decides.
- `5`: very persistent gap closure and order enforcement, still bounded by
  owner authority and safety rules.

## CLI Surface

Target commands:

```bash
p2p project interaction-style show
p2p project interaction-style set --technical-verbosity 3
p2p project interaction-style set --formality 1 --assertiveness 2
```

Options:

- `--technical-verbosity INTEGER`
- `--formality INTEGER`
- `--assertiveness INTEGER`
- `--actor TEXT`, default `local`
- `--root PATH`, consistent with other project commands

Output should be stable enough for tests while remaining human-facing. Example:

```text
Project interaction style
  scope: project
  configured: false
  source: defaults
  technical_verbosity: 2  balanced
  formality: 2  direct
  assertiveness: 0  baseline
  path: .p2p/project/interaction-style.yml
```

`set` should print the same effective view after writing.

## MCP Surface

Tool names:

- `p2p_project_interaction_style_show`
  - Read-only.
  - Input: `root`.
  - Output: effective interaction style view.

- `p2p_project_interaction_style_set`
  - Write-safe project configuration tool.
  - Input: `root`, optional `technical_verbosity`, optional `formality`,
    optional `assertiveness`, optional `actor`.
  - Output: updated effective interaction style view.
  - Does not make governance decisions and does not authorize arbitrary
    filesystem writes.

## Validation

Validation behavior:

- Missing `.p2p/project/interaction-style.yml`: no finding.
- Malformed YAML: `error`.
- Missing top-level `interaction_style`: `error`.
- Wrong schema version: `error` unless explicitly supported by a future
  migration.
- Missing required scales in a present file: `error`.
- Non-integer or out-of-range values: `error`.
- Unknown future keys: either `warning` or preserved metadata, decided in the
  service implementation and covered by tests.

Suggested recovery command:

```bash
p2p project interaction-style set --technical-verbosity 2 --formality 2 --assertiveness 0
```

## Generated Instructions And Policy

Generated `AGENTS.md`, adapter-specific files, and Codex project skills should
include:

- Run `p2p project interaction-style show` or MCP
  `p2p_project_interaction_style_show` to inspect the project default.
- Use `p2p project interaction-style set ...` or MCP
  `p2p_project_interaction_style_set` to update values when explicitly asked by
  the owner.
- Apply technical verbosity, formality, and assertiveness to owner-facing
  communication.
- Do not let style override governance, readiness, validation, permissions,
  consent, source-of-truth, or facts.
- Do not edit `.p2p` files directly, reverse-engineer managed paths, or copy
  temporary files into managed P2P memory as a workaround.

Generated `.p2p/agent-policy.yml` should include structured data:

```yaml
interaction_style:
  source: p2p_project_interaction_style
  scope: project
  defaults:
    technical_verbosity: 2
    formality: 2
    assertiveness: 0
  commands:
    show: p2p project interaction-style show
    set: p2p project interaction-style set
  mcp_tools:
    show: p2p_project_interaction_style_show
    set: p2p_project_interaction_style_set
  affects:
    - owner_facing_wording
    - detail_level
    - follow_up_pressure
  does_not_affect:
    - governance_authority
    - readiness_scores
    - validation_truth
    - permissions
    - consent
    - factual_claims
```

## Testing Strategy

- Unit tests for pure core validation and descriptors.
- Service tests for default fallback, set/update, partial updates, invalid
  values, malformed state, and atomic persistence.
- CLI tests for show/set output and failure paths.
- MCP tests for catalog schema, registry ordering, handler dispatch, read-only
  behavior, and write-safe mutation.
- Validation tests for missing and malformed state.
- Context tests for effective style inclusion and allowed commands.
- Agent instruction snapshot/content tests for `AGENTS.md`, Codex skill output,
  adapter files, and `.p2p/agent-policy.yml`.
- Compatibility tests for readiness to prove style does not alter readiness
  scoring or owner override semantics.

## Risks And Tradeoffs

- Risk: style language may be interpreted as permission to change facts or
  governance behavior.
  Mitigation: every generated block and data contract states the non-effect
  list explicitly.

- Risk: `assertiveness` name overlaps with readiness assertiveness guidance.
  Mitigation: service and generated text distinguish project communication
  preference from readiness-derived safety guidance.

- Risk: adding configuration under `.p2p/project/` creates compatibility
  pressure for older projects.
  Mitigation: missing state is a non-error default fallback; only malformed
  present state is invalid.

- Risk: generated instructions become too verbose.
  Mitigation: use one shared block and concise per-adapter text, with details in
  `.p2p/agent-policy.yml` and docs.

## Future Extensions

- Per-agent overrides layered over project defaults.
- Session/runtime overrides that do not mutate project defaults.
- Additional independent scales beyond the first three.
- Optional UI or prompts for changing style interactively.
- Migration support if schema version changes.
