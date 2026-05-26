# CLI Foundation

## Provenance

- Proposal: PROP-001
- Source: .p2p/proposals/PROP-001-cli-foundation

## Problem

P2P Engine does not exist yet as an executable tool. The project has a solid foundation document, but no CLI, no generated `.p2p/` structure, no automated proposal workflow, and no prompt generation.

Without a first working CLI, every proposal must be created manually. That is acceptable for the bootstrap phase, but it must become automated quickly so the project can start using its own method.

## Proposal

Build the first P2P Engine CLI using Python and Typer.

The CLI should focus on local file generation and workflow guidance:

```text
p2p init
p2p proposal create
p2p contribution add
p2p digest prompt
p2p clarify prompt
p2p decision record
p2p plan prompt
p2p tasks prompt
p2p status
```

The first version should implement prompt generation instead of direct AI integration. A command such as:

```bash
p2p digest prompt PROP-001
```

should generate:

```text
.p2p/prompts/PROP-001/digest.prompt.md
```

The user can then provide that prompt to Codex, ChatGPT, Claude, Llama, or another model manually and paste the output into the correct artifact.

## Decision

# Decision — PROP-001 CLI Foundation

## Status

`accepted`

## Outcome

Build the first P2P Engine CLI as a local, Git-native, prompt-only Python application.

## Reason

The project needs a minimal executable workflow before adding AI adapters, exporters, MCP, or a web interface. Automating the manually bootstrapped `.p2p/` structure is the shortest path to dogfooding.

## Conditions

- Keep the MVP file-based.
- Do not add direct AI provider integration yet.
- Do not add a web app yet.
- Prefer explicit, inspectable artifacts over hidden state.
- Make generated files easy to edit manually.

## Date

2026-05-19

## Approver

bootstrap maintainer
