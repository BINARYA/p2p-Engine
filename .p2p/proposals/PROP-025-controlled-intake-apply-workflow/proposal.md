# PROP-025 - Controlled Intake Apply Workflow

## Status

`accepted`

## Problem

Intake analysis can recommend actions, but there is no controlled, auditable workflow to turn selected suggestions into P2P state changes.

## Context

The project now supports operational briefs, p2p next, and choice discovery/blocking. Intake apply should follow the same source-of-truth discipline: plan first, show reviewable actions, run only explicit supported actions, and log what was applied.

## Goals

- Add p2p intake apply plan INTAKE-XXX to create apply-plan.yml.
- Add p2p intake apply show INTAKE-XXX to inspect the plan.
- Add p2p intake apply run INTAKE-XXX --action APPLY-XXX for explicit application.
- Record applied actions in applied-actions.yml.
- Support add_contribution and open_choice with explicit options in the MVP.

## Non-Goals

- Do not automatically apply all intake recommendations by default.
- Do not apply governance decisions such as accept, reject, or defer.
- Do not invoke AI directly.

## Proposal

Implement a two-phase controlled intake apply workflow. The plan command converts suggested-actions.yml into a versioned apply-plan.yml with support classifications. The show command displays the plan. The run command applies one explicit supported action and writes applied-actions.yml, while governance-only actions remain preview-only.

## Acceptance Criteria

- p2p intake apply plan INTAKE-XXX writes apply-plan.yml.
- p2p intake apply show INTAKE-XXX displays planned actions.
- p2p intake apply run supports add_contribution.
- p2p intake apply run supports open_choice only when at least two --option values are provided.
- defer, accept, reject, duplicate and unsupported actions are not applied automatically.
- applied-actions.yml records every successful application.

## Decision

Pending.
