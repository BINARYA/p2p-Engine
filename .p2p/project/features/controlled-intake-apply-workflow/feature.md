# Controlled Intake Apply Workflow

## Provenance

- Proposal: PROP-025
- Source: .p2p/proposals/PROP-025-controlled-intake-apply-workflow

## Problem

Intake analysis can recommend actions, but there is no controlled, auditable workflow to turn selected suggestions into P2P state changes.

## Proposal

Implement a two-phase controlled intake apply workflow. The plan command converts suggested-actions.yml into a versioned apply-plan.yml with support classifications. The show command displays the plan. The run command applies one explicit supported action and writes applied-actions.yml, while governance-only actions remain preview-only.

## Decision

# Decision - PROP-025

## Status

`accepted`

## Outcome

accepted

## Reason

Accepted to implement intake apply as an auditable plan/show/run workflow rather than direct automatic application.

## Date

2026-05-25

## Approver

local
