# P2P CLI Guide

This guide is the command-line reference for P2P Engine.

Status: scaffold. The README links here as the future detailed CLI guide.

## Principles

- Use CLI commands for P2P mutations.
- Do not edit `.p2p/` internals by hand unless repairing with explicit owner intent.
- Use `p2p context --budget small` before broad inspection.
- Owner-controlled governance actions require explicit owner instruction.

## First Commands

```bash
p2p init
p2p context --budget small
p2p validate
p2p registry refresh
p2p next
```

## Project Initialization

```bash
p2p init
p2p init "Project Name" --agent codex --repository local --domain software
```

The interactive wizard asks for project name, agent profile, repository mode, project domain, rubric criteria, and MCP setup hint.

## Proposals

```bash
p2p proposal create "Title" --problem "..." --goal "..." --proposal "..." --acceptance "..."
p2p proposal list
p2p proposal show PROP-001
p2p proposal update PROP-001 --goal "..."
p2p proposal accept PROP-001 --reason "..."
p2p proposal reject PROP-001 --reason "..."
p2p proposal defer PROP-001 --reason "..."
```

## Choices

```bash
p2p choice create --title "Decision" --option "A" --option "B"
p2p choice list
p2p choice show CHOICE-001
p2p choice decide CHOICE-001 --option A --reason "..."
```

## Change Sets

```bash
p2p change create --from PROP-001
p2p change status
p2p change show CHANGE-001
p2p change set-status CHANGE-001 planned
p2p change tasks CHANGE-001
```

## Work

```bash
p2p work status
p2p work show WORK-001
p2p work submit WORK-001
p2p work review WORK-001
p2p work publish WORK-001
p2p work accept WORK-001
p2p work finalize WORK-001
p2p work cleanup WORK-001
```

## Assessment

```bash
p2p assess refresh
p2p assess show
p2p project rubrics show
p2p assess maturity refresh
p2p assess maturity show
```

## Specs And Export

```bash
p2p spec refresh --change CHANGE-001
p2p spec prompt --change CHANGE-001
p2p spec import CHANGE-001 spec-output/
p2p spec export --change CHANGE-001 --target speckit
p2p spec export-validate CHANGE-001 --target speckit
```

## To Be Expanded

- command-by-command examples;
- expected output samples;
- common errors and recovery;
- full workflow walkthroughs.

