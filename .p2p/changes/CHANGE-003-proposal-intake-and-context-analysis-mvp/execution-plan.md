# Execution Plan - PROP-017

## Objective

Add a prompt-only intake workflow that helps users and agents classify new ideas against existing P2P project memory.

## Workstream 1 - Intake Model

Define:

- intake ID format;
- artifact location;
- input format;
- recommendation categories;
- suggested action schema.

Candidate structure:

```text
.p2p/intake/
  INTAKE-001/
    input.md
    context.md
    related-proposals.yml
    recommendation.md
    suggested-actions.yml
```

## Workstream 2 - Prompt Generation

Implement:

```bash
p2p intake prompt "raw idea"
```

The prompt should include:

- raw idea;
- registry status;
- proposal registry summary;
- change registry summary;
- decision registry summary;
- relation registry summary;
- project overview.

## Workstream 3 - Import And Status

Implement:

```bash
p2p intake import INTAKE-001 output/
p2p intake status
```

The import command should accept either a single `recommendation.md` file or a directory containing structured intake artifacts.

## Workstream 4 - Agent Guidance

Document how Codex/Claude should use intake:

- run registry refresh/status;
- generate intake prompt;
- ask the user whether to create proposal/contribution/choice/conflict;
- use P2P commands to record the selected path.

## Workstream 5 - Tests And Documentation

Add tests for:

- intake prompt creation;
- intake directory creation;
- intake import;
- intake status;
- no governance decision being recorded by intake.

Update README with the A/B/C multi-agent scenario.
