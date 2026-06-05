# Findings - PROP-006

## F001 - Basic Agent Profiles Already Exist

P2P Engine already implements `generic`, `codex`, `claude`, and `all` profiles.
The current implementation can generate `AGENTS.md`, `CLAUDE.md`,
`.codex/skills/p2p-project/SKILL.md`, and `.p2p/agent-policy.yml`.

Impact:
PROP-006 should not be framed as introducing profiles from zero. It should
focus on lifecycle management for installed integrations.

## F002 - Project Init Should Install All Supported Project-Local Adapters

The owner does not want P2P to choose one default agent. A project can safely
support several agent tools at once as long as their generated files do not
overwrite each other.

Impact:
Default init should install all supported project-local adapters. Narrower
installation remains available when the owner wants fewer generated files.

## F003 - The Missing Layer Is Installation State

The current model can generate instructions but does not record which files were
generated, which template version produced them, whether they changed, or
whether they can be updated or removed safely.

Impact:
The main missing artifact is `.p2p/agent-integrations.yml`.

## F004 - Agent Files Are Not Interchangeable

Different tools consume different project-local instruction files:

- Codex reads `AGENTS.md` and supports repo-scoped skills.
- Claude Code project memory supports `CLAUDE.md`.
- Cursor uses project rules in `.cursor/rules` and also supports `AGENTS.md`.
- GitHub Copilot uses `.github/copilot-instructions.md`.
- Gemini CLI uses `GEMINI.md`.
- OpenCode supports `AGENTS.md` and can use `opencode.json` for additional
  instruction paths or permissions.

Impact:
P2P needs adapter definitions rather than a single generic output file.

## F005 - AGENTS.md Is The Shared Baseline

`AGENTS.md` should remain the cross-agent baseline because it is readable by
humans, generic agents, and several modern agent tools. Tool-specific files
should supplement it only where they provide better integration.

Impact:
`AGENTS.md` is a shared managed file and needs special uninstall/update rules.

## F006 - Safe Update Requires Hashes

Without stored hashes P2P cannot distinguish:

- generated file unchanged;
- generated file manually edited;
- generated file stale because template changed;
- unmanaged file with the same path.

Impact:
Every managed generated file needs a stored hash and ownership metadata.

## F007 - No Active Agent Is Needed

The project owner does not need P2P to choose whether a contributor uses Codex,
Claude, Cursor, Copilot, Gemini, or OpenCode. Integrations should be installed
because somebody needs them, and multiple integrations should coexist.

Impact:
Do not introduce `active_agent`, `default_agent`, `preferred_agent`,
`p2p agent use`, `p2p agent current`, or `install --no-use` in the MVP.

## F008 - Existing Implementation Should Be Migrated, Not Replaced

The current `p2p agent instructions refresh` behavior should remain compatible.
New install/update commands can call the same rendering logic while recording
registry metadata.

Impact:
PROP-006 can be implemented incrementally without breaking existing projects.

## F009 - MCP And CLI Are Peer Interfaces Over P2P Core

MCP does not teach agents how to use the CLI. MCP exposes P2P Engine
capabilities as structured tools for MCP-compatible agents. Generated
instructions still explain when to use CLI, when to use MCP, what order to
follow, and which governance boundaries apply.

Impact:
PROP-006 should instruct agent profiles to describe operating-channel
preference:

- if MCP is configured, prefer MCP tools for structured P2P operations;
- otherwise use CLI when shell access exists;
- otherwise ask the user to run the required P2P command.

CLI and MCP behavior must share the same underlying core semantics.

## F010 - `.agents/skills` Is Potentially Shared

Codex supports repo-scoped skills from `.agents/skills`. OpenCode documentation
also describes loading skills from `.agents/skills`.

Impact:
Any file generated under `.agents/skills` must be agent-neutral. Do not put
Codex-only behavior in a shared skill path. If Codex-specific behavior is still
needed, preserve existing `.codex/skills` behavior as a compatibility/migration
matter rather than using it as the general shared adapter path.
## F011 - Agent Incisiveness Is A Method Behavior Problem

The observed weakness is not mainly that one agent lacks a better technical
profile. It is that P2P's method instructions do not yet force agents to turn
readiness gaps into concrete refinement work.

An agent profile answers "where do instructions go and which tools can this
agent use?" The method policy answers "what should the agent do when the
proposal is weak?" The second question belongs in the generic baseline and must
be inherited by all generated agent files.

## F012 - Readiness Must Become Operational For Agents

Readiness currently gives a score, label, failed gates, missing items, and
suggested next actions. Agents can still stop at diagnosis unless instructions
and future commands guide them through a refinement loop.

The desired loop is:

```text
readiness gap
  -> required refinement action
  -> candidate alternatives
  -> recommendation
  -> owner decision
  -> proposal update
  -> readiness re-check
```

## F013 - Generated Instructions Must Include Gap Handling

Every generated agent file should preserve a common rule:

```text
Do not stop at identifying gaps. For each failed readiness gate, explain the
failure, propose alternatives, recommend one when justified, identify the owner
decision, draft the concrete update, and re-check readiness after refinement.
```

This is a generic P2P behavior and should not live only in the Codex adapter.

## F014 - Remaining Questions Can Be Closed With Conservative MVP Defaults

The remaining questions do not require more product discovery. They can be
settled with conservative implementation defaults:

- versioned `.p2p/agent-integrations.yml`;
- built-in package templates;
- SHA-256 over exact bytes;
- managed Markdown header as a human hint;
- conservative migration that never overwrites unknown or drifted files;
- future readiness refinement commands under `p2p proposal readiness`.

Impact:
PROP-006 can move toward decision once these defaults are recorded, even if
small internal names change during implementation.
