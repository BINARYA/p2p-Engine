# P2PWorkspace Agent Integration Facade Cleanup Design

## Current State

`AgentInstructionService` owns agent integration registry behavior, but
`P2PWorkspace` still exposes private methods such as
`_agent_integrations_path`, `_agent_integrations_registry`,
`_write_agent_integrations_registry`, `_agent_registry_file_map`,
`_build_agent_integrations_registry`, and `_agent_integration_status`.

Most of these wrappers are no longer used outside the facade. The only active
internal dependency is validation, which asks `P2PWorkspace` for the registry
path.

## Target State

- Keep public workspace methods:
  - `agent_integrations_list`
  - `agent_integration_show`
  - `install_agent_integrations`
  - `uninstall_agent_integration`
- Wire `ValidationService.agent_integrations_path` to
  `self._agent_instruction_service().path`.
- Remove private wrapper methods that only forward to `AgentInstructionService`.

## Compatibility

The service remains the owner of registry reads, writes, drift detection, file
maps, and status rendering. External callers continue to use public workspace,
CLI, or MCP entry points.
