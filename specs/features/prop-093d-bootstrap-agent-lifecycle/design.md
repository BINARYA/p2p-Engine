# PROP-093D Bootstrap Agent Lifecycle Design

## Design Summary

`PROP-093D` hardens first-run agent setup without replacing the existing agent
integration registry. The main work is to introduce an adaptive default
selection policy and make lifecycle operations visible during and after init.

The implementation should keep adapter install/update/uninstall safety in the
existing agent instruction service. Init should only decide the initial target
set and display clear next steps.

## Key Decisions

### D001: Separate selection policy from install mechanics

Agent selection should be a small service-level policy that returns an effective
agent profile or adapter set. The existing agent instruction service should
continue to own file generation, registry writes, drift checks, and uninstall
safety.

### D002: Detection is conservative and explicit

Detection should map known runtime signals to supported adapter IDs only.
Unknown or ambiguous signals produce no detected adapter.

Examples of possible signals:

- environment variables set by known agent runtimes;
- explicit CLI/MCP argument;
- future injected detector in tests.

Detection must be testable without depending on the real developer environment.

### D003: Fallback `all` is allowed but warned

`all` remains a compatibility fallback when no explicit agent is provided and
detection fails. The warning is part of the user-visible contract because the
footprint is intentionally broad.

### D004: Existing lifecycle service remains authoritative

Install, update, doctor, show, list, and uninstall behavior remains owned by the
agent instruction service and registry hardening feature. This slice should not
duplicate registry safety logic.

### D005: CLI and MCP use the same selector

CLI init and MCP init should call the same selection policy so their defaults do
not drift.

### D006: Init compatibility is preserved through additive metadata

Existing callers currently treat project init as a created-path workflow. This
slice should not break callers that expect that behavior.

If init needs richer selection details, expose them additively through a
summary/result wrapper, a new helper method, or additive CLI/MCP payload fields.
Do not require CLI, MCP, storage facade, or tests to adapt to a breaking return
type unless a compatibility shim preserves the existing path-list contract.

### D007: Detection is not project identity

Detected current-agent information is a bootstrap hint. It is not the project
identity and should not be persisted as authoritative registry or project
metadata in the first implementation.

The authoritative durable state remains the installed adapter set and its
health in the existing agent integration registry.

### D008: Lifecycle guidance coexists with `PROP-093C`

`PROP-093D` should add a concise lifecycle guidance block to generated
instructions without replacing or duplicating the `PROP-093C` persistence
policy blocks.

Generated instruction tests should assert both concepts remain present.

### D009: MCP catalog text is part of the contract

Because MCP clients see tool descriptions and schemas, the `p2p_init_project`
tool catalog should be updated when defaults change. It must not continue to
claim a blind `all` default after adaptive selection is implemented.

## Components

### New or existing agent selection helper

Preferred approach:

- add a small cohesive helper, such as `AgentProfileSelectionService` or
  `agent_selection.py`;
- inject environment/runtime detection for tests;
- return effective profile, detected adapter, fallback reason, and warning.

Candidate result fields:

- `requested_profile`;
- `effective_profile`;
- `effective_adapters`;
- `detected_adapter`;
- `selection_source`;
- `fallback_used`;
- `warning`.

### `src/p2p_engine/services/project_initialization.py`

Expected changes:

- call the selection helper before refreshing instructions;
- keep init deterministic;
- include selected adapter information in a result model or summary helper if
  required.

The current service returns `list[Path]`. If richer summary data is needed,
prefer adding a backward-compatible wrapper or result object carefully. Avoid
breaking existing facade callers unless a compatibility shim is added.

Implementation should inspect every `init_project()` caller before changing
the signature. At minimum this includes CLI init, MCP init, `P2PWorkspace`, and
tests.

### `src/p2p_engine/cli.py`

Expected changes:

- guided init default selection uses adaptive default;
- guided prompt explains `all` footprint;
- init summary groups agent integration information and lifecycle commands;
- existing CLI flags remain supported.

### `src/p2p_engine/mcp/handlers/maintenance.py`

Expected changes:

- MCP init uses the same default-selection policy;
- MCP result exposes warning/selection metadata if the existing payload allows
  additive fields.

### `src/p2p_engine/mcp/catalog/maintenance.py`

Expected changes:

- update `p2p_init_project` descriptions so they describe adaptive defaults and
  fallback `all` accurately;
- keep schemas additive and compatible;
- do not add new lifecycle tools unless an actual MCP parity gap is found.

### `src/p2p_engine/services/agent_templates.py`

Expected changes:

- generated instructions mention lifecycle commands for adding/removing
  supported adapters;
- add guidance through shared or adjacent template blocks so the persistence
  policy introduced by `PROP-093C` is preserved;
- do not duplicate full docs.

### Documentation

Likely touched docs:

- `docs/INSTALL.md`;
- `docs/AGENT-INTEGRATION.md`;
- `docs/CLI-GUIDE.md` if init behavior is described there.

## Data And Contracts

### Effective Profile

The effective profile should continue to use existing profile normalization:

- `generic`;
- single adapter values;
- comma-separated multi-adapter values;
- `all`.

The generic baseline remains implicit in expansion.

### Detection Metadata

Detection metadata should be user-visible but not required for existing
projects.

For this slice, the preferred implementation is to report detection in init
output/result without adding persistent schema. If future work persists
detection metadata, it must be additive, optional, and must not redefine project
identity.

### Init Summary

The summary should group output by purpose:

- P2P governance state;
- project rubric and permissions;
- agent integrations;
- MCP setup hint when requested;
- repository hygiene when implemented by `PROP-093E`;
- next actions.

This slice owns the agent integration section. `PROP-093E` owns MCP/hygiene
sections.

## Error Handling

- Unsupported explicit adapter values should keep existing normalization errors.
- Ambiguous detection should fall back to `all` with warning.
- Detection failures should not abort init.
- Install failures should keep existing service errors.

## Migration Strategy

No migration is required.

Existing projects keep their registry. Owners can inspect and adjust adapters
using lifecycle commands.

## Test Strategy

Use injectable detector inputs in service tests:

- explicit profile bypasses detection;
- detected Codex/Claude/etc. produces `generic,<adapter>`;
- unknown detection falls back to `all` with warning;
- multi-adapter input remains supported.

Use CLI tests for guided prompt/default text and init summary. Use MCP tests for
init parity and additive result fields.

Use existing lifecycle tests as regression coverage rather than duplicating all
registry hardening scenarios.

Add compatibility tests for:

- existing projects initialized with broad `all` adapters are not narrowed by
  refresh or update under adaptive defaults;
- generated instructions still include the `PROP-093C` persistent write
  boundary after lifecycle guidance is added;
- MCP catalog descriptions and schemas describe adaptive init defaults without
  stale blind-`all` wording;
- init compatibility callers that expect created paths still work.

## Risks And Mitigations

### Detection is wrong

Mitigation: keep detection conservative, inject it for tests, and allow explicit
owner override.

### Service return type compatibility

Mitigation: preserve existing `init_project()` return behavior or add an
additive summary method/result without breaking callers.

### Fallback `all` still has broad footprint

Mitigation: make warning visible and document post-init uninstall/update
lifecycle.

### CLI/MCP drift

Mitigation: use one selection helper and add parity tests.

### Generated instruction collision with `PROP-093C`

Mitigation: add lifecycle guidance through the same template layer and assert
that persistence policy blocks remain present.

### Detected agent mistaken for project identity

Mitigation: wording should say "detected current client" or equivalent, and
should explain that other integrations can be added later. Do not persist the
detected client as authoritative project identity.

### Existing broad installs narrowed accidentally

Mitigation: adaptive selection applies to fresh init defaults only. Existing
registry state should be preserved by refresh/update unless the owner invokes a
safe uninstall lifecycle command.

### MCP catalog drift

Mitigation: update MCP tool descriptions in the same slice as handler behavior
and add tests that catch stale default text.
