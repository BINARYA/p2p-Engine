# P2PWorkspace Work Branch Helper Consolidation Design

## Decision

`work_branches` contains two YAML usage patterns:

- local manifest files, which can use `foundation.files`;
- branch-ref manifest content loaded as text, which should keep direct
  `yaml.safe_load`.

Only local file helpers are consolidated in this step.

## Implementation

- Replace `_yaml_dump` with `foundation.files.yaml_dump`.
- Replace tolerant local `_read_yaml_mapping` with
  `foundation.files.read_yaml_mapping_or_default`.
- Keep `yaml` import for branch-ref `safe_load` calls.
- Keep conflict marker and review suggestion helpers local to the Work branch
  lifecycle service.

## Compatibility

No public behavior changes are expected. Local Work manifest reads keep tolerant
fallback behavior; branch-ref manifest parsing remains unchanged.
