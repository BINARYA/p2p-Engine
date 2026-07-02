# Assumptions - PROP-090

## Accepted Baseline

- PROP-085 remains accepted and its MVP implementation is the baseline.
- PROP-090 completes and hardens that direction rather than replacing it.

## Compatibility

- Existing p2p project vertical commands should remain the public namespace for
  the first production slice.
- Existing project-local packs under .p2p/project/verticals should remain
  supported.
- Current single-file vertical.yml packs should remain loadable.
- base_project remains the canonical fallback vertical in the first
  implementation.

## Runtime State

- Agents need durable project definition state to continue guided work across
  sessions.
- definition.yml is project-definition state, not governance decision state.
- definition-state writes must go through supported CLI/service/MCP paths.

## Readiness And Maturity

- Project maturity remains governed by .p2p/project/rubrics.yml and enabled
  criteria.
- Vertical packs provide structured inputs and do not create a parallel maturity
  engine.

## Future Compatibility

- Wavekit compatibility matters, but remote search/install/update/publish is
  not required in the first implementation.
- The full next-action engine can be deferred until definition-state semantics
  stabilize.

