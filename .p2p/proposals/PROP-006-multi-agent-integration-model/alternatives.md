# Alternatives - PROP-006

PROP-006 is no longer about inventing basic agent profiles from scratch. P2P
Engine already supports generated instructions for `generic`, `codex`, and
`claude`. The remaining product question is how far to evolve those profiles
into governed, inspectable, updateable integrations.

## Alternative A - Keep Lightweight Instruction Profiles

Keep the current model and add only small inspection commands.

Candidate commands:

```bash
p2p agent list
p2p agent show codex
p2p agent instructions refresh --profile cursor
```

Pros:

- Lowest implementation risk.
- Fits the current code.
- Avoids lifecycle machinery.

Cons:

- Does not record which files were generated.
- Cannot safely update or uninstall generated files.
- Does not distinguish a supported profile from an installed integration.
- Leaves manual drift invisible.

Assessment:
Useful as an incremental baseline, but too weak for a durable multi-agent
model.

## Alternative B - Agent Integration Registry

Introduce a first-class registry of installed agent integrations:

```text
.p2p/agent-integrations.yml
```

The registry records installed adapters, generated files, template versions,
hashes, shared files, drift status, and installation status. It does not choose
an active/default/preferred agent.

Candidate commands:

```bash
p2p agent list
p2p agent show <agent>
p2p agent install <agent|all>
p2p agent update <agent|all>
p2p agent doctor <agent|all>
p2p agent uninstall <agent>
```

Pros:

- Makes installed integrations visible.
- Enables drift detection.
- Enables safe update and safe uninstall.
- Supports multiple collaborators using different agents.
- Keeps P2P Engine as the source of truth for generated agent artifacts.

Cons:

- Adds schema and lifecycle complexity.
- Requires clear rules for shared files such as `AGENTS.md`.
- Requires hash and ownership semantics.

Assessment:
This is the strongest MVP foundation.

## Alternative C - Registry Plus Active Agent

Add an active/default/preferred agent to Alternative B.

Candidate commands:

```bash
p2p agent use codex
p2p agent current
p2p agent switch claude
```

Pros:

- Useful when a project wants one primary agent surface.
- Can improve setup hints for single-agent usage.

Cons:

- Adds state the owner does not need.
- Can imply that one agent is preferred project-wide.
- Does not match teams where different contributors use different agents.
- Requires extra commands such as `use`, `current`, and possibly `--no-use`.

Assessment:
Rejected for the MVP. P2P should support installed integrations, not select a
project-level favorite agent.

## Alternative D - Adapter-Specific Integration Model

Model each supported agent as an adapter with file targets and capabilities.

Initial adapters:

```text
generic
codex
claude
cursor
copilot
gemini
opencode
```

Indicative target files:

```text
generic   -> AGENTS.md
codex     -> AGENTS.md, .codex/skills/p2p-project/SKILL.md
claude    -> AGENTS.md, CLAUDE.md
cursor    -> AGENTS.md, .cursor/rules/p2p.mdc
copilot   -> AGENTS.md, .github/copilot-instructions.md
gemini    -> AGENTS.md, GEMINI.md
opencode  -> AGENTS.md, optionally opencode.json
```

Pros:

- Represents real differences between tools.
- Avoids assuming that every agent reads the same files.
- Allows capability-specific guidance such as MCP support, local command
  support, skill support, and permission model.

Cons:

- Tool conventions change over time.
- Requires documentation checks and adapter versioning.
- Some integrations may be advisory because the external tool does not provide
  strong enforcement.

Assessment:
This should be combined with Alternative B for a serious MVP.

## Alternative E - External Integration Packages

Allow external adapter packages from local paths, Git repositories, or URLs.

Candidate commands:

```bash
p2p agent install custom --from ./my-agent-adapter.yml
p2p agent update all
```

Pros:

- Highly extensible.
- Allows community-maintained adapters.

Cons:

- Larger security surface.
- Requires adapter validation and trust model.
- Premature for the current project.

Assessment:
Defer. Keep adapter definitions internal until the core lifecycle is stable.

## Recommended Direction

Adopt a hybrid of Alternatives B and D:

```text
Agent Integration Registry MVP
```

The MVP should promote existing agent profiles into governed integrations with:

- `.p2p/agent-integrations.yml`;
- no project-level active/default/preferred agent;
- baseline `generic` always present;
- install/list/show/update/doctor/uninstall commands;
- `p2p agent install all` when adapter file targets do not conflict;
- adapter-specific file targets;
- generated file hashes;
- safe update and safe uninstall rules;
- coexistence of multiple installed agents.

External adapter packages remain out of scope for the first implementation.
