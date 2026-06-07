# P2PWorkspace Project Maturity Service Extraction Design

## Current Runtime Shape

`storage/filesystem.py` still owns project definition maturity behavior:

- `ProjectRubrics`;
- `ProjectDefinitionMaturity`;
- rubric initialization and preview;
- rubric show parsing;
- maturity computation, persistence, and show parsing;
- helper payload generation for domain/rubrics/maturity.

The behavior is consumed by:

- CLI `project rubrics init/show`;
- CLI `assess maturity refresh/show`;
- MCP `p2p_project_rubrics_init`, `p2p_project_rubrics_show`,
  `p2p_maturity_refresh`, and `p2p_maturity_show`;
- project assessment inclusion through `show_definition_maturity()`.

## Target Shape

Add `src/p2p_engine/services/project_maturity.py` with:

- `ProjectRubrics`;
- `ProjectDefinitionMaturity`;
- `ProjectMaturityService`;
- local helpers for domain normalization, domain state payload, rubrics payload,
  maturity payload, criterion matching, and evidence extraction.

`P2PWorkspace` remains the compatibility facade and delegates maturity/rubric
methods to the service.

## Service Dependencies

The service receives:

- `root`;
- `p2p_dir`;
- `proposal_summaries`;
- `find_proposal_dir`.

The service reads proposal and decision markdown directly to compute project
definition evidence. This keeps maturity independent from proposal lifecycle
mutation and registry generation.

## Compatibility Rules

- Keep output dataclass fields unchanged.
- Keep relative paths unchanged.
- Keep YAML payload shape unchanged.
- Keep built-in rubric templates unchanged.
- Keep CLI/MCP presentation outside the service.
- Keep project initialization outside this extraction; `init_project()` may
  keep using helper payloads until a dedicated bootstrap extraction exists.

## Verification Map

```bash
.venv/bin/pytest tests/test_project_maturity_service.py
.venv/bin/pytest tests/test_cli.py -k "maturity or rubrics or domain_template or default_domain"
.venv/bin/pytest tests/test_mcp.py -k "maturity or rubrics or custom_domain"
.venv/bin/pytest tests/test_mcp_maintenance_handler.py -k maturity
.venv/bin/p2p validate
.venv/bin/pytest
```

## Implementation Evidence

Implemented in:

- `src/p2p_engine/services/project_maturity.py`;
- `src/p2p_engine/storage/filesystem.py` facade wiring;
- `tests/test_project_maturity_service.py`;
- `specs/features/p2pworkspace-project-maturity-service-extraction/tasks.md`.

Verification:

```bash
.venv/bin/pytest tests/test_project_maturity_service.py
# 4 passed

.venv/bin/pytest tests/test_cli.py -k "maturity or rubrics or domain_template or default_domain"
# 3 passed, 90 deselected

.venv/bin/pytest tests/test_mcp.py -k "maturity or rubrics or custom_domain"
# 2 passed, 42 deselected

.venv/bin/pytest tests/test_mcp_maintenance_handler.py
# 4 passed

.venv/bin/p2p validate
# errors: 0, warnings: 0, infos: 0, findings: none

.venv/bin/pytest
# 326 passed
```
