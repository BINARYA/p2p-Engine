# P2PWorkspace Change Set Lifecycle Service Extraction Requirements

## Purpose

Extract Change Set lifecycle behavior from `P2PWorkspace` into a cohesive
service while preserving CLI, MCP, software-spec, spec-export, registry, work
planning, project assessment, and next-action behavior.

This is local software-development planning. It is not P2P governance state.

## Current Behavior To Preserve

- `p2p change create` creates `.p2p/changes/CHANGE-XXX-<slug>/` from an
  accepted proposal.
- Change creation refuses proposals that are not accepted.
- Change creation writes the existing artifact set:
  `change.md`, included/referenced/excluded proposal files, included decisions,
  `impact-map.yml`, `git-policy.yml`, `execution-plan.md`, `tasks.yml`, and
  `actions.yml`.
- `p2p change status`, `show`, `policy`, `set-status`, and `tasks` keep the
  same output behavior.
- MCP change tools keep the same JSON response shapes.
- Other services can still resolve Change Set directories through
  `P2PWorkspace._find_change_dir`.

## Functional Requirements

1. The service MUST own Change Set ID allocation, directory lookup, creation,
   status listing, policy reading, show, status update, and task/action reading.
2. The service MUST keep `.p2p/changes` file layout unchanged.
3. The service MUST preserve Change Set frontmatter and markdown structure.
4. The service MUST preserve status transition validation and error messages.
5. The service MUST preserve invalid `git-policy.yml`, `tasks.yml`, and
   `actions.yml` error messages.
6. The service MUST avoid direct CLI and MCP imports.
7. `P2PWorkspace` MUST remain the compatibility facade for public callers.

## Compatibility Requirements

- Public method names on `P2PWorkspace` remain:
  `create_change_set`, `change_set_statuses`, `change_set_policy`,
  `show_change_set`, `update_change_set_status`, and `change_set_tasks`.
- Private compatibility method `_find_change_dir` remains available and
  delegates to the service.
- Existing imports of `ChangeSetStatus`, `ChangeSetPolicy`, `ChangeSetDetail`,
  and `ChangeSetTaskView` from `p2p_engine.storage.filesystem` remain valid.
- No CLI command, CLI output, MCP tool name, or MCP response key changes are
  allowed.

## Non-Goals

- Do not change software-spec or spec-export generation.
- Do not change Work planning behavior.
- Do not introduce Git branch/commit automation.
- Do not extract validation, initialization, maturity/rubrics, or agent
  instructions in this slice.

## Acceptance Criteria

- `src/p2p_engine/services/changes.py` contains the extracted service and
  Change Set models.
- `src/p2p_engine/storage/filesystem.py` delegates Change Set public behavior
  and `_find_change_dir` to the service.
- Existing CLI, MCP, software-spec, spec-export, registry, work-planning, and
  next-action tests pass unchanged.
- New service-level tests cover create/show/status/policy/tasks/status update
  and error paths.
