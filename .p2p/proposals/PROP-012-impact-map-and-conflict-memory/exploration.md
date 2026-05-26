# Exploration - PROP-012

## Interpretation

PROP-012 adds the missing analysis layer between a proposal and the rationalized project state. P2P Engine can already create proposals, record decisions, and refresh `.p2p/project/`, but it cannot yet explain what a proposal touches or remember which alternatives were rejected because they conflicted with an accepted direction.

## Core Idea

Every meaningful proposal should produce an impact map before decision:

```text
proposal
→ affected features
→ affected commands/files/artifacts
→ dependencies
→ overlaps
→ conflicts
→ decision implications
```

Conflict memory should then live in `.p2p/project/conflicts.yml`, so future proposals can be checked against previous mutually exclusive choices.

## Suggested Artifacts

Proposal-level artifacts:

```text
.p2p/proposals/<proposal>/
  impact-map.yml
  related-proposals.yml
  conflict-analysis.yml
```

Project-level artifact:

```text
.p2p/project/conflicts.yml
```

## MVP Workflow

```bash
p2p impact prompt PROP-012

# user/AI produces impact-map.yml, related-proposals.yml, conflict-analysis.yml

p2p impact import PROP-012 impact-output/

p2p conflict record PROP-010 PROP-012 \
  --type overlaps \
  --reason "Both modify project-state semantics."

p2p conflict status
```

## Boundary

The CLI can record and expose impact/conflict information, but should not automatically reject or accept proposals. Final decisions remain governance-defined and human-approved.
