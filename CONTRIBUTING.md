# Contributing

P2P Engine is early-stage. Small, focused changes are easiest to review.

Before opening a large PR, please open an issue or proposal explaining the
problem, alternatives, and intended scope.

## Local Setup

```bash
git clone https://github.com/BINARYA/p2p-Engine.git
cd p2p-Engine
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
```

## Checks

Run:

```bash
python -m pytest -q
p2p validate
```

If `p2p` is not on `PATH`, use:

```bash
.venv/bin/p2p validate
```

## P2P Project State

Use P2P CLI or MCP primitives for `.p2p/` mutations. Do not edit generated
registries or internal P2P files by hand unless the change is explicitly about
storage format or repair.

Owner-controlled governance actions, such as accepting proposals or deciding
choices, should be explicit in the issue, PR, or maintainer instruction.

## Pull Requests

- Keep PRs scoped to one problem.
- Include tests or explain why tests are not applicable.
- Update docs when command behavior, workflows, or public boundaries change.
- Avoid broad refactors mixed with feature or documentation work.
