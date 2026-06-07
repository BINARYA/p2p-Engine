# P2PWorkspace Renderers Validators Foundation Design

## Requirements Covered

- R001 - Markdown Foundation
- R002 - Markdown Behavior Compatibility
- R003 - YAML Validation Foundation
- R004 - Domain Renderer Boundary
- R005 - Compatibility Preservation
- R006 - Focused Test Coverage
- N001 - Pure Foundation
- N002 - No Behavior Drift
- N003 - Narrow Extraction

## Key Decisions

### D001 - Extract Shared Helpers, Not Domain Renderers

This feature extracts shared Markdown and YAML helper functions only.

Rationale: moving software-spec, project-definition, proposal, or agent
instruction renderers now would mix multiple domains and make output drift hard
to review. A small foundation reduces duplication risk for the next services.

### D002 - Use Utility Modules Instead Of Services

The extracted helpers live in utility/foundation modules, not application
services.

Rationale: these functions are pure parsing/formatting/validation primitives;
they do not own a workflow or domain lifecycle.

### D003 - Preserve Legacy Function Names As Imports

`filesystem.py` should import the shared helpers using the existing private
names where practical.

Rationale: this minimizes call-site churn and makes the diff reviewable.

### D004 - Keep YAML Dump Local For Now

`_yaml_dump` remains local in modules that write YAML.

Rationale: several services already own small YAML write helpers. Consolidating
all YAML serialization is a separate cleanup and not required for this
foundation.

## Components

### `src/p2p_engine/foundation/markdown.py`

Owns pure Markdown helpers:

- `read_title`
- `read_markdown_section`
- `markdown_has_section`
- `read_frontmatter`
- `replace_frontmatter`
- `strip_markdown_title`
- `replace_section`

No filesystem, CLI, MCP, Git, or workspace dependency.

### `src/p2p_engine/foundation/validators.py`

Owns generic YAML validators:

- `validate_tasks_yaml`
- `validate_yaml_key`

No filesystem, CLI, MCP, Git, or workspace dependency.

### `src/p2p_engine/storage/filesystem.py`

Imports foundation helpers under existing private helper names:

- `_read_title`
- `_read_markdown_section`
- `_markdown_has_section`
- `_read_frontmatter`
- `_replace_frontmatter`
- `_strip_markdown_title`
- `_replace_section`
- `_validate_tasks_yaml`
- `_validate_yaml_key`

Keeps domain renderers and domain validators in place.

## Compatibility Tests To Run

Focused foundation tests:

```bash
.venv/bin/pytest tests/test_foundation_helpers.py
```

Mapped compatibility:

```bash
.venv/bin/pytest \
  tests/test_skeleton.py::test_create_proposal_with_details_writes_useful_sections \
  tests/test_skeleton.py::test_update_proposal_replaces_only_requested_sections \
  tests/test_cli.py::test_cli_validate_reports_invalid_yaml_as_error \
  tests/test_cli.py::test_cli_validate_valid_project_and_json_output \
  tests/test_cli.py::test_cli_validate_reports_duplicate_proposal_ids_as_error \
  tests/test_cli.py::test_cli_software_spec_refresh_prompt_import_status_and_show \
  tests/test_mcp.py::test_mcp_validate_returns_structured_findings \
  tests/test_mcp.py::test_mcp_write_safe_spec_export_and_work_flow
```

Validation:

```bash
.venv/bin/p2p validate
```

Full suite:

```bash
.venv/bin/pytest
```

## Risks And Tradeoffs

- Importing helpers under legacy private names keeps the diff small, but a
  later cleanup may rename call sites to public helper names.
- YAML dump helpers remain duplicated for now. This avoids broad service churn
  across already extracted services.
- Domain renderers remain in the monolith until their owning services are
  extracted. This is intentional to avoid crossing domains.

## Out Of Scope

- Software-spec service extraction.
- Project definition/spec-export extraction.
- Proposal document service extraction.
- Readiness service extraction.
- CLI/MCP modularization.

## Implementation Evidence

Covered by T001-T018.

### Source Changes

Added foundation modules:

- `src/p2p_engine/foundation/__init__.py`
- `src/p2p_engine/foundation/markdown.py`
- `src/p2p_engine/foundation/validators.py`

Updated compatibility caller:

- `src/p2p_engine/storage/filesystem.py`

Added focused tests:

- `tests/test_foundation_helpers.py`

Updated local feature specs:

- `specs/features/p2pworkspace-renderers-validators-foundation/requirements.md`
- `specs/features/p2pworkspace-renderers-validators-foundation/design.md`
- `specs/features/p2pworkspace-renderers-validators-foundation/tasks.md`

### Helpers Moved

Moved to `p2p_engine.foundation.markdown`:

- `read_title`
- `read_markdown_section`
- `markdown_has_section`
- `read_frontmatter`
- `replace_frontmatter`
- `strip_markdown_title`
- `replace_section`

Moved to `p2p_engine.foundation.validators`:

- `validate_tasks_yaml`
- `validate_yaml_key`

`filesystem.py` imports these helpers under the previous private names so
existing call sites remain stable.

### Helpers Left In Place

Domain renderers intentionally remain in `src/p2p_engine/storage/filesystem.py`
until their owning services are extracted:

- proposal Markdown renderer;
- change Markdown renderer;
- software-spec Markdown renderers;
- project definition, generic, OpenSpec, and Spec Kit renderers;
- project state renderers;
- agent instruction renderers.

Domain validators also remain in place:

- readiness profile validation;
- readiness assessment validation;
- agent integrations validation;
- project definition export validation orchestration.

YAML serialization helpers were not consolidated in this feature because
existing extracted services already own small local YAML write helpers and a
global serialization cleanup is not required for the next extraction.

### Compatibility Correction

The initial compatibility command list used descriptive test names for
software-spec/spec-export behavior. The repo currently covers that flow through
`tests/test_cli.py::test_cli_software_spec_refresh_prompt_import_status_and_show`.
The design command list was updated to use the real test name.

### Verification Commands

Focused foundation tests:

```bash
.venv/bin/pytest tests/test_foundation_helpers.py
```

Result:

- `5 passed`

Mapped compatibility tests:

```bash
.venv/bin/pytest \
  tests/test_skeleton.py::test_create_proposal_with_details_writes_useful_sections \
  tests/test_skeleton.py::test_update_proposal_replaces_only_requested_sections \
  tests/test_cli.py::test_cli_validate_reports_invalid_yaml_as_error \
  tests/test_cli.py::test_cli_validate_valid_project_and_json_output \
  tests/test_cli.py::test_cli_validate_reports_duplicate_proposal_ids_as_error \
  tests/test_mcp.py::test_mcp_validate_returns_structured_findings \
  tests/test_mcp.py::test_mcp_write_safe_spec_export_and_work_flow
```

Result:

- `7 passed`

Software-spec/export compatibility:

```bash
.venv/bin/pytest tests/test_cli.py::test_cli_software_spec_refresh_prompt_import_status_and_show
```

Result:

- `1 passed`

Validation:

```bash
.venv/bin/p2p validate
```

Result:

- `errors: 0`
- `warnings: 0`
- `infos: 0`
- `findings: none`

Full post-extraction suite:

```bash
.venv/bin/pytest
```

Result:

- `165 passed`

### Source Scope Review

Runtime extraction scope:

- `src/p2p_engine/foundation/`
- `src/p2p_engine/storage/filesystem.py`
- `tests/test_foundation_helpers.py`
- `specs/features/p2pworkspace-renderers-validators-foundation/`

The worktree also contains pre-existing `.p2p`, `AGENTS.md`, `docs/`, other
`specs/`, and earlier service extraction changes. Those files are not part of
this foundation extraction unless listed above.

### Remaining Gaps

No behavior gap is known for this feature after focused, mapped compatibility,
P2P validation, and full-suite verification.

Follow-up extraction enabled by this foundation:

- `p2pworkspace-software-spec-service-extraction`
