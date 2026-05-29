# P2P CLI Guide

This guide covers the practical command-line workflows for P2P Engine. It is not
an exhaustive generated reference; use `p2p --help` and `p2p <group> --help` for
the complete command list in your installed version.

## Principles

- Use CLI commands for P2P mutations.
- Do not edit `.p2p/` internals by hand unless repairing with explicit owner intent.
- Use `p2p context --budget small` before broad inspection.
- Owner-controlled governance actions require explicit owner instruction.
- Run `p2p validate` and `p2p registry refresh` after meaningful P2P changes.

## 1. Start A New Project

Interactive setup:

```bash
p2p init
```

Scriptable setup:

```bash
p2p init "My Project" \
  --agent codex \
  --repository local \
  --domain software \
  --mcp-hint
```

Typical first checks:

```bash
p2p status
p2p context --budget small
p2p validate
p2p registry refresh
p2p next
```

Expected shape:

```text
P2P compact context
  budget: small
Current state:
  validation:
    ok: True
Next actions:
  ...
```

## 2. Capture A Rough Idea

Use intake when the input is messy, overlapping, or not ready to become a
proposal.

```bash
p2p intake prompt "We may need a local MCP server, but it must not bypass owner decisions."
p2p intake status
```

The prompt workflow creates an intake folder and a prompt for human or AI
analysis. Import and apply steps are controlled:

```bash
p2p intake import INTAKE-001 intake-output/
p2p intake apply plan INTAKE-001
p2p intake apply show INTAKE-001
```

Only run an apply action after reviewing what it will do:

```bash
p2p intake apply run INTAKE-001 --action APPLY-001
```

## 3. Create And Refine A Proposal

Create a structured proposal:

```bash
p2p proposal create "Local MCP Server" \
  --problem "Agents need bounded access to P2P project state." \
  --context "The CLI is the source of truth, but MCP clients need tool calls." \
  --goal "Expose read-only project context through a local stdio server." \
  --non-goal "Let agents accept proposals or decide choices." \
  --proposal "Add a local MCP server with read-only status, context, registry, and proposal tools." \
  --acceptance "An MCP client can call p2p_context before reading project files." \
  --acceptance "No MCP tool makes owner governance decisions."
```

Inspect and update:

```bash
p2p proposal list
p2p proposal show PROP-001
p2p proposal update PROP-001 --goal "Keep tool boundaries explicit."
```

Add review material without rewriting the proposal:

```bash
p2p contribution add PROP-001 \
  "The MCP surface should label read-only and write-safe tools clearly." \
  --type constraint \
  --relevance high
```

## 4. Decide A Proposal

Proposal decisions are owner-controlled. Use these only when the owner has made
the corresponding decision.

```bash
p2p proposal accept PROP-001 --reason "The read-only MCP boundary is clear."
p2p proposal reject PROP-001 --reason "The scope conflicts with current priorities."
p2p proposal defer PROP-001 --reason "Needs more design evidence."
```

After a decision:

```bash
p2p registry refresh
p2p validate
```

## 5. Compare Alternatives With Choices

Use choices when the project needs an explicit selection between alternatives.

```bash
p2p choice create \
  --title "MCP write boundary" \
  --option "Read-only tools only" \
  --option "Write-safe draft tools" \
  --option "Full governance tools"
```

Inspect and decide:

```bash
p2p choice list
p2p choice show CHOICE-001
p2p choice decide CHOICE-001 \
  --option "Write-safe draft tools" \
  --reason "Draft mutations are useful, while owner decisions remain outside MCP."
```

Advisory discovery does not modify project state:

```bash
p2p choice discover
```

## 6. Create A Change Set

Create Change Sets from accepted intent:

```bash
p2p change create --from PROP-001
p2p change status
p2p change show CHANGE-001
```

Move lifecycle state when work planning changes:

```bash
p2p change set-status CHANGE-001 planned
p2p change tasks CHANGE-001
```

Change Sets are metadata first. They describe operational work derived from
accepted project intent; they do not replace Git commits or code review.

## 7. Generate And Export Specs

For software projects, a Change Set can produce a P2P-native spec and optional
downstream export bundle.

```bash
p2p spec refresh --change CHANGE-001
p2p spec status
p2p spec show CHANGE-001
p2p spec prompt --change CHANGE-001
```

After reviewing refined spec output:

```bash
p2p spec import CHANGE-001 spec-output/
p2p spec export --change CHANGE-001 --target speckit
p2p spec export-status
p2p spec export-validate CHANGE-001 --target speckit
```

## 8. Manage Work Metadata

Work commands manage handoff and branch lifecycle metadata for P2P-managed work.

```bash
p2p work plan --change CHANGE-001 --target speckit
p2p work status
p2p work show WORK-001
```

Branch and review commands can touch Git state. Use them only when the local
repository policy is clear:

```bash
p2p work branch WORK-001
p2p work submit WORK-001
p2p work review WORK-001
p2p work publish WORK-001
p2p work request-review WORK-001
p2p work accept WORK-001
p2p work finalize WORK-001
p2p work cleanup WORK-001
```

## 9. Assess And Validate

Structural validation:

```bash
p2p validate
```

Readiness assessment:

```bash
p2p assess refresh
p2p assess show
```

Project definition maturity:

```bash
p2p project rubrics show
p2p assess maturity refresh
p2p assess maturity show
```

Maturity assessment checks project definition coverage against rubrics. It is
not a measure of implementation completeness.

## 10. Recover From Common Problems

`p2p: command not found`

Use the virtualenv binary or activate the virtualenv:

```bash
/path/to/p2p-Engine/.venv/bin/p2p --help
. /path/to/p2p-Engine/.venv/bin/activate
```

Registries look stale:

```bash
p2p registry refresh
p2p validate
```

An agent wants to edit `.p2p/` manually:

```text
Use CLI or MCP primitives. If a primitive is missing, stop and report it.
Do not invent .p2p files or IDs.
```

You need the exact command surface:

```bash
p2p --help
p2p proposal --help
p2p choice --help
p2p change --help
p2p spec --help
p2p work --help
```
