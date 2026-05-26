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

