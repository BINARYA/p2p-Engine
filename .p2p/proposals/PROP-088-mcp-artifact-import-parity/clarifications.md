# Clarifications - PROP-088

- The observed issue is not that MCP cannot write at all. MCP can create draft
  proposals, update proposal sections, refresh registries, and set artifact
  coverage state.
- The missing capability is controlled import or update of long-form proposal
  artifact content through MCP.
- CLI import primitives already exist for at least impact and exploration
  outputs, so the first target is MCP parity with those commands.
- This proposal should not add arbitrary `.p2p/` file writes.
- Owner governance decisions remain separate from artifact content import.

