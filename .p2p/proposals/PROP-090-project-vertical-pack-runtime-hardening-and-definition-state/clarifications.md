# Clarifications - PROP-090

## Resolved Clarifications

- PROP-090 extends and hardens PROP-085. It is not an unrelated vertical system.
- p2p project vertical remains the canonical command namespace for the first
  production slice.
- .p2p/project/verticals remains the project-local vertical pack location.
- base_project remains the canonical fallback id.
- generic_project is not introduced in the first implementation.
- definition.yml is required for durable agent-guided project construction.
- definition-state writes are in scope, but only through a narrow structured
  patch/update contract.
- The full next-action engine is deferred.
- Installed local packs are resolved from P2P_HOME/verticals and ~/.p2p/verticals,
  with P2P_HOME precedence.
- Unsafe guidance validation is severity-dependent.
- Existing projects require explicit lock repair/migration; no implicit
  lockfile generation during ordinary reads.

## Remaining Clarifications

No blocking clarifications remain before deriving local development specs.

