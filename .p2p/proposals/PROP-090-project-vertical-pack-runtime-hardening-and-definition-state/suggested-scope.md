# Suggested Scope - PROP-090

## First Production Slice

- Compatibility audit of the current PROP-085 MVP.
- Canonical multi-file pack schema.
- Single-file pack compatibility loader.
- Resolver precedence across explicit path, project-local, P2P_HOME, user-home,
  packaged seed resources, future registry source, and base_project fallback.
- vertical.lock.yml for new init/select flows.
- Explicit repair/migration command for existing active vertical state without a
  lockfile.
- definition.yml generation and validation.
- Narrow structured definition-state update contract.
- JSON context surfaces for active vertical, sections, section detail, rubrics,
  and definition state.
- Init integration for vertical/profile/module/rubric setup without full
  section interview.
- Severity-dependent pack safety validation.
- Docs and tests for compatibility, resolver, lockfile, definition state,
  validation, and agent guidance.

## Deferred

- Wavekit remote search/install/update/publish.
- Full p2p project next-action --json engine.
- Top-level p2p vertical alias.
- generic_project alias for base_project.
- Advanced state migration and long-answer merge behavior.
- Full interactive definition editor.

## Explicitly Out Of Scope

- Executable vertical plugins.
- Domain-specific agent skills for every vertical.
- Silent fallback after lockfile creation.
- Automatic retroactive lockfile generation during validation/readiness/export.
- Replacing project rubrics or changing enabled:false semantics.

