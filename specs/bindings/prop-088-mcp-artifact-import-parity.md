# Binding Report - PROP-088 MCP Artifact Import Parity

## Inputs

- Source proposal: `PROP-088 - MCP Artifact Import Parity`
- Accepted Change Set: `CHANGE-066 - MCP Artifact Import Parity`
- Existing steering files:
  - `specs/steering/structure.md`
- Source inspected:
  - `src/p2p_engine/services/proposal_artifacts.py`
  - `src/p2p_engine/storage/filesystem.py`
  - `src/p2p_engine/cli_commands/prompts.py`
  - `src/p2p_engine/cli_commands/project_analysis.py`
  - `src/p2p_engine/mcp/catalog/proposals.py`
  - `src/p2p_engine/mcp/catalog/prompts.py`
  - `src/p2p_engine/mcp/registry.py`
  - `src/p2p_engine/mcp/tools.py`
  - `src/p2p_engine/mcp/handlers/proposals.py`
  - `src/p2p_engine/mcp/handlers/work_specs.py`
  - `src/p2p_engine/mcp/handlers/common.py`
- Tests inspected:
  - `tests/test_proposal_artifact_service.py`
  - `tests/test_mcp_proposal_handler.py`
  - `tests/test_mcp.py`
  - `tests/test_mcp_registry.py`
- Local quality guidance inspected:
  - `AGENTS-p2p-dev-specs.md`
  - `specs/skills/ENGINEERING_QUALITY_SKILL.md`
  - `specs/skills/TEST_QUALITY_SKILL.md`

## Classification

### Steering Context

- `.p2p/` remains governed project state.
- `specs/` owns local implementation planning only.
- `P2PWorkspace` remains a compatibility facade.
- New domain behavior should live behind cohesive services rather than in
  `src/p2p_engine/cli.py`, `src/p2p_engine/storage/filesystem.py`, or
  `src/p2p_engine/mcp/tools.py`.
- Public MCP behavior is a compatibility contract and must be tested at the MCP
  surface.

### Feature Candidate

`PROP-088` maps to a new local feature:

```text
specs/features/mcp-artifact-import-parity/
```

### Current Implementation Focus

The implementation feature should add MCP write-safe import parity for existing
controlled CLI proposal artifact imports:

- exploration;
- impact;
- clarification;
- synthesis/proposal;
- execution plan;
- tasks.

It should not create a generic arbitrary artifact import primitive.

### Open Questions And Gaps

- No owner decision remains open for MVP scope. The owner selected total parity
  with existing controlled CLI import primitives.
- The implementation still needs a concrete code choice between:
  - service-owned direct payload helpers; or
  - controlled temporary staging that reuses existing source-path import
    methods.
- The implementation must prove that artifact coverage state remains separate
  from content import unless a later accepted feature changes that behavior.

## Steering Updates

No steering files were updated. Existing steering already covers:

- `specs/` as local implementation planning;
- MCP tool surface as a public contract;
- service extraction and facade preservation.

## Feature Specs Created Or Updated

Created:

- `specs/features/mcp-artifact-import-parity/requirements.md`
- `specs/features/mcp-artifact-import-parity/design.md`
- `specs/features/mcp-artifact-import-parity/tasks.md`
- `specs/bindings/prop-088-mcp-artifact-import-parity.md`

## Requirement-To-Evidence Matrix

| Requirement | Expected Behavior | Evidence | Status | Notes |
| --- | --- | --- | --- | --- |
| R001 | MCP lists six import tools. | `src/p2p_engine/mcp/registry.py`, `src/p2p_engine/mcp/catalog/proposals.py`, future MCP tests. | planned | Tool names are additive. |
| R002-R003 | Source-path exploration and impact imports match CLI behavior. | `ProposalArtifactService.import_exploration`, `ProposalArtifactService.import_impact`, future MCP tests. | planned | Existing service behavior is the baseline. |
| R004-R007 | Clarify, synthesize, plan, and tasks imports map to fixed targets. | `ProposalArtifactService.import_artifact`, future MCP tests. | planned | Existing tasks validation must be preserved. |
| R008-R012 | Direct payload imports write only fixed targets and allowlisted files. | Future service helpers and tests. | planned | Payload mode is new MCP-facing behavior. |
| R013-R019 | Invalid input modes, filenames, paths, proposals, and YAML fail safely. | Future service and MCP tests. | planned | Error behavior must avoid uncontrolled writes. |
| R020-R023 | Import tools do not decide proposals, update artifact coverage state, or replace prompt-only tools. | Future MCP handler payloads and regression tests. | planned | Governance and artifact-state separation remain explicit. |
| AC001-AC009 | Tool listing, source parity, payload import, validation, docs, and full validation. | Future implementation and validation commands. | planned | No task is marked complete from proposal text alone. |

## Task Completion Decisions

No implementation task was marked complete in this binding pass.

The created `tasks.md` is an implementation plan. Task completion requires
evidence from `src/`, `tests/`, `docs/`, or observed command behavior.

## Implementation Gaps

- MCP import tool definitions do not yet exist.
- MCP handler dispatch for artifact content import does not yet exist.
- Direct payload import helpers do not yet exist.
- MCP tests for import parity do not yet exist.
- MCP documentation for artifact content import does not yet exist.

## Owner Questions

No owner question is required to start the MVP implementation.

The chosen direction is:

- total MCP parity with existing controlled CLI import primitives;
- source path and direct payload support;
- generic arbitrary artifact import deferred.
