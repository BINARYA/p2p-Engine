# CHANGE-065 Implementation Tasks

Temporary implementation checklist for `CHANGE-065` / `WORK-004`.
Delete this file after the implementation is complete and the P2P Work item is
submitted/reviewed.

## Scope

Implement PROP-006: Agent Integration Registry MVP.

The current implementation already has:

- `p2p init --agent generic|codex|claude|all`
- `p2p agent instructions refresh`
- `AGENTS.md`
- `CLAUDE.md`
- `.codex/skills/p2p-project/SKILL.md`
- `.p2p/agent-policy.yml`
- MCP tool `p2p_agent_instructions_refresh`

The implementation must evolve this into:

- default init installs all built-in project-local adapters;
- `generic` baseline is always present and cannot be removed;
- `.p2p/agent-integrations.yml` records managed generated files;
- file hashes and drift detection protect user edits;
- CLI exposes `p2p agent list/show/install/update/doctor/uninstall`;
- MCP exposes equivalent read/write-safe lifecycle tools;
- generated instructions include the readiness gap handling method behavior.

## Phase 0 - Baseline Checks

- Run current test suite before edits.
- Record current behavior for:
  - `p2p init --agent generic`
  - `p2p init --agent codex`
  - `p2p init --agent claude`
  - `p2p init --agent all`
  - `p2p agent instructions refresh`
- Confirm no unrelated dirty files are touched during implementation.

## Phase 1 - Registry Model

Create a small internal model for agent integrations in
`src/p2p_engine/storage/filesystem.py` or a new focused helper module.

Registry path:

```text
.p2p/agent-integrations.yml
```

MVP fields:

```yaml
schema_version: 1
baseline_profile: generic
generated_at: "..."
adapters:
  codex:
    status: installed
    maturity: stable
    template_version: agent-template-v1
    capabilities: {}
    files:
      - path: AGENTS.md
        shared: true
        owner: generic
        managed: true
        template_id: generic-agents-md-v1
        sha256: "..."
        drift: clean
```

Tasks:

- Add constants for built-in adapters:
  - `generic`
  - `codex`
  - `claude`
  - `cursor`
  - `copilot`
  - `gemini`
  - `opencode`
- Add adapter file matrix.
- Add SHA-256 helper over exact file bytes.
- Add registry read/write helpers.
- Add drift classifier:
  - `clean`
  - `missing`
  - `drifted`
  - `unmanaged`
- Add migration helper for existing generated files.

Tests:

- Registry is created on init.
- Registry rejects active/default/current/use/switch state.
- Hashes are exact-byte hashes.
- Drift changes when a managed file is manually edited.

## Phase 2 - Template Rendering

Move generated agent file content behind adapter templates/renderers.

MVP file matrix:

```text
generic   -> AGENTS.md, .p2p/agent-policy.yml
codex     -> AGENTS.md, .agents/skills/p2p-project/SKILL.md, optional legacy .codex/skills/p2p-project/SKILL.md
claude    -> AGENTS.md, CLAUDE.md
cursor    -> AGENTS.md, .cursor/rules/p2p.mdc
copilot   -> AGENTS.md, .github/copilot-instructions.md
gemini    -> AGENTS.md, GEMINI.md
opencode  -> AGENTS.md
```

Tasks:

- Preserve current `AGENTS.md` behavior.
- Add readiness gap handling block to generic baseline.
- Add generated managed header where practical.
- Add Cursor `.cursor/rules/p2p.mdc`.
- Add Copilot `.github/copilot-instructions.md`.
- Add Gemini `GEMINI.md`.
- Keep OpenCode MVP to shared `AGENTS.md`.
- Decide whether `.agents/skills/p2p-project/SKILL.md` can be fully agent-neutral.
- Preserve `.codex/skills/p2p-project/SKILL.md` compatibility if needed.

Tests:

- Snapshot-style assertions for each generated adapter file.
- All generated files preserve the readiness gap handling behavior.
- Copilot file contains actual P2P rules, not only a pointer.
- `.cursorrules` is not generated.
- `opencode.json` is not generated.

## Phase 3 - Init Behavior

Change `p2p init` default behavior.

Current:

```text
--agent default = generic
```

Target:

```text
p2p init "Project"          -> generic + all built-in adapters
p2p init "Project" --agent codex
                            -> generic + codex
p2p init "Project" --agent codex --agent claude
                            -> generic + codex + claude
```

Tasks:

- Update CLI option to accept repeated `--agent`.
- Update prompt choices to include all built-in adapters.
- Ensure narrowed init always includes `generic`.
- Ensure default init means all built-in adapters.
- Update init next-step output.
- Maintain backwards compatibility for `--agent all`.

Tests:

- Default init installs all adapters.
- Narrowed init includes generic.
- `--agent all` still works.
- Invalid adapter names fail clearly.

## Phase 4 - CLI Lifecycle Commands

Add top-level `p2p agent` lifecycle commands while keeping
`p2p agent instructions refresh` compatible.

Commands:

```bash
p2p agent list
p2p agent show <agent>
p2p agent install <agent|all>
p2p agent update <agent|all>
p2p agent doctor <agent|all>
p2p agent uninstall <agent>
```

Tasks:

- Keep existing runtime `p2p agent doctor` behavior or merge it carefully with
  integration doctor output.
- Decide whether runtime doctor should remain available as a mode/section.
- Add `list` output with supported/installed/drift status.
- Add `show` output with adapter capabilities and managed files.
- Add `install` with conflict checks.
- Add `update` that refuses drifted overwrites unless explicit force is added.
- Add `uninstall` that refuses `generic` and removes only clean non-shared files.

Tests:

- `list` shows all supported adapters.
- `show codex` includes files and drift state.
- `install all` rejects non-shared path conflicts.
- `update` preserves drifted files.
- `uninstall generic` fails.
- `uninstall cursor` removes only cursor-owned clean files.

## Phase 5 - Validation

Extend validation to inspect `.p2p/agent-integrations.yml`.

Checks:

- schema version is supported;
- baseline profile is `generic`;
- adapters are known;
- file records have required fields;
- hashes are valid hex SHA-256 strings;
- no active/default/current/use/switch state exists;
- shared file ownership is coherent;
- generic baseline exists when registry exists.

Tests:

- malformed registry produces validation errors or warnings as appropriate;
- valid registry passes.

## Phase 6 - MCP Parity

Add MCP tools over the same core behavior.

Read tools:

```text
p2p_agent_list
p2p_agent_show
```

Write-safe tools:

```text
p2p_agent_install
p2p_agent_update
p2p_agent_uninstall
```

Tasks:

- Add tool definitions in `src/p2p_engine/mcp/tools.py`.
- Call shared workspace methods, not separate file logic.
- Return structured JSON with registry and file status.
- Preserve drift/conflict/uninstall safety.

Tests:

- MCP tool definitions include the new tools.
- MCP install/update/uninstall matches CLI behavior.
- MCP does not bypass drift checks.

## Phase 7 - Documentation

Update docs:

- `README.md`
- `docs/INSTALL.md` if relevant
- `docs/MCP.md` if relevant
- release/how-to docs only if command surface affects release workflow

Document:

- default init installs all adapters;
- narrowed init examples;
- no default/active agent;
- registry and drift model;
- safe uninstall;
- CLI/MCP distinction;
- readiness gap handling behavior in generated instructions.

## Phase 8 - Verification

Run:

```bash
.venv/bin/python -m pytest
.venv/bin/p2p validate
.venv/bin/p2p agent list
.venv/bin/p2p agent doctor all
```

Also test in a temp project:

```bash
.venv/bin/p2p init "Agent Demo" --root /tmp/p2p-agent-demo
.venv/bin/p2p agent list --root /tmp/p2p-agent-demo
.venv/bin/p2p agent show codex --root /tmp/p2p-agent-demo
.venv/bin/p2p agent update all --root /tmp/p2p-agent-demo
.venv/bin/p2p agent uninstall cursor --root /tmp/p2p-agent-demo
```

## Open Coding Decisions

- Whether to implement adapter templates as package data files immediately or
  keep renderer functions for the first slice while preserving the public
  behavior.
- Whether `.agents/skills/p2p-project/SKILL.md` is safe enough as a shared
  agent-neutral skill in the first implementation.
- Whether `p2p agent doctor` should combine runtime doctor and integration
  doctor, or whether runtime doctor should move to a separate subcommand later.

