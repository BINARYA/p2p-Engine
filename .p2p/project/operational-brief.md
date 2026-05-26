# P2P Engine Operational Brief

## Where We Are

P2P Engine now has the complete local managed Work lifecycle plus a read-only operational status view.

The managed Work flow currently supported by the CLI is:

```text
p2p work plan
p2p work status
p2p work branch
p2p work submit
p2p work review
p2p work publish
p2p work accept
```

The project state is current at 37 proposals and 23 Change Sets. All recorded Change Sets are completed, including `CHANGE-023` / `PROP-037` for Managed Work Status Summary MVP. Registries are not stale.

## Accepted Direction

- P2P remains CLI-first, file-based, and Git-native.
- Change Sets remain the operational unit for implementation and export.
- Work items are the user-facing abstraction over managed Git operations.
- Current managed Git safe level is Level 5: owner-controlled local accept / merge.
- `p2p work status` is the default read-only view before choosing any Work lifecycle command.
- Publishing and accepting remain separate: `p2p work publish` pushes the managed branch, while `p2p work accept` merges locally into the base branch and does not push the base branch or delete branches.
- Optional PR creation, base branch push, cleanup, and conflict recovery are future refinements, not current behavior.

## Active Work

- `WORK-001` exists and is still `planned` for `CHANGE-012` / `speckit`.
- `p2p work status` currently recommends `p2p work branch WORK-001` for that Work item.
- No Change Set is currently planned or in progress.
- Draft proposals remain: `PROP-002` Exploration Phase, `PROP-006` Multi-Agent Integration Model, `PROP-007` Proposal Intake and Overlap Analysis, and `PROP-008` Governance Model.
- `INTAKE-001` is analyzed and has a controlled apply plan.
- `INTAKE-002` is pending and should be inspected before more product-direction work.

## Blockers / Inconsistencies

- No active formal choice blockers are recorded.
- `CHOICE-001` is decided: prompt-only first, Codex adapter later.
- `CHOICE-PROP-008` remains proposal-local vote metadata rather than a project-level choice.
- `WORK-001` is an older planned handoff artifact and should be inspected before use to confirm it still reflects current project direction.

## Recommended Next Actions

1. Inspect the pending intake.
   Reason: `INTAKE-002` is pending and may contain the next raw project direction.
   Command: `.venv/bin/p2p intake status`

2. Review the controlled apply plan for `INTAKE-001`.
   Reason: `INTAKE-001` already has an analyzed apply plan with pending actions; the owner should decide whether any apply action is still relevant after managed Work Level 5.
   Command: `.venv/bin/p2p intake apply show INTAKE-001`

3. Decide the next managed Work hardening slice.
   Reason: the base Work lifecycle is complete and readable. The next likely refinements are merge-conflict guidance, finalize/push-main, cleanup, or GitHub PR handoff.
   Command: `.venv/bin/p2p work status`

## Not Yet

- Do not add automatic PR creation, base branch push, branch deletion, cleanup, or conflict recovery without a new accepted proposal and Change Set.
- Do not treat draft proposals or pending intake as accepted direction.
- Do not move from prompt-only/Codex-assisted workflows to direct provider integration without revisiting the accepted AI integration choice.
