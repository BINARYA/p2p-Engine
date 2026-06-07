# P2PWorkspace Spec Export Renderer Service Ownership Requirements

## Goal

Move spec-export rendering ownership out of `P2PWorkspace` compatibility helpers
and into `SpecExportService`.

## Requirements

- `SpecExportService` must be usable without renderer callbacks supplied by
  `storage.filesystem`.
- Generic, OpenSpec, and Spec Kit prompt exports must preserve the current
  generated artifact names and content semantics.
- Generic export validation must keep the required project definition section
  checks and source traceability check.
- `P2PWorkspace` may continue to inject workspace data providers such as Change
  Set lookup, accepted proposal records, status, and proposal summaries.
- `P2PWorkspace` must not keep duplicated software-spec renderer helpers that
  are already implemented in `SoftwareSpecService`.
- The refactor must not change public CLI, MCP, or storage output paths.

## Non-Goals

- Do not change `.p2p/outputs/` layout in this implementation slice.
- Do not introduce new export targets.
- Do not implement root-level project export behavior here.
- Do not alter P2P governance state manually.

## Verification

- Focused unit coverage for `SpecExportService`.
- Focused CLI regression coverage for spec export commands.
- Full pytest suite.
- `p2p validate`.
