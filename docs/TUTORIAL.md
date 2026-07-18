# Tutorial: From Rough Idea to Accepted Proposal

This tutorial shows the smallest useful P2P Engine loop. The goal is not to
learn every command; it is to see why P2P Engine exists.

1. initialize a project;
2. capture rough intent;
3. create a proposal;
4. record an owner decision;
5. create a Change Set;
6. refresh registries and generate agent context.

The example assumes P2P Engine is installed in the project-local `.venv`. If
`p2p` is not on `PATH`, use `.venv/bin/p2p`.

## Scenario

You have a software project with a vague direction:

```text
We need to decide whether the first interface should be CLI-only, MCP-first, or
a web app. Agents will help, but owner decisions must stay explicit.
```

P2P Engine turns that rough intent into versioned project state under `.p2p/`.

## What You Will See

Before P2P Engine, the project has an ambiguous note:

```text
Maybe start with CLI. Or MCP. Or a web app. Agents should help somehow.
```

After this tutorial, the project has a traceable chain:

```text
rough idea
  -> structured proposal
  -> explicit owner decision
  -> operational Change Set
  -> generated registries
  -> compact agent context
```

That chain is the core value: decisions become inspectable project memory instead
of disappearing into chats, issues, or ad hoc notes.

## 1. Create A Demo Project

```bash
mkdir /tmp/p2p-demo
cd /tmp/p2p-demo
p2p init "P2P Demo" --agent codex --repository local --domain software --mcp-hint
```

Expected shape:

```text
P2P workspace initialized.
  created .p2p/project.yml
  created .p2p/project/rubrics.yml
  created AGENTS.md
  created .p2p/agent-policy.yml
```

Initial project files:

```text
.
  AGENTS.md
  .p2p/
    agent-policy.yml
    project.yml
    project/
      rubrics.yml
```

## 2. Ask For Compact Context

```bash
p2p context --budget small
```

This is the default first step for agents. It summarizes project state and tells
the agent what not to scan.

Expected shape:

```text
P2P compact context
  budget: small
Current state:
  validation:
    ok: True
Allowed commands:
  - p2p context --budget small
  - p2p validate
  ...
Do not read:
  - Do not scan all .p2p/ directories.
```

## 3. Capture The Rough Idea

Use intake when the input is not yet a clean proposal.

```bash
p2p intake prompt "Decide whether the first interface should be CLI-only, MCP-first, or a web app. Agents may help, but owner decisions must stay explicit."
p2p intake status
```

The intake prompt is advisory. It can help a human or AI identify related
proposals, possible duplicates, choices, risks, or next actions. It does not
decide anything by itself.

## 4. Create The First Proposal

Create a proposal for the narrow first direction:

```bash
p2p proposal create "Start With CLI And Local MCP" \
  --problem "The project needs a first usable interface without overbuilding a hosted product." \
  --context "The project needs Git-native governance state, bounded agent context, and explicit owner decisions." \
  --goal "Make the engine usable from source through CLI commands." \
  --goal "Expose safe local MCP tools for agents." \
  --non-goal "Build a hosted web product in the first implementation layer." \
  --proposal "Start with a deterministic local CLI and a local stdio MCP server. Keep hosted mediator or web layers out of the engine repository." \
  --acceptance "A user can initialize a project, create a proposal, decide it, and inspect compact context." \
  --acceptance "Agents can read compact context through MCP without bypassing owner decisions."
```

Inspect it:

```bash
p2p proposal list
p2p proposal show PROP-001
```

Expected shape:

```text
PROP-001 - Start With CLI And Local MCP
  status: draft

Problem:
  ...
```

## 5. Record The Owner Decision

When the owner decides, preview the outcome without writing:

```bash
p2p decision preview PROP-001 \
  --event-type accepted \
  --reason "This keeps the first implementation local, inspectable, and agent-safe." \
  --format json
```

Review the response, then apply the exact returned date, operation key, source
head when present, and preview token:

```bash
p2p decision apply PROP-001 \
  --event-type accepted \
  --reason "This keeps the first implementation local, inspectable, and agent-safe." \
  --decided-on '<preview-decided-on>' \
  --operation-key '<preview-operation-key>' \
  --preview-token '<preview-token>' \
  --confirm
```

The proposal now has an append-only decision trail. Inspect it with
`p2p decision status PROP-001` and `p2p decision history PROP-001`.

Expected shape:

```text
Decision:
  status: accepted
  reason: This keeps the first implementation local, inspectable, and agent-safe.
```

## 6. Create A Change Set

Accepted intent can become operational work metadata:

```bash
p2p change create --from PROP-001
p2p change status
p2p change show CHANGE-001
```

Expected shape:

```text
Change Sets
  CHANGE-001  proposed  Start With CLI And Local MCP
```

Move it when planning starts:

```bash
p2p change set-status CHANGE-001 planned
p2p change tasks CHANGE-001
```

## 7. Refresh Project State

```bash
p2p registry refresh
p2p validate
p2p assess refresh
p2p assess show
p2p assess maturity refresh
p2p assess maturity show
```

These commands keep generated indexes and deterministic assessments aligned with
the project state.

## 8. Generate Agent Context Again

```bash
p2p context --budget small
```

Now the context packet can point agents toward accepted intent, Change Sets, and
bounded next actions.

## Result

The project now has visible governance state:

```text
.p2p/
  proposals/
    PROP-001-start-with-cli-and-local-mcp/
  changes/
    CHANGE-001-start-with-cli-and-local-mcp/
  intake/
  registries/
  project/
    assessment.yml
    maturity.yml
    rubrics.yml
```

The important result is not just files on disk. The project now has a traceable
chain:

```text
rough idea -> proposal -> owner decision -> Change Set -> registries -> agent context
```

That chain is what P2P Engine preserves in Git. A new agent can start from
`p2p context --budget small`, see the accepted direction and Change Set, and
avoid rediscovering the same decision from scratch.
