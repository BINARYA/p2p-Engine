# P2PWorkspace Registry Record Builder Service Extraction Design

## Current Runtime Shape

`storage/filesystem.py` still owns registry record helper methods:

- `_accepted_proposals()`;
- `_proposal_registry_records()`;
- `_decision_registry_records()`;
- `_change_registry_records()`;
- `_choice_registry_records()`;
- `_relation_registry_records()`;
- `_artifact_registry_records()`;
- `_readiness_registry_records()`;
- `_changes_for_proposal()`.

`RegistryService` already owns refresh/status/show, but it receives these
record builders as callbacks from `P2PWorkspace`.

## Target Shape

Add `src/p2p_engine/services/registry_records.py` with
`RegistryRecordBuilderService` and the record construction methods listed
above.

`P2PWorkspace` remains the compatibility facade. Its existing internal helper
methods delegate to the record builder so existing service wiring remains
compatible.

## Service Dependencies

The service receives:

- `root`;
- `p2p_dir`;
- `read_proposal_readiness` callback.

It may import markdown parsing helpers and local YAML readers. It must not
write files.

## Compatibility Rules

- Preserve existing path string formats.
- Preserve record ordering from sorted directory traversal.
- Preserve fallback values for missing frontmatter, decisions, tasks, and
  readiness data.
- Preserve proposal vote-derived choice records.
- Preserve relation records generated from changes and proposal related
  changes.

## Verification Map

```bash
.venv/bin/pytest tests/test_registry_record_builder_service.py
.venv/bin/pytest tests/test_registry_service.py
.venv/bin/pytest tests/test_next_actions_service.py
.venv/bin/pytest tests/test_choice_lifecycle_service.py
.venv/bin/p2p validate
.venv/bin/pytest
```

## Implementation Evidence

Implemented in `src/p2p_engine/services/registry_records.py`.

`P2PWorkspace` now owns a lazy `RegistryRecordBuilderService` factory. Existing
internal facade helper methods such as `_proposal_registry_records()` and
`_change_registry_records()` delegate to the builder, preserving compatibility
for `RegistryService`, `NextActionService`, `ChoiceLifecycleService`, project
state, assessment, and validation consumers.

Verification completed:

```bash
.venv/bin/pytest tests/test_registry_record_builder_service.py
.venv/bin/pytest tests/test_registry_service.py
.venv/bin/pytest tests/test_next_actions_service.py
.venv/bin/pytest tests/test_choice_lifecycle_service.py
.venv/bin/pytest tests/test_project_state_service.py
.venv/bin/pytest tests/test_cli.py -k "project_refresh_status_and_show or registry_refresh_status_and_show"
.venv/bin/p2p validate
.venv/bin/pytest
```

Result: focused tests passed, validation reported 0 findings, and the full
suite passed with 359 tests.
