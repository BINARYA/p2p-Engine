# Alternatives - PROP-002

## Context

PROP-002 is not only about adding an `explore` command. The deeper product
problem is that P2P Engine must prevent proposals from moving too quickly from a
generic idea to an accepted direction without enough questioning, comparison,
risk analysis, owner input, and scope definition.

The alternatives below compare different ways to make proposal exploration a
real decision-support workflow instead of a passive artifact scaffold.

## Alternative A - Strict Completeness Gate

Require every proposal to have all exploration artifacts meaningfully populated
before it can be considered mature:

- `exploration.md`
- `findings.md`
- `alternatives.md`
- `open-questions.md`
- `risks.md`
- `assumptions.md`
- `suggested-scope.md`

The agent must inspect these artifacts and challenge missing, empty, or generic
content before recommending acceptance or implementation.

Pros:

- Simple rule to explain and enforce.
- Makes the existing proposal artifact structure operationally meaningful.
- Reduces the chance that important concerns stay only in chat.
- Encourages consistent proposal records across the project.

Cons:

- Can become bureaucratic for small or obvious proposals.
- May produce decorative text if the agent optimizes for "all files filled"
  instead of useful exploration.
- Does not by itself define whether the content is good enough.

Best fit:

- Governance-critical, architectural, or high-impact proposals where the cost of
  weak exploration is high.

## Alternative B - Proposal Readiness Gate

Introduce an explicit readiness workflow, for example:

```text
draft -> explored -> ready_for_decision -> accepted/rejected/deferred
```

A proposal cannot become `ready_for_decision` while key exploration gaps remain,
such as missing alternatives, unresolved owner questions, unclear assumptions,
unassessed risks, or absent acceptance criteria.

`p2p next` should report specific readiness gaps instead of only saying that a
draft proposal should be reviewed.

Pros:

- Directly addresses the current weakness in `next` recommendations.
- Separates "draft exists" from "proposal is ready to decide".
- Gives agents a concrete workflow to follow.
- Can make proposal review more repeatable and auditable.

Cons:

- Requires new state, checks, or derived readiness logic.
- Needs careful governance boundaries so agents do not decide readiness in place
  of the owner.
- May require migration or interpretation for existing proposals.

Best fit:

- Core P2P Engine workflow because readiness is central to turning discussion
  into trustworthy decisions.

## Alternative C - Agent Interrogation Protocol

Define explicit agent behavior for proposal exploration. The agent should be
instructed to be deliberately demanding before allowing an idea to harden into a
proposal:

- Do not accept the first generic formulation as sufficient.
- Ask targeted questions about ambiguity, constraints, edge cases, and user
  intent.
- Separate desired outcome from implementation approach.
- Identify assumptions that are being silently made.
- Generate and compare alternatives, including smaller and more structural
  options.
- Look for overlap, conflict, or duplication with existing proposals.
- Ask the owner for real governance decisions instead of inventing them.
- Capture unresolved questions instead of smoothing them over.

Pros:

- Improves the quality of AI-assisted proposal development immediately.
- Fits the current Codex skill and MCP-agent direction.
- Makes the agent more useful as a critical collaborator, not just a summarizer.
- Can be implemented first as instructions and later enforced by CLI/MCP checks.

Cons:

- If implemented only as prose instructions, compliance may be inconsistent.
- Different agents may apply the protocol with different levels of rigor.
- Without readiness checks, the protocol may not reliably affect `p2p next`.

Best fit:

- Agent-facing workflows, MCP clients, Codex skill behavior, and prompt
  generation.

## Alternative D - Alternatives-First Proposal Model

Require non-trivial proposals to identify at least two or three plausible
directions before recommending one. Example pattern:

```text
A - minimal implementation
B - structured workflow
C - agent-first / MCP-first workflow
```

Each option should be compared on cost, risk, product impact, implementation
complexity, governance effect, agent ergonomics, and future extensibility.

Pros:

- Forces real choice rather than documenting the first solution.
- Helps the owner understand tradeoffs before deciding.
- Makes sub-optimal choices acceptable when chosen consciously for pragmatic
  reasons.
- Creates a stronger basis for future precedent and conflict analysis.

Cons:

- Can feel heavy for routine maintenance work.
- Requires the agent to invent alternatives responsibly without overcomplicating
  simple problems.
- Needs a way to distinguish meaningful alternatives from artificial ones.

Best fit:

- Product, governance, architecture, MCP surface, agent behavior, and lifecycle
  proposals.

## Alternative E - Tiered Exploration Model

Classify proposals by required exploration depth, for example:

```text
small / routine
medium / product
large / architectural
governance-critical
```

The higher the tier, the more exploration artifacts become required or strongly
recommended. A small documentation fix may need only a concise proposal and risk
note; a governance or agent-workflow proposal should require alternatives,
risks, assumptions, open questions, and explicit suggested scope.

Pros:

- Avoids unnecessary bureaucracy for small changes.
- Allows strictness where it matters most.
- Gives `p2p next` a basis for targeted refinement prompts.
- Makes the exploration workflow scalable across project sizes.

Cons:

- The tiering rules must be clear or agents may classify too many proposals as
  small.
- Adds one more decision point before exploration.
- Needs owner override when the apparent size of a proposal hides strategic
  importance.

Best fit:

- Projects that need both lightweight iteration and serious governance for
  important decisions.

## Alternative F - Hybrid Exploration And Readiness Model

Combine the strongest parts of the previous alternatives:

- Keep exploration artifacts as the durable proposal memory.
- Add readiness checks for missing or weak exploration dimensions.
- Instruct agents to interrogate proposals actively and persistently.
- Require alternatives for non-trivial proposals.
- Use tiers to avoid forcing full ceremony on every tiny change.
- Make `p2p next` surface concrete refinement gaps.

The intended workflow becomes:

```text
rough idea -> explored draft -> readiness gaps -> owner questions -> alternatives
comparison -> suggested scope -> ready for decision
```

Pros:

- Addresses the actual observed failure mode from multiple angles.
- Gives both humans and agents a clearer path from idea to decision.
- Preserves lightweight operation for simple proposals while strengthening core
  product and governance work.
- Makes the existing proposal files useful instead of optional decoration.

Cons:

- More complex than a single command or single artifact rule.
- Requires careful implementation sequencing.
- Needs good documentation and skill/MCP alignment to avoid confusing agents.

Best fit:

- Recommended direction for PROP-002 because proposal exploration is central to
  P2P Engine's value.

## Cross-Cutting Comment - Multi-Criteria Decision Support

The alternatives should not only list pros and cons. P2P Engine should consider
a lightweight value or scoring system that derives an impact measure from the
pros and cons across the analyzed dimensions.

This could work like a multi-criteria analysis model where each alternative is
evaluated against explicit criteria such as:

- product impact
- implementation cost
- governance clarity
- agent ergonomics
- risk reduction
- documentation burden
- future extensibility
- migration complexity

The goal is not to force the mathematically "best" option. The goal is to help
the owner choose consciously. A user may intentionally select a sub-optimal
alternative because it is cheaper, faster, easier to explain, or better aligned
with current project constraints. The important point is that the tradeoff is
visible, recorded, and auditable.

This scoring model should remain advisory. It must support owner judgment, not
replace governance decisions.
