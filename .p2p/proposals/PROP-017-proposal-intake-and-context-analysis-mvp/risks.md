# Risks - PROP-017

## R001 - False Duplicate Detection

Risk:
The intake process may classify a genuinely new idea as already covered.

Mitigation:
Output should include confidence, rationale and suggested human review. Intake recommendations are advisory.

## R002 - Agent Overreach

Risk:
An agent may treat an intake recommendation as a decision.

Mitigation:
Make governance explicit: intake can suggest `create proposal`, `add contribution`, `open choice`, or `record conflict`, but cannot accept/reject proposals.

## R003 - Registry Drift

Risk:
Intake quality depends on registries being current.

Mitigation:
Require `p2p registry status` in intake context and recommend `p2p registry refresh` when stale.

## R004 - Overcomplex MVP

Risk:
Semantic search, embeddings, AI adapters or MCP could make the first implementation too large.

Mitigation:
Keep the MVP prompt-only, file-based and registry-backed.
