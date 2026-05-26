# Clarifications - PROP-010

## Q1. Should `.p2p/outputs/` be committed to Git by default, or treated as regenerable build output?

`.p2p/outputs/` should be committed to Git by default because it represents the rationalized project state, not a disposable build artifact.

The official version of `.p2p/outputs/` lives on `main`. Proposal branches may contain preview updates to `.p2p/outputs/` showing how the accepted project state would change if the proposal is approved.

When a proposal branch is merged into `main`, the corresponding output changes become official. This keeps Git as the audit layer:

- proposal branch = proposed change to project state;
- review/decision = governance step;
- merge to main = accepted state;
- `.p2p/outputs/` on main = canonical rationalized project specification.

Generated outputs should include provenance back to proposal IDs and decisions, so it is always clear which accepted proposal changed which part of the output.

Clarification:

`.p2p/outputs/` is derived and versioned. It is not the primary source, but it is official project state once it lands on `main`. Source artifacts remain proposals, decisions, governance files, and docs.

## Q2. Should accepted decisions refresh outputs automatically in the MVP?

For the MVP, refresh should be explicit:

```bash
p2p decision record PROP-010 --outcome accepted --reason "..."
p2p project refresh
```

Automatic refresh can come later as an opt-in configuration. Explicit refresh makes the diff easier to inspect and avoids surprising users when recording a decision changes broad project artifacts.

## Q3. What is the minimum shape of a P2P software spec?

The generated layer should probably be named `project` rather than generic `outputs`, because its role is to represent the rationalized project state.

Suggested structure:

```text
.p2p/project/
  overview.md
  problem.md
  scope.md
  project-swot.md
  features/
    <feature-id>/
      feature.md
      tasks.yml
      actions.yml
  decisions-map.yml
  conflicts.yml
  exports/
    markdown/
    openspec/
    speckit/
```

Minimum content:

- project context;
- problem scope;
- general SWOT explaining how the project addresses the problem;
- feature list;
- operational tasks per feature;
- optional single actions/checklist items under tasks;
- provenance back to proposals and decisions.

This model can learn from Spec Kit/OpenSpec later, but should remain P2P-native and governance-first.

## Q4. Can one accepted proposal update multiple modules/features?

Yes. A proposal or suggestion may affect many parts of the system.

Each proposal should explicitly declare:

- what project areas it touches;
- what features/modules it updates;
- what new tasks/actions it creates;
- what assumptions it changes;
- what other accepted decisions it depends on;
- what proposals it conflicts with or supersedes.

This means P2P needs an impact map. A proposal should not be treated as a single-module patch by default.

## Q5. How should conflicts between accepted proposals be handled?

Conflicting proposals should be marked explicitly before acceptance. If proposals are mutually exclusive, they should be grouped as competing alternatives.

The system should preserve memory of the contrast:

```text
conflict group
  alternatives:
    - PROP-010
    - PROP-011
    - PROP-012
  decision:
    winner: PROP-011
    rejected:
      - PROP-010
      - PROP-012
```

If one alternative is accepted, mutually exclusive alternatives should be rejected, superseded, or marked as not selected. They should not remain open as if they could still be accepted unchanged.

This is a high-value use case for AI: detect overlap, hidden incompatibility, duplicated intent, and mutually exclusive directions, then ask humans to choose which path to take.

The conflict memory should live in the project layer, for example:

```text
.p2p/project/conflicts.yml
.p2p/project/decisions-map.yml
```
