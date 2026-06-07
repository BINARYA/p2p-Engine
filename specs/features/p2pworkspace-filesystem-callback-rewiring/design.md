# P2PWorkspace Filesystem Callback Rewiring Design

## Current State

`P2PWorkspace` still contains private methods whose only purpose is to adapt
callbacks between extracted services:

- `_permissions_path`
- `_accepted_proposals`
- registry record callbacks
- `_find_proposal_dir`
- `_duplicate_proposal_ids`
- `_find_change_dir`
- `_find_work_dir`

These wrappers are small, but they keep duplicated ownership signals in the
facade. The owning services already expose the equivalent methods.

## Rewiring Strategy

The composition layer will obtain concrete service instances first and pass
their bound methods into dependent services:

- `PermissionsService.path`
- `ProposalDocumentService.find_dir`
- `ProposalDocumentService.duplicate_ids`
- `ChangeSetLifecycleService.find_dir`
- `WorkPlanningService.find_dir`
- `RegistryRecordBuilderService.*_records`
- `RegistryRecordBuilderService.accepted_proposals`

This keeps lazy construction in `P2PWorkspace` while removing private
pass-through methods once callers no longer need them.

## Circular Dependency Check

The rewiring is allowed only for dependencies that do not require the target
service to construct itself through the dependent service. For example,
`WorkBranchService` may receive `WorkPlanningService.find_dir`, while
`WorkPlanningService` may receive `ChangeSetLifecycleService.find_dir`.

## Test Update

Focused service tests that used private wrappers will be updated to use
service-owned collaborators. This makes tests reflect the extracted service
architecture instead of the old facade shape.
