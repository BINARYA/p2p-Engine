# PROP-093B Artifact Status And Owner View Tasks

## Status

`draft`

## Implementation Rules

- Implement after or alongside `PROP-093A` reduced proposal scaffolding.
- Keep default `proposal show` behavior compatible.
- Treat all view/status operations as read-only.
- Do not create files to make artifact status look uniform.
- Keep readiness and artifact status conceptually separate.

## Tasks

- [x] B1. Inspect existing proposal artifact state tests and identify coverage
      gaps for reduced-footprint and legacy proposals.

- [x] B2. Add service tests for a logical artifact catalog that lists expected
      artifact slots when optional files are absent.

- [x] B3. Add service tests for legacy proposals that already contain narrative
      artifact files.

- [x] B4. Add service tests for proposals with imported artifacts.

- [x] B5. Define or extend the artifact catalog view model with expectation,
      status, provenance, path, summary, and next-action fields.

- [x] B5a. Define stable public view-model values for materialization,
      source hints, and provenance confidence while reusing existing
      expectation/status enums where they already express the state.

- [x] B5b. Define question grouping in the full-view model for structured
      owner questions, analytical open-question contributions, and legacy
      `open-questions.md` artifacts.

- [x] B6. Update the artifact state service or introduce a cohesive catalog
      service that derives the view without mutating files.

- [x] B6a. Add service tests proving artifact status and readiness remain
      separate and may diverge without either overriding the other.

- [x] B7. Add tests proving artifact status rendering does not create, update,
      or delete proposal files.

- [x] B7a. Strengthen read-only tests with file-list preservation and content
      hash, mtime, or equivalent non-mutation checks for existing files.

- [x] B8. Add service tests for a full proposal view containing proposal body,
      decision, readiness, contributions, narrative artifacts, artifact status,
      grouped questions, and next actions.

- [x] B8a. Add service or CLI tests proving long narrative/imported artifacts
      are summarized or clipped in owner-facing full view output.

- [x] B9. Implement a proposal full-view service or extend an existing service
      behind a cohesive boundary.

- [x] B10. Add CLI tests proving default `p2p proposal show PROP-XXX` remains
       compatible.

- [x] B11. Add CLI tests for the explicit full view surface, preferably
       `p2p proposal show PROP-XXX --full`.

- [x] B12. Implement the CLI full view renderer using the service-level view
       model.

- [x] B13. Add MCP schema/handler tests for read-only artifact status and full
       proposal view parity.

- [x] B13a. Add MCP tests for structured full-view fields and stable public
       values, including artifact status, materialization/provenance, question
       groups, and next actions.

- [x] B14. Implement MCP read-only parity through a `full` argument on an
       existing show tool or a dedicated full-view tool.

- [x] B15. Update documentation to explain logical artifact status, physical
       file footprints, and owner full review.

- [x] B15a. Document that displayed proposal artifact paths are backing
       evidence/source hints, not direct edit targets.

- [x] B16. Run focused validation for artifact state service, full-view service,
       CLI proposal show, and MCP proposal tools.

- [x] B17. Run broader public-surface validation for proposal workflows.

- [x] B18. Record validation evidence in the implementation notes or final
       development summary.

## Implementation Notes

- Added `ProposalReviewViewService` as the cohesive read-only view boundary for
  logical artifact catalog and owner-facing full proposal view.
- Added `P2PWorkspace.proposal_artifact_catalog()` and
  `P2PWorkspace.proposal_full_view()` facade methods.
- Added `p2p proposal show PROP-XXX --full` while preserving default
  `proposal show` output.
- Extended MCP `p2p_proposal_show` with `full: true` and extended
  `p2p_proposal_artifact_status` with structured `artifact_status` catalog
  output while preserving existing `artifact_state`.
- Documented logical artifact status, full owner review, grouped question
  sources, and evidence/source path semantics.

## Validation Evidence

- `.venv/bin/python -m pytest tests/test_proposal_review_view_service.py`
  - 6 passed.
- `.venv/bin/python -m pytest tests/test_mcp_proposal_handler.py`
  - 10 passed.
- `.venv/bin/python -m pytest tests/test_cli.py -k "proposal_list_show_and_choice_registry_output"`
  - 1 passed.
- `.venv/bin/python -m pytest tests/test_mcp.py -k "tool_definitions_expose_agent_safe_surface"`
  - 1 passed.
- `.venv/bin/python -m pytest tests/test_proposal_review_view_service.py tests/test_proposal_artifact_state_service.py tests/test_proposal_artifact_service.py`
  - 24 passed.
- `.venv/bin/python -m pytest tests/test_mcp_proposal_handler.py tests/test_mcp.py`
  - 69 passed.
- `.venv/bin/python -m pytest tests/test_cli.py`
  - 106 passed.
