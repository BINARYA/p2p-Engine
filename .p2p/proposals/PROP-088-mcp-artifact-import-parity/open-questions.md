# Open Questions - PROP-088

## Answered

- Should the MVP include only impact and exploration import parity?
  Answer: yes. The MVP scope is limited to MCP parity for existing impact and
  exploration imports. A generic artifact import primitive is deferred until the
  specific import parity is proven and a stricter allowlist and validation model
  are designed.

## Still Open

- Should clarification import parity be included in the same proposal?
  Recommended answer: include it only if the implementation can reuse the
  existing `clarify import` service without broadening scope.
- Should MCP support direct content strings or source paths for imports?
  Recommended answer: prefer the narrowest shape that fits stdio MCP clients and
  preserves validation/audit clarity.

