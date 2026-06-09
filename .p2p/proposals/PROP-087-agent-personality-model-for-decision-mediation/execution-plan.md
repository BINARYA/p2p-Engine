# Execution Plan - PROP-087

## Implementation Slices

1. Add a project-level interaction style domain model with:
   - `technical_verbosity`
   - `formality`
   - `assertiveness`
   - defaults `2`, `2`, and `0`
   - validation for integer values from `0` to `5`

2. Add project workspace/service support:
   - read current interaction style
   - initialize/fallback defaults when missing
   - update values with validation
   - preserve backward compatibility for existing projects

3. Add CLI surface:
   - `p2p project interaction-style show`
   - `p2p project interaction-style set`
   - actionable validation errors for invalid values

4. Add MCP surface:
   - read-only project interaction style status tool
   - write-safe project interaction style update tool
   - descriptions that clarify no governance decision side effects

5. Update generated agent instructions and local/project skills:
   - explain how to inspect style
   - explain how to update style
   - state that direct `.p2p` edits are not allowed
   - render numeric values into concrete communication behavior

6. Add validation and tests:
   - defaults and missing-config fallback
   - value bounds
   - CLI show/set behavior
   - MCP read/update behavior
   - generated instruction content
   - no persisted named presets

## Completion Criteria

- Existing projects without interaction style remain valid.
- New or refreshed generated instructions include project interaction style
  guidance.
- CLI and MCP expose the same source-of-truth behavior.
- Interaction style changes do not alter readiness truth, validation results,
  permissions, governance decisions, or audit requirements.
