# P2PWorkspace Project Initialization Service Extraction Design

## Current Runtime Shape

`P2PWorkspace.init_project()` still assembles the core `.p2p` workspace and
root-level agent instruction files directly in `storage/filesystem.py`.

It coordinates existing extracted behavior:

- remote profile default payload;
- readiness profile default payload;
- domain and rubric payloads;
- permissions policy default payload;
- agent instruction refresh.

## Target Shape

Add `src/p2p_engine/services/project_initialization.py` with:

- `ProjectInitializationService`;
- local `slugify` and YAML dump helpers;
- deterministic bootstrap file assembly;
- idempotent write/created-path behavior;
- directory creation for proposals/prompts;
- final delegation to the agent instruction refresh callback.

`P2PWorkspace.init_project()` remains the compatibility facade and delegates to
the service.

## Service Dependencies

The service receives:

- `root`;
- `p2p_dir`;
- `normalize_agent_profile`;
- `normalize_repository_mode`;
- `normalize_project_domain`;
- `remote_profile_default_payload`;
- `readiness_default_profile_payload`;
- `permissions_default_policy_payload`;
- `domain_state_payload`;
- `domain_setup_next_actions_payload`;
- `rubrics_payload`;
- `project_domain_templates`;
- `refresh_agent_instructions`.

The service writes files directly because bootstrap is the write boundary being
extracted.

## Compatibility Rules

- Preserve exact relative paths.
- Preserve payload shape and YAML dump style.
- Preserve idempotency: existing files are not overwritten by bootstrap.
- Preserve agent instruction refresh behavior by calling the facade callback.
- Keep CLI/MCP formatting outside the service.

## Verification Map

```bash
.venv/bin/pytest tests/test_project_initialization_service.py
.venv/bin/pytest tests/test_cli.py -k "init or wizard"
.venv/bin/pytest tests/test_mcp.py -k "init_project or custom_domain or agent"
.venv/bin/pytest tests/test_mcp_maintenance_handler.py
.venv/bin/pytest tests/test_skeleton.py
.venv/bin/p2p validate
.venv/bin/pytest
```

## Implementation Evidence

Implemented in `src/p2p_engine/services/project_initialization.py`.

`P2PWorkspace.init_project()` now delegates to a lazy
`ProjectInitializationService` factory. The compatibility facade still exposes
the same public method signature and return type.

Verification completed:

```bash
.venv/bin/pytest tests/test_project_initialization_service.py
.venv/bin/pytest tests/test_cli.py -k "init or wizard"
.venv/bin/pytest tests/test_mcp.py -k "init_project or custom_domain or agent" tests/test_mcp_maintenance_handler.py
.venv/bin/pytest tests/test_skeleton.py
.venv/bin/p2p validate
.venv/bin/pytest
```

Result: focused tests passed, validation reported 0 findings, and the full
suite passed with 335 tests.
