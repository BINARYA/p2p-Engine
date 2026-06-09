# Exploration - PROP-087

## Explored Design Direction

The proposal started with two style dimensions: technical verbosity and
formality. During refinement, a third dimension emerged: assertiveness. This is
not simply tone. It controls how strongly the agent challenges incomplete
reasoning, missing artifacts, unresolved questions, and weak evidence.

The resulting model is a project-level `interaction_style` with three explicit
numeric scales:

- `technical_verbosity`: how much engine/technical language appears in
  owner-facing communication.
- `formality`: how formal or informal the agent sounds.
- `assertiveness`: how persistent the agent is about gaps, ordering, evidence,
  and follow-up.

## Main Alternatives

### Project-Level Default

Store one interaction style for the project.

This is the selected first-slice direction because it gives all agents and
mediators the same interaction contract with the decision owner. It is simple,
stable, and compatible with generated project instructions.

### Per-Agent Defaults

Store different styles for Codex, Claude, generic agents, or future clients.

This may be useful later, but it risks inconsistent owner experience and more
configuration paths. It is deferred.

### Runtime Or Session Overrides

Allow temporary style changes during a command or conversation.

This is flexible but harder to audit and harder to expose consistently through
remote MCP. It is deferred until the project-level model is stable.

## Presets Considered And Rejected

Named presets were considered as a convenience layer, for example a mediator
preset or non-technical preset. The owner rejected persisted presets for the
first implementation because they do not scale when more dimensions are added.

The system should keep explicit independent scales as the source of truth.
Labels may be shown as explanatory UI/help text only.
