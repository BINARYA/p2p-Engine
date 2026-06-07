# P2PWorkspace Project Maturity Helper Consolidation Design

## Decision

`project_maturity` can use `foundation.files` if the strict YAML mapping helper
supports an optional custom error message. The default behavior remains:

`Invalid YAML mapping: <path>`

`project_maturity` will call the same helper with:

`YAML document must be a mapping: <path>`

## Implementation

- Extend `read_yaml_mapping(path, default, *, error_message=None)`.
- Add focused foundation tests for default and custom error messages.
- Replace `project_maturity` local YAML helpers with foundation imports.
- Use a local wrapper only to bind the custom error message and keep call sites
  unchanged.

## Compatibility

The default helper contract remains backward-compatible. `project_maturity`
preserves its distinct error text.
