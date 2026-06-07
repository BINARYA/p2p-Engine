# P2PWorkspace Agent Template Renderer Extraction Design

## Current Runtime Shape

After `services.agent_instructions` extraction, `storage/filesystem.py` still
contains long agent template renderer helpers and adapter constants. These are
not runtime orchestration anymore, but they keep `filesystem.py` large and make
agent text evolution hard to isolate.

## Target Shape

Add `src/p2p_engine/services/agent_templates.py` with:

- `BUILT_IN_AGENT_ADAPTERS`;
- `AGENT_PROFILES`;
- `READINESS_GAP_HANDLING_BLOCK`;
- `normalize_agent_profile()`;
- `expanded_agent_profiles()`;
- `agent_adapter_capabilities()`;
- `agent_instruction_files()`;
- `agent_adapter_files()`;
- `agent_policy()`;
- private renderer helpers for each generated instruction file.

`P2PWorkspace` imports these functions and passes them to
`AgentInstructionService`. `init_project()` continues to normalize the selected
profile through the imported function.

## Compatibility Rules

- Do not change template strings while moving them.
- Do not change template IDs or file paths.
- Do not change profile aliases or allowed adapters.
- Keep service orchestration in `services.agent_instructions`.
- Keep project bootstrap orchestration in `P2PWorkspace.init_project()` until a
  dedicated initialization extraction exists.

## Verification Map

```bash
.venv/bin/pytest tests/test_agent_instructions_service.py
.venv/bin/pytest tests/test_cli.py -k "agent or wizard"
.venv/bin/pytest tests/test_mcp.py -k agent
.venv/bin/pytest tests/test_mcp_maintenance_handler.py
.venv/bin/p2p validate
.venv/bin/pytest
```

## Implementation Evidence

Implemented in:

- `src/p2p_engine/services/agent_templates.py`;
- `src/p2p_engine/storage/filesystem.py` import wiring;
- `specs/features/p2pworkspace-agent-template-renderer-extraction/tasks.md`.

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
