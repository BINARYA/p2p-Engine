# P2PWorkspace Filesystem Facade Wrapper Cleanup Design

## Current Shape

`P2PWorkspace` now delegates most runtime behavior to extracted services, but
`storage.filesystem` still contains private methods that simply forward to those
services. Some wrappers are intentional composition points because services
receive them as callbacks. Others are obsolete compatibility residue with no
callers.

## Cleanup Decision

This feature removes only wrappers confirmed by repository search to have no
callers outside their own definitions:

- `_consent_path`
- `_next_consent_id`
- `_compute_project_assessment`
- `_project_definition`
- `_work_summary_from_manifest`
- `_work_summary_from_scan`
- `_changes_for_proposal`
- `_next_proposal_id`
- `_proposal_branch_metadata`
- `_sync_remote`
- `_require_sync_remote`
- `_next_work_id`

Their service-owned equivalents remain available in:

- `services.consent`
- `services.project_assessment`
- `services.spec_export`
- `services.work_planning`
- `services.registry_records`
- `services.proposals`
- `services.proposal_branches`
- `services.sync`

## Preserved Wrappers

Wrappers such as `_find_proposal_dir`, `_find_change_dir`,
`_find_work_dir`, `_duplicate_proposal_ids`, registry record callbacks, and
`_permissions_path` remain because current services or focused tests still use
them. Rewiring those callbacks can be handled later as a separate, lower-risk
composition cleanup.

## Compatibility

The cleanup is internal-only. Public `P2PWorkspace` methods keep delegating to
service methods with the same observable behavior.
