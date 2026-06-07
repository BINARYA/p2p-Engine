# P2PWorkspace Foundation Helper Service Consolidation 5 Design

## Decision

`changes` and `intake` both use strict YAML mapping readers whose behavior
matches `foundation.files.read_yaml_mapping`.

`changes` also uses a slug helper with fallback `"item"`, which maps to
`foundation.files.slugify(value, fallback="item")`.

`project_maturity` remains excluded because it raises
`ValueError("YAML document must be a mapping: <path>")`, which is not equivalent
to the foundation strict helper message.

## Implementation

- Replace local YAML helpers in `changes` and `intake` with foundation imports.
- Replace local `changes` slug helper with a local alias around foundation
  `slugify(..., fallback="item")`.
- Remove unused `yaml` imports.
- Keep call sites unchanged where possible.

## Compatibility

No public behavior changes are expected. YAML serialization, YAML strict read
semantics, and `changes` slug fallback remain unchanged.
