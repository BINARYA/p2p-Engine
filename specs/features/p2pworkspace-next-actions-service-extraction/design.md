# P2PWorkspace Next Actions Service Extraction Design

## Summary

Create `NextActionService` as the internal owner of next-action behavior. Keep
`P2PWorkspace` as a stable facade that wires project-specific dependencies into
the service.

The extraction is intentionally narrow. It removes a coherent block from
`storage/filesystem.py` without changing CLI/MCP behavior or `.p2p/` data
formats.

## Target Module

`src/p2p_engine/services/next_actions.py`

Expected contents:

- `NextAction` dataclass.
- `NextActionService` class.
- Small dependency protocol or constructor callables for reading surrounding
  project state.

`src/p2p_engine/storage/filesystem.py` should import and re-export
`NextAction`, so compatibility imports keep working.

## Service Responsibilities

- Resolve `.p2p/project/next-actions.yml`.
- Resolve `.p2p/project/next-actions-log.yml`.
- Read and write curated next-action YAML.
- Convert YAML records to `NextAction`.
- Normalize curated records.
- Allocate curated IDs with the existing `NEXT-001` sequence.
- Complete or retire curated records and append audit-log entries.
- Deduplicate active/generated actions.
- Generate fallback actions from:
  - stale registry status,
  - non-terminal Change Sets,
  - pending intake records,
  - draft proposal readiness state,
  - unresolved choice records,
  - empty-project review fallback.
- Generate active choice blocker actions from active choice block links.

## Facade Responsibilities

`P2PWorkspace` should provide:

- a cached `_next_action_service()` factory;
- public delegating methods:
  - `next_actions`
  - `next_action_add`
  - `next_action_complete`
  - `next_action_retire`
  - `next_actions_refresh`

The facade should pass service dependencies as callables. This keeps the service
independent from CLI/MCP and avoids a direct dependency on the full workspace
object.

## Suggested Dependencies

The service needs access to:

- `root`
- `p2p_dir`
- `registry_status`
- `change_registry_records`
- `intake_statuses`
- `proposal_summaries`
- `read_proposal_readiness`
- `choice_registry_records`
- `choice_statuses`
- `show_choice`
- YAML read/write helpers or local equivalents

If moving the YAML helpers would expand the slice too far, keep the existing
private helper functions in `filesystem.py` and pass reader/writer callables.
Prefer moving only the next-action-specific logic in this feature.

## Model Compatibility

Current consumers use attributes on `NextAction`, not concrete type identity.
Still, `p2p_engine.storage.filesystem.NextAction` should remain importable.

Recommended approach:

1. Define `NextAction` in `services.next_actions`.
2. Import it in `storage.filesystem`.
3. Remove the old inline dataclass definition from `filesystem.py`.

## Risk Controls

- Do not change generated command strings.
- Do not change generated action IDs.
- Preserve fallback generation order exactly.
- Preserve audit-log `closed_on` date behavior.
- Keep service tests close to current CLI/MCP scenarios before removing the old
  helper code.
- Run focused next-action tests first, then broader CLI/MCP tests, then the full
  suite.

## Verification Plan

Focused tests:

- `tests/test_next_actions_service.py`
- `tests/test_cli.py -k "next"`
- `tests/test_mcp.py -k "next"`
- `tests/test_mcp_maintenance_handler.py`

Regression tests:

- full `pytest`
- `.venv/bin/p2p validate`
