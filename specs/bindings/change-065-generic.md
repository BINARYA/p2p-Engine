# Binding Report - CHANGE-065 Generic Export

## Inputs

- Generic project export:
  `.p2p/outputs/spec-export/CHANGE-065/generic/project.md`
- Generic propose prompt:
  `.p2p/outputs/spec-export/CHANGE-065/generic/propose.md`
- Existing steering files: `specs/steering/*`
- Source inspected:
  - `src/p2p_engine/cli.py`
  - `src/p2p_engine/storage/filesystem.py`
  - `src/p2p_engine/mcp/tools.py`
  - `src/p2p_engine/mcp/server.py`
  - `src/p2p_engine/prompts/*`
  - `src/p2p_engine/storage/git.py`
- Tests inspected:
  - `tests/test_cli.py`
  - `tests/test_mcp.py`

## Classification

### Steering Context

Imported into `specs/steering/*`:

- vision: organize distributed project intent into governed project definition;
- product boundary: P2P defines and exports projects; it does not decide for the
  owner or serve as hidden local coding task state;
- users: owners, contributors, AI agents, downstream tools;
- domain boundary: every project can produce generic output; software-only
  formats apply only to software-compatible domains;
- implementation rule: generated project output is theory/context until bound
  to `src`, `tests`, `docs`, or observed command behavior.

### Feature Candidates

The export source traceability and code surfaces were grouped into feature
capabilities rather than one feature per proposal:

- CLI proposal governance.
- Proposal readiness and prompts.
- Project state, registries, and assessment.
- Intake, choices, conflicts, and next actions.
- Agent integration registry.
- MCP tool surface.
- Managed work, sync, permissions, and consent.
- Legacy software-spec export.
- Documentation, install, and release.
- Domain-aware visible project definition export.

### Current Export Focus

The export is generated from:

```text
.p2p/outputs/spec-export/CHANGE-065/generic/
```

Its executive summary and software-domain sections are focused on
`CHANGE-065` / `PROP-006`, especially the Agent Integration Registry MVP. This
material was mapped to `specs/features/agent-integration-registry/`, not copied
into global steering.

### Open Questions And Gaps

- The current export path still depends on Change Set software-spec output.
- The future domain-aware visible project definition export is not implemented
  in `src/` yet.
- Existing software-spec behavior is implemented, but should be treated as
  legacy/software-only compatibility in future work.
- No full source evidence pass was performed for every individual accepted
  proposal; features were grouped by product capability.

## Steering Updates

Updated:

- `specs/steering/product.md`
- `specs/steering/domain.md`
- `specs/steering/structure.md`
- `specs/steering/tech.md`

Key additions:

- generated `project.md` is source context, not implementation proof;
- generated output must be classified before import;
- task completion requires binding evidence;
- feature grouping is by capability, not proposal ID.

## Feature Specs Created Or Updated

Created:

- `specs/features/cli-proposal-governance/`
- `specs/features/proposal-readiness-and-prompts/`
- `specs/features/project-state-registries-assessment/`
- `specs/features/intake-choice-conflict-next/`
- `specs/features/agent-integration-registry/`
- `specs/features/mcp-tool-surface/`
- `specs/features/managed-work-sync-permissions/`
- `specs/features/legacy-software-spec-export/`
- `specs/features/documentation-install-release/`

Updated:

- `specs/features/domain-aware-visible-project-definition-export/tasks.md`

## Requirement-To-Evidence Matrix

| Feature | Evidence | Status | Notes |
| --- | --- | --- | --- |
| CLI proposal governance | `src/p2p_engine/cli.py:218`, `src/p2p_engine/cli.py:885`, `src/p2p_engine/storage/filesystem.py:2763`, `tests/test_cli.py:22`, `tests/test_cli.py:1296`, `tests/test_cli.py:1363` | implemented | Core init, proposal, contribution, and decision surfaces exist. |
| Proposal readiness and prompts | `src/p2p_engine/cli.py:1024`, `src/p2p_engine/cli.py:1509`, `src/p2p_engine/storage/filesystem.py:2542`, `tests/test_cli.py:1188`, `tests/test_cli.py:1453`, `tests/test_mcp.py:1199` | implemented | Readiness and prompt-only workflows are implemented as advisory/deterministic surfaces. |
| Project state, registries, and assessment | `src/p2p_engine/cli.py:1793`, `src/p2p_engine/cli.py:2771`, `src/p2p_engine/storage/filesystem.py:3202`, `src/p2p_engine/storage/filesystem.py:5408`, `tests/test_cli.py:1602`, `tests/test_cli.py:1866`, `tests/test_mcp.py:1251` | implemented | Generated project state, registries, validation, rubrics, maturity, brief, and next actions are covered. |
| Intake, choices, conflicts, and next | `src/p2p_engine/cli.py:2851`, `src/p2p_engine/cli.py:2958`, `src/p2p_engine/cli.py:2155`, `tests/test_cli.py:3352`, `tests/test_cli.py:3424`, `tests/test_cli.py:3504`, `tests/test_mcp.py:1443` | implemented | Advisory intake/impact and explicit choice/conflict/next-action flows exist. |
| Agent integration registry | `src/p2p_engine/cli.py:430`, `src/p2p_engine/storage/filesystem.py:880`, `src/p2p_engine/storage/filesystem.py:904`, `src/p2p_engine/storage/filesystem.py:7050`, `tests/test_cli.py:951`, `tests/test_cli.py:998`, `tests/test_mcp.py:1081` | implemented | Default adapters, narrowed init, registry, drift, update, uninstall, and MCP lifecycle are covered. |
| MCP tool surface | `src/p2p_engine/mcp/tools.py:15`, `src/p2p_engine/mcp/tools.py:977`, `src/p2p_engine/mcp/tools.py:1856`, `tests/test_mcp.py:46`, `tests/test_mcp.py:1045`, `tests/test_mcp.py:1498`, `tests/test_mcp.py:1589` | implemented | Tool definitions, dispatch, write-safe tools, prompt tools, and JSON-RPC coverage exist. |
| Managed work, sync, permissions, and consent | `src/p2p_engine/cli.py:2224`, `src/p2p_engine/cli.py:2476`, `src/p2p_engine/cli.py:2543`, `src/p2p_engine/cli.py:1892`, `src/p2p_engine/storage/filesystem.py:1211`, `src/p2p_engine/storage/filesystem.py:4225`, `tests/test_cli.py:2119`, `tests/test_cli.py:2941`, `tests/test_cli.py:3184` | implemented | Change Set, Work lifecycle, sync, remote profile, permissions, and consent are implemented. |
| Legacy software-spec export | `src/p2p_engine/cli.py:2340`, `src/p2p_engine/cli.py:2412`, `src/p2p_engine/storage/filesystem.py:3964`, `src/p2p_engine/storage/filesystem.py:4090`, `tests/test_cli.py:1935`, `tests/test_mcp.py:1498` | implemented | Current behavior exists but is classified as legacy/software-only compatibility. |
| Documentation, install, and release | `README.md`, `docs/INSTALL.md`, `docs/MCP.md`, `pyproject.toml`, `.github/workflows/release.yml` | implemented | Evidence is docs/config, not primarily `src`. |
| Domain-aware visible project definition export | Current `src` still routes export through software-spec. | not_implemented | Requirements/design/tasks exist locally; implementation remains open. |

## Task Completion Decisions

Tasks were marked complete only in feature specs where direct evidence exists.

All checked tasks point to one or more of:

- `src/p2p_engine/cli.py`
- `src/p2p_engine/storage/filesystem.py`
- `src/p2p_engine/mcp/tools.py`
- `tests/test_cli.py`
- `tests/test_mcp.py`
- docs/config files for documentation/release-only tasks

No task in `domain-aware-visible-project-definition-export` was marked complete
from runtime evidence.

## Implementation Gaps

- Implement root-visible, domain-aware generic project definition export.
- Gate OpenSpec and Spec Kit by software-compatible domain or explicit profile.
- Update CLI, MCP, docs, and skills to stop recommending software-spec as the
  default project definition path.
- Decide whether `p2p spec` remains software-only compatibility or becomes
  deprecated.
- Decide the root-level output directory name and generated-file overwrite
  policy.

## Owner Questions

- What should the visible output directory be named: `p2p-output/`,
  `project-output/`, `project-definition/`, or another name?
- Should legacy `p2p spec` remain indefinitely for software projects?
- Should the next implementation pass start from
  `domain-aware-visible-project-definition-export/tasks.md`?
