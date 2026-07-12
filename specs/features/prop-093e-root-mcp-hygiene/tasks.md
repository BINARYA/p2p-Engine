# PROP-093E Root, MCP, And Hygiene Tasks

## Status

`implemented`

## Implementation Rules

- Keep root/MCP and hygiene changes independently releasable.
- Do not introduce sibling-repository support.
- Do not overwrite or reorder existing `.gitignore` content.
- Never add `.p2p/` to `.gitignore`.
- Preserve existing MCP configurations and short executable documentation.

## Tasks

- [x] E1. Review current CLI init, MCP docs, install docs, and MCP tests for
      assumptions about `p2p-mcp-server` as the primary hint.

- [x] E2. Add service/helper tests for deriving MCP server name from project
      identity with directory-name fallback.

- [x] E2a. Add server-name slug tests for punctuation, spaces, uppercase,
      missing identity, and an existing `p2p-` prefix.

- [x] E3. Add service/helper tests for preferred Codex MCP command using
      `.venv/bin/python -m p2p_engine.mcp.server --root <project-root>`.

- [x] E3a. Add tests for missing `.venv/bin/python`: init must not fail and
      the hint must clearly mark the path as conventional/expected or include
      the fallback command.

- [x] E3b. Add MCP hint rendering tests for project roots with spaces and
      shell-special characters.

- [x] E4. Add service/helper tests for retaining the short
      `p2p-mcp-server --root <project-root>` fallback command.

- [x] E5. Implement a small MCP hint helper that returns structured preferred
      and fallback command data.

- [x] E5a. Split generic MCP server command data from client-specific
      registration command data in the helper view model.

- [x] E6. Add CLI init tests for grouped MCP setup output and decision-root
      wording.

- [x] E7. Update CLI init summary rendering to use the MCP hint helper and
      explain `--root` as the governed P2P decision root.

- [x] E8. Add generated instruction tests proving agents are told to use
      explicit `--root` when cwd is ambiguous.

- [x] E9. Update generated agent instructions with governed-root discovery and
      root-aware command guidance.

- [x] E10. Add docs tests or targeted text checks proving docs do not describe
       `--root` as sibling-repository support.

- [x] E10a. Add generated-instruction text checks proving root guidance avoids
       sibling-repository examples and does not promote arbitrary filesystem
       traversal as the primary root-discovery model.

- [x] E11. Update `docs/MCP.md`, `docs/INSTALL.md`, and
       `docs/AGENT-INTEGRATION.md` to prefer project-local Python while keeping
       the PATH-based alternative.

- [x] E12. Add focused tests for `.gitignore` hygiene when no `.gitignore`
       exists.

- [x] E13. Add focused tests for appending missing patterns without overwriting
       existing `.gitignore` content.

- [x] E13a. Add focused tests proving existing `.gitignore` content before the
       P2P-managed section is preserved byte-for-byte where practical.

- [x] E14. Add focused tests proving hygiene is idempotent and does not
       duplicate patterns.

- [x] E14a. Add focused tests for exact equivalent patterns such as `.venv`
       versus `.venv/`.

- [x] E15. Add focused tests proving `.p2p/` is never added and an existing
       `.p2p/` ignore produces warning-only behavior.

- [x] E15a. Add focused tests for explicit `.p2p/`, `.p2p`, and broad dotfile
       ignore patterns where the helper can detect them conservatively.

- [x] E16. Implement a small `.gitignore` hygiene helper/service with
       structured result fields for status, added patterns, warnings, and path.

- [x] E17. Decide and implement hygiene activation policy: automatic default,
       guided option, and/or `--gitignore/--no-gitignore` flags, with summary
       output documenting the selected behavior.

- [x] E17a. Add compatibility tests proving existing `init_project()` callers
       still receive the expected created-path return type or compatibility
       facade while summary metadata remains additive.

- [x] E18. Add CLI init tests for repository hygiene summary output.

- [x] E19. Add MCP init tests for additive MCP hint and hygiene metadata, or
       document an explicit deferral if MCP hygiene is not implemented in this
       slice.

- [x] E19a. Add MCP init compatibility tests proving existing response fields
       remain present when new MCP hint or hygiene metadata is added.

- [x] E20. Run focused validation for MCP hint helper, gitignore hygiene helper,
       project initialization, and generated instruction tests.

- [x] E21. Run public-contract validation for CLI init and MCP init behavior.

- [x] E22. Record validation evidence and compatibility notes in the
       implementation summary.

## Implementation Summary

- Added `McpHint` construction with stable server-name slugging, project-local
  Python module command parts, Codex registration command parts, PATH fallback,
  missing-venv notes, and shell rendering.
- Added append-only `.gitignore` hygiene with a short P2P-managed section,
  idempotent exact-first matching, `.p2p/` warning-only behavior, and broad
  dotfile warning behavior.
- Extended `ProjectInitializationResult` additively with `mcp_hint` and
  `gitignore_hygiene`; `init_project()` remains a created-path compatibility
  facade.
- Updated CLI init summary with separate agent, repository hygiene, MCP setup,
  and next-step sections.
- Updated MCP init response with additive `mcp_hint` and `gitignore_hygiene`
  fields while preserving existing response fields.
- Updated generated agent instructions and docs with governed-root guidance.

Hygiene activation policy: automatic append-only default during init. No guided
prompt or opt-out flag was added in this slice because the helper is
non-destructive, idempotent, and visible in CLI/MCP summaries.

## Validation Evidence

- `.venv/bin/python -m pytest tests/test_mcp_hint_service.py tests/test_gitignore_hygiene_service.py -q`
- `.venv/bin/python -m pytest tests/test_project_initialization_service.py::test_project_initialization_summary_includes_mcp_hint_and_gitignore_hygiene tests/test_project_initialization_service.py::test_project_initialization_compat_facade_includes_gitignore_path_once tests/test_cli.py::test_cli_init_mcp_hint_uses_root_aware_project_python_command tests/test_cli.py::test_cli_init_prints_repository_hygiene_summary tests/test_mcp.py::test_mcp_init_returns_additive_mcp_hint_and_hygiene_metadata tests/test_agent_instructions_service.py::test_agent_instruction_service_generates_lifecycle_guidance_with_persistence_policy tests/test_docs_root_mcp_hygiene.py -q`
- `.venv/bin/python -m pytest tests/test_project_initialization_service.py tests/test_mcp_hint_service.py tests/test_gitignore_hygiene_service.py tests/test_agent_instructions_service.py -q`
- `.venv/bin/python -m pytest tests/test_cli.py -k "init or agent" -q`
- `.venv/bin/python -m pytest tests/test_mcp.py -k "init or agent" -q`
- `.venv/bin/python -m pytest tests/test_mcp_registry.py tests/test_mcp_maintenance_handler.py -q`
- `git diff --check`
- `.venv/bin/python -m pytest -q` -> 562 passed
