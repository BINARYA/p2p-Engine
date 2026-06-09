# Findings - PROP-088

- The gap is MCP parity for proposal artifact content imports, not the
  underlying artifact import service itself.
- The CLI currently exposes controlled import primitives for impact and
  exploration output.
- MCP exposes artifact coverage state tools, which are useful but do not write
  the long-form artifact contents that readiness evaluates.
- PROP-086 requires agents to stop when a needed public primitive is missing;
  therefore this gap is expected behavior today but blocks the intended
  artifact-aware agent workflow.
- The first implementation should reuse existing services instead of
  introducing a generic managed-file writer.

