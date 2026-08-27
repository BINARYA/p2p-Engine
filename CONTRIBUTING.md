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

## Enable Your Agent For This Repository

This section is only for contributors who want an agent to add proposals,
contributions, or implementation changes to the P2P Engine repository itself.
Normal users should follow `docs/INSTALL.md` instead and initialize P2P inside
their own target project.

From the P2P Engine checkout, verify the implementation directly:

```bash
.venv/bin/python -m pip check
./scripts/test-public.sh -q
```

If your agent supports MCP local stdio servers, configure it only against an
actual P2P project-state root. The P2P Engine source checkout is not that root:

```bash
/absolute/path/to/p2p-Engine/.venv/bin/python \
  -m p2p_engine.mcp.server \
  --root /absolute/path/to/projects/p2p-engine-project
```

For Codex CLI, the command has this shape:

```bash
codex mcp add p2p-engine -- \
  /absolute/path/to/p2p-Engine/.venv/bin/python \
  -m p2p_engine.mcp.server \
  --root /absolute/path/to/projects/p2p-engine-project
```

Then tell the agent:

```text
Use the P2P MCP server for the separate P2P Engine project-state repository.
Start with p2p_context.
Use P2P CLI/MCP primitives for proposals, contributions, Change Sets, validation, and registries.
Do not edit .p2p files manually.
Do not accept, reject, defer, decide, merge, push, or publish unless the maintainer explicitly instructs that exact action.
```

For non-MCP governance work, pass the separate root explicitly:

```bash
.venv/bin/p2p context --budget small --root ../projects/p2p-engine-project
.venv/bin/p2p proposal list --root ../projects/p2p-engine-project
.venv/bin/p2p change status --root ../projects/p2p-engine-project
```

When proposing substantial work for P2P Engine, prefer this flow:

```bash
.venv/bin/p2p proposal create "Short Title" \
  --problem "What gap or risk this addresses." \
  --context "Relevant project context." \
  --goal "What success looks like." \
  --proposal "Proposed direction." \
  --acceptance "How maintainers can verify it." \
  --root ../projects/p2p-engine-project

.venv/bin/p2p registry refresh --root ../projects/p2p-engine-project
.venv/bin/p2p validate --root ../projects/p2p-engine-project
```

Maintainer governance remains explicit. A contributor or agent may draft,
refine, and analyze proposals, but proposal decisions and repository-level Git
operations require maintainer instruction.

## Checks

Run:

```bash
python -m pytest -q
python scripts/check-source-boundary.py
```

## P2P Project State

The canonical design state is in the separate
`../projects/p2p-engine-project/` repository. Use P2P CLI or MCP primitives for
its `.p2p/` mutations. Do not edit generated
registries or internal P2P files by hand unless the change is explicitly about
storage format or repair.

Owner-controlled governance actions, such as accepting proposals or deciding
choices, should be explicit in the issue, PR, or maintainer instruction.

## Pull Requests

- Keep PRs scoped to one problem.
- Include tests or explain why tests are not applicable.
- Update docs when command behavior, workflows, or public boundaries change.
- Avoid broad refactors mixed with feature or documentation work.
