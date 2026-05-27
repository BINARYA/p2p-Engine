# Recommendation - INTAKE-002

## Classification

`duplicate` / `already_decided` / `future_follow_up`

## Rationale

The intake idea:

```text
La CLI dovrebbe integrare subito Codex invece di restare prompt-only
```

does not introduce a new independent project direction. It repeats the direct-Codex alternative already evaluated by `CHOICE-001 - Initial AI Integration Strategy`.

The relevant decided choice is:

```text
CHOICE-001 selected option C:
Prompt-only first, Codex adapter later
```

So the current project direction remains:

```text
prompt-only MVP
-> Codex skill / agent guidance
-> later adapter-oriented direct Codex integration
```

The intake should not create a new choice and should not reopen the MVP boundary by itself. It is useful as future input for `PROP-006 - Multi-Agent Integration Model`, because that draft proposal is the natural home for direct AI provider adapters.

## Primary Recommendation

Do not create a new proposal and do not open a new choice.

Record this intake as a contribution to `PROP-006`, preserving the desire for direct Codex integration as future adapter work after the prompt-only foundation remains stable.

## Next Operational Step

Create a controlled apply plan and apply only the `add_contribution` action for `PROP-006`.
