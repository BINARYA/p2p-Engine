# P2PWorkspace Facade Final Reassessment Design

## Scope

The reassessment reviews the runtime structure that remains after the modular
refactoring sequence reached helper consolidation step 55.

The audit covers:

- `storage/filesystem.py` as the `P2PWorkspace` compatibility facade and service
  composition root.
- `cli.py` as the Typer application root and bootstrap command holder.
- `cli_commands/*` as command presentation modules.
- `mcp/tools.py` as the MCP dispatch facade.
- `mcp/registry.py` as the MCP tool catalog and schema module.
- `mcp/handlers/*` as MCP execution handlers.

## Current Measurements

Current largest Python modules under `src/p2p_engine`:

| Module | Lines | Assessment |
| --- | ---: | --- |
| `storage/filesystem.py` | 1,276 | Large but now mostly compatibility facade and service composition. |
| `mcp/registry.py` | 1,075 | Large schema/catalog module; strongest remaining extraction candidate. |
| `services/work_branches.py` | 932 | Domain service with complex managed Work branch lifecycle. |
| `services/proposal_branches.py` | 931 | Domain service with complex managed proposal branch lifecycle. |
| `cli_commands/proposals.py` | 616 | Presentation module for a large command family. |
| `mcp/handlers/collaboration.py` | 566 | MCP handler for sync/proposal collaboration flows. |
| `services/spec_export.py` | 560 | Domain export service. |
| `cli_commands/collaboration.py` | 537 | Presentation module for governance/collaboration commands. |
| `cli_commands/work_specs.py` | 535 | Presentation module for Change Set, spec, and Work commands. |
| `services/readiness.py` | 525 | Domain readiness service. |
| `cli.py` | 318 | Application root and init command; no longer a command monolith. |
| `mcp/tools.py` | 15 | Dispatch facade only. |

## Findings

### `storage.filesystem`

`P2PWorkspace` remains large because it is the public compatibility facade and
service composition root. The post-refactor shape is acceptable for now:

- service construction is centralized;
- public methods delegate to cohesive services;
- local dataclasses have been removed;
- duplicated YAML/path/slug helpers have moved to `foundation.files`;
- only facade-local duplicate proposal ID message formatting remains as a
  module-level helper.

Further reduction would require a deliberate facade partitioning strategy. That
would be higher risk because tests, CLI, MCP, and downstream callers still use
`P2PWorkspace` as a stable public API.

### `cli.py` and CLI Command Modules

`cli.py` now owns Typer app assembly and the interactive `init` command. This is
an acceptable application-root responsibility.

The largest CLI command modules are still sizable, but they are presentation
modules rather than domain services. They should not be split only by size. A
future split is justified when a command family has repeated output rendering,
JSON transformation, or error handling that can move to a dedicated renderer.

### MCP Tools and Registry

`mcp/tools.py` is already minimal dispatch glue. Runtime execution has been
split into handlers.

`mcp/registry.py` is the strongest remaining concentration. It combines:

- global `TOOL_NAMES`;
- prompt tool generation;
- all tool definition dictionaries;
- JSON schema helper usage.

This is not domain logic, but it is compatibility-sensitive API surface. The
next focused runtime refactor should split MCP tool definitions by domain while
preserving the exact exported tool list and schemas.

### MCP Handlers

Handlers are already separated by operational area. `mcp/handlers/collaboration.py`
is still large because collaboration flows require permission/consent and branch
lifecycle orchestration. It should remain intact until registry/schema
definitions are split; handler changes carry more behavioral risk.

## Decision

Do not start another `P2PWorkspace` extraction immediately. The next recommended
feature is a focused MCP registry catalog split:

- move tool definition groups into domain modules;
- keep `mcp.registry.tool_definitions()` and `TOOL_NAMES` as stable public
  compatibility exports;
- add or preserve tests proving the tool names, schemas, and required fields do
  not change.

`storage.filesystem` should remain the compatibility facade for now.
