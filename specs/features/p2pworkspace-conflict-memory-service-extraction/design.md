# P2PWorkspace Conflict Memory Service Extraction Design

## Summary

Create `ConflictMemoryService` as the owner of project conflict-memory records.
Keep `P2PWorkspace` as a facade that wires proposal lookup and root paths into
the service.

This is a deliberately small extraction before the larger intake/choice/change
lifecycle split.

## Target Module

`src/p2p_engine/services/conflicts.py`

Expected contents:

- `ConflictStatus` dataclass.
- `ConflictMemoryService` class.
- Small YAML read/write helpers local to the module.

`src/p2p_engine/storage/filesystem.py` should import and re-export
`ConflictStatus`, so compatibility imports keep working.

## Service Responsibilities

- Resolve `.p2p/project/conflicts.yml`.
- Read conflict payloads.
- Validate the `conflicts` collection shape.
- Allocate sequential `CONFLICT-001` IDs using current count behavior.
- Append conflict records.
- Normalize status output by filtering non-dictionary conflict records.
- Return paths relative to project root.

## Facade Responsibilities

`P2PWorkspace` should provide:

- a cached `_conflict_memory_service()` factory;
- public delegating methods:
  - `record_conflict`
  - `conflict_status`

The facade passes `find_proposal_dir` as a callable so the service can validate
proposal references without depending on the whole workspace object.

## Verification Plan

Focused tests:

- `tests/test_conflict_memory_service.py`
- `tests/test_cli.py -k impact_import_and_conflict_memory`
- `tests/test_mcp.py -k conflict`

Regression tests:

- full `pytest`
- `.venv/bin/p2p validate`
