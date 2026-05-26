# P2P Engine Operational Brief

## Where We Are

P2P Engine now has the managed Work lifecycle through finalization, plus read-only status and guided merge-conflict recovery.

The supported managed Work flow is:

```text
p2p work plan
p2p work status
p2p work branch
p2p work submit
p2p work review
p2p work publish
p2p work accept
p2p work accept --continue
p2p work accept --abort
p2p work finalize
```

The project state is current at 39 proposals and 25 Change Sets. All recorded Change Sets are completed, including `CHANGE-025` / `PROP-039` for Managed Work Finalize MVP. Registries are not stale.

## Accepted Direction

- P2P remains CLI-first, file-based, and Git-native.
- Change Sets remain the operational unit for implementation and export.
- Work items are the user-facing abstraction over managed Git operations.
- Current managed Git safe level includes finalization: accepted Work can be pushed to the configured remote base branch through `p2p work finalize`.
- `p2p work status` is the default read-only view before choosing any Work lifecycle command.
- Merge conflicts during `p2p work accept` are explicit and recoverable through `--continue` and `--abort`.
- Publishing, accepting, and finalizing remain separate:
  - `p2p work publish` pushes the managed Work branch.
  - `p2p work accept` merges locally into the base branch.
  - `p2p work finalize` pushes the accepted base branch.
- Branch cleanup and GitHub PR creation are future refinements, not current behavior.

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
   Reason: `INTAKE-001` already has an analyzed apply plan with pending actions; the owner should decide whether any apply action is still relevant after the managed Work lifecycle reached finalization.
   Command: `.venv/bin/p2p intake apply show INTAKE-001`

3. Decide the next managed Work hardening slice.
   Reason: the base lifecycle is complete through finalize. The next likely refinements are branch cleanup, GitHub PR handoff, richer multi-branch visibility, or retiring/staging `WORK-001`.
   Command: `.venv/bin/p2p work status`

## Not Yet

- Do not add automatic PR creation, branch deletion, or cleanup without a new accepted proposal and Change Set.
- Do not treat draft proposals or pending intake as accepted direction.
- Do not move from prompt-only/Codex-assisted workflows to direct provider integration without revisiting the accepted AI integration choice.
