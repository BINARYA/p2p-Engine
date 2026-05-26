# Execution Plan — PROP-001 CLI Foundation

## Objective

Implement the first minimal `p2p` CLI so the manual bootstrap workflow can become repeatable automation.

## Workstreams

| ID | Name | Domain | Outcome |
|---|---|---|---|
| WS1 | Python package skeleton | software | Installable project with CLI entry point |
| WS2 | Core file model | software | Project and proposal artifacts can be generated and located |
| WS3 | CLI commands | software | Minimal commands cover init, proposal, contribution, decision, prompt, and status |
| WS4 | Prompt generator | software | Digest, clarify, plan, and task prompts are generated as files |
| WS5 | Validation and tests | quality | Basic schema and command behavior are covered by tests |
| WS6 | Documentation | documentation | README explains bootstrap and MVP usage |

## Milestones

- M1: Create Python package skeleton.
- M2: Implement `p2p init`.
- M3: Implement `p2p proposal create`.
- M4: Implement `p2p contribution add`.
- M5: Implement `p2p decision record`.
- M6: Implement prompt generation commands.
- M7: Implement `p2p status`.
- M8: Use CLI to create `PROP-002`.

## Dependencies

- Python packaging decision.
- YAML parser.
- Typer command structure.
- Stable `.p2p/` file layout.

## Risks

- Too many commands in the first slice may slow delivery.
- Interactive command UX can complicate tests.
- Prompt templates can become vague if artifact contracts are not explicit.
- Git branch behavior can introduce edge cases before the file workflow is stable.

## Implementation Strategy

Start with non-interactive commands and explicit flags where practical. Add interactive prompts only after the core command behavior is testable.

The first implementation should prioritize deterministic filesystem output.

## Next Step

Create the Python package skeleton and implement `p2p init`.

