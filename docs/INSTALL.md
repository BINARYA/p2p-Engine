# Installing P2P Engine

This guide describes how to install P2P Engine and use it with a new target
project.

If you want to contribute to the P2P Engine repository itself, use
[`CONTRIBUTING.md`](../CONTRIBUTING.md). Contributor setup is intentionally kept
separate from the normal new-project setup.

Current status:

```text
Source checkout: 0.5.0.
Supported distribution: project-local install from the GitHub Release wheel.
Transitional channel: versioned .whl files attached to GitHub Releases.
Future target: public package registry, e.g. PyPI.
```

## Requirements

- Python 3.11 or newer
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

Install the published 0.5.0 wheel from GitHub Releases:

```bash
.venv/bin/python -m pip install \
  https://github.com/BINARYA/p2p-Engine/releases/download/v0.5.0/p2p_engine-0.5.0-py3-none-any.whl
```

The wheel filename follows:

```text
p2p_engine-<version>-py3-none-any.whl
```

Download `SHA256SUMS` from the same release and verify the wheel before
installation:

```bash
sha256sum --check --ignore-missing SHA256SUMS
```

The check must name the selected wheel as `OK`. Checksums prove byte integrity;
they are not signatures or provenance attestations. The tag-triggered release
workflow also creates a GitHub Artifact Attestation for the exact published
files. Verification is optional and requires only the GitHub CLI:

```bash
gh attestation verify p2p_engine-0.5.0-py3-none-any.whl \
  --repo BINARYA/p2p-Engine
```

The attestation binds the downloaded artifact to the public repository,
release workflow and source commit. It is generated only for release tags, not
for normal pushes, pull requests or ordinary CI runs.

Verify the CLI:

```bash
.venv/bin/p2p --help
.venv/bin/python -m p2p_engine.mcp.server --help
.venv/bin/p2p doctor
.venv/bin/p2p status --format json
```

For a server worker integration such as WaveKit, verify the machine contract
before enabling writes:

```bash
.venv/bin/p2p version --format json
.venv/bin/p2p status --format json
.venv/bin/p2p runtime status --format json
.venv/bin/p2p workspace schema status --format json
.venv/bin/p2p workspace transaction status --format json
.venv/bin/p2p project snapshot --format json
```

Retryable WaveKit writes should pass the persisted server operation id as
`--operation-key wavekit:<uuid>` and recover uncertain responses with:

```bash
.venv/bin/p2p mutation status --operation-key wavekit:<uuid> --format json
```

Local MCP stdio remains an agent-facing protocol-native surface. It is not the
WaveKit worker retry transport and is not wrapped in `p2p-cli/v1`.

If the target project already contains `.p2p/project/runtime.yml`, read it
before choosing the wheel version. That contract declares:

```text
runtime.p2p.requires      compatible runtime range
runtime.p2p.recommended   exact recommended runtime version
```

After installing the recommended version, run:

```bash
.venv/bin/p2p runtime status
```

`p2p runtime status` is read-only. It reports compatibility and guidance; it
does not install, upgrade, downgrade, or modify the runtime environment.

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
Initial agent profile: adaptive default, or generic, codex, claude, all
Optional free domain classification
Structure starter: generic, empty
Rubric criteria customization for the generic starter
MCP setup hint
```

For a scriptable non-interactive setup:

```bash
.venv/bin/p2p init "My Project" \
  --domain software \
  --vertical binarya/software_project@2.0.0 \
  --mcp-hint
```

When `--agent` is omitted, `p2p init` uses an adaptive bootstrap default: it
detects the current client when possible and installs `generic` plus that
adapter. If detection is unreliable, it falls back to all built-in adapters for
compatibility and prints the fallback reason.

Detection is only a bootstrap hint. It does not make the detected client the
project identity and is not persisted in `.p2p/project.yml` or
`.p2p/agent-integrations.yml`.

To generate only selected adapters, repeat `--agent`:

```bash
.venv/bin/p2p init "My Project" \
  --agent codex \
  --agent claude
```

Use the lifecycle commands shown by init to manage the footprint later, such as
`p2p agent list`, `p2p agent install <adapter>`,
`p2p agent update <adapter>`, `p2p agent doctor <adapter>`,
`p2p agent uninstall <adapter>`, and
`p2p agent instructions refresh --profile <adapter>`.

The generated `AGENTS.md`, adapter-specific files, and `.p2p/agent-policy.yml`
include the project persistence policy: agents may analyze freely, but
meaningful persistent writes need classification, preview, and strict placement
unless the owner requested the exact operation and artifact.

The domain is optional free classification and is independent from structure.
Use exactly one structure source: `--starter generic`, `--starter empty`, or an
exact vertical release such as `--vertical binarya/software_project@2.0.0`.
Human text mode defaults to `generic`; JSON mode requires an explicit source.
Changing the domain later does not modify sections, rubrics or readiness.

New projects also receive:

```text
.p2p/project/runtime.yml
P2P-SETUP.md
```

The runtime contract uses exact initial compatibility for the installed P2P
Engine version. `P2P-SETUP.md` is generated from that contract and points back
to `.p2p/project/runtime.yml` as the source of truth.

For existing projects, ordinary `p2p init` does not recover a required but
missing runtime contract. Restore `.p2p/project/runtime.yml` from project
history, or use a future explicit recovery operation when one exists.

### Source-Control Boundary

P2P projects need only the filesystem-backed P2P workspace:

```bash
.venv/bin/p2p init "My Project" \
  --domain software \
  --vertical binarya/software_project@2.0.0 \
  --owner matteo \
  --mcp-hint
```

P2P Engine does not create or synchronize repositories, manage branches or
commits, configure provider credentials, or operate pull requests and releases.
When a project uses source control, configure it with external repository
tooling. Repository, issue, pull-request, commit and release identifiers may be
stored only as inert traceability references.

## Upgrade An Existing Project

Do not rerun `p2p init` to upgrade an existing P2P project. Upgrade the runtime
inside the project's `.venv`, then refresh generated P2P artifacts.

From the target project:

```bash
.venv/bin/python -m pip install --upgrade \
  https://github.com/BINARYA/p2p-Engine/releases/download/v<published-version>/p2p_engine-<published-version>-py3-none-any.whl

.venv/bin/p2p doctor
.venv/bin/p2p runtime status
.venv/bin/p2p agent doctor
.venv/bin/p2p agent list
.venv/bin/p2p agent update all
.venv/bin/p2p registry refresh
.venv/bin/p2p agent instructions refresh
.venv/bin/p2p validate
```

This upgrades the installed engine runtime. It does not inspect, pull, merge or
otherwise modify a source repository.

P2P Engine 0.5.0 is a clean break for current runtime state: it supports
workspace schema 4 and portable vertical schema 3 only. It does not provide
in-runtime migration, conversion or compatibility aliases for older workspace
or vertical schemas; recreate or externally convert older development
workspaces before using this runtime for governed writes.

## Publish A GitHub Release Wheel

This section is for P2P Engine maintainers publishing a GitHub Release artifact.
Normal target projects should install the published wheel instead.

The normal release path is automated by GitHub Actions. The owner first runs the
non-publishing candidate workflow for one exact, already-approved commit SHA:

```bash
gh workflow run release-candidate.yml \
  --ref main \
  -f ref=<approved-40-character-commit-sha>
```

Only after that exact SHA is green may the owner create and push its matching
version tag:

```bash
git tag -a v0.5.0 <approved-40-character-commit-sha> -m "P2P Engine v0.5.0"
git push origin v0.5.0
```

The candidate workflow runs public/full tests across the supported Python
matrix, runs `p2p validate`, builds the source distribution and wheel twice,
verifies archive contents, runs installed-wheel smoke tests, and retains the
exact verified artifact set for seven days. The tag workflow downloads that
same set, rechecks its checksums, generates GitHub Artifact Attestations and
creates the matching GitHub Release exactly once. It does not rebuild a second
unrelated upload set. The tag must match `pyproject.toml`: tag `v0.5.0`
requires `version = "0.5.0"`. Do not reuse an existing version or tag for
different contents.

Expected release assets:

```text
p2p_engine-<version>-py3-none-any.whl
p2p_engine-<version>.tar.gz
SHA256SUMS
```

GitHub stores the signed attestation alongside the repository rather than as a
fourth release asset. Maintainers do not manage signing keys or run a separate
command: pushing the final version tag triggers attestation automatically after
the complete candidate gate passes.

### Manual Build Fallback

Use this only when debugging the release workflow or preparing artifacts
manually.

From the P2P Engine source checkout:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
SOURCE_DATE_EPOCH=<approved-commit-timestamp> \
  ./scripts/build-release-candidate.sh
```

The expected wheel artifact is:

```text
dist/p2p_engine-<version>-py3-none-any.whl
```

This fallback is diagnostic only and does not authorize manual upload. A release
must still pass the create-only tag workflow. For example, the candidate set is:

```text
v0.5.0 -> p2p_engine-0.5.0-py3-none-any.whl, p2p_engine-0.5.0.tar.gz, SHA256SUMS
```

## Connect An Agent

P2P Engine is intended to be agent-mediated. After initialization, point your
agent at the target project, not at the P2P Engine checkout unless you are
contributing to P2P Engine itself.

The recommended local integration mode is MCP over `stdio`. In this mode, the
agent client starts the P2P MCP server as a local subprocess. If multiple
clients connect to the same target project, each client may start its own
process; shared P2P state lives in the target root's `.p2p/` directory.

The MCP server command should point at the governed P2P decision root. Prefer
the project-local Python module form:

```bash
/path/to/my-project/.venv/bin/python \
  -m p2p_engine.mcp.server \
  --root /path/to/my-project
```

Use that command in any MCP-capable client that supports local stdio servers.
`--root` selects the P2P project root used for decisions and state.
Some clients also let agents invoke the CLI directly from the target project.

P2P Engine does not currently run a shared Streamable HTTP MCP service. That is
the appropriate future model if multiple agents need to connect to one
long-running server process.

### Codex CLI

If `p2p-mcp-server` is available on `PATH`, this shorter fallback remains
available:

```bash
codex mcp add p2p-my-project -- \
  p2p-mcp-server \
  --root /path/to/my-project
```

Preferred project-local virtualenv form:

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
p2p consent grant proposal_decision_apply PROP-001@PREVIEW-TOKEN \
  --actor lorenzo --approved-by matteo
p2p consent status
p2p consent show CONSENT-001
```

Then the MCP client may call the matching decision tool with:

```json
{
  "tool": "p2p_proposal_decision_apply",
  "arguments": {
    "root": "/path/to/my-project",
    "proposal_id": "PROP-001",
    "event_type": "accepted",
    "preview_token": "<preview-token>",
    "operation_key": "<operation-key>",
    "reason": "Owner-approved reason",
    "actor_id": "lorenzo",
    "consent_id": "CONSENT-001"
  }
}
```

Current proposal decision operations:

```text
proposal_accept           -> p2p_proposal_accept
proposal_reject           -> p2p_proposal_reject
proposal_defer            -> p2p_proposal_defer
proposal_decision_apply   -> p2p_proposal_decision_apply
```

Consent receipts are declarative audit records. They are not strong
authentication. Hosted products must enforce their own identity, authorization
and transport controls before invoking P2P Engine.

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

For current project completeness, prefer read-only project readiness and
progress. Maturity output is a compatibility projection of readiness-v2
definition completeness.

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

Assign explicit project-memory scope before an authority-creating decision.
For this project-wide example, read the current memory and structure revisions,
then copy those exact values into the mutation:

```bash
p2p project memory classification --format json
p2p proposal scope show PROP-001 --format json
p2p proposal scope set PROP-001 \
  --kind project_global \
  --expected-memory-revision '<data.memory_classification.memory_revision>' \
  --expected-structure-revision '<data.memory_classification.structure.revision>' \
  --operation-key 'local:scope-prop-001' \
  --format json
```

Use `--kind sections --section-id <active-section-id>` instead when the
proposal concerns only named active sections. An `unassigned` proposal may be
drafted, but it cannot be accepted or reinstated.

Preview it when the owner decides:

```bash
p2p decision preview PROP-001 \
  --event-type accepted \
  --reason "This is the initial direction." \
  --format json
```

Apply only after reviewing the response, resubmitting its exact
`decided_on`, `operation_key`, source head when present, and `preview_token`
with `p2p decision apply ... --confirm`. The compatibility
`p2p proposal accept` command follows the same two-phase contract and does not
write without those apply ingredients.

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

- P2P Engine is distributed as a Python wheel and source distribution; a
  standalone compiled executable and public package-registry publication are
  not available yet.
- The current supported release is 0.5.0; normal users should install its
  published wheel rather than depend on a source checkout.
- MCP support is local stdio. Privileged write operations are available only
  through explicit permission-gated tools.
- Work is logical planning and handoff metadata. P2P Engine does not create or
  manage implementation branches, commits, review requests, merges or releases.
- Provider PR/MR creation and repository synchronization are external delivery
  integrations, not P2P Engine runtime primitives.
- Project readiness scoring is deterministic and conservative, not AI semantic review.
- Mediator and Web layers are not implemented.
