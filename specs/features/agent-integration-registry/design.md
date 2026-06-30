# Design - Agent Integration Registry

## Requirements Covered

- R001, R002, R003, R004, R005, R006

## Key Decisions

- D001: Generic is the mandatory baseline adapter.
  Rationale: every agent profile inherits common P2P governance boundaries.

- D002: File drift makes updates conservative by default.
  Rationale: generated files may be edited by humans and must not be overwritten
  silently.

- D003: MCP exposes the same safe lifecycle operations as structured tools.
  Rationale: compatible agents should not parse CLI text or edit files directly.

## Components

- `src/p2p_engine/services/agent_templates.py`
  - Adapter ids, profile normalization, generated instruction files, adapter
    file maps, and template ownership metadata.
- `src/p2p_engine/services/agent_instructions.py`
  - Registry construction, adapter lifecycle operations, drift detection,
    safe uninstall, and list/show service views.
- `src/p2p_engine/storage/filesystem.py`
  - `P2PWorkspace` compatibility facade delegating agent behavior to
    `AgentInstructionService`.
- `src/p2p_engine/cli.py`
  - Init command defaulting to all built-in adapters when no agent is narrowed.
- `src/p2p_engine/cli_commands/agents.py`
  - `agent list`, `agent show`, `agent install`, `agent update`,
    `agent uninstall`, and `agent instructions refresh`.
- `src/p2p_engine/cli_commands/doctor.py`
  - Current `agent doctor` presentation surface.
- `src/p2p_engine/mcp/catalog/agents.py`
  - `p2p_agent_*` tool definitions.
- `src/p2p_engine/mcp/handlers/project.py`
  - Read-only MCP agent list/show dispatch.
- `src/p2p_engine/mcp/handlers/maintenance.py`
  - Write-safe MCP init, refresh, install, update, and uninstall dispatch.
- `tests/test_agent_instructions_service.py`, `tests/test_cli.py`,
  `tests/test_mcp.py`, `tests/test_mcp_maintenance_handler.py`
  - Service, CLI, MCP, init, registry, drift, and lifecycle coverage.

## Evidence

- Adapter registry and templates:
  `src/p2p_engine/services/agent_templates.py:15`,
  `src/p2p_engine/services/agent_templates.py:19`,
  `src/p2p_engine/services/agent_templates.py:42`,
  `src/p2p_engine/services/agent_templates.py:154`,
  `src/p2p_engine/services/agent_templates.py:188`.
- Agent lifecycle service:
  `src/p2p_engine/services/agent_instructions.py:33`,
  `src/p2p_engine/services/agent_instructions.py:67`,
  `src/p2p_engine/services/agent_instructions.py:144`,
  `src/p2p_engine/services/agent_instructions.py:242`,
  `src/p2p_engine/services/agent_instructions.py:338`,
  `src/p2p_engine/services/agent_instructions.py:372`.
- CLI and doctor surfaces:
  `src/p2p_engine/cli.py:161`, `src/p2p_engine/cli.py:231`,
  `src/p2p_engine/cli_commands/agents.py:12`,
  `src/p2p_engine/cli_commands/agents.py:51`,
  `src/p2p_engine/cli_commands/agents.py:64`,
  `src/p2p_engine/cli_commands/agents.py:84`,
  `src/p2p_engine/cli_commands/agents.py:97`,
  `src/p2p_engine/cli_commands/agents.py:110`,
  `src/p2p_engine/cli_commands/doctor.py:16`,
  `src/p2p_engine/cli_commands/doctor.py:25`.
- MCP definitions and handlers:
  `src/p2p_engine/mcp/catalog/agents.py:9`,
  `src/p2p_engine/mcp/catalog/agents.py:27`,
  `src/p2p_engine/mcp/catalog/agents.py:35`,
  `src/p2p_engine/mcp/catalog/agents.py:52`,
  `src/p2p_engine/mcp/catalog/agents.py:71`,
  `src/p2p_engine/mcp/catalog/agents.py:90`,
  `src/p2p_engine/mcp/handlers/project.py:15`,
  `src/p2p_engine/mcp/handlers/project.py:17`,
  `src/p2p_engine/mcp/handlers/maintenance.py:14`,
  `src/p2p_engine/mcp/handlers/maintenance.py:26`,
  `src/p2p_engine/mcp/handlers/maintenance.py:33`,
  `src/p2p_engine/mcp/handlers/maintenance.py:42`,
  `src/p2p_engine/mcp/handlers/maintenance.py:51`.
- Tests:
  `tests/test_agent_instructions_service.py:8`,
  `tests/test_agent_instructions_service.py:39`,
  `tests/test_agent_instructions_service.py:57`,
  `tests/test_agent_instructions_service.py:73`,
  `tests/test_cli.py:1078`,
  `tests/test_cli.py:1114`,
  `tests/test_cli.py:1125`,
  `tests/test_cli.py:1153`,
  `tests/test_mcp.py:1194`.

## Risks

- Generated instruction templates are product behavior; future local-only
  development rules must not leak into released templates unless intentionally
  accepted.
