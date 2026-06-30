# Requirements - Agent Integration Registry Production Hardening

## Scope

Bring the existing Agent Integration Registry MVP to production-grade behavior.

The current MVP already supports generated agent instructions, adapter install
and uninstall flows, registry writes, drift detection, and MCP lifecycle tools.
This feature does not reimplement that MVP. It formalizes and hardens the
runtime contract so generated agent files can be managed safely in real
projects.

## Origin

- Source Change Set: CHANGE-065 / PROP-006 context, bound locally through
  `specs/features/agent-integration-registry/`.
- Follow-up source: local source review of `src/`, `tests/`, and the current
  feature spec.
- Existing MVP feature: `specs/features/agent-integration-registry/`.

## In Scope

- Production invariants for the agent integration registry.
- Semantic registry validation beyond YAML shape checks.
- Safe default behavior for refresh, install, update, uninstall, and init.
- CLI and MCP parity for defaults and lifecycle semantics.
- A real agent-specific doctor surface with structured health findings for CLI
  and MCP.
- Correct aggregate adapter and project health reporting.
- Test coverage for dangerous edge cases and corrupted registry states.
- Documentation updates for public safety behavior.

## Out Of Scope

- Replacing the current adapter set.
- Adding per-agent or per-session interaction style overrides.
- Implementing local template override directories.
- Introducing direct AI provider invocation.
- Creating a web UI.
- Removing the existing MVP lifecycle commands.
- Moving templates to package-data assets unless explicitly selected as a later
  task after safety hardening.

## Functional Requirements

- R001: THE SYSTEM SHALL treat `generic` as a mandatory baseline adapter that is
  always present in the effective install set and cannot be uninstalled through
  service, CLI, or MCP entry points.
- R002: WHEN CLI project initialization and MCP project initialization are run
  without an explicit agent selection, THE SYSTEM SHALL use the same default
  agent set.
- R003: WHEN an agent operation would write a file that already exists and is
  not known as a clean managed file, THE SYSTEM SHALL skip or fail safely unless
  an explicit force option is provided for that operation.
- R004: WHEN `refresh_agent_instructions` updates generated instructions, THE
  SYSTEM SHALL apply the same drift and unmanaged-file safety rules as
  install/update.
- R005: WHEN an adapter has any managed file with status `missing`, `modified`,
  `unmanaged`, `conflicted`, or `stale_template`, THE SYSTEM SHALL NOT report
  the adapter as clean.
- R006: WHEN the registry is validated, THE SYSTEM SHALL validate semantic
  invariants including mandatory generic baseline, known adapters, relative
  safe paths, no path escape, no duplicate incompatible file ownership,
  required file metadata, known drift/status values, and forbidden active or
  preferred agent keys.
- R007: WHEN the registry references a managed file that exists, THE SYSTEM
  SHALL verify whether the recorded hash matches the current file bytes and
  report mismatches as modified/drifted state.
- R008: WHEN the registry references a managed file that does not exist, THE
  SYSTEM SHALL report missing state through list/show/doctor and validation.
- R009: WHEN shared files are installed or uninstalled, THE SYSTEM SHALL preserve
  files still referenced by `generic` or any other installed adapter.
- R010: WHEN `agent doctor` runs, THE SYSTEM SHALL perform agent-specific
  registry, file, hash, shared ownership, generic baseline, and safety checks
  and return actionable findings.
- R011: WHEN doctor output is requested through CLI, THE SYSTEM SHALL expose
  clear health status and exit behavior suitable for automation.
- R012: WHEN doctor or lifecycle behavior is exposed through MCP, THE SYSTEM
  SHALL use the same service-layer semantics as CLI and return structured data;
  this feature SHALL expose a read-only MCP agent doctor tool.
- R013: WHEN an operation supports force, THE SYSTEM SHALL make force explicit,
  narrow to the named operation, and covered by tests proving non-force behavior
  remains conservative.
- R014: WHEN an adapter has no dedicated file and consumes only shared generic
  instructions, THE SYSTEM SHALL represent that adapter explicitly in the
  registry and health model.
- R015: WHEN registry, policy, or generated files are written by the service,
  THE SYSTEM SHALL use atomic writes or document and isolate any exception.

## Non-Functional Requirements

- N001: THE SYSTEM SHALL keep domain rules and safety checks in services, not in
  Typer command bodies or MCP transport handlers.
- N002: THE SYSTEM SHALL preserve existing public commands and compatible output
  unless a breaking change is explicitly accepted.
- N003: THE SYSTEM SHALL keep `P2PWorkspace` as a compatibility facade with
  delegation only.
- N004: THE SYSTEM SHALL provide actionable diagnostics with recovery guidance
  for every unsafe or invalid registry condition.
- N005: THE SYSTEM SHALL test observable behavior through service, CLI, and MCP
  surfaces where public behavior is affected.
- N006: THE SYSTEM SHALL avoid direct writes outside the project root and reject
  registry paths that are absolute or escape through `..`.

## Edge Cases And Errors

- E001: Registry missing `generic` baseline.
- E002: Attempt to uninstall `generic`.
- E003: CLI init and MCP init default to different adapter sets.
- E004: Drifted file encountered during refresh.
- E005: Existing unmanaged target file encountered during install.
- E006: Managed file declared in registry but missing on disk.
- E007: Managed file hash mismatch.
- E008: Absolute registry path.
- E009: Registry path containing `..` or escaping the project root.
- E010: Duplicate file path with incompatible ownership metadata.
- E011: Shared file referenced by multiple adapters during uninstall.
- E012: OpenCode adapter installed with shared-only file ownership.
- E013: Unknown adapter or template id.
- E014: Registry contains forbidden active/default/current/preferred agent
  state.

## Acceptance Criteria

- AC001: Focused service tests cover generic baseline invariants, safe refresh,
  drift status, missing files, unmanaged files, and shared-file uninstall
  behavior.
- AC002: CLI tests cover default init parity, generic uninstall refusal,
  agent doctor health output, non-force safety, and force behavior where
  supported.
- AC003: MCP tests cover default init parity, lifecycle safety, generic
  uninstall refusal, and structured MCP agent doctor output.
- AC004: Validation tests cover malformed and semantically invalid
  `.p2p/agent-integrations.yml` payloads.
- AC005: Existing agent integration MVP tests continue to pass.
- AC006: Documentation describes registry invariants, safe lifecycle behavior,
  doctor semantics, and CLI/MCP parity.
- AC007: The feature spec, design, and tasks reference current source modules
  and no longer rely on stale pre-refactor line references.
