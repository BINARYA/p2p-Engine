# P2PWorkspace Foundation File Helper Extraction Design

## Decision

`storage.filesystem` still contains generic support functions that are not
runtime behavior of the `P2PWorkspace` facade:

- slug normalization
- YAML dumping
- YAML reading
- YAML mapping validation
- relative path formatting

These helpers belong in a small foundation module because they are pure,
side-effect-bounded utilities and can be reused later by other services.

## Implementation

- Add `p2p_engine.foundation.files` with:
  - `slugify`
  - `identity_slug`
  - `relative_to_root`
  - `yaml_dump`
  - `read_yaml`
  - `read_yaml_mapping`
- Update `storage.filesystem` imports and call sites.
- Keep `_duplicate_proposal_ids_message` in `storage.filesystem`, but make it
  use the foundation `relative_to_root` helper.
- Add focused tests in `tests/test_foundation_helpers.py`.

## Compatibility

The extracted functions preserve the current behavior exactly, including:

- empty slug fallback to `"project"`
- `identity_slug` raising `ValueError("Actor identity is required")`
- YAML dump using `sort_keys=False` and ASCII-safe output
- missing YAML files returning the supplied default
- invalid YAML mappings raising `ValueError("Invalid YAML mapping: <path>")`
