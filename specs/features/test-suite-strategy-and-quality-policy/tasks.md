# Tasks - test-suite-strategy-and-quality-policy

- [x] T001: Create a current suite inventory for R001; completion is a checked-in
  note or docs section with test file count, collected test count, runtime, and
  largest/slowest areas.
- [x] T002: Define the initial marker taxonomy for R002; completion is marker
  names and intended use cases reviewed against the current test suite.
- [x] T003: Register pytest markers in `pyproject.toml` for R002/N005;
  completion is pytest collecting without unknown-marker warnings.
- [x] T004: Draft `specs/skills/TEST_QUALITY_SKILL.md` for R006-R015; completion
  is a policy covering test layer selection, duplication rules, public-surface
  tests, slow/integration tests, and validation evidence.
- [x] T005: Update `AGENTS.md` and `AGENTS-p2p-dev-specs.md` for R015;
  completion is local instructions directing future agents to apply the test
  quality skill when adding, changing, or reviewing tests.
- [x] T006: Add `docs/TESTING.md` for R003-R005/R013; completion is documented
  focused, public-contract, smoke, and full-suite commands.
- [x] T007: Add optional validation scripts for R003-R005; completion is scripts
  that wrap the documented focused, public-contract, smoke, and full-suite
  pytest commands without changing test behavior.
- [x] T008: Apply markers to service/unit/adapter tests for R002/R010;
  completion is focused marker commands collecting the expected test families.
- [x] T009: Apply markers to CLI and MCP tests for R002/R008/R009; completion is
  public-contract marker commands collecting the expected public-surface tests.
- [x] T010: Apply `git`, `integration`, `slow`, and `smoke` markers where
  applicable for R011/E001-E003; completion is documented examples for combined
  markers.
- [x] T011: Review `tests/test_cli.py` for R012; completion is either a justified
  split plan or a written decision to keep it intact with markers.
- [x] T012: Resolve the `tests/test_cli.py` split decision from T011; completion
  is either a justified behavior-preserving split or a written decision to keep
  the file intact with markers.
- [x] T013: Review `tests/test_mcp.py` for R012; completion is either a justified
  split plan or a written decision to keep it intact with markers.
- [x] T014: Resolve the `tests/test_mcp.py` split decision from T013; completion
  is either a justified behavior-preserving split or a written decision to keep
  the file intact with markers.
- [x] T015: Update `specs/features/_template/tasks.md` for R006/R013; completion
  is a task-template prompt for focused test commands and broad validation
  evidence.
- [x] T016: Add a test-suite policy implementation note; completion is a concise
  summary of marker decisions, script decisions, files split, and residual
  risks.
- [x] T017: Run focused marker validation for R003; completion is command output
  reviewed and recorded in the implementation note.
- [x] T018: Run public-contract validation for R004; completion is command output
  reviewed and recorded in the implementation note.
- [x] T019: Run the full suite for R005/AC008; completion is full-suite command
  output reviewed and recorded in the implementation note.
- [x] T020: Review the final feature against
  `specs/skills/ENGINEERING_QUALITY_SKILL.md`; completion is confirmation that
  the work preserved public behavior, avoided opportunistic cleanup, and kept
  test changes scoped.
