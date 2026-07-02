# Implementation Note

## Design Choice

The production hardening stays behind `ProjectVerticalService` with
`P2PWorkspace` as a delegation facade. CLI and MCP changes are additive and keep
the existing human-readable defaults.

## Compatibility Impact

Single-file `vertical.yml` packs remain valid. Canonical multi-file packs are
loaded in the same normalized runtime model. Existing projects without active
vertical state keep read-time `base_project` fallback without materializing
`vertical.yml`, `vertical.lock.yml`, or `definition.yml`.

Explicit vertical selection now writes:

- `.p2p/project/vertical.yml`
- `.p2p/project/vertical.lock.yml`
- `.p2p/project/definition.yml`
- `.p2p/project/rubrics.yml`

Existing active vertical state without lock is diagnosed by validation and can
be repaired with `p2p project vertical lock repair --actor <actor>`.

## Behavior Changes

- Multi-file vertical packs support `manifest.yml`, `vertical.yml`, split
  `sections/`, `rubrics.yml`, and optional profile/module/artifact/example
  content.
- Resolver precedence now includes project-local, `P2P_HOME/verticals`,
  `~/.p2p/verticals`, internal resources, and fallback.
- Lock status fails closed on missing source or checksum mismatch after a lock
  exists.
- Project definition state supports deterministic initialization and structured
  patch updates.
- CLI and MCP expose JSON-ready context, sections, lock, rubrics, and
  definition-state surfaces.
- Pack safety validation treats vertical content as declarative data and blocks
  instruction override, code execution, permission, and path-escape attempts.

## Files Changed

- `src/p2p_engine/core/project_verticals.py`
- `src/p2p_engine/services/project_verticals.py`
- `src/p2p_engine/services/project_maturity.py`
- `src/p2p_engine/services/visible_project_export.py`
- `src/p2p_engine/services/agent_templates.py`
- `src/p2p_engine/storage/filesystem.py`
- `src/p2p_engine/cli.py`
- `src/p2p_engine/cli_commands/project_ops.py`
- `src/p2p_engine/mcp/catalog/project.py`
- `src/p2p_engine/mcp/handlers/project.py`
- `src/p2p_engine/mcp/registry.py`
- `tests/test_project_verticals.py`
- `tests/test_project_initialization_service.py`
- `tests/test_project_maturity_service.py`
- `tests/test_mcp.py`
- `tests/test_agent_instructions_service.py`
- `docs/CLI-GUIDE.md`
- `docs/MCP.md`
- `docs/CONCEPTS.md`
- `docs/GLOSSARY.md`

## Validation Evidence

- `.venv/bin/pytest tests/test_project_verticals.py tests/test_project_initialization_service.py tests/test_project_maturity_service.py tests/test_mcp.py tests/test_agent_instructions_service.py -q`
- `.venv/bin/pytest tests/test_cli.py -q`
- `.venv/bin/pytest tests/test_validation_service.py tests/test_mcp_project_handler.py -q`
- `.venv/bin/p2p validate`
- `.venv/bin/python -m pytest -q`

## Residual Risk

Remote/Wavekit search/install/publish, executable plugins, and a full
`project next-action --json` engine remain intentionally deferred. Canonical
seed-pack conversion is supported by the loader but internal packaged seeds
remain single-file compatibility packs in this implementation slice.
