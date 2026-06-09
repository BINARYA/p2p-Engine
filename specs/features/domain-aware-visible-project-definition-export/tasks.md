# Tasks - Domain-Aware Visible Project Definition Export

- [x] T001: Update local feature specs to match accepted `PROP-083`; completion
  is requirements/design/tasks naming `outputs/latest/project.md`, review
  snapshots, nested profile exports, and compatibility boundaries.
- [x] T002: Add visible project export service; completion is a service that
  renders `project.md`, creates `outputs/latest/`, and archives previous latest
  into `outputs/review-###/`.
- [x] T003: Wire `P2PWorkspace` facade methods; completion is delegation without
  adding rendering logic to `filesystem.py`.
- [x] T004: Add project CLI commands; completion is `p2p project export` and
  `p2p project export-status`.
- [x] T005: Add MCP project export/status tools if project MCP handlers support
  the needed surface; completion is registry/catalog/handler coverage.
- [x] T006: Add tests for service and CLI visible export behavior, including
  first export, second export review snapshot, and status.
- [x] T007: Add or update MCP tests if MCP tools are implemented.
- [x] T008: Update CLI/MCP docs to describe visible project export as the
  default project definition output and spec export as compatibility/software
  handoff.
- [x] T009: Verify legacy spec export compatibility tests still pass.
- [x] T010: Run `p2p validate` and focused pytest; completion is recorded output
  in the final implementation note.
- [x] T011: Record follow-up work for proactive skill/readiness calculation
  revision after implementation.
