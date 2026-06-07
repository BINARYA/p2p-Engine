# P2PWorkspace Agent Instructions Service Extraction Design

## Current Runtime Shape

`storage/filesystem.py` still owns agent-related behavior:

- agent profile normalization and expansion;
- instruction file generation;
- agent policy generation;
- agent integration registry generation;
- list/show/install/update/uninstall orchestration;
- template text for AGENTS, Codex, Claude, Cursor, Copilot, Gemini, and
  compatible shared skill files.

The behavior is consumed by:

- `init_project()`;
- CLI `agent instructions refresh`, `agent list/show/install/update/uninstall`;
- MCP `p2p_agent_*` maintenance/project tools;
- `doctor` output for agent integration status.

## Target Shape

Add `src/p2p_engine/services/agent_instructions.py` with:

- `AgentInstructionsResult`;
- `AgentIntegrationResult`;
- `AgentInstructionService`;
- refresh/list/show/install/update/uninstall orchestration;
- agent integration registry helpers and drift helpers.

`P2PWorkspace` remains the compatibility facade and delegates public agent
methods to the service. `init_project()` continues to call
`refresh_agent_instructions()` through the facade.

Template renderers remain callback dependencies in `filesystem.py` for this
slice. That keeps generated text exactly stable and leaves a smaller future
slice available for template relocation.

## Service Dependencies

The service receives:

- `root`;
- `p2p_dir`;
- `project_name`;
- `repository_mode`;
- `set_repository_mode`.
- template and policy renderer callbacks;
- adapter normalization/expansion callbacks.

The service directly reads/writes instruction files, `.p2p/agent-policy.yml`,
and `.p2p/agent-integrations.yml`.

## Compatibility Rules

- Keep generated file paths and template IDs unchanged.
- Keep registry payload fields unchanged.
- Keep drift detection semantics unchanged.
- Keep `generic` installed as baseline and non-uninstallable.
- Keep relative return paths unchanged.
- Keep CLI/MCP formatting outside the service.

## Verification Map

```bash
.venv/bin/pytest tests/test_agent_instructions_service.py
.venv/bin/pytest tests/test_cli.py -k "agent or wizard"
.venv/bin/pytest tests/test_mcp.py -k "agent"
.venv/bin/pytest tests/test_mcp_maintenance_handler.py
.venv/bin/p2p validate
.venv/bin/pytest
```

## Implementation Evidence

Implemented in:

- `src/p2p_engine/services/agent_instructions.py`;
- `src/p2p_engine/storage/filesystem.py` facade wiring;
- `tests/test_agent_instructions_service.py`;
- `specs/features/p2pworkspace-agent-instructions-service-extraction/tasks.md`.

Verification:

```bash
.venv/bin/pytest tests/test_agent_instructions_service.py tests/test_cli.py -k "agent or wizard"
# 13 passed, 84 deselected

.venv/bin/pytest tests/test_mcp.py -k agent tests/test_mcp_maintenance_handler.py
# 3 passed, 45 deselected

.venv/bin/p2p validate
# errors: 0, warnings: 0, infos: 0, findings: none

.venv/bin/pytest
# 330 passed
```

Note: the service extraction intentionally left long template text renderers in
`filesystem.py` as compatibility callbacks. Runtime orchestration, registry
building, drift handling, install/update/uninstall, and list/show behavior now
live in `services.agent_instructions`.
