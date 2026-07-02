# Open Questions - PROP-090

## Blocking Questions

None currently open.

## Resolved Owner Questions

- Q001: Implement definition-state writes in the first production slice through
  a narrow structured patch/update contract.
- Q002: Defer the full next-action engine; expose JSON context and optionally
  next_suggested_action in definition.yml.
- Q003: Omit generic_project from the first implementation; keep base_project
  canonical.
- Q004: Resolve installed packs from both P2P_HOME/verticals and ~/.p2p/verticals
  with P2P_HOME precedence.
- Q005: Use severity-dependent unsafe guidance validation.
- Q006: Generate lockfiles automatically for new init/select flows; existing
  projects require explicit repair/migration.

## Deferred Follow-Up Questions

- Should a top-level p2p vertical alias be introduced after the project-scoped
  commands are stable?
- Should generic_project ever become a non-breaking alias for base_project?
- Which Wavekit trust/signature policy is required before remote packs are
  enabled?
- What prioritization algorithm should a future next-action engine use after
  definition-state semantics stabilize?

