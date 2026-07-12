# Findings

- Readiness currently applies placeholder detection to concatenated evidence.
  That makes a weak supplemental artifact capable of downgrading a meaningful
  primary section.
- The Acceptance Criteria criterion is especially exposed because it combines
  the `proposal.md` section with `execution-plan.md`.
- The proposal question workflow has two related signals: `state` and
  `applied_to_proposal`. When they disagree, readiness and apply can disagree
  about whether a question is still actionable.
- The bug is reproducible without broad project state: a focused service test
  can construct a proposal with meaningful acceptance criteria, add a
  placeholder-only execution plan, run readiness assessment, and assert that the
  criterion is not classified as placeholder.
- A second focused test can construct a question state where `state` is
  `answered`, `applied_to_proposal` is true, and `applied_at` is present, then
  assert that readiness does not report `answered_not_applied` after the
  supported normalization behavior.
- The fix should not make placeholder detection less strict for primary
  evidence. A proposal whose primary evidence is absent or placeholder-only
  should still receive missing or placeholder findings.
