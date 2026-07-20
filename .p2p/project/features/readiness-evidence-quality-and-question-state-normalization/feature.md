# Readiness Evidence Quality and Question State Normalization

## Provenance

- Proposal: PROP-096
- Source: .p2p/proposals/PROP-096-readiness-evidence-quality-and-question-state-normalization

## Problem

Readiness assessment can report false missing evidence when composed evidence includes a placeholder-only secondary artifact. We observed this when a meaningful Acceptance Criteria section was combined with an execution-plan.md file containing only the literal placeholder line `Pending`. The proposal question workflow can also leave answered questions in an inconsistent state where applied_to_proposal is true but state remains answered, causing readiness to keep reporting answered_not_applied even though the answer was already incorporated.

## Proposal

Refine readiness assessment so placeholder detection is artifact-aware. A placeholder-only supplemental artifact such as execution-plan.md should contribute no evidence or a separate warning, but it must not downgrade a meaningful primary section such as proposal.md Acceptance Criteria to placeholder. Refine proposal question normalization so a question with applied_to_proposal true and a non-empty applied_at is classified as applied, or provide a deterministic reassess or apply repair that promotes this internally consistent applied marker to state applied. The fix should keep existing readiness profiles and scoring thresholds stable while removing false missing and answered_not_applied findings.

## Decision

# Decision - PROP-096

## Status

`accepted`

## Outcome

accepted

## Event Type

accepted

## Effective State

accepted

## Reason

Owner accepts the readiness evidence quality and question state normalization fix after readiness reached decision_ready and the bug scope was fully bounded.

## Date

2026-07-13

## Approver

mrjungle

## Owner

mrjungle

## Ledger Head

PDE-96cf784b12e1ef5801ed0303

## Decision Fingerprint

a2cd5cc59a9a249bfc86b83acc9891f50895efc55a9628ca8d88aad62732f5b3

## Lineage

None.

## Canonical Source

decision-events.yml
