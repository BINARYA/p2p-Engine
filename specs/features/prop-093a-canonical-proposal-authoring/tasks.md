# PROP-093A Canonical Proposal Authoring Tasks

## Status

`implemented`

## Implementation Rules

- Keep changes scoped to proposal authoring and contribution contracts.
- Do not manually edit `.p2p/` state.
- Do not delete or rewrite existing proposal artifacts.
- Preserve existing CLI and MCP commands unless an additive option is required.
- Add tests before or with each behavior change.

## Tasks

- [x] A1. Inspect current proposal creation tests and identify assertions that
      depend on the exact placeholder exploration file list.

- [x] A2. Add a focused service test proving that a newly created proposal does
      not create editable-looking empty narrative artifact placeholders.

- [x] A3. Add a compatibility service test proving that an existing proposal
      with legacy narrative artifact files is still readable.

- [x] A4. Update `ProposalDocumentService` scaffold generation so new proposals
      omit empty narrative placeholders while preserving required core files.

- [x] A5. Add tests proving prompt/exploration/readiness context tolerates
      missing narrative artifact files.

- [x] A6. Update proposal artifact services only where needed so missing
      optional narrative artifacts are treated as normal states.

- [x] A7. Add contribution model tests for the target contribution concepts:
      finding, open question, alternative, risk, assumption, constraint,
      objection, implementation suggestion, and scope boundary.

- [x] A8. Extend `ContributionType` with additive values or explicit aliases
      while preserving all existing persisted values.

- [x] A9. Update contribution service validation so invalid contribution types
      report the allowed values.

- [x] A10. Add CLI tests for new contribution types and invalid type errors.

- [x] A11. Update CLI contribution command help and parsing to use the shared
       contribution type contract.

- [x] A12. Add MCP catalog or handler tests that assert contribution type
       schema parity with the core contribution model.

- [x] A13. Update MCP proposal contribution schemas and handlers to accept the
       same allowed contribution types as CLI.

- [x] A14. Add CLI test coverage for proposal create output guidance.

- [x] A15. Update proposal create/post-create output so it points to canonical
       P2P commands instead of direct `.p2p/` edits.

- [x] A16. Update documentation for the canonical proposal-authoring flow and
       explain why narrative artifacts may be absent.

- [x] A17. Run focused validation for proposal document service, proposal
       artifact service, contribution CLI, and MCP proposal tests.

- [x] A18. Run broader public-surface validation for CLI and MCP proposal
       workflows.

- [x] A19. Record validation evidence in the implementation notes or final
       development summary.

## Implementation Notes

- New proposal scaffolds no longer create empty narrative exploration
  placeholders: `exploration.md`, `findings.md`, `alternatives.md`,
  `open-questions.md`, `risks.md`, `assumptions.md`, and
  `suggested-scope.md`.
- Legacy/imported narrative artifacts remain readable through prompt and
  exploration artifact services.
- Contribution types are additive: existing persisted values remain accepted,
  and canonical authoring concepts now share one core validation contract across
  service, CLI, and MCP.
- CLI `proposal create` now prints canonical next-step commands instead of
  encouraging direct `.p2p/` file editing.
- Documentation updated in `docs/CLI-GUIDE.md`, `docs/MCP.md`, and
  `docs/GLOSSARY.md`.

## Validation Evidence

- `.venv/bin/pytest tests/test_contribution_model.py tests/test_proposal_document_service.py tests/test_proposal_artifact_service.py tests/test_skeleton.py`
  - Result: 32 passed.
- `.venv/bin/pytest tests/test_mcp_proposal_handler.py tests/test_mcp.py::test_mcp_proposal_contribution_schema_matches_core_types tests/test_mcp.py::test_mcp_proposal_contribution_add_does_not_decide tests/test_cli.py::test_cli_init_status_create_and_prompt_flow tests/test_cli.py::test_cli_lists_proposal_contributions tests/test_cli.py::test_cli_accepts_canonical_contribution_types_and_reports_allowed_invalid_type`
  - Result: 15 passed.
- `.venv/bin/pytest tests/test_mcp.py tests/test_mcp_proposal_handler.py`
  - Result: 69 passed.
- `.venv/bin/pytest tests/test_cli.py`
  - Result: 106 passed.
- `git diff --check`
  - Result: passed.
