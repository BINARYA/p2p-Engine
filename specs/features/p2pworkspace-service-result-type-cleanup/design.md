# P2PWorkspace Service Result Type Cleanup Design

## Current State

Several result dataclasses are duplicated in `storage.filesystem` even though
they are already defined and returned by extracted services:

- `ProjectStateStatus`, `ProjectBriefPrompt` in `services.project_state`;
- `ProjectAssessment` in `services.project_assessment`;
- `RegistryStatus`, `RegistryView` in `services.registries`;
- `SoftwareSpecStatus`, `SoftwareSpecPrompt` in `services.software_spec`;
- `SoftwareSpecExportStatus`, `SoftwareSpecExportValidation` in
  `services.spec_export`;
- `RemoteProjectProfile` in `services.remote_profile`.

The duplicates make `P2PWorkspace` look like the owner of result models it no
longer constructs.

## Target State

`storage.filesystem` imports those result types from their owning services and
keeps only compatibility facade methods.

## Compatibility

The dataclasses have the same fields as the duplicate facade definitions. The
runtime objects already come from services, so this step should be a type
ownership cleanup with no output change.

## Verification

Run focused tests for the affected service groups, CLI/MCP smoke coverage, P2P
validation, and the full pytest suite.
