# P2PWorkspace Project Assessment Service Extraction Design

## Design

Create `src/p2p_engine/services/project_assessment.py`.

The service owns:

- deterministic project assessment computation;
- assessment YAML payload generation;
- `.p2p/project/assessment.yml` write/read;
- `ProjectAssessment` compatible dataclass.

`P2PWorkspace` delegates:

- `refresh_project_assessment`
- `show_project_assessment`
- `_compute_project_assessment`

The service receives callbacks for all external state reads:

- validation result;
- registry status;
- proposal summaries;
- choice statuses;
- Change Set statuses;
- Work summaries;
- project state status;
- next actions;
- optional definition maturity lookup.

## Out Of Scope

The service must not own:

- validation implementation;
- registry generation or registry show;
- proposal, choice, change, Work lifecycle behavior;
- project-state refresh;
- definition maturity computation;
- rubrics;
- context packets;
- intake;
- Git/sync;
- CLI/MCP formatting.

## Compatibility Surface

The following must remain compatible:

- `.p2p/project/assessment.yml`;
- YAML keys `generated_on`, `assessment_type`, `completion`, `maturity`,
  `factors`, `gaps`, and `suggested_actions`;
- completion factor ids and messages;
- statuses `blocked`, `not_started`, `ready`, `needs_review`, `at_risk`;
- confidence values `low`, `medium`, `high`;
- missing assessment error text.

## Verification

```bash
.venv/bin/pytest tests/test_project_assessment_service.py
.venv/bin/pytest tests/test_cli.py::test_cli_assess_refresh_and_show tests/test_cli.py::test_cli_assess_show_requires_refresh tests/test_mcp.py::test_mcp_assess_refresh_and_show
.venv/bin/p2p validate
.venv/bin/pytest
```

## Current Status

Implemented.

## Implementation Evidence

Runtime code:

- `src/p2p_engine/services/project_assessment.py` owns deterministic project
  assessment computation, assessment payload generation, assessment refresh
  writes, and assessment show/read parsing.
- `src/p2p_engine/storage/filesystem.py` keeps `P2PWorkspace` as the public
  facade and delegates `refresh_project_assessment`,
  `show_project_assessment`, and `_compute_project_assessment` to
  `ProjectAssessmentService`.
- `tests/test_project_assessment_service.py` covers the extracted service and
  facade delegation.

Compatibility and boundary checks:

- Definition maturity computation, rubrics, project-state refresh, registry
  generation, next-action lifecycle, context packets, intake, Git/sync, CLI
  formatting, and MCP formatting remain outside the service.
- Maturity status and score are included through callbacks only when the
  maturity assessment exists.
- The legacy `_project_assessment_payload` helper was removed from
  `filesystem.py` after moving payload generation into the service.
- The service has no Typer, Rich, MCP, JSON-RPC, Git, sync, rubrics, maturity
  computation, context-packet, intake, or lifecycle imports.

Executed verification:

```bash
.venv/bin/pytest tests/test_project_assessment_service.py
# 5 passed

.venv/bin/pytest tests/test_cli.py::test_cli_assess_refresh_and_show tests/test_cli.py::test_cli_assess_show_requires_refresh tests/test_mcp.py::test_mcp_assess_refresh_and_show
# 3 passed

.venv/bin/p2p validate
# errors: 0, warnings: 0, infos: 0, findings: none

.venv/bin/pytest
# 193 passed
```
