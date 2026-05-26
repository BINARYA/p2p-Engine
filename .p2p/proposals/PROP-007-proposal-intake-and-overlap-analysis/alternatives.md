# Alternatives - PROP-007

## Alternative A - `p2p proposal triage`

Triage lives under the proposal namespace.

Pros:

- Clear relationship with proposal lifecycle.
- Keeps command intent explicit.

Cons:

- Slightly longer command.

## Alternative B - `p2p triage`

Triage is top-level workflow.

Pros:

- Short and memorable.
- Could later triage comments, tasks, or risks too.

Cons:

- Less obvious that output affects proposals.

## Alternative C - Skill-only triage

Codex skill performs the triage without a CLI command.

Pros:

- Conversational.
- Fast to start.

Cons:

- Harder to validate.
- Risk of leaving triage only in chat.
- Violates P2P source-of-truth direction.

## Recommended Direction

Start with `p2p proposal triage prompt` and `p2p proposal triage import`, because the first target is proposal governance.
