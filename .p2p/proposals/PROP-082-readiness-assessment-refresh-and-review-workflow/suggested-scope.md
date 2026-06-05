# Suggested Scope - PROP-082

## Product Direction

Readiness must evolve from a conservative diagnostic snapshot into a governed
review workflow.

The workflow should support these distinct operations:

```text
init
  -> bootstrap a conservative first assessment

refresh
  -> synchronize/read current readiness snapshot without pretending to perform
     qualitative reassessment

assess
  -> re-evaluate proposal artifacts and update computed readiness evidence

review
  -> record human or owner-reviewed assessment confirmation

resolve-gate
  -> explicitly record that a failed gate is resolved with evidence/reason

import
  -> validate and persist a structured assessment produced by an agent or
     external review process

override
  -> decision-time owner governance event that does not falsify computed_score
```

## Included In MVP

- CLI command design for readiness assessment and review.
- Criterion-level evidence persistence through public P2P commands.
- Confidence update through public P2P commands.
- Failed gate resolution with reason and actor.
- Assessment source tracking:
  - deterministic;
  - agent_assisted;
  - owner_reviewed.
- Validation for malformed readiness records.
- MCP tool parity over the same core behavior.

## Candidate Commands

```bash
p2p proposal readiness assess PROP-XXX
p2p proposal readiness review PROP-XXX --by owner --reason "..."
p2p proposal readiness resolve-gate PROP-XXX owner_questions_resolution --reason "..."
p2p proposal readiness import PROP-XXX assessment.yml
```

Exact names may change during implementation planning, but the behavior must be
available through public commands rather than manual `readiness.yml` edits.

## Excluded From MVP

- Automatic proposal acceptance.
- Replacing owner decision authority.
- Falsifying `computed_score` when owner override is used.
- Building a perfect AI scoring model.
- Treating readiness metadata as more authoritative than proposal artifacts.

