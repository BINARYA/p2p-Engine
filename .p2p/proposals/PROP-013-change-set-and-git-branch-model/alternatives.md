# Alternatives - PROP-013

## Alternative A - Proposal Always Creates Branch

Every proposal gets a dedicated Git branch.

Pros:

- Strong isolation.
- Easy review of file diffs per proposal.
- Simple policy.

Cons:

- Too many branches for small ideas.
- Operational overhead.
- Proposal and branch become overly coupled.
- Historical memory can be dispersed if branches are deleted.

## Alternative B - Proposal Never Creates Branch

All proposals live only as `.p2p/` artifacts on the current branch.

Pros:

- Simpler CLI.
- Less Git overhead.
- Proposal registry remains centralized.

Cons:

- Weak isolation for controversial or complex proposals.
- Harder collaboration for concurrent proposal work.
- Harder review of project-state preview changes.

## Alternative C - Hybrid Proposal/Change Set Model

Proposals live in `.p2p/`. Branches are optional for proposals and recommended or required for operational change sets.

Pros:

- Keeps proposal as decision unit.
- Keeps Git as audit/collaboration layer.
- Reduces branch clutter.
- Allows formal branch workflow when implementation starts.

Cons:

- Requires branch policy criteria.
- Requires a new change-set abstraction.

## Alternative D - Managed Git Under The Hood

Users work only with P2P concepts. P2P Engine applies Git operations internally according to `git_policy.yml`.

Pros:

- Best user experience for non-Git users.
- Keeps Git-native auditability and portability.
- Removes arbitrary user-facing branch decisions.
- Lets AI agents use the P2P public interface instead of direct Git commands.
- Preserves advanced/debug visibility through verbose and doctor commands.

Cons:

- Requires a Git adapter.
- Requires careful safety rules for automatic commits/branches/tags.
- Debugging internal Git state needs explicit tooling.

## Preferred Direction

Alternative D.

Alternative C is still conceptually useful, but the user-facing model should be managed Git under the hood rather than exposing branch decisions as a normal workflow concern.
