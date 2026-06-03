# Spec Kit Plan Prompt

Use this content with `/speckit.plan`. Provide technical implementation choices derived from accepted P2P memory.

## Architecture / Operating Model

## Implementation Targets

local_cli

## Data Flow

Not specified yet.

## CLI/API Surface

Not specified yet.

## Storage / Artifacts

- Change Set metadata.

## Implementation Targets

local_cli

## Data Model

```yaml
entities:
- name: ChangeSet
  description: Operational package derived from accepted project intent.
- name: SoftwareSpec
  description: P2P-native normalized implementation-facing specification.
- name: ExportTarget:openspec
  description: Downstream export target.
- name: ExportTarget:speckit
  description: Downstream export target.
- name: PROP-072
  description: Concurrent Managed Work and Merge Decision Model

```

## Testing And Validation

## Criteria

- Change Set metadata is present and reviewable.

## Tests / Verification

- Not specified yet.

## Constraints

- Preserve P2P provenance.
- Do not introduce implementation scope not supported by accepted P2P memory.
