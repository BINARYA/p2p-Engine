# Execution Plan - P2P-Governed Software Specification Lifecycle

## Implementation Shape

1. Update software-domain generated guidance so a request for specs is routed through the software vertical rather than directly to a standalone durable file.
2. Add the operational routing table to generated agent instructions and project skills for software projects.
3. Document the lifecycle from vertical definition to one or more proposals, choices, accepted direction, Change Set, P2P-native spec, and downstream export.
4. Add or update tests that verify generated guidance, docs, and template text do not describe standalone spec files as primary untracked project memory.
5. Reuse existing P2P primitives for the first slice: `proposal`, `choice`, `readiness`, `change`, `spec`, and `spec export`.

## Verification

- Generated software-domain instructions include the routing table.
- Documentation describes exploratory outlines, P2P-native specs, generated exports, stable documentation, and explicit external files distinctly.
- Tests cover spec-request routing, multi-proposal source model, readiness split, and PROP-093 action-preview interaction.
- No new external artifact registry or exporter target is introduced by this proposal.
