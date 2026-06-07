# P2PWorkspace Work Branch Lifecycle Service Extraction Requirements

## Scope

Extract managed Work branch lifecycle behavior from `P2PWorkspace` into a
cohesive internal service while preserving existing CLI, MCP, storage, Git, and
consent behavior.

This is local development specification work. It is not P2P governance state.

## Functional Requirements

- Preserve `P2PWorkspace` public methods and return shapes for:
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
  - `scan_work_branches`
- Preserve Work manifest shape at `.p2p/work/WORK-XXX/manifest.yml`.
- Preserve Work branch naming from the manifest `git.branch_name`.
- Preserve status transitions and managed Git level flags.
- Preserve all current error messages and guard order unless a focused test
  proves behavior remains compatible.
- Preserve merge conflict metadata, continue/abort commands, and conflict
  marker detection behavior.
- Preserve local and remote branch cleanup semantics.
- Preserve Git side effects through injected adapter callables, not direct
  subprocess calls inside the service.

## Compatibility Requirements

- CLI command behavior and output remain unchanged.
- MCP tool payloads and consent-gated operation behavior remain unchanged.
- Consent verification/consumption stays outside the Work branch service.
- Work planning metadata remains owned by `services.work_planning`.
- Remote profile ownership stays in `services.remote_profile`.
- Sync status/fetch/pull/push stays in `services.sync`.

## Non-Goals

- Do not change Work planning behavior.
- Do not change proposal branch lifecycle behavior.
- Do not split CLI or MCP files in this feature.
- Do not change `.p2p` managed artifact layout.
