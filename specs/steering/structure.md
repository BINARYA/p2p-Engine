# Structure Steering

## Repository Layers

```text
.p2p/
  Managed P2P governance and project state.

specs/
  Local development requirements, design, and implementation tasks.

src/p2p_engine/
  Runtime package code.

tests/
  Automated test coverage.

docs/
  Maintained user and contributor documentation.
```

## Ownership Boundaries

- `src/p2p_engine/cli.py` owns the Typer CLI surface.
- `src/p2p_engine/storage/filesystem.py` currently owns most filesystem-backed
  workspace behavior.
- `src/p2p_engine/mcp/` owns MCP tool definitions and dispatch.
- `src/p2p_engine/prompts/` owns reusable prompt text generation.
- `src/p2p_engine/storage/git.py` owns low-level Git command helpers.
- `tests/test_cli.py` covers CLI behavior.
- `tests/test_mcp.py` covers MCP behavior.
- `specs/` owns local implementation planning only.

## Target Architecture Direction

`P2PWorkspace` is the stable compatibility facade for existing CLI, MCP, and
internal callers. It is not the long-term home for all behavior.

Future non-trivial behavior should move toward cohesive internal services and
adapters behind that facade:

- domain rules and lifecycle invariants;
- application services and use cases;
- filesystem, Git, registry, export, consent, and agent adapters;
- CLI presentation;
- MCP schema and transport handling.

`src/p2p_engine/cli.py`, `src/p2p_engine/storage/filesystem.py`, and
`src/p2p_engine/mcp/tools.py` should become thinner compatibility and
orchestration layers. New unrelated domain logic should not be added to those
files by default.

## Feature Grouping

Local specs group implementation by product capability, not by individual P2P
proposal IDs.

Current feature groups:

- CLI foundation and proposal governance.
- Proposal readiness and prompt workflow.
- Project state, registries, and assessment.
- Intake, choices, conflicts, and next actions.
- Agent integration registry and generated instructions.
- MCP tool surface.
- Managed work, sync, permissions, and consent.
- Project definition export and legacy software-spec export.
- P2PWorkspace modular refactoring contract.

## Development Rule

Implementation steps, file-level coding plans, and validation checklists belong
in `specs/features/<feature-name>/tasks.md`, not in `.p2p/`.

If a feature changes runtime behavior, update tests with the implementation.
If a feature changes public behavior, update `docs/` with the implementation.

For the modular refactoring program, implement architecture guidance first.
Extract services/use cases before splitting CLI modules. Any breaking change to
CLI, MCP, storage artifacts, consent semantics, Git/sync behavior, validation,
registry refresh, or owner-controlled governance requires a separate accepted
proposal.
