# Design - PROP-096 Readiness Evidence Quality And Question State Normalization

## Overview

PROP-096 fixes readiness false positives without changing governance policy or
readiness scoring thresholds.

The implementation should touch two narrow areas:

- readiness evidence quality aggregation in `src/p2p_engine/services/readiness.py`;
- structured owner question classification or normalization in readiness and, if
  needed, `src/p2p_engine/services/proposal_questions.py`.

## Key Decisions

### D001 - Score Evidence Sources Separately

Replace concatenation-based quality checks for composed criteria with
source-aware aggregation.

Current shape to avoid:

```python
acceptance_text = proposal_acceptance + "\n" + execution_plan
quality = readiness_text_quality(acceptance_text)
```

Preferred shape:

```python
primary_quality = readiness_text_quality(proposal_acceptance)
supplemental_quality = readiness_text_quality(execution_plan)
quality = aggregate_evidence_quality(primary_quality, supplemental_quality)
```

Rationale: a placeholder-only supplemental file should not downgrade meaningful
primary evidence.

Satisfies: R001-R011.

### D002 - Preserve Strict Placeholder Detection

The aggregation rule must not make readiness optimistic.

Recommended aggregation behavior:

- if any primary evidence is `meaningful` or `ready`, aggregate is at least
  `meaningful`;
- if primary is `missing` or `placeholder`, meaningful supplemental evidence may
  make the aggregate meaningful only where the criterion explicitly allows
  supplemental evidence;
- if all available evidence is placeholder, aggregate is `placeholder`;
- if all evidence is missing, aggregate is `missing`;
- `thin` remains `thin` unless meaningful evidence exists.

Satisfies: R004-R007.

### D003 - Keep Artifact Coverage Separate

Readiness criterion quality and artifact coverage are related but separate.

If `proposal.md` Acceptance Criteria are meaningful and `execution-plan.md` is
placeholder-only, the criterion can be meaningful while artifact coverage still
suggests improving `execution-plan.md`.

Satisfies: R017-R019.

### D004 - Classify Already-Applied Questions As Closed

Structured question summary should treat a question as closed when:

```yaml
state: answered
applied_to_proposal: true
applied_at: <non-empty>
```

The simplest fix is in `_classify_structured_question`: check the durable applied
marker before the generic `state == "answered"` branch and append the question to
`closed_questions`.

Alternative: implement normalization in `ProposalQuestionService.reassess` that
promotes such records to `state: applied`. This mutates `questions.yml`; use it
only if explicit normalization is preferred over read-time classification.

Preferred first implementation: read-time classification in readiness, because
it fixes false readiness output without introducing a new mutation path.

Satisfies: R012-R016.

### D005 - Preserve Existing Apply Flow

`ProposalQuestionService.apply_summary` currently applies only questions with:

```python
state == answered and answer.strip() and not applied_to_proposal
```

This behavior should stay unchanged. PROP-096 should not make answered questions
look applied unless the durable applied marker already exists.

Satisfies: R014-R016.

## Components

### Readiness Service

File: `src/p2p_engine/services/readiness.py`

Add helper functions such as:

```python
readiness_evidence_quality(primary, *supplemental)
aggregate_readiness_qualities(...)
```

Use them for `acceptance_criteria_quality` first. Consider using the same helper
for `scope_boundaries` and `tradeoff_analysis` if those criteria combine
multiple sources and can suffer the same false downgrade.

### Proposal Question Classification

File: `src/p2p_engine/services/readiness.py`

Update `_classify_structured_question` to detect durable applied markers before
the answered-not-applied branch.

If choosing mutation-based normalization, update:

File: `src/p2p_engine/services/proposal_questions.py`

`reassess` should promote only records with both `applied_to_proposal: true` and
non-empty `applied_at`.

### Tests

Primary tests should be service-level:

- `tests/test_readiness_service.py`;
- `tests/test_proposal_questions_service.py` if normalization is added there.

CLI tests are not necessary unless human output or CLI exit behavior changes.

## Error Handling

No new user-facing error is required. The fix removes false findings rather than
adding new failure modes.

If a malformed question payload is encountered, existing validation behavior
continues to apply.

## Compatibility

- Existing readiness profile schema remains unchanged.
- Existing readiness labels and thresholds remain unchanged.
- Existing question state schema remains unchanged.
- Existing `p2p proposal questions apply` behavior remains unchanged for normal
  answered-unapplied questions.
- Existing artifact-state behavior remains separate from criterion quality.

## Alternatives

- Ignore `execution-plan.md` entirely for acceptance criteria: rejected because
  supplemental evidence can be useful.
- Mark all answered questions with `applied_to_proposal: true` as closed even
  without `applied_at`: rejected because it weakens the durable marker.
- Add a manual repair command: rejected for this bug fix because read-time
  classification is enough and safer.

## Test Strategy

Focused tests:

```bash
.venv/bin/pytest tests/test_readiness_service.py
.venv/bin/pytest tests/test_proposal_questions_service.py
```

Full validation before completion:

```bash
./scripts/test-full.sh
```

CLI validation is optional unless CLI output changes.
