# P2PWorkspace Project Context Renderer Service Extraction Design

## Current Runtime Shape

`storage/filesystem.py` still owns two context renderers:

- `_intake_context()`;
- `_project_brief_context()`.

They are passed as callbacks into `IntakeLifecycleService` and
`ProjectStateService`.

## Target Shape

Add `src/p2p_engine/services/project_contexts.py` with:

- `ProjectContextRendererService`;
- `render_intake_context()`;
- `render_project_brief_context()`;
- local optional file read helper;
- minimal protocols for registry status, registry view, and intake status.

`P2PWorkspace` wires the renderer service into `IntakeLifecycleService` and
`ProjectStateService`. The old facade helper methods are removed.

## Service Dependencies

The service receives:

- `p2p_dir`;
- `show_registry` callback;
- `intake_statuses` callback.

The service reads project files under `.p2p/project/` but does not mutate state.

## Compatibility Rules

- Preserve existing markdown headings and list formats.
- Preserve missing registry text: `Not generated yet.`
- Preserve empty registry text: `- None.`
- Preserve intake/project brief record limits.
- Preserve source project file inclusion order.

## Verification Map

```bash
.venv/bin/pytest tests/test_project_context_renderer_service.py
.venv/bin/pytest tests/test_project_state_service.py
.venv/bin/pytest tests/test_intake_lifecycle_service.py
.venv/bin/pytest tests/test_cli.py -k "brief or intake"
.venv/bin/pytest tests/test_mcp.py -k "brief or intake"
.venv/bin/p2p validate
.venv/bin/pytest
```

## Implementation Evidence

Implemented in `src/p2p_engine/services/project_contexts.py`.

`P2PWorkspace` now wires `ProjectContextRendererService` into
`IntakeLifecycleService` and `ProjectStateService`. The old
`_intake_context()` and `_project_brief_context()` facade helpers were removed.

Verification completed:

```bash
.venv/bin/pytest tests/test_project_context_renderer_service.py
.venv/bin/pytest tests/test_project_state_service.py
.venv/bin/pytest tests/test_intake_lifecycle_service.py
.venv/bin/pytest tests/test_cli.py -k "brief or intake"
.venv/bin/pytest tests/test_mcp.py -k "brief or intake"
.venv/bin/p2p validate
.venv/bin/pytest
```

Result: focused tests passed, validation reported 0 findings, and the full
suite passed with 354 tests.
