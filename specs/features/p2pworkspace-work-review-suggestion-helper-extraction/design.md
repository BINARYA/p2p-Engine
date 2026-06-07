# P2PWorkspace Work Review Suggestion Helper Extraction Design

## Decision

`WorkBranchService` owns Work branch lifecycle behavior, including the metadata
written when external review is requested. The review suggestion helper is part
of that behavior and should live in `services.work_branches`.

## Implementation

- Add `_review_request_suggestion`, `_github_web_url`, and `_gitlab_web_url` to
  `services.work_branches`.
- Make the `review_request_suggestion` constructor dependency optional and
  default it to the service-owned helper.
- Remove the helper injection from `P2PWorkspace._work_branch_service`.
- Remove the duplicate helper functions from `storage.filesystem`.

## Compatibility

Tests may still pass a custom `review_request_suggestion` callable to preserve
focused deterministic assertions. Runtime behavior uses the service default.
