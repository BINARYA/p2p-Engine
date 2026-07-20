# Project Definition Maturity Rubrics

## Provenance

- Proposal: PROP-056
- Source: .p2p/proposals/PROP-056-project-definition-maturity-rubrics

## Problem

P2P assess currently measures deterministic structural readiness: validation, registries, proposal status, choices, changes, work items, and operational brief availability. This is useful, but it does not evaluate whether the planned project definition covers the important topics for its domain. For P2P exports, the main question is not whether implementation is complete, but whether the project has been sufficiently defined through proposals, decisions, tradeoffs, risks, requirements, and acceptance criteria.

## Proposal

Add Project Definition Maturity Rubrics. A project may define a domain and an enabled list of criteria under .p2p/project/rubrics.yml. The first MVP ships deterministic built-in rubrics for at least generic and software domains, with an architecture that can add grant_document, board_game, hardware, service, and other domains later. The init flow should be able to create an initial rubric profile, and a dedicated command should refresh/show maturity assessment. The assessment should scan P2P project artifacts conservatively and report each criterion as covered, partial, or missing, with evidence IDs when available. Scores represent definition maturity: whether the planned project has treated relevant topics enough for export, not whether implementation has been completed.

## Decision

# Decision - PROP-056

## Status

`accepted`

## Outcome

accepted

## Event Type

accepted

## Effective State

accepted

## Reason

Accepted to distinguish structural readiness from project definition maturity and introduce extensible domain rubrics as deterministic drivers for export readiness.

## Date

2026-05-28

## Approver

mrjungle

## Owner

mrjungle

## Ledger Head

PDE-0619ce664d038ebb0f909ce6

## Decision Fingerprint

9c45ad593e333c3b063d13c5b9bdbf6d093e2f3e799b7f162a3f3dd004e54d05

## Lineage

None.

## Canonical Source

decision-events.yml
