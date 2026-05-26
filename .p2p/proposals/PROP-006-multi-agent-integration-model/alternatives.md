# Alternatives - PROP-006

## Alternative A - Agent Profiles Only

Create static templates for each supported agent.

Pros:

- Simple to implement.
- Works with current file-based model.
- No runtime AI dependency.

Cons:

- No lifecycle management.
- Harder to know what is installed or stale.

## Alternative B - Integration Registry

Add a registry similar in spirit to Spec Kit: agent keys, install/list/use/update/remove, default integration, installed files.

Pros:

- Explicit state.
- Scales beyond Codex.
- Supports generic integrations.
- Easier upgrades.

Cons:

- More schema and command complexity.

## Alternative C - OpenSpec-Style Slash Commands First

Generate slash commands/skills for several tools and rely on each agent UI to invoke them.

Pros:

- Natural for AI coding assistants.
- Good UX for tools that support slash commands.

Cons:

- Tool behavior varies widely.
- P2P still needs a registry to avoid unmanaged files.

## Recommended Direction

Start with Alternative B in a minimal form, implemented file-first:

```text
.p2p/agent-integrations.yml
.p2p/agent-templates/
```

Then generate Codex/Claude/generic outputs from templates.
