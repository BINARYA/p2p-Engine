# Operational Brief

## Where We Are

P2P Engine has completed the managed Work pipeline through Level 5. The CLI can now plan Work from validated exports, create managed branches, submit local commits, record local review requests, publish managed branches to the remote, and accept published Work by locally merging the managed branch into the base branch under owner control.

The project memory is current at 36 proposals and 22 Change Sets. All recorded Change Sets are completed, including `CHANGE-022` / `PROP-036` for Managed Work Accept MVP. Registries are not stale.

## Accepted Direction

- P2P remains CLI-first, file-based, and Git-native.
- Change Sets remain the operational unit for implementation and export.
- Work items are the user-facing abstraction over Git operations.
- Current managed Git safe level is Level 5: owner-controlled local accept / merge.
- Publishing and accepting remain separated: `p2p work publish` pushes the managed branch, while `p2p work accept` merges locally into the base branch and does not push the base branch or delete branches.
- Optional PR creation, base branch push, and cleanup are future levels, not current behavior.

## Active Work

- No Change Set is currently planned or in progress.
- Draft proposals remain: `PROP-002` Exploration Phase, `PROP-006` Multi-Agent Integration Model, `PROP-007` Proposal Intake and Overlap Analysis, and `PROP-008` Governance Model.
- `INTAKE-001` is analyzed and has a controlled apply plan.
- `INTAKE-002` is pending and should be inspected before more product-direction work.
- `WORK-001` exists as an older planned handoff artifact and should be inspected or retired if it no longer reflects current project direction.

## Blockers / Inconsistencies

- No active formal choice blockers are recorded.
- `CHOICE-001` is decided: prompt-only first, Codex adapter later.
- `CHOICE-PROP-008` remains proposal-local vote metadata rather than a project-level choice.
- The next-action file was stale before this refresh and pointed to already completed managed branch creation work.

## Recommended Next Actions

1. Inspect the pending intake.
   Reason: `INTAKE-002` is the only pending intake record and may contain the next raw project direction.
   Command: `.venv/bin/p2p intake status`

2. Review the controlled apply plan for `INTAKE-001`.
   Reason: `INTAKE-001` already has an analyzed apply plan with pending actions; the owner should decide whether any apply action is still relevant after Level 5.
   Command: `.venv/bin/p2p intake apply show INTAKE-001`

3. Choose the next product slice after managed Work Level 5.
   Reason: the managed Git pipeline has reached local owner-controlled merge, so the next implementation should be an explicit proposal, likely around optional PR creation, base branch push / cleanup, or revisiting the pending governance and multi-agent proposals.
   Command: `.venv/bin/p2p proposal list --status draft`

## Not Yet

- Do not add automatic PR creation, base branch push, branch deletion, or cleanup without a new accepted proposal and Change Set.
- Do not treat draft proposals or pending intake as accepted direction.
- Do not move from prompt-only/Codex-assisted workflows to direct provider integration without revisiting the accepted AI integration choice.
