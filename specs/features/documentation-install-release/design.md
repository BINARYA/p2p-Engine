# Design - Documentation Install Release

## Requirements Covered

- R001, R002, R003, R004

## Key Decisions

- D001: Keep README as the product entry point and detailed docs in `docs/`.
  Rationale: users need a short entry point and deeper references.

- D002: Keep agent setup docs explicit about CLI versus MCP.
  Rationale: MCP is intentionally bounded and should not be mistaken for full
  owner privilege.

## Components

- `README.md`
- `docs/INSTALL.md`
- `docs/MCP.md`
- `docs/AGENTS.md`
- `CONTRIBUTING.md`
- `pyproject.toml`
- `.github/workflows/release.yml`

## Evidence

- Package entrypoints: `pyproject.toml`
- Release workflow: `.github/workflows/release.yml`
- Docs present under `docs/`

## Status Note

This feature is primarily documentation/configuration. It is not implemented in
`src/` except for the package entrypoints that expose runtime commands.
