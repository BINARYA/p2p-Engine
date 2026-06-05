# P2PWorkspace Project Definition And Spec Export Extraction Design

## Design

Create `src/p2p_engine/services/spec_export.py`.

The service owns:

- generic/OpenSpec/Spec Kit export target list;
- export file generation;
- export status listing;
- export show;
- export validation;
- project definition synthesis from accepted proposals, draft proposals,
  project metadata, governance docs, rubrics, assessment, maturity, and
  software-spec artifacts.

`P2PWorkspace` delegates:

- `export_software_spec`
- `software_spec_export_statuses`
- `show_software_spec_export`
- `validate_software_spec_export`
- `_project_definition`

Work planning remains outside the service and continues to call
`validate_software_spec_export`.

## Verification

```bash
.venv/bin/pytest tests/test_spec_export_service.py
.venv/bin/pytest tests/test_cli.py::test_cli_software_spec_refresh_prompt_import_status_and_show
.venv/bin/pytest tests/test_mcp.py::test_mcp_write_safe_spec_export_and_work_flow
.venv/bin/p2p validate
.venv/bin/pytest
```

## Implementation Evidence

### Source Changes

Added service module:

- `src/p2p_engine/services/spec_export.py`

Updated facade:

- `src/p2p_engine/storage/filesystem.py`

Added focused tests:

- `tests/test_spec_export_service.py`

Updated local feature specs:

- `specs/features/p2pworkspace-project-definition-and-spec-export-extraction/`

### Facade Methods Delegated

`P2PWorkspace` now constructs `SpecExportService` lazily and delegates:

- `export_software_spec`
- `software_spec_export_statuses`
- `show_software_spec_export`
- `validate_software_spec_export`
- `_project_definition`

### Behavior Moved

Moved behind `SpecExportService`:

- export target validation workflow;
- software-spec artifact precondition checks;
- export directory replacement and file write workflow;
- export status listing;
- export show file selection workflow;
- export validation workflow;
- project definition data synthesis.

### Behavior Left In Place

For risk control, renderer functions and required-file helper functions remain
in `filesystem.py` and are passed as explicit callbacks to the service:

- `_software_spec_export_files`
- `_software_spec_export_required_files`
- `_software_spec_export_show_file`
- `_project_definition_required_sections`
- generic/OpenSpec/Spec Kit markdown renderers

Work planning remains outside the service and continues to call
`validate_software_spec_export` through the facade.

### Verification Commands

```bash
.venv/bin/pytest tests/test_spec_export_service.py
# 2 passed

.venv/bin/pytest tests/test_cli.py::test_cli_software_spec_refresh_prompt_import_status_and_show tests/test_mcp.py::test_mcp_write_safe_spec_export_and_work_flow
# 2 passed

.venv/bin/p2p validate
# errors: 0, warnings: 0, infos: 0

.venv/bin/pytest
# 169 passed
```

### Remaining Gaps

No behavior gap is known after focused, mapped compatibility, P2P validation,
and full-suite verification.

Follow-up cleanup:

- move renderer functions from `filesystem.py` into `SpecExportService` or a
  dedicated renderer module once the workflow extraction has settled.

Next extraction candidate:

- `p2pworkspace-proposal-document-service-extraction`
