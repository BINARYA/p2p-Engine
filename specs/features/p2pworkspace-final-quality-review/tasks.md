# P2PWorkspace Final Quality Review Tasks

## Tasks

### Phase 1 - Tracking

- [x] T001: Create local final quality review feature files under
  `specs/features/p2pworkspace-final-quality-review/`.

### Phase 2 - Dead Code And Import Review

- [x] T002: Run static import/dead-code checks available in the local
  environment.
- [x] T003: Inspect static-check findings and classify required fixes versus
  false positives.
- [x] T004: Apply only required cleanup fixes that do not alter public behavior.

### Phase 3 - MCP Catalog Readability

- [x] T005: Identify MCP catalog files or registry literals with non-readable
  long dictionary/tuple lines.
- [x] T006: Reformat MCP catalog definitions and large registry literals without
  changing tool contracts.
- [x] T007: Verify MCP registry tests cover tool ordering and schema
  preservation.

### Phase 4 - Residual Sensitive File Review

- [x] T008: Review `src/p2p_engine/storage/filesystem.py` as compatibility
  facade and composition root.
- [x] T009: Review `src/p2p_engine/services/work_branches.py` as cohesive Work
  branch lifecycle service.
- [x] T010: Review `src/p2p_engine/services/proposal_branches.py` as cohesive
  proposal branch lifecycle service.
- [x] T011: Record required cleanup findings or future evolution candidates.

### Phase 5 - MCP Consent And Owner-Controlled Flow Review

- [x] T012: Review `src/p2p_engine/mcp/handlers/collaboration_proposals.py`.
- [x] T013: Review consent audit helper behavior in
  `src/p2p_engine/mcp/consent_audit.py`.
- [x] T014: Confirm proposal collaboration MCP flows do not bypass consent,
  audit, or owner-controlled operation boundaries.

### Phase 6 - Final Validation

- [x] T015: Run `.venv/bin/p2p validate`.
- [x] T016: Run the full automated test suite.
- [x] T017: Record final validation result.

### Phase 7 - Working Tree And Commit Strategy

- [x] T018: Review working tree scope after cleanup.
- [x] T019: Recommend a reviewable commit strategy for the refactoring branch.

### Phase 8 - Future Evolutions

- [x] T020: Record non-blocking future evolution candidates in
  `future-evolutions.md`.
