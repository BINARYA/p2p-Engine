# Alternatives - PROP-087

## A. Project-Level Interaction Style

Store one `interaction_style` for the project.

Pros:

- Consistent experience for the decision owner.
- Simple schema and validation.
- Good default for generated project instructions.
- Easy to expose via `p2p project interaction-style`.

Cons:

- Less flexible for different agent surfaces.
- Requires a future extension if an owner wants agent-specific style.

Status: selected for the first implementation.

## B. Per-Agent Interaction Style

Store one style per agent profile.

Pros:

- Different clients can have different interaction contracts.
- Useful if one agent is used as a technical operator and another as a mediator.

Cons:

- More configuration paths.
- Higher risk of inconsistent owner experience.
- More generated instruction variants.

Status: deferred.

## C. Runtime Or Session Override

Allow temporary style changes for one session or command.

Pros:

- Flexible for debugging, demos, or exceptional conversations.
- Could let the owner temporarily raise or lower assertiveness.

Cons:

- Harder to persist and audit.
- Weak fit for remote MCP unless exposed through explicit stateful primitives.
- Can make behavior unpredictable across sessions.

Status: deferred.

## D. Named Presets

Persist named combinations of scale values.

Pros:

- Easy to choose at first.
- Friendly for non-technical setup.

Cons:

- Does not scale with three or more dimensions.
- Creates another abstraction layer to explain and maintain.
- Can hide the actual values that drive behavior.

Status: rejected for persisted configuration.
