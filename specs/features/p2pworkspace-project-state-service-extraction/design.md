# P2PWorkspace Project State Service Extraction Design

## Design

Create `src/p2p_engine/services/project_state.py`.

The service owns:

- `.p2p/project` directory creation for project state artifacts;
- overview/problem/scope/SWOT/decisions-map writes;
- feature artifact writes for accepted proposals;
- conflicts file bootstrap;
- project state status mapping;
- project state show lookup;
- project brief prompt/context file writes;
- project brief import/show.

`P2PWorkspace` delegates:

- `refresh_project_state`
- `project_state_status`
- `show_project_state`
- `create_project_brief_prompt`
- `import_project_brief`
- `show_project_brief`

The service receives callbacks for behavior that remains outside this slice:

- accepted proposal records;
- project name;
- next actions;
- registry status;
- project brief context generation.

Markdown renderers may be moved into the service if doing so does not create
new coupling; otherwise the facade can pass renderer callbacks in this slice.

## Out Of Scope

The service must not own:

- project assessment computation or persistence;
- definition maturity;
- project rubrics;
- next-action add/complete/retire/refresh behavior;
- registry generation/status/show behavior;
- context packets;
- intake;
- Git/sync;
- CLI/MCP formatting.

## Compatibility Surface

The following must remain compatible:

- `.p2p/project/overview.md`
- `.p2p/project/problem.md`
- `.p2p/project/scope.md`
- `.p2p/project/project-swot.md`
- `.p2p/project/decisions-map.yml`
- `.p2p/project/conflicts.yml`
- `.p2p/project/features/<feature_id>/feature.md`
- `.p2p/project/features/<feature_id>/tasks.yml`
- `.p2p/project/features/<feature_id>/actions.yml`
- `.p2p/project/brief-context.md`
- `.p2p/project/brief.prompt.md`
- `.p2p/project/operational-brief.md`
- `.p2p/project/next-actions.yml`

## Verification

```bash
.venv/bin/pytest tests/test_project_state_service.py
.venv/bin/pytest tests/test_cli.py::test_cli_project_refresh_status_and_show tests/test_cli.py::test_cli_project_brief_prompt_import_and_show tests/test_mcp.py::test_mcp_call_tool_reads_project_state tests/test_mcp.py::test_mcp_project_brief_prompt_and_show
.venv/bin/p2p validate
.venv/bin/pytest
```

## Current Status

Implemented.

## Implementation Evidence

Runtime code:

- `src/p2p_engine/services/project_state.py` owns project refresh artifacts,
  feature artifact writes, project state status/show, project brief prompt,
  project brief import, and project brief show.
- `src/p2p_engine/storage/filesystem.py` keeps `P2PWorkspace` as the public
  facade and delegates project-state methods to `ProjectStateService`.
- `tests/test_project_state_service.py` covers the extracted service and facade
  delegation.

Compatibility and boundary checks:

- Project assessment, definition maturity, rubrics, next-action lifecycle,
  registry generation, context packets, intake, Git/sync, CLI formatting, and
  MCP formatting remain outside the service.
- Project-state markdown renderers and the operational brief prompt renderer
  moved from `filesystem.py` into the service.
- Brief context generation remains in `P2PWorkspace` for this slice because it
  depends on registry views and existing project context formatting.
- The service has no Typer, Rich, MCP, JSON-RPC, Git, sync, assessment,
  maturity, rubrics, context-packet, or lifecycle imports.

Executed verification:

```bash
.venv/bin/pytest tests/test_project_state_service.py
# 4 passed

.venv/bin/pytest tests/test_cli.py::test_cli_project_refresh_status_and_show tests/test_cli.py::test_cli_project_brief_prompt_import_and_show tests/test_mcp.py::test_mcp_call_tool_reads_project_state tests/test_mcp.py::test_mcp_project_brief_prompt_and_show
# 4 passed

.venv/bin/p2p validate
# errors: 0, warnings: 0, infos: 0, findings: none

.venv/bin/pytest
# 188 passed
```
