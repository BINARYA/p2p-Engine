# Findings - PROP-089

- In PROP-088, `questions.yml` records Q001 as `applied`, but readiness still
  reports `owner_questions_resolution:needs_owner_input`.
- `readiness.assess` uses `count_open_questions(open-questions.md)` as a
  blocker source even when structured question state exists.
- `count_open_questions` counts any bullet line ending in `?`, including
  historical answered questions and recommended questions in prose.
- `_pending_high_questions` only counts structured high-priority questions in
  `to_answer` or `answered` states; medium and low priority structured questions
  do not affect that counter.
- `readiness.review` can report `owner_questions: none` while readiness still
  has a failed gate, which is confusing for agents and owners.
- The design for proposal readiness review says applied question answers should
  be evidence for owner-question resolution, so implementation and design are
  not fully converged.

Relevant implementation areas:

- `src/p2p_engine/services/readiness.py`
- `src/p2p_engine/services/proposal_questions.py`
- `tests/test_readiness_service.py`
- `tests/test_proposal_questions_service.py`

