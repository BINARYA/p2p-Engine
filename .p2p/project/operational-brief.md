# P2P Engine Operational Brief

## Where We Are

P2P Engine now has the managed Work lifecycle through cleanup, plus a provider-agnostic remote project profile and optional external review handoff.

The supported managed Work flow is:

```text
p2p project remote show
p2p project remote configure
p2p work plan
p2p work status
p2p work branch
p2p work submit
p2p work review
p2p work publish
p2p work request-review
p2p work accept
p2p work accept --continue
p2p work accept --abort
p2p work finalize
p2p work cleanup
```

The project state is current at 41 proposals and 27 Change Sets. All recorded Change Sets are completed, including `CHANGE-027` / `PROP-041` for Remote Project Profile and Review Request Policy. Registries are not stale.

## Accepted Direction

- P2P remains CLI-first, file-based, and Git-native.
- Change Sets remain the operational unit for implementation and export.
- Work items are the user-facing abstraction over managed Git operations.
- GitHub/GitLab integration remains optional and adapter-based.
- The core workflow remains provider-agnostic: `publish` pushes a managed branch, while `request-review` records an external review handoff without opening a PR/MR.
- The current project remote profile is remote-backed with provider `github`, remote `origin`, and URL `git@github.com:BINARYA/p2p-Engine.git`.
- Work lifecycle responsibilities remain separated:
  - `p2p work review` requests local owner review.
  - `p2p work publish` pushes the managed Work branch.
  - `p2p work request-review` records optional external review guidance.
  - `p2p work accept` merges locally into the base branch.
  - `p2p work finalize` pushes the accepted base branch.
  - `p2p work cleanup` deletes finalized Work branches, with remote deletion only when explicitly requested through `--remote`.

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
   Reason: `INTAKE-001` already has an analyzed apply plan with pending actions; the owner should decide whether any apply action is still relevant after the managed Work lifecycle reached cleanup and remote review handoff.
   Command: `.venv/bin/p2p intake apply show INTAKE-001`

3. Decide the next integration slice.
   Reason: the base managed Work lifecycle now has local review, remote publish, optional external review handoff, owner-controlled accept/finalize, and cleanup. The next likely refinements are real provider adapters for PR/MR creation/observation, richer remote multi-branch visibility, or retiring/staging `WORK-001`.
   Command: `.venv/bin/p2p work status`

## Not Yet

- Do not add automatic PR/MR creation without a new accepted proposal and Change Set.
- Do not treat draft proposals or pending intake as accepted direction.
- Do not move from prompt-only/Codex-assisted workflows to direct provider integration without revisiting the accepted AI integration choice.
