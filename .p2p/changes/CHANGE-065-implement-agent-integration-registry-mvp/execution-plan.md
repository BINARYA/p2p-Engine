# Execution Plan - PROP-006

## Phase 1 - Adapter Matrix And Registry Model

Define the built-in adapter matrix:

```text
generic   -> AGENTS.md, .p2p/agent-policy.yml
codex     -> AGENTS.md, .agents/skills/p2p-project/SKILL.md, optional legacy .codex/skills/p2p-project/SKILL.md
claude    -> AGENTS.md, CLAUDE.md
cursor    -> AGENTS.md, .cursor/rules/p2p.mdc
copilot   -> AGENTS.md, .github/copilot-instructions.md
gemini    -> AGENTS.md, GEMINI.md
opencode  -> AGENTS.md
```

Define `.p2p/agent-integrations.yml` with:

- schema version;
- `baseline_profile: generic`;
- installed integrations;
- adapter id and template version;
- generated file manifest;
- SHA-256 hashes;
- shared-file markers;
- drift status.

The registry must not contain `active_agent`, `default_agent`, or
`preferred_agent`.

Add validation for malformed registry records.

Use this MVP schema shape:

```yaml
schema_version: 1
baseline_profile: generic
generated_at: "2026-06-05T00:00:00Z"
adapters:
  generic:
    status: installed
    maturity: stable
    template_version: agent-template-v1
    files: []
```

Each file record includes `path`, `shared`, `owner`, `managed`, `template_id`,
`sha256`, and `drift`.

Use SHA-256 over exact file bytes.

Store built-in templates as package data:

```text
src/p2p_engine/templates/agents/<adapter>/<file-template>
```

Project-local template overrides are deferred.

## Phase 2 - Generic Method Policy

Define the minimum generic method content used by all generated agent files.

The generic policy must include:

- P2P source-of-truth and write-boundary rules;
- owner-controlled governance decisions;
- CLI/MCP operating-channel rules;
- compact context before broad reads;
- readiness inspection before recommending acceptance;
- readiness gap handling.

Readiness gap handling must instruct agents to:

1. explain each failed gate in proposal-specific terms;
2. propose concrete alternatives;
3. recommend one option when justified;
4. identify the owner decision needed;
5. draft exact candidate edits to close the gap;
6. ask only for authority-bound decisions;
7. re-check or request readiness re-check after refinement.

Ensure every adapter template preserves this block, even if phrased in the
host tool's preferred format.

## Phase 3 - Default Init Behavior

Change project init so the default behavior installs all supported
project-local adapters.

Narrow install remains available:

```bash
p2p init "Project Name" --agent codex
p2p init "Project Name" --agent codex --agent claude
```

Even narrowed install must always include `generic`.

## Phase 4 - Read-Only Inspection

Implement:

```bash
p2p agent list
p2p agent show <agent>
p2p agent doctor <agent|all>
```

These commands must report supported adapters, installed state, file ownership,
hash status, drift, missing files, baseline profile, and file conflicts.

`doctor` must also verify that generated instruction files preserve the generic
method behavior block.

Expose equivalent MCP read tools:

```text
p2p_agent_list
p2p_agent_show
```

## Phase 5 - Install

Implement:

```bash
p2p agent install <agent>
p2p agent install all
```

Installation should ensure the `generic` baseline exists, install the requested
adapter or adapters, and record registry metadata.

`install all` must not let adapters overwrite each other's non-shared files.

Expose equivalent write-safe MCP tool backed by the same core behavior:

```text
p2p_agent_install
```

## Phase 6 - Safe Update

Implement:

```bash
p2p agent update <agent>
p2p agent update all
```

Update may overwrite unchanged generated files. Drifted files must be reported
and preserved unless an explicit force/confirmation mechanism is implemented.

Expose equivalent MCP tool:

```text
p2p_agent_update
```

## Phase 7 - Safe Uninstall

Implement:

```bash
p2p agent uninstall <agent>
```

Uninstall may remove only the target adapter's managed non-shared files whose
current hash matches the registry. It must preserve `AGENTS.md`,
`.p2p/agent-policy.yml`, drifted files, unmanaged files, and files still shared
by other installed integrations.

`generic` cannot be uninstalled.

Expose equivalent MCP tool:

```text
p2p_agent_uninstall
```

## Phase 8 - Documentation

Update installation, MCP, and agent integration documentation.

Documentation must explain:

- default init installs all built-in project-local adapters;
- generated instructions define method and guardrails;
- CLI is the universal textual interface;
- MCP is the structured agent-native interface;
- CLI and MCP expose the same P2P capabilities through the same core behavior;
- P2P does not choose a project-level preferred agent;
- generated instructions must turn readiness gaps into alternatives,
  recommendations, owner questions, candidate edits, and readiness re-checks.

## Phase 9 - Readiness Refinement Follow-Up Hook

Do not block the Agent Integration Registry MVP on dedicated readiness
refinement commands. However, shape the generated policy so a later command or
MCP layer can expose the same workflow.

Candidate future command/tool surfaces:

```text
p2p proposal readiness next PROP-XXX
p2p proposal readiness refine PROP-XXX
p2p proposal readiness questions PROP-XXX
p2p_proposal_readiness_next
p2p_proposal_readiness_refine
p2p_proposal_readiness_questions
```

## Verification

- Unit tests for registry validation and hash drift.
- CLI tests for init default all, narrowed init, install/list/show/update/uninstall.
- MCP tests for equivalent read and write-safe tools.
- Snapshot-style tests for generated adapter files.
- Snapshot tests proving every generated adapter file preserves the generic
  readiness gap handling block.
- Regression tests for existing `p2p agent instructions refresh`.
- Validation coverage for malformed `.p2p/agent-integrations.yml`.
- Tests for `install all` conflict handling.
