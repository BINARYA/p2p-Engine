# P2PWorkspace Refactoring Inventory

## Purpose

This inventory tracks the current runtime shape before refactoring. It is the
source for future extraction tasks and must distinguish runtime implementation
from P2P state, docs, and local planning specs.

## Status

- Current phase: Phase 1 inventory setup
- Completed tasks: T001-T004
- Runtime changes: none

## File Inventory

### Source Measurement Baseline

Measured with `wc -l` from the repository root.

| Area | Path | Lines | Current role | Refactoring concern |
| --- | --- | ---: | --- | --- |
| CLI | `src/p2p_engine/cli.py` | 3,147 | Typer command registration, command handlers, console output, JSON output, command glue | Large presentation surface with direct workspace orchestration; should become thinner after services exist. |
| Workspace/storage | `src/p2p_engine/storage/filesystem.py` | 9,971 | `P2PWorkspace`, dataclasses, storage, lifecycle workflows, validation, registries, specs/export, generated text, YAML/Markdown helpers | Primary monolith; mixes facade, use cases, persistence, rendering, validation, and helper logic. |
| MCP | `src/p2p_engine/mcp/tools.py` | 2,105 | MCP tool names, schemas, dispatch, permission-gated tool orchestration, JSON conversion | Tool schema and dispatch are coupled; should eventually move toward registry/handler separation. |
| Git adapter | `src/p2p_engine/storage/git.py` | 184 | Thin wrappers around Git subprocess calls | Returns booleans/strings and hides error detail; future extraction may need richer error reporting. |
| Core models | `src/p2p_engine/core/*.py` | 121 | Small dataclasses/enums for proposals, decisions, contributions, plans, projects, tasks | Underused domain layer; candidate destination for stable domain contracts. |
| Exporters | `src/p2p_engine/exporters/*.py` | 35 | Minimal markdown/OpenSpec exporters | Very small; current export behavior mostly lives in `filesystem.py`. |
| Prompts | `src/p2p_engine/prompts/*.py` | 341 | Prompt rendering helpers | Already separated reasonably; should remain independent renderer layer. |
| CLI tests | `tests/test_cli.py` | 3,969 | End-to-end CLI behavior tests across most command groups | Main compatibility contract for CLI and `.p2p` artifacts. |
| MCP tests | `tests/test_mcp.py` | 1,622 | MCP tool surface and behavior tests | Main compatibility contract for MCP schemas, dispatch, and permission-gated tools. |

### Current File Responsibility Matrix

| File or area | Current responsibilities | Current type | Refactoring concern |
| --- | --- | --- | --- |
| `src/p2p_engine/__main__.py` | Module entrypoint into CLI | Presentation/bootstrap | Low concern; should remain thin. |
| `src/p2p_engine/cli.py` | Typer app composition, command options, command handlers, printing, error handling, calls into `P2PWorkspace` | Presentation plus orchestration | Should not receive new domain logic; split after service boundaries exist. |
| `src/p2p_engine/storage/filesystem.py` | Workspace facade, persistence, lifecycle workflows, generated artifact rendering, validation, registry generation, project/spec/work/choice/intake behavior | Facade, application, persistence, rendering, validation | Highest refactoring concern; needs method map before code movement. |
| `src/p2p_engine/storage/git.py` | Git command subprocess adapter | Adapter/helper | Small but behavior-critical; future rich errors should preserve current callers. |
| `src/p2p_engine/mcp/server.py` | MCP stdio server wrapper | Transport/bootstrap | Lower concern; keep transport separate from tool behavior. |
| `src/p2p_engine/mcp/tools.py` | MCP tool declaration and dispatch into `P2PWorkspace`, consent orchestration for permission-gated tools | MCP schema, presentation, orchestration | Large and compatibility-sensitive; split only after service/tool handler boundaries exist. |
| `src/p2p_engine/core/` | Small domain dataclasses and enums | Domain model | Candidate home for stable domain contracts, but currently too small to absorb behavior directly. |
| `src/p2p_engine/exporters/` | Minimal exporter helpers | Adapter/renderer | Candidate home for project/spec export rendering now concentrated in `filesystem.py`. |
| `src/p2p_engine/prompts/` | Prompt renderers | Renderer/helper | Already reasonably separated; keep as independent prompt rendering layer. |
| `tests/test_cli.py` | CLI compatibility and storage artifact behavior | Tests | Must remain the main guard for CLI-visible behavior during refactoring. |
| `tests/test_mcp.py` | MCP tool compatibility, consent-gated behavior, JSON-RPC behavior | Tests | Must remain the main guard for MCP behavior during refactoring. |

## Runtime Versus Generated/Planning State

### Runtime Source

Runtime implementation lives under:

- `src/p2p_engine/`
- `tests/`
- packaging and entrypoint metadata such as `pyproject.toml`

Only changes to these areas can implement runtime behavior.

### Managed P2P State

Managed project governance and generated project memory live under `.p2p/`.
Those files are not runtime implementation. They can be refreshed by P2P
commands and can provide accepted direction, but they must not be treated as
proof that source behavior has changed.

### Maintained Documentation

Maintained docs under `docs/`, `README.md`, `AGENTS.md`, and agent instruction
files can define contributor guidance or public behavior. They are evidence for
documentation and process requirements, but not for runtime behavior unless
paired with source/tests.

### Local Development Specs

Local development specs live under `specs/`. They define requirements, design,
tasks, binding reports, and evidence decisions for this repository. They are
not release artifacts and do not implement runtime behavior.

## P2PWorkspace Method Map

### Raw Method Index

Measured from `src/p2p_engine/storage/filesystem.py`.

- Public methods: 131
- Class-private/helper methods: 67
- Total class methods: 198

This is a raw index for navigation. Responsibility grouping starts in T006.

#### Public Methods

| Line | Method |
| ---: | --- |
| 734 | `init_project` |
| 824 | `refresh_agent_instructions` |
| 880 | `agent_integrations_list` |
| 894 | `agent_integration_show` |
| 904 | `install_agent_integrations` |
| 1013 | `uninstall_agent_integration` |
| 1175 | `permissions_show` |
| 1181 | `permissions_actor_add` |
| 1211 | `consent_grant` |
| 1264 | `consent_request` |
| 1311 | `consent_show` |
| 1318 | `consent_statuses` |
| 1327 | `consent_revoke` |
| 1340 | `consent_validate` |
| 1378 | `consent_consume` |
| 1391 | `consent_mark_used_with_error` |
| 1461 | `status` |
| 1488 | `remote_profile` |
| 1511 | `configure_remote_profile` |
| 1553 | `sync_status` |
| 1617 | `sync_fetch` |
| 1630 | `sync_pull` |
| 1647 | `sync_push` |
| 1664 | `proposal_summaries` |
| 1670 | `show_proposal` |
| 1685 | `commit_proposal_draft` |
| 1700 | `branch_proposal` |
| 1766 | `show_proposal_branch` |
| 1785 | `publish_proposal_branch` |
| 1852 | `request_proposal_branch_review` |
| 1892 | `retire_proposal_branch` |
| 1919 | `accept_proposal_branch` |
| 1925 | `reject_proposal_branch` |
| 1971 | `merge_proposal_branch` |
| 2037 | `continue_merge_proposal_branch` |
| 2084 | `abort_merge_proposal_branch` |
| 2100 | `finalize_proposal_branch` |
| 2155 | `cleanup_proposal_branch` |
| 2265 | `scan_proposal_branches` |
| 2303 | `check` |
| 2319 | `validate` |
| 2542 | `readiness_profile` |
| 2562 | `read_proposal_readiness` |
| 2596 | `write_proposal_readiness` |
| 2604 | `record_proposal_readiness_override` |
| 2629 | `refresh_proposal_readiness` |
| 2652 | `initialize_proposal_readiness` |
| 2763 | `create_proposal` |
| 2766 | `create_proposal_with_details` |
| 2814 | `update_proposal` |
| 2841 | `add_contribution` |
| 2871 | `list_contributions` |
| 2898 | `record_decision` |
| 2924 | `generate_prompt` |
| 2970 | `import_exploration` |
| 2991 | `exploration_status` |
| 3020 | `import_artifact` |
| 3039 | `import_impact` |
| 3067 | `init_governance` |
| 3103 | `governance_status` |
| 3123 | `record_vote` |
| 3166 | `vote_status` |
| 3181 | `record_precedent` |
| 3202 | `refresh_project_state` |
| 3260 | `project_state_status` |
| 3278 | `show_project_state` |
| 3291 | `create_project_brief_prompt` |
| 3305 | `import_project_brief` |
| 3333 | `show_project_brief` |
| 3339 | `refresh_project_assessment` |
| 3346 | `show_project_assessment` |
| 3376 | `init_project_rubrics` |
| 3396 | `init_project_rubrics_preview` |
| 3401 | `show_project_rubrics` |
| 3420 | `refresh_definition_maturity` |
| 3427 | `show_definition_maturity` |
| 3752 | `context_packet` |
| 3964 | `refresh_software_spec` |
| 4022 | `software_spec_statuses` |
| 4047 | `show_software_spec` |
| 4053 | `create_software_spec_prompt` |
| 4069 | `import_software_spec` |
| 4090 | `export_software_spec` |
| 4128 | `software_spec_export_statuses` |
| 4158 | `show_software_spec_export` |
| 4166 | `validate_software_spec_export` |
| 4225 | `create_work_plan` |
| 4252 | `work_statuses` |
| 4285 | `work_summaries` |
| 4297 | `show_work` |
| 4384 | `branch_work` |
| 4450 | `retire_work` |
| 4475 | `submit_work` |
| 4537 | `review_work` |
| 4596 | `publish_work` |
| 4658 | `request_external_work_review` |
| 4738 | `accept_work` |
| 4838 | `continue_accept_work` |
| 4896 | `abort_accept_work` |
| 4930 | `finalize_work` |
| 4988 | `cleanup_work` |
| 5084 | `scan_work_branches` |
| 5129 | `next_actions` |
| 5139 | `next_action_add` |
| 5179 | `next_action_complete` |
| 5182 | `next_action_retire` |
| 5185 | `next_actions_refresh` |
| 5204 | `record_conflict` |
| 5239 | `conflict_status` |
| 5252 | `create_change_set` |
| 5310 | `change_set_statuses` |
| 5331 | `change_set_policy` |
| 5352 | `show_change_set` |
| 5370 | `update_change_set_status` |
| 5392 | `change_set_tasks` |
| 5408 | `refresh_registries` |
| 5469 | `registry_status` |
| 5530 | `show_registry` |
| 5555 | `create_intake_prompt` |
| 5600 | `import_intake` |
| 5629 | `intake_statuses` |
| 5647 | `create_intake_apply_plan` |
| 5695 | `show_intake_apply_plan` |
| 5710 | `run_intake_apply_action` |
| 5799 | `create_choice` |
| 5891 | `choice_statuses` |
| 5913 | `show_choice` |
| 5938 | `discover_choices` |
| 5991 | `block_choice` |
| 6033 | `unblock_choice` |
| 6056 | `decide_choice` |

#### Class-Private And Helper Methods

| Line | Method |
| ---: | --- |
| 730 | `__init__` |
| 1071 | `_agent_integrations_path` |
| 1074 | `_agent_integrations_registry` |
| 1084 | `_write_agent_integrations_registry` |
| 1089 | `_agent_registry_file_map` |
| 1105 | `_build_agent_integrations_registry` |
| 1143 | `_agent_integration_status` |
| 1411 | `_project_name` |
| 1419 | `_repository_mode` |
| 1429 | `_permissions_path` |
| 1432 | `_consent_path` |
| 1436 | `_next_consent_id` |
| 1448 | `_set_repository_mode` |
| 1931 | `_decide_proposal_branch` |
| 3446 | `_compute_definition_maturity` |
| 3532 | `_definition_evidence_records` |
| 3564 | `_criterion_matches` |
| 3585 | `_compute_project_assessment` |
| 3843 | `_default_context_artifacts` |
| 3882 | `_context_artifact` |
| 3937 | `_context_allowed_commands` |
| 4197 | `_project_definition` |
| 4313 | `_work_summary_from_manifest` |
| 4359 | `_work_summary_from_scan` |
| 5076 | `_scanned_work_items` |
| 6109 | `_accepted_proposals` |
| 6139 | `_proposal_registry_records` |
| 6164 | `_decision_registry_records` |
| 6185 | `_change_registry_records` |
| 6218 | `_choice_registry_records` |
| 6277 | `_relation_registry_records` |
| 6317 | `_artifact_registry_records` |
| 6351 | `_readiness_registry_records` |
| 6374 | `_changes_for_proposal` |
| 6382 | `_intake_context` |
| 6422 | `_project_brief_context` |
| 6496 | `_intake_apply_action_metadata` |
| 6526 | `_next_actions_from_project_file` |
| 6543 | `_next_actions_path` |
| 6546 | `_next_actions_log_path` |
| 6549 | `_read_next_actions_payload` |
| 6555 | `_write_next_actions_payload` |
| 6560 | `_next_action_from_record` |
| 6571 | `_normalize_next_action_record` |
| 6581 | `_next_curated_next_action_id` |
| 6591 | `_close_next_action` |
| 6633 | `_dedupe_next_actions` |
| 6644 | `_fallback_next_actions` |
| 6776 | `_active_choice_blocker_actions` |
| 6803 | `_next_proposal_id` |
| 6812 | `_find_proposal_dir` |
| 6827 | `_duplicate_proposal_ids` |
| 6839 | `_proposal_branch_metadata` |
| 6847 | `_proposal_branch_metadata_from_local_ref` |
| 6871 | `_remote_proposal_ids` |
| 6888 | `_auto_renumber_proposal_branch` |
| 6945 | `_next_available_proposal_id` |
| 6958 | `_sync_remote` |
| 6964 | `_require_sync_remote` |
| 6973 | `_next_change_id` |
| 6982 | `_find_change_dir` |
| 6993 | `_next_intake_id` |
| 7002 | `_find_intake_dir` |
| 7011 | `_next_choice_id` |
| 7020 | `_find_choice_dir` |
| 7031 | `_next_work_id` |
| 7040 | `_find_work_dir` |

## Target Modules

Covered by T015-T020.

### Service Boundary Template

Covered by T015.

Use this template for every candidate service or module boundary created during
this refactoring. The goal is to make extraction decisions explicit before code
moves, so each future implementation task can preserve behavior through the
`P2PWorkspace` facade.

```text
#### Boundary: <candidate module path>

Status:
- Proposed | Ready for extraction | Extracted | Deferred

Owns:
- Runtime responsibilities this service owns after extraction.

Does Not Own:
- Nearby responsibilities that must remain outside the service.

Inputs:
- Domain IDs, option values, parsed payloads, service dependencies, adapters,
  or facade arguments consumed by this service.

Outputs:
- Dataclasses, dictionaries, paths, markdown/yaml payloads, status rows, or
  errors returned to the facade, CLI, or MCP layer.

Storage Paths:
- `.p2p/...` paths read or written by this service.
- State files whose format must remain compatible.

Side Effects:
- Filesystem writes, Git operations, remote operations, commits, pushes,
  audit-log writes, generated artifacts, or managed branch changes.

Facade Methods:
- `P2PWorkspace` public methods that must remain available and delegate here.
- Significant private helpers to move or keep as facade-only glue.

CLI/MCP Surface:
- Commands and MCP tool names whose current behavior depends on this boundary.

Compatibility Tests:
- Existing tests that must pass unchanged after extraction.
- Missing tests that should be added before extraction.

Dependencies:
- Services, adapters, renderers, validators, or domain helpers this boundary
  may call.

Extraction Risks:
- Behavior, path, format, permission, Git, readiness, or governance risks.

Extraction Notes:
- Sequencing constraints, migration notes, or compatibility requirements.
```

Boundary rules:

- Keep `P2PWorkspace` as the public compatibility facade until a later feature
  explicitly changes CLI or MCP wiring.
- Do not let services call Typer, Rich, or MCP serialization code. Presentation
  belongs outside services.
- Do not let renderers read `.p2p` state directly. Renderers should receive a
  ready context object or primitive data.
- Do not let validators perform writes. Validators should return success or
  raise current-compatible errors.
- Keep filesystem paths centralized enough that storage layout changes can be
  reviewed deliberately.
- Keep Git and remote side effects behind adapters/services with explicit guard
  checks and audit behavior.
- Treat governance decisions as owner-controlled even when services expose the
  mechanics for recording them.
- Preserve current dataclass return shapes and error messages where CLI/MCP
  tests assert them.

Recommended boundary status meanings:

- `Proposed`: boundary is mapped but not yet ready for code movement.
- `Ready for extraction`: tests and sequencing are sufficient for a follow-up
  implementation task.
- `Extracted`: runtime code has moved and facade delegation is in place.
- `Deferred`: boundary is understood but should wait for another feature,
  missing tests, or a product decision.

### Permissions And Consent Target Boundaries

Covered by T016.

#### Boundary: `p2p_engine.services.permissions`

Status:
- Ready for extraction.

Owns:
- Permission policy read/write behavior for `.p2p/project/permissions.yml`.
- Default permission policy payload generation during project initialization.
- Actor identity normalization, role normalization, actor kind normalization,
  and actor add/update semantics.
- Validation support for malformed permission policy payloads.

Does Not Own:
- Consent receipt lifecycle.
- MCP permission-gated execution.
- Git audit commits or pushes.
- Owner governance decisions; it only stores declared actors and roles.

Inputs:
- Project root or filesystem adapter rooted at `.p2p`.
- Owner name/email values during initialization.
- Actor name, optional email, role, kind, and tool class values.
- Existing permissions payload.

Outputs:
- `PermissionPolicy` and `PermissionActor` compatible return objects.
- Updated permissions YAML payload.
- Current-compatible `ValueError` messages for invalid roles, actor kinds, and
  invalid policy structure.

Storage Paths:
- `.p2p/project/permissions.yml`

Side Effects:
- Writes permissions policy when initializing defaults or adding/updating
  actors.
- No Git, remote, consent, or proposal side effects.

Facade Methods:
- `P2PWorkspace.permissions_show`
- `P2PWorkspace.permissions_actor_add`
- `_permissions_path`
- `_permissions_payload`
- `_identity_slug`
- `_normalize_permission_role`
- `_normalize_actor_kind`

CLI/MCP Surface:
- `permissions show`
- `permissions actor add`
- `p2p_permissions_show`
- `p2p_project_init` indirectly through default policy creation.

Compatibility Tests:
- `tests/test_cli.py::test_cli_init_owner_populates_permissions_policy`
- `tests/test_cli.py::test_cli_permissions_actor_and_consent_receipts`
- `tests/test_cli.py::test_cli_validate_reports_invalid_permissions_policy`
- `tests/test_mcp.py::test_mcp_permission_and_consent_read_tools`
- Missing before extraction: focused unit tests for actor id normalization and
  role/kind normalization if service-level tests are introduced.

Dependencies:
- Filesystem adapter or path resolver.
- YAML read/write helpers.
- Domain dataclasses for permission policy and actors.

Extraction Risks:
- Accidental policy format drift.
- Changing generated owner actor ids during initialization.
- Weakening validation for malformed policies.

Extraction Notes:
- Extract before `consent` if doing very small steps, because consent validation
  depends on actors and owner roles.
- Keep initialization behavior compatible: project init must still create the
  same default owner/admin policy.

#### Boundary: `p2p_engine.services.consent`

Status:
- Ready for extraction after or together with `permissions`.

Owns:
- Consent id allocation and receipt path resolution.
- Consent grant, request, show, list/status, revoke, validate, consume, and
  used-with-error transitions.
- Consent operation normalization and consent id normalization.
- Receipt payload-to-dataclass mapping.
- Expiry handling, including mutating expired receipts to `expired` during
  validation.

Does Not Own:
- Permission policy authoring, except reading actor/role information through
  the permissions service.
- MCP audit commit/push behavior.
- Execution of permission-gated operations.
- CLI/Rich output or MCP serialization.

Inputs:
- Operation, target, actor id, optional approver id, rationale, duration, and
  receipt id.
- Current permission policy from `permissions`.
- Current time provider if introduced for testability.

Outputs:
- `ConsentReceipt` compatible return objects.
- Validation success/failure with existing error semantics.
- Updated consent YAML receipts.

Storage Paths:
- `.p2p/consents/CONSENT-XXX/consent.yml`

Side Effects:
- Creates consent directories and writes consent receipts.
- Updates receipt status to `revoked`, `expired`, `consumed`, or
  `used_with_error`.
- No Git commits, pushes, proposal changes, or sync changes.

Facade Methods:
- `P2PWorkspace.consent_grant`
- `P2PWorkspace.consent_request`
- `P2PWorkspace.consent_show`
- `P2PWorkspace.consent_statuses`
- `P2PWorkspace.consent_revoke`
- `P2PWorkspace.consent_validate`
- `P2PWorkspace.consent_consume`
- `P2PWorkspace.consent_mark_used_with_error`
- `_consent_path`
- `_next_consent_id`
- `_normalize_consent_operation`
- `_normalize_consent_id`
- `_consent_receipt_from_payload`

CLI/MCP Surface:
- `consent grant`
- `consent show`
- `consent status`
- `consent revoke`
- `p2p_consent_request`
- `p2p_consent_status`
- `p2p_consent_show`
- all permission-gated MCP tools that validate and consume consent.

Compatibility Tests:
- `tests/test_cli.py::test_cli_permissions_actor_and_consent_receipts`
- `tests/test_cli.py::test_cli_consent_grant_requires_owner_approver`
- `tests/test_mcp.py::test_mcp_remote_configure_and_consent_request_are_write_safe`
- `tests/test_mcp.py::test_mcp_requested_consent_does_not_authorize_publish`
- `tests/test_mcp.py::test_mcp_draft_proposal_decision_requires_granted_consent`
- `tests/test_mcp.py::test_mcp_draft_proposal_accept_and_defer_consume_matching_consent`
- `tests/test_mcp.py::test_mcp_proposal_publish_requires_and_consumes_consent`
- `tests/test_mcp.py::test_mcp_proposal_publish_rejects_actor_mismatch_without_consuming_consent`
- `tests/test_mcp.py::test_mcp_sync_push_requires_and_consumes_consent`
- `tests/test_mcp.py::test_mcp_sync_pull_requires_and_consumes_consent`
- `tests/test_mcp.py::test_mcp_proposal_request_review_requires_and_consumes_consent`
- `tests/test_mcp.py::test_mcp_proposal_merge_requires_and_consumes_consent`
- `tests/test_mcp.py::test_mcp_proposal_finalize_requires_and_consumes_consent`
- `tests/test_mcp.py::test_mcp_proposal_reject_and_cleanup_require_consent`
- `tests/test_mcp.py::test_mcp_permission_and_consent_read_tools`
- Missing before extraction: focused unit tests for expiry mutation and
  used-with-error transition if service-level tests are introduced.

Dependencies:
- `p2p_engine.services.permissions`
- Filesystem adapter or path resolver.
- YAML read/write helpers.
- Domain dataclasses for consent receipts.

Extraction Risks:
- Accidentally allowing `requested` receipts to authorize execution.
- Consuming receipts on actor/target mismatch.
- Losing used-with-error marking after partial side effects.
- Changing sequential `CONSENT-XXX` allocation.

Extraction Notes:
- This service can be extracted without moving MCP audit code if the facade
  methods remain stable.
- Keep receipt status transitions narrow and explicit.

#### Boundary: `p2p_engine.mcp.consent_audit`

Status:
- Proposed.

Owns:
- MCP-side orchestration around permission-gated operations: validate consent,
  run the operation, consume the receipt, and write/push audit commits when
  configured.
- Handling head-change or partial-side-effect cases by marking consent with
  error.

Does Not Own:
- Permission policy storage.
- Consent receipt storage rules.
- Core operation implementations such as sync, proposal publish, merge, or
  cleanup.

Inputs:
- Workspace facade.
- Consent id, operation, target, actor id.
- Operation callback/result.
- Git adapter or current MCP helper functions.

Outputs:
- Operation result payload for MCP.
- Audit commit/push result metadata where relevant.
- Consent error marking when audit cannot complete safely.

Storage Paths:
- Consent receipts through `P2PWorkspace` facade.
- Git repository history for audit commits.

Side Effects:
- Git commits with message `P2P consent consume CONSENT-XXX`.
- Optional remote push behavior.
- Consent consume or used-with-error status changes through the facade.

Facade Methods:
- Calls `consent_validate`, `consent_consume`, and
  `consent_mark_used_with_error`.
- Does not become a `P2PWorkspace` method unless a later MCP refactor requires
  it.

CLI/MCP Surface:
- MCP-only permission-gated tools, including sync pull/push and proposal
  branch lifecycle tools.

Compatibility Tests:
- All MCP consent-consuming tests listed for `p2p_engine.services.consent`.
- Missing before extraction: explicit audit helper unit tests may be useful
  only after MCP tool registry modularization begins.

Dependencies:
- `P2PWorkspace` facade.
- Git adapter or existing MCP Git helper functions.

Extraction Risks:
- Mixing core governance state with MCP transport concerns.
- Losing audit commits or push behavior.
- Marking consent consumed before operation side effects are durable.

Extraction Notes:
- Do not extract this before the core `permissions` and `consent` services
  unless the implementation is limited to moving existing MCP helper functions
  behind an internal helper module.

### Proposal And Readiness Target Boundaries

Covered by T017.

#### Boundary: `p2p_engine.services.proposals`

Status:
- Proposed.

Owns:
- Proposal id allocation, duplicate id detection, proposal directory lookup,
  create/list/show/update behavior, contribution add/list behavior, proposal
  metadata parsing, and proposal summary/detail mapping.
- Draft proposal content changes that do not decide governance state.
- Proposal-local choice display and registry-facing proposal metadata.

Does Not Own:
- Proposal branch Git lifecycle.
- Owner acceptance/rejection/defer mechanics beyond delegating to governance
  status transitions.
- Readiness scoring and readiness profile computation.
- Registry refresh as a whole, except exposing proposal records to registry
  services.

Inputs:
- Proposal title, problem, goal, proposal text, acceptance text, non-goals,
  optional source/context metadata, contribution text, and proposal id.
- Filesystem adapter rooted at `.p2p`.

Outputs:
- Proposal summary/detail dataclasses and contribution records.
- Proposal markdown/frontmatter payloads.
- Existing clean errors for missing or ambiguous duplicate proposal ids.

Storage Paths:
- `.p2p/proposals/PROP-XXX/proposal.md`
- `.p2p/proposals/PROP-XXX/contributions.yml`
- Proposal-local auxiliary files that are read for details or registries.

Side Effects:
- Creates proposal directories and markdown files.
- Updates draft proposal content.
- Appends proposal contributions.
- No Git branch, remote, sync, readiness override, or governance decision side
  effects.

Facade Methods:
- `proposal_summaries`
- `show_proposal`
- `create_proposal`
- `update_proposal`
- `add_proposal_contribution`
- `proposal_contributions`
- `_next_proposal_id`
- `_find_proposal_dir`
- `_duplicate_proposal_ids`
- proposal markdown/frontmatter parsing helpers used only by proposals.

CLI/MCP Surface:
- `proposal list`
- `proposal show`
- `proposal create`
- `proposal update`
- `proposal contribution add`
- `proposal contribution list`
- `p2p_proposal_list`
- `p2p_proposal_show`
- `p2p_proposal_create`
- `p2p_proposal_update`
- `p2p_proposal_contribution_add`

Compatibility Tests:
- `tests/test_cli.py::test_cli_proposal_list_show_and_choice_registry_output`
- `tests/test_cli.py::test_cli_missing_proposal_returns_clean_error`
- `tests/test_cli.py::test_cli_lists_proposal_contributions`
- `tests/test_cli.py::test_cli_validate_reports_duplicate_proposal_ids_as_error`
- `tests/test_cli.py::test_cli_registry_refresh_rejects_duplicate_proposal_ids`
- `tests/test_cli.py::test_cli_proposal_show_reports_ambiguous_duplicate_id_guidance`
- `tests/test_mcp.py::test_mcp_proposal_create_creates_draft_only`
- `tests/test_mcp.py::test_mcp_proposal_update_refines_draft_without_deciding`
- `tests/test_mcp.py::test_mcp_proposal_contribution_add_does_not_decide`
- `tests/test_mcp.py::test_mcp_validate_reports_duplicate_proposal_ids`

Dependencies:
- Filesystem adapter or path resolver.
- Markdown/frontmatter/YAML helpers.
- Registry service later consumes proposal summaries.

Extraction Risks:
- Accidentally treating draft updates as governance decisions.
- Changing proposal id allocation or duplicate-id guidance.
- Breaking proposal-local choice/registry output.

Extraction Notes:
- This service should be extracted after permissions/consent if branch or MCP
  write-safe operations remain consent-gated.
- Keep proposal branch metadata outside this service; branch operations are
  Git side-effecting and belong to T019.

#### Boundary: `p2p_engine.services.proposal_governance`

Status:
- Proposed.

Owns:
- Proposal decision mechanics for accept, reject, defer, direct decision
  shortcuts, readiness override metadata recorded during acceptance, and
  governance-adjacent proposal status transitions.
- Governance support flows that record SWOT, votes, precedents, and decisions
  when they directly affect proposal decision context.

Does Not Own:
- Readiness score computation.
- Proposal markdown authoring for draft updates.
- Proposal branch accept/reject/merge/finalize/cleanup lifecycle.
- Owner authorization policy; owner control remains a product/governance rule
  enforced at CLI/MCP boundary and by command semantics.

Inputs:
- Proposal id, decision/status, actor/owner metadata, rationale, optional
  readiness override fields, and governance artifact payloads.

Outputs:
- Updated proposal decision/status payloads.
- Governance artifact summaries and current-compatible CLI/MCP payloads.

Storage Paths:
- `.p2p/proposals/PROP-XXX/proposal.md`
- Governance artifact paths already used by SWOT, vote, precedent, and
  decision flows.

Side Effects:
- Writes proposal decision/status metadata.
- Writes governance support artifacts.
- No Git operations and no branch metadata changes.

Facade Methods:
- proposal accept/reject/defer/decision shortcut methods;
- governance SWOT/vote/precedent/decision methods mapped in earlier proposal
  lifecycle sections;
- readiness override recording that currently happens during proposal
  acceptance.

CLI/MCP Surface:
- `proposal accept`
- `proposal reject`
- `proposal defer`
- proposal decision shortcuts
- governance SWOT/vote/precedent/decision commands
- `p2p_proposal_accept`
- `p2p_proposal_reject`
- `p2p_proposal_defer`

Compatibility Tests:
- `tests/test_cli.py::test_cli_proposal_accept_can_record_readiness_override`
- `tests/test_cli.py::test_cli_proposal_decision_shortcuts`
- `tests/test_cli.py::test_cli_governance_swot_vote_and_precedent_flow`
- `tests/test_mcp.py::test_mcp_draft_proposal_decision_requires_granted_consent`
- `tests/test_mcp.py::test_mcp_draft_proposal_accept_and_defer_consume_matching_consent`

Dependencies:
- `p2p_engine.services.proposals`
- `p2p_engine.services.readiness` for advisory readiness information and
  override metadata shape.
- Consent gating remains outside the service for MCP.

Extraction Risks:
- Blurring owner-controlled governance decisions with advisory services.
- Losing readiness override traceability.
- Mixing branch governance decisions with proposal text decisions.

Extraction Notes:
- Keep this smaller than the full proposal lifecycle at first. It should not
  absorb branch accept/reject, because those operate on managed Git branches.

#### Boundary: `p2p_engine.services.readiness`

Status:
- Proposed.

Owns:
- Readiness profile initialization, refresh, status, show/explain, score/gate
  computation, missing artifact analysis, advisory status output, and override
  metadata handling.
- Readiness prompt generation only where it directly uses readiness context.

Does Not Own:
- Final owner decision to accept or reject a proposal.
- Proposal content editing.
- Change Set creation.
- Project maturity assessment or rubrics, except where readiness profile inputs
  reference rubric-like gates.

Inputs:
- Proposal id.
- Readiness profile configuration.
- Proposal details, supporting artifacts, choices/blockers, and optional
  override metadata.

Outputs:
- Readiness status/detail/explanation dataclasses and serialized payloads.
- Refreshed readiness files with current score/gate data.
- Advisory warnings used by CLI/MCP.

Storage Paths:
- Proposal readiness artifacts under each proposal directory.
- Readiness profile/configuration files currently initialized by project setup.

Side Effects:
- Writes refreshed readiness artifacts.
- May write initial readiness profile/configuration.
- No proposal decision, Git, remote, or consent side effects.

Facade Methods:
- readiness profile init/show helpers;
- proposal readiness status/refresh/explain methods;
- readiness override read/write helpers used by proposal acceptance;
- readiness prompt/context helpers that are not part of generic prompt import.

CLI/MCP Surface:
- `proposal readiness show`
- `proposal readiness refresh`
- `proposal readiness explain`
- `p2p_proposal_readiness_show`
- `p2p_proposal_readiness_refresh`
- `p2p_proposal_readiness_explain`

Compatibility Tests:
- `tests/test_cli.py::test_cli_proposal_readiness_status_refresh_and_explain`
- `tests/test_cli.py::test_cli_proposal_accept_can_record_readiness_override`
- `tests/test_mcp.py::test_mcp_proposal_readiness_tools_are_advisory`
- Next-action tests that depend on low readiness fallbacks:
  `tests/test_cli.py::test_cli_next_falls_back_to_improve_low_readiness_draft`

Dependencies:
- `p2p_engine.services.proposals`
- Choices/blockers service for advisory blockers.
- Filesystem adapter and YAML/Markdown helpers.

Extraction Risks:
- Accidentally turning advisory readiness into a hard governance gate.
- Stale readiness not being refreshed before CLI/MCP explanation.
- Losing override metadata during proposal acceptance.

Extraction Notes:
- Readiness can be extracted independently from proposal branch Git work.
- Keep all readiness language advisory unless the owner explicitly overrides or
  accepts despite weak readiness.

### Project State, Registry, And Export Target Boundaries

Covered by T018.

#### Boundary: `p2p_engine.services.project_state`

Status:
- Proposed.

Owns:
- Generated project state refresh/show/status behavior under `.p2p/project`.
- Rationalized project memory derived from accepted proposals, decisions,
  Change Sets, choices, rubrics, assessments, maturity, conflicts, and
  operational brief artifacts.
- Project brief show/import state where it is consumed as project context.

Does Not Own:
- Raw proposal lifecycle or proposal decision mechanics.
- Registry file generation as an indexing concern.
- Software-spec generation or downstream export rendering.
- Project initialization.

Inputs:
- Accepted proposal summaries/details.
- Decision and Change Set summaries.
- Choice/conflict/readiness/maturity evidence.
- Existing project metadata from `.p2p/project.yml`.

Outputs:
- Generated project state files and section content.
- Project state status rows.
- Context-ready project state snippets for other services.

Storage Paths:
- `.p2p/project/`
- `.p2p/project.yml` for read-only project metadata where needed.

Side Effects:
- Writes generated project state files.
- No governance decisions, Git operations, or spec export writes.

Facade Methods:
- project refresh/show/status methods mapped in T012.
- project brief show/import may remain in prompt/import services until a later
  project-context split is implemented.

CLI/MCP Surface:
- `project refresh`
- `project show`
- `project status`
- `p2p_project_refresh`
- `p2p_project_show`
- `p2p_project_status`

Compatibility Tests:
- `tests/test_cli.py::test_cli_project_refresh_and_show`
- `tests/test_cli.py::test_cli_project_brief_prompt_import_and_show`
- `tests/test_mcp.py::test_mcp_change_project_registry_and_remote_read_tools`
- `tests/test_mcp.py::test_mcp_project_brief_prompt_and_show`

Dependencies:
- `proposals`, `proposal_governance`, `change_sets`, `choices`, `conflicts`,
  `readiness`, and `project_rubrics` services once extracted.
- Filesystem adapter and markdown/YAML helpers.

Extraction Risks:
- Treating draft proposals as accepted truth.
- Losing project-state traceability back to accepted artifacts.
- Creating circular dependencies with registries or spec export.

Extraction Notes:
- Extract after proposal/readiness summaries are stable.
- Keep generated project state distinct from local implementation specs under
  root `specs/`.

#### Boundary: `p2p_engine.services.registries`

Status:
- Proposed.

Owns:
- Registry refresh/status/show behavior.
- Registry freshness metadata and record counts.
- Generated registry records for proposals, decisions, changes, choices,
  relations, artifacts, readiness, scanned branches, and other indexed state.

Does Not Own:
- The domain lifecycle that creates source artifacts.
- Validation of every domain artifact beyond registry shape/freshness checks.
- Git branch scanning itself, except consuming scan records emitted by branch
  services.

Inputs:
- Domain summaries from proposals, choices, Change Sets, Work, readiness,
  conflicts, relations, and scanned branch services.
- Current generated registry files.

Outputs:
- Registry YAML/markdown files.
- Registry status rows and record counts.
- Logical registry content returned by `show`.

Storage Paths:
- Generated registry files under `.p2p/project` or the current registry output
  paths mapped in T012.

Side Effects:
- Writes generated registry files and freshness metadata.
- No Git, remote, governance decision, or export side effects.

Facade Methods:
- registry refresh/status/show methods mapped in T012.
- registry helper functions that build or normalize records.

CLI/MCP Surface:
- `registry refresh`
- `registry status`
- `registry show`
- registry-related MCP read/write-safe tools already mapped in T012.

Compatibility Tests:
- `tests/test_cli.py::test_cli_registry_refresh_rejects_duplicate_proposal_ids`
- `tests/test_cli.py::test_cli_registry_includes_choice_artifacts`
- `tests/test_mcp.py::test_mcp_change_project_registry_and_remote_read_tools`

Dependencies:
- Domain services provide summaries; registry service should not read every
  domain layout directly after extraction.
- Filesystem adapter and YAML helpers.

Extraction Risks:
- Making registries stale by bypassing freshness metadata.
- Reintroducing broad `.p2p` scanning inside multiple services.
- Coupling registry generation to presentation output.

Extraction Notes:
- Registry extraction should wait until at least proposal, choice, Change Set,
  and Work summaries have stable service facades.

#### Boundary: `p2p_engine.services.software_specs`

Status:
- Proposed.

Owns:
- Deterministic `software-spec` refresh/status/show/prompt/import behavior.
- Required normalized spec artifact set and import validation for
  `index.md`, `requirements.md`, `design.md`, `commands.yml`,
  `data-model.yml`, `acceptance.md`, and `provenance.yml`.

Does Not Own:
- Generic/OpenSpec/Spec Kit export rendering.
- Work plan creation.
- P2P Change Set creation.
- Local root `specs/` implementation tasks.

Inputs:
- Change Set id and Change Set details.
- Included accepted proposal details.
- Change Set tasks and frontmatter.
- Optional refined spec source directory for import.

Outputs:
- `SoftwareSpecStatus` and `SoftwareSpecPrompt` compatible return objects.
- Normalized spec artifacts.

Storage Paths:
- `.p2p/outputs/software-spec/{CHANGE-ID}/`

Side Effects:
- Writes normalized spec artifacts and refinement prompt.
- Copies validated imported spec artifacts.
- No export, Work, Git, or governance side effects.

Facade Methods:
- `refresh_software_spec`
- `software_spec_statuses`
- `show_software_spec`
- `create_software_spec_prompt`
- `import_software_spec`
- `_software_spec_required_files`
- software-spec markdown/YAML render helpers.

CLI/MCP Surface:
- `spec refresh`
- `spec status`
- `spec show`
- `spec prompt`
- `spec import`
- `p2p_spec_refresh`
- `p2p_spec_status`
- `p2p_spec_show`
- `p2p_spec_prompt`

Compatibility Tests:
- `tests/test_cli.py::test_cli_software_spec_refresh_prompt_import_status_and_show`
- `tests/test_mcp.py::test_mcp_write_safe_spec_export_and_work_flow`

Dependencies:
- `change_sets`
- `proposals`
- Filesystem adapter, YAML validators, and software-spec renderers.

Extraction Risks:
- Continuing to generate software-spec for non-software domains after the
  domain-aware export feature changes behavior.
- Changing required file names or YAML top-level keys.
- Blurring P2P export output with local implementation `specs/`.

Extraction Notes:
- Extract before `spec_exports`; export depends on a complete normalized spec.
- Keep current behavior during refactoring, even if later product features
  change target applicability and output location.

#### Boundary: `p2p_engine.services.project_definition`

Status:
- Proposed.

Owns:
- Assembly of generic project definition context from project metadata,
  accepted proposals, draft proposals, governance text, rubrics, assessment,
  maturity, Change Set data, and normalized software-spec artifacts.

Does Not Own:
- Markdown rendering of the final `project.md`.
- Target-specific OpenSpec or Spec Kit prompt rendering.
- Raw project state refresh.

Inputs:
- Change Set detail.
- Normalized software-spec directory.
- Accepted/draft proposal summaries.
- Governance/project/rubric/assessment/maturity files.

Outputs:
- Project definition context object or dictionary consumed by renderers.

Storage Paths:
- Reads `.p2p/project.yml`, `.p2p/governance/*`, `.p2p/project/*`, and
  `.p2p/outputs/software-spec/{CHANGE-ID}/`.

Side Effects:
- None. This boundary should be read-only.

Facade Methods:
- `_project_definition`
- definition context helpers only if they assemble data rather than render.

CLI/MCP Surface:
- Indirect through `spec export`, `spec export-show`, and export validation.

Compatibility Tests:
- `tests/test_mcp.py::test_mcp_project_definition_maturity`
- `tests/test_mcp.py::test_mcp_write_safe_spec_export_and_work_flow`
- CLI spec export assertions inside
  `tests/test_cli.py::test_cli_software_spec_refresh_prompt_import_status_and_show`

Dependencies:
- `software_specs`
- `proposals`
- `project_state` or direct read adapter until project-state extraction exists.

Extraction Risks:
- Letting renderers perform state reads.
- Including draft material as accepted project truth.
- Losing source traceability.

Extraction Notes:
- Keep synthesis read-only and renderer-neutral.

#### Boundary: `p2p_engine.services.spec_exports`

Status:
- Proposed.

Owns:
- Export/status/show/validate behavior for `generic`, `openspec`, and
  `speckit` targets.
- Export target constants, primary show-file selection, and required-file
  validation.
- Dispatch to target renderers.

Does Not Own:
- Normalized software-spec generation.
- Project definition context assembly.
- Work plan creation.
- Domain policy that may later decide which targets are applicable.

Inputs:
- Change Set id.
- Target name.
- Valid normalized software-spec directory.
- Project definition context.

Outputs:
- `SoftwareSpecExportStatus` and `SoftwareSpecExportValidation` compatible
  return objects.
- Target-specific output files.

Storage Paths:
- `.p2p/outputs/spec-export/{CHANGE-ID}/{target}/`

Side Effects:
- Deletes/recreates one target export directory.
- Writes target-specific export files.
- No Work, Git, proposal, or governance side effects.

Facade Methods:
- `export_software_spec`
- `software_spec_export_statuses`
- `show_software_spec_export`
- `validate_software_spec_export`
- `_software_spec_export_targets`
- `_software_spec_export_files`
- `_software_spec_export_artifacts`
- `_software_spec_export_required_files`
- `_software_spec_export_show_file`
- `_project_definition_required_sections`

CLI/MCP Surface:
- `spec export`
- `spec export-status`
- `spec export-show`
- `spec export-validate`
- `p2p_spec_export`
- `p2p_spec_export_status`
- `p2p_spec_export_show`
- `p2p_spec_export_validate`

Compatibility Tests:
- `tests/test_cli.py::test_cli_software_spec_refresh_prompt_import_status_and_show`
- `tests/test_cli.py::test_cli_work_plan_list_and_show`
- `tests/test_mcp.py::test_mcp_write_safe_spec_export_and_work_flow`

Dependencies:
- `software_specs`
- `project_definition`
- target renderers and export validators.

Extraction Risks:
- Removing legacy helper behavior without proving it is unused.
- Changing export path before the visible-output product feature is ready.
- Weakening generic project definition required-section validation.

Extraction Notes:
- Keep target renderers document-oriented. They must not create implementation
  tasks in local `specs/`.
- Work planning should depend on public export validation, not private export
  path assumptions.

#### Boundary: `p2p_engine.services.validation`

Status:
- Deferred.

Owns:
- Cross-domain validation orchestration after enough domain services exist.

Does Not Own:
- Domain-specific mutation or rendering.

Extraction Notes:
- Validation depends on proposal, registry, readiness, permissions, consent,
  agent integration, and generated output boundaries. Keep it as a later
  extraction target even though YAML-shape helpers may move earlier.

### Work, Sync, Git, And Branch Target Boundaries

Covered by T019.

#### Boundary: `p2p_engine.services.remote_profile`

Status:
- Ready for extraction.

Owns:
- Remote profile read/configure behavior from project metadata.
- Repository mode normalization where it directly affects remote profile.
- Validation of remote mode, provider, remote alias, URL, and review request
  metadata.

Does Not Own:
- Git fetch/pull/push.
- Proposal or Work branch lifecycle.
- Consent gating.

Inputs:
- Remote mode/provider/remote/url/review request options.
- Current `.p2p/project.yml` payload.

Outputs:
- `RemoteProfile` compatible return objects.
- Updated project metadata.

Storage Paths:
- `.p2p/project.yml`

Side Effects:
- Writes remote profile metadata.
- No Git command execution.

Facade Methods:
- `remote_profile`
- `configure_remote_profile`
- `_repository_mode`
- `_set_repository_mode`
- `_normalize_repository_mode`
- `_init_remote_profile_payload`

CLI/MCP Surface:
- `project remote show`
- `project remote configure`
- `p2p_project_remote_show`
- `p2p_project_remote_configure`

Compatibility Tests:
- `tests/test_mcp.py::test_mcp_remote_configure_and_consent_request_are_write_safe`
- `tests/test_mcp.py::test_mcp_change_project_registry_and_remote_read_tools`
- CLI remote/sync tests already mapped in T008/T025.

Dependencies:
- Filesystem adapter and YAML helpers.

Extraction Risks:
- Changing local/remote repository mode defaults.
- Breaking sync readiness by changing profile shape.

Extraction Notes:
- This is a low-risk extraction candidate compared with branch lifecycle.

#### Boundary: `p2p_engine.adapters.git`

Status:
- Proposed.

Owns:
- Low-level Git subprocess operations and conversion of Git failures into
  stable adapter results.
- Current branch, clean worktree, changed files, branch existence, merge state,
  local/remote branch listing, ref file reads, fetch/pull/push, branch delete,
  no-commit merge, abort, restore, stage, and commit operations.

Does Not Own:
- P2P domain guard logic.
- Permission/consent.
- Branch metadata writes.
- Owner-controlled governance decisions.

Inputs:
- Repository root, branch/ref/path/remote names, commit messages.

Outputs:
- Current adapter return shapes: bools, strings, lists, `GitStatus`, or `None`
  on collapsed Git failures.

Storage Paths:
- `.git/` through Git commands only.
- No direct `.p2p` writes.

Side Effects:
- Executes Git commands that may mutate worktree, branches, index, commits, or
  remotes, depending on caller.

Facade Methods:
- No direct `P2PWorkspace` public methods. Domain services call the adapter.

CLI/MCP Surface:
- Indirect through sync, proposal branch, Work branch, and consent audit flows.

Compatibility Tests:
- Proposal branch, Work branch, sync, merge/finalize/cleanup, and consent audit
  tests mapped in T008, T013, T019, T025.

Dependencies:
- Standard library subprocess/path behavior.

Extraction Risks:
- Changing failure handling from current `None`/falsey semantics.
- Making side-effecting Git commands easier to call without domain guards.
- Breaking tests that rely on exact branch names and commit behavior.

Extraction Notes:
- Keep the adapter thin. Richer errors should be introduced through a dedicated
  future task with compatibility tests, not bundled into first extraction.

#### Boundary: `p2p_engine.services.sync`

Status:
- Proposed.

Owns:
- Sync status/fetch/pull/push orchestration.
- Clean worktree/current branch/remote URL guard checks.
- Sync remote resolution and readiness validation.

Does Not Own:
- Remote profile persistence.
- Proposal or Work branch lifecycle.
- Consent gating for MCP.

Inputs:
- Remote name override, current Git status, configured remote profile.

Outputs:
- `SyncStatus` compatible return objects and side-effect operation summaries.

Storage Paths:
- Reads `.p2p/project.yml` through remote profile service.
- Mutates Git repo through adapter for fetch/pull/push.

Side Effects:
- Git fetch, fast-forward pull, and push.

Facade Methods:
- `sync_status`
- `sync_fetch`
- `sync_pull`
- `sync_push`
- `_sync_remote`
- `_require_sync_remote`

CLI/MCP Surface:
- `sync status`
- `sync fetch`
- `sync pull`
- `sync push`
- `p2p_sync_status`
- `p2p_sync_fetch`
- `p2p_sync_pull`
- `p2p_sync_push`

Compatibility Tests:
- `tests/test_mcp.py::test_mcp_safe_managed_sync_and_proposal_branch_tools`
- `tests/test_mcp.py::test_mcp_sync_push_requires_and_consumes_consent`
- `tests/test_mcp.py::test_mcp_sync_pull_requires_and_consumes_consent`
- CLI sync tests mapped in T008/T025.

Dependencies:
- `remote_profile`
- `adapters.git`
- Consent gating remains outside the core sync service for MCP.

Extraction Risks:
- Weakening clean-worktree or branch guards.
- Pulling/pushing wrong branch or remote.
- Changing remote URL mismatch reporting.

Extraction Notes:
- Extract after `remote_profile` and before branch services if possible.

#### Boundary: `p2p_engine.services.proposal_branches`

Status:
- Proposed.

Owns:
- Managed proposal branch metadata.
- Proposal draft commit, branch, show branch status, publish, request review,
  retire, branch accept/reject, merge, merge continue/abort, finalize, cleanup,
  scan, remote collision detection, and auto-renumber behavior.

Does Not Own:
- Proposal document create/update/show except through `proposals` service.
- Core proposal governance accept/reject/defer for non-branch proposals.
- Consent gating and MCP audit.
- Low-level Git command implementation.

Inputs:
- Proposal id, actor, base branch, provider, remote, review metadata, owner
  decision rationale, and branch operation flags.

Outputs:
- Proposal branch detail/status dataclasses and metadata payloads.
- Existing errors for dirty worktree, wrong branch, missing remote, collision,
  unresolved conflicts, and invalid lifecycle status.

Storage Paths:
- `.p2p/proposals/PROP-XXX/branch.yml`
- proposal branch scan registry paths mapped in T008/T012.

Side Effects:
- Git branch creation/checkout/rename/merge/abort/delete/push.
- Branch metadata writes.
- Proposal directory renumbering during auto-renumber.

Facade Methods:
- `commit_proposal_draft`
- `branch_proposal`
- `show_proposal_branch`
- `publish_proposal_branch`
- `request_proposal_branch_review`
- `retire_proposal_branch`
- `accept_proposal_branch`
- `reject_proposal_branch`
- `_decide_proposal_branch`
- `merge_proposal_branch`
- `continue_merge_proposal_branch`
- `abort_merge_proposal_branch`
- `finalize_proposal_branch`
- `cleanup_proposal_branch`
- `scan_proposal_branches`
- proposal branch metadata/name/hash helpers.

CLI/MCP Surface:
- `proposal draft-commit`
- `proposal branch`
- `proposal branch-status`
- `proposal publish`
- `proposal request-review`
- `proposal retire-branch`
- `proposal accept-branch`
- `proposal reject-branch`
- `proposal merge`
- `proposal finalize`
- `proposal cleanup`
- `proposal scan`
- matching `p2p_proposal_*` branch tools.

Compatibility Tests:
- `tests/test_cli.py::test_cli_proposal_branch_creates_managed_branch_metadata`
- `tests/test_cli.py::test_cli_proposal_publish_request_review_and_scan`
- `tests/test_cli.py::test_cli_proposal_publish_auto_renumbers_on_remote_id_collision`
- `tests/test_cli.py::test_cli_proposal_publish_detects_collision_from_remote_main`
- `tests/test_cli.py::test_cli_proposal_retire_branch_records_reason`
- `tests/test_cli.py::test_cli_proposal_merge_merges_reviewed_branch_into_base`
- `tests/test_cli.py::test_cli_proposal_accept_branch_records_governance_decision`
- `tests/test_cli.py::test_cli_proposal_finalize_pushes_merged_base_branch`
- `tests/test_cli.py::test_cli_proposal_cleanup_deletes_local_and_remote_branch`
- `tests/test_mcp.py::test_mcp_safe_managed_sync_and_proposal_branch_tools`
- `tests/test_mcp.py::test_mcp_proposal_draft_commit_then_branch_from_explicit_base`
- `tests/test_mcp.py::test_mcp_proposal_branch_refuses_proposal_branch_base_without_opt_in`
- MCP consent-consuming proposal branch tests listed in T016.

Dependencies:
- `proposals`
- `sync`
- `remote_profile`
- `adapters.git`
- Branch metadata parser/renderer helpers.

Extraction Risks:
- Very high: branch lifecycle mutates Git state and governance metadata.
- Auto-renumber can rewrite proposal ids, directories, branch names, and commit
  metadata.
- Merge conflict continue/abort state must remain exact.

Extraction Notes:
- Do not extract before permissions/consent and basic proposal services are
  stable.
- Preserve all branch status names and lifecycle guards.

#### Boundary: `p2p_engine.services.work_plans`

Status:
- Proposed.

Owns:
- Work plan creation from validated spec exports.
- Work manifest read/show/status/list/summary behavior.
- Work next-action computation by status.

Does Not Own:
- Git branch execution.
- Spec export generation.
- Proposal branch lifecycle.

Inputs:
- Change Set id, export target, validated export path, Change Set metadata.

Outputs:
- Work detail and Work summary dataclasses.
- Work manifest payloads.

Storage Paths:
- `.p2p/work/WORK-XXX/work.yml`
- Reads `.p2p/outputs/spec-export/...` only through export validation result.

Side Effects:
- Creates Work directories and manifests.
- Retires planned Work when no Git side effect is involved.

Facade Methods:
- `create_work_plan`
- `work_statuses`
- `work_summaries`
- `show_work`
- `retire_work`
- `_work_summary_from_manifest`
- `_work_summary_from_scan`
- `_work_manifest`
- `_work_next_action`

CLI/MCP Surface:
- `work plan`
- `work list`
- `work status`
- `work show`
- `work retire`
- `p2p_work_plan`
- `p2p_work_list`
- `p2p_work_status`
- `p2p_work_show`

Compatibility Tests:
- `tests/test_cli.py::test_cli_work_plan_list_and_show`
- `tests/test_cli.py::test_cli_work_retire_marks_planned_work_retired`
- `tests/test_cli.py::test_cli_work_retire_requires_planned_status`
- `tests/test_mcp.py::test_mcp_write_safe_spec_export_and_work_flow`

Dependencies:
- `change_sets`
- `spec_exports`
- Filesystem adapter.

Extraction Risks:
- Coupling Work plan to private export paths instead of validation contract.
- Changing Work manifest layout consumed by branch execution.

Extraction Notes:
- Extract before `work_branches` if Work refactoring is started.

#### Boundary: `p2p_engine.services.work_branches`

Status:
- Proposed.

Owns:
- Work branch, submit, review, publish, external review request, accept,
  accept continue/abort, finalize, cleanup, and scan lifecycle.

Does Not Own:
- Work plan creation.
- Spec export validation.
- Low-level Git command implementation.
- Consent gating and MCP audit.

Inputs:
- Work id, branch operation options, remote/provider data, owner action
  metadata, current Git status.

Outputs:
- Updated Work detail/manifest payloads and operation status.

Storage Paths:
- `.p2p/work/WORK-XXX/work.yml`
- Work branch scan registry paths.

Side Effects:
- Git branch creation/checkout/commit/push/merge/abort/delete.
- Work manifest lifecycle writes.

Facade Methods:
- `branch_work`
- `submit_work`
- `review_work`
- `publish_work`
- `request_external_work_review`
- `accept_work`
- `continue_accept_work`
- `abort_accept_work`
- `finalize_work`
- `cleanup_work`
- `_scanned_work_items`
- `scan_work_branches`

CLI/MCP Surface:
- `work branch`
- `work submit`
- `work review`
- `work publish`
- `work request-review`
- `work accept`
- `work finalize`
- `work cleanup`
- `work scan`

Compatibility Tests:
- Work branch lifecycle tests listed in T013, including branch, submit,
  review, publish, request-review, accept, finalize, cleanup, conflict
  continue/abort, and scan tests.

Dependencies:
- `work_plans`
- `sync`
- `remote_profile`
- `adapters.git`

Extraction Risks:
- Very high: lifecycle is Git side-effecting and status-sensitive.
- Submit must continue to reject manifest-only changes.
- Accept conflict handling must preserve manifest rollback/continue behavior.

Extraction Notes:
- Extract after `work_plans` and after proposal branch extraction patterns are
  proven, because the two lifecycles share guard concepts.

### CLI And MCP Target Boundaries

Covered by T020.

#### Boundary: `p2p_engine.cli_commands.*`

Status:
- Deferred.

Owns:
- Typer command grouping, option/argument declarations, CLI-specific error
  presentation, Rich console output, and user-facing formatting.
- Thin translation from CLI inputs to `P2PWorkspace` facade calls or, after a
  later explicit feature, stable service calls.

Does Not Own:
- Domain lifecycle behavior.
- Filesystem layouts.
- Git operation rules.
- Consent validation.
- Rendering of domain markdown/YAML artifacts.

Inputs:
- Parsed Typer arguments/options.
- Workspace root.
- User-facing flags such as `--root`, `--change`, `--target`, `--actor`, and
  provider/remote options.

Outputs:
- Console text and exit codes.

Storage Paths:
- None directly. CLI modules should not write files except through the facade
  or services.

Side Effects:
- Only side effects performed by called facade/service methods.

Facade Methods:
- Initially all current CLI commands continue to call `P2PWorkspace`.
- Future command modules should group commands by domain:
  `cli_commands.proposals`, `cli_commands.readiness`,
  `cli_commands.permissions`, `cli_commands.consent`,
  `cli_commands.sync`, `cli_commands.work`, `cli_commands.specs`,
  `cli_commands.project`, and `cli_commands.agent`.

CLI/MCP Surface:
- All current `p2p` CLI command names must remain stable unless a product
  proposal explicitly changes them.

Compatibility Tests:
- Existing `tests/test_cli.py` behavior tests. Command modularization should
  not require rewriting assertions unless output intentionally changes through
  a later accepted feature.

Dependencies:
- `P2PWorkspace` facade during the refactoring.
- Later, stable service interfaces only after domain extraction is complete.

Extraction Risks:
- Moving CLI first can hide domain coupling rather than reducing it.
- Rich/Typer code can leak into services if boundaries are not enforced.
- Output formatting changes can break many compatibility tests.

Extraction Notes:
- Do not introduce `cli_commands/*` until at least one or two core services are
  extracted and facade delegation is proven.
- When introduced, move command groups mechanically and keep command function
  bodies thin.

#### Boundary: `p2p_engine.mcp.registry`

Status:
- Deferred.

Owns:
- MCP tool definition registry, schemas, read/write-safe classification, and
  routing from tool name to handler.
- Transport-level serialization through `_to_jsonable` and MCP-specific
  argument validation.

Does Not Own:
- Domain service behavior.
- Consent receipt lifecycle.
- Git audit side effects, except calling a dedicated MCP consent-audit helper.
- CLI presentation.

Inputs:
- MCP tool name and arguments.
- Workspace root.
- Optional consent receipt fields for permission-gated tools.

Outputs:
- JSON-serializable MCP result payloads.
- MCP errors with current-compatible messages.

Storage Paths:
- None directly. MCP handlers should use the facade, services, or explicit MCP
  helper modules.

Side Effects:
- Only side effects performed by called facade/service/helper methods.
- Permission-gated tools may call MCP consent-audit helpers that perform Git
  audit commits and optional pushes.

Facade Methods:
- Initially keep routing through `P2PWorkspace`.
- Later handlers may call stable services only after those services exist and
  preserve facade behavior.

CLI/MCP Surface:
- All existing `p2p_*` tool names and schemas must remain stable.
- Tool names should be grouped by domain in the registry after extraction:
  project, permissions, consent, proposals, readiness, sync, change, work,
  choices, next actions, spec/export, intake, and agent integration.

Compatibility Tests:
- Existing `tests/test_mcp.py` behavior tests, especially write-safe and
  consent-gated tool tests.
- Missing before extraction: a focused schema registry test may be useful if
  tool definitions move out of `mcp/tools.py`.

Dependencies:
- `P2PWorkspace` facade.
- `mcp.consent_audit` for permission-gated operations after it exists.
- Domain services only after extraction.

Extraction Risks:
- Accidentally making read-only MCP tools write state.
- Losing consent validation/consumption around permission-gated tools.
- Schema drift across tools.
- Returning non-JSON-serializable domain objects.

Extraction Notes:
- Do not modularize MCP routing before consent boundaries are clear.
- Keep read-only/write-safe/permission-gated classifications explicit in the
  registry to avoid relying on naming conventions.

#### Boundary: `p2p_engine.presentation.formatters`

Status:
- Proposed.

Owns:
- Shared formatting helpers for CLI tables/sections and MCP serialization only
  where duplication becomes material.

Does Not Own:
- Domain logic or file writes.

Extraction Notes:
- Optional later cleanup. It should not block service extraction.
- Prefer keeping presentation duplication temporarily over coupling services to
  presentation formats.

Service-before-presentation recommendation:

1. Extract `permissions` and `consent` behind `P2PWorkspace`.
2. Extract low-risk metadata services such as `remote_profile`.
3. Extract selected pure/read-heavy services such as `software_specs`,
   `project_definition`, or `proposals`.
4. Extract higher-risk Git lifecycle services only after tests and facade
   delegation patterns are proven.
5. Introduce `cli_commands/*` and `mcp.registry` only when command/tool files
   can mostly delegate to already-stable service boundaries.

## Responsibility Group Mappings

### Initialization And Agent Integration

Covered by T006.

Current behavior:

- initializes `.p2p` project files, templates, governance placeholders,
  readiness profile, domain state, rubrics, permissions policy, remote profile,
  proposal/prompt directories, and generated agent instructions;
- maintains generated agent instruction files for generic, Codex, Claude,
  Cursor, Copilot, Gemini, and OpenCode profiles;
- maintains `.p2p/agent-policy.yml`;
- maintains `.p2p/agent-integrations.yml` with file ownership, hashes, shared
  files, drift status, and adapter capabilities;
- supports agent install/update/uninstall/list/show workflows;
- supports rubric initialization, rubric preview, and rubric show for project
  definition maturity.

Candidate target areas:

- `p2p_engine.services.project_init`
- `p2p_engine.services.agent_integrations`
- `p2p_engine.services.project_rubrics`
- `p2p_engine.adapters.filesystem`
- `p2p_engine.renderers.agent_instructions` or
  `p2p_engine.services.agent_templates`

The exact names are recommendations only. Final module names belong to T015-T020.

| Current method/helper | Line | Current responsibility | Candidate target area | Facade behavior |
| --- | ---: | --- | --- | --- |
| `__init__` | 730 | Store root and `.p2p` paths | `P2PWorkspace` facade plus filesystem adapter bootstrap | Keep in facade. |
| `init_project` | 734 | Create initial `.p2p` state, templates, readiness profile, domain/rubrics, permissions, directories, and agent instructions | `project_init` service coordinating domain/rubrics/agent services | Keep method; delegate after extraction. |
| `refresh_agent_instructions` | 824 | Generate/update project-local agent instructions and policy, merge profiles, update registry | `agent_integrations` service | Keep method; delegate after extraction. |
| `agent_integrations_list` | 880 | Return installed/supported adapter summary | `agent_integrations` service | Keep method; delegate after extraction. |
| `agent_integration_show` | 894 | Return one adapter status with file drift | `agent_integrations` service | Keep method; delegate after extraction. |
| `install_agent_integrations` | 904 | Install/update adapter files with drift protection and registry update | `agent_integrations` service | Keep method; delegate after extraction. |
| `uninstall_agent_integration` | 1013 | Remove safe managed adapter files and refresh shared policy/registry | `agent_integrations` service | Keep method; delegate after extraction. |
| `_agent_integrations_path` | 1071 | Resolve registry path | filesystem adapter or `agent_integrations` service | Move behind service. |
| `_agent_integrations_registry` | 1074 | Read agent integration registry | filesystem adapter or `agent_integrations` service | Move behind service. |
| `_write_agent_integrations_registry` | 1084 | Write agent integration registry | filesystem adapter or `agent_integrations` service | Move behind service. |
| `_agent_registry_file_map` | 1089 | Build file-record lookup from registry | `agent_integrations` service | Move behind service. |
| `_build_agent_integrations_registry` | 1105 | Build adapter registry with file hashes, drift status, capabilities | `agent_integrations` service | Move behind service. |
| `_agent_integration_status` | 1143 | Compute status and drift for one adapter | `agent_integrations` service | Move behind service. |
| `_project_name` | 1411 | Read project display name from project state | filesystem/project metadata adapter | Shared helper; keep until metadata service exists. |
| `_repository_mode` | 1419 | Read repository mode from project state | filesystem/project metadata adapter | Shared helper; keep until metadata service exists. |
| `_set_repository_mode` | 1448 | Persist repository mode in project state | filesystem/project metadata adapter | Shared helper; keep until metadata service exists. |
| `init_project_rubrics` | 3376 | Write rubrics and domain state, update project domain | `project_rubrics` service | Keep method; delegate after extraction. |
| `init_project_rubrics_preview` | 3396 | Return built-in rubric criteria preview | `project_rubrics` service | Keep method; delegate after extraction. |
| `show_project_rubrics` | 3401 | Read configured rubric payload as domain object | `project_rubrics` service | Keep method; delegate after extraction. |
| `_normalize_agent_profile` | 7198 | Normalize agent profile and aliases | `agent_integrations` service or domain helper | Move with agent integration logic. |
| `_expanded_agent_profiles` | 7221 | Expand selected profile to generic plus adapter profiles | `agent_integrations` service or domain helper | Move with agent integration logic. |
| `_remove_empty_parents` | 7234 | Remove empty directories after safe uninstall | filesystem adapter helper | Move behind filesystem adapter. |
| `_sha256_file` | 7245 | Hash managed generated files | filesystem adapter helper | Move behind filesystem adapter. |
| `_managed_markdown_header` | 7249 | Build generated markdown header | agent template renderer | Move with template rendering. |
| `_agent_adapter_capabilities` | 7272 | Describe adapter capabilities | `agent_integrations` service | Move with adapter registry model. |
| `_normalize_repository_mode` | 7281 | Normalize repository mode | project metadata/domain helper | Shared helper; may move later. |
| `_init_remote_profile_payload` | 7288 | Build initial remote profile payload during init | project init or remote profile service | Keep coupled to init until remote service extraction. |
| `_normalize_project_domain` | 7329 | Normalize domain template aliases | `project_rubrics` or domain service | Move with domain/rubrics logic. |
| `_domain_state_payload` | 7355 | Build domain state payload | `project_rubrics` or domain service | Move with domain/rubrics logic. |
| `_domain_setup_next_actions_payload` | 7384 | Build domain setup next actions for unresolved domains | domain service or next-action service | Requires boundary decision because it touches next actions. |
| `_rubrics_payload` | 7409 | Build rubric payload from domain template and enabled criteria | `project_rubrics` service | Move with rubric logic. |
| `_agent_instruction_files` | 7460 | Select generated instruction files for profiles | agent template renderer | Move with template rendering. |
| `_agent_adapter_files` | 7490 | Select adapter-owned/shared files and template ids | `agent_integrations` service | Move with adapter registry model. |
| `_agent_policy` | 7521 | Build `.p2p/agent-policy.yml` payload | agent policy renderer/service | Move with agent integration logic. |
| `_agents_markdown` | 7679 | Render generic `AGENTS.md` | agent template renderer | Move with generated instruction templates. |
| `_shared_p2p_project_skill` | 7823 | Render shared project skill | agent template renderer | Move with generated instruction templates. |
| `_codex_project_skill` | 7853 | Render Codex project skill | agent template renderer | Move with generated instruction templates. |
| `_claude_markdown` | 7915 | Render Claude instructions | agent template renderer | Move with generated instruction templates. |
| `_cursor_rule` | 7944 | Render Cursor rule | agent template renderer | Move with generated instruction templates. |
| `_copilot_instructions` | 7967 | Render Copilot instructions | agent template renderer | Move with generated instruction templates. |
| `_gemini_markdown` | 7988 | Render Gemini instructions | agent template renderer | Move with generated instruction templates. |

Existing compatibility tests:

- `tests/test_cli.py::test_cli_init_status_create_and_prompt_flow`
- `tests/test_cli.py::test_cli_init_default_domain_and_rubric_are_unresolved`
- `tests/test_cli.py::test_cli_init_domain_template_populates_rubric`
- `tests/test_cli.py::test_cli_project_rubrics_and_definition_maturity`
- `tests/test_cli.py::test_cli_init_without_name_runs_guided_wizard`
- `tests/test_cli.py::test_cli_init_guided_wizard_can_disable_rubric_criteria`
- `tests/test_cli.py::test_cli_init_can_generate_agent_specific_instructions`
- `tests/test_cli.py::test_cli_init_defaults_to_all_agent_integrations`
- `tests/test_cli.py::test_cli_init_narrow_agent_still_includes_generic`
- `tests/test_cli.py::test_cli_agent_lifecycle_update_refuses_drift_and_uninstall_preserves_shared`
- `tests/test_cli.py::test_cli_agent_install_does_not_claim_unmanaged_existing_file`
- `tests/test_cli.py::test_cli_agent_instructions_refresh_adds_profiles_without_removing_existing`
- `tests/test_mcp.py::test_mcp_write_safe_bootstrap_tools`
- `tests/test_mcp.py::test_mcp_agent_integration_lifecycle_tools`
- `tests/test_mcp.py::test_mcp_init_project_can_start_with_unresolved_custom_domain`
- `tests/test_mcp.py::test_mcp_project_definition_maturity`

Extraction notes:

- This area is broad but separable because agent integration has strong file
  boundaries and focused tests.
- `init_project` coordinates many domains and should not be the first code
  extraction unless services for domain/rubrics, permissions, remote profile,
  and agent instructions already exist.
- Agent template rendering is a good later extraction candidate after
  permissions/consent because it is mostly deterministic file generation.
- Domain/rubrics setup is coupled to maturity assessment and next actions; map
  those dependencies again during T010 and T013.

### Permissions And Consent

Covered by T007.

Current behavior:

- stores project-declared identities, roles, tool classes, and repository-mode
  permission metadata in `.p2p/project/permissions.yml`;
- supports actor add/update through CLI and workspace API;
- grants, requests, shows, lists, revokes, validates, consumes, and marks
  consent receipts under `.p2p/consents/CONSENT-XXX/consent.yml`;
- normalizes identity ids, roles, actor kinds, consent operations, and consent
  ids;
- validates operation, target, actor, status, and expiry before privileged MCP
  operations;
- lets MCP request consent without granting it;
- consumes consent and records Git audit commits for permission-gated MCP
  operations in `src/p2p_engine/mcp/tools.py`.

Candidate target areas:

- `p2p_engine.services.permissions`
- `p2p_engine.services.consent`
- `p2p_engine.adapters.filesystem`
- `p2p_engine.mcp.consent_audit` or equivalent MCP-side audit helper

The permission policy and consent receipt lifecycle are the recommended first
future extraction because the boundary is clear, the safety value is high, and
existing CLI/MCP coverage is strong.

| Current method/helper | Line | Current responsibility | Candidate target area | Facade behavior |
| --- | ---: | --- | --- | --- |
| `permissions_show` | 1175 | Read or synthesize project permission policy | `permissions` service | Keep method; delegate after extraction. |
| `permissions_actor_add` | 1181 | Add/update actor identity in permissions policy | `permissions` service | Keep method; delegate after extraction. |
| `consent_grant` | 1211 | Create granted consent receipt after validating actor and owner approver | `consent` service | Keep method; delegate after extraction. |
| `consent_request` | 1264 | Create requested consent receipt without granting execution | `consent` service | Keep method; delegate after extraction. |
| `consent_show` | 1311 | Read one consent receipt | `consent` service | Keep method; delegate after extraction. |
| `consent_statuses` | 1318 | List consent receipts | `consent` service | Keep method; delegate after extraction. |
| `consent_revoke` | 1327 | Revoke non-consumed consent receipt | `consent` service | Keep method; delegate after extraction. |
| `consent_validate` | 1340 | Validate granted receipt for operation, target, actor, and expiry | `consent` service | Keep method; delegate after extraction. |
| `consent_consume` | 1378 | Mark granted receipt consumed and store result | `consent` service | Keep method; delegate after extraction. |
| `consent_mark_used_with_error` | 1391 | Mark granted receipt used with error after partial side effects | `consent` service | Keep method; delegate after extraction. |
| `_permissions_path` | 1429 | Resolve permission policy path | filesystem adapter or `permissions` service | Move behind service. |
| `_consent_path` | 1432 | Normalize receipt id and resolve receipt path | filesystem adapter or `consent` service | Move behind service. |
| `_next_consent_id` | 1436 | Allocate next sequential consent id from filesystem state | `consent` service | Move behind service. |
| `_permissions_payload` | 8041 | Build default role-plus-consent policy payload | `permissions` service | Move behind service. |
| `_identity_slug` | 8098 | Normalize identity strings to actor ids | `permissions`/`consent` shared helper | Move with permission domain helpers. |
| `_normalize_permission_role` | 8105 | Validate and normalize permission role | `permissions` service | Move with permission domain helpers. |
| `_normalize_actor_kind` | 8113 | Validate and normalize actor kind | `permissions` service | Move with permission domain helpers. |
| `_normalize_consent_operation` | 8121 | Validate and normalize consent operation | `consent` service | Move with consent domain helpers. |
| `_normalize_consent_id` | 8129 | Validate and normalize `CONSENT-XXX` id | `consent` service | Move with consent domain helpers. |
| `_consent_receipt_from_payload` | 8136 | Convert YAML payload to `ConsentReceipt` dataclass | `consent` service or domain mapper | Move with consent service. |

Related CLI surfaces:

- `permissions show`
- `permissions actor add`
- `consent grant`
- `consent show`
- `consent status`
- `consent revoke`

Related MCP surfaces:

- `p2p_permissions_show`
- `p2p_consent_request`
- `p2p_consent_status`
- `p2p_consent_show`
- permission-gated tools that call `consent_validate`, then consume receipts:
  sync pull/push, proposal draft decisions, proposal branch publish/review/
  accept/reject/merge/finalize/cleanup.

MCP-side helpers that must be considered in the extraction:

- `_consume_consent_with_audit`
- `_commit_and_push_consent_audit`
- `_mark_consent_error_on_head_change`

These helpers currently live outside `P2PWorkspace` in `mcp/tools.py` because
they combine consent lifecycle with MCP-side Git audit side effects. They should
not be moved blindly into the core consent service unless the audit boundary is
explicitly designed.

Existing compatibility tests:

- `tests/test_cli.py::test_cli_init_status_create_and_prompt_flow`
- `tests/test_cli.py::test_cli_init_owner_populates_permissions_policy`
- `tests/test_cli.py::test_cli_permissions_actor_and_consent_receipts`
- `tests/test_cli.py::test_cli_consent_grant_requires_owner_approver`
- `tests/test_cli.py::test_cli_validate_reports_invalid_permissions_policy`
- `tests/test_mcp.py::test_mcp_remote_configure_and_consent_request_are_write_safe`
- `tests/test_mcp.py::test_mcp_requested_consent_does_not_authorize_publish`
- `tests/test_mcp.py::test_mcp_draft_proposal_decision_requires_granted_consent`
- `tests/test_mcp.py::test_mcp_draft_proposal_accept_and_defer_consume_matching_consent`
- `tests/test_mcp.py::test_mcp_proposal_publish_requires_and_consumes_consent`
- `tests/test_mcp.py::test_mcp_proposal_publish_rejects_actor_mismatch_without_consuming_consent`
- `tests/test_mcp.py::test_mcp_sync_push_requires_and_consumes_consent`
- `tests/test_mcp.py::test_mcp_sync_pull_requires_and_consumes_consent`
- `tests/test_mcp.py::test_mcp_proposal_request_review_requires_and_consumes_consent`
- `tests/test_mcp.py::test_mcp_proposal_merge_requires_and_consumes_consent`
- `tests/test_mcp.py::test_mcp_proposal_finalize_requires_and_consumes_consent`
- `tests/test_mcp.py::test_mcp_proposal_reject_and_cleanup_require_consent`
- `tests/test_mcp.py::test_mcp_permission_and_consent_read_tools`

Extraction notes:

- This is the strongest first extraction candidate.
- Keep `P2PWorkspace` method signatures and `ConsentReceipt`/`PermissionActor`
  return shapes stable.
- Preserve `.p2p/project/permissions.yml` and `.p2p/consents/*/consent.yml`
  layouts.
- Preserve requested consent semantics: requested receipts must not authorize
  execution.
- Preserve expiry handling that mutates expired receipts to `expired`.
- Preserve consumed and used-with-error status transitions.
- Preserve MCP audit behavior for consent-consuming operations, including
  commit message `P2P consent consume CONSENT-XXX` and optional push behavior.
- Avoid mixing policy/receipt lifecycle with MCP-specific Git audit in the same
  first extraction unless the boundary is documented in T016.

### Remote, Sync, And Git-Related Proposal Branching

Covered by T008.

Current behavior:

- stores the project remote profile in `.p2p/project.yml` with local/remote
  mode, provider, remote alias, URL, and review-request metadata;
- reports sync readiness by combining P2P remote profile state with Git
  repository state, current branch, clean worktree state, and Git remote URL;
- wraps Git fetch, fast-forward pull, and push operations behind workspace
  methods;
- creates proposal draft commits and managed proposal branches from clean Git
  state;
- stores managed proposal branch metadata in `.p2p/proposals/*/branch.yml`;
- publishes proposal branches, detects remote proposal id collisions, and can
  auto-renumber a local proposal branch before publish;
- records review request, retire, accept/reject, merge, merge conflict,
  finalize, cleanup, and scan state for managed proposal branches;
- uses `storage/git.py` as a thin subprocess adapter returning simple
  bool/string/list results.

Candidate target areas:

- `p2p_engine.services.remote_profile`
- `p2p_engine.services.sync`
- `p2p_engine.services.proposal_branches`
- `p2p_engine.services.branch_metadata`
- `p2p_engine.adapters.git`
- `p2p_engine.adapters.filesystem`

The remote/sync boundary can be extracted before the full proposal lifecycle.
The proposal branch lifecycle should be extracted more cautiously because it is
governance-sensitive and overlaps with proposal lifecycle mapping in T009.

| Current method/helper | Line | Current responsibility | Candidate target area | Facade behavior |
| --- | ---: | --- | --- | --- |
| `_set_repository_mode` | 1448 | Persist repository mode in project state | remote/project metadata service | Shared helper; delegate after extraction. |
| `remote_profile` | 1488 | Read remote profile from project state | `remote_profile` service | Keep method; delegate after extraction. |
| `configure_remote_profile` | 1511 | Validate and persist remote profile | `remote_profile` service | Keep method; delegate after extraction. |
| `sync_status` | 1553 | Combine Git status, configured profile, selected remote, URL mismatch, and sync readiness | `sync` service with Git adapter | Keep method; delegate after extraction. |
| `sync_fetch` | 1617 | Validate sync remote and run Git fetch | `sync` service with Git adapter | Keep method; delegate after extraction. |
| `sync_pull` | 1630 | Validate branch/clean state and run fast-forward pull | `sync` service with Git adapter | Keep method; delegate after extraction. |
| `sync_push` | 1647 | Validate branch/clean state and push current branch | `sync` service with Git adapter | Keep method; delegate after extraction. |
| `commit_proposal_draft` | 1685 | Commit current proposal draft changes through Git | proposal branch or proposal collaboration service | Keep method; delegate after extraction. |
| `branch_proposal` | 1700 | Create managed proposal branch and write branch metadata | `proposal_branches` service | Keep method; delegate after extraction. |
| `show_proposal_branch` | 1766 | Read managed proposal branch metadata | `proposal_branches` or `branch_metadata` service | Keep method; delegate after extraction. |
| `publish_proposal_branch` | 1785 | Fetch remote, detect collisions, publish metadata, push branch | `proposal_branches` service with sync/Git dependencies | Keep method; delegate after extraction. |
| `request_proposal_branch_review` | 1852 | Mark published branch as review requested | `proposal_branches` service | Keep method; delegate after extraction. |
| `retire_proposal_branch` | 1892 | Mark branch retired with owner reason | `proposal_branches` service | Keep method; delegate after extraction. |
| `accept_proposal_branch` | 1919 | Owner-controlled branch acceptance wrapper | `proposal_branches` service | Keep method; delegate after extraction. |
| `reject_proposal_branch` | 1925 | Owner-controlled branch rejection wrapper | `proposal_branches` service | Keep method; delegate after extraction. |
| `_decide_proposal_branch` | 1931 | Shared accept/reject branch state transition | `proposal_branches` service | Move behind service. |
| `merge_proposal_branch` | 1971 | Merge managed proposal branch into base branch and record merge/conflict state | `proposal_branches` service with Git adapter | Keep method; delegate after extraction. |
| `continue_merge_proposal_branch` | 2037 | Continue conflict resolution and create merge commit | `proposal_branches` service with Git adapter | Keep method; delegate after extraction. |
| `abort_merge_proposal_branch` | 2084 | Abort managed proposal merge and return to source branch | `proposal_branches` service with Git adapter | Keep method; delegate after extraction. |
| `finalize_proposal_branch` | 2100 | Mark merged proposal finalized and push base branch | `proposal_branches` service with sync/Git dependencies | Keep method; delegate after extraction. |
| `cleanup_proposal_branch` | 2155 | Delete local/remote managed proposal branch and record cleanup | `proposal_branches` service with Git adapter | Keep method; delegate after extraction. |
| `scan_proposal_branches` | 2265 | Read local proposal branch metadata without checkout and update scan registry | `proposal_branches` or branch registry service | Keep method; delegate after extraction. |
| `_proposal_branch_metadata` | 6839 | Locate current proposal branch metadata file | `branch_metadata` service | Move behind service. |
| `_proposal_branch_metadata_from_local_ref` | 6847 | Read proposal metadata from local proposal branch refs | `branch_metadata` service with Git adapter | Move behind service. |
| `_remote_proposal_ids` | 6871 | Collect proposal ids from remote proposal branches and remote base tree | `proposal_branches` service with Git adapter | Move behind service. |
| `_auto_renumber_proposal_branch` | 6888 | Move local proposal directory, rewrite ids, rename branch, commit metadata | `proposal_branches` service | Move behind service. |
| `_next_available_proposal_id` | 6945 | Allocate next proposal id from local and remote ids | proposal id allocation service or proposal service | Shared helper; final owner decided in T009/T017. |
| `_sync_remote` | 6958 | Resolve explicit remote or configured profile remote | `sync` service | Move behind service. |
| `_require_sync_remote` | 6964 | Validate sync readiness before side-effect operations | `sync` service | Move behind service. |

Git adapter functions currently used by this area:

| Current function | Current responsibility | Candidate target area |
| --- | --- | --- |
| `get_git_status` | Detect repository, current branch, and clean worktree | `adapters.git` |
| `head_commit` | Resolve current commit | `adapters.git` |
| `branch_exists` | Check local branch existence | `adapters.git` |
| `create_and_checkout_branch` | Create and checkout local branch | `adapters.git` |
| `checkout_branch` | Checkout local branch | `adapters.git` |
| `rename_current_branch` | Rename current branch | `adapters.git` |
| `changed_files` | List uncommitted changed files | `adapters.git` |
| `commit_all` | Stage all files and commit | `adapters.git` |
| `stage_all` | Stage all files | `adapters.git` |
| `remote_url` | Read Git remote URL | `adapters.git` |
| `fetch_remote` | Fetch remote | `adapters.git` |
| `pull_branch` | Fast-forward pull a branch | `adapters.git` |
| `push_branch` | Push branch with upstream | `adapters.git` |
| `delete_local_branch` | Delete merged local branch | `adapters.git` |
| `delete_local_branch_force` | Force-delete local branch | `adapters.git` |
| `delete_remote_branch` | Delete remote branch | `adapters.git` |
| `merge_branch_no_commit` | Start no-commit merge | `adapters.git` |
| `conflicted_files` | List unresolved merge conflicts | `adapters.git` |
| `merge_in_progress` | Detect `.git/MERGE_HEAD` | `adapters.git` |
| `abort_merge` | Abort Git merge | `adapters.git` |
| `restore_path` | Restore a path during merge abort | `adapters.git` |
| `list_local_work_branches` | List local Work branches | `adapters.git`; mapped again in T013. |
| `list_local_proposal_branches` | List local proposal branches | `adapters.git` |
| `list_remote_proposal_branches` | List remote proposal branches | `adapters.git` |
| `list_files_at_ref` | List files at a Git ref | `adapters.git` |
| `read_file_at_ref` | Read file content at a Git ref | `adapters.git` |
| `_run_git` | Execute subprocess Git command and collapse failures to `None` | `adapters.git` implementation detail |

Related CLI surfaces:

- `init --repository remote`
- `project remote configure`
- `project remote show`
- `sync status`
- `sync fetch`
- `sync pull`
- `sync push`
- `proposal draft-commit`
- `proposal branch`
- `proposal branch-status`
- `proposal publish`
- `proposal request-review`
- `proposal retire-branch`
- `proposal accept-branch`
- `proposal reject-branch`
- `proposal merge`
- `proposal finalize`
- `proposal cleanup`
- `proposal scan`

Related MCP surfaces:

- `p2p_project_remote_show`
- `p2p_project_remote_configure`
- `p2p_sync_status`
- `p2p_sync_fetch`
- `p2p_sync_pull`
- `p2p_sync_push`
- `p2p_proposal_draft_commit`
- `p2p_proposal_branch`
- `p2p_proposal_branch_status`
- `p2p_proposal_publish`
- `p2p_proposal_request_review`
- `p2p_proposal_accept_branch`
- `p2p_proposal_reject_branch`
- `p2p_proposal_merge`
- `p2p_proposal_finalize`
- `p2p_proposal_cleanup`
- `p2p_proposal_branch_scan`

Existing compatibility tests:

- `tests/test_cli.py::test_cli_proposal_branch_creates_managed_branch_metadata`
- `tests/test_cli.py::test_cli_proposal_publish_request_review_and_scan`
- `tests/test_cli.py::test_cli_proposal_publish_auto_renumbers_on_remote_id_collision`
- `tests/test_cli.py::test_cli_proposal_publish_detects_collision_from_remote_main`
- `tests/test_cli.py::test_cli_proposal_retire_branch_records_reason`
- `tests/test_cli.py::test_cli_proposal_merge_merges_reviewed_branch_into_base`
- `tests/test_cli.py::test_cli_proposal_accept_branch_records_governance_decision`
- `tests/test_cli.py::test_cli_proposal_finalize_pushes_merged_base_branch`
- `tests/test_cli.py::test_cli_proposal_cleanup_deletes_local_and_remote_branch`
- `tests/test_cli.py::test_cli_init_cloud_configures_remote_profile`
- `tests/test_cli.py::test_cli_init_rejects_ambiguous_repository_remote_alias`
- `tests/test_cli.py::test_cli_sync_status_reports_local_project_without_remote`
- `tests/test_cli.py::test_cli_sync_status_detects_git_origin_when_p2p_profile_is_local`
- `tests/test_cli.py::test_cli_sync_status_detects_remote_profile_url_mismatch`
- `tests/test_cli.py::test_cli_sync_push_fetch_and_pull_wrap_git_remote`
- `tests/test_cli.py::test_cli_sync_pull_requires_clean_worktree`
- `tests/test_cli.py::test_cli_project_remote_configure_and_show`
- `tests/test_mcp.py::test_mcp_safe_managed_sync_and_proposal_branch_tools`
- `tests/test_mcp.py::test_mcp_remote_configure_and_consent_request_are_write_safe`
- `tests/test_mcp.py::test_mcp_proposal_draft_commit_then_branch_from_explicit_base`
- `tests/test_mcp.py::test_mcp_proposal_branch_refuses_proposal_branch_base_without_opt_in`
- `tests/test_mcp.py::test_mcp_proposal_publish_requires_and_consumes_consent`
- `tests/test_mcp.py::test_mcp_sync_push_requires_and_consumes_consent`
- `tests/test_mcp.py::test_mcp_sync_pull_requires_and_consumes_consent`
- `tests/test_mcp.py::test_mcp_proposal_request_review_requires_and_consumes_consent`
- `tests/test_mcp.py::test_mcp_proposal_merge_requires_and_consumes_consent`
- `tests/test_mcp.py::test_mcp_proposal_finalize_requires_and_consumes_consent`
- `tests/test_mcp.py::test_mcp_proposal_reject_and_cleanup_require_consent`
- `tests/test_mcp.py::test_mcp_change_project_registry_and_remote_read_tools`

Extraction notes:

- Extract `remote_profile` and `sync` before `proposal_branches` if the goal is
  a low-risk first cut; they already have a narrower public surface.
- Keep the existing Git adapter result semantics until callers are moved. It
  currently collapses failed Git commands to `None` or `False`; richer Git
  errors should be a later behavior-preserving enhancement with explicit tests.
- Preserve `.p2p/proposals/*/branch.yml` layout and status names exactly.
- Preserve clean-worktree and expected-branch guards before any side-effecting
  Git operation.
- Preserve `--auto-renumber` behavior because it depends on remote branch refs
  and remote base-tree inspection.
- Treat merge/finalize/cleanup as high-risk operations because they mutate Git
  history/state and, through MCP, are permission-gated by consent receipts.
- Revisit proposal branch ownership in T009 and T017: some behavior may belong
  to a broader proposal lifecycle service, while Git transitions should remain
  behind branch/sync/Git boundaries.

### Proposal Lifecycle

Covered by T009.

Current behavior:

- lists proposal summaries by scanning `.p2p/proposals/*`;
- shows one proposal by reading `proposal.md` and `decision.md`;
- creates proposal scaffolds with proposal, contribution, comment, digest,
  clarification, decision, execution-plan, task, and exploration files;
- updates structured sections in `proposal.md`;
- appends and lists typed proposal contributions in `contributions.yml`;
- records owner-controlled governance decisions in `decision.md` and mirrors
  the decision status into `proposal.md`;
- creates proposal draft commits before collaboration branch work;
- coordinates managed proposal branch lifecycle: branch, publish, review,
  retire, branch accept/reject, merge, conflict continue/abort, finalize,
  cleanup, and scan;
- detects missing or ambiguous proposal ids and duplicate proposal directories.

Candidate target areas:

- `p2p_engine.services.proposals`
- `p2p_engine.services.proposal_documents`
- `p2p_engine.services.contributions`
- `p2p_engine.services.decisions`
- `p2p_engine.services.proposal_branches`
- `p2p_engine.services.proposal_id_allocator`
- `p2p_engine.adapters.filesystem`
- `p2p_engine.adapters.git`
- `p2p_engine.renderers.proposal_markdown`

The proposal service should own proposal identity, document scaffold/update,
summary/detail reads, and proposal-local contributions. Decision recording can
be a separate service because it is owner-controlled governance state and is
also exposed through both CLI shortcuts and MCP consent-gated tools. Managed
branch mechanics remain a branch collaboration service with Git dependencies,
even though they are part of the broader proposal lifecycle.

| Current method/helper | Line | Current responsibility | Candidate target area | Facade behavior |
| --- | ---: | --- | --- | --- |
| `proposal_summaries` | 1664 | List proposal summaries and optional status filter | `proposals` service | Keep method; delegate after extraction. |
| `show_proposal` | 1670 | Read proposal detail and decision summary | `proposals` service with document reader | Keep method; delegate after extraction. |
| `commit_proposal_draft` | 1685 | Commit current proposal draft changes before branch collaboration | proposal collaboration service with Git adapter | Keep method; delegate after extraction. |
| `branch_proposal` | 1700 | Create managed proposal collaboration branch | `proposal_branches` service | Keep method; already detailed in T008. |
| `show_proposal_branch` | 1766 | Show managed proposal branch metadata | `proposal_branches` service | Keep method; already detailed in T008. |
| `publish_proposal_branch` | 1785 | Publish proposal branch, including collision handling | `proposal_branches` service | Keep method; already detailed in T008. |
| `request_proposal_branch_review` | 1852 | Record external review handoff metadata | `proposal_branches` service | Keep method; already detailed in T008. |
| `retire_proposal_branch` | 1892 | Retire a managed proposal branch with reason | `proposal_branches` service | Keep method; already detailed in T008. |
| `accept_proposal_branch` | 1919 | Owner-controlled acceptance of a managed proposal branch | `proposal_branches` or branch decision service | Keep method; delegate after extraction. |
| `reject_proposal_branch` | 1925 | Owner-controlled rejection of a managed proposal branch | `proposal_branches` or branch decision service | Keep method; delegate after extraction. |
| `_decide_proposal_branch` | 1931 | Shared branch accept/reject transition | `proposal_branches` or branch decision service | Move behind service. |
| `merge_proposal_branch` | 1971 | Merge proposal branch into base branch | `proposal_branches` service with Git adapter | Keep method; already detailed in T008. |
| `continue_merge_proposal_branch` | 2037 | Continue proposal branch merge after conflict resolution | `proposal_branches` service with Git adapter | Keep method; already detailed in T008. |
| `abort_merge_proposal_branch` | 2084 | Abort conflicted proposal branch merge | `proposal_branches` service with Git adapter | Keep method; already detailed in T008. |
| `finalize_proposal_branch` | 2100 | Finalize merged proposal branch by pushing base branch | `proposal_branches` service with sync/Git dependencies | Keep method; already detailed in T008. |
| `cleanup_proposal_branch` | 2155 | Clean finalized/rejected/retired proposal branch | `proposal_branches` service with Git adapter | Keep method; already detailed in T008. |
| `scan_proposal_branches` | 2265 | Scan local proposal branches and update branch registry | `proposal_branches` or branch registry service | Keep method; already detailed in T008. |
| `create_proposal` | 2763 | Minimal proposal scaffold wrapper | `proposals` service | Keep method; delegate after extraction. |
| `create_proposal_with_details` | 2766 | Allocate id, create proposal directory, and write scaffold files | `proposals` service plus proposal markdown renderer | Keep method; delegate after extraction. |
| `update_proposal` | 2814 | Replace selected structured sections in `proposal.md` | `proposal_documents` service | Keep method; delegate after extraction. |
| `add_contribution` | 2841 | Append typed contribution to `contributions.yml` | `contributions` service | Keep method; delegate after extraction. |
| `list_contributions` | 2871 | Read and normalize proposal contribution list | `contributions` service | Keep method; delegate after extraction. |
| `record_decision` | 2898 | Write `decision.md` and update proposal status | `decisions` service with proposal document dependency | Keep method; delegate after extraction. |
| `_next_proposal_id` | 6803 | Allocate next local proposal id from proposal directories | `proposal_id_allocator` service | Move behind service. |
| `_find_proposal_dir` | 6812 | Resolve one proposal directory and reject missing/ambiguous ids | `proposals` service or filesystem adapter | Move behind service. |
| `_duplicate_proposal_ids` | 6827 | Detect duplicate proposal ids by directory name | validation/proposals service | Move behind service; also used by validation. |
| `_proposal_branch_metadata` | 6839 | Locate branch metadata for current proposal | `proposal_branches` service | Move behind service; already detailed in T008. |
| `_proposal_branch_metadata_from_local_ref` | 6847 | Locate proposal branch metadata from local refs | `proposal_branches` service with Git adapter | Move behind service; already detailed in T008. |
| `_slugify` | 8008 | Build stable directory/branch slugs | shared text/id helper | Move only after caller ownership is clear. |
| `_proposal_markdown` | 8196 | Render initial `proposal.md` scaffold | proposal markdown renderer | Move with proposal document service. |
| `_read_proposal_status` | 8552 | Extract proposal status from markdown | proposal document parser | Move with proposal document service. |
| `_proposal_id_from_dir_name` | 8560 | Parse proposal id from directory name | proposal id helper | Move with proposal service. |
| `_proposal_id_from_branch_name` | 8565 | Parse proposal id from managed branch name | proposal branch helper | Move with proposal branch service. |
| `_duplicate_proposal_ids_message` | 8570 | Format duplicate proposal diagnostic | validation/proposals service | Move when validation boundary is extracted. |
| `_proposal_branch_name` | 8582 | Build managed proposal branch name | proposal branch service | Move with proposal branch service. |
| `_branch_hash16` | 8587 | Compute managed branch identity hash | proposal branch service | Move with proposal branch service. |
| `_proposal_branch_detail_from_metadata` | 8592 | Map branch metadata to dataclass | proposal branch service/domain mapper | Move with proposal branch service. |
| `_read_title` | 8611 | Extract markdown H1 | proposal document parser or shared markdown helper | Shared helper; move after parser boundary. |
| `_read_markdown_section` | 8618 | Extract markdown section body | proposal document parser or shared markdown helper | Shared helper; move after parser boundary. |
| `_clean_proposal_title` | 8633 | Remove proposal id prefix from titles | proposal document parser/helper | Move with proposal service. |
| `_replace_status` | 9697 | Replace proposal status section | proposal document writer | Move with decision/proposal document service. |
| `_paragraph` | 9703 | Normalize optional paragraph body | proposal markdown renderer | Move with renderer. |
| `_bullets` | 9710 | Normalize optional bullet list | proposal markdown renderer | Move with renderer. |
| `_replace_section` | 9719 | Replace markdown section body | proposal document writer | Move with document writer. |
| `_review_request_suggestion` | 9901 | Build provider-specific review next action | proposal branch/review service | Move with proposal branch service. |

Related CLI surfaces:

- `proposal create`
- `proposal update`
- `proposal list`
- `proposal show`
- `proposal accept`
- `proposal reject`
- `proposal defer`
- `decision record`
- `contribution add`
- `contribution list`
- `proposal contribution add`
- `proposal contribution list`
- `proposal contributions`
- `proposal draft-commit`
- `proposal branch`
- `proposal status`
- `proposal publish`
- `proposal request-review`
- `proposal retire-branch`
- `proposal accept-branch`
- `proposal reject-branch`
- `proposal merge`
- `proposal finalize`
- `proposal cleanup`
- `proposal scan`

Related MCP surfaces:

- `p2p_proposal_create`
- `p2p_proposal_update`
- `p2p_proposal_contribution_add`
- `p2p_proposal_contribution_list`
- `p2p_proposal_list`
- `p2p_proposal_show`
- `p2p_proposal_accept`
- `p2p_proposal_reject`
- `p2p_proposal_defer`
- `p2p_proposal_draft_commit`
- `p2p_proposal_branch`
- `p2p_proposal_branch_status`
- `p2p_proposal_publish`
- `p2p_proposal_request_review`
- `p2p_proposal_accept_branch`
- `p2p_proposal_reject_branch`
- `p2p_proposal_merge`
- `p2p_proposal_finalize`
- `p2p_proposal_cleanup`
- `p2p_proposal_branch_scan`

Existing compatibility tests:

- `tests/test_cli.py::test_cli_validate_reports_duplicate_proposal_ids_as_error`
- `tests/test_cli.py::test_cli_registry_refresh_rejects_duplicate_proposal_ids`
- `tests/test_cli.py::test_cli_proposal_show_reports_ambiguous_duplicate_id_guidance`
- `tests/test_cli.py::test_cli_proposal_branch_creates_managed_branch_metadata`
- `tests/test_cli.py::test_cli_proposal_publish_request_review_and_scan`
- `tests/test_cli.py::test_cli_proposal_publish_auto_renumbers_on_remote_id_collision`
- `tests/test_cli.py::test_cli_proposal_publish_detects_collision_from_remote_main`
- `tests/test_cli.py::test_cli_proposal_retire_branch_records_reason`
- `tests/test_cli.py::test_cli_proposal_merge_merges_reviewed_branch_into_base`
- `tests/test_cli.py::test_cli_proposal_accept_branch_records_governance_decision`
- `tests/test_cli.py::test_cli_proposal_finalize_pushes_merged_base_branch`
- `tests/test_cli.py::test_cli_proposal_cleanup_deletes_local_and_remote_branch`
- `tests/test_cli.py::test_cli_import_exploration_file_and_record_decision`
- `tests/test_cli.py::test_cli_lists_proposal_contributions`
- `tests/test_cli.py::test_cli_proposal_accept_can_record_readiness_override`
- `tests/test_cli.py::test_cli_proposal_decision_shortcuts`
- `tests/test_cli.py::test_cli_proposal_list_show_and_choice_registry_output`
- `tests/test_cli.py::test_cli_missing_proposal_returns_clean_error`
- `tests/test_mcp.py::test_mcp_draft_proposal_decision_requires_granted_consent`
- `tests/test_mcp.py::test_mcp_draft_proposal_accept_and_defer_consume_matching_consent`
- `tests/test_mcp.py::test_mcp_proposal_draft_commit_then_branch_from_explicit_base`
- `tests/test_mcp.py::test_mcp_proposal_branch_refuses_proposal_branch_base_without_opt_in`
- `tests/test_mcp.py::test_mcp_proposal_publish_requires_and_consumes_consent`
- `tests/test_mcp.py::test_mcp_proposal_publish_rejects_actor_mismatch_without_consuming_consent`
- `tests/test_mcp.py::test_mcp_proposal_request_review_requires_and_consumes_consent`
- `tests/test_mcp.py::test_mcp_proposal_merge_requires_and_consumes_consent`
- `tests/test_mcp.py::test_mcp_proposal_finalize_requires_and_consumes_consent`
- `tests/test_mcp.py::test_mcp_proposal_reject_and_cleanup_require_consent`
- `tests/test_mcp.py::test_mcp_validate_reports_duplicate_proposal_ids`
- `tests/test_mcp.py::test_mcp_proposal_create_creates_draft_only`
- `tests/test_mcp.py::test_mcp_proposal_update_refines_draft_without_deciding`
- `tests/test_mcp.py::test_mcp_proposal_contribution_add_does_not_decide`

Extraction notes:

- Start with read/scaffold/update/contribution services before decision and
  branch services; they are less coupled to Git and consent.
- Keep proposal directory and file names stable:
  `proposal.md`, `decision.md`, `contributions.yml`, `comments.yml`,
  `ai-digest.md`, `clarifications.md`, `execution-plan.md`, `tasks.yml`, and
  exploration artifacts.
- Keep `Proposal`, `ProposalDetail`, `ProposalSummary`, `Contribution`,
  `ProposalContributionList`, and `Decision` return shapes stable while moving
  logic behind services.
- Preserve owner decision boundaries: creation, update, and contribution tools
  must not decide; accept/reject/defer and branch accept/reject remain
  owner-controlled.
- Preserve readiness warning/override behavior in CLI proposal acceptance; the
  readiness internals are mapped separately in T010.
- Preserve duplicate-id diagnostics and validation behavior; duplicate proposal
  handling overlaps with T012 validation/registry mapping.
- Do not merge document decision recording with managed branch decision
  recording without an explicit boundary in T017: they are both governance
  decisions, but they mutate different artifacts and have different operational
  consequences.

### Readiness, Context, Assessment, And Maturity

Covered by T010.

Current behavior:

- stores readiness profiles under `.p2p/config/readiness-profiles/*.yml`;
- stores per-proposal readiness under `.p2p/proposals/*/readiness.yml`;
- can read, write, refresh, initialize, explain, and owner-override proposal
  readiness;
- computes initial proposal readiness from proposal sections and exploration
  artifacts using deterministic text-quality heuristics;
- validates readiness profile and readiness assessment payloads;
- computes project assessment from validation, registry freshness, proposals,
  choices, Change Sets, Work items, project state, next actions, and optional
  maturity state;
- stores project assessment under `.p2p/project/assessment.yml`;
- computes project definition maturity from domain rubrics and evidence found
  in proposals and Change Sets;
- stores maturity assessment under `.p2p/project/maturity-assessment.yml`;
- returns compact context packets for agents with current state, next actions,
  relevant artifacts, allowed commands, explicit read limits, and bounded next
  step.

Candidate target areas:

- `p2p_engine.services.proposal_readiness`
- `p2p_engine.services.readiness_profiles`
- `p2p_engine.services.project_assessment`
- `p2p_engine.services.definition_maturity`
- `p2p_engine.services.context_packets`
- `p2p_engine.services.project_rubrics`
- `p2p_engine.adapters.filesystem`
- `p2p_engine.parsers.markdown`

These areas should not be collapsed into a generic "assessment" module.
Proposal readiness, project readiness, definition maturity, and compact context
answer different questions and have different source artifacts.

| Current method/helper | Line | Current responsibility | Candidate target area | Facade behavior |
| --- | ---: | --- | --- | --- |
| `readiness_profile` | 2542 | Read/create default readiness profile and map it to `ReadinessProfile` | `readiness_profiles` service | Keep method; delegate after extraction. |
| `read_proposal_readiness` | 2562 | Read readiness or synthesize `not_assessed` state | `proposal_readiness` service | Keep method; delegate after extraction. |
| `write_proposal_readiness` | 2596 | Validate and write proposal readiness payload | `proposal_readiness` service | Keep method; delegate after extraction. |
| `record_proposal_readiness_override` | 2604 | Record owner override forcing effective readiness | `proposal_readiness` service | Keep method; delegate after extraction. |
| `refresh_proposal_readiness` | 2629 | Refresh stored readiness or create `not_assessed` placeholder | `proposal_readiness` service | Keep method; delegate after extraction. |
| `initialize_proposal_readiness` | 2652 | Bootstrap readiness from proposal/exploration artifact evidence | `proposal_readiness` service with markdown parser | Keep method; delegate after extraction. |
| `refresh_project_assessment` | 3339 | Compute and write project readiness assessment | `project_assessment` service | Keep method; delegate after extraction. |
| `show_project_assessment` | 3346 | Read stored project assessment | `project_assessment` service | Keep method; delegate after extraction. |
| `refresh_definition_maturity` | 3420 | Compute and write project definition maturity | `definition_maturity` service | Keep method; delegate after extraction. |
| `show_definition_maturity` | 3427 | Read stored maturity assessment | `definition_maturity` service | Keep method; delegate after extraction. |
| `_compute_definition_maturity` | 3446 | Score rubric criteria against proposal/change evidence | `definition_maturity` service | Move behind service. |
| `_definition_evidence_records` | 3532 | Build maturity evidence records from proposals and Change Sets | `definition_maturity` service with proposal/change readers | Move behind service. |
| `_criterion_matches` | 3564 | Match rubric keywords against evidence text | `definition_maturity` service | Move behind service. |
| `_compute_project_assessment` | 3585 | Score project readiness from validation, registries, lifecycle state, and next actions | `project_assessment` service | Move behind service. |
| `context_packet` | 3752 | Build compact bounded agent context | `context_packets` service | Keep method; delegate after extraction. |
| `_default_context_artifacts` | 3843 | Select default compact artifacts from draft proposals, choices, and active changes | `context_packets` service | Move behind service. |
| `_context_artifact` | 3882 | Build target-specific context artifact summary | `context_packets` service | Move behind service. |
| `_context_allowed_commands` | 3937 | Provide safe command list by optional target type | `context_packets` service | Move behind service. |
| `_readiness_registry_records` | 6351 | Build readiness registry rows from proposal records | registry service or `proposal_readiness` service | Ownership to revisit in T012. |
| `_project_assessment_payload` | 8150 | Serialize project assessment dataclass to YAML payload | `project_assessment` service mapper | Move behind service. |
| `_definition_maturity_payload` | 8169 | Serialize maturity dataclass to YAML payload | `definition_maturity` service mapper | Move behind service. |
| `_short_text` | 8190 | Bound medium-context text snippets | `context_packets` service or shared text helper | Move with context packet logic if not reused. |
| `_default_readiness_profile_payload` | 8227 | Build default readiness profile config | `readiness_profiles` service | Move behind service. |
| `_validate_readiness_profile_payload` | 8300 | Validate readiness profile schema and scoring rules | `readiness_profiles` service | Move behind service. |
| `_validate_readiness_assessment_payload` | 8350 | Validate proposal readiness assessment schema | `proposal_readiness` service | Move behind service. |
| `_refresh_readiness_payload` | 8433 | Recompute score, label, missing, suggested next, and failed gates | `proposal_readiness` service | Move behind service. |
| `_readiness_effective_points` | 8485 | Apply artifact-quality caps to criterion points | `proposal_readiness` service | Move behind service. |
| `_readiness_label` | 8503 | Map numeric readiness score to label thresholds | `proposal_readiness` service | Move behind service. |
| `_readiness_text_quality` | 9765 | Classify artifact text as missing/placeholder/thin/meaningful | `proposal_readiness` service or text-quality helper | Move behind service. |
| `_initial_readiness_points` | 9794 | Convert initial text quality into criterion points | `proposal_readiness` service | Move behind service. |

Related CLI surfaces:

- `context`
- `assess refresh`
- `assess show`
- `assess maturity refresh`
- `assess maturity show`
- `proposal readiness show`
- `proposal readiness refresh`
- `proposal readiness init`
- `proposal readiness explain`
- `proposal accept --override-readiness`

Related MCP surfaces:

- `p2p_context`
- `p2p_assess_refresh`
- `p2p_assess_show`
- `p2p_maturity_refresh`
- `p2p_maturity_show`
- `p2p_proposal_readiness_get`
- `p2p_proposal_readiness_init`
- `p2p_proposal_readiness_refresh`
- `p2p_proposal_readiness_explain`
- `p2p_proposal_readiness_list_gaps`

Existing compatibility tests:

- `tests/test_cli.py::test_cli_assess_refresh_and_show`
- `tests/test_cli.py::test_cli_assess_show_requires_refresh`
- `tests/test_cli.py::test_cli_project_rubrics_and_definition_maturity`
- `tests/test_cli.py::test_cli_context_returns_compact_packet`
- `tests/test_cli.py::test_cli_context_target_limits_artifact_details`
- `tests/test_cli.py::test_cli_proposal_readiness_status_refresh_and_explain`
- `tests/test_cli.py::test_cli_proposal_accept_can_record_readiness_override`
- `tests/test_cli.py::test_cli_registry_refresh_status_and_show`
- `tests/test_cli.py::test_cli_next_falls_back_to_draft_proposal_review`
- `tests/test_cli.py::test_cli_next_falls_back_to_improve_low_readiness_draft`
- `tests/test_mcp.py::test_mcp_assess_refresh_and_show`
- `tests/test_mcp.py::test_mcp_proposal_readiness_tools_are_advisory`
- `tests/test_mcp.py::test_mcp_context_returns_compact_packet`
- `tests/test_mcp.py::test_mcp_project_definition_maturity`

Extraction notes:

- Proposal readiness is a good candidate after proposal document parsing exists;
  it depends on proposal sections, exploration artifacts, and markdown helpers.
- Keep readiness advisory. Refresh/init/explain must not accept, reject, defer,
  merge, publish, or otherwise make governance decisions.
- Preserve owner override fields and semantics exactly:
  `owner_override`, `effective_status`, `effective_score`,
  `override_reason`, `override_approver`, `override_recorded_at`.
- Preserve default profile scoring totals, thresholds, quality caps, and tier
  requirements.
- Project assessment depends on broad lifecycle services. It should be
  extracted after summaries for proposals, choices, changes, work, registries,
  validation, project state, and next actions have stable service facades.
- Definition maturity depends on project rubrics and evidence from proposals and
  Change Sets. Keep rubric initialization/show mapped with T006, but define the
  final boundary in T017/T018.
- Context packets are presentation-oriented but behaviorally important for token
  discipline. Preserve budget validation, target normalization, omitted body
  behavior for small budget, allowed commands, do-not-read guidance, and bounded
  next step selection.
- Readiness registry rows overlap with registry extraction and should be
  finalized in T012 rather than moved prematurely.

### Prompt And Import Workflows

Covered by T011.

Current behavior:

- generates proposal-scoped prompts under `.p2p/prompts/PROP-XXX/*.prompt.md`
  for explore, digest, clarify, synthesize, plan, tasks, swot, and impact;
- imports proposal-scoped exploration artifacts, clarification output,
  synthesized proposal markdown, execution plan, tasks YAML, and impact YAML
  artifacts;
- reports exploration artifact status and suggested next prompt command;
- creates intake prompt workspaces under `.p2p/intake/INTAKE-XXX`;
- imports intake recommendations, related proposal mappings, suggested actions,
  and context;
- lists intake analysis status;
- creates operational project brief context and prompt artifacts under
  `.p2p/project`;
- imports and shows operational project brief artifacts;
- creates software-spec refinement prompts from deterministic generated spec
  context;
- imports refined software-spec artifact directories after validating required
  files and YAML top-level keys.

Candidate target areas:

- `p2p_engine.services.proposal_prompts`
- `p2p_engine.services.proposal_imports`
- `p2p_engine.services.intake`
- `p2p_engine.services.project_brief`
- `p2p_engine.services.software_spec_prompting`
- `p2p_engine.services.software_spec_imports`
- `p2p_engine.renderers.prompts`
- `p2p_engine.adapters.filesystem`
- `p2p_engine.validators.yaml_shapes`
- `p2p_engine.services.artifact_quality`

Prompt rendering and artifact importing should be split. Prompt generation is
advisory and should not import output or make governance decisions. Importing is
write-safe only for well-known artifact paths and should preserve shape
validation.

| Current method/helper | Line | Current responsibility | Candidate target area | Facade behavior |
| --- | ---: | --- | --- | --- |
| `generate_prompt` | 2924 | Build proposal prompt context and render prompt file for supported prompt kinds | `proposal_prompts` service plus prompt renderers | Keep method; delegate after extraction. |
| `import_exploration` | 2970 | Import exploration directory or file into proposal artifacts | `proposal_imports` service | Keep method; delegate after extraction. |
| `exploration_status` | 2991 | Report exploration artifact presence, quality, unresolved questions, and next command | `proposal_imports` or `artifact_quality` service | Keep method; delegate after extraction. |
| `import_artifact` | 3020 | Import clarify/synthesize/plan/tasks single-file outputs to fixed proposal files | `proposal_imports` service | Keep method; delegate after extraction. |
| `import_impact` | 3039 | Import impact-map, related-proposals, and conflict-analysis artifacts | `proposal_imports` or impact service | Keep method; delegate after extraction. |
| `create_project_brief_prompt` | 3291 | Generate project brief context and prompt | `project_brief` service plus prompt renderer | Keep method; delegate after extraction. |
| `import_project_brief` | 3305 | Import operational brief and optional next actions | `project_brief` service | Keep method; delegate after extraction. |
| `show_project_brief` | 3334 | Read imported operational brief | `project_brief` service | Keep method; delegate after extraction. |
| `create_software_spec_prompt` | 4053 | Refresh deterministic software spec and render refinement prompt | `software_spec_prompting` service | Keep method; delegate after extraction; full spec boundary in T014. |
| `import_software_spec` | 4069 | Import validated refined software-spec directory | `software_spec_imports` service | Keep method; delegate after extraction; full spec boundary in T014. |
| `create_intake_prompt` | 5555 | Allocate intake id, write raw input/context/prompt and placeholder artifacts | `intake` service plus prompt renderer | Keep method; delegate after extraction. |
| `import_intake` | 5600 | Import recommendation, related proposals, suggested actions, and context | `intake` service | Keep method; delegate after extraction. |
| `intake_statuses` | 5629 | List intake records and analyzed/pending state | `intake` service | Keep method; delegate after extraction. |
| `_intake_context` | 6382 | Build registry/project context for intake prompt | `intake` service or context builder | Move behind service. |
| `_project_brief_context` | 6422 | Build registry/project context for operational brief prompt | `project_brief` service or context builder | Move behind service. |
| `_next_intake_id` | 6993 | Allocate sequential intake id | `intake` service | Move behind service. |
| `_find_intake_dir` | 7002 | Resolve existing intake directory | `intake` service | Move behind service. |
| `_intake_prompt_markdown` | 8777 | Render intake prompt markdown | prompt renderer | Move behind renderer. |
| `_project_brief_prompt_markdown` | 8811 | Render operational brief prompt markdown | prompt renderer | Move behind renderer. |
| `_software_spec_required_files` | 8854 | Return required software-spec artifact filenames | software-spec service/import validator | Ownership finalized in T014. |
| `_software_spec_refine_prompt` | 9598 | Render software-spec refinement prompt | software-spec prompt renderer | Ownership finalized in T014. |
| `_has_meaningful_content` | 9724 | Detect non-placeholder artifact content | `artifact_quality` helper | Shared with readiness; move after boundary decision. |
| `_artifact_quality_state` | 9738 | Classify artifact quality state | `artifact_quality` helper | Shared with readiness; move after boundary decision. |
| `_count_open_questions` | 9813 | Count unresolved open questions | `artifact_quality` or proposal analysis helper | Shared helper. |
| `_validate_tasks_yaml` | 9822 | Validate imported tasks YAML top-level shape | `validators.yaml_shapes` | Move behind import service. |
| `_validate_yaml_key` | 9831 | Validate imported YAML top-level key | `validators.yaml_shapes` | Move behind import service. |

Prompt renderer modules already exist under `src/p2p_engine/prompts/`:

- `explore.py`
- `digest.py`
- `clarify.py`
- `synthesize.py`
- `plan.py`
- `tasks.py`
- `swot.py`
- `impact.py`
- `common.py`

Those modules are natural renderer boundaries. The extraction should move
context gathering and file writes out of `P2PWorkspace`, not rewrite the prompt
templates unless behavior needs to change later.

Related CLI surfaces:

- `explore prompt`
- `explore import`
- `explore status`
- `digest prompt`
- `clarify prompt`
- `clarify import`
- `synthesize prompt`
- `synthesize import`
- `plan prompt`
- `plan import`
- `tasks prompt`
- `tasks import`
- `swot prompt`
- `impact prompt`
- `impact import`
- `project brief prompt`
- `project brief import`
- `project brief show`
- `spec prompt`
- `spec import`
- `intake prompt`
- `intake import`
- `intake status`

Related MCP surfaces:

- `p2p_explore_prompt`
- `p2p_digest_prompt`
- `p2p_clarify_prompt`
- `p2p_synthesize_prompt`
- `p2p_plan_prompt`
- `p2p_tasks_prompt`
- `p2p_swot_prompt`
- `p2p_impact_prompt`
- `p2p_spec_prompt`
- `p2p_intake_prompt`
- `p2p_intake_status`
- `p2p_project_brief_prompt`
- `p2p_project_brief_show`

Existing compatibility tests:

- `tests/test_cli.py::test_cli_init_status_create_and_prompt_flow`
- `tests/test_cli.py::test_cli_import_exploration_file_and_record_decision`
- `tests/test_cli.py::test_cli_missing_proposal_returns_clean_error`
- `tests/test_cli.py::test_cli_prompt_only_import_workflow_to_tasks`
- `tests/test_cli.py::test_cli_tasks_import_rejects_invalid_yaml_shape`
- `tests/test_cli.py::test_cli_governance_swot_vote_and_precedent_flow`
- `tests/test_cli.py::test_cli_impact_import_and_conflict_memory`
- `tests/test_cli.py::test_cli_software_spec_refresh_prompt_import_status_and_show`
- `tests/test_cli.py::test_cli_intake_prompt_import_and_status`
- `tests/test_cli.py::test_cli_project_brief_prompt_import_and_show`
- `tests/test_mcp.py::test_mcp_intake_prompt_and_status`
- `tests/test_mcp.py::test_mcp_project_brief_prompt_and_show`
- `tests/test_mcp.py::test_mcp_impact_prompt_generates_prompt_only`
- `tests/test_mcp.py::test_mcp_prompt_tools_generate_prompts_without_importing_outputs`

Extraction notes:

- Keep prompt tools advisory. Generating a prompt must not import artifacts,
  record decisions, accept/reject/defer proposals, merge branches, or apply
  recommendations.
- Keep import paths fixed and explicit. Do not allow arbitrary writes from
  imported prompt outputs.
- Preserve validation for `tasks.yml`, `impact-map.yml`,
  `related-proposals.yml`, `conflict-analysis.yml`, `next-actions.yml`,
  intake YAML, and software-spec YAML files.
- Preserve file/directory import behavior: directory imports copy known files;
  single-file imports map to one known target where supported.
- Keep software-spec prompt/import mapped here only as prompt/import behavior.
  Software-spec refresh/status/show/export/rendering belongs to T014.
- Intake apply planning/running is not part of this prompt/import boundary; it
  belongs to T013 with choices, next actions, and governance workflow effects.
- Artifact quality helpers are shared by exploration status and readiness. Do
  not move them into only one service until the shared boundary is explicit.

### Project State, Registries, Validation, And Parsing Helpers

Covered by T012.

Current behavior:

- exposes base workspace status from `.p2p/project.yml` and proposal
  directories;
- validates minimal workspace structure, YAML readability, readiness profiles,
  readiness assessments, agent integrations, permissions, consents, proposal
  directory shape, proposal/decision sections, status consistency, duplicate
  proposal ids, and registry freshness;
- generates rationalized project state under `.p2p/project` from accepted
  proposals;
- reads project state status and project sections;
- refreshes generated registries for proposals, decisions, changes, choices,
  relations, artifacts, and readiness;
- reports registry freshness and record counts;
- reads one generated registry by logical name;
- centralizes low-level YAML, markdown, frontmatter, slug, id, duplicate-id,
  artifact-quality, and YAML-shape helpers used by many domains.

Candidate target areas:

- `p2p_engine.services.workspace_status`
- `p2p_engine.services.validation`
- `p2p_engine.services.project_state`
- `p2p_engine.services.registries`
- `p2p_engine.services.registry_records`
- `p2p_engine.parsers.markdown`
- `p2p_engine.parsers.frontmatter`
- `p2p_engine.validators.yaml_shapes`
- `p2p_engine.services.id_resolution`
- `p2p_engine.services.artifact_quality`
- `p2p_engine.adapters.filesystem`

This is the main shared-infrastructure boundary. It should be extracted after
the first narrow service extraction proves the facade/delegation pattern,
because many other services currently depend on these helpers.

| Current method/helper | Line | Current responsibility | Candidate target area | Facade behavior |
| --- | ---: | --- | --- | --- |
| `status` | 1461 | Read project name and proposal summaries | `workspace_status` service | Keep method; delegate after extraction. |
| `check` | 2303 | Verify minimal required workspace paths | `validation` service | Keep method; delegate after extraction. |
| `validate` | 2319 | Run structural and semantic validation findings | `validation` service with domain validators | Keep method; delegate after extraction. |
| `refresh_project_state` | 3202 | Generate project overview/problem/scope/swot/decision map/features from accepted proposals | `project_state` service | Keep method; delegate after extraction. |
| `project_state_status` | 3260 | Summarize generated project state, features, brief, and next actions | `project_state` service | Keep method; delegate after extraction. |
| `show_project_state` | 3278 | Read generated project section or feature markdown | `project_state` service | Keep method; delegate after extraction. |
| `refresh_registries` | 5408 | Generate all registry files from source artifacts | `registries` service | Keep method; delegate after extraction. |
| `registry_status` | 5469 | Report generated registry presence, record counts, and staleness | `registries` service | Keep method; delegate after extraction. |
| `show_registry` | 5530 | Read one generated registry by logical name | `registries` service | Keep method; delegate after extraction. |
| `_proposal_registry_records` | 6139 | Build proposal registry rows | `registry_records` or proposal service | Move behind registry service. |
| `_decision_registry_records` | 6173 | Build decision registry rows from proposals | `registry_records` or decision service | Move behind registry service. |
| `_change_registry_records` | 6194 | Build Change Set registry rows | `registry_records` or change service | Move behind registry service. |
| `_choice_registry_records` | 6230 | Build choice registry rows including proposal votes | `registry_records` or choice service | Move behind registry service. |
| `_relation_registry_records` | 6293 | Build relation rows across proposals and changes | `registry_records` service | Move behind registry service. |
| `_artifact_registry_records` | 6327 | Build artifact rows for proposals and changes | `registry_records` service | Move behind registry service. |
| `_readiness_registry_records` | 6351 | Build readiness registry rows | registry service with proposal readiness dependency | Move behind registry service. |
| `_changes_for_proposal` | 6378 | Resolve Change Sets that include one proposal | relation/registry helper | Move behind registry service. |
| `_project_name` | 1411 | Read project display name | project metadata service | Shared helper; delegate later. |
| `_repository_mode` | 1419 | Read local/remote repository mode | project metadata service | Shared helper; already relevant to T006/T008. |
| `_set_repository_mode` | 1448 | Persist repository mode | project metadata service | Shared helper; already relevant to T006/T008. |
| `_next_proposal_id` | 6803 | Allocate proposal id | `id_resolution` or proposal service | Move with proposal service. |
| `_find_proposal_dir` | 6812 | Resolve proposal directory and reject ambiguity | `id_resolution` or proposal service | Move with proposal service. |
| `_duplicate_proposal_ids` | 6827 | Detect duplicate proposal ids | `validation` or `id_resolution` service | Shared by validation and registries. |
| `_next_change_id` | 6973 | Allocate Change Set id | `id_resolution` or change service | Move with change service. |
| `_find_change_dir` | 6982 | Resolve Change Set directory | `id_resolution` or change service | Move with change service. |
| `_next_intake_id` | 6993 | Allocate intake id | `id_resolution` or intake service | Move with intake service. |
| `_find_intake_dir` | 7002 | Resolve intake directory | `id_resolution` or intake service | Move with intake service. |
| `_next_choice_id` | 7011 | Allocate choice id | `id_resolution` or choice service | Move with choice service. |
| `_find_choice_dir` | 7020 | Resolve choice directory | `id_resolution` or choice service | Move with choice service. |
| `_next_work_id` | 7031 | Allocate Work id | `id_resolution` or work service | Move with work service. |
| `_find_work_dir` | 7040 | Resolve Work directory | `id_resolution` or work service | Move with work service. |
| `_slugify` | 8008 | Produce stable slug strings | shared text/id helper | Move after service ownership is clear. |
| `_yaml_dump` | 8013 | Dump YAML with project formatting | filesystem/YAML adapter | Shared helper. |
| `_read_optional` | 8534 | Read text file or return empty string | filesystem adapter | Shared helper. |
| `_read_yaml` | 8538 | Read YAML with default | filesystem/YAML adapter | Shared helper. |
| `_read_yaml_mapping` | 8545 | Read YAML mapping or fail | filesystem/YAML adapter | Shared helper. |
| `_read_proposal_status` | 8552 | Parse proposal markdown status | markdown parser/proposal document service | Already mapped in T009. |
| `_duplicate_proposal_ids_message` | 8570 | Format duplicate id diagnostic | validation/id service | Move with duplicate-id validation. |
| `_read_title` | 8611 | Parse markdown H1 | markdown parser | Shared helper. |
| `_read_markdown_section` | 8618 | Parse markdown section body | markdown parser | Shared helper. |
| `_markdown_has_section` | 8630 | Test for markdown section presence | markdown parser | Shared helper. |
| `_clean_proposal_title` | 8633 | Remove proposal id prefix from H1 | proposal document helper | Already mapped in T009. |
| `_read_frontmatter` | 8638 | Parse YAML frontmatter | frontmatter parser | Shared helper. |
| `_replace_frontmatter` | 8651 | Replace YAML frontmatter and preserve body | frontmatter writer | Shared helper. |
| `_replace_status` | 9697 | Replace markdown status section | markdown writer | Shared helper; used by decisions. |
| `_replace_section` | 9719 | Replace markdown section body | markdown writer | Shared helper. |
| `_has_meaningful_content` | 9724 | Detect non-placeholder artifact content | `artifact_quality` service | Shared with T010/T011. |
| `_artifact_quality_state` | 9738 | Classify artifact quality state | `artifact_quality` service | Shared with T010/T011. |
| `_has_meaningful_intake_recommendation` | 9806 | Detect imported intake recommendation | intake/artifact-quality helper | Move with intake or artifact-quality. |
| `_count_open_questions` | 9813 | Count unresolved question bullets | artifact/proposal analysis helper | Shared helper. |
| `_validate_tasks_yaml` | 9822 | Validate task YAML shape | `validators.yaml_shapes` | Shared with import/change services. |
| `_validate_yaml_key` | 9831 | Validate YAML top-level key | `validators.yaml_shapes` | Shared import/export helper. |

Related CLI surfaces:

- `status`
- `check`
- `validate`
- `project refresh`
- `project status`
- `project show`
- `registry refresh`
- `registry status`
- `registry show`

Related MCP surfaces:

- `p2p_validate`
- `p2p_project_refresh`
- `p2p_project_status`
- `p2p_project_show`
- `p2p_registry_refresh`
- `p2p_registry_status`
- `p2p_registry_show`

Existing compatibility tests:

- `tests/test_cli.py::test_cli_init_status_create_and_prompt_flow`
- `tests/test_cli.py::test_cli_validate_reports_invalid_permissions_policy`
- `tests/test_cli.py::test_cli_validate_valid_project_and_json_output`
- `tests/test_cli.py::test_cli_validate_reports_invalid_yaml_as_error`
- `tests/test_cli.py::test_cli_validate_reports_stale_registries_as_warning`
- `tests/test_cli.py::test_cli_validate_reports_duplicate_proposal_ids_as_error`
- `tests/test_cli.py::test_cli_registry_refresh_rejects_duplicate_proposal_ids`
- `tests/test_cli.py::test_cli_proposal_show_reports_ambiguous_duplicate_id_guidance`
- `tests/test_cli.py::test_cli_project_refresh_status_and_show`
- `tests/test_cli.py::test_cli_registry_refresh_status_and_show`
- `tests/test_cli.py::test_cli_registry_includes_choice_artifacts`
- `tests/test_mcp.py::test_mcp_registry_refresh_tool`
- `tests/test_mcp.py::test_mcp_validate_returns_structured_findings`
- `tests/test_mcp.py::test_mcp_validate_reports_duplicate_proposal_ids`
- `tests/test_mcp.py::test_mcp_change_project_registry_and_remote_read_tools`

Extraction notes:

- Do not make registry files source of truth. They are generated views over
  proposal, decision, change, choice, artifact, and readiness state.
- Keep `refresh_registries` duplicate-id guard before writing generated
  registries; ambiguous proposal ids make downstream views unreliable.
- Keep validation read-only. Validation may compute findings and suggested
  commands, but it must not repair state.
- Move parser helpers carefully. Markdown/frontmatter helpers are currently used
  by proposals, decisions, changes, choices, project state, registries, and
  readiness.
- Keep project state generation separate from spec/export generation. The
  `.p2p/project` view is a rationalized P2P project memory, not software
  implementation specs.
- Keep generated project state under P2P governance state for now; the separate
  visible root output concern belongs to the accepted proposal/export work, not
  to this local refactoring inventory.
- Consolidate YAML validators only when callers can preserve their current error
  messages.

### Change Sets, Work, Choices, Conflicts, And Next Actions

Covered by T013.

Current behavior:

- creates Change Sets from accepted proposals and writes Change Set metadata,
  included/referenced proposal links, decisions, impact map, git policy,
  execution plan, tasks, and actions;
- lists, shows, policy-checks, status-transitions, and task-views Change Sets;
- creates Work plans from validated software-spec exports;
- manages Work lifecycle from planned to branch, submit, review, publish,
  external review request, accept, conflict continue/abort, finalize, cleanup,
  and branch scan;
- records and reads proposal conflicts in `.p2p/project/conflicts.yml`;
- creates project choices, lists/shows choices, discovers advisory choice
  findings, blocks/unblocks proposals or Change Sets on choices, and decides
  choices;
- creates intake apply plans from imported intake suggested actions and runs
  the supported write-safe actions;
- combines curated next actions, active choice blockers, and generated fallback
  next actions, with lifecycle support for add, complete, retire, refresh, and
  audit log.

Candidate target areas:

- `p2p_engine.services.change_sets`
- `p2p_engine.services.work_plans`
- `p2p_engine.services.work_branches`
- `p2p_engine.services.choices`
- `p2p_engine.services.conflicts`
- `p2p_engine.services.next_actions`
- `p2p_engine.services.intake_apply`
- `p2p_engine.adapters.git`
- `p2p_engine.adapters.filesystem`
- `p2p_engine.renderers.change_markdown`
- `p2p_engine.renderers.work_manifest`

Work lifecycle and proposal branch lifecycle are similar but should not be
merged first. Work is implementation-oriented and tied to Change Sets and
software-spec exports; proposal branches are governance collaboration around
proposal text. The shared part is Git adapter behavior, not the domain service.

| Current method/helper | Line | Current responsibility | Candidate target area | Facade behavior |
| --- | ---: | --- | --- | --- |
| `create_change_set` | 5252 | Create Change Set from an accepted proposal and seed metadata/artifacts | `change_sets` service | Keep method; delegate after extraction. |
| `change_set_statuses` | 5310 | List Change Set summaries from frontmatter | `change_sets` service | Keep method; delegate after extraction. |
| `change_set_policy` | 5331 | Read metadata-only Git policy for Change Set | `change_sets` or policy service | Keep method; delegate after extraction. |
| `show_change_set` | 5352 | Read Change Set detail from markdown/frontmatter | `change_sets` service | Keep method; delegate after extraction. |
| `update_change_set_status` | 5370 | Enforce allowed Change Set status transitions | `change_sets` service | Keep method; delegate after extraction. |
| `change_set_tasks` | 5392 | Read Change Set tasks/actions views | `change_sets` service | Keep method; delegate after extraction. |
| `_change_markdown` | 8728 | Render initial Change Set markdown/frontmatter | change renderer | Move with Change Set service. |
| `create_work_plan` | 4225 | Create Work manifest from validated software-spec export | `work_plans` service | Keep method; delegate after extraction. |
| `work_statuses` | 4252 | List Work status rows from local manifests and branch scan registry | `work_plans` service | Keep method; delegate after extraction. |
| `work_summaries` | 4285 | List actionable Work summaries | `work_plans` service | Keep method; delegate after extraction. |
| `show_work` | 4297 | Read one Work manifest as detail | `work_plans` service | Keep method; delegate after extraction. |
| `_work_summary_from_manifest` | 4313 | Convert local Work manifest to summary | `work_plans` service mapper | Move behind service. |
| `_work_summary_from_scan` | 4359 | Convert scanned branch registry row to summary | `work_plans` service mapper | Move behind service. |
| `branch_work` | 4384 | Create managed Work branch and update manifest | `work_branches` service with Git adapter | Keep method; delegate after extraction. |
| `retire_work` | 4450 | Retire planned Work without touching Git | `work_plans` service | Keep method; delegate after extraction. |
| `submit_work` | 4475 | Commit non-manifest Work changes on managed branch | `work_branches` service with Git adapter | Keep method; delegate after extraction. |
| `review_work` | 4537 | Mark submitted Work ready for local review | `work_branches` service | Keep method; delegate after extraction. |
| `publish_work` | 4596 | Push reviewed Work branch to remote | `work_branches` service with Git adapter | Keep method; delegate after extraction. |
| `request_external_work_review` | 4658 | Record provider-advisory external review metadata | `work_branches` service | Keep method; delegate after extraction. |
| `accept_work` | 4738 | Owner-controlled merge of published Work into base branch | `work_branches` service with Git adapter | Keep method; delegate after extraction. |
| `continue_accept_work` | 4838 | Continue Work accept after resolving merge conflicts | `work_branches` service with Git adapter | Keep method; delegate after extraction. |
| `abort_accept_work` | 4896 | Abort conflicted Work accept merge and restore manifest | `work_branches` service with Git adapter | Keep method; delegate after extraction. |
| `finalize_work` | 4930 | Push accepted base branch and mark Work finalized | `work_branches` service with Git adapter | Keep method; delegate after extraction. |
| `cleanup_work` | 4988 | Delete finalized Work branches and record cleanup | `work_branches` service with Git adapter | Keep method; delegate after extraction. |
| `_scanned_work_items` | 5068 | Read Work branch scan registry rows | `work_branches` or registry service | Move behind service. |
| `scan_work_branches` | 5084 | Scan local `p2p/work/*` branches without checkout | `work_branches` service with Git adapter | Keep method; delegate after extraction. |
| `_work_manifest` | 8673 | Build initial Work manifest payload | work manifest renderer/factory | Move with Work planning. |
| `_work_next_action` | 9865 | Compute Work next action and note by status | `work_plans` service | Move behind service. |
| `record_conflict` | 5204 | Append project conflict record for two or more proposals | `conflicts` service | Keep method; delegate after extraction. |
| `conflict_status` | 5239 | Read recorded project conflicts | `conflicts` service | Keep method; delegate after extraction. |
| `create_choice` | 5799 | Create project choice markdown/options/decision/links artifacts | `choices` service | Keep method; delegate after extraction. |
| `choice_statuses` | 5891 | List project choices | `choices` service | Keep method; delegate after extraction. |
| `show_choice` | 5913 | Read project choice detail, options, links, blocks | `choices` service | Keep method; delegate after extraction. |
| `discover_choices` | 5938 | Produce advisory findings for proposal-local and project choices | `choices` service | Keep method; delegate after extraction. |
| `block_choice` | 5991 | Record or update active choice blocker | `choices` service | Keep method; delegate after extraction. |
| `unblock_choice` | 6033 | Mark active choice blocker inactive | `choices` service | Keep method; delegate after extraction. |
| `decide_choice` | 6056 | Select option and write decision/frontmatter status | `choices` service | Keep method; delegate after extraction. |
| `_find_choice_option` | 9840 | Resolve option by id or title | `choices` service helper | Move behind service. |
| `create_intake_apply_plan` | 5647 | Convert intake suggested actions into controlled apply plan | `intake_apply` service | Keep method; delegate after extraction. |
| `show_intake_apply_plan` | 5695 | Read controlled intake apply plan | `intake_apply` service | Keep method; delegate after extraction. |
| `run_intake_apply_action` | 5710 | Execute supported intake apply actions and audit applied action | `intake_apply` service | Keep method; delegate after extraction. |
| `_intake_apply_action_metadata` | 6496 | Classify intake suggested action support and preview command | `intake_apply` service | Move behind service. |
| `_find_apply_plan_action` | 9852 | Resolve apply plan action by id | `intake_apply` service helper | Move behind service. |
| `next_actions` | 5129 | Combine choice blockers, curated actions, and generated fallbacks | `next_actions` service | Keep method; delegate after extraction. |
| `next_action_add` | 5139 | Add curated next action | `next_actions` service | Keep method; delegate after extraction. |
| `next_action_complete` | 5179 | Close curated next action as completed | `next_actions` service | Keep method; delegate after extraction. |
| `next_action_retire` | 5182 | Close curated next action as retired | `next_actions` service | Keep method; delegate after extraction. |
| `next_actions_refresh` | 5185 | Normalize curated next actions and count generated actions | `next_actions` service | Keep method; delegate after extraction. |
| `_next_actions_from_project_file` | 6526 | Read active curated next actions | `next_actions` service | Move behind service. |
| `_next_actions_path` | 6543 | Resolve active next actions path | `next_actions` service/filesystem adapter | Move behind service. |
| `_next_actions_log_path` | 6546 | Resolve next actions audit log path | `next_actions` service/filesystem adapter | Move behind service. |
| `_read_next_actions_payload` | 6549 | Read active next action payload | `next_actions` service | Move behind service. |
| `_write_next_actions_payload` | 6555 | Write active next action payload | `next_actions` service | Move behind service. |
| `_next_action_from_record` | 6560 | Convert next action record to dataclass | `next_actions` service mapper | Move behind service. |
| `_normalize_next_action_record` | 6571 | Normalize curated next action record | `next_actions` service | Move behind service. |
| `_next_curated_next_action_id` | 6581 | Allocate curated next action id | `next_actions` service | Move behind service. |
| `_close_next_action` | 6591 | Move next action to audit log with status/reason | `next_actions` service | Move behind service. |
| `_dedupe_next_actions` | 6633 | Dedupe next actions by kind/target | `next_actions` service | Move behind service. |
| `_fallback_next_actions` | 6644 | Generate fallback next actions from registries, changes, intake, proposals, readiness, choices | `next_actions` service | Move behind service. |
| `_active_choice_blocker_actions` | 6776 | Generate high-priority next actions from active choice blockers | `next_actions` service with choices dependency | Move behind service. |

Related CLI surfaces:

- `change create`
- `change status`
- `change policy`
- `change show`
- `change set-status`
- `change tasks`
- `work plan`
- `work list`
- `work status`
- `work scan`
- `work branch`
- `work retire`
- `work submit`
- `work review`
- `work publish`
- `work request-review`
- `work accept`
- `work finalize`
- `work cleanup`
- `work show`
- `choice create`
- `choice list`
- `choice status`
- `choice show`
- `choice discover`
- `choice block`
- `choice unblock`
- `choice decide`
- `conflict record`
- `conflict status`
- `next`, `next list`
- `next add`
- `next complete`
- `next retire`
- `next refresh`
- `intake apply plan`
- `intake apply show`
- `intake apply run`

Related MCP surfaces:

- `p2p_change_create`
- `p2p_change_status`
- `p2p_change_show`
- `p2p_change_tasks`
- `p2p_work_plan`
- `p2p_work_list`
- `p2p_work_status`
- `p2p_work_show`
- `p2p_choice_discover`
- `p2p_choice_list`
- `p2p_choice_show`
- `p2p_conflict_status`
- `p2p_next`
- `p2p_next_add`
- `p2p_next_complete`
- `p2p_next_retire`
- `p2p_next_refresh`

Existing compatibility tests:

- `tests/test_cli.py::test_cli_change_create_status_and_policy`
- `tests/test_cli.py::test_cli_change_lifecycle_show_and_tasks`
- `tests/test_cli.py::test_cli_work_plan_list_and_show`
- `tests/test_cli.py::test_cli_work_retire_marks_planned_work_retired`
- `tests/test_cli.py::test_cli_work_retire_requires_planned_status`
- `tests/test_cli.py::test_cli_work_branch_creates_managed_branch`
- `tests/test_cli.py::test_cli_work_branch_requires_clean_worktree`
- `tests/test_cli.py::test_cli_work_submit_creates_local_commit`
- `tests/test_cli.py::test_cli_work_submit_requires_non_manifest_changes`
- `tests/test_cli.py::test_cli_work_review_requests_local_review`
- `tests/test_cli.py::test_cli_work_review_requires_submitted_clean_branch`
- `tests/test_cli.py::test_cli_work_publish_pushes_reviewed_branch`
- `tests/test_cli.py::test_cli_work_publish_requires_review_and_remote`
- `tests/test_cli.py::test_cli_work_request_review_records_provider_handoff`
- `tests/test_cli.py::test_cli_work_accept_merges_published_branch`
- `tests/test_cli.py::test_cli_work_accept_requires_published_base_branch`
- `tests/test_cli.py::test_cli_work_finalize_requires_accepted_and_remote`
- `tests/test_cli.py::test_cli_work_cleanup_requires_finalized_branch`
- `tests/test_cli.py::test_cli_work_accept_conflict_continue_and_abort`
- `tests/test_cli.py::test_cli_work_scan_reads_local_branch_without_checkout`
- `tests/test_cli.py::test_cli_impact_import_and_conflict_memory`
- `tests/test_cli.py::test_cli_registry_includes_choice_artifacts`
- `tests/test_cli.py::test_cli_choice_create_list_and_decide`
- `tests/test_cli.py::test_cli_choice_discovery_blocking_and_next_integration`
- `tests/test_cli.py::test_cli_intake_apply_plan_show_and_run`
- `tests/test_cli.py::test_cli_next_falls_back_without_imported_next_actions`
- `tests/test_cli.py::test_cli_next_falls_back_to_draft_proposal_review`
- `tests/test_cli.py::test_cli_next_falls_back_to_improve_low_readiness_draft`
- `tests/test_cli.py::test_cli_next_manages_curated_lifecycle_and_log`
- `tests/test_cli.py::test_cli_next_retire_and_refresh`
- `tests/test_cli.py::test_cli_next_shows_generated_actions_when_curated_actions_exist`
- `tests/test_cli.py::test_cli_next_deduplicates_curated_and_generated_actions`
- `tests/test_mcp.py::test_mcp_managed_next_action_lifecycle`
- `tests/test_mcp.py::test_mcp_next_retire_and_refresh`
- `tests/test_mcp.py::test_mcp_choice_discover_is_advisory`
- `tests/test_mcp.py::test_mcp_conflict_status_reads_without_recording`
- `tests/test_mcp.py::test_mcp_change_project_registry_and_remote_read_tools`
- `tests/test_mcp.py::test_mcp_write_safe_spec_export_and_work_flow`
- `tests/test_mcp.py::test_mcp_change_create_is_metadata_only_for_accepted_proposal`

Extraction notes:

- Extract Work planning separately from Work branch operations. Planning is
  metadata/spec-export driven; branch operations are Git side-effecting and
  higher risk.
- Preserve Work lifecycle state names and manifest layout. Existing CLI and
  tests depend on `planned`, `branched`, `submitted`, `review_requested`,
  `published`, `merge_conflict`, `accepted`, `finalized`, `cleaned`, and
  `retired`.
- Preserve Work guards: clean worktree, expected branch, required status,
  non-manifest changes for submit, remote existence for publish/finalize/
  cleanup, and branch existence for accept/cleanup.
- Keep Change Set status transitions constrained by
  `CHANGE_STATUS_TRANSITIONS`.
- Keep `git-policy.yml` metadata-only behavior separate from managed Work Git
  operations. Change Sets describe policy; Work performs implementation
  handoff.
- Keep choices and conflicts governance-adjacent but not identical. Conflicts
  record proposal relationships; choices model unresolved options and blockers.
- Keep choice discovery advisory. It must not create, decide, block, or unblock
  choices.
- Keep intake apply intentionally narrow. It currently supports contribution
  addition and choice creation; governance-only or preview-only actions must not
  be executed automatically.
- Preserve next-action precedence: active choice blockers, curated project
  actions, then generated fallbacks, followed by dedupe on kind/target.
- Next actions are advisory planning aids, not governance decisions.

### Software Spec And Project Definition Export

Covered by T014.

Current behavior:

- generates a deterministic P2P-native `software-spec` bundle from a Change Set
  under `.p2p/outputs/software-spec/{CHANGE-ID}`;
- derives the generated spec from accepted proposal details, Change Set
  frontmatter, `change.md`, `tasks.yml`, and provenance references;
- supports status, show, prompt generation, and import for refined
  `software-spec` artifacts;
- exports the generated spec into target-specific project definition outputs
  under `.p2p/outputs/spec-export/{CHANGE-ID}/{target}`;
- supports `generic`, `openspec`, and `speckit` targets;
- builds a generic project definition from P2P project metadata, accepted
  proposals, draft proposals, governance text, rubrics, assessment, maturity,
  and generated software-spec artifacts;
- validates export presence and, for `generic`, validates required project
  definition sections plus source traceability.

Candidate target areas:

- `p2p_engine.services.software_specs`
- `p2p_engine.services.project_definition`
- `p2p_engine.services.spec_exports`
- `p2p_engine.renderers.software_spec`
- `p2p_engine.renderers.project_definition`
- `p2p_engine.renderers.spec_export`
- `p2p_engine.adapters.filesystem`
- `p2p_engine.validators.spec_export`

`software-spec` generation, generic project definition synthesis, and
target-specific export rendering should be separate modules. They are currently
coupled because `P2PWorkspace` owns file paths, Change Set lookup, project state
lookup, and all markdown rendering helpers. The facade can keep the existing
method names, but extraction should avoid making export targets responsible for
reading raw `.p2p` state directly.

The current implementation still stores outputs under `.p2p/outputs/...`. That
is existing behavior, not the desired long-term product boundary discussed in
the domain-aware visible export feature. This inventory should preserve current
tests during refactoring while leaving room for the later feature to change
output location and target applicability rules.

| Current method/helper | Line | Current responsibility | Candidate target area | Facade behavior |
| --- | ---: | --- | --- | --- |
| `refresh_software_spec` | 3964 | Generate normalized spec files from one Change Set | `software_specs` service | Keep method; delegate after extraction. |
| `software_spec_statuses` | 4022 | List generated spec bundles and completeness | `software_specs` service | Keep method; delegate after extraction. |
| `show_software_spec` | 4047 | Read generated spec `index.md` | `software_specs` service | Keep method; delegate after extraction. |
| `create_software_spec_prompt` | 4053 | Refresh spec and create refinement prompt | `software_specs` service plus prompt renderer | Keep method; delegate after extraction. |
| `import_software_spec` | 4069 | Validate and copy refined spec artifacts | `software_specs` service plus validator | Keep method; delegate after extraction. |
| `export_software_spec` | 4090 | Validate generated spec and write target export files | `spec_exports` service | Keep method; delegate after extraction. |
| `software_spec_export_statuses` | 4128 | List export bundles and completeness by target | `spec_exports` service | Keep method; delegate after extraction. |
| `show_software_spec_export` | 4158 | Read primary export document for target | `spec_exports` service | Keep method; delegate after extraction. |
| `validate_software_spec_export` | 4166 | Validate target files and generic required sections | `spec_export` validator | Keep method; delegate after extraction. |
| `_project_definition` | 4197 | Assemble definition context from project state, proposals, governance, rubrics, assessment, maturity, and spec files | `project_definition` service | Move behind export service. |
| `_software_spec_required_files` | 8854 | Define required normalized spec artifact names | `software_specs` constants | Move with spec service. |
| `_software_spec_export_targets` | 8866 | Define supported export targets | `spec_exports` constants | Move with export service. |
| `_software_spec_export_files` | 8870 | Dispatch target-specific export file rendering | `spec_exports` service/renderer dispatcher | Move behind export service. |
| `_software_spec_export_artifacts` | 8897 | List expected artifact names by target | `spec_exports` constants | Move with export service. |
| `_software_spec_export_required_files` | 8916 | List required export files by target | `spec_export` validator | Move with validator. |
| `_software_spec_export_show_file` | 8935 | Select primary show file by target | `spec_exports` constants | Move with export service. |
| `_project_definition_required_sections` | 8945 | Define generic project definition validation sections | `spec_export` validator | Move with validator. |
| `_speckit_feature_dir` | 8972 | Legacy helper for folder-shaped Spec Kit exports | `spec_exports` legacy/compat helper | Keep isolated or remove in later feature if unused. |
| `_definition_value` | 8984 | Normalize definition values for renderers | `project_definition` renderer helper | Move with renderer. |
| `_definition_spec` | 8994 | Read a generated spec artifact from definition context | `project_definition` renderer helper | Move with renderer. |
| `_definition_accepted` | 9001 | Normalize accepted proposal list for renderers | `project_definition` renderer helper | Move with renderer. |
| `_definition_drafts` | 9006 | Normalize draft proposal list for renderers | `project_definition` renderer helper | Move with renderer. |
| `_accepted_bullets` | 9011 | Render accepted proposal fields as markdown bullets | `project_definition` renderer helper | Move with renderer. |
| `_proposal_sources` | 9024 | Render source traceability from accepted proposals | `project_definition` renderer helper | Move with renderer. |
| `_pending_proposals` | 9036 | Render draft proposals as pending context | `project_definition` renderer helper | Move with renderer. |
| `_domain_sections` | 9041 | Render domain-specific project definition extension | `project_definition` renderer | Move with renderer; keep domain branching explicit. |
| `_project_definition_markdown` | 9084 | Render canonical generic `project.md` | `project_definition` renderer | Move with renderer. |
| `_generic_propose_markdown` | 9161 | Render generic initialization prompt | `spec_export` renderer | Move with generic export renderer. |
| `_openspec_propose_markdown` | 9173 | Render OpenSpec proposal input | `spec_export` renderer | Move with OpenSpec renderer. |
| `_speckit_constitution_markdown` | 9196 | Render Spec Kit constitution prompt | `spec_export` renderer | Move with Spec Kit renderer. |
| `_speckit_specify_markdown` | 9213 | Render Spec Kit specify prompt | `spec_export` renderer | Move with Spec Kit renderer. |
| `_speckit_plan_prompt_markdown` | 9231 | Render Spec Kit plan prompt | `spec_export` renderer | Move with Spec Kit renderer. |
| `_openspec_export_index` | 9271 | Legacy OpenSpec folder-shaped export index helper | `spec_exports` legacy/compat helper | Keep isolated or remove in later feature if unused. |
| `_openspec_spec_markdown` | 9290 | Legacy OpenSpec folder-shaped spec helper | `spec_exports` legacy/compat helper | Keep isolated or remove in later feature if unused. |
| `_speckit_export_index` | 9304 | Legacy Spec Kit folder-shaped export index helper | `spec_exports` legacy/compat helper | Keep isolated or remove in later feature if unused. |
| `_speckit_spec_markdown` | 9328 | Legacy Spec Kit folder-shaped spec helper | `spec_exports` legacy/compat helper | Keep isolated or remove in later feature if unused. |
| `_speckit_plan_markdown` | 9349 | Legacy Spec Kit folder-shaped plan helper | `spec_exports` legacy/compat helper | Keep isolated or remove in later feature if unused. |
| `_speckit_research_markdown` | 9386 | Legacy Spec Kit folder-shaped research helper | `spec_exports` legacy/compat helper | Keep isolated or remove in later feature if unused. |
| `_speckit_data_model_markdown` | 9403 | Legacy Spec Kit folder-shaped data model helper | `spec_exports` legacy/compat helper | Keep isolated or remove in later feature if unused. |
| `_speckit_quickstart_markdown` | 9413 | Legacy Spec Kit folder-shaped quickstart helper | `spec_exports` legacy/compat helper | Keep isolated or remove in later feature if unused. |
| `_speckit_tasks_markdown` | 9430 | Legacy Spec Kit folder-shaped tasks helper | `spec_exports` legacy/compat helper | Keep isolated or remove in later feature if unused. |
| `_speckit_contracts_readme` | 9447 | Legacy Spec Kit folder-shaped contracts helper | `spec_exports` legacy/compat helper | Keep isolated or remove in later feature if unused. |
| `_software_spec_index_markdown` | 9467 | Render normalized spec index | `software_spec` renderer | Move with spec renderer. |
| `_software_spec_requirements_markdown` | 9491 | Render normalized requirements from accepted proposals | `software_spec` renderer | Move with spec renderer. |
| `_software_spec_design_markdown` | 9526 | Render normalized design from Change Set frontmatter and deliverables | `software_spec` renderer | Move with spec renderer. |
| `_software_spec_commands` | 9540 | Derive command metadata from Change Set tasks | `software_spec` renderer/model mapper | Move with spec service. |
| `_software_spec_entities` | 9557 | Derive entity metadata from targets and accepted proposals | `software_spec` renderer/model mapper | Move with spec service. |
| `_software_spec_acceptance_markdown` | 9578 | Render acceptance criteria and verification task list | `software_spec` renderer | Move with spec renderer. |
| `_software_spec_refine_prompt` | 9598 | Render software-spec refinement prompt | prompt renderer | Move with prompt renderer. |

Related CLI surfaces:

- `spec refresh`
- `spec status`
- `spec show`
- `spec prompt`
- `spec import`
- `spec export`
- `spec export-status`
- `spec export-show`
- `spec export-validate`
- `work plan` depends on a validated spec export but belongs to T013.

Related MCP surfaces:

- `p2p_spec_status`
- `p2p_spec_show`
- `p2p_spec_export_status`
- `p2p_spec_export_show`
- `p2p_spec_refresh`
- `p2p_spec_export`
- `p2p_spec_export_validate`
- `p2p_work_plan` depends on a validated spec export but belongs to T013.

Existing compatibility tests:

- `tests/test_cli.py::test_cli_software_spec_refresh_prompt_import_status_and_show`
- `tests/test_cli.py::test_cli_change_create_status_and_policy`
- `tests/test_cli.py::test_cli_change_lifecycle_show_and_tasks`
- `tests/test_cli.py::test_cli_work_plan_list_and_show`
- `tests/test_mcp.py::test_mcp_project_definition_maturity`
- `tests/test_mcp.py::test_mcp_write_safe_spec_export_and_work_flow`

Extraction notes:

- Extract normalized `software-spec` generation before target-specific export
  rendering. Export depends on the normalized spec artifact set.
- Keep import validation strict: all required files must exist, and YAML files
  must expose the expected top-level keys.
- Keep `generic` export validation stricter than target file presence: it must
  verify required project definition sections and source traceability.
- Keep project definition synthesis separate from markdown rendering. Synthesis
  reads project state and accepted/draft proposal summaries; rendering should
  consume a ready definition object.
- Treat the current `generic`, `openspec`, and `speckit` renderers as
  target-specific document renderers, not as implementation task generators.
- Isolate legacy folder-shaped OpenSpec/Spec Kit helpers. They are present in
  the source but no longer appear to be used by `_software_spec_export_files`;
  future cleanup should prove that with tests before removal.
- Do not let Work planning own export validation. Work should call the public
  validation/export service contract and then create its own manifest.

## Compatibility Test Map

Covered by T021-T026.

### CLI Permissions And Consent Tests

Covered by T021.

| Test | Covers | Boundary protected | Extraction risk covered |
| --- | --- | --- | --- |
| `tests/test_cli.py::test_cli_init_owner_populates_permissions_policy` | Project initialization creates owner/admin permission policy | `services.permissions`, project init integration | Prevents default policy/owner actor drift. |
| `tests/test_cli.py::test_cli_permissions_actor_and_consent_receipts` | Actor add/update, consent grant/show/status/revoke lifecycle | `services.permissions`, `services.consent` | Protects policy writes, receipt creation, status list, and revoke semantics. |
| `tests/test_cli.py::test_cli_consent_grant_requires_owner_approver` | Granted consent requires an owner approver | `services.consent`, `services.permissions` | Prevents non-owner approval from authorizing privileged work. |
| `tests/test_cli.py::test_cli_validate_reports_invalid_permissions_policy` | Workspace validation reports malformed permission policy | `services.permissions`, `services.validation` | Protects policy schema validation and CLI diagnostics. |

Coverage notes:

- CLI coverage is strong for the local permission policy and basic consent
  receipt lifecycle.
- CLI does not cover permission-gated operation execution because that behavior
  is exposed through MCP write-safe/permission-gated tools.
- Service extraction should keep these CLI tests unchanged; any new
  service-level tests should supplement, not replace, the CLI compatibility
  tests.

### MCP Permissions And Consent Tests

Covered by T022.

| Test | Covers | Boundary protected | Extraction risk covered |
| --- | --- | --- | --- |
| `tests/test_mcp.py::test_mcp_remote_configure_and_consent_request_are_write_safe` | Remote configure and consent request are write-safe; requested consent is not authorization | `services.consent`, MCP registry | Prevents consent request from becoming execution approval. |
| `tests/test_mcp.py::test_mcp_requested_consent_does_not_authorize_publish` | Requested receipt fails for proposal publish | `services.consent`, `mcp.consent_audit` | Protects granted-only validation. |
| `tests/test_mcp.py::test_mcp_draft_proposal_decision_requires_granted_consent` | Draft proposal reject requires granted consent and consumes it | `services.consent`, proposal governance MCP tools | Protects decision gating and consume semantics. |
| `tests/test_mcp.py::test_mcp_draft_proposal_accept_and_defer_consume_matching_consent` | Draft accept/defer consume matching consent | `services.consent`, proposal governance MCP tools | Protects operation/target matching across decision outcomes. |
| `tests/test_mcp.py::test_mcp_proposal_publish_requires_and_consumes_consent` | Publish requires consent, consumes it, and records result | `services.consent`, `proposal_branches`, `mcp.consent_audit` | Protects publish gating and receipt result payload. |
| `tests/test_mcp.py::test_mcp_proposal_publish_rejects_actor_mismatch_without_consuming_consent` | Actor mismatch fails without consuming receipt | `services.consent` | Protects mismatch failure from burning valid consent. |
| `tests/test_mcp.py::test_mcp_sync_push_requires_and_consumes_consent` | Sync push requires and consumes consent | `services.consent`, `services.sync`, `mcp.consent_audit` | Protects remote side-effect gating. |
| `tests/test_mcp.py::test_mcp_sync_pull_requires_and_consumes_consent` | Sync pull requires and consumes consent | `services.consent`, `services.sync`, `mcp.consent_audit` | Protects pull gating and receipt lifecycle. |
| `tests/test_mcp.py::test_mcp_proposal_request_review_requires_and_consumes_consent` | Proposal review handoff requires consent | `services.consent`, `proposal_branches` | Protects review-request gating. |
| `tests/test_mcp.py::test_mcp_proposal_merge_requires_and_consumes_consent` | Proposal merge requires consent and writes audit commit | `services.consent`, `proposal_branches`, `mcp.consent_audit` | Protects merge gating and audit commit message behavior. |
| `tests/test_mcp.py::test_mcp_proposal_finalize_requires_and_consumes_consent` | Finalize requires consent, pushes base, and writes audit commit | `services.consent`, `proposal_branches`, `sync`, `mcp.consent_audit` | Protects finalize gating, push, and receipt result. |
| `tests/test_mcp.py::test_mcp_proposal_reject_and_cleanup_require_consent` | Branch reject and cleanup require consent | `services.consent`, `proposal_branches`, `mcp.consent_audit` | Protects destructive branch lifecycle gating. |
| `tests/test_mcp.py::test_mcp_permission_and_consent_read_tools` | Permission/consent read tools expose current state | `services.permissions`, `services.consent`, MCP registry | Protects read-only MCP surface and JSON serialization. |

Coverage notes:

- MCP coverage is the primary safety net for permission-gated side effects.
- Consent-audit behavior is covered through end-to-end MCP tests, not focused
  unit tests. That is acceptable before service extraction, but a future MCP
  registry extraction should add smaller audit-helper tests.
- Actor mismatch, requested-vs-granted status, operation matching, target
  matching, consumption, and audit commits must remain unchanged.

### CLI Proposal, Readiness, Prompt, And Governance Tests

Covered by T023.

| Test | Covers | Boundary protected | Extraction risk covered |
| --- | --- | --- | --- |
| `tests/test_cli.py::test_cli_init_status_create_and_prompt_flow` | Basic init, status, proposal create, and prompt flow | `services.proposals`, prompt services | Protects first-user proposal/prompt path. |
| `tests/test_cli.py::test_cli_validate_reports_duplicate_proposal_ids_as_error` | Duplicate proposal id validation | `services.proposals`, `services.validation` | Protects duplicate-id detection. |
| `tests/test_cli.py::test_cli_proposal_show_reports_ambiguous_duplicate_id_guidance` | Ambiguous proposal show diagnostic | `services.proposals` | Protects clean user-facing error guidance. |
| `tests/test_cli.py::test_cli_import_exploration_file_and_record_decision` | Exploration import and decision recording | proposal import services, `proposal_governance` | Protects fixed import paths and decision writes. |
| `tests/test_cli.py::test_cli_proposal_readiness_status_refresh_and_explain` | Readiness status/refresh/explain | `services.readiness` | Protects advisory score/explanation behavior. |
| `tests/test_cli.py::test_cli_lists_proposal_contributions` | Contribution add/list behavior | `services.proposals`, contributions boundary | Protects contribution YAML shape and listing. |
| `tests/test_cli.py::test_cli_proposal_accept_can_record_readiness_override` | Proposal accept with readiness override | `proposal_governance`, `services.readiness` | Protects override metadata and owner decision semantics. |
| `tests/test_cli.py::test_cli_proposal_decision_shortcuts` | Accept/reject/defer shortcuts | `proposal_governance` | Protects proposal status transitions. |
| `tests/test_cli.py::test_cli_proposal_list_show_and_choice_registry_output` | Proposal list/show and choice registry display | `services.proposals`, choices/registries | Protects proposal display plus related choice context. |
| `tests/test_cli.py::test_cli_missing_proposal_returns_clean_error` | Missing proposal diagnostics | `services.proposals` | Protects user-facing missing-id errors. |
| `tests/test_cli.py::test_cli_prompt_only_import_workflow_to_tasks` | Prompt/import pipeline through tasks | prompt/import services | Protects prompt-only workflow and fixed artifact imports. |
| `tests/test_cli.py::test_cli_tasks_import_rejects_invalid_yaml_shape` | Invalid tasks YAML import rejection | import validators | Protects YAML shape validation. |
| `tests/test_cli.py::test_cli_governance_swot_vote_and_precedent_flow` | SWOT, vote, precedent governance flow | prompt services, `proposal_governance` | Protects governance support artifacts. |
| `tests/test_cli.py::test_cli_impact_import_and_conflict_memory` | Impact import and conflict memory | proposal imports, conflicts | Protects impact YAML import and conflict recording. |
| `tests/test_cli.py::test_cli_intake_prompt_import_and_status` | Intake prompt/import/status | intake service | Protects intake artifact layout and status. |
| `tests/test_cli.py::test_cli_project_brief_prompt_import_and_show` | Project brief prompt/import/show | project brief/project state services | Protects operational brief context path and display. |
| `tests/test_cli.py::test_cli_next_falls_back_to_draft_proposal_review` | Next-action fallback to draft proposal review | next actions, proposals | Protects generated advisory next action behavior. |
| `tests/test_cli.py::test_cli_next_falls_back_to_improve_low_readiness_draft` | Next-action fallback for low readiness | next actions, readiness | Protects readiness-to-next-action integration. |

Coverage notes:

- Proposal branch lifecycle tests are intentionally mapped in T025 because they
  protect Git/sync behavior more than proposal document behavior.
- Software-spec prompt/import/export is mapped in T024 because it is part of
  generated project/spec output.
- T023 coverage is sufficient for proposal/readiness extraction only if
  proposal branch methods remain outside the first proposal service extraction.

### Project State, Registry, Spec/Export, Change Set, Work, Choice, And Next Tests

Covered by T024.

| Test | Covers | Boundary protected | Extraction risk covered |
| --- | --- | --- | --- |
| `tests/test_cli.py::test_cli_project_refresh_status_and_show` | Project state refresh/status/show | `services.project_state` | Protects generated project file layout and show behavior. |
| `tests/test_cli.py::test_cli_registry_refresh_status_and_show` | Registry refresh/status/show | `services.registries` | Protects registry generation and freshness/status output. |
| `tests/test_cli.py::test_cli_registry_refresh_rejects_duplicate_proposal_ids` | Registry rejects duplicate proposal ids | `services.registries`, `services.validation` | Protects duplicate-id validation before indexing. |
| `tests/test_cli.py::test_cli_registry_includes_choice_artifacts` | Choice artifacts appear in registries | `services.registries`, `services.choices` | Protects cross-domain registry records. |
| `tests/test_cli.py::test_cli_software_spec_refresh_prompt_import_status_and_show` | Software spec refresh/prompt/import/export/status/show/validate | `software_specs`, `project_definition`, `spec_exports` | Protects normalized spec artifacts and target exports. |
| `tests/test_cli.py::test_cli_change_create_status_and_policy` | Change Set create/status/policy | `services.change_sets` | Protects metadata-only Change Set creation and policy output. |
| `tests/test_cli.py::test_cli_change_lifecycle_show_and_tasks` | Change Set show/status transitions/tasks | `services.change_sets` | Protects lifecycle transitions and task views. |
| `tests/test_cli.py::test_cli_work_plan_list_and_show` | Work plan/list/show from validated export | `work_plans`, `spec_exports` | Protects Work manifest creation from export validation. |
| `tests/test_cli.py::test_cli_work_retire_marks_planned_work_retired` | Retire planned Work | `work_plans` | Protects metadata-only Work retirement. |
| `tests/test_cli.py::test_cli_work_retire_requires_planned_status` | Retire rejects non-planned Work | `work_plans` | Protects Work status guard. |
| `tests/test_cli.py::test_cli_choice_create_list_and_decide` | Choice lifecycle | `services.choices` | Protects choice options, decision, and status. |
| `tests/test_cli.py::test_cli_choice_discovery_blocking_and_next_integration` | Choice discovery, blockers, next integration | `choices`, `next_actions` | Protects advisory discovery and blocker next actions. |
| `tests/test_cli.py::test_cli_intake_apply_plan_show_and_run` | Intake apply plan/show/run | `intake_apply` | Protects controlled apply actions. |
| `tests/test_cli.py::test_cli_next_falls_back_without_imported_next_actions` | Generated next fallback without curated actions | `next_actions` | Protects fallback generation. |
| `tests/test_cli.py::test_cli_next_manages_curated_lifecycle_and_log` | Curated next add/complete/log | `next_actions` | Protects curated lifecycle and audit log. |
| `tests/test_cli.py::test_cli_next_retire_and_refresh` | Next retire/refresh | `next_actions` | Protects close/normalize behavior. |
| `tests/test_cli.py::test_cli_next_shows_generated_actions_when_curated_actions_exist` | Curated plus generated visibility | `next_actions` | Protects generated action visibility. |
| `tests/test_cli.py::test_cli_next_deduplicates_curated_and_generated_actions` | Dedupe behavior | `next_actions` | Protects kind/target dedupe semantics. |
| `tests/test_mcp.py::test_mcp_registry_refresh_tool` | MCP registry refresh | `services.registries`, MCP registry | Protects write-safe registry refresh tool. |
| `tests/test_mcp.py::test_mcp_project_definition_maturity` | Project definition maturity | project rubrics, project definition | Protects maturity evidence and payload shape. |
| `tests/test_mcp.py::test_mcp_call_tool_reads_project_state` | MCP project state read | `services.project_state`, MCP registry | Protects read tool serialization. |
| `tests/test_mcp.py::test_mcp_change_project_registry_and_remote_read_tools` | Change/project/registry/remote read tools | change/project/registry/remote services | Protects MCP read-only status/show surfaces. |
| `tests/test_mcp.py::test_mcp_write_safe_spec_export_and_work_flow` | Spec export and Work plan flow | `software_specs`, `spec_exports`, `work_plans` | Protects write-safe export and Work handoff. |
| `tests/test_mcp.py::test_mcp_change_create_is_metadata_only_for_accepted_proposal` | Change create metadata-only semantics | `services.change_sets` | Protects MCP Change Set creation boundary. |
| `tests/test_mcp.py::test_mcp_project_refresh_writes_generated_project_files` | MCP project refresh writes generated files | `services.project_state` | Protects generated project state side effect. |
| `tests/test_mcp.py::test_mcp_managed_next_action_lifecycle` | MCP next add/complete lifecycle | `next_actions` | Protects managed next-action JSON payloads. |
| `tests/test_mcp.py::test_mcp_next_retire_and_refresh` | MCP next retire/refresh | `next_actions` | Protects MCP parity with CLI lifecycle. |
| `tests/test_mcp.py::test_mcp_choice_discover_is_advisory` | Choice discovery is advisory | `choices` | Protects no-write discovery semantics. |
| `tests/test_mcp.py::test_mcp_conflict_status_reads_without_recording` | Conflict status read-only behavior | `conflicts` | Protects read-only MCP conflict status. |

Coverage notes:

- Work Git execution tests are mapped in T025; this section covers Work plan
  and metadata-only Work status/retire behavior.
- Spec export tests currently protect existing `.p2p/outputs/...` behavior.
  Later visible-output/domain-aware product changes need their own tests.
- Choice discovery and conflict status are explicitly advisory/read-only in MCP.

### Git, Sync, Proposal Branch, And Work Branch Tests

Covered by T025.

| Test | Covers | Boundary protected | Extraction risk covered |
| --- | --- | --- | --- |
| `tests/test_cli.py::test_cli_init_cloud_configures_remote_profile` | Init remote profile | `remote_profile` | Protects remote project defaults. |
| `tests/test_cli.py::test_cli_init_rejects_ambiguous_repository_remote_alias` | Ambiguous remote alias rejection | `remote_profile` | Protects remote alias validation. |
| `tests/test_cli.py::test_cli_project_remote_configure_and_show` | Remote configure/show | `remote_profile` | Protects persisted remote profile shape. |
| `tests/test_cli.py::test_cli_sync_status_reports_local_project_without_remote` | Local sync status | `sync`, Git adapter | Protects local/no-remote readiness reporting. |
| `tests/test_cli.py::test_cli_sync_status_detects_git_origin_when_p2p_profile_is_local` | Git origin detection with local P2P profile | `sync`, Git adapter | Protects mixed local/Git remote diagnostics. |
| `tests/test_cli.py::test_cli_sync_status_detects_remote_profile_url_mismatch` | Remote URL mismatch | `sync`, `remote_profile` | Protects mismatch warning behavior. |
| `tests/test_cli.py::test_cli_sync_push_fetch_and_pull_wrap_git_remote` | Fetch/push/pull wrappers | `sync`, Git adapter | Protects Git remote side effects. |
| `tests/test_cli.py::test_cli_sync_pull_requires_clean_worktree` | Pull clean-worktree guard | `sync` | Protects side-effect guard. |
| `tests/test_cli.py::test_cli_proposal_branch_creates_managed_branch_metadata` | Proposal branch creation and metadata | `proposal_branches`, Git adapter | Protects branch naming and metadata layout. |
| `tests/test_cli.py::test_cli_proposal_publish_request_review_and_scan` | Publish, review, scan | `proposal_branches`, `sync` | Protects remote publish and scan registry. |
| `tests/test_cli.py::test_cli_proposal_publish_auto_renumbers_on_remote_id_collision` | Auto-renumber on remote branch collision | `proposal_branches` | Protects high-risk id/branch rewrite behavior. |
| `tests/test_cli.py::test_cli_proposal_publish_detects_collision_from_remote_main` | Collision from remote main tree | `proposal_branches`, Git adapter | Protects remote tree inspection. |
| `tests/test_cli.py::test_cli_proposal_retire_branch_records_reason` | Branch retire reason | `proposal_branches` | Protects retired metadata. |
| `tests/test_cli.py::test_cli_proposal_merge_merges_reviewed_branch_into_base` | Merge reviewed branch | `proposal_branches`, Git adapter | Protects merge operation and base branch state. |
| `tests/test_cli.py::test_cli_proposal_accept_branch_records_governance_decision` | Branch accept decision | `proposal_branches` | Protects owner branch decision metadata. |
| `tests/test_cli.py::test_cli_proposal_finalize_pushes_merged_base_branch` | Finalize pushes base | `proposal_branches`, `sync` | Protects final push behavior. |
| `tests/test_cli.py::test_cli_proposal_cleanup_deletes_local_and_remote_branch` | Branch cleanup | `proposal_branches`, Git adapter | Protects local/remote delete behavior. |
| `tests/test_cli.py::test_cli_work_branch_creates_managed_branch` | Work branch creation | `work_branches`, Git adapter | Protects Work branch naming and manifest update. |
| `tests/test_cli.py::test_cli_work_branch_requires_clean_worktree` | Work branch clean-worktree guard | `work_branches` | Protects dirty worktree rejection. |
| `tests/test_cli.py::test_cli_work_submit_creates_local_commit` | Work submit commit | `work_branches`, Git adapter | Protects submit side effect. |
| `tests/test_cli.py::test_cli_work_submit_requires_non_manifest_changes` | Submit rejects manifest-only changes | `work_branches` | Protects implementation-change guard. |
| `tests/test_cli.py::test_cli_work_review_requests_local_review` | Local Work review request | `work_branches` | Protects review metadata. |
| `tests/test_cli.py::test_cli_work_review_requires_submitted_clean_branch` | Work review status/branch guards | `work_branches` | Protects review preconditions. |
| `tests/test_cli.py::test_cli_work_publish_pushes_reviewed_branch` | Work publish push | `work_branches`, `sync` | Protects remote publish. |
| `tests/test_cli.py::test_cli_work_publish_requires_review_and_remote` | Work publish guards | `work_branches`, `remote_profile` | Protects status and remote requirements. |
| `tests/test_cli.py::test_cli_work_request_review_records_provider_handoff` | External Work review metadata | `work_branches` | Protects provider handoff shape. |
| `tests/test_cli.py::test_cli_work_accept_merges_published_branch` | Work accept merge | `work_branches`, Git adapter | Protects Work merge into base. |
| `tests/test_cli.py::test_cli_work_accept_requires_published_base_branch` | Work accept status/base branch guards | `work_branches` | Protects accept preconditions. |
| `tests/test_cli.py::test_cli_work_finalize_requires_accepted_and_remote` | Work finalize guards | `work_branches`, `sync` | Protects accepted/remote preconditions. |
| `tests/test_cli.py::test_cli_work_cleanup_requires_finalized_branch` | Work cleanup guards | `work_branches` | Protects cleanup preconditions. |
| `tests/test_cli.py::test_cli_work_accept_conflict_continue_and_abort` | Work accept conflict continue/abort | `work_branches`, Git adapter | Protects merge-conflict lifecycle and manifest restoration. |
| `tests/test_cli.py::test_cli_work_scan_reads_local_branch_without_checkout` | Work branch scan without checkout | `work_branches`, Git adapter | Protects ref-based scan behavior. |
| `tests/test_mcp.py::test_mcp_safe_managed_sync_and_proposal_branch_tools` | Safe MCP sync and proposal branch read/write-safe tools | `sync`, `proposal_branches`, MCP registry | Protects MCP tool payloads and safety flags. |
| `tests/test_mcp.py::test_mcp_proposal_draft_commit_then_branch_from_explicit_base` | Draft commit then branch from explicit base | `proposal_branches`, Git adapter | Protects explicit base branch behavior. |
| `tests/test_mcp.py::test_mcp_proposal_branch_refuses_proposal_branch_base_without_opt_in` | Refuse branch chaining by default | `proposal_branches` | Protects unsafe branch-base guard. |
| MCP consent-consuming branch/sync tests from T022 | Publish, review, merge, finalize, cleanup, sync pull/push with consent | `sync`, `proposal_branches`, `mcp.consent_audit` | Protects permission-gated Git side effects. |

Coverage notes:

- Git/sync coverage is end-to-end and therefore valuable for compatibility, but
  service extraction should add smaller adapter/service tests only after the
  boundaries exist.
- Proposal branch and Work branch lifecycles should not be extracted in the
  same change as the low-risk `remote_profile` service.
- Auto-renumber, merge conflict continue/abort, cleanup, and consent audit are
  the highest-risk behaviors in this group.

### Missing Or Recommended Test Gaps

Covered by T026.

| Responsibility group | Current coverage level | Missing/recommended tests before extraction |
| --- | --- | --- |
| `services.permissions` | Good CLI/MCP compatibility coverage | Add service-level tests for `_identity_slug`, role normalization, actor kind normalization, and default owner payload if service extraction introduces public helpers. |
| `services.consent` | Strong MCP end-to-end coverage plus CLI lifecycle tests | Add focused tests for expiry mutation to `expired`, `used_with_error`, revoke-after-consume rejection, and sequential id allocation under existing receipts. |
| `mcp.consent_audit` | Covered indirectly by MCP side-effect tests | Add helper-level tests after MCP audit module exists: successful audit commit, head-change error marking, push failure behavior, and no consume-before-operation result. |
| `services.proposals` | Good CLI/MCP document lifecycle coverage | Add service-level tests for proposal markdown parsing, section replacement, duplicate id diagnostics, and contribution YAML normalization once extracted. |
| `proposal_governance` | Good CLI/MCP decision coverage | Add focused tests that acceptance/rejection/defer do not run branch operations and that readiness override fields are preserved exactly. |
| `services.readiness` | Good CLI/MCP advisory coverage | Add focused tests for profile threshold math, quality caps, missing artifact classification, owner override effective status, and blocker integration. |
| Prompt/import services | Good CLI/MCP workflow coverage | Add focused validator tests for each imported YAML shape and fixed-path write map before moving import code. |
| `project_state` | Moderate CLI/MCP generated-output coverage | Add tests that draft proposals never appear as accepted truth, source traceability survives refresh, and project brief/next actions do not overwrite unrelated generated state. |
| `registries` | Moderate CLI/MCP registry coverage | Add focused tests for each registry type count/record schema: proposals, decisions, changes, choices, relations, artifacts, readiness, and scanned branches. |
| `software_specs` | Good CLI coverage for current behavior | Add tests for missing required artifact import failure per file, YAML top-level key failure per file, and non-software-domain behavior after the domain-aware export feature lands. |
| `project_definition` | Moderate export-driven coverage | Add focused tests that accepted proposals are included, draft proposals are only pending, governance/rubrics/maturity inputs are read correctly, and source traceability is mandatory. |
| `spec_exports` | Good current target coverage | Add tests for unsupported target errors, incomplete export status per target, legacy helper removal proof, and future visible root output path once product behavior changes. |
| `remote_profile` | Good CLI/MCP coverage | Add focused tests for provider validation, URL persistence, local/remote mode transitions, and review request metadata defaults. |
| Git adapter | Good end-to-end coverage, little direct coverage | Add adapter-level tests only if adapter behavior changes from current thin subprocess wrapper, especially failure-to-`None` semantics. |
| `sync` | Good CLI/MCP end-to-end coverage | Add service-level tests for remote URL mismatch, clean worktree guards, selected remote resolution, and branch mismatch before extraction. |
| `proposal_branches` | Strong but high-risk end-to-end coverage | Add focused tests for metadata transition matrix, auto-renumber file rewrite details, merge conflict abort restoration, remote collision from branch and base tree, and cleanup partial failures. |
| `work_plans` | Good metadata coverage | Add focused tests for manifest schema, next-action by Work status, and dependency on public export validation rather than private export paths. |
| `work_branches` | Strong but high-risk end-to-end coverage | Add focused tests for status transition matrix, manifest-only submit rejection, accept conflict rollback, cleanup partial failures, and scan registry schema. |
| CLI modularization | Broad CLI coverage | Add command-registration smoke tests only when `cli_commands/*` is introduced. |
| MCP registry modularization | Broad MCP coverage | Add schema registry tests for read-only/write-safe/permission-gated classifications before moving tool definitions. |

Phase 4 conclusion:

- The current compatibility suite is sufficient to start the first narrow
  extraction with `permissions` and `consent`, provided `P2PWorkspace` remains
  the facade.
- High-risk Git lifecycle services need additional focused tests before code
  movement, even though end-to-end CLI/MCP coverage is strong.
- CLI/MCP modularization should wait until service boundaries are extracted and
  backed by both compatibility and focused service tests.

## Extraction Order

Covered by T027-T028.

### Extraction Risk Criteria

Covered by T027.

Use these criteria to order future implementation features. Score each
candidate boundary from `1` to `5` in every dimension, where `1` is low risk
and `5` is high risk.

| Criterion | Score 1 | Score 3 | Score 5 |
| --- | --- | --- | --- |
| Owner-governance sensitivity | Advisory or read-only behavior | Records metadata affecting decisions | Accepts/rejects/merges/finalizes or changes owner-controlled outcomes |
| Storage sensitivity | Reads/writes one isolated generated file | Writes existing `.p2p` domain state | Rewrites ids, moves directories, or changes multi-file state |
| Git/network side effects | No Git or network operations | Reads Git refs/status only | Commits, merges, pushes, pulls, deletes branches, or handles conflicts |
| CLI/MCP exposure | Internal helper only | One CLI or MCP surface | Multiple CLI/MCP commands/tools or permission-gated MCP tools |
| Test coverage | Focused and compatibility tests exist | End-to-end compatibility tests exist only | Missing or weak coverage for key transitions |
| Coupling | Pure service with clear inputs | Depends on two or three domain services | Coordinates many domains or shared helpers |

Derived risk bands:

| Total score | Risk band | Extraction rule |
| ---: | --- | --- |
| 6-10 | Low | Can be an early extraction if facade delegation is preserved. |
| 11-16 | Medium | Extract after focused tests or after dependencies are stable. |
| 17-22 | High | Needs a dedicated feature, focused tests, and careful sequencing. |
| 23-30 | Critical | Do not extract until lower-risk dependencies are done and behavior is exhaustively mapped. |

Initial candidate scoring:

| Boundary | Governance | Storage | Git/network | CLI/MCP | Tests | Coupling | Total | Band |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `services.permissions` | 2 | 3 | 1 | 3 | 2 | 2 | 13 | Medium |
| `services.consent` | 4 | 3 | 1 | 5 | 2 | 3 | 18 | High |
| `mcp.consent_audit` | 5 | 3 | 5 | 5 | 3 | 4 | 25 | Critical |
| `services.remote_profile` | 1 | 3 | 1 | 3 | 2 | 2 | 12 | Medium |
| `services.software_specs` | 1 | 3 | 1 | 3 | 2 | 3 | 13 | Medium |
| `services.project_definition` | 1 | 1 | 1 | 2 | 3 | 4 | 12 | Medium |
| `services.proposals` | 3 | 3 | 1 | 4 | 2 | 3 | 16 | Medium |
| `services.readiness` | 2 | 3 | 1 | 3 | 2 | 4 | 15 | Medium |
| `services.project_state` | 2 | 3 | 1 | 3 | 3 | 5 | 17 | High |
| `services.registries` | 2 | 3 | 1 | 3 | 3 | 5 | 17 | High |
| `services.spec_exports` | 1 | 3 | 1 | 3 | 2 | 4 | 14 | Medium |
| `services.sync` | 2 | 1 | 5 | 5 | 2 | 4 | 19 | High |
| `services.proposal_branches` | 5 | 5 | 5 | 5 | 2 | 5 | 27 | Critical |
| `services.work_plans` | 2 | 3 | 1 | 3 | 2 | 3 | 14 | Medium |
| `services.work_branches` | 4 | 4 | 5 | 4 | 2 | 5 | 24 | Critical |
| `cli_commands.*` | 1 | 1 | 1 | 5 | 2 | 5 | 15 | Medium |
| `mcp.registry` | 3 | 1 | 1 | 5 | 2 | 5 | 17 | High |

Risk interpretation:

- `permissions` is the first practical extraction because its risk is medium,
  its storage is narrow, and it unlocks `consent`.
- `consent` is high-risk because of governance semantics and MCP exposure, but
  it has strong compatibility tests and a clear boundary.
- `remote_profile` is a good low-side-effect extraction after
  permissions/consent patterns are proven.
- `proposal_branches`, `work_branches`, and `mcp.consent_audit` are critical
  and should not be early extractions.

### Staged Extraction Order

Covered by T028.

This order assumes `P2PWorkspace` remains the compatibility facade throughout
the refactoring. Each stage should be implemented as one or more follow-up
local feature specs under `specs/features/*`; no stage should change CLI/MCP
names, storage paths, or governance semantics unless a separate proposal says
so.

| Stage | Candidate boundary | Why here | Required before start | Done when |
| ---: | --- | --- | --- | --- |
| 0 | Architecture contract and inventory | Establishes map, tests, and facade constraints | Current feature complete | Inventory, risk scoring, test map, facade contract exist. |
| 1 | `services.permissions` | Narrow storage, no Git, clear tests, unlocks consent | T021/T022 mapped | `P2PWorkspace` delegates permissions show/actor add and init default policy without CLI/MCP drift. |
| 2 | `services.consent` | Clear lifecycle, safety-critical, strong tests | Stage 1 complete; focused expiry/error tests added if needed | Consent grant/request/show/status/revoke/validate/consume/error delegate through facade. |
| 3 | `services.remote_profile` | Low side effects, simple project metadata, useful for later sync | Stages 1-2 complete | Remote configure/show and init remote defaults delegate through facade. |
| 4 | Pure renderers and validators | Mostly deterministic helpers; reduces monolith size without side effects | Shared helper ownership confirmed | Markdown/YAML renderers and validators move without changing output. |
| 5 | `services.software_specs` | Generated output only, good tests, no Git | Renderer/validator split ready | Spec refresh/status/show/prompt/import delegate through facade. |
| 6 | `services.project_definition` and `services.spec_exports` | Depends on software specs and renderers; needed for output cleanup later | Stage 5 complete | Generic/OpenSpec/Spec Kit exports delegate through facade with same paths and validation. |
| 7 | `services.proposals` document/contribution core | Core domain, no Git if branch lifecycle stays out | Duplicate-id and markdown parser tests added if needed | Proposal list/show/create/update/contribution delegate; branch methods unchanged. |
| 8 | `services.readiness` | Depends on proposal parsing and advisory artifacts | Stage 7 complete; focused scoring tests added if needed | Readiness show/refresh/explain and override metadata delegate through facade. |
| 9 | `proposal_governance` non-branch decisions | Owner-sensitive but no Git if branch decisions stay out | Stages 7-8 complete | Accept/reject/defer and decision shortcut behavior delegate with readiness override intact. |
| 10 | `work_plans` | Metadata-only Work behavior, depends on spec export validation | Stage 6 complete | Work plan/list/status/show/retire delegate; branch execution unchanged. |
| 11 | `project_state` and `registries` | Broad coupling; safer after domain summaries exist | Stages 7-10 complete | Project refresh/status/show and registry refresh/status/show delegate through stable summary APIs. |
| 12 | `sync` | Git side effects, but simpler than branch lifecycles | Stage 3 complete; focused guard tests added | Sync status/fetch/pull/push delegate with guards intact. |
| 13 | `proposal_branches` | Critical Git/governance lifecycle | Stages 7, 9, 12 complete; focused transition tests added | Proposal branch lifecycle delegates with branch state, collision, merge, finalize, cleanup unchanged. |
| 14 | `work_branches` | Critical Git lifecycle; can reuse patterns from proposal branches | Stages 10, 12, 13 complete; focused transition tests added | Work branch lifecycle delegates with conflict/cleanup semantics unchanged. |
| 15 | `mcp.consent_audit` | Critical because it combines consent, Git, and MCP | Stages 2, 12-14 complete; audit helper tests added | MCP permission-gated tools call audit helper with identical consume/error/commit behavior. |
| 16 | `mcp.registry` | Presentation/router split after services stabilize | Relevant services extracted; schema tests added | Tool definitions/handlers are modular with unchanged tool names and schemas. |
| 17 | `cli_commands.*` | Presentation split last to avoid moving coupled business logic | Relevant services extracted; command registration tests added | CLI command modules are thin and keep current command names/output. |

Explicit non-goals for this staged order:

- Do not move CLI/MCP presentation before service boundaries exist.
- Do not combine proposal branch and Work branch extraction in one feature.
- Do not change `.p2p` storage layout during refactoring.
- Do not move outputs from `.p2p/outputs` to visible root directories as part
  of refactoring; that belongs to the accepted domain-aware visible export
  product feature.
- Do not remove legacy OpenSpec/Spec Kit helpers until a focused cleanup proves
  they are unused and covered by tests.
 

## Facade Contract

Covered by T029-T031.

### `P2PWorkspace` Delegation Contract

Covered by T029.

Rules for all extracted services:

- Public `P2PWorkspace` method names, parameters, return dataclasses, returned
  dictionaries, and raised error messages remain compatibility contracts.
- CLI and MCP continue to call `P2PWorkspace` until a later explicit
  presentation refactor.
- Services may receive dependencies such as filesystem adapters, Git adapters,
  renderers, validators, and other services, but callers must not need to know
  those internals.
- Services must not import Typer, Rich, or MCP transport code.
- Renderers must not read `.p2p` state directly.
- Validators must not write files.

Initial delegation table:

| Facade methods | Target service | Must preserve |
| --- | --- | --- |
| `permissions_show`, `permissions_actor_add` | `services.permissions` | `PermissionPolicy`/actor payload shape, policy path, default owner/admin semantics, invalid policy errors. |
| `consent_grant`, `consent_request`, `consent_show`, `consent_statuses`, `consent_revoke`, `consent_validate`, `consent_consume`, `consent_mark_used_with_error` | `services.consent` | `ConsentReceipt` shape, `CONSENT-XXX` ids, requested/granted/consumed/expired/revoked/error semantics. |
| `remote_profile`, `configure_remote_profile` | `services.remote_profile` | `RemoteProfile` shape, project metadata layout, provider/mode validation. |
| `refresh_software_spec`, `software_spec_statuses`, `show_software_spec`, `create_software_spec_prompt`, `import_software_spec` | `services.software_specs` | Required artifact names, YAML keys, prompt path, current `.p2p/outputs/software-spec` location. |
| `export_software_spec`, `software_spec_export_statuses`, `show_software_spec_export`, `validate_software_spec_export` | `services.spec_exports` | Target names, output files, primary show file, generic section validation, current `.p2p/outputs/spec-export` location. |
| `proposal_summaries`, `show_proposal`, `create_proposal`, `create_proposal_with_details`, `update_proposal`, `add_contribution`, `list_contributions` | `services.proposals` | Proposal ids, directory naming, markdown sections, contribution YAML, missing/duplicate id errors. |
| proposal accept/reject/defer/decision methods | `proposal_governance` | Owner-controlled decision semantics, status writes, readiness override metadata. |
| readiness status/refresh/explain/profile helpers | `services.readiness` | Advisory status, scoring, gates, override fields, explanation payload. |
| `create_work_plan`, `work_statuses`, `work_summaries`, `show_work`, `retire_work` | `services.work_plans` | Work ids, manifest schema, target validation dependency, status names. |
| `sync_status`, `sync_fetch`, `sync_pull`, `sync_push` | `services.sync` | Sync status payload, clean worktree guards, remote URL mismatch behavior, Git side effects. |
| proposal branch lifecycle methods | `services.proposal_branches` | Branch names, `branch.yml`, lifecycle status names, collision/auto-renumber, merge/finalize/cleanup behavior. |
| Work branch lifecycle methods | `services.work_branches` | Work branch names, manifest transitions, submit guards, conflict continue/abort, finalize/cleanup behavior. |
| project refresh/status/show methods | `services.project_state` | Generated state paths, accepted-only truth, source traceability. |
| registry refresh/status/show methods | `services.registries` | Registry paths, freshness metadata, record counts, duplicate-id handling. |
| choice lifecycle methods | `services.choices` | Choice ids, option/decision payloads, blocker semantics, advisory discovery. |
| conflict methods | `services.conflicts` | Conflict record/status schema and read-only MCP status behavior. |
| next-action methods | `services.next_actions` | Curated/generated precedence, dedupe, lifecycle audit log, advisory semantics. |
| intake prompt/import/status/apply methods | `services.intake` and `services.intake_apply` | Intake ids, fixed artifact paths, controlled apply action whitelist. |

Delegation implementation expectations:

- A future extraction may instantiate services lazily inside `P2PWorkspace` or
  through a small internal service container.
- `P2PWorkspace.__init__` should remain the owner of root path bootstrap until
  a filesystem adapter boundary is implemented.
- Private helpers should move only when all current callers are in the same
  target boundary or a shared helper module has an explicit owner.
- During transition, private helper duplication is preferable to hidden
  cross-service imports that recreate the monolith.

### Temporary-Stay Methods And Helpers

Covered by T030.

These methods/helpers should remain in `P2PWorkspace` or in their current files
until later extractions because they coordinate multiple domains, have high
side effects, or lack focused service tests.

| Method/helper group | Stay reason | Revisit after |
| --- | --- | --- |
| `P2PWorkspace.__init__` and root/path bootstrap | Facade constructs the project root and `.p2p` paths used by all services | Filesystem adapter/service container design exists. |
| `init_project` | Coordinates project metadata, permissions, remote profile, rubrics, domains, directories, and agent files | Permissions, remote profile, rubrics, and agent integration services exist. |
| `_project_name`, `_repository_mode`, shared project metadata helpers | Used by many domains and not yet owned by one service | Project metadata boundary is explicit. |
| Markdown/frontmatter helpers used across proposals, Change Sets, specs, readiness, and prompts | Shared parser ownership is not yet isolated | Parser/helper module has focused tests. |
| `_slugify` and id/name helpers used by proposal, Change Set, Work, Spec Kit, and branches | Cross-domain naming behavior is sensitive | Domain-specific callers are separated and shared naming tests exist. |
| Validation orchestration | Reads many domains and generated files | Domain services expose stable summary/read APIs. |
| Project assessment and maturity computation | Broad evidence gathering across proposals, Change Sets, rubrics, choices, and generated project state | Project state, registries, readiness, and rubrics services exist. |
| Context packet generation | Pulls project state, next actions, readiness, proposals, choices, changes, work, and command suggestions | Read-only service APIs are stable. |
| Next-action fallback generation | Depends on choices, readiness, proposals, changes, work, registries, intake, and project state | Those services expose stable summaries. |
| `proposal_branches` lifecycle methods | Critical Git/governance side effects | Proposal core, governance, sync, consent, and focused branch tests exist. |
| `work_branches` lifecycle methods | Critical Git side effects and conflict handling | Work plan, sync, Git adapter, and focused Work branch tests exist. |
| `mcp/tools.py` permission-gated audit helpers | Combine MCP routing, consent, Git audit commits, and optional pushes | Consent, sync, branch services exist and audit helper tests are added. |
| CLI command functions in `cli.py` | Presentation should move after services, not before | Most target services are extracted. |
| MCP tool registry/handlers in `mcp/tools.py` | Tool schemas and permission classes should move after services and consent audit are stable | Services and audit helper exist; schema classification tests exist. |
| Legacy OpenSpec/Spec Kit folder-shaped helper functions | Potentially unused but should not be removed during broad refactor | Focused cleanup proves unused behavior and target export tests pass. |

Temporary-stay rule:

- If a helper has callers from more than one unmoved boundary, leave it in
  place or move it only to an explicit shared parser/validator/renderer module.
- If a method performs Git/network side effects, do not move it as part of a
  low-risk metadata extraction.
- If a method changes owner-controlled governance state, do not move it unless
  the corresponding service boundary and tests are dedicated to that behavior.

### Separate-Proposal Change Boundaries

Covered by T031.

The following behaviors are not implementation details. They cannot change as
part of modular refactoring unless the owner accepts a separate P2P proposal or
an explicit local feature spec derived from an accepted proposal.

| Behavior | Why it needs separate approval |
| --- | --- |
| CLI command names, arguments, option names, defaults, and exit semantics | Existing users and agents depend on the public CLI surface. |
| MCP tool names, schemas, read-only/write-safe/permission-gated classification, and result payloads | External agents and consent policy depend on stable MCP contracts. |
| `.p2p` storage paths and YAML/Markdown file schemas | Existing projects must remain readable and writable after upgrade. |
| Proposal, Change Set, Choice, Work, Consent, Intake, and Next Action id formats | Id formats are referenced by files, branches, registries, prompts, and users. |
| Governance semantics for accept/reject/defer/merge/finalize/cleanup | Owner-controlled actions must not change under a refactoring label. |
| Consent authorization semantics | Requested receipts must not authorize execution; actor/operation/target/expiry checks must remain intact. |
| MCP consent audit commit/push behavior | Auditability and permission-gated side effects are safety-critical. |
| Git branch names and lifecycle status names for proposal and Work branches | Remote branches, metadata, tests, and users rely on these names. |
| Auto-renumber behavior for proposal publish collisions | This rewrites ids/directories/branches and is product behavior, not internal structure. |
| Output location for spec exports | Moving from `.p2p/outputs` to visible root output is product behavior already tracked separately, not a refactoring side effect. |
| Domain applicability of generic/OpenSpec/Spec Kit exports | Non-software domain behavior must be governed by the domain-aware export feature. |
| Removal of legacy OpenSpec/Spec Kit helper behavior | Cleanup requires proof and an explicit compatibility decision. |
| Readiness thresholds, scoring, gates, override semantics, and advisory language | Acceptance guidance and owner override behavior depend on these semantics. |
| Project-state truth policy for accepted vs draft proposals | Treating drafts as truth would change governance meaning. |
| Validation strictness for imported YAML/spec artifacts | Relaxing or tightening validation changes user workflows. |

Refactoring-safe changes:

- Moving code behind services while preserving public behavior.
- Adding focused tests that document existing behavior.
- Adding internal adapters/renderers/validators with no output drift.
- Introducing internal service construction inside `P2PWorkspace`.

Refactoring-unsafe changes:

- Renaming commands, tools, ids, paths, or statuses.
- Changing file layouts or generated output locations.
- Changing who can approve, consume, or bypass consent.
- Changing Git side-effect order, branch names, merge behavior, or cleanup
  behavior.
- Turning advisory readiness/choice discovery/next actions into automatic
  governance decisions.

## Follow-Up Feature Seeds

Covered by T032-T034.

### Seed: Permissions And Consent Service Extraction

Covered by T032.

Proposed feature name:

- `p2pworkspace-permissions-consent-service-extraction`

Purpose:

- Extract permission policy and consent receipt lifecycle behavior from
  `P2PWorkspace` into dedicated internal services while preserving all CLI,
  MCP, storage, dataclass, and governance semantics.

Requirement outline:

- Preserve `P2PWorkspace` public methods for permissions and consent.
- Preserve `.p2p/project/permissions.yml` layout.
- Preserve `.p2p/consents/CONSENT-XXX/consent.yml` layout.
- Preserve owner/admin default policy generated during project init.
- Preserve actor id, role, actor kind, consent operation, and consent id
  normalization.
- Preserve granted/requested/revoked/expired/consumed/used-with-error receipt
  semantics.
- Preserve validation for operation, target, actor, status, expiry, and owner
  approver.
- Keep MCP consent audit helpers outside the core consent service unless a
  focused audit boundary is explicitly implemented.
- Keep CLI and MCP tools calling `P2PWorkspace`.

Design questions:

- Should `permissions` and `consent` be extracted in one feature or two smaller
  feature slices?
- Should service constructors receive raw paths, a filesystem adapter, or the
  current `P2PWorkspace` root/path values?
- Should normalization helpers live in `services.permissions`,
  `services.consent`, or a small shared domain helper module?
- Should expiry use an injectable clock for focused tests, or preserve current
  direct time behavior for the first extraction?
- Should service-level tests be added before moving code, or in the same
  implementation feature?

Initial task seeds:

- Create `src/p2p_engine/services/permissions.py` with no behavior drift.
- Move permission payload generation, actor normalization, role/kind
  normalization, policy read/write, and actor add/update behavior.
- Add focused tests for owner default payload and normalization helpers.
- Delegate `P2PWorkspace.permissions_show` and
  `P2PWorkspace.permissions_actor_add` to the service.
- Run existing CLI/MCP permission tests.
- Create `src/p2p_engine/services/consent.py` with no behavior drift.
- Move consent id/path helpers, operation/id normalization, grant/request/show/
  status/revoke/validate/consume/error behavior, and receipt mapper.
- Add focused tests for requested-not-authorized, actor mismatch, expiry,
  used-with-error, and consumed/revoked guards.
- Delegate `P2PWorkspace` consent methods to the service.
- Run all CLI/MCP consent and permission-gated operation tests.
- Confirm `src/p2p_engine/mcp/tools.py` audit helpers still work through the
  facade and were not silently folded into the consent service.

Acceptance seed:

- All existing tests from T021 and T022 pass unchanged.
- New focused service tests pass.
- `P2PWorkspace` method signatures and return objects are unchanged.
- No CLI/MCP command/tool schema changes.
- No `.p2p` path or YAML layout changes.

### Subsequent Extraction Backlog

Covered by T033.

These are local feature seeds to create after the permissions/consent extraction
feature is complete. Names are recommendations, not final proposal ids.

| Order | Proposed feature name | Scope | Key prerequisites | Notes |
| ---: | --- | --- | --- | --- |
| 1 | `p2pworkspace-remote-profile-service-extraction` | Extract remote profile read/configure/default payload behavior | Permissions/consent pattern proven | Low side-effect metadata extraction. |
| 2 | `p2pworkspace-renderers-validators-foundation` | Extract pure markdown renderers and YAML-shape validators used by specs/prompts/proposals | Shared helper ownership reviewed | Must avoid output drift. |
| 3 | `p2pworkspace-software-spec-service-extraction` | Extract software-spec refresh/status/show/prompt/import | Renderer/validator foundation | Keep current `.p2p/outputs/software-spec` behavior. |
| 4 | `p2pworkspace-project-definition-and-spec-export-extraction` | Extract project definition synthesis and generic/OpenSpec/Spec Kit exports | Software-spec service exists | Do not implement visible root output here. |
| 5 | `p2pworkspace-proposal-document-service-extraction` | Extract proposal list/show/create/update/contributions and proposal id resolution | Parser/render helpers stable | Exclude proposal branch lifecycle. |
| 6 | `p2pworkspace-readiness-service-extraction` | Extract readiness status/refresh/explain/profile/override helpers | Proposal document service exists | Keep readiness advisory. |
| 7 | `p2pworkspace-proposal-governance-service-extraction` | Extract non-branch accept/reject/defer/decision behavior | Proposal and readiness services exist | Keep owner-controlled semantics. |
| 8 | `p2pworkspace-work-plan-service-extraction` | Extract Work plan/list/status/show/retire metadata behavior | Spec export service exists | Exclude Work branch Git lifecycle. |
| 9 | `p2pworkspace-project-state-and-registry-extraction` | Extract generated project state and registries | Proposal/readiness/choice/change/work summaries stable | High coupling; keep accepted-only truth. |
| 10 | `p2pworkspace-sync-service-extraction` | Extract sync status/fetch/pull/push and remote guard logic | Remote profile service exists | Add focused clean-worktree/remote tests. |
| 11 | `p2pworkspace-proposal-branch-service-extraction` | Extract proposal branch lifecycle | Proposal/governance/sync services exist | Critical; one dedicated feature only. |
| 12 | `p2pworkspace-work-branch-service-extraction` | Extract Work branch lifecycle | Work plan/sync/proposal branch patterns proven | Critical; include conflict tests. |
| 13 | `p2pworkspace-mcp-consent-audit-helper-extraction` | Extract MCP consent audit helper behavior | Consent/sync/branch services exist | Keep permission-gated tool behavior unchanged. |
| 14 | `p2pworkspace-mcp-tool-registry-modularization` | Split MCP schemas/handlers by domain | Services and audit helper exist | Keep tool names/schemas unchanged. |
| 15 | `p2pworkspace-cli-command-modularization` | Split Typer command groups into `cli_commands/*` | Services extracted; MCP split optional | Presentation-only refactor. |

Backlog rules:

- Every backlog feature must start from the current inventory section for its
  boundary.
- Every backlog feature must add or confirm focused tests before moving
  high-risk behavior.
- Git lifecycle features must not be combined with CLI/MCP presentation
  modularization.
- Product behavior changes such as visible root exports, domain-aware export
  gating, or CLI/MCP breaking changes require separate proposal-derived specs.

### Reusable Done Criteria For Extraction Features

Covered by T034.

Each future extraction feature is done only when all relevant criteria below
are satisfied.

Behavior compatibility:

- Public `P2PWorkspace` methods keep the same names, parameters, return
  dataclasses/payloads, and error behavior.
- Existing CLI command names, options, arguments, output assertions, and exit
  semantics remain unchanged.
- Existing MCP tool names, schemas, read/write/permission-gated classification,
  and JSON payloads remain unchanged.
- `.p2p` storage paths, YAML keys, markdown sections, id formats, and status
  values remain unchanged.
- Advisory behavior stays advisory: readiness, choice discovery, next actions,
  prompt generation, and context generation must not make governance decisions.

Implementation structure:

- Extracted code lives behind an internal service/adapter/renderer/validator
  boundary named in this inventory.
- `P2PWorkspace` remains the public facade and delegates to the new boundary.
- Services do not import Typer, Rich, MCP transport code, or CLI formatters.
- Renderers receive prepared context and do not read `.p2p` state directly.
- Validators do not perform writes.
- Git/network side effects remain behind explicit adapters/services with
  guard checks.

Testing:

- All existing compatibility tests mapped for the touched boundary pass.
- Focused tests are added for moved normalization, validation, transition, or
  side-effect guard behavior when existing coverage is only end-to-end.
- High-risk Git/consent/governance extractions include negative-path tests for
  guard failures.
- No tests are weakened or removed to make extraction pass.

Traceability:

- The feature spec references the relevant boundary section in this inventory.
- Tasks identify which facade methods delegate after extraction.
- Tasks identify which helpers moved, which stayed temporarily, and why.
- Any intentional behavior change is explicitly excluded from refactoring and
  moved to a separate proposal-derived feature.

Verification:

- Run the focused tests for the moved boundary.
- Run the mapped CLI/MCP compatibility tests for that boundary.
- Run broader test suites when the extraction touches shared helpers, parsers,
  Git adapters, consent, governance, or generated output.
- Review `git diff` and confirm no unrelated `.p2p` generated state or local
  implementation specs were changed accidentally.

Completion statement template:

```text
Extraction complete for <boundary>.

- Facade methods delegated: <list>
- Services/adapters/renderers added: <list>
- Helpers moved: <list>
- Helpers intentionally left in P2PWorkspace: <list>
- Storage/CLI/MCP behavior changed: no
- Focused tests run: <commands>
- Compatibility tests run: <commands>
- Follow-up gaps: <list or none>
```

## Verification

Covered by T035-T038.

### Runtime Source Change Review

Covered by T035.

Reviewed commands:

```bash
git status --short src
git diff --name-only -- src
```

Result:

- No files under `src/` were reported.
- This feature changed local specification artifacts only.

### Local Validation

Covered by T036.

Reviewed command:

```bash
.venv/bin/p2p validate
```

Result:

```text
Validation
  errors: 0
  warnings: 0
  infos: 0
  findings: none
```

### Requirement Traceability

Covered by T037.

| Requirement | Evidence |
| --- | --- |
| R001 - Runtime Surface Inventory | File inventory, measurement baseline, responsibility matrix, and generated/non-source context. |
| R002 - P2PWorkspace Method Map | Method list and responsibility group mappings T005-T014. |
| R003 - Target Module Boundaries | Service boundary template and target boundaries T015-T020. |
| R004 - Compatibility Test Map | CLI/MCP compatibility map and missing test gaps T021-T026. |
| R005 - Extraction Order | Risk criteria and staged extraction order T027-T028. |
| R006 - Facade Contract | Delegation contract, temporary-stay methods, and separate-proposal boundaries T029-T031. |
| R007 - Implementation Task Derivation | Follow-up feature seeds, backlog, and done criteria T032-T034. |

### Task Completion Evidence

Covered by T038.

- T001-T004 are evidenced by inventory setup, baseline, file matrix, and source
  vs generated-state distinction.
- T005-T014 are evidenced by method maps and responsibility group mappings.
- T015-T020 are evidenced by target module boundary sections.
- T021-T026 are evidenced by compatibility test map and gap list.
- T027-T031 are evidenced by extraction order and facade contract sections.
- T032-T034 are evidenced by follow-up feature seeds and reusable done
  criteria.
- T035 is evidenced by reviewed `git status --short src` and
  `git diff --name-only -- src` output with no source files.
- T036 is evidenced by `.venv/bin/p2p validate` returning zero findings.
- T037 is evidenced by the requirement traceability table above.
