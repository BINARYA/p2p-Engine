# P2PWorkspace Governance Service Extraction Design

## Current Runtime Shape

`storage/filesystem.py` still owns a compact but real governance cluster:

- `init_governance()`;
- `governance_status()`;
- `record_vote()`;
- `vote_status()`;
- `record_precedent()`;
- `_vote_status_from_data()`.

The CLI collaboration commands call these methods through `P2PWorkspace`.

## Target Shape

Add `src/p2p_engine/services/governance.py` with:

- `GovernanceService`;
- `GovernanceStatus`;
- `VoteStatus`;
- YAML read/write helpers scoped to the service;
- vote status calculation.

`P2PWorkspace` remains the compatibility facade and delegates the existing
methods to the service.

## Service Dependencies

The service receives:

- `root`;
- `p2p_dir`;
- `find_proposal_dir` callback for proposal existence and location checks.

No CLI/MCP/branch/sync dependencies are allowed.

## Compatibility Rules

- Preserve exact file names under `.p2p/governance/` and proposal directories.
- Preserve existing overwrite semantics for governance initialization.
- Preserve relative path returns.
- Preserve vote counting and tie semantics.
- Preserve malformed YAML/list validation errors.

## Verification Map

```bash
.venv/bin/pytest tests/test_governance_service.py
.venv/bin/pytest tests/test_cli.py -k "governance or vote or precedent"
.venv/bin/pytest tests/test_choice_lifecycle_service.py
.venv/bin/p2p validate
.venv/bin/pytest
```

## Implementation Evidence

Implemented in `src/p2p_engine/services/governance.py`.

`P2PWorkspace` now exposes the same governance, vote, and precedent methods as
compatibility facades while delegating runtime behavior to `GovernanceService`.

Verification completed:

```bash
.venv/bin/pytest tests/test_governance_service.py
.venv/bin/pytest tests/test_cli.py -k "governance or vote or precedent"
.venv/bin/pytest tests/test_choice_lifecycle_service.py
.venv/bin/p2p validate
.venv/bin/pytest
```

Result: focused tests passed, validation reported 0 findings, and the full
suite passed with 341 tests.
