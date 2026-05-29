# Installing P2P Engine

This guide describes how to install P2P Engine and use it with a new target
project.

If you want to contribute to the P2P Engine repository itself, use
[`CONTRIBUTING.md`](../CONTRIBUTING.md). Contributor setup is intentionally kept
separate from the normal new-project setup.

Current status:

```text
Supported today: install from source with Python virtualenv.
Future target: packaged or compiled CLI distribution.
```

## Requirements

- Python 3.11 or newer
- Git
- A shell with virtualenv support
- Optional: an MCP-capable or CLI-capable agent client

## Install From Source

Clone the repository:

```bash
git clone https://github.com/BINARYA/p2p-Engine.git
cd p2p-Engine
```

If you prefer SSH and already have GitHub SSH keys configured:

```bash
git clone git@github.com:BINARYA/p2p-Engine.git
cd p2p-Engine
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv
. .venv/bin/activate
```

Install P2P Engine in editable mode:

```bash
pip install -e ".[dev]"
```

Verify the CLI:

```bash
p2p --help
python -m p2p_engine.mcp.server --help
python -m pytest -q
```

If `p2p` is not on `PATH`, call it through the virtualenv:

```bash
/path/to/p2p-Engine/.venv/bin/p2p --help
```

## Initialize A New Target Project

The repository you cloned above is the engine checkout. The target project is a
different directory: it is the project where `.p2p/` state, generated agent
instructions, proposals, decisions, Change Sets, and exports will live.

Create a project directory:

```bash
mkdir my-project
cd my-project
```

Run the guided wizard:

```bash
/path/to/p2p-Engine/.venv/bin/p2p init
```

The wizard asks for:

```text
Project name
Initial agent profile: generic, codex, claude, all
Repository mode: local, cloud
Project domain: generic, software, grant_document, board_game
Rubric criteria customization
MCP setup hint
```

For a scriptable non-interactive setup:

```bash
/path/to/p2p-Engine/.venv/bin/p2p init "My Project" \
  --agent codex \
  --repository local \
  --domain software \
  --mcp-hint
```

## Connect An Agent

P2P Engine is intended to be agent-mediated. After initialization, point your
agent at the target project, not at the P2P Engine checkout unless you are
contributing to P2P Engine itself.

The MCP server command has this shape:

```bash
/path/to/p2p-Engine/.venv/bin/python \
  -m p2p_engine.mcp.server \
  --root /path/to/my-project
```

Use that command in any MCP-capable client that supports local stdio servers.
Some clients also let agents invoke the CLI directly from the target project.

In the agent, start with:

```text
Use the P2P MCP server for this project.
Start with p2p_context.
Use CLI/MCP primitives for P2P writes.
Do not edit .p2p files manually.
If a primitive is missing, stop and report what is missing.
```

## Verify A Target Project

From inside the project directory:

```bash
/path/to/p2p-Engine/.venv/bin/p2p context --budget small
/path/to/p2p-Engine/.venv/bin/p2p validate
/path/to/p2p-Engine/.venv/bin/p2p registry refresh
/path/to/p2p-Engine/.venv/bin/p2p next
```

Assess structural readiness:

```bash
/path/to/p2p-Engine/.venv/bin/p2p assess refresh
/path/to/p2p-Engine/.venv/bin/p2p assess show
```

Assess project definition maturity:

```bash
/path/to/p2p-Engine/.venv/bin/p2p project rubrics show
/path/to/p2p-Engine/.venv/bin/p2p assess maturity refresh
/path/to/p2p-Engine/.venv/bin/p2p assess maturity show
```

## Configure MCP Locally With Codex CLI

If `p2p-mcp-server` is available on `PATH`:

```bash
codex mcp add p2p-my-project -- \
  p2p-mcp-server \
  --root /path/to/my-project
```

If it is not on `PATH`, or if your editable install did not refresh console scripts yet, use the Python module from the source checkout:

```bash
codex mcp add p2p-my-project -- \
  /path/to/p2p-Engine/.venv/bin/python \
  -m p2p_engine.mcp.server \
  --root /path/to/my-project
```

List configured MCP servers:

```bash
codex mcp list
```

In an MCP-capable agent, ask for a compact status first:

```text
Use the P2P MCP server and show p2p_context for this project.
```

The agent should use compact context before broad file reads.

## Optional Manual CLI Trial

Most users should let agents use these primitives through MCP or CLI access.
Manual CLI use is useful for inspection, debugging, recovery, and learning the
P2P object model.

Create a proposal:

```bash
p2p proposal create "First project direction" \
  --problem "The project needs a clear initial direction." \
  --goal "Define the first accepted scope." \
  --proposal "Start with a small verified project definition." \
  --acceptance "The owner can review and decide the proposal."
```

Inspect it:

```bash
p2p proposal show PROP-001
```

Accept it when the owner decides:

```bash
p2p proposal accept PROP-001 --reason "This is the initial direction."
```

Create a Change Set:

```bash
p2p change create --from PROP-001
```

## Troubleshooting

`p2p: command not found`

Use the virtualenv binary:

```bash
/path/to/p2p-Engine/.venv/bin/p2p --help
```

or activate the virtualenv:

```bash
. /path/to/p2p-Engine/.venv/bin/activate
```

MCP server cannot start

Use the explicit Python module command:

```bash
/path/to/p2p-Engine/.venv/bin/python -m p2p_engine.mcp.server --root /path/to/project
```

Agent tries to edit `.p2p/` by hand

Tell it to use CLI or MCP primitives only:

```text
Use p2p_context first. If a write primitive is missing, stop and report what is missing.
Do not create or edit .p2p files manually.
```

Project looks stale

Run:

```bash
p2p validate
p2p registry refresh
p2p project refresh
p2p assess refresh
```

## Current Limitations

- Installation is source-based.
- Packaged or compiled CLI distribution is future work.
- MCP support is local stdio MVP.
- Rubric maturity scoring is deterministic and conservative, not AI semantic review.
- Mediator and Web layers are not implemented.
