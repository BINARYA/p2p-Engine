# P2PWorkspace Registry Service Extraction Design

## Design

Create `src/p2p_engine/services/registries.py`.

The service owns:

- registry filename/key/source mapping;
- registry file writes;
- registry status checks;
- registry show/read behavior;
- `RegistryStatus` and `RegistryView` compatible dataclasses.

`P2PWorkspace` delegates:

- `refresh_registries`
- `registry_status`
- `show_registry`

The service receives callbacks for:

- duplicate proposal id lookup;
- duplicate proposal id error formatting;
- proposal registry records;
- change registry records;
- decision registry records;
- choice registry records;
- relation registry records;
- artifact registry records;
- readiness registry records.

## Out Of Scope

The service must not own:

- proposal/change/choice/readiness record construction;
- project-state refresh or assessment;
- context packet generation;
- intake context generation;
- CLI/MCP formatting;
- Git/sync/branch/work lifecycle behavior.

## Compatibility Surface

The following must remain compatible:

- files:
  - `proposals.yml`
  - `decisions.yml`
  - `changes.yml`
  - `choices.yml`
  - `relations.yml`
  - `artifacts.yml`
  - `readiness.yml`
- top-level list keys matching registry names;
- `source` strings currently written by `refresh_registries`;
- status fields: `registries_dir`, `files`, `proposals_count`,
  `changes_count`, `stale`;
- supported `show_registry` names and errors.

## Verification

```bash
.venv/bin/pytest tests/test_registry_service.py
.venv/bin/pytest tests/test_cli.py::test_cli_registry_refresh_status_and_show tests/test_cli.py::test_cli_registry_refresh_rejects_duplicate_proposal_ids tests/test_mcp.py::test_mcp_registry_refresh_tool tests/test_mcp.py::test_mcp_change_project_registry_and_remote_read_tools
.venv/bin/p2p validate
.venv/bin/pytest
```

## Current Status

Implemented.

## Implementation Evidence

Runtime code:

- `src/p2p_engine/services/registries.py` owns registry filename/key/source
  mapping, registry file writes, registry status checks, stale detection, and
  registry show/read validation.
- `src/p2p_engine/storage/filesystem.py` keeps `P2PWorkspace` as the public
  facade and delegates `refresh_registries`, `registry_status`, and
  `show_registry` to `RegistryService`.
- `tests/test_registry_service.py` covers the extracted service and facade
  delegation.

Compatibility and boundary checks:

- Registry record builders for proposals, decisions, changes, choices,
  relations, artifacts, and readiness remain in `P2PWorkspace` for this slice.
- Project-state refresh/assessment, context packet generation, intake context,
  CLI formatting, MCP formatting, Git/sync, and lifecycle behavior remain
  outside the service.
- The service has no Typer, Rich, MCP, JSON-RPC, Git, sync, project-state,
  assessment, context, intake, branch, Work, proposal-branch, or Change Set
  lifecycle imports.

Executed verification:

```bash
.venv/bin/pytest tests/test_registry_service.py
# 4 passed

.venv/bin/pytest tests/test_cli.py::test_cli_registry_refresh_status_and_show tests/test_cli.py::test_cli_registry_refresh_rejects_duplicate_proposal_ids tests/test_mcp.py::test_mcp_registry_refresh_tool tests/test_mcp.py::test_mcp_change_project_registry_and_remote_read_tools
# 4 passed

.venv/bin/p2p validate
# errors: 0, warnings: 0, infos: 0, findings: none

.venv/bin/pytest
# 184 passed
```
