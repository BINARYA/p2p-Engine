# P2PWorkspace Foundation Helper Service Consolidation 2 Design

## Decision

The second consolidation tranche should keep behavioral compatibility by
separating two helper contracts:

- `read_yaml_mapping`: strict; raises on non-mapping YAML.
- `read_yaml_mapping_or_default`: tolerant; returns the supplied default or `{}`
  when the file is missing or not a mapping.

`remote_profile`, `permissions`, and `consent` currently use the tolerant
contract. `project_state` only needs YAML dumping and can use `yaml_dump`
directly.

## Implementation

- Add `read_yaml_mapping_or_default` to `foundation.files`.
- Add focused foundation tests for missing, mapping, and non-mapping YAML input.
- Update selected services to import:
  - `yaml_dump`
  - `read_yaml_mapping_or_default`
  - `identity_slug` where applicable
- Remove duplicated helper definitions and unused imports from selected services.

## Compatibility

The following behaviors must remain unchanged:

- malformed/non-mapping permissions, consent, or project remote YAML reads fall
  back to the provided default instead of raising;
- permissions identity slug still raises `ValueError("Actor identity is required")`;
- YAML output still uses `sort_keys=False` and ASCII-safe serialization.
