# P2PWorkspace Remote Profile Service Extraction Requirements

## Scope

This feature continues the P2PWorkspace modular refactoring roadmap by
extracting remote project profile behavior from `P2PWorkspace` into an internal
service.

The extraction must preserve public CLI, MCP, storage, and sync-facing behavior.

## Origin

- Accepted source proposal: `PROP-059 - P2PWorkspace Modular Refactoring Plan`
- Architecture contract:
  `specs/features/p2pworkspace-modular-refactoring-contract/`
- Detailed inventory:
  `specs/features/p2pworkspace-refactoring-inventory-and-extraction-map/`
- Previous runtime extraction:
  `specs/features/p2pworkspace-permissions-consent-service-extraction/`

## In Scope

- Introduce an internal remote profile service.
- Move remote profile default payload, read, and configure behavior behind the
  service.
- Keep `P2PWorkspace` as the public compatibility facade.
- Preserve `.p2p/project.yml` remote section layout.
- Add focused tests for local and remote profile behavior.
- Run mapped CLI/MCP compatibility tests and full validation.

## Out Of Scope

- Changing sync status/fetch/pull/push behavior.
- Changing Git remote operations.
- Changing provider names, command names, options, output, or MCP schemas.
- Creating remote repositories on external providers.
- Moving proposal branch or Work branch remote behavior.
- Moving project initialization orchestration beyond delegating remote payload
  generation.

## Functional Requirements

### R001 - Remote Profile Service

THE SYSTEM SHALL provide an internal remote profile service that owns default
remote profile payload generation, remote profile read behavior, and remote
profile configure behavior.

Acceptance: `P2PWorkspace.remote_profile` and
`P2PWorkspace.configure_remote_profile` delegate to the service and return the
same remote profile-compatible object as before.

Status: implemented

### R002 - Initialization Compatibility

WHEN a project is initialized, THE SYSTEM SHALL create the same `remote` section
inside `.p2p/project.yml` as before.

Acceptance: local initialization keeps `mode: local`, `provider: local`,
`remote: null`, `url: null`, and the advisory review request block; cloud
initialization keeps provider, remote, URL, and review request fields.

Status: implemented

### R003 - Configure Compatibility

WHEN the remote profile is configured, THE SYSTEM SHALL preserve current
validation and write semantics.

Acceptance: invalid modes/providers still raise the same error fragments,
local mode clears remote and URL, remote mode rejects provider `local`, and
remote mode resolves missing URLs from the local Git remote when available.

Status: implemented

### R004 - Storage Compatibility

THE SYSTEM SHALL preserve `.p2p/project.yml` as the storage location for the
remote profile.

Acceptance: no new remote profile file is introduced and existing CLI/MCP tests
continue to read the same YAML shape.

Status: implemented

### R005 - Sync Boundary Preservation

THE SYSTEM SHALL keep sync behavior outside the remote profile service in this
feature.

Acceptance: `sync_status`, `sync_fetch`, `sync_pull`, `sync_push`,
`_sync_remote`, and `_require_sync_remote` remain facade/sync concerns and only
consume the remote profile through `P2PWorkspace`.

Status: implemented

### R006 - CLI/MCP Compatibility

THE SYSTEM SHALL preserve CLI and MCP behavior for project remote profile show
and configure commands/tools.

Acceptance: mapped CLI and MCP tests pass unchanged.

Status: implemented

### R007 - Focused Test Coverage

THE SYSTEM SHALL add focused tests for remote profile service behavior.

Acceptance: tests cover local default payload, remote default payload, profile
read fallback, configure local, configure remote with explicit URL, configure
remote with Git URL fallback, and invalid mode/provider paths.

Status: implemented

## Non-Functional Requirements

### N001 - No Behavior Drift

THE SYSTEM SHALL treat this as an internal extraction only.

Acceptance: no public CLI/MCP/storage/sync behavior changes are introduced.

Status: implemented

### N002 - No Presentation Coupling

THE SYSTEM SHALL keep the remote profile service free of Typer, Rich, and MCP
transport imports.

Acceptance: the service is called from `P2PWorkspace` and returns domain
objects or existing-compatible payloads.

Status: implemented

### N003 - Narrow Extraction

THE SYSTEM SHALL avoid moving unrelated sync, proposal branch, Work branch,
permission, consent, registry, or export behavior.

Acceptance: source changes are limited to the new service, facade delegation,
focused tests, and local feature specs.

Status: implemented

## Edge Cases And Errors

- Local initialization with remote provider or URL options.
- Cloud initialization with invalid provider.
- Cloud initialization with blank remote name defaults to `origin`.
- Configure invalid remote mode.
- Configure invalid provider.
- Configure remote mode with provider `local`.
- Configure remote mode without explicit URL and without matching Git remote.
- Missing `.p2p/project.yml` remote section fallback.
- Malformed remote or review request section fallback.

## Acceptance Criteria

- AC001: `P2PWorkspace` remains the public facade for remote profile behavior.
- AC002: Remote profile behavior is implemented behind an internal service.
- AC003: `.p2p/project.yml` remote section shape is unchanged.
- AC004: Existing CLI/MCP remote profile tests pass unchanged.
- AC005: Focused service tests cover moved behavior and negative paths.
- AC006: Sync and branch behavior are not moved in this feature.
- AC007: The completed implementation report lists facade methods delegated,
  helpers moved, helpers left in place, tests run, and remaining gaps.
