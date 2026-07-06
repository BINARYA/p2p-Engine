# Implementation Note - MCP Artifact Import Parity

## Design Choice

Implemented explicit write-safe MCP import tools for the existing controlled
proposal artifact import workflows:

- `p2p_explore_import`
- `p2p_impact_import`
- `p2p_clarify_import`
- `p2p_synthesize_import`
- `p2p_plan_import`
- `p2p_tasks_import`

The implementation keeps target mapping and validation in
`ProposalArtifactService`, with `P2PWorkspace` acting only as a compatibility
facade. MCP handlers parse arguments, delegate to the facade, and return
structured payloads.

## Compatibility Impact

- CLI import behavior is unchanged.
- Existing MCP tools and payloads are unchanged.
- New MCP tools are additive.
- `.p2p` proposal artifact filenames and layout are unchanged.
- Artifact coverage state remains separate from artifact content import.

## Behavior Changes

- MCP clients can import proposal artifact content from a source path.
- Relative MCP `source` paths resolve from the project root.
- MCP clients can import direct `content` payloads for the primary fixed target.
- MCP clients can import allowlisted multi-file `artifacts` payloads for
  exploration and impact.
- Import calls require exactly one input mode: `source`, `content`, or
  `artifacts`.
- Impact YAML and tasks YAML validation is preserved for MCP imports.
- Import results include proposal ID, import kind, input mode, imported paths,
  filenames, validation flags, and `artifact_state_updated: false`.
- Import tools do not accept, reject, defer, merge, publish, finalize, or decide
  proposals.

## Files Changed

- `src/p2p_engine/services/proposal_artifacts.py`
- `src/p2p_engine/storage/filesystem.py`
- `src/p2p_engine/mcp/catalog/proposals.py`
- `src/p2p_engine/mcp/registry.py`
- `src/p2p_engine/mcp/handlers/proposals.py`
- `tests/test_proposal_artifact_service.py`
- `tests/test_mcp_proposal_handler.py`
- `tests/test_mcp_registry.py`
- `tests/test_mcp.py`
- `docs/MCP.md`
- `specs/features/mcp-artifact-import-parity/tasks.md`

## Tests Run

```bash
.venv/bin/pytest tests/test_proposal_artifact_service.py
.venv/bin/pytest tests/test_mcp_proposal_handler.py tests/test_mcp_registry.py
.venv/bin/pytest tests/test_mcp.py
.venv/bin/p2p validate
.venv/bin/pytest
```

Results:

```text
tests/test_proposal_artifact_service.py: 9 passed
tests/test_mcp_proposal_handler.py tests/test_mcp_registry.py: 16 passed
tests/test_mcp.py: 58 passed
p2p validate: errors 0, warnings 0, infos 0
full pytest: 509 passed
```

## Residual Risks

- The new MCP tools are intentionally additive; clients that list all tools may
  need to classify these as write-safe artifact content imports.
- `artifacts` mode remains limited to exploration and impact by design.
- Generic arbitrary proposal artifact import remains unsupported.

## Follow-Ups

- No separate follow-up is needed for the accepted `PROP-088` MVP scope.
- A future proposal is still required before adding generic arbitrary artifact
  imports, automatic artifact coverage-state updates, or consent-gated import
  semantics.
