# P2PWorkspace Remote Profile Service Extraction Design

## Requirements Covered

- R001 - Remote Profile Service
- R002 - Initialization Compatibility
- R003 - Configure Compatibility
- R004 - Storage Compatibility
- R005 - Sync Boundary Preservation
- R006 - CLI/MCP Compatibility
- R007 - Focused Test Coverage
- N001 - No Behavior Drift
- N002 - No Presentation Coupling
- N003 - Narrow Extraction

## Key Decisions

### D001 - Extract Remote Profile Before Sync

Extract remote profile metadata before sync behavior.

Rationale: sync depends on selected remote/profile metadata, but remote profile
read/configure behavior has limited side effects and can prove another small
service extraction before Git-heavy work.

### D002 - Keep `P2PWorkspace` As The Public Boundary

CLI, MCP, sync, proposal branches, and Work branches continue to call
`P2PWorkspace.remote_profile` or `P2PWorkspace.configure_remote_profile`.

Rationale: this preserves compatibility while reducing `filesystem.py`.

### D003 - Use Rooted Service Constructor

The service receives `root` and `p2p_dir`, plus a Git remote URL resolver
callable.

Rationale: this keeps the service independent from `P2PWorkspace` while
allowing tests to verify URL fallback behavior without shelling out to Git.

### D004 - Keep Sync Guards Out Of Scope

`sync_status`, `_sync_remote`, and `_require_sync_remote` are not extracted.

Rationale: those methods combine remote profile metadata with Git status,
branch state, and clean-worktree/remote mismatch behavior. They belong in a
later sync extraction.

## Components

### `src/p2p_engine/services/remote_profile.py`

Owns:

- `.p2p/project.yml` path resolution for remote profile reads/writes;
- default remote profile payload generation for local/cloud repository modes;
- profile read fallback from missing or malformed remote sections;
- configure validation and write behavior;
- mapping YAML data to a remote profile dataclass.

Does not own:

- sync status/fetch/pull/push;
- Git branch operations;
- proposal branch or Work branch publishing;
- CLI/Rich output;
- MCP schema/transport behavior;
- external provider repository creation.

### `src/p2p_engine/storage/filesystem.py`

Keeps:

- `P2PWorkspace` facade methods;
- project initialization orchestration;
- sync and branch workflows that consume the remote profile.

Delegates:

- remote profile default payload during init;
- `remote_profile`;
- `configure_remote_profile`.

## Data And Contracts

Storage path:

- `.p2p/project.yml`

Remote section keys to preserve:

- `mode`
- `provider`
- `remote`
- `url`
- `review_request.mode`
- `review_request.opens_external_request`

Profile defaults to preserve:

- local mode: provider `local`, no remote, no URL;
- remote mode: provider defaults to `generic`, remote defaults to `origin`,
  URL is explicit or resolved from the Git remote;
- review request is advisory and does not open external requests.

## Error Handling

Preserve current error fragments for:

- `Remote provider and URL options require --repository cloud`;
- `Remote provider must be generic, github, or gitlab`;
- blank remote name during cloud initialization falls back to `origin`;
- `Remote project mode must be local or remote`;
- `Remote provider must be local, generic, github, or gitlab`;
- `Remote-backed projects cannot use provider local`;
- `Remote URL is required and Git remote was not found`.

## Compatibility Tests To Run

Focused service tests:

```bash
.venv/bin/pytest tests/test_remote_profile_service.py
```

CLI compatibility:

```bash
.venv/bin/pytest \
  tests/test_cli.py::test_cli_init_cloud_configures_remote_profile \
  tests/test_cli.py::test_cli_init_rejects_ambiguous_repository_remote_alias \
  tests/test_cli.py::test_cli_project_remote_configure_and_show \
  tests/test_cli.py::test_cli_sync_status_reports_local_project_without_remote \
  tests/test_cli.py::test_cli_sync_status_detects_remote_profile_url_mismatch
```

MCP compatibility:

```bash
.venv/bin/pytest \
  tests/test_mcp.py::test_mcp_remote_configure_and_consent_request_are_write_safe \
  tests/test_mcp.py::test_mcp_change_project_registry_and_remote_read_tools
```

Validation:

```bash
.venv/bin/p2p validate
```

## Risks And Tradeoffs

- The service still touches `.p2p/project.yml`; this is acceptable because it
  owns only the remote section and does not introduce a new storage file.
- Keeping the dataclass local to the service while `P2PWorkspace` annotations
  remain compatible may create temporary duplicate names, but it avoids a broad
  domain model migration in this feature.
- URL fallback still depends on Git remote resolution through an injected
  callable; this keeps behavior unchanged and testable.

## Out Of Scope

- Sync service extraction.
- Git adapter refactoring.
- CLI command modularization.
- MCP tool registry modularization.
- Provider API integration.

## Implementation Evidence

Covered by T001-T020.

### Baseline

Before runtime extraction:

```bash
.venv/bin/pytest
```

Result:

- `155 passed`

### Source Changes

Added service module:

- `src/p2p_engine/services/remote_profile.py`

Updated facade:

- `src/p2p_engine/storage/filesystem.py`

Added focused tests:

- `tests/test_remote_profile_service.py`

Updated local feature specs:

- `specs/features/p2pworkspace-remote-profile-service-extraction/requirements.md`
- `specs/features/p2pworkspace-remote-profile-service-extraction/design.md`
- `specs/features/p2pworkspace-remote-profile-service-extraction/tasks.md`

### Facade Methods Delegated

`P2PWorkspace` now constructs `RemoteProfileService` lazily and delegates:

- `remote_profile`
- `configure_remote_profile`

Project initialization now obtains the default remote profile payload from
`RemoteProfileService.default_payload`.

### Behavior Moved

Moved behind `RemoteProfileService`:

- `.p2p/project.yml` path resolution for remote profile reads/writes;
- local/cloud remote profile default payload generation;
- remote profile read fallback from missing or malformed sections;
- configure validation and write behavior;
- mapping YAML data to a remote profile dataclass;
- Git remote URL fallback through an injected resolver callable.

### Behavior Left In Place

The following remain in `P2PWorkspace` or existing adapters for later
extractions:

- `sync_status`
- `sync_fetch`
- `sync_pull`
- `sync_push`
- `_sync_remote`
- `_require_sync_remote`
- proposal branch remote publish/finalize/cleanup behavior;
- Work branch remote publish/finalize/cleanup behavior;
- Git adapter functions in `src/p2p_engine/storage/git.py`;
- CLI and MCP presentation/transport logic.

The legacy helper `_init_remote_profile_payload` remains in
`src/p2p_engine/storage/filesystem.py` for a later dead-code cleanup pass. It is
no longer used by project initialization.

### Compatibility Correction

During focused test creation, the initial spec assumed that a blank remote name
for cloud initialization raised `Remote name is required for cloud-backed
projects`. The existing implementation actually treats an empty remote value as
missing and falls back to `origin`.

The spec and focused test were corrected to preserve existing behavior rather
than introduce drift.

### Verification Commands

Focused service tests:

```bash
.venv/bin/pytest tests/test_remote_profile_service.py
```

Result:

- `5 passed`

Mapped CLI compatibility:

```bash
.venv/bin/pytest \
  tests/test_cli.py::test_cli_init_cloud_configures_remote_profile \
  tests/test_cli.py::test_cli_init_rejects_ambiguous_repository_remote_alias \
  tests/test_cli.py::test_cli_project_remote_configure_and_show \
  tests/test_cli.py::test_cli_sync_status_reports_local_project_without_remote \
  tests/test_cli.py::test_cli_sync_status_detects_remote_profile_url_mismatch
```

Result:

- `5 passed`

Mapped MCP compatibility:

```bash
.venv/bin/pytest \
  tests/test_mcp.py::test_mcp_remote_configure_and_consent_request_are_write_safe \
  tests/test_mcp.py::test_mcp_change_project_registry_and_remote_read_tools
```

Result:

- `2 passed`

Validation:

```bash
.venv/bin/p2p validate
```

Result:

- `errors: 0`
- `warnings: 0`
- `infos: 0`
- `findings: none`

Full post-extraction suite:

```bash
.venv/bin/pytest
```

Result:

- `160 passed`

### Source Scope Review

Runtime extraction scope:

- `src/p2p_engine/services/remote_profile.py`
- `src/p2p_engine/storage/filesystem.py`
- `tests/test_remote_profile_service.py`
- `specs/features/p2pworkspace-remote-profile-service-extraction/`

The worktree also contains pre-existing `.p2p`, `AGENTS.md`, `docs/`, and
other `specs/` changes from previous project-definition and refactoring-spec
work. Those files are not part of this remote profile runtime extraction.

### Remaining Gaps

No behavior gap is known for this feature after focused, CLI, MCP, P2P
validation, and full-suite verification.

Possible follow-up cleanup:

- remove unused legacy remote helper code from `P2PWorkspace` after a separate
  dead-code review;
- move remote-profile dataclass ownership to a shared core module only if a
  later extraction needs a single canonical domain type.
