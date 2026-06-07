# P2PWorkspace Readiness Service Extraction Design

## Design

Create `src/p2p_engine/services/readiness.py`.

The service owns:

- default readiness profile payload;
- readiness profile validation and mapping;
- readiness assessment validation and mapping;
- proposal readiness read/write;
- owner override metadata;
- refresh/scoring computation;
- initial assessment bootstrap from proposal artifacts.

`P2PWorkspace` delegates:

- `readiness_profile`
- `read_proposal_readiness`
- `write_proposal_readiness`
- `record_proposal_readiness_override`
- `refresh_proposal_readiness`
- `initialize_proposal_readiness`

Out of scope:

- CLI/MCP formatting;
- proposal accept/reject/defer decisions;
- next-action orchestration;
- registry generation.

## Verification

```bash
.venv/bin/pytest tests/test_readiness_service.py
.venv/bin/pytest tests/test_skeleton.py::test_init_project_creates_default_readiness_profile tests/test_skeleton.py::test_missing_proposal_readiness_is_not_assessed tests/test_skeleton.py::test_write_and_read_proposal_readiness_assessment tests/test_skeleton.py::test_refresh_proposal_readiness_computes_score_with_artifact_caps tests/test_cli.py::test_cli_proposal_readiness_status_refresh_and_explain tests/test_cli.py::test_cli_proposal_accept_can_record_readiness_override tests/test_mcp.py::test_mcp_proposal_readiness_tools_are_advisory
.venv/bin/p2p validate
.venv/bin/pytest
```

## Current Status

Implemented.

## Implementation Evidence

Runtime code:

- `src/p2p_engine/services/readiness.py` owns readiness profile payloads,
  validation, assessment mapping, proposal readiness read/write, override,
  refresh/scoring, and initialization from proposal artifacts.
- `src/p2p_engine/storage/filesystem.py` keeps the `P2PWorkspace` public facade
  and delegates readiness operations to `ReadinessService`.
- `tests/test_readiness_service.py` covers the extracted service directly.

Compatibility and boundary checks:

- Readiness YAML paths and payload shapes are preserved.
- CLI/MCP presentation remains outside the service.
- Proposal acceptance/rejection/defer decisions, Git branch behavior, registry
  generation, and next-action orchestration remain outside the service.
- The service has no Typer, Rich, MCP, Git, branch, or registry imports.

Executed verification:

```bash
.venv/bin/pytest tests/test_readiness_service.py tests/test_skeleton.py::test_init_project_creates_default_readiness_profile tests/test_skeleton.py::test_missing_proposal_readiness_is_not_assessed tests/test_skeleton.py::test_write_and_read_proposal_readiness_assessment tests/test_skeleton.py::test_refresh_proposal_readiness_computes_score_with_artifact_caps tests/test_cli.py::test_cli_proposal_readiness_status_refresh_and_explain tests/test_cli.py::test_cli_proposal_accept_can_record_readiness_override tests/test_mcp.py::test_mcp_proposal_readiness_tools_are_advisory
# 9 passed

.venv/bin/pytest
# 173 passed
```
