# Clarifications - PROP-017

## Intake Role

Intake is an advisory phase before or alongside proposal creation. It helps classify a raw idea against current project memory.

## Governance Boundary

Intake must not accept, reject, defer or supersede proposals. It can suggest those actions, but a governance/decision command must record them.

## Agent Use

Agents should use intake before creating a new proposal when the user submits an idea that may overlap existing work.

## Registry Dependency

Intake should use generated registries as the compact context layer. If registries are stale, the CLI should suggest:

```bash
p2p registry refresh
```
