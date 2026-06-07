# P2PWorkspace Spec Export Renderer Service Ownership Design

## Current State

`SpecExportService` owns export orchestration but still receives target
renderers, required-file calculators, show-file selection, and project
definition section lists from `storage.filesystem`.

This keeps a large block of export-specific helper functions in
`P2PWorkspace`, even though the runtime behavior has already been delegated to a
service.

## Target State

`SpecExportService` becomes the owner of:

- supported export targets;
- target artifact names;
- target required-file validation;
- target show-file selection;
- project definition required sections;
- generic, OpenSpec, and Spec Kit prompt renderers;
- project-definition rendering helpers.

`P2PWorkspace` remains responsible only for wiring repository-specific data
providers into the service.

## Compatibility

The refactor preserves:

- `.p2p/outputs/spec-export/<CHANGE>/<target>/` output paths;
- `generic/project.md` and `generic/propose.md`;
- `openspec/propose.md`;
- `speckit/speckit.constitution.md`, `speckit/speckit.specify.md`, and
  `speckit/speckit.plan.md`;
- current validation behavior for generic sections and source traceability.

## Cleanup Boundary

After moving active export helpers, remove only helpers that are proven unused by
`rg`:

- legacy export helper functions no longer called by service or tests;
- duplicated software-spec renderer helpers now implemented inside
  `SoftwareSpecService`.

Do not remove shared low-level filesystem helpers that are still used by
remaining `P2PWorkspace` compatibility behavior.
