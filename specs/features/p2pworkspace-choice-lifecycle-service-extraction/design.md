# P2PWorkspace Choice Lifecycle Service Extraction Design

## Summary

Create `ChoiceLifecycleService` as the owner of `.p2p/choices` runtime
behavior. Keep `P2PWorkspace` as a stable facade that wires proposal/change
lookup and registry dependencies into the service.

This slice continues the modular refactoring by moving a cohesive lifecycle out
of `storage/filesystem.py` without changing public CLI/MCP behavior.

## Target Module

`src/p2p_engine/services/choices.py`

Expected contents:

- `ChoiceStatus` dataclass.
- `ChoiceDetail` dataclass.
- `ChoiceDiscoveryFinding` dataclass.
- `ChoiceLifecycleService` class.
- Local YAML, optional-file, slug, and option lookup helpers where needed.

`src/p2p_engine/storage/filesystem.py` should import and re-export the choice
dataclasses for compatibility.

## Service Responsibilities

- Resolve `.p2p/choices`.
- Allocate sequential `CHOICE-001` IDs.
- Resolve existing choice directories by ID.
- Create choice artifact sets:
  - `choice.md`
  - `options.yml`
  - `decision.md`
  - `links.yml`
- List choice statuses.
- Show choice detail.
- Discover advisory findings from proposal-local choice registry records and
  project choices.
- Record and update active blockers.
- Deactivate blockers.
- Decide choices by selecting an option, updating options, writing
  `decision.md`, and updating choice frontmatter.

## Facade Responsibilities

`P2PWorkspace` should provide:

- a cached `_choice_lifecycle_service()` factory;
- public delegating methods:
  - `create_choice`
  - `choice_statuses`
  - `show_choice`
  - `discover_choices`
  - `block_choice`
  - `unblock_choice`
  - `decide_choice`

The facade passes these dependencies:

- `find_proposal_dir`
- `find_change_dir`
- `choice_registry_records`

## Compatibility Notes

- `NextActionService` already consumes choices through facade callables, so it
  should not import the new choice service.
- `ProjectAssessmentService` consumes `choice_statuses` through a facade
  callable, so no direct dependency change is needed.
- MCP handlers and CLI command modules must continue calling `P2PWorkspace`.

## Verification Plan

Focused tests:

- `tests/test_choice_lifecycle_service.py`
- `tests/test_cli.py -k "choice_create_list_and_decide or choice_discovery_blocking_and_next_integration"`
- `tests/test_mcp.py -k choice`
- `tests/test_next_actions_service.py -k choice`

Regression tests:

- full `pytest`
- `.venv/bin/p2p validate`
