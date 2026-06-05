# Suggested Scope - PROP-006

## Product Direction

Promote generated agent instructions into a governed **Agent Integration
Registry MVP**.

Project initialization should create the file structures for all supported
project-local agent integrations by default, unless the owner explicitly asks to
include only a subset.

`generic` is always present and cannot be removed. Specific agent integrations
can be added, updated, or removed later.

## Architectural Model

P2P has three separate layers:

```text
Generated agent instructions
  -> explain the P2P method, workflow, guardrails, and operating channel

CLI
  -> exposes textual P2P commands for humans, scripts, CI, and agents with shell

MCP
  -> exposes structured P2P tools for MCP-compatible agents
```

MCP does not teach agents the CLI. MCP gives compatible agents a structured way
to use P2P Engine capabilities without relying on textual command syntax.

CLI and MCP must both sit above the same P2P core behavior:

```text
P2P Core
   ^        ^
 CLI      MCP
```

## Baseline And Default Install Behavior

`generic` is the common baseline profile and is always generated.

Default project initialization installs all supported project-local adapters:

```bash
p2p init "Project Name"
```

Expected effect:

```yaml
baseline_profile: generic
integrations:
  generic:
    status: installed
  codex:
    status: installed
  claude:
    status: installed
  cursor:
    status: installed
  copilot:
    status: installed
  gemini:
    status: installed
  opencode:
    status: installed
```

The owner can choose a narrower install set:

```bash
p2p init "Project Name" --agent codex
p2p init "Project Name" --agent codex --agent claude
```

Even in a narrowed install, `generic` is still created.

Later lifecycle:

```bash
p2p agent install cursor
p2p agent install all
p2p agent update all
p2p agent uninstall cursor
```

There is no project-level preferred/default/active agent. P2P should not care
which collaborator uses which agent.

## Minimal Generic Content

The generic baseline is the source content from which all agent-specific files
are derived.

Minimum generic content:

```text
1. P2P Engine is the project governance source of truth.
2. Use P2P CLI or MCP tools for P2P writes.
3. Do not edit `.p2p/` internals directly.
4. If no CLI command or MCP write tool exists, stop and report the missing
   primitive.
5. The owner controls proposal decisions, choice decisions, managed merges,
   finalize, cleanup, and governance policy.
6. Before recommending proposal acceptance, inspect readiness and report gaps.
7. Prefer compact context before broad reads.
8. For managed P2P sync/branch/publish/merge flows, use P2P commands or
   explicit permission-gated MCP tools, not raw Git escape hatches.
9. If MCP is configured, use structured MCP tools for P2P operations.
10. If MCP is unavailable but shell access exists, use the `p2p` CLI.
11. If neither MCP nor CLI is available, ask the user to run the required P2P
    command.
```

Generated agent files may rephrase this content for their host tool, but they
must not weaken these rules.

## Method Behavior: Readiness-Driven Refinement

PROP-006 must not only decide which files are generated for each agent. It must
also define the common method behavior those files carry.

The distinction is:

```text
agent adapter/profile
  -> where instructions are written, which file format is used, whether CLI or
     MCP is available, and what host-tool conventions apply

agent policy / method behavior
  -> how every agent should behave when working with weak proposals, readiness
     gaps, owner questions, alternatives, and governance boundaries

readiness workflow
  -> concrete CLI/MCP-visible actions that transform a diagnostic score into
     refinement work
```

The "incalzante" behavior is a P2P method requirement, not a Codex-specific
personality trait. Every generated integration must preserve it.

When a proposal is weak, low-confidence, below target, or has failed readiness
gates, generated instructions must tell the agent not to stop at summarizing
gaps. For each failed gate or material gap, the agent should:

1. explain why the gate failed in proposal-specific terms;
2. propose one to three concrete alternatives;
3. recommend one option when evidence supports a recommendation;
4. identify the owner decision required;
5. draft the exact proposal, scope, risk, acceptance, or question update that
   would close the gap;
6. ask for confirmation only where owner authority is required;
7. re-check or request readiness re-check after the refinement is applied.

This should turn a diagnostic such as:

```yaml
failed_gates:
  - owner_questions_resolution
missing:
  - acceptance_criteria_quality
  - impact_overlap_analysis
```

into operational refinement actions such as:

```text
1. Resolve owner question
   - clarify the decision to make
   - offer alternatives
   - recommend one
   - ask for owner confirmation

2. Improve acceptance criteria
   - propose exact criteria
   - connect each criterion to expected behavior

3. Add impact and overlap analysis
   - compare with related policies, MCP tools, CLI flows, and existing files
   - identify what changes and what stays separate
```

The generated instruction files should therefore include a "readiness gap
handling" block in the generic baseline and adapt it to each tool. The same
behavior should also become visible through P2P Engine commands and MCP tools
over time, so the core makes this workflow hard to ignore.

## Included In MVP

### Registry

Add:

```text
.p2p/agent-integrations.yml
```

The registry records:

- schema version;
- baseline profile;
- available adapter definitions;
- installed integrations;
- generated files;
- template version;
- file hash;
- ownership status;
- shared-file flag;
- drift status;
- last installed or updated timestamp.

It must not record `active_agent`, `default_agent`, or `preferred_agent`.

MVP schema:

```yaml
schema_version: 1
baseline_profile: generic
generated_at: "2026-06-05T00:00:00Z"
adapters:
  generic:
    status: installed
    maturity: stable
    template_version: agent-template-v1
    files:
      - path: AGENTS.md
        shared: true
        owner: generic
        managed: true
        template_id: generic-agents-md-v1
        sha256: "..."
        drift: clean
  codex:
    status: installed
    maturity: stable
    template_version: agent-template-v1
    capabilities:
      mcp: supported
      shell: supported
      project_instructions: true
    files:
      - path: .agents/skills/p2p-project/SKILL.md
        shared: false
        owner: codex
        managed: true
        template_id: codex-p2p-skill-v1
        sha256: "..."
        drift: clean
```

Hashing is SHA-256 over exact file bytes. Do not normalize line endings,
whitespace, or Markdown formatting before hashing.

Templates live in package data for the MVP:

```text
src/p2p_engine/templates/agents/<adapter>/<file-template>
```

Project-local template overrides are deferred.

Generated Markdown files should include a short managed header where practical:

```markdown
<!--
Managed by P2P Engine.
Adapter: codex
Template: codex-p2p-skill-v1
Do not edit generated sections unless you accept drift.
-->
```

The registry is still the source of truth. The header is a human hint.

### CLI Commands

Add:

```bash
p2p agent list
p2p agent show <agent>
p2p agent install <agent|all>
p2p agent update <agent|all>
p2p agent doctor <agent|all>
p2p agent uninstall <agent>
```

Command semantics:

- `list`: show supported adapters and installed state.
- `show`: explain adapter capabilities, files, hashes, and drift.
- `install`: generate files, record registry manifest, and ensure `generic`
  baseline.
- `install all`: install all supported project-local adapters whose file targets
  do not conflict.
- `update`: refresh generated files only when safe.
- `doctor`: check registry health, missing files, hashes, drift, and baseline
  consistency.
- `uninstall`: remove only the target adapter's safe, managed, unchanged,
  non-shared files.

Excluded commands:

```text
p2p agent use
p2p agent switch
p2p agent current
p2p agent install --no-use
```

These are unnecessary because there is no active/default agent.

### Adapter File Matrix

#### generic

Files:

```text
AGENTS.md
.p2p/agent-policy.yml
```

Purpose:

- portable baseline for humans and generic agents;
- source content for generated agent-specific files;
- structured P2P agent policy.

Removal:

- cannot be uninstalled;
- not removed by uninstalling other adapters.

#### codex

Files:

```text
AGENTS.md                         shared baseline
.agents/skills/p2p-project/SKILL.md
```

Optional compatibility/migration:

```text
.codex/skills/p2p-project/SKILL.md
```

Notes:

- Codex officially reads `AGENTS.md`.
- Codex repo-scoped skills are discovered from `.agents/skills`.
- `.agents/skills` may also be visible to other tools such as OpenCode, so the
  skill content must be agent-neutral or the adapter must avoid installing it
  when it would be interpreted incorrectly.
- The existing P2P implementation currently generates `.codex/skills/...`;
  migration should preserve existing projects while moving new generation toward
  the official/common skill location if verified safe.

#### claude

Files:

```text
AGENTS.md     shared baseline
CLAUDE.md
```

Optional future:

```text
.claude/CLAUDE.md
.claude/skills/p2p-project/SKILL.md
```

Notes:

- Claude Code project memory supports `./CLAUDE.md` or `./.claude/CLAUDE.md`.
- MVP should generate root `CLAUDE.md` as the simplest shared project memory.
- Claude-specific skills/slash-command files are deferred unless the exact
  current format is needed.

#### cursor

Files:

```text
AGENTS.md
.cursor/rules/p2p.mdc
```

Notes:

- Cursor supports project rules in `.cursor/rules`.
- Cursor also supports `AGENTS.md` as a simpler Markdown alternative.
- `.cursorrules` is legacy and must not be generated.

#### copilot

Files:

```text
AGENTS.md
.github/copilot-instructions.md
```

Notes:

- GitHub Copilot uses `.github/copilot-instructions.md` for repository custom
  instructions.
- The Copilot file should contain the minimal generic P2P rules, not just a
  pointer, because Copilot may not follow arbitrary import/link semantics.

#### gemini

Files:

```text
AGENTS.md
GEMINI.md
```

Notes:

- Gemini CLI uses `GEMINI.md` context files.
- `GEMINI.md` should contain the minimal generic P2P rules adapted for Gemini.

#### opencode

Files:

```text
AGENTS.md
```

Optional future:

```text
opencode.json
.opencode/agents/p2p.md
.opencode/skills/p2p-project/SKILL.md
```

Notes:

- OpenCode supports `AGENTS.md`.
- `opencode.json` should not be generated in the MVP unless P2P needs to
  configure instruction paths or permissions.
- OpenCode may also load `.agents/skills`; therefore `.agents/skills` must not
  contain Codex-only behavior.

### Known File Sharing And Conflicts

Shared files:

```text
AGENTS.md
.p2p/agent-policy.yml
```

These are shared baseline files and are not conflicts.

No blocking adapter file conflicts are currently expected for the MVP matrix.

Potential conflict areas:

- `.agents/skills`: likely shared by more than one agent ecosystem. Do not put
  Codex-only content there.
- `opencode.json`: may already exist in a project for unrelated OpenCode
  settings. Do not generate by default in MVP.
- `.github/copilot-instructions.md`: may already exist in public repositories.
  Treat pre-existing unmanaged files as drift/unmanaged and avoid overwriting
  without explicit force.
- `.cursor/rules`: directory is shared with user-created Cursor rules. Generate
  only a dedicated `p2p.mdc` file.

### Safety Rules

- `AGENTS.md` is the shared baseline file.
- Uninstalling a specific agent must not remove `AGENTS.md` or
  `.p2p/agent-policy.yml`.
- `update` must detect manual drift by comparing stored hash and current hash.
- `update` may overwrite unchanged generated files.
- `update` must require `--force` or explicit user confirmation for drifted
  managed files.
- `uninstall` must remove only the target adapter's managed files whose current
  hash matches the registry and that are not shared baseline files.
- manually modified files should be marked `drifted`, not silently replaced.
- `install all` must fail or warn when two adapters would manage the same
  non-shared path.

### Doctor And Migration

`p2p agent doctor <agent|all>` checks:

- registry exists and validates;
- installed files exist;
- hashes match;
- shared files are still referenced;
- `generic` baseline exists;
- adapter documentation hints are available;
- no adapter claims ownership of a non-shared file owned by another adapter;
- no uninstall would remove a shared baseline file;
- generated instruction files include the generic method behavior block.

Existing projects migrate conservatively:

- if an existing file matches a known generated template hash, mark it
  `managed`;
- if an existing file exists but does not match, mark it `unmanaged` or
  `drifted`;
- do not overwrite unmanaged or drifted files during migration;
- preserve `.codex/skills/...` as compatibility if present;
- always ensure the `generic` baseline exists or report the missing baseline
  through `doctor`.

### MCP

Add MCP tools in the same implementation scope as the CLI lifecycle, backed by
the same core behavior.

Read-only tools:

```text
p2p_agent_list
p2p_agent_show
```

Write-safe tools:

```text
p2p_agent_install
p2p_agent_update
p2p_agent_uninstall
```

These tools are not governance decisions and do not require owner-decision
permissions, but they must preserve the same drift, shared-file, conflict, and
safe uninstall checks as the CLI.

### Readiness Refinement Surface

PROP-006 should integrate with the readiness model by ensuring generated agent
instructions point agents toward concrete refinement actions.

The implementation can start with instruction text only, but the product model
should leave room for CLI and MCP surfaces such as:

```bash
p2p proposal readiness next PROP-XXX
p2p proposal readiness refine PROP-XXX
p2p proposal readiness questions PROP-XXX
```

Equivalent MCP concepts could be exposed later as:

```text
p2p_proposal_readiness_next
p2p_proposal_readiness_refine
p2p_proposal_readiness_questions
```

These commands/tools are not required to solve the file-generation registry
MVP, but the generated policy must be written so agents naturally perform this
workflow even before dedicated commands exist.

## Excluded From MVP

- Project-level preferred/default/active agent state.
- `p2p agent use`, `switch`, `current`, and `install --no-use`.
- `.cursorrules` generation.
- Default `opencode.json` generation unless a concrete permission/instruction
  need is introduced.
- Destructive overwrite of pre-existing unmanaged agent files.
- External adapter packages from arbitrary URLs or Git repositories.
- Destructive uninstall of modified files.
- Automatic editing of user/global agent configuration outside the project
  without explicit consent.
- Direct AI provider invocation.
- Hosted web UI integration.
- Full support for every existing AI coding assistant.
- MCP client auto-registration in user home directories, unless handled by a
  separate consent-gated setup proposal.
- Full implementation of dedicated readiness refinement commands, unless it is
  split into or covered by a separate readiness-focused proposal.

## Future Work

- External adapter package format.
- Team-shared adapter catalog.
- Adapter compatibility checks against installed agent CLI versions.
- Per-agent MCP setup validation.
- Adapter-specific prompt libraries.
- Registry migration commands.
- OpenCode permission templates in `opencode.json`.
- Claude skill/slash-command adapter once the exact target format is stabilized.
- Dedicated readiness refinement commands and MCP tools that convert failed
  gates into ranked owner questions, alternatives, candidate edits, and next
  actions.
