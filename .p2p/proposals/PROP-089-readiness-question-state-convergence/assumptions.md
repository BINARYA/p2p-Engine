# Assumptions - PROP-089

- `questions.yml` is the correct durable lifecycle record for proposal
  questions.
- `open-questions.md` remains valuable as a human-facing artifact, but should
  not be the source of truth when structured state exists.
- Readiness is advisory and must not perform owner governance decisions.
- Existing proposals without structured question state must remain valid.
- The improvement should be implemented in services, not directly in CLI or MCP
  handlers.

