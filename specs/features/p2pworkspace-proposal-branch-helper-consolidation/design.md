# P2PWorkspace Proposal Branch Helper Consolidation Design

## Decision

`proposal_branches` contains two YAML usage patterns:

- local metadata files, which can use `foundation.files`;
- branch-ref metadata content loaded as text, which should keep direct
  `yaml.safe_load`.

Only local file helpers are consolidated in this step.

## Implementation

- Replace `_yaml_dump` with `foundation.files.yaml_dump`.
- Replace local tolerant `_read_yaml_mapping` with
  `foundation.files.read_yaml_mapping_or_default`.
- Replace local `_slugify` with a wrapper over
  `foundation.files.slugify(value, fallback="")`.
- Keep the `yaml` import because branch-ref content parsing still uses
  `yaml.safe_load`.

## Compatibility

No public behavior changes are expected. Empty proposal branch slugs still
return `""`, allowing existing call-site fallbacks to apply.
