# Exploration - PROP-017

## Interpretation

This proposal introduces the missing bridge between raw user/agent ideas and the structured P2P workflow.

P2P Engine already stores proposals, decisions, change sets, conflicts, project state and registries. However, a new idea still enters the system without enough guidance. An agent or user needs help answering:

- is this idea already covered?
- should it be a new proposal?
- should it become a contribution to an existing proposal?
- is it an alternative to an existing direction?
- does it open a governance choice?
- does it conflict with an accepted decision?

## Scenario

The target scenario is collaborative and multi-agent:

- user A owns the project and uses Codex;
- user B uses Claude to comment on A's proposal;
- user C uses another agent to introduce a new idea;
- P2P Engine provides shared project memory and governance state;
- A asks for a synthesis of pending proposals, overlaps and decisions.

This requires P2P Engine to support context-aware intake before proposal acceptance.

## Core Idea

Introduce an intake workflow backed by generated registries:

```text
raw idea / observation
-> registry-backed context scan
-> related proposals and changes
-> possible duplicate/overlap/conflict/alternative classification
-> suggested next action
-> proposal, contribution, choice or conflict artifact
```

## MVP Boundary

The MVP should remain prompt-only and deterministic where possible.

The CLI can gather context from `.p2p/registries/` and generate an intake prompt. An external AI or agent produces the analysis, and P2P imports the result as an artifact.

The first implementation does not need embeddings, semantic search, direct AI calls, MCP or automatic decisions.

## Candidate Commands

```bash
p2p intake prompt "La CLI dovrebbe integrare subito Codex"
p2p intake import intake-output.md
p2p intake status
```

Potential later commands:

```bash
p2p intake analyze "..."
p2p proposal show PROP-001
p2p proposal list --status accepted
p2p relation add PROP-017 --type related_to --target PROP-007
p2p choice create --title "Initial AI strategy"
```

## Expected Output

The intake phase should produce:

```text
.p2p/intake/
  INTAKE-001/
    input.md
    context.md
    related-proposals.yml
    recommendation.md
    suggested-actions.yml
```

The output should be advisory. It must not accept, reject or merge proposals without a governance command.
