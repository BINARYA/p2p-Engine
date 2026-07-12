# PROP-096 - Readiness Evidence Quality and Question State Normalization

## Status

`accepted`

## Problem

Readiness assessment can report false missing evidence when composed evidence includes a placeholder-only secondary artifact. We observed this when a meaningful Acceptance Criteria section was combined with an execution-plan.md file containing only the literal placeholder line `Pending`. The proposal question workflow can also leave answered questions in an inconsistent state where applied_to_proposal is true but state remains answered, causing readiness to keep reporting answered_not_applied even though the answer was already incorporated.

## Context

The issue was observed while finalizing PROP-095. The proposal itself had meaningful acceptance criteria, but readiness marked acceptance_criteria_quality as placeholder because execution-plan.md still contained the default placeholder line. Separately, Q001 through Q004 were already marked applied_to_proposal true, but the question state was still answered, and proposal questions apply skipped them because they were not considered unapplied.

## Goals

- Make readiness quality scoring evaluate each evidence artifact without letting a placeholder-only supplemental artifact invalidate meaningful primary evidence.
- Normalize proposal question state so answered questions already marked applied_to_proposal true are treated as applied or are repairable through a supported CLI flow.
- Add regression tests that reproduce the PROP-095 failure mode and prove readiness assess does not produce false missing evidence.

## Non-Goals

- Do not redesign the readiness scoring model or readiness profile thresholds.
- Do not change owner governance semantics or make readiness scores authoritative decisions.
- Do not introduce direct editing of .p2p proposal question state as a supported user workflow.

## Proposal

Refine readiness assessment so placeholder detection is artifact-aware. A placeholder-only supplemental artifact such as execution-plan.md should contribute no evidence or a separate warning, but it must not downgrade a meaningful primary section such as proposal.md Acceptance Criteria to placeholder. Refine proposal question normalization so a question with applied_to_proposal true and a non-empty applied_at is classified as applied, or provide a deterministic reassess or apply repair that promotes this internally consistent applied marker to state applied. The fix should keep existing readiness profiles and scoring thresholds stable while removing false missing and answered_not_applied findings.

## Acceptance Criteria

- Given proposal.md has meaningful Acceptance Criteria and execution-plan.md contains only the default placeholder line, when readiness assess runs, acceptance_criteria_quality is not classified as placeholder or missing solely because of the supplemental execution-plan.md placeholder.
- Given all acceptance evidence is actually placeholder or absent, readiness still reports acceptance_criteria_quality as missing or placeholder.
- Given a proposal question has state answered, applied_to_proposal true, and applied_at set, readiness owner_question_state does not report it as answered_not_applied after the supported normalization path runs.
- Given a proposal question is answered and applied_to_proposal false, the existing apply flow still reports and applies it normally.
- Regression tests cover readiness composed evidence, placeholder-only supplemental artifacts, and applied question state normalization.

## Decision

Pending.
