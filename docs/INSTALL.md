# Installing P2P Engine

This guide describes how to install P2P Engine and use it with a new target
project.

If you want to contribute to the P2P Engine repository itself, use
[`CONTRIBUTING.md`](../CONTRIBUTING.md). Contributor setup is intentionally kept
separate from the normal new-project setup.

Current status:

```text
Supported today: project-local install from a GitHub Release wheel.
Transitional channel: versioned .whl files attached to GitHub Releases.
Future target: public package registry, e.g. PyPI.
```

## Requirements

- Python 3.11 or newer
- Git
- A shell with virtualenv support
- Optional: an MCP-capable or CLI-capable agent client

## Install Into A Project

Install P2P Engine into the target project's own virtual environment. Do not
clone or reference a separate P2P Engine source checkout for normal project use.

Create a project directory:

```bash
mkdir my-project
cd my-project
python3 -m venv .venv
```

Install a versioned wheel from GitHub Releases:

```bash
.venv/bin/python -m pip install \
  https://github.com/BINARYA/p2p-Engine/releases/download/v0.1.5/p2p_engine-0.1.5-py3-none-any.whl
```

Replace `v0.1.5` and `p2p_engine-0.1.5-py3-none-any.whl` with the release you
intend to use. The wheel filename is expected to follow:

```text
p2p_engine-<version>-py3-none-any.whl
```

Verify the CLI:

```bash
.venv/bin/p2p --help
.venv/bin/python -m p2p_engine.mcp.server --help
.venv/bin/p2p doctor
```

GitHub Release wheels are a transitional distribution model. The planned public
package flow is:

```bash
.venv/bin/python -m pip install p2p-engine
.venv/bin/python -m pip install --upgrade p2p-engine
```

## Initialize A New Target Project

The target project is the project where `.p2p/` state, generated agent
instructions, proposals, decisions, Change Sets, and exports will live. It also
contains the `.venv` with the `p2p` runtime.

Run the guided wizard:

```bash
.venv/bin/p2p init
```

The wizard asks for:

```text
Project name
Initial agent profile: generic, codex, claude, all
Repository mode: local, cloud
Domain template: none, custom, generic, software, grant_document, board_game
Rubric criteria customization, when a template supplies criteria
MCP setup hint
```

For a scriptable non-interactive setup:

```bash
.venv/bin/p2p init "My Project" \
  --repository local \
  --domain software \
  --mcp-hint
```

By default, `p2p init` creates the generic baseline plus all built-in
project-local agent integrations. To generate only selected adapters, repeat
`--agent`:

```bash
.venv/bin/p2p init "My Project" \
  --agent codex \
  --agent claude \
  --repository local
```

If you omit `--domain`, P2P starts with unresolved domain and rubric state. The
first recommended project activities are then to define the domain and define
the rubric with the user and agent. Use a domain template such as `software`
when you want P2P to pre-populate rubric criteria at init time.

### Local vs Remote-Backed Projects

Local projects need only the P2P workspace:

```bash
.venv/bin/p2p init "My Project" \
  --repository local \
  --domain software \
  --owner matteo \
  --mcp-hint
```

Remote-backed projects add a P2P remote profile and a Git remote. The current
MVP keeps these as explicit steps:

```bash
.venv/bin/p2p init "My Project" \
  --repository cloud \
  --domain software \
  --owner matteo \
  --mcp-hint

git remote add origin git@github.com:ORG/REPO.git

.venv/bin/p2p project remote configure \
  --mode remote \
  --provider github \
  --remote origin \
  --url git@github.com:ORG/REPO.git

.venv/bin/p2p project remote show
.venv/bin/p2p sync status
```

To modify the remote profile later, run `p2p project remote configure` again.
To mark the project local-only again:

```bash
.venv/bin/p2p project remote configure --mode local
```

P2P does not create provider repositories, configure SSH keys, create tokens, or
change GitHub/GitLab branch protection in the MVP. It records P2P profile
metadata and validates local Git readiness. Proposal `PROP-073` tracks a more
ergonomic one-command remote initialization flow.

## Upgrade An Existing Project

Do not rerun `p2p init` to upgrade an existing P2P project. Upgrade the runtime
inside the project's `.venv`, then refresh generated P2P artifacts.

From the target project:

```bash
.venv/bin/python -m pip install --upgrade \
  https://github.com/BINARYA/p2p-Engine/releases/download/v0.1.5/p2p_engine-0.1.5-py3-none-any.whl

.venv/bin/p2p doctor
.venv/bin/p2p agent doctor
.venv/bin/p2p agent list
.venv/bin/p2p agent update all
.venv/bin/p2p registry refresh
.venv/bin/p2p agent instructions refresh
.venv/bin/p2p validate
```

This upgrades the installed engine runtime. It does not pull or merge the target
project repository. For project Git synchronization, use the P2P sync commands
documented for managed collaboration.

## Publish A GitHub Release Wheel

This section is for P2P Engine maintainers publishing a GitHub Release artifact.
Normal target projects should install the published wheel instead.

The normal release path is automated by GitHub Actions. Update the package
version, commit and push `main`, then push a matching version tag:

```bash
# pyproject.toml
# [project]
# version = "0.1.5"

git add pyproject.toml
git commit -m "Bump version to 0.1.5"
git push origin main

git tag -a v0.1.5 -m "P2P Engine v0.1.5"
git push origin v0.1.5
```

The release workflow runs tests, runs `p2p validate`, builds the source
distribution and wheel, and uploads both files to the matching GitHub Release.
The tag must match `pyproject.toml`: tag `v0.1.5` requires
`version = "0.1.5"`. Do not reuse an existing version or tag for different
contents.

Expected release assets:

```text
p2p_engine-<version>-py3-none-any.whl
p2p_engine-<version>.tar.gz
```

### Manual Build Fallback

Use this only when debugging the release workflow or preparing artifacts
manually.

From the P2P Engine source checkout:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
python -m build
```

The expected wheel artifact is:

```text
dist/p2p_engine-<version>-py3-none-any.whl
```

Attach that `.whl` and the matching `.tar.gz` to the GitHub Release only if the
automated workflow is unavailable. For example:

```text
v0.1.5 -> p2p_engine-0.1.5-py3-none-any.whl, p2p_engine-0.1.5.tar.gz
```

## Connect An Agent

P2P Engine is intended to be agent-mediated. After initialization, point your
agent at the target project, not at the P2P Engine checkout unless you are
contributing to P2P Engine itself.

The recommended local integration mode is MCP over `stdio`. In this mode, the
agent client starts the P2P MCP server as a local subprocess. If multiple
clients connect to the same target project, each client may start its own
process; shared state lives in the target repository, `.p2p/`, Git, and P2P
core storage.

The MCP server command has this shape:

```bash
.venv/bin/python \
  -m p2p_engine.mcp.server \
  --root /path/to/my-project
```

Use that command in any MCP-capable client that supports local stdio servers.
Some clients also let agents invoke the CLI directly from the target project.

P2P Engine does not currently run a shared Streamable HTTP MCP service. That is
the appropriate future model if multiple agents need to connect to one
long-running server process.

### Codex CLI

If `p2p-mcp-server` is available on `PATH`:

```bash
codex mcp add p2p-my-project -- \
  p2p-mcp-server \
  --root /path/to/my-project
```

If it is not on `PATH`, use the Python module from the project-local virtualenv:

```bash
codex mcp add p2p-my-project -- \
  .venv/bin/python \
  -m p2p_engine.mcp.server \
  --root /path/to/my-project
```

Verify:

```bash
codex mcp list
```

Inside the Codex terminal UI, use:

```text
/mcp
```

Codex CLI and the Codex IDE extension share MCP configuration through
`config.toml`. You can also configure the server directly:

```toml
[mcp_servers.p2p-my-project]
command = "/path/to/my-project/.venv/bin/python"
args = ["-m", "p2p_engine.mcp.server", "--root", "/path/to/my-project"]
startup_timeout_sec = 20
tool_timeout_sec = 60
```

### Claude Code

For Claude in the terminal, add the same local stdio server:

```bash
claude mcp add --transport stdio p2p-my-project -- \
  /path/to/my-project/.venv/bin/python \
  -m p2p_engine.mcp.server \
  --root /path/to/my-project
```

Verify:

```bash
claude mcp list
```

Claude Code also supports project-scoped MCP configuration:

```bash
claude mcp add --transport stdio --scope project p2p-my-project -- \
  /path/to/my-project/.venv/bin/python \
  -m p2p_engine.mcp.server \
  --root /path/to/my-project
```

Use project scope only when you intentionally want the project to carry a
shared `.mcp.json` MCP config. Project-scoped servers may require client-side
approval for safety.

Inside Claude Code, use:

```text
/mcp
```

### Claude Desktop

Claude Desktop local MCP setup uses its MCP configuration file. Add a server
entry with the same command and arguments:

```json
{
  "mcpServers": {
    "p2p-my-project": {
      "command": "/path/to/my-project/.venv/bin/python",
      "args": [
        "-m",
        "p2p_engine.mcp.server",
        "--root",
        "/path/to/my-project"
      ]
    }
  }
}
```

Open Claude Desktop settings, edit the local MCP config, save it, and restart
Claude Desktop if required by the client.

Documented config paths:

```text
macOS:   ~/Library/Application Support/Claude/claude_desktop_config.json
Windows: %APPDATA%\Claude\claude_desktop_config.json
```

Do not assume the Claude Desktop config path is the same on unsupported or
undocumented platforms.

### VS Code With GitHub Copilot Agent

VS Code's MCP configuration is separate from Codex configuration. Use workspace
`.vscode/mcp.json` or the user profile MCP configuration:

```json
{
  "servers": {
    "p2p-my-project": {
      "type": "stdio",
      "command": "${workspaceFolder}/.venv/bin/python",
      "args": [
        "-m",
        "p2p_engine.mcp.server",
        "--root",
        "${workspaceFolder}"
      ]
    }
  }
}
```

### Other MCP Clients

For Codex app, IDE extensions, or other MCP-capable clients, use the client's
MCP configuration UI or config file with these fields:

```text
name: p2p-my-project
transport: stdio
command: /path/to/my-project/.venv/bin/python
args: -m p2p_engine.mcp.server --root /path/to/my-project
```

Do not point the MCP server at the P2P Engine checkout unless you are
contributing to P2P Engine itself. For contributor setup, use
[`CONTRIBUTING.md`](../CONTRIBUTING.md).

In the agent, start with:

```text
Use the P2P MCP server for this project.
Start with p2p_context.
Use CLI/MCP primitives for P2P writes.
Do not edit .p2p files manually.
If a primitive is missing, stop and report what is missing.
```

## Permission-Gated MCP Operations

MCP can perform selected privileged operations only when an owner has granted a
matching consent receipt. The CLI creates and audits those receipts.

Create or inspect project identities:

```bash
p2p permissions show
p2p permissions actor add lorenzo --role contributor
```

Grant one operation:

```bash
p2p consent grant proposal_publish PROP-001 --actor lorenzo --approved-by matteo
p2p consent status
p2p consent show CONSENT-001
```

Then the MCP client may call the matching tool with:

```json
{
  "tool": "p2p_proposal_publish",
  "arguments": {
    "root": "/path/to/my-project",
    "proposal_id": "PROP-001",
    "actor_id": "lorenzo",
    "consent_id": "CONSENT-001"
  }
}
```

Common proposal lifecycle operations:

```text
proposal_publish          -> p2p_proposal_publish
proposal_request_review   -> p2p_proposal_request_review
proposal_accept           -> p2p_proposal_accept
proposal_reject           -> p2p_proposal_reject
proposal_defer            -> p2p_proposal_defer
proposal_accept_branch    -> p2p_proposal_accept_branch
proposal_reject_branch    -> p2p_proposal_reject_branch
proposal_merge            -> p2p_proposal_merge
proposal_finalize         -> p2p_proposal_finalize
proposal_cleanup          -> p2p_proposal_cleanup
sync_pull                 -> p2p_sync_pull
sync_push                 -> p2p_sync_push
```

Consent receipts are declarative audit records. They are not strong
authentication. In cloud-backed projects, provider permissions, branch
protection, and token scopes remain the enforcement layer for protected remote
state.

## Verify A Target Project

From inside the project directory:

```bash
.venv/bin/p2p context --budget small
.venv/bin/p2p validate
.venv/bin/p2p registry refresh
.venv/bin/p2p next
```

Assess structural readiness:

```bash
.venv/bin/p2p assess refresh
.venv/bin/p2p assess show
```

Assess project definition maturity:

```bash
.venv/bin/p2p project rubrics show
.venv/bin/p2p assess maturity refresh
.venv/bin/p2p assess maturity show
```

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

Run the runtime diagnostics with the first available command:

```bash
p2p agent doctor --root /path/to/project
.venv/bin/p2p agent doctor --root /path/to/project
python -m p2p_engine agent doctor --root /path/to/project
```

Discovery order for agents:

```text
p2p
.venv/bin/p2p
python -m p2p_engine
available MCP tools
```

If `p2p` is not on `PATH`, use the project-local virtualenv binary:

```bash
.venv/bin/p2p --help
```

or activate the virtualenv:

```bash
. .venv/bin/activate
```

If the package is importable but the console script is not installed, use:

```bash
python -m p2p_engine --help
```

MCP server cannot start

Use the explicit Python module command:

```bash
.venv/bin/python -m p2p_engine.mcp.server --root /path/to/project
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
- MCP support is local stdio. Selected write operations are available only
  through explicit permission-gated tools.
- Provider PR/MR creation is not implemented; request-review records handoff
  metadata and guidance only.
- Full Work lifecycle parity through permission-gated MCP is not implemented.
- Rubric maturity scoring is deterministic and conservative, not AI semantic review.
- Mediator and Web layers are not implemented.
