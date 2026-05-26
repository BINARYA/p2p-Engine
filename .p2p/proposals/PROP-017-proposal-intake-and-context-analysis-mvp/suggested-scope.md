# Suggested Scope - PROP-017

## Include

- Define the intake workflow for raw ideas and observations.
- Create an intake prompt generator backed by:
  - `proposals.yml`
  - `changes.yml`
  - `relations.yml`
  - `decisions.yml`
  - `project/overview.md`
- Define imported intake artifacts:
  - `input.md`
  - `context.md`
  - `related-proposals.yml`
  - `recommendation.md`
  - `suggested-actions.yml`
- Add initial commands:
  - `p2p intake prompt "raw idea"`
  - `p2p intake import INTAKE-001 output/`
  - `p2p intake status`
- Define possible recommendations:
  - create new proposal
  - add contribution to existing proposal
  - open choice
  - record conflict
  - defer idea
  - reject as duplicate suggestion

## Exclude

- Direct AI provider calls.
- MCP tools.
- Embeddings or vector search.
- Automatic acceptance/rejection of proposals.
- Automatic Git operations.
- Web UI.

## MVP Completion Boundary

The MVP is complete when a user or agent can submit a raw idea, generate a context-rich intake prompt, import analysis output and inspect suggested next actions.
