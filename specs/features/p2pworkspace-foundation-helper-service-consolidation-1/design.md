# P2PWorkspace Foundation Helper Service Consolidation 1 Design

## Decision

The first consolidation tranche should touch small, well-tested services whose
local helpers are exact equivalents of `foundation.files`:

- `_yaml_dump` -> `foundation.files.yaml_dump`
- `_read_yaml` -> `foundation.files.read_yaml`
- `_read_yaml_mapping` -> `foundation.files.read_yaml_mapping`

`services.next_actions` keeps its `re` import because it is used by action ID
generation and validation logic.

## Implementation

- Import foundation helpers with local aliases matching the existing call sites.
- Remove local duplicate helper definitions.
- Remove `yaml` imports where they become unused.
- Keep service code call sites unchanged to reduce behavioral risk.

## Compatibility

The shared helpers preserve the same behavior as the removed service-local
helpers:

- missing files return the supplied default;
- YAML dumps use `sort_keys=False` and ASCII-safe output;
- non-mapping YAML raises `ValueError("Invalid YAML mapping: <path>")`.
