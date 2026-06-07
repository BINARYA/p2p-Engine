# P2PWorkspace Spec Export Renderer Service Ownership Tasks

## Phase 1: Reference Audit

- [x] T001 Identify spec-export callbacks still injected by `P2PWorkspace`.
- [x] T002 Identify software-spec helper duplicates that are no longer used.
- [x] T003 Confirm test coupling to filesystem-level export helpers.

## Phase 2: Service Ownership

- [x] T004 Move export target, required-file, show-file, and required-section
      behavior into `SpecExportService`.
- [x] T005 Move active project-definition and prompt renderers into
      `SpecExportService`.
- [x] T006 Keep `P2PWorkspace` wiring limited to data providers.

## Phase 3: Cleanup

- [x] T007 Remove unused filesystem export helper functions.
- [x] T008 Remove unused duplicate filesystem software-spec renderer helpers.
- [x] T009 Update tests to instantiate `SpecExportService` without filesystem
      renderer callbacks.

## Phase 4: Verification

- [x] T010 Run focused spec export and software spec service tests.
- [x] T011 Run focused CLI spec/export regression tests.
- [x] T012 Run `p2p validate`.
- [x] T013 Run the full pytest suite.
- [x] T014 Update the refactoring status tracker with the completed step and
      remaining concentration.
