# P2PWorkspace Work Planning Helper Consolidation Design

## Decision

`services.work_planning` uses helper behavior equivalent to `foundation.files`:

- `_yaml_dump` matches `yaml_dump`.
- `_read_yaml_mapping` matches strict `read_yaml_mapping`.

The service does not require custom YAML error messages or tolerant fallback
behavior.

## Implementation

- Import `yaml_dump` and `read_yaml_mapping` from `foundation.files`.
- Keep existing local aliases so Work planning call sites do not change.
- Remove local YAML helper definitions and unused `yaml` import.

## Compatibility

No public behavior changes are expected. Work planning manifests keep the same
serialization and malformed YAML behavior.
