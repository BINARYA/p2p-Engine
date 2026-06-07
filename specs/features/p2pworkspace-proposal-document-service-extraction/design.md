# P2PWorkspace Proposal Document Service Extraction Design

## Design

Create `src/p2p_engine/services/proposals.py`.

The service owns:

- proposal id allocation;
- proposal directory lookup and duplicate-id grouping;
- proposal markdown creation;
- proposal show/detail mapping;
- proposal update section replacement;
- contribution add/list behavior.

`P2PWorkspace` delegates:

- `show_proposal`
- `create_proposal`
- `create_proposal_with_details`
- `update_proposal`
- `add_contribution`
- `list_contributions`
- `_next_proposal_id`
- `_find_proposal_dir`
- `_duplicate_proposal_ids`

Out of scope:

- `record_decision`
- readiness methods
- proposal branch lifecycle
- sync/Git behavior

## Verification

```bash
.venv/bin/pytest tests/test_proposal_document_service.py
.venv/bin/pytest tests/test_skeleton.py::test_create_proposal_with_details_writes_useful_sections tests/test_skeleton.py::test_update_proposal_replaces_only_requested_sections tests/test_cli.py::test_cli_lists_proposal_contributions tests/test_mcp.py::test_mcp_validate_reports_duplicate_proposal_ids
.venv/bin/p2p validate
.venv/bin/pytest
```

## Implementation Evidence

### Source Changes

Added service module:

- `src/p2p_engine/services/proposals.py`

Updated facade:

- `src/p2p_engine/storage/filesystem.py`

Added focused tests:

- `tests/test_proposal_document_service.py`

Updated local feature specs:

- `specs/features/p2pworkspace-proposal-document-service-extraction/`

### Facade Methods Delegated

`P2PWorkspace` now constructs `ProposalDocumentService` lazily and delegates:

- `show_proposal`
- `create_proposal`
- `create_proposal_with_details`
- `update_proposal`
- `add_contribution`
- `list_contributions`
- `_next_proposal_id`
- `_find_proposal_dir`
- `_duplicate_proposal_ids`

### Behavior Moved

Moved behind `ProposalDocumentService`:

- proposal id allocation;
- proposal directory lookup;
- duplicate proposal id grouping;
- proposal markdown creation and initial artifact creation;
- proposal detail mapping;
- proposal section update behavior;
- contribution add/list behavior.

### Behavior Left In Place

These remain outside the service:

- `record_decision`;
- readiness profile/assessment methods;
- proposal branch lifecycle;
- branch metadata and Git operations;
- registry refresh and validation orchestration;
- choice/change/work behavior.

### Verification Commands

```bash
.venv/bin/pytest tests/test_proposal_document_service.py
# 2 passed

.venv/bin/pytest tests/test_skeleton.py::test_create_proposal_with_details_writes_useful_sections tests/test_skeleton.py::test_update_proposal_replaces_only_requested_sections tests/test_cli.py::test_cli_lists_proposal_contributions tests/test_mcp.py::test_mcp_validate_reports_duplicate_proposal_ids
# 4 passed

.venv/bin/p2p validate
# errors: 0, warnings: 0, infos: 0

.venv/bin/pytest
# 171 passed
```

### Remaining Gaps

No behavior gap is known after focused, mapped compatibility, P2P validation,
and full-suite verification.

Next extraction candidate:

- `p2pworkspace-readiness-service-extraction`
