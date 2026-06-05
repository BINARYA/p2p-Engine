# P2PWorkspace Work Planning Service Extraction Design

## Design

Create `src/p2p_engine/services/work_planning.py`.

The service owns:

- `WORK-XXX` id allocation;
- `.p2p/work/WORK-XXX` directory lookup;
- Work manifest generation for planned Work;
- Work detail mapping from `manifest.yml`;
- Work status mapping from local manifests and scanned registry items;
- Work summary mapping and next-action hints.

`P2PWorkspace` delegates:

- `create_work_plan`
- `work_statuses`
- `work_summaries`
- `show_work`
- `_next_work_id`
- `_find_work_dir`
- `_work_summary_from_manifest`
- `_work_summary_from_scan`

The service receives callbacks for compatibility-sensitive operations that
remain outside the service:

- target validation;
- spec export validation;
- Change Set directory lookup;
- scanned Work registry reads.

## Out Of Scope

The service must not own:

- Work branch creation;
- Work retire/submit/review/publish;
- Work accept/continue/abort/finalize/cleanup;
- branch scanning implementation;
- Git adapter calls;
- sync and remote resolution;
- provider review handoff;
- CLI/MCP formatting.

## Compatibility Surface

The following must remain compatible:

- manifest keys and values produced by `p2p work plan`;
- branch candidate naming: `p2p/work/work-001-change-001-target`;
- `WorkDetail`, `WorkStatus`, and `WorkSummary` observable attributes;
- scanned Work registry inclusion in `work_statuses` and `work_summaries`;
- next-action text for planned, branched, submitted, review, published,
  merge-conflict, accepted, finalized, cleaned, retired, scanned, and unknown
  statuses;
- existing errors for unsupported targets and missing Work ids.

## Verification

```bash
.venv/bin/pytest tests/test_work_planning_service.py
.venv/bin/pytest tests/test_cli.py::test_cli_work_plan_list_and_show tests/test_mcp.py::test_mcp_write_safe_spec_export_and_work_flow
.venv/bin/p2p validate
.venv/bin/pytest
```

## Current Status

Implemented.

## Implementation Evidence

Runtime code:

- `src/p2p_engine/services/work_planning.py` owns Work plan manifest
  generation, Work id allocation, Work directory lookup, Work detail mapping,
  Work status mapping, Work summary mapping, and next-action hints.
- `src/p2p_engine/storage/filesystem.py` keeps `P2PWorkspace` as the facade and
  delegates Work planning methods and helper methods to `WorkPlanningService`.
- `tests/test_work_planning_service.py` covers the extracted service and facade
  delegation.

Compatibility and boundary checks:

- `p2p work plan`, `p2p work list`, `p2p work status`, and `p2p work show`
  remain compatible through `P2PWorkspace`.
- MCP `p2p_work_plan`, `p2p_work_list`, and `p2p_work_show` continue to receive
  dataclass payloads convertible with the existing JSON serializer.
- Work branch, retire, submit, review, publish, accept, finalize, cleanup,
  branch scanning implementation, Git/sync, provider handoff, consent,
  CLI formatting, and MCP formatting remain outside the service.
- The legacy `_work_manifest` and `_work_next_action` helpers were removed from
  `filesystem.py` after moving their behavior into the service.

Executed verification:

```bash
.venv/bin/pytest tests/test_work_planning_service.py
# 4 passed

.venv/bin/pytest tests/test_work_planning_service.py tests/test_cli.py::test_cli_work_plan_list_and_show tests/test_mcp.py::test_mcp_write_safe_spec_export_and_work_flow
# 6 passed

.venv/bin/p2p validate
# errors: 0, warnings: 0, infos: 0, findings: none

.venv/bin/pytest
# 180 passed
```
