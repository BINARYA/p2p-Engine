# Guided Rubric Selection During Init

## Provenance

- Proposal: PROP-057
- Source: .p2p/proposals/PROP-057-guided-rubric-selection-during-init

## Problem

The init wizard now asks for a project domain and generates domain rubrics automatically, but the owner cannot confirm which suggested criteria should actually drive project definition maturity. This makes the rubric feel imposed by the system instead of selected as part of project governance.

## Proposal

Add Guided Rubric Selection During Init. When p2p init runs interactively, after project domain selection it should ask whether to customize rubric criteria. If the owner says no, P2P keeps all domain criteria enabled. If the owner says yes, P2P asks an enable/disable confirmation for each suggested criterion and saves the selected enabled flags into .p2p/project/rubrics.yml. Scripted init with a project name remains non-interactive and uses the full default rubric for the selected domain.

## Decision

# Decision - PROP-057

## Status

`accepted`

## Outcome

accepted

## Reason

Accepted to close the domain-to-rubric onboarding loop by letting the owner confirm which suggested criteria drive project definition maturity.

## Date

2026-05-28

## Approver

local
