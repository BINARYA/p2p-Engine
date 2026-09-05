# Project Integration Artifacts

P2P-managed agent instructions are regenerable runtime projections. They are
not canonical project memory, are excluded from canonical bundles and semantic
digests, and do not expose the selected storage adapter.

## Implemented Access Profiles

| Profile | Local memory | Agent surfaces | Authority | Current support |
|---|---:|---|---|---|
| `standalone` | yes | CLI and MCP `stdio` | local | implemented |
| `linked-local` | replica | CLI sync/watch and domain MCP `stdio` | WaveKit | durable feed, automatic MCP read catch-up and authenticated online MCP writes; offline writes blocked |
| `remote-only` | no | web, API and MCP HTTP | WaveKit | WaveKit-owned; local P2P rendering is inapplicable |

`linked-local` is rendered only after a transfer receipt or clone snapshot
establishes the remote binding. Catch-up records source, revision and freshness;
offline reads are visibly stale and offline writes are rejected. `remote-only`
is a real WaveKit access mode, but it has no client-local P2P project, CLI,
MCP `stdio`, manifest or generated files. WaveKit owns its authenticated web,
API and MCP HTTP instructions and tool discovery. Local P2P integration
commands therefore report the profile boundary and reject rendering without
writing. This does not constrain the private server-side storage used by the
WaveKit worker.

## Independent Compatibility Dimensions

The integration manifest records these dimensions separately:

- P2P Engine runtime/generator version;
- local-memory schema version;
- domain contract;
- canonical-bundle contract;
- durable synchronization protocol, negotiated independently;
- linked-project lifecycle protocol, negotiated independently;
- `p2p-project-integration/v1` integration contract and manifest version.

A refresh of agent artifacts is not a memory migration. A future sync-protocol
change is not an integration-contract upgrade. A runtime that encounters a
newer unsupported integration major preserves it and reports `unsupported`
instead of overwriting it.

## Artifact Inventory

Clean initialization can generate the following inventory according to the
selected agent adapters:

| Artifact | Owner | Ownership model | Renderer or source |
|---|---|---|---|
| `AGENTS.md` | P2P or user+P2P | whole file on clean init; marked section in an existing user file | generic renderer |
| `P2P-INTEGRATION.md` | P2P | whole file | access-profile renderer |
| `P2P-SETUP.md` | P2P runtime | whole file | runtime-contract renderer |
| `.p2p/agent-policy.yml` | P2P | whole file | policy renderer |
| `.agents/skills/p2p-project/**` | P2P | whole files | Codex skill renderers |
| `.agents/skills/p2p-project-curator/**` | P2P | whole files | curator skill renderers |
| `CLAUDE.md` | P2P | whole file | Claude renderer |
| `.cursor/rules/p2p.mdc` | P2P | whole file | Cursor renderer |
| `.github/copilot-instructions.md` | P2P | whole file | Copilot renderer |
| `GEMINI.md` | P2P | whole file | Gemini renderer |
| `.p2p/agent-integrations.yml` | P2P | integration manifest | lifecycle service |

OpenCode consumes the shared `AGENTS.md` baseline and has no separate file.
P2P reports a root-aware MCP `stdio` command but does not generate or mutate a
client's host configuration file. Such configuration remains user-owned.

Every whole-file header or managed-section marker declares the generator
version, integration contract, active profile and ownership boundary.
The manifest records stable paths, ownership kind and SHA-256 digests. Output
is deterministic; timestamps are not part of the manifest.

## Lifecycle

Use the local CLI for host-file mutations:

```bash
p2p integration status --format json
p2p integration install --profile standalone --agent all --format json
p2p integration refresh --profile standalone --format json
p2p integration profile standalone --format json
p2p integration remove --format json
```

Do not manually select `linked-local` as a substitute for transfer. The
authority-transfer service performs the profile transition only after atomic
local binding. See [`AUTHORITY-TRANSFER.md`](AUTHORITY-TRANSFER.md).

Generated linked-local guidance exposes lifecycle status/preview and
publication inspection through read-only MCP only. Destructive or
authority-affecting lifecycle apply remains owner-run CLI, and an unavailable
WaveKit lifecycle capability is never bypassed with direct `.p2p` edits. See
[`LINKED-PROJECT-LIFECYCLE.md`](LINKED-PROJECT-LIFECYCLE.md).

The operations are idempotent. Candidate files and the manifest are staged and
committed by one atomic workspace transaction. Source hashes are checked again
under the transaction lock; normal failures roll back, while an external edit
that prevents rollback leaves the existing recovery journal.

Refresh changes only proven P2P whole files or the section delimited by the
stable `p2p-project-access` markers. Content outside that section is preserved
byte for byte. Duplicate, malformed, nested or unmatched markers fail closed.
Removal deletes only unchanged P2P whole files or the managed section. A later
install reconstructs them without changing project identity, authority,
canonical revision, semantic digest or bundle content.

MCP exposes only `p2p_integration_status` plus the existing read-only adapter
list/show/doctor tools. MCP does not install, refresh, update or remove files in
its host configuration or project checkout.

## Agent Boundary

Generated instructions expose public CLI and registered MCP surfaces only.
They never provide credentials or instruct an agent to access YAML/Markdown
internals, database files, journals, WAL, SQL tables or generated exports as
canonical state. Git branch, commit, merge, push, pull-request and release
operations remain external implementation workflows.

The filesystem/SQLite comparison was owned by the earlier backend gate. Its
evidence remains in the ignored local feature packages
`evaluate-and-select-local-project-state-backend` and
`add-sqlite-project-state-backend`; this lifecycle does not rerun or redefine
that benchmark. The selected product line currently uses the filesystem
backend, while the SQLite experiment is deferred on its separate branch.
