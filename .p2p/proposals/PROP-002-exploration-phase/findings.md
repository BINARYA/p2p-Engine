# Findings - PROP-002

## Existing Findings

```yaml
findings:
  - id: F001
    type: hidden_decision
    title: Exploration as repeatable phase
    impact: high
    related_to:
      - workflow
      - proposal_lifecycle

  - id: F002
    type: architectural_principle
    title: CLI engine remains source of truth
    impact: high
    related_to:
      - cli
      - agent_skills
      - filesystem_storage
```

## New Findings From Review

### F003 - Proposal maturity should be measurable

Proposal readiness should not be only a binary or informal state. A proposal can
have a formal maturity value from 0 to 100, computed from defined exploration
criteria.

### F004 - Pedantry should relax by maturity threshold

Agent strictness should be tied to maturity thresholds. The owner suggested
step thresholds at 70, 85, and 95.

### F005 - Computed readiness and owner override must be separate

Owner override should not falsify the computed score. The analytical score and
the governance decision must remain separate.

### F006 - Readiness should complement proposal lifecycle state

The design should not replace proposal lifecycle state with readiness. It should
combine both procedural state and analytical quality.

### F007 - Maturity is advisory unless owner-controlled policy says otherwise

The maturity score should guide the agent and improve `p2p next`, but it should
not silently replace owner decisions.

### F008 - Multi-criteria analysis can support maturity and decision quality

The maturity score and the alternatives comparison can share a multi-criteria
model that makes tradeoffs visible without replacing owner judgment.

### F009 - Score alone is not enough

A total score can hide essential weaknesses if strong secondary areas compensate
for missing critical dimensions. The readiness model should combine total score,
minimum gates, confidence, evidence, artifact quality gates, and override
metadata.

### F010 - Minimum gates are required for important proposals

For medium, architectural, and governance-critical proposals, certain criteria
must meet minimum quality thresholds.

### F011 - Confidence should be separate from score

A proposal can be well documented but based on fragile assumptions. Readiness
should include confidence and confidence reasons.

### F012 - Criterion scores need evidence

Each criterion score should point to the artifacts or sections that justify it.

### F013 - Artifact quality must cap criterion scoring

If an artifact is placeholder or thin, related criteria should be capped.

### F014 - `p2p next` should show delta to target

`p2p next` should estimate the gap to the target score and suggest the
highest-impact refinement actions.

### F015 - PROP-002 is governance-critical

PROP-002 defines how future proposals are explored, evaluated, and moved toward
decision. It is therefore governance-critical.

### F016 - Readiness must be profile-based and versioned

The 10-criterion model is the first default profile, not a hardcoded permanent
model. Every readiness assessment must record the profile id and version used to
compute it.

### F017 - Markdown remains authored, structured data remains machine-facing

Human-readable artifacts should remain authored in Markdown. Machine-readable
readiness data should live in metadata, readiness snapshots, registries,
exports, or audit records.

### F018 - Owner override is a governance event

Override is not a score edit. It creates an audited governance event such as
`accept_with_override`, preserving the computed score and recording reason,
authority, and failed gates.

### F019 - Governance gates must be configurable

The final product model must support warnings, hard gates, override policies,
reason requirements, and different behavior by governance profile, proposal
tier, and failure type.

### F020 - Open drafts should adopt readiness immediately

New proposals and current open drafts should use readiness. Already accepted
proposals should preserve historical decisions and use legacy markers or
optional retrospective assessment.

### F021 - Hybrid assessment is the right product model

The engine should validate, cap, aggregate, gate, and store readiness. Agents
should provide qualitative assessment, evidence, notes, confidence reasons, and
recommendations. The agent should not produce an opaque final score.

### F022 - MCP write operations are governance-gated, not merely deferred

Read tools can be agent-accessible. Write/governance operations such as
readiness override or accept-with-override are part of the product model, but
must require explicit governance permission and must not be agent-autonomous.

### F023 - Readiness override belongs primarily to acceptance

The primary UX should be `p2p proposal accept --override-readiness --reason`.
This communicates that the owner is accepting despite readiness gaps. A
standalone readiness override risks implying that computed readiness is being
modified.

### F024 - `needs_owner_input` is a first-class artifact state

`needs_owner_input` is different from `thin`. An artifact can be specific and
useful but blocked because only the owner can choose a policy, strictness level,
or strategic direction.

### F025 - Current unresolved-question counting is semantically weak

`p2p explore status` can report a different unresolved count than the number of
implementation decision points visible in `open-questions.md`. Future status and
readiness logic should distinguish explicit questions, decision items, grouped
subtopics, and artifact quality states.
