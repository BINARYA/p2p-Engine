# P2PWorkspace Proposal Branch Lifecycle Service Extraction Requirements

## Scope

Extract managed proposal branch lifecycle behavior from `P2PWorkspace` into a
cohesive internal service while preserving existing CLI, MCP, storage, Git, and
consent behavior.

This is local development specification work. It is not P2P governance state.

## Functional Requirements

- Preserve `P2PWorkspace` public methods and return shapes for:
  - `branch_proposal`
  - `show_proposal_branch`
  - `publish_proposal_branch`
  - `request_proposal_branch_review`
  - `retire_proposal_branch`
  - `accept_proposal_branch`
  - `reject_proposal_branch`
  - `merge_proposal_branch`
  - `continue_merge_proposal_branch`
  - `abort_merge_proposal_branch`
  - `finalize_proposal_branch`
  - `cleanup_proposal_branch`
  - `scan_proposal_branches`
- Preserve all current error messages and guard order unless a focused test
  proves that a different order is behaviorally equivalent.
- Preserve branch name format:
  `p2p/proposal/<PROP-ID>-<title-slug>-<actor-slug>-<hash16>`.
- Preserve branch metadata file shape at
  `.p2p/proposals/<proposal-dir>/branch.yml`.
- Preserve auto-renumber behavior when remote proposal ID collisions are found.
- Preserve merge conflict metadata, continue/abort commands, and conflict
  marker detection behavior.
- Preserve local and remote branch cleanup semantics.
- Preserve Git side effects through injected adapter callables, not direct
  subprocess calls inside the service.

## Compatibility Requirements

- CLI command behavior and output remain unchanged.
- MCP tool payloads and consent-gated operation behavior remain unchanged.
- Consent verification/consumption stays outside the branch lifecycle service.
- Remote profile ownership stays in `services.remote_profile`.
- Sync status/fetch/pull/push stays in `services.sync`.
- Proposal document lookup stays in `services.proposals`, accessed through
  injected callbacks.

## Non-Goals

- Do not change owner-controlled governance semantics.
- Do not change proposal acceptance/rejection for non-branch proposals.
- Do not extract Work branch lifecycle in this feature.
- Do not split CLI or MCP files in this feature.
- Do not change `.p2p` managed artifact layout.
