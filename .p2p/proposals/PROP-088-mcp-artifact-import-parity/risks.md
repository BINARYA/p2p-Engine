# Risks - PROP-088

- A generic import tool could become an arbitrary write API for managed P2P
  state if it is not narrowly allowlisted.
- MCP clients may not share filesystem assumptions with CLI users; import input
  shape must be explicit and testable.
- Import tools that bypass existing validation would weaken artifact readiness.
- Documentation drift could make agents believe unsupported artifact writes are
  allowed.

Mitigation: start with existing import services, keep unsupported artifact kinds
explicitly rejected, and document the boundary in the MCP tool matrix.

