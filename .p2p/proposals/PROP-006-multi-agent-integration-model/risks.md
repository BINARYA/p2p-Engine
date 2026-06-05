# Risks - PROP-006

## R1 - Overengineering

Risk:
Replicating too much of Spec Kit, OpenSpec, or external agent configuration
systems before P2P Engine needs it.

Mitigation:
Keep the MVP focused on a local registry, generated files, hashes, install all,
safe update, and safe uninstall. Defer external adapter packages and deep
provider-specific automation.

## R2 - Shared File Ownership

Risk:
Several adapters may depend on `AGENTS.md`. A naive uninstall could remove a
baseline file still needed by other integrations.

Mitigation:
Track `shared: true` files in `.p2p/agent-integrations.yml`. Uninstalling a
specific agent must not remove `AGENTS.md` or `.p2p/agent-policy.yml`.

## R3 - Manual Drift And Data Loss

Risk:
Users may edit generated files manually. Update or uninstall could overwrite or
delete those changes.

Mitigation:
Store generated file hashes. If the current hash differs from the stored hash,
mark the file as drifted and require explicit `--force` or manual resolution.

## R4 - Tool Convention Drift

Risk:
Cursor, Copilot, Gemini, OpenCode, Claude, or Codex may change their instruction
file conventions.

Mitigation:
Version adapter templates. Keep adapter definitions internal in the MVP. Update
documentation and tests when external conventions change.

## R5 - False Sense Of Enforcement

Risk:
Some agents treat instruction files as advisory and may not follow them
deterministically.

Mitigation:
Generated instructions must describe P2P boundaries clearly, but P2P Engine
must still rely on CLI validation, readiness checks, permission gates, and owner
decisions. Do not treat agent instructions as hard security.

## R6 - Global Configuration Side Effects

Risk:
Installing an adapter might be interpreted as permission to edit user-level
agent configuration, home directories, IDE settings, or MCP client config.

Mitigation:
PROP-006 MVP should only manage project-local files. Any user/global
configuration requires a separate explicit consent-gated flow.

## R7 - Registry Corruption Or Staleness

Risk:
The registry may get out of sync with actual files.

Mitigation:
`p2p agent show`, `p2p agent list`, and `p2p agent doctor` should recompute
current file hashes and report stale, missing, modified, or orphaned files.

## R8 - Adapter Surface Too Broad

Risk:
Supporting many agents at once can dilute quality and leave poorly tested
templates.

Mitigation:
Implement adapter behavior with a shared test harness and snapshot tests. Keep
the initial templates small, explicit, and based on documented file conventions.

## R9 - File Target Collisions During Install All

Risk:
`p2p agent install all` could cause two adapters to manage the same non-shared
file path.

Mitigation:
Declare shared vs non-shared file targets in adapter definitions. `install all`
must fail or warn before writing when two adapters would own the same non-shared
path.
