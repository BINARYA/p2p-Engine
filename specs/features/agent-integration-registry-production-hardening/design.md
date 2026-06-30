# Design - Agent Integration Registry Production Hardening

## Requirements Covered

- R001-R015
- N001-N006
- E001-E014
- AC001-AC007

## Key Decisions

- D001: Treat this as a new hardening feature, not a rewrite of the MVP.
  Rationale: `agent-integration-registry` already captures and implements the
  MVP. Production-readiness changes add stricter contracts and tests; keeping
  them separate avoids rewriting completed history and makes the follow-up
  easier to review.

- D002: Put health and validation rules in service code.
  Rationale: CLI and MCP must be thin transport/presentation layers. The same
  registry semantics must drive service tests, CLI commands, MCP tools, and
  validation.

- D003: Separate file status from adapter health.
  Rationale: `drift=clean` is too weak as an aggregate state. A file can be
  clean, modified, missing, unmanaged, conflicted, or stale. Adapter/project
  health should summarize those states without hiding errors.

- D004: Keep safety conservative by default.
  Rationale: generated agent files are visible project files and may be edited
  by users. The default behavior must never overwrite or delete user-modified
  content silently.

- D005: Align CLI and MCP defaults unless there is an explicit documented
  exception.
  Rationale: two public entry points creating different project shapes without
  an explicit option is surprising and hard to support.

- D006: Keep template relocation out of the first hardening slice.
  Rationale: package-data templates are useful, but safety, validation, and
  doctor behavior are higher-risk production gaps. Template relocation can be a
  later feature once the runtime contract is solid.

## Components

- `src/p2p_engine/services/agent_instructions.py`
  - Owns lifecycle planning and application for refresh/install/update/uninstall.
  - Should expose reusable registry status and health logic.
  - Should reject `generic` uninstall at service level.

- `src/p2p_engine/services/agent_templates.py`
  - Owns adapter definitions, aliases, expected file map, template IDs, and
    shared-file metadata.
  - May expose known template IDs to validation/doctor logic.

- `src/p2p_engine/services/validation.py`
  - Should call semantic agent registry validation and report actionable
    findings.

- `src/p2p_engine/cli_commands/agents.py`
  - Presents list/show/install/update/uninstall behavior.
  - Should remain free of domain decisions.

- `src/p2p_engine/cli_commands/doctor.py`
  - Presents runtime and agent doctor output.
  - Agent-specific findings should come from service logic.

- `src/p2p_engine/mcp/catalog/agents.py`
  - Defines structured MCP agent lifecycle tools.
  - Should expose a read-only `p2p_agent_doctor` tool backed by the same
    service result used by CLI doctor.

- `src/p2p_engine/mcp/handlers/project.py`
  - Handles read-only list/show.

- `src/p2p_engine/mcp/handlers/maintenance.py`
  - Handles write-safe install/update/uninstall and read-only agent doctor
    dispatch.

- `src/p2p_engine/services/project_initialization.py`
  - Calls agent instruction refresh during init.
  - Must receive the same default agent semantics as CLI/MCP.

- `tests/`
  - Service tests for status/health/safety rules.
  - CLI tests for observable commands and exit behavior.
  - MCP tests for parity and structured payloads.
  - Validation tests for invalid registry states.

- `docs/`
  - CLI/MCP/agent integration docs for invariants and safety behavior.

## Data And Contracts

### File Status

Use an explicit file status model in service output and doctor findings:

```text
clean
modified
missing
unmanaged
conflicted
stale_template
```

The existing registry field may remain `drift` for compatibility, but service
views should not collapse all non-clean states into `clean`.

### Adapter Health

Adapter health summarizes file statuses:

```text
clean
warning
error
```

Suggested mapping:

- `clean`: all expected managed files are present and match recorded hashes.
- `warning`: unmanaged or stale state that blocks automatic mutation but does
  not prove corruption.
- `error`: missing mandatory file, hash mismatch for managed file, invalid
  registry shape, unsafe path, forbidden state, or incompatible ownership.

### Registry Invariants

The registry must preserve these invariants:

- `schema_version` is supported.
- `baseline_profile` is `generic`.
- `generic` exists in `adapters`.
- No active/default/preferred/current/use/switch state exists.
- Adapter IDs are known.
- File paths are project-relative, not absolute, and do not escape root.
- Managed file records contain required metadata.
- Shared files are not deleted while referenced.
- Duplicate file paths have compatible shared/owner metadata.
- Recorded hashes are either empty for missing/unmanaged state or valid SHA-256.

### Shared File Ownership

Shared files have a single owner and may have multiple consumers. `generic`
owns shared baseline files such as `AGENTS.md` and `.p2p/agent-policy.yml`.
Adapter records may reference `AGENTS.md` with `shared: true` and
`owner: generic` to declare that they consume the baseline instruction surface.

Uninstalling an adapter must remove only safe, managed, unchanged, non-shared
files owned by that adapter. Shared files remain in place while `generic` or
any other installed adapter can still reference them.

OpenCode is represented as a shared-only adapter: installing it records the
adapter and its consumption of `AGENTS.md`, but does not create an
`opencode.json` file by default. Uninstalling OpenCode removes the adapter
record while preserving `AGENTS.md`.

### Operation Planning

Prefer a plan/apply shape for lifecycle operations:

```text
plan_agent_file_changes(operation, target, force=False)
apply_agent_file_changes(plan)
```

The plan should identify creates, clean updates, skipped drifted files, skipped
unmanaged files, blocked deletes, and force-only actions. CLI and MCP can then
display or return the same structured operation result.

## Error Handling

- Invalid registry payloads should produce validation findings and doctor
  findings, not silent default success.
- Unsafe writes should return skipped or blocked records with reasons.
- Force should be explicit and should not imply delete or overwrite outside the
  named operation.
- `generic` uninstall should fail from the service before CLI/MCP formatting.
- Path safety failures should be errors, not warnings.

## Migration And Compatibility

- Existing registry files should remain readable if they use schema version 1.
- Existing public CLI commands should continue to work.
- Existing `drift` fields can remain in registry records for compatibility.
- New health/status fields can be added to service views and doctor output
  without changing persisted schema immediately.
- If persisted schema changes are required, introduce a schema version decision
  and migration task before changing writes.

## Recommended Work Slices

### Slice 1 - Invariants And Parity

- Align default agent selection between CLI and MCP init.
- Enforce `generic` non-uninstallable through service, CLI, and MCP.
- Add tests for both.

### Slice 2 - Safe Writes, Refresh And Health

- Introduce atomic writes for registry/policy/generated files before broadening
  lifecycle write behavior.
- Rework refresh to use conservative write rules.
- Add file status and adapter health summaries.
- Ensure missing/unmanaged/modified files never aggregate to clean.

### Slice 3 - Semantic Validation And Doctor

- Add semantic registry validation.
- Implement real agent doctor findings from service logic.
- Add CLI and MCP doctor structured output.

### Slice 4 - Docs And Evidence

- Update docs and feature evidence.

### Slice 5 - Optional Template Maintenance

- Evaluate template package-data relocation and template staleness tracking as a
  separate follow-up if still needed.

## Risks And Tradeoffs

- Strict validation may reveal invalid state in existing projects. Mitigation:
  classify issues clearly and provide recovery commands.
- Adding health/status while retaining `drift` can create duplicate concepts.
  Mitigation: document compatibility role of `drift` and use health/status in
  new service views.
- Force behavior can become too broad. Mitigation: keep force operation-scoped
  and test non-force behavior first.
- MCP doctor expands public tool surface. Mitigation: expose it as read-only,
  back it with the same structured service result as CLI doctor, and cover it
  with MCP tests.

## Out Of Scope

- Changing the set of supported adapters.
- Adding `opencode.json` by default.
- Implementing local template overrides.
- Deprecating existing agent lifecycle commands.
- Moving all template text out of Python in the first hardening slice.
