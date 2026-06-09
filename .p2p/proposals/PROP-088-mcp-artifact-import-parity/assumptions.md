# Assumptions - PROP-088

- Existing CLI import behavior for impact and exploration is the correct
  baseline for MCP parity.
- Artifact state remains separate from artifact content. Updating content does
  not automatically decide governance.
- P2P Engine should keep `.p2p/` mutations behind CLI or explicit MCP tools.
- Tests can exercise MCP handlers without requiring a hosted MCP deployment.

