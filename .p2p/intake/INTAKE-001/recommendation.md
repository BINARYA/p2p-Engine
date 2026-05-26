# Recommendation - INTAKE-001

## Classification

`alternative` / `overlap`

## Rationale

The idea "La CLI dovrebbe integrare subito Codex invece di restare prompt-only" is not a completely new project direction. It overlaps with already accepted work and introduces a competing implementation strategy.

Relevant existing intent:

- `PROP-001 — CLI Foundation` defines the first CLI as local, Git-native and prompt-only.
- `PROP-004 — Prompt-only Import Workflow` explicitly accepts the prompt/import workflow as the MVP strategy.
- `PROP-005 — Codex Skill Integration` already covers Codex integration at the skill/method level, not as direct CLI invocation.
- `PROP-006 — Multi-Agent Integration Model` is still draft and is the natural future area for direct AI adapters.

The raw idea challenges the current sequencing:

```text
current accepted path:
prompt-only first -> skill/agent guidance -> later AI adapter

new idea:
direct Codex integration immediately inside the CLI
```

This should not be accepted directly through intake, because it would alter an accepted MVP boundary. It should be framed as a governance/design choice about AI integration timing.

## Primary Recommendation

Open a choice on the initial AI integration strategy.

Suggested choice:

```text
CHOICE — Initial AI integration strategy

Option A: keep prompt-only first
Option B: integrate Codex directly now
Option C: keep prompt-only first and plan Codex adapter as a later Change Set
```

Recommended option for the current MVP: `Option C`.

Reason:
It preserves the accepted prompt-only workflow while keeping direct Codex integration visible as a planned evolution rather than losing the idea.

## Next Operational Step

Record the idea as a contribution against `PROP-004` or create a choice artifact when the CLI supports `p2p choice`.
