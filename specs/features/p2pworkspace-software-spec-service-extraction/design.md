# P2PWorkspace Software Spec Service Extraction Design

## Decisions

### D001 - Native Spec First, Export Later

Extract `.p2p/outputs/software-spec` behavior first and leave downstream export
targets in place.

Rationale: export rendering depends on project-definition synthesis and should
be extracted in the next dedicated feature.

### D002 - Callback Dependencies

`SoftwareSpecService` receives callbacks for Change Set lookup, proposal lookup,
and proposal directory lookup.

Rationale: this avoids passing the whole `P2PWorkspace` into the service while
preserving existing source-of-truth behavior.

## Components

### `src/p2p_engine/services/software_spec.py`

Owns:

- required software-spec files;
- refresh generation;
- status listing;
- show;
- refinement prompt;
- import validation/copy;
- software-spec native renderers.

Does not own:

- generic/OpenSpec/Spec Kit export files;
- project definition synthesis;
- Work planning;
- CLI/MCP presentation.

### `src/p2p_engine/storage/filesystem.py`

Keeps the public facade and delegates:

- `refresh_software_spec`
- `software_spec_statuses`
- `show_software_spec`
- `create_software_spec_prompt`
- `import_software_spec`

## Verification Commands

```bash
.venv/bin/pytest tests/test_software_spec_service.py
.venv/bin/pytest tests/test_cli.py::test_cli_software_spec_refresh_prompt_import_status_and_show
.venv/bin/pytest tests/test_mcp.py::test_mcp_write_safe_spec_export_and_work_flow
.venv/bin/p2p validate
.venv/bin/pytest
```

## Implementation Evidence

### Source Changes

Added service module:

- `src/p2p_engine/services/software_spec.py`

Updated facade:

- `src/p2p_engine/storage/filesystem.py`

Added focused tests:

- `tests/test_software_spec_service.py`

Updated local feature specs:

- `specs/features/p2pworkspace-software-spec-service-extraction/`

### Facade Methods Delegated

`P2PWorkspace` now constructs `SoftwareSpecService` lazily and delegates:

- `refresh_software_spec`
- `software_spec_statuses`
- `show_software_spec`
- `create_software_spec_prompt`
- `import_software_spec`

### Behavior Moved

Moved behind `SoftwareSpecService`:

- required native software-spec artifact list;
- software-spec refresh file generation;
- software-spec status listing;
- software-spec show;
- software-spec refinement prompt generation;
- software-spec import validation and copy behavior;
- native software-spec renderers for index, requirements, design, commands,
  data model, acceptance, and refinement prompt.

### Behavior Left In Place

The following remain in `P2PWorkspace` for later extraction:

- `export_software_spec`
- `software_spec_export_statuses`
- `show_software_spec_export`
- `validate_software_spec_export`
- project-definition synthesis;
- generic/OpenSpec/Spec Kit renderers;
- Work planning.

### Compatibility Corrections

Focused tests were corrected to match existing behavior:

- proposal acceptance is represented by `record_decision(..., DecisionOutcome.accepted, ...)`;
- software-spec import YAML validation checks for top-level key presence, not
  the type of the value under that key.

### Verification Commands

```bash
.venv/bin/pytest tests/test_software_spec_service.py
# 2 passed

.venv/bin/pytest tests/test_cli.py::test_cli_software_spec_refresh_prompt_import_status_and_show tests/test_mcp.py::test_mcp_write_safe_spec_export_and_work_flow
# 2 passed

.venv/bin/p2p validate
# errors: 0, warnings: 0, infos: 0

.venv/bin/pytest
# 167 passed
```

### Remaining Gaps

No behavior gap is known for this feature after focused, mapped compatibility,
P2P validation, and full-suite verification.

The next extraction should be project-definition/spec-export behavior.
