# P2PWorkspace Sync Service Extraction Design

## Current Behavior

`P2PWorkspace` currently owns sync status computation and the managed
fetch/pull/push wrappers directly in `storage/filesystem.py`.

The current behavior combines:

- selected remote resolution from explicit CLI/MCP input or the remote profile;
- Git status reads;
- Git remote URL reads;
- local profile diagnostics;
- remote URL mismatch diagnostics;
- clean worktree and detached HEAD guards;
- Git fetch, fast-forward pull, and push calls.

## Target Boundary

Create `src/p2p_engine/services/sync.py`.

The service owns:

- `SyncStatus` and `SyncResult` dataclasses;
- selected remote resolution;
- sync status computation;
- sync remote validation;
- fetch/pull/push orchestration through injected Git adapter callables.

The service does not own:

- remote profile persistence;
- Git subprocess implementation;
- CLI/MCP presentation;
- consent request, verification, consumption, or audit behavior;
- proposal branch or Work branch lifecycle operations.

## Service Interface

`SyncService` receives:

- `root: Path`
- `remote_profile: Callable[[], object]`
- `git_status: Callable[[Path], object]`
- `remote_url: Callable[[Path, str], str | None]`
- `fetch_remote: Callable[[Path, str], bool]`
- `pull_branch: Callable[[Path, str, str], bool]`
- `push_branch: Callable[[Path, str, str], bool]`

The profile object is read structurally through attributes already exposed by
the remote profile service: `mode`, `provider`, `remote`, `url`.

The Git status object is read structurally through attributes exposed by
`storage.git.get_git_status`: `is_repository`, `branch`, `is_clean`.

## Facade Integration

`P2PWorkspace` keeps the existing public methods:

- `sync_status`
- `sync_fetch`
- `sync_pull`
- `sync_push`
- `_sync_remote`
- `_require_sync_remote`

Those methods delegate to `SyncService` so existing internal callers and tests
continue to work during the refactor.

`P2PWorkspace` gains a lazy `_sync_service()` factory.

## Compatibility Checks

Focused tests cover:

- local project outside Git repository;
- local P2P profile with Git origin diagnostic;
- explicit remote override;
- remote URL mismatch;
- missing remote diagnostics;
- fetch delegates through adapter;
- pull rejects detached HEAD;
- pull rejects dirty worktree;
- push rejects dirty worktree;
- failed adapter operations preserve error messages.

Mapped CLI tests:

```bash
.venv/bin/pytest \
  tests/test_cli.py::test_cli_sync_status_reports_local_project_without_remote \
  tests/test_cli.py::test_cli_sync_status_detects_git_origin_when_p2p_profile_is_local \
  tests/test_cli.py::test_cli_sync_status_detects_remote_profile_url_mismatch \
  tests/test_cli.py::test_cli_sync_push_fetch_and_pull_wrap_git_remote \
  tests/test_cli.py::test_cli_sync_pull_requires_clean_worktree
```

Mapped MCP tests:

```bash
.venv/bin/pytest \
  tests/test_mcp.py::test_mcp_safe_managed_sync_and_proposal_branch_tools \
  tests/test_mcp.py::test_mcp_sync_push_requires_and_consumes_consent \
  tests/test_mcp.py::test_mcp_sync_pull_requires_and_consumes_consent
```

Final checks:

```bash
.venv/bin/pytest
.venv/bin/p2p validate
```

## Risks

- Guard-order drift can change user-facing error messages.
- Dataclass ownership changes can affect MCP JSON conversion if field names
  drift.
- Remote profile local/remote diagnostics are easy to regress because they
  depend on both P2P profile and Git adapter state.
- Sync is used by consent-gated MCP tools, so CLI-only verification is not
  enough.
