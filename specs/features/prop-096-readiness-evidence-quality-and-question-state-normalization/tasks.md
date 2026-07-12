# Tasks - PROP-096 Readiness Evidence Quality And Question State Normalization

## Status

`implemented`

## Implementation Rules

- Keep the fix focused on readiness evidence aggregation and question-state
  classification.
- Do not change readiness profile weights, thresholds, labels, or owner override
  policy.
- Do not introduce manual `.p2p` repair as a normal workflow.
- Prefer service tests over CLI tests unless CLI output changes.

## Tasks

- [x] T001. Re-read accepted `PROP-096`, this feature spec, readiness service,
      proposal question service, and quality policies before coding.
      - Covers: all requirements.
      - Output: implementation notes in final summary.

- [x] T002. Add a regression test for meaningful primary Acceptance Criteria
      combined with placeholder-only `execution-plan.md`.
      - Covers: R001-R003, R008-R010, AC001.
      - Expected file: `tests/test_readiness_service.py`.
      - Expected failing behavior before fix: `acceptance_criteria_quality`
        becomes `placeholder` or missing.

- [x] T003. Add regression tests proving missing or placeholder-only primary
      acceptance evidence still reports missing or placeholder.
      - Covers: R004-R007, R011, AC002.
      - Expected file: `tests/test_readiness_service.py`.

- [x] T004. Implement source-aware readiness evidence quality aggregation.
      - Covers: R001-R011, R017-R019.
      - Expected file: `src/p2p_engine/services/readiness.py`.
      - Completion: no concatenated placeholder-only supplemental text can
        downgrade meaningful primary evidence.

- [x] T005. Apply source-aware aggregation to `acceptance_criteria_quality`.
      - Covers: R008-R011.
      - Completion: `proposal.md` Acceptance Criteria is primary;
        `execution-plan.md` is supplemental.

- [x] T006. Review other composed readiness criteria and use the same helper
      where the same false-downgrade risk exists.
      - Covers: R001-R007.
      - Candidate criteria: `scope_boundaries`, `tradeoff_analysis`.
      - Completion: no broad scoring behavior change beyond composed-evidence
        safety.

- [x] T007. Add a regression test for an answered question already marked
      applied.
      - Covers: R012-R013, R015-R016, AC003.
      - Fixture: `state: answered`, `applied_to_proposal: true`, non-empty
        `applied_at`.
      - Expected result: not listed in `answered_not_applied`.

- [x] T008. Add a regression test proving ordinary answered unapplied questions
      still require apply.
      - Covers: R014-R016, AC004.
      - Fixture: `state: answered`, non-empty answer,
        `applied_to_proposal: false`.
      - Expected result: listed in `answered_not_applied` and handled by
        existing apply behavior.

- [x] T009. Implement already-applied question classification in readiness.
      - Covers: R012-R016.
      - Preferred file: `src/p2p_engine/services/readiness.py`.
      - Completion: durable applied marker is checked before generic answered
        classification.

- [x] T010. If read-time classification is insufficient, implement deterministic
      normalization in `ProposalQuestionService.reassess`.
      - Covers: R012-R016.
      - Expected file: `src/p2p_engine/services/proposal_questions.py`.
      - Constraint: normalize only records with `applied_to_proposal: true` and
        non-empty `applied_at`.
      - Result: read-time classification was sufficient; no mutation-based
        normalization was added.

- [x] T011. Run focused readiness and question tests.
      - Required:
        `.venv/bin/pytest tests/test_readiness_service.py`
        `.venv/bin/pytest tests/test_proposal_questions_service.py`

- [x] T012. Run public validation if CLI output changed; otherwise document why
      CLI validation is not required.
      - Conditional command:
        `./scripts/test-public.sh`

- [x] T013. Run full validation before declaring complete.
      - Required unless explicitly deferred:
        `./scripts/test-full.sh`

- [x] T014. Final review: confirm readiness profile defaults, schemas,
      thresholds, labels, and normal question apply behavior are unchanged.
      - Covers: out-of-scope protections.
