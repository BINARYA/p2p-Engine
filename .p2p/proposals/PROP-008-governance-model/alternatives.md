# Alternatives - PROP-008

## Alternative A - owner_decides

The project owner or maintainer decides.

Pros:

- Fast.
- Clear accountability.
- Good for bootstrap.

Cons:

- Less participatory.
- Can centralize too much power.

## Alternative B - open_consensus

Anyone can propose and support proposals; blocking objections matter.

Pros:

- Inclusive.
- Good for communities.
- Encourages discussion.

Cons:

- Slower.
- Can be ambiguous without clear blocking criteria.

## Alternative C - exclusive_vote

When alternatives conflict, one wins through a recorded vote.

Pros:

- Clear result.
- Good for mutually exclusive choices.
- Creates traceable precedent.

Cons:

- Requires voter identity/roles.
- Can become heavy without tooling.

## Recommended MVP

Use `owner_decides` as default, support `exclusive_vote` as a recorded file-based mechanism, and keep `open_consensus` as a documented mode before enforcing it technically.
