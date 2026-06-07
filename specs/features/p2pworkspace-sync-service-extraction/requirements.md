# P2PWorkspace Sync Service Extraction Requirements

## Scope

Extract P2PWorkspace sync behavior into a cohesive internal service while
preserving the existing facade, CLI, MCP, Git adapter, consent, and remote
profile behavior.

This is local development specification work. It is not P2P governance state.

## Functional Requirements

- `P2PWorkspace.sync_status(remote=None)` MUST preserve the existing return
  fields and values for repository detection, branch, clean worktree state,
  remote mode, provider, selected remote, profile URL, resolved Git remote URL,
  `can_sync`, and reason.
- `P2PWorkspace.sync_fetch(remote=None)` MUST fetch the selected Git remote
  through the existing Git adapter and return the same action/status/branch/
  remote/remote_url shape.
- `P2PWorkspace.sync_pull(remote=None)` MUST preserve the current guard order:
  valid sync remote, attached branch, clean worktree, fast-forward-only pull.
- `P2PWorkspace.sync_push(remote=None)` MUST preserve the current guard order:
  valid sync remote, attached branch, clean worktree, push current branch.
- Explicit `remote` arguments MUST override the configured P2P remote profile.
- A local P2P remote profile with an existing Git `origin` and no explicit
  remote override MUST still report the current diagnostic that suggests
  configuring the P2P remote profile.
- A P2P remote profile URL mismatch with the Git remote URL MUST remain a
  `can_sync: false` status with the same human-readable reason.
- Missing Git remotes MUST keep the current diagnostics for profile URL and
  no-profile-URL cases.
- The service MUST use injected Git adapter callables so focused tests can
  cover behavior without real Git repositories.

## Compatibility Requirements

- Public `P2PWorkspace` method names, arguments, return attribute names, and
  error messages MUST remain compatible.
- CLI command names, options, output labels, and exit behavior MUST remain
  unchanged.
- MCP tool names, payload shapes, safety classification, consent checks, and
  consent receipt lifecycle MUST remain unchanged.
- Remote profile persistence remains owned by `services.remote_profile`.
- Raw Git subprocess calls remain owned by `storage.git`; the sync service only
  orchestrates through injected adapter callables.
- Proposal branch lifecycle and Work branch lifecycle remain outside this
  extraction.

## Non-Goals

- Do not change `.p2p` artifact layout.
- Do not change provider repository creation behavior.
- Do not split CLI or MCP modules in this feature.
- Do not move proposal publish/review/finalize/cleanup behavior.
- Do not move Work publish/finalize/cleanup behavior.
