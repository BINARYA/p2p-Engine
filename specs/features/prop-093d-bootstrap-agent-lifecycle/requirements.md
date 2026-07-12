# PROP-093D Bootstrap Agent Lifecycle Requirements

## Status

`draft`

## Traceability

- P2P proposal: `PROP-093 - Agent Persistence Boundaries And Proposal Authoring Flow`
- Accepted slice: `093-D - Bootstrap And Integration Lifecycle`
- Related local specs:
  - `specs/features/agent-integration-registry-production-hardening/`
  - `specs/features/p2pworkspace-agent-instructions-service-extraction/`
  - `specs/features/prop-093c-agent-persistence-policy/`

## Problem

The current init flow can make broad agent adapter generation feel accidental.
Guided init exposes `all` as the first choice, and scripted defaults may not
communicate how to add or remove integrations later.

At the same time, P2P already has an agent integration registry, install/update,
doctor, and uninstall behavior. The missing piece is not a new registry
architecture. The missing piece is a first-run strategy that chooses a sensible
initial integration set, explains the footprint, and shows the lifecycle for
adding or removing supported agents after initialization.

## Goals

- Make init adaptive and predictable.
- Always include the generic baseline.
- Add a detected current agent when detection is reliable.
- Fall back to `all` only when detection is unavailable and the user has not
  provided an explicit selection.
- Preserve explicit owner selection for one adapter, multiple adapters, and
  `all`.
- Make init summary and docs explain how to list, install, update, doctor,
  refresh, and uninstall integrations later.
- Keep lifecycle operations non-destructive and compatible with existing
  registry hardening.
- Preserve compatibility for existing init callers while exposing richer
  selection metadata additively.
- Avoid turning detected current-agent information into permanent project
  identity.

## Non-Goals

- Do not rewrite the agent integration registry.
- Do not remove support for any built-in adapter.
- Do not make one agent profile a permanent project identity.
- Do not silently remove existing adapter files during upgrade.
- Do not persist detected current-agent identity as authoritative project state.
- Do not implement agent persistence policy text; that belongs to `PROP-093C`.
- Do not implement MCP root or `.gitignore` hardening; that belongs to
  `PROP-093E`.

## Scope

In scope:

- init default agent selection;
- current-agent detection helper or adapter;
- CLI guided init prompt ordering and warning text;
- scripted init default behavior;
- MCP init parity;
- MCP tool catalog and result descriptions when init defaults change;
- init summary content for agent integration lifecycle;
- docs for adding/removing supported agent integrations.

Out of scope:

- changing adapter inventory;
- changing registry schema for adaptive selection metadata in this slice;
- changing drift, hash, unmanaged-file, or safe uninstall semantics already
  covered by earlier registry hardening;
- external provider authentication or remote agent installation;
- adding new MCP lifecycle tools when existing tools already cover the
  lifecycle semantics.

## Requirements

### R001: Generic baseline is always included

When P2P initializes a project, the effective agent integration set shall always
include `generic`.

The owner shall not need to select `generic` manually to receive baseline
instructions.

### R002: Explicit owner selection is preserved

When the owner provides an explicit agent selection, P2P shall honor it while
still including the generic baseline.

Supported explicit selections include:

- one adapter;
- multiple adapters;
- `all`.

### R003: Adaptive default uses detected current agent

When init runs without an explicit agent selection and P2P can reliably detect
the current client/agent, P2P shall initialize `generic` plus the detected
adapter.

Detection shall not invent unsupported adapter names.

### R004: Unknown detection falls back to `all` with warning

When init runs without an explicit agent selection and P2P cannot reliably
detect the current client/agent, P2P shall fall back to `all`.

The CLI/MCP result or init summary shall include a concise warning that this
creates files or registry records for all built-in adapters.

### R005: Guided init makes `all` explicit

In guided init, choosing `all` shall remain available, but the UI shall make the
broader footprint visible before or during selection.

The default shown to the owner shall be the adaptive default, not a blind `all`
choice when detection succeeds.

### R006: Scripted init remains deterministic

Scripted init shall remain deterministic. It shall not start a domain interview
or agent conversation.

Any detection used for defaults shall be based on explicit environment,
process, or known runtime signals and shall produce a stable selection result
or fallback.

Detection metadata used for this decision shall be reported as init metadata or
summary information only. It shall not become a persistent project identity.

### R007: Init summary groups agent integration output

After init, CLI output shall group created files or summaries by purpose,
including an agent integration section.

The agent integration section shall identify installed adapters and the
lifecycle commands for later changes.

### R008: Lifecycle guidance is visible

Generated instructions, init summary, and maintained docs shall explain:

```bash
p2p agent list
p2p agent install <adapter>
p2p agent update <adapter>
p2p agent doctor <adapter>
p2p agent uninstall <adapter>
p2p agent instructions refresh --profile <adapter>
```

The guidance shall cover Claude, Cursor, Copilot, Gemini, OpenCode, Codex, and
the generic baseline.

The documented lifecycle command shapes shall match the implemented CLI command
surface and MCP lifecycle tool catalog.

### R009: Lifecycle commands remain non-destructive

Install, update, refresh, doctor, and uninstall shall preserve existing registry
safety rules:

- do not overwrite drifted files without explicit force behavior;
- do not overwrite unmanaged files silently;
- do not remove shared baseline files;
- do not remove files still referenced by another installed adapter;
- do not allow `generic` uninstall.

### R010: MCP init and lifecycle parity is explicit

MCP init shall use the same default-selection semantics as CLI init.

MCP lifecycle tools shall expose the same service semantics as CLI lifecycle
commands. Any MCP gap shall be documented as deferred with a reason.

MCP tool descriptions and schemas shall not retain stale text that says init
blindly defaults to `all` after adaptive selection is implemented.

### R011: Existing projects are non-destructively upgradable

Projects initialized by earlier releases shall remain valid.

Refreshing or updating integrations shall not remove existing adapter files
unless the owner invokes a safe lifecycle command whose semantics allow removal.

Adaptive selection shall apply to fresh init defaults only. Existing projects
with `all` or broader installed adapter sets shall not be automatically narrowed
to `generic` plus a detected adapter during refresh, update, doctor, or upgrade.

### R012: Adapter selection state is inspectable

The owner or agent shall be able to inspect which adapters are installed and
their health through existing or updated lifecycle status surfaces.

At minimum, `p2p agent list`, `p2p agent show <adapter>`, and `p2p agent doctor`
shall remain sufficient.

### R013: Init compatibility facade is preserved

Existing public or facade init callers that expect created paths shall remain
compatible.

If richer selection metadata is needed, it shall be exposed through additive
result fields, a wrapper result, or a new method without breaking callers that
expect the existing created-path behavior.

Before changing any init signature, the implementation shall inspect CLI, MCP,
storage facade, and tests that call init.

### R014: Generated lifecycle guidance coexists with persistence policy

Generated instruction updates shall add concise lifecycle guidance without
removing or weakening the persistence policy introduced by `PROP-093C`.

Tests shall prove that generated instructions contain both the persistence
boundary and the lifecycle guidance after refresh.

## Public Surface Impact

### CLI

- Guided init default and prompt text change.
- Scripted init default behavior may change when no explicit agent is supplied.
- Init summary gains grouped agent lifecycle guidance.
- Existing lifecycle commands remain compatible.

### MCP

- MCP init default behavior changes to match CLI.
- Existing MCP agent lifecycle tools remain compatible and may need updated
  result text or tests.
- MCP init and lifecycle tool descriptions shall be updated when their
  documented defaults or semantics change.

### Storage

- Agent integration registry remains the source of installed adapter state.
- Existing registry schema remains compatible.
- Detected current-agent metadata is not persisted as project identity in this
  slice.

### Docs

- Installation and agent integration docs shall explain adaptive defaults and
  lifecycle commands.

### Tests

- Service, CLI, and MCP tests shall cover adaptive default, fallback `all`,
  explicit selections, lifecycle guidance, and compatibility.
- Tests shall cover existing broad installations not being narrowed by refresh
  or update.
- Tests shall cover generated instruction coexistence with `PROP-093C` policy
  blocks.
- Tests shall cover MCP catalog/description alignment for adaptive init.

## Compatibility

This slice changes default behavior only when the owner does not explicitly
select adapters. Explicit `--agent` values and existing lifecycle commands remain
supported.

Existing projects retain installed files and registry entries. The owner can
add, update, doctor, or uninstall integrations through existing lifecycle
commands.

## Risks

- Detection may be unreliable in shells, CI, or IDE-integrated terminals.
- Falling back to `all` can still create a broad footprint.
- Changing defaults can surprise tests or scripts that assumed implicit `all`.
- Lifecycle guidance may become outdated if command names change.

## Acceptance Criteria

- Init always includes the generic baseline.
- Explicit one-adapter, multi-adapter, and `all` selections remain supported.
- No explicit selection plus reliable detection creates `generic` plus detected
  adapter.
- No explicit selection plus unknown detection falls back to `all` with a clear
  warning.
- Guided init shows the adaptive default and makes `all` footprint explicit.
- Init summary and generated instructions explain add/update/doctor/refresh/
  uninstall lifecycle commands.
- CLI and MCP init use the same default-selection semantics.
- Existing projects and adapter files are preserved unless the owner invokes a
  safe lifecycle command.
- Existing broad adapter installs are not narrowed automatically by refresh or
  update.
- MCP tool descriptions no longer claim a blind default to `all` after adaptive
  selection is implemented.
- Generated instructions include lifecycle guidance while preserving the
  `PROP-093C` persistence boundary.
- Init compatibility callers expecting created paths remain supported.
- Focused service, CLI, MCP, and compatibility tests cover the behavior.
