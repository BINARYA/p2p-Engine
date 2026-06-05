# Local Development Specs

This directory contains local development specifications for the P2P Engine
repository.

These files are repository development aids. They are not P2P governance state,
not runtime behavior, and not release artifacts unless the owner explicitly
decides otherwise.

Use this layer when moving from accepted project direction to implementation
work:

1. Read the relevant steering files.
2. Create or update a feature spec under `specs/features/<feature-name>/`.
3. Keep `requirements.md`, `design.md`, and `tasks.md` aligned.
4. Implement code in `src/`, tests in `tests/`, and maintained docs in `docs/`.

Do not use `.p2p/changes`, `.p2p/work`, or `.p2p/outputs` to track coding
steps, branch state, or implementation checklists for this repository.

## Structure

```text
specs/
  steering/
    product.md
    domain.md
    structure.md
    tech.md
  features/
    _template/
      requirements.md
      design.md
      tasks.md
```

## Feature Rule

Every implementation feature should answer:

- Which requirement is being implemented?
- Which design decision covers it?
- Which task realizes it?
- Which test proves it works?
- If it derives from P2P, which proposal, choice, or decision originated it?

## Binding Generated Project Output

When a generated generic project export needs to update local software specs,
use:

```text
specs/methods/project-output-binding.md
specs/skills/project-output-binding.md
```

For substantial sync work, create a binding report from:

```text
specs/bindings/_template.md
```

The binding method prevents generated project theory from being mistaken for
implemented code. Tasks may be checked only when `src/`, `tests/`, `docs/`, or
observed command behavior provide evidence.

## Binding Accepted P2P Proposals

When an accepted P2P proposal is the source and no Change Set generic export is
appropriate yet, bind from:

- `p2p proposal show PROP-XXX`;
- `p2p proposal contribution list PROP-XXX`;
- refreshed `.p2p/project` feature output;
- existing local steering and feature specs.

Do not force a `spec export generic` only to create binding input. Create a
binding report under `specs/bindings/` and derive local feature specs from the
accepted proposal. Implementation tasks remain unchecked until code, tests,
docs, or observed command behavior prove completion.
