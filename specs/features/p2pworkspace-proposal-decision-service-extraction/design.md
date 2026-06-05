# P2PWorkspace Proposal Decision Service Extraction Design

## Design

Create `src/p2p_engine/services/proposal_decisions.py`.

The service owns:

- decision markdown generation for proposal decisions;
- writing `decision.md`;
- updating the proposal `## Status` section;
- returning the existing `p2p_engine.core.decision.Decision` dataclass.

`P2PWorkspace` delegates:

- `record_decision`

The service depends only on:

- repository root;
- `.p2p` directory;
- a proposal directory resolver callback;
- `Decision` and `DecisionOutcome`;
- pure markdown helper `replace_section`.

## Out Of Scope

The service must not own:

- CLI shortcut readiness warnings or readiness override behavior;
- MCP consent validation, consent consumption, audit commit orchestration, or
  JSON payload formatting;
- managed proposal branch accept/reject/merge/finalize/cleanup behavior;
- Git and sync operations;
- registry generation;
- project-state refresh;
- Work, choice, or Change Set decisions.

## Compatibility Surface

The following must remain byte-shape compatible enough for existing tests and
users:

- `decision.md` title and sections:
  - `# Decision - PROP-XXX`
  - `## Status`
  - `## Outcome`
  - `## Reason`
  - `## Date`
  - `## Approver`
- proposal `## Status` value format with backticks;
- `Decision` return fields and date type;
- error behavior from proposal directory lookup.

## Verification

```bash
.venv/bin/pytest tests/test_proposal_decision_service.py
.venv/bin/pytest tests/test_cli.py::test_cli_import_exploration_file_and_record_decision tests/test_cli.py::test_cli_proposal_decision_shortcuts tests/test_mcp.py::test_mcp_draft_proposal_decision_requires_granted_consent tests/test_mcp.py::test_mcp_draft_proposal_accept_and_defer_consume_matching_consent
.venv/bin/p2p validate
.venv/bin/pytest
```

## Current Status

Implemented.

## Implementation Evidence

Runtime code:

- `src/p2p_engine/services/proposal_decisions.py` owns proposal decision
  markdown generation, `decision.md` writes, proposal status mutation, and
  `Decision` return construction.
- `src/p2p_engine/storage/filesystem.py` keeps `P2PWorkspace.record_decision`
  as the public facade and delegates to `ProposalDecisionService`.
- `tests/test_proposal_decision_service.py` covers the extracted service and
  facade delegation.

Compatibility and boundary checks:

- CLI `proposal accept`, `proposal reject`, `proposal defer`, and
  `decision record` continue through `P2PWorkspace.record_decision`.
- MCP proposal decision tools continue to own consent validation, consent
  consumption, audit behavior, and JSON response formatting.
- Managed proposal branch lifecycle, Git/sync, readiness override checks,
  registries, and project-state refresh remain outside the service.
- The service has no Typer, Rich, MCP, JSON-RPC, Git, registry, project-state,
  branch, sync, consent, or readiness imports.

Executed verification:

```bash
.venv/bin/pytest tests/test_proposal_decision_service.py tests/test_cli.py::test_cli_import_exploration_file_and_record_decision tests/test_cli.py::test_cli_proposal_decision_shortcuts tests/test_mcp.py::test_mcp_draft_proposal_decision_requires_granted_consent tests/test_mcp.py::test_mcp_draft_proposal_accept_and_defer_consume_matching_consent
# 7 passed

.venv/bin/p2p validate
# errors: 0, warnings: 0, infos: 0, findings: none

.venv/bin/pytest
# 176 passed
```
