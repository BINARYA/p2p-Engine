# Implementation Note - Proposal Artifact State Readiness

## Evidence Summary

- Code implements artifact state as a dedicated domain/service layer:
  `src/p2p_engine/core/proposal_artifact_state.py` and
  `src/p2p_engine/services/proposal_artifact_state.py`.
- `P2PWorkspace` exposes facade delegation only; CLI and MCP handlers delegate
  through the workspace/service boundary.
- New proposals initialize `artifact-state.yml` by default through the engine
  write path. Existing proposals without state read as advisory
  `absent_legacy`.
- Readiness, compact context, validation, generated agent instructions, CLI
  docs, MCP docs, and agent integration docs consume or describe the new state.
- Focused tests passed: service, CLI, readiness, context, validation, MCP
  handler, MCP registry, and agent instructions.
- Full test suite passed: `402 passed`.
- P2P validation passed: `errors: 0`, `warnings: 0`, `infos: 0`.

## Existing Import Workflows

`ProposalArtifactService.import_exploration`, `import_artifact`, and
`import_impact` remain compatibility behavior for existing public local CLI
workflows. They are explicit engine operations, not an agent-side workaround.

The artifact-state feature does not introduce a workflow where an agent prepares
a temporary file and copies it into `.p2p` as the mutation surface. Agents must
use `p2p proposal artifact ...`, existing public import commands, or explicit
write-safe MCP tools. If a future remote MCP client needs to import large
generated proposal content, the correct extension is a dedicated MCP/CLI import
primitive backed by the engine, not direct file copying or reverse-engineered
proposal paths.

## Follow-Up Boundary

No follow-up is required to complete this feature slice. A future proposal may
standardize remote-safe import/update tools for large proposal artifacts if MCP
clients need parity with the current local CLI import commands.
