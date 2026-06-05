# Tasks - Domain-Aware Visible Project Definition Export

- [ ] T001: Inspect current CLI, MCP, docs, and skill references to
  `software-spec`; completion is a list of affected files in the implementation
  notes.
- [ ] T002: Define the visible root-level output directory name and generated
  file conflict policy; completion is an update to this design spec.
- [ ] T003: Add project-level generic export generation; completion is a CLI path
  that writes `generic/project.md` without requiring a Change Set.
- [ ] T004: Add domain/profile gating for OpenSpec and Spec Kit; completion is
  non-software projects rejecting those targets by default.
- [ ] T005: Update CLI help text away from default `software-spec` language;
  completion is help output matching the domain-aware workflow.
- [ ] T006: Update MCP tools or descriptions if project export is exposed
  through MCP; completion is MCP tests covering the updated behavior.
- [ ] T007: Update agent skills and public docs to recommend project definition
  export rather than Change Set software-spec export by default.
- [ ] T008: Add or update CLI tests for generic export, target gating, and
  visible root-level output.
- [ ] T009: Run focused tests for CLI and MCP; completion is reviewed test
  output.
- [ ] T010: Review legacy `p2p spec` behavior and document whether it remains
  software-only compatibility or becomes deprecated.

## Current Binding Status

No task in this feature is marked complete from `src/` evidence yet.

The current implementation still exposes the Change Set based software-spec
workflow through `src/p2p_engine/cli.py:2340`, `src/p2p_engine/cli.py:2412`,
and `src/p2p_engine/storage/filesystem.py:3964`. That behavior is tracked as
implemented legacy behavior in `specs/features/legacy-software-spec-export/`.
