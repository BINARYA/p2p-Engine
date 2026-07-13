# Implementation Note - PROP-099 Human Project Publication Pipeline

## Delivered

- Added `ProjectPublicationService` for publication paths, manifest handling,
  source fingerprinting, prepare/import/validate/render/review orchestration,
  stage status, and cascading staleness.
- Added deterministic publication validation with `error`, `warning`, and
  `advisory` findings.
- Added optional WeasyPrint-backed `neutral-v1` PDF renderer behind the
  `p2p-engine[pdf]` extra; no handcrafted PDF fallback.
- Added render/path-safety regression coverage for stale validation refusal,
  optional PDF capability errors, fixed publication output paths, unsafe import
  sources, and real WeasyPrint smoke rendering when the optional dependency is
  available.
- Added release-template curator instructions in
  `src/p2p_engine/services/agent_templates.py`, with generated Codex outputs
  under `.agents/skills/p2p-project-curator/SKILL.md` and
  `.codex/skills/p2p-project-curator/SKILL.md` when the Codex adapter is
  installed. Claude receives equivalent generated guidance in `CLAUDE.md`.
- Added project-level CLI commands:
  - `p2p project publish prepare`
  - `p2p project publish import <file>`
  - `p2p project publish validate`
  - `p2p project publish render`
  - `p2p project publish review`
  - `p2p project publish status`
- Added MCP tools:
  - `p2p_project_publish_prepare`
  - `p2p_project_publish_import`
  - `p2p_project_publish_validate`
  - `p2p_project_publish_render`
  - `p2p_project_publish_status`

MCP intentionally does not expose owner review or model curation in the first
slice.

## Validation

- `.venv/bin/pytest tests/test_project_publication_service.py`
- `.venv/bin/pytest tests/test_cli.py -k "project_publish"`
- `.venv/bin/pytest tests/test_mcp.py -k "project_publish"`
- `./scripts/test-public.sh`
- `./scripts/test-full.sh`
- `.venv/bin/p2p validate`

Final evidence:

- public suite: 236 passed
- full suite: 654 passed
- P2P validation: 0 errors, 0 warnings

## Renderer Dependency

PDF rendering imports WeasyPrint lazily. In environments without
`p2p-engine[pdf]` and native WeasyPrint dependencies, `render` fails clearly and
does not write a partial PDF. Tests use a fake renderer for deterministic
pipeline orchestration and approval behavior, plus an import-skipped real
WeasyPrint smoke test when the optional dependency is available.

## Follow-Ups

- Add broader CLI-level owner review loop coverage if the command surface grows.
- Consider a publication package manifest export for downstream tools after the
  first workflow is used on real projects.
