# P2PWorkspace Permissions Consent Service Extraction Design

## Requirements Covered

- R001 - Permission Service
- R002 - Permission Storage Compatibility
- R003 - Consent Service
- R004 - Consent Storage Compatibility
- R005 - Consent Validation Semantics
- R006 - MCP Audit Boundary Preservation
- R007 - Facade Compatibility
- R008 - Focused Test Coverage
- R009 - Compatibility Test Preservation
- N001 - No Behavior Drift
- N002 - No Presentation Coupling
- N003 - Narrow Extraction

## Key Decisions

### D001 - Extract Permissions And Consent Together

Extract permissions and consent in one implementation feature.

Rationale: consent validation depends on permission actors and owner roles. A
single feature can introduce the service pattern once while keeping the first
runtime extraction small enough to review.

### D002 - Keep `P2PWorkspace` As The Only Public Caller Boundary

CLI and MCP continue to call `P2PWorkspace`; `P2PWorkspace` delegates to
services.

Rationale: this preserves all existing public behavior and follows the
compatibility facade contract.

### D003 - Use Rooted Service Constructors

Initial service constructors should receive `root` and `p2p_dir` or a minimal
path context from `P2PWorkspace`, not a broad `P2PWorkspace` instance.

Rationale: this keeps services independent from the monolith while avoiding a
larger filesystem adapter design in the first extraction.

### D004 - Keep Shared Normalization Close To The Services

Permission-specific normalization belongs in `services.permissions`. Consent
operation/id normalization belongs in `services.consent`. Shared actor id
normalization can live in `services.permissions` and be imported by consent, or
in a small internal helper if needed.

Rationale: avoid creating a generic helper module before there is real shared
complexity.

### D005 - Do Not Move MCP Audit Helpers

MCP consent audit helpers remain in `src/p2p_engine/mcp/tools.py` for this
feature.

Rationale: audit helpers combine consent, Git commits, optional pushes, and MCP
permission-gated operation orchestration. Moving them now would expand scope
from service extraction into MCP/Git lifecycle work.

### D006 - Add Focused Tests With Compatibility Tests

Add service-level tests for moved logic and keep existing CLI/MCP tests as
compatibility guards.

Rationale: end-to-end tests protect behavior; focused tests make future
service maintenance safer.

## Components

### `src/p2p_engine/services/permissions.py`

Owns:

- `.p2p/project/permissions.yml` path resolution.
- Default permission policy payload generation.
- Permission policy read/synthesize behavior.
- Actor add/update behavior.
- Identity slug generation.
- Permission role normalization.
- Actor kind normalization.
- Mapping YAML payloads to existing permission dataclasses.

Does not own:

- Consent receipt lifecycle.
- MCP audit.
- CLI output.
- Project initialization orchestration beyond providing the default payload or
  service method used by `init_project`.

### `src/p2p_engine/services/consent.py`

Owns:

- Consent receipt path resolution.
- Sequential `CONSENT-XXX` allocation.
- Consent operation normalization.
- Consent id normalization.
- Consent receipt mapper.
- Grant/request/show/status/revoke/validate/consume/used-with-error behavior.
- Expiry mutation to `expired`.

Does not own:

- Permission policy authoring.
- MCP audit commits/pushes.
- Permission-gated operation execution.
- CLI/MCP presentation.

### `src/p2p_engine/storage/filesystem.py`

Keeps:

- `P2PWorkspace` public methods.
- Facade compatibility.
- Service construction/delegation.
- Broader project initialization orchestration.

Moves or delegates:

- `permissions_show`
- `permissions_actor_add`
- `consent_grant`
- `consent_request`
- `consent_show`
- `consent_statuses`
- `consent_revoke`
- `consent_validate`
- `consent_consume`
- `consent_mark_used_with_error`
- `_permissions_path`
- `_consent_path`
- `_next_consent_id`
- `_permissions_payload`
- `_identity_slug`
- `_normalize_permission_role`
- `_normalize_actor_kind`
- `_normalize_consent_operation`
- `_normalize_consent_id`
- `_consent_receipt_from_payload`

### `src/p2p_engine/mcp/tools.py`

No structural extraction in this feature.

Must continue to work through the facade:

- `_consume_consent_with_audit`
- `_commit_and_push_consent_audit`
- `_mark_consent_error_on_head_change`

### Tests

Add focused tests, preferably in a new file:

- `tests/test_permissions_consent_services.py`

Keep compatibility tests in:

- `tests/test_cli.py`
- `tests/test_mcp.py`

## Data And Contracts

### Permission Policy

Storage path:

- `.p2p/project/permissions.yml`

Must preserve:

- owner/admin default policy generated during project initialization;
- actor ids generated from identity names;
- role names;
- actor kinds;
- tool class metadata;
- malformed policy validation behavior.

### Consent Receipts

Storage path:

- `.p2p/consents/CONSENT-XXX/consent.yml`

Must preserve:

- sequential `CONSENT-XXX` ids;
- status values;
- operation, target, actor, approver, rationale, expiry, and result fields;
- requested receipts not authorizing execution;
- expiry mutation to `expired`;
- consumed receipt result payloads;
- used-with-error behavior for partial side effects.

## Error Handling

Existing error behavior must be preserved for:

- invalid permission role;
- invalid actor kind;
- missing permission actor;
- non-owner consent approver;
- invalid consent operation;
- invalid consent id;
- missing consent receipt;
- requested receipt used as authorization;
- actor mismatch;
- operation mismatch;
- target mismatch;
- expired/revoked/consumed/used-with-error receipts.

Where tests assert message fragments, preserve those fragments exactly.

## Migration And Compatibility

No migration is required. Existing projects should continue using the same
files and methods.

Compatibility-sensitive surfaces:

- CLI: `permissions show`, `permissions actor add`, `consent grant`,
  `consent show`, `consent status`, `consent revoke`.
- MCP: `p2p_permissions_show`, `p2p_consent_request`,
  `p2p_consent_status`, `p2p_consent_show`, and all permission-gated tools
  that validate and consume consent.
- Storage: `.p2p/project/permissions.yml` and
  `.p2p/consents/CONSENT-XXX/consent.yml`.
- Audit: MCP audit commit message `P2P consent consume CONSENT-XXX`.

## Compatibility Tests To Run

Focused service tests:

```bash
.venv/bin/pytest tests/test_permissions_consent_services.py
```

CLI compatibility:

```bash
.venv/bin/pytest \
  tests/test_cli.py::test_cli_init_owner_populates_permissions_policy \
  tests/test_cli.py::test_cli_permissions_actor_and_consent_receipts \
  tests/test_cli.py::test_cli_consent_grant_requires_owner_approver \
  tests/test_cli.py::test_cli_validate_reports_invalid_permissions_policy
```

MCP compatibility:

```bash
.venv/bin/pytest \
  tests/test_mcp.py::test_mcp_remote_configure_and_consent_request_are_write_safe \
  tests/test_mcp.py::test_mcp_requested_consent_does_not_authorize_publish \
  tests/test_mcp.py::test_mcp_draft_proposal_decision_requires_granted_consent \
  tests/test_mcp.py::test_mcp_draft_proposal_accept_and_defer_consume_matching_consent \
  tests/test_mcp.py::test_mcp_proposal_publish_requires_and_consumes_consent \
  tests/test_mcp.py::test_mcp_proposal_publish_rejects_actor_mismatch_without_consuming_consent \
  tests/test_mcp.py::test_mcp_sync_push_requires_and_consumes_consent \
  tests/test_mcp.py::test_mcp_sync_pull_requires_and_consumes_consent \
  tests/test_mcp.py::test_mcp_proposal_request_review_requires_and_consumes_consent \
  tests/test_mcp.py::test_mcp_proposal_merge_requires_and_consumes_consent \
  tests/test_mcp.py::test_mcp_proposal_finalize_requires_and_consumes_consent \
  tests/test_mcp.py::test_mcp_proposal_reject_and_cleanup_require_consent \
  tests/test_mcp.py::test_mcp_permission_and_consent_read_tools
```

Validation:

```bash
.venv/bin/p2p validate
```

## Risks And Tradeoffs

- Extracting permissions and consent together is larger than extracting
  permissions alone, but keeps dependent validation behavior in one reviewable
  feature.
- Rooted service constructors are pragmatic for the first extraction, but a
  later filesystem adapter may still be useful.
- Keeping MCP audit helpers in place means `mcp/tools.py` remains coupled for
  now, but avoids broadening this feature into Git/audit refactoring.

## Out Of Scope

- MCP audit helper extraction.
- Sync/proposal branch/Work branch extraction.
- CLI command modularization.
- MCP tool registry modularization.
- Storage migrations.
- Behavior changes to consent authorization.

## Preparation Verification

This feature spec was created before runtime implementation starts.

Reviewed commands:

```bash
git status --short src specs/features/p2pworkspace-permissions-consent-service-extraction
.venv/bin/p2p validate
```

Result:

- No runtime source files under `src/` were changed while creating this feature
  spec.
- `.venv/bin/p2p validate` completed with `errors: 0`, `warnings: 0`,
  `infos: 0`, and `findings: none`.

## Phase 1 Review Evidence

Covered by T001-T003.

### Current Implementation Review

Reviewed source:

```bash
sed -n '1160,1455p' src/p2p_engine/storage/filesystem.py
sed -n '8030,8158p' src/p2p_engine/storage/filesystem.py
```

Facade methods to delegate:

- `permissions_show`
- `permissions_actor_add`
- `consent_grant`
- `consent_request`
- `consent_show`
- `consent_statuses`
- `consent_revoke`
- `consent_validate`
- `consent_consume`
- `consent_mark_used_with_error`

Helpers to move behind services:

- `_permissions_path`
- `_consent_path`
- `_next_consent_id`
- `_permissions_payload`
- `_identity_slug`
- `_normalize_permission_role`
- `_normalize_actor_kind`
- `_normalize_consent_operation`
- `_normalize_consent_id`
- `_consent_receipt_from_payload`

Helpers intentionally left outside this extraction:

- `_repository_mode`, because it is shared project metadata used beyond
  permissions.
- `_slugify`, because it is shared by proposal, branch, Work, and export naming.
- MCP consent audit helpers, because they combine consent with Git/audit and
  MCP permission-gated operation orchestration.

### MCP Audit Review

Reviewed source:

```bash
rg -n "def _consume_consent_with_audit|def _commit_and_push_consent_audit|def _mark_consent_error_on_head_change|consent_validate|consent_consume|consent_mark_used_with_error" src/p2p_engine/mcp/tools.py
```

Confirmed boundary:

- MCP tools call `workspace.consent_validate`, `workspace.consent_consume`, and
  `workspace.consent_mark_used_with_error` through the `P2PWorkspace` facade.
- `_consume_consent_with_audit`, `_commit_and_push_consent_audit`, and
  `_mark_consent_error_on_head_change` remain MCP-side for this feature.
- The service extraction must not move Git audit commit/push behavior.

### Compatibility Test Commands

Focused service test command to create and run after service tests exist:

```bash
.venv/bin/pytest tests/test_permissions_consent_services.py
```

CLI compatibility command:

```bash
.venv/bin/pytest \
  tests/test_cli.py::test_cli_init_owner_populates_permissions_policy \
  tests/test_cli.py::test_cli_permissions_actor_and_consent_receipts \
  tests/test_cli.py::test_cli_consent_grant_requires_owner_approver \
  tests/test_cli.py::test_cli_validate_reports_invalid_permissions_policy
```

MCP compatibility command:

```bash
.venv/bin/pytest \
  tests/test_mcp.py::test_mcp_remote_configure_and_consent_request_are_write_safe \
  tests/test_mcp.py::test_mcp_requested_consent_does_not_authorize_publish \
  tests/test_mcp.py::test_mcp_draft_proposal_decision_requires_granted_consent \
  tests/test_mcp.py::test_mcp_draft_proposal_accept_and_defer_consume_matching_consent \
  tests/test_mcp.py::test_mcp_proposal_publish_requires_and_consumes_consent \
  tests/test_mcp.py::test_mcp_proposal_publish_rejects_actor_mismatch_without_consuming_consent \
  tests/test_mcp.py::test_mcp_sync_push_requires_and_consumes_consent \
  tests/test_mcp.py::test_mcp_sync_pull_requires_and_consumes_consent \
  tests/test_mcp.py::test_mcp_proposal_request_review_requires_and_consumes_consent \
  tests/test_mcp.py::test_mcp_proposal_merge_requires_and_consumes_consent \
  tests/test_mcp.py::test_mcp_proposal_finalize_requires_and_consumes_consent \
  tests/test_mcp.py::test_mcp_proposal_reject_and_cleanup_require_consent \
  tests/test_mcp.py::test_mcp_permission_and_consent_read_tools
```

## Implementation Evidence

Covered by T004-T025.

### Source Changes

Added service modules:

- `src/p2p_engine/services/__init__.py`
- `src/p2p_engine/services/permissions.py`
- `src/p2p_engine/services/consent.py`

Updated facade:

- `src/p2p_engine/storage/filesystem.py`

Added focused tests:

- `tests/test_permissions_consent_services.py`

### Facade Methods Delegated

`P2PWorkspace` now constructs internal services lazily and delegates:

- `permissions_show`
- `permissions_actor_add`
- `consent_grant`
- `consent_request`
- `consent_show`
- `consent_statuses`
- `consent_revoke`
- `consent_validate`
- `consent_consume`
- `consent_mark_used_with_error`
- `_permissions_path`
- `_consent_path`
- `_next_consent_id`

Project initialization now obtains the default permission policy payload from
`PermissionsService.default_policy_payload`.

### Behavior Moved

Moved behind `PermissionsService`:

- permission policy path resolution;
- default permission policy payload generation;
- permission policy read/write behavior;
- actor add/update behavior;
- actor id, role, and kind normalization.

Moved behind `ConsentService`:

- consent path resolution;
- sequential `CONSENT-XXX` id allocation;
- consent operation and id normalization;
- receipt payload mapping;
- grant/request/show/status/revoke behavior;
- validate/consume/used-with-error transitions;
- expiry mutation to `expired`.

### Helpers Left In Place

The previous helper functions and dataclasses in
`src/p2p_engine/storage/filesystem.py` were not broadly deleted in this first
runtime extraction. Some are still used by unrelated `P2PWorkspace` behavior,
and the rest are intentionally left for a later cleanup pass so this feature
remains a behavior-preserving extraction.

MCP audit helpers remain in `src/p2p_engine/mcp/tools.py`:

- `_consume_consent_with_audit`
- `_commit_and_push_consent_audit`
- `_mark_consent_error_on_head_change`

They continue to call the `P2PWorkspace` facade and were not folded into the
core consent service.

### Verification Commands

Focused service tests:

```bash
.venv/bin/pytest tests/test_permissions_consent_services.py
```

Result:

- `5 passed`

Mapped CLI compatibility:

```bash
.venv/bin/pytest tests/test_cli.py -k "permissions or consent or validate_reports_invalid_permissions_policy"
```

Result:

- `4 passed, 89 deselected`

Mapped MCP compatibility:

```bash
.venv/bin/pytest tests/test_mcp.py -k "consent or permission"
```

Result:

- `13 passed, 31 deselected`

Validation:

```bash
.venv/bin/p2p validate
```

Result:

- `errors: 0`
- `warnings: 0`
- `infos: 0`
- `findings: none`

### Source Scope Review

Reviewed with:

```bash
git status --short
```

Current runtime extraction scope:

- `src/p2p_engine/storage/filesystem.py`
- `src/p2p_engine/services/`
- `tests/test_permissions_consent_services.py`
- `specs/features/p2pworkspace-permissions-consent-service-extraction/`

The worktree also contains pre-existing `.p2p`, `AGENTS.md`, `docs/`, and
other `specs/` changes from previous project-definition and refactoring-spec
work. Those files are not part of this runtime extraction and were not changed
to implement the permission/consent service boundary.

### Remaining Gaps

No behavior gap is known for this feature after the focused, CLI, MCP, and P2P
validation commands above.

Possible follow-up cleanup:

- remove unused legacy helper functions from `P2PWorkspace` after a separate
  dead-code review;
- move shared domain dataclasses to service-owned or core-owned modules if a
  later extraction needs a single canonical definition.
