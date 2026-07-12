# Write Path Inventory - PROP-084

## Purpose

This local implementation artifact supports the PROP-084 governed-write gate.
It is not P2P governance state.

Before implementing the gate, every public entry point that can mutate
P2P-managed project state must be classified here or in an equivalent test
fixture.

## Classification

- `guarded`: PROP-084 runtime preflight runs before mutation.
- `read_only`: the entry point does not mutate P2P-managed state.
- `deferred`: the entry point is intentionally outside this implementation,
  with reason and residual risk.

## Required Domains

The inventory must cover public CLI, service/facade, and MCP entry points for:

- proposals;
- decisions;
- choices;
- changes;
- work;
- governance;
- permissions;
- consent;
- managed sync;
- managed branches;
- project initialization paths that create or touch P2P-managed state;
- existing-project initialization where `runtime_contract.required: true` is
  present but `.p2p/project/runtime.yml` is missing;
- validation and status paths, classified as read-only when applicable.

## Inventory Matrix

| Domain | Public Entry Point | Surface | Classification | Guard Location | Tests | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| proposal | create/update/contribution/prompt/import/readiness/questions/artifacts | CLI/service/MCP | guarded | `P2PWorkspace._ensure_runtime_write_allowed` | `tests/test_runtime_write_gate.py`, proposal/readiness/question/artifact service tests | Read-only show/list/status paths remain unguarded. |
| decision | proposal accept/reject/defer and decision record | CLI/service/MCP | guarded | `P2PWorkspace.record_decision`, readiness override path | `tests/test_runtime_write_gate.py`, proposal decision tests | Owner authority rules still apply after runtime preflight. |
| choice | create/block/unblock/decide | CLI/service/MCP | guarded | `P2PWorkspace` choice mutators | `tests/test_runtime_write_gate.py`, choice lifecycle tests | Choice show/list/discover/governance-preflight are read-only. |
| change | create/status update and software-spec write flows | CLI/service/MCP | guarded | `P2PWorkspace` change/spec mutators | `tests/test_runtime_write_gate.py`, change/spec tests | Show/status/policy/tasks are read-only. |
| work | plan/branch/retire/submit/review/publish/request-review/accept/finalize/cleanup | CLI/service/MCP | guarded | `P2PWorkspace` work mutators | `tests/test_runtime_write_gate.py`, work branch/planning tests | Work show/list/status/scan are read-only. |
| governance | init/vote/precedent record | CLI/service/MCP | guarded | `P2PWorkspace` governance mutators | `tests/test_runtime_write_gate.py`, governance tests | Governance status/validate/search/preflight are read-only. |
| permission | actor add | CLI/service/MCP | guarded | `P2PWorkspace.permissions_actor_add` | `tests/test_runtime_write_gate.py`, permissions tests | Permissions show is read-only. |
| consent | grant/request/revoke/consume/error mark | CLI/service/MCP | guarded | `P2PWorkspace` consent mutators | `tests/test_runtime_write_gate.py`, consent tests | Consent show/status/validate are read-only validation paths. |
| sync | fetch/pull/push | CLI/service/MCP | guarded | `P2PWorkspace.sync_fetch/pull/push` | `tests/test_runtime_write_gate.py`, sync tests | Sync status is read-only. |
| managed branch | proposal/work branch publish/request/accept/reject/merge/finalize/cleanup | CLI/service/MCP | guarded | `P2PWorkspace` proposal/work branch mutators | `tests/test_runtime_write_gate.py`, branch service tests | Branch status/scan are read-only. |
| project initialization - new project | `p2p init` on a root without `.p2p/project.yml` | CLI/service/MCP | guarded | bootstrap exception in `P2PWorkspace.init_project_with_summary` | `tests/test_project_initialization_service.py` | Allowed because no project contract exists yet; creates `runtime.yml` and marker. |
| project initialization - existing project | `p2p init` on a root with `.p2p/project.yml` | CLI/service/MCP | guarded | `P2PWorkspace.init_project_with_summary` | `tests/test_project_initialization_service.py` | Runtime preflight runs before idempotent writes. |
| project initialization - missing required runtime contract | `p2p init` with marker present and missing `runtime.yml` | CLI/service/MCP | guarded | `P2PWorkspace.init_project_with_summary` | `tests/test_project_initialization_service.py` | Blocks before mutation and does not regenerate `runtime.yml` from the active local runtime. |
| validation/status | status/context/check/validate/runtime status/show/list/read commands | CLI/service/MCP | read_only | no write preflight required | `tests/test_runtime_contract_service.py`, `tests/test_validation_service.py`, `tests/test_cli.py` | Must remain available for diagnosis when writes are blocked. |

## Completion Rule

Implementation is not complete until every guarded class has test evidence that
the runtime preflight runs before mutation and read-only paths remain available
for diagnosis.
