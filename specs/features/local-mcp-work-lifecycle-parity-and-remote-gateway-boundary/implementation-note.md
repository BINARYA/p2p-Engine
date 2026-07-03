# Implementation Note - Local MCP Work Lifecycle Parity And Remote Gateway Boundary

## Scope Implemented

Implemented local MCP parity for the managed Work lifecycle.

New MCP tools:

- `p2p_work_branch`
- `p2p_work_submit`
- `p2p_work_review`
- `p2p_work_publish`
- `p2p_work_request_review`
- `p2p_work_accept`
- `p2p_work_finalize`
- `p2p_work_cleanup`

Existing Work read/plan tools remain unchanged:

- `p2p_work_list`
- `p2p_work_status`
- `p2p_work_show`
- `p2p_work_plan`

## Owner Modules And Boundaries

Behavior remains owned by existing modules:

- `src/p2p_engine/services/work_branches.py` owns Work lifecycle rules,
  branch state, Git preconditions, publish, review handoff, accept, finalize,
  cleanup, and conflict behavior.
- `src/p2p_engine/services/consent.py` owns receipt validation, status,
  operation, target, actor, expiry, consumption, and used-with-error state.
- `src/p2p_engine/mcp/catalog/work_specs.py` owns Work MCP tool schemas and
  descriptions.
- `src/p2p_engine/mcp/handlers/work_specs.py` owns MCP argument translation,
  consent validation calls, result packaging, and governance/effect payloads.
- `src/p2p_engine/mcp/consent_audit.py` owns consent consumption audit commits
  and optional pushes.
- `src/p2p_engine/storage/filesystem.py` remains a compatibility facade only;
  no new Work lifecycle logic was added there.

MCP delegates lifecycle behavior to `P2PWorkspace` facade methods and does not
duplicate the Work state machine.

## Consent And Governance Behavior

Preparatory tools are local and consent-free:

- `p2p_work_branch`
- `p2p_work_submit`
- `p2p_work_review`

Privileged tools require granted matching consent receipts:

- `p2p_work_publish` -> `work_publish`
- `p2p_work_request_review` -> `work_request_review`
- `p2p_work_accept` -> `work_accept`
- `p2p_work_finalize` -> `work_finalize`
- `p2p_work_cleanup` -> `work_cleanup`

Consent validation checks the exact `operation`, `target` (`work_id`),
`actor_id`, receipt status, and expiry through the existing consent service.
Successful privileged operations consume the receipt with structured result
metadata and use existing MCP consent audit helpers.

Accept conflicts return `work_accept_conflict`, include conflicted files, set
`manual_resolution_required: true`, set `merge_performed: false`, and mark the
receipt `used_with_error`.

Finalize and cleanup remain separate. Finalize pushes accepted base-branch
metadata. Cleanup deletes the local Work branch and deletes the remote branch
only when `delete_remote` is true.

## Remote Gateway Boundary

The implementation intentionally stays local/core MCP only.

Not implemented in P2P Engine core:

- remote HTTP MCP;
- Wavekit user authentication;
- hosted client grants;
- strong hosted receipts;
- tenancy;
- billing;
- rate limits;
- hosted audit retention;
- provider PR/MR creation.

`p2p_work_request_review` records provider-advisory metadata and suggested next
steps only. It does not create GitHub pull requests, GitLab merge requests, or
provider-side review records.

## Files Changed

Runtime:

- `src/p2p_engine/mcp/registry.py`
- `src/p2p_engine/mcp/catalog/work_specs.py`
- `src/p2p_engine/mcp/handlers/work_specs.py`
- `src/p2p_engine/services/agent_templates.py`

Tests:

- `tests/test_mcp_registry.py`
- `tests/test_mcp_work_spec_handler.py`
- `tests/test_mcp.py`

Documentation/specs:

- `docs/MCP.md`
- `docs/INSTALL.md`
- `specs/features/local-mcp-work-lifecycle-parity-and-remote-gateway-boundary/implementation-note.md`
- `specs/features/local-mcp-work-lifecycle-parity-and-remote-gateway-boundary/tasks.md`

## Test Strategy

The test set follows `TEST_QUALITY_SKILL.md`:

- registry tests protect tool names, strict schemas, stable required fields,
  and absence of raw Git shortcuts;
- handler tests protect MCP dispatch, consent validation wiring, audit helper
  calls, JSON-ready payloads, governance metadata, and conflict handling using
  a fake workspace;
- public MCP tests protect real `call_tool` dispatch, missing arguments,
  consent mismatch rejection, and one full Work lifecycle with Git, remote,
  consents, publish, request-review, accept, finalize, and cleanup;
- service tests remain the source for detailed Work lifecycle domain
  preconditions;
- CLI tests are run for compatibility but were not duplicated for new MCP
  behavior.

No new raw Git MCP tools were added.

## Validation Evidence

Baseline before edits:

```bash
.venv/bin/pytest tests/test_work_branch_service.py tests/test_mcp_work_spec_handler.py tests/test_mcp_registry.py
# 45 passed
```

Focused MCP validation:

```bash
.venv/bin/pytest tests/test_mcp_work_spec_handler.py tests/test_mcp_registry.py
# 13 passed
```

Targeted public MCP validation:

```bash
.venv/bin/pytest tests/test_mcp.py -k "work_lifecycle or work_publish_rejects_consent_actor_mismatch or work_flow"
# 4 passed
```

Public MCP/registry/handler validation:

```bash
.venv/bin/pytest tests/test_mcp_work_spec_handler.py tests/test_mcp_registry.py tests/test_mcp.py
# 70 passed
```

Service compatibility:

```bash
.venv/bin/pytest tests/test_work_branch_service.py
# 37 passed
```

CLI Work compatibility:

```bash
.venv/bin/pytest tests/test_cli.py -k "work_"
# 18 passed
```

Repository validation:

```bash
.venv/bin/p2p validate
# errors: 0; warnings: 0; infos: 0
```

Public suite:

```bash
./scripts/test-public.sh
# 199 passed, 300 deselected
```

Full suite:

```bash
./scripts/test-full.sh
# 499 passed
```

## Quality Review

Engineering quality checks:

- no validation, permission, consent, or governance bypass was introduced;
- no raw Git shortcut MCP tools were added;
- no lifecycle rules were moved into MCP;
- `P2PWorkspace` remains a facade;
- side effects are visible in tool descriptions, payloads, and tests;
- remote gateway concerns remain documentation-only.

Test quality checks:

- service behavior is not duplicated exhaustively at MCP layer;
- public MCP tests cover public dispatch and permission boundaries;
- handler tests cover payload and consent/audit wiring at the lowest useful
  layer;
- full-suite validation passed.

## Residual Risks And Follow-Ups

- MCP error payloads still rely on existing `ValueError` messages from the
  service layer. A future explicit domain error model could make MCP failures
  more machine-readable.
- Consent receipts are local audit records, not strong authentication. Remote
  gateways such as Wavekit must enforce user identity, grants, tenancy, and
  hosted audit policy before invoking core lifecycle tools.
