# Assumptions - PROP-006

- P2P Engine remains local-first and file-based for this proposal.
- P2P Engine does not invoke AI providers directly.
- Agent integrations produce project-local instructions and metadata.
- Generated instructions are advisory guardrails, not hard security.
- P2P CLI, `.p2p` state, validation, readiness, and owner decisions remain the
  source of truth.
- Multiple agent integrations may coexist in the same project.
- `AGENTS.md` is the shared baseline instruction file.
- Tool-specific files are generated only when they add value for that adapter.
- Safe update and uninstall require file hashes.
- Existing generated instruction behavior must remain backward compatible.
- External adapter packages are deferred until the internal adapter lifecycle is
  stable.
