# Tasks - Agent Integration Registry

- [x] T001: Implement R001 default all-agent init; completion evidenced by
  `src/p2p_engine/cli.py:161`, `src/p2p_engine/cli.py:231`,
  `src/p2p_engine/services/agent_templates.py:15`,
  `src/p2p_engine/services/agent_templates.py:42`,
  `src/p2p_engine/services/agent_instructions.py:338`, and
  `tests/test_cli.py:1078`.
- [x] T002: Implement R002 narrowed init with generic baseline; completion
  evidenced by `src/p2p_engine/services/agent_templates.py:42`,
  `src/p2p_engine/services/agent_instructions.py:338`, and
  `tests/test_cli.py:1114`.
- [x] T003: Implement R003 integration registry writes; completion evidenced by
  `src/p2p_engine/services/agent_instructions.py:301`,
  `src/p2p_engine/services/agent_instructions.py:304`,
  `src/p2p_engine/services/agent_instructions.py:338`, and
  `tests/test_cli.py:1078`.
- [x] T004: Implement R004 drift-safe update/uninstall; completion evidenced by
  `src/p2p_engine/services/agent_instructions.py:144`,
  `src/p2p_engine/services/agent_instructions.py:242`,
  `tests/test_agent_instructions_service.py:57`, and
  `tests/test_cli.py:1125`.
- [x] T005: Implement R005 agent CLI management commands; completion evidenced
  by `src/p2p_engine/cli_commands/agents.py:12`,
  `src/p2p_engine/cli_commands/agents.py:51`,
  `src/p2p_engine/cli_commands/agents.py:64`,
  `src/p2p_engine/cli_commands/agents.py:84`,
  `src/p2p_engine/cli_commands/agents.py:97`,
  `src/p2p_engine/cli_commands/agents.py:110`,
  `src/p2p_engine/cli_commands/doctor.py:25`, and
  `tests/test_cli.py:1125`.
- [x] T006: Implement R006 MCP agent lifecycle tools; completion evidenced by
  `src/p2p_engine/mcp/catalog/agents.py:9`,
  `src/p2p_engine/mcp/catalog/agents.py:27`,
  `src/p2p_engine/mcp/catalog/agents.py:35`,
  `src/p2p_engine/mcp/catalog/agents.py:52`,
  `src/p2p_engine/mcp/catalog/agents.py:71`,
  `src/p2p_engine/mcp/catalog/agents.py:90`,
  `src/p2p_engine/mcp/handlers/project.py:15`,
  `src/p2p_engine/mcp/handlers/maintenance.py:33`, and
  `tests/test_mcp.py:1194`.
