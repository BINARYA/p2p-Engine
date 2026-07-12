# PROP-094 P2P-Governed Software Specification Lifecycle Tasks

## Status

`implemented`

## Implementation Rules

- Do not write `.p2p/` by hand.
- Keep P2P governance decisions owner-controlled.
- Preserve existing CLI commands, MCP tool names, and spec/export paths.
- Put new lifecycle policy in cohesive service/core modules; keep
  `P2PWorkspace`, CLI, and MCP as facade/presentation layers.
- Do not block legacy-compatible spec generation solely because an older project
  has no active software vertical.
- Add MCP parity for lifecycle guidance because this feature is agent-facing.
- Follow `specs/skills/ENGINEERING_QUALITY_SKILL.md` and
  `specs/skills/TEST_QUALITY_SKILL.md` before implementation.

## Tasks

- [x] T01. Review current software-spec, spec-export, project-vertical,
      project-definition, choice, CLI, MCP, and agent-template ownership before
      coding.
      - Covers: R001-R017, N002
      - Output: implementation notes in the work summary, not `.p2p/`.

- [x] T02. Add focused tests proving existing software-spec refresh, prompt,
      import, export, export-show, and export-validate behavior still works
      before lifecycle changes.
      - Covers: R011, N001
      - Suggested validation:
        `.venv/bin/python -m pytest tests/test_software_spec_service.py tests/test_spec_export_service.py -q`

- [x] T03. Add service or vertical tests proving a built-in `software_project`
      vertical is listed, shown, and validates cleanly.
      - Covers: R003, R004, R005
      - Expected files: `tests/test_project_verticals.py` or a focused vertical
        resource test.

- [x] T04. Add tests proving the software vertical exposes fields/sections for
      objective, users/actors, scope/MVP, workflows, data model, integrations,
      constraints/NFRs, acceptance/validation, and risks/decisions.
      - Covers: R003
      - Test layer: service/resource.

- [x] T05. Implement the `software_project` built-in vertical resource.
      - Covers: R003, R004, R005
      - Expected files:
        `src/p2p_engine/resources/verticals/software_project/`.
      - Completion: internal vertical validation passes with no safety warnings.

- [x] T06. Add tests proving project readiness review can report software
      vertical coverage gaps without requiring automatic activation.
      - Covers: R005, R008
      - Test layer: service/CLI JSON if needed.

- [x] T07. Define lifecycle core models for route, diagnostic, preflight, and
      view payloads.
      - Covers: R001, R012, R013, N003
      - Expected files:
        `src/p2p_engine/core/software_spec_lifecycle.py` or equivalent.
      - Completion: stable string values are documented in tests.

- [x] T08. Add service tests for deterministic lifecycle route mapping for all
      supported intents.
      - Covers: R001, R002, R012
      - Test layer: service/unit.

- [x] T09. Implement `SoftwareSpecLifecycleService` as read-only/advisory
      lifecycle policy.
      - Covers: R001, R002, R006, R007, R008, R015, R016, N002, N004
      - Expected files:
        `src/p2p_engine/services/software_spec_lifecycle.py`.
      - Completion: no method in this service writes files or mutates state.

- [x] T10. Add preflight tests for missing Change Set, missing governed source,
      non-accepted source proposal, accepted source proposal, inactive software
      vertical, and incomplete software definition state.
      - Covers: R006, R008, E001-E005
      - Test layer: service.

- [x] T11. Inspect current choice/blocking data model and add the smallest
      useful preflight coverage for known blocking choices.
      - Covers: R007
      - If a deterministic blocking relationship is not available, document an
        advisory-only first implementation in code comments/tests and do not
        invent relationships.

- [x] T12. Add `P2PWorkspace` facade delegation for lifecycle route/preflight
      without adding core logic to `storage/filesystem.py`.
      - Covers: R012, R013, N002
      - Expected file: `src/p2p_engine/storage/filesystem.py`.
      - Completion: facade tests or existing caller tests prove delegation.

- [x] T13. Integrate preflight into `refresh_software_spec()` so blockers fail
      before writing generated spec artifacts and advisories remain visible.
      - Covers: R006, R008, R009, E001-E005
      - Test layer: service/facade plus CLI for public output.

- [x] T14. Integrate preflight into `export_software_spec()` so blockers fail
      before writing target exports and advisories remain visible.
      - Covers: R010
      - Test layer: service/facade plus CLI/MCP public behavior.

- [x] T15. Add a read-only CLI lifecycle command under `p2p spec`.
      - Covers: R001, R002, R012, R015
      - Preferred command:
        `p2p spec lifecycle --intent implementation_spec --change CHANGE-001`.
      - Expected file: `src/p2p_engine/cli_commands/specs.py`.

- [x] T16. Add CLI tests for lifecycle command output, unsupported intent
      errors, blocker rendering, advisory rendering, and suggested commands.
      - Covers: R012, R015, E007
      - Test layer: CLI/public contract.

- [x] T17. Update `p2p spec refresh` CLI output to print lifecycle blockers or
      advisories using stable wording.
      - Covers: R009, R011
      - Compatibility: command name/options/path remain unchanged.

- [x] T18. Update `p2p spec export` CLI output to print lifecycle blockers or
      advisories using stable wording.
      - Covers: R010, R011
      - Compatibility: command name/options/path remain unchanged.

- [x] T19. Add CLI tests proving blocking preflight prevents refresh/export
      writes.
      - Covers: R009, R010, N004
      - Assertions: output path does not exist after blocking failure.

- [x] T20. Add MCP catalog entry for read-only/advisory `p2p_spec_lifecycle`.
      - Covers: R013
      - Expected file: `src/p2p_engine/mcp/catalog/work_specs.py`.
      - Completion: schema includes supported intent enum and optional
        `change_id`.

- [x] T21. Add MCP handler support for `p2p_spec_lifecycle`.
      - Covers: R013, R015
      - Expected file: `src/p2p_engine/mcp/handlers/work_specs.py`.
      - Completion: payload matches service view fields through `to_jsonable`.

- [x] T22. Add additive lifecycle/preflight payload fields to MCP
      `p2p_spec_refresh` and `p2p_spec_export`.
      - Covers: R009, R010, R013
      - Compatibility: existing `spec` and `export` response fields remain
        present.

- [x] T23. Add MCP tests for lifecycle tool schema, handler response,
      refresh/export additive diagnostics, and unsupported intent errors.
      - Covers: R013, E007
      - Suggested validation:
        `.venv/bin/python -m pytest tests/test_mcp_registry.py tests/test_mcp_work_spec_handler.py -q`

- [x] T24. Update generated agent policy payload with a
      `software_spec_lifecycle` section.
      - Covers: R014
      - Expected file: `src/p2p_engine/services/agent_templates.py`.
      - Required payload fields: route ids, commands, MCP tools, exact-file
        caveat, and owner-decision boundary.

- [x] T25. Update generated markdown instruction blocks so agents classify
      ambiguous spec requests before writing durable files.
      - Covers: R002, R014, R016
      - Preserve existing `PROP-093` persistent-write preview text.

- [x] T26. Add generated-instruction tests for route table, exact-file handling,
      software vertical guidance, and continued presence of the persistent-write
      policy.
      - Covers: R014, R016
      - Suggested validation:
        `.venv/bin/python -m pytest tests/test_agent_instructions_service.py -q`

- [x] T27. Update docs for CLI, MCP, and agent integration lifecycle guidance.
      - Covers: R017
      - Expected files:
        `docs/CLI-GUIDE.md`, `docs/MCP.md`, `docs/AGENT-INTEGRATION.md`.
      - Keep visible project definition export distinct from software spec
        export.

- [x] T28. Add focused docs checks only where docs wording is public contract.
      - Covers: R017
      - Test layer: docs text tests if an existing docs test file is present or
        a small targeted test is justified.

- [x] T29. Run focused service/resource validation.
      - Covers: R003-R010
      - Suggested commands:
        `.venv/bin/python -m pytest tests/test_project_verticals.py tests/test_software_spec_service.py tests/test_spec_export_service.py -q`

- [x] T30. Run public CLI/MCP validation.
      - Covers: R011-R013
      - Suggested commands:
        `.venv/bin/python -m pytest tests/test_cli.py -k "spec or vertical or definition" -q`
        `.venv/bin/python -m pytest tests/test_mcp_registry.py tests/test_mcp_work_spec_handler.py tests/test_mcp.py -k "spec or vertical" -q`

- [x] T31. Run generated instruction and docs validation.
      - Covers: R014, R017
      - Suggested commands:
        `.venv/bin/python -m pytest tests/test_agent_instructions_service.py -q`

- [x] T32. Run formatting and full validation before committing.
      - Covers: N001-N005
      - Required commands:
        `git diff --check`
        `.venv/bin/python -m pytest -q`

- [x] T33. Record implementation summary and validation evidence in this file
      after implementation is complete.
      - Covers: quality policy completion reporting
      - Include design choice, compatibility impact, behavior changes, files
        changed, tests added/updated, risks, and follow-up.

## Completion Criteria

- `software_project` vertical is available and valid.
- Lifecycle route/preflight guidance is implemented once and reused by CLI/MCP.
- Spec refresh/export block ungoverned implementation/export writes before
  writing files.
- Advisory gaps guide older projects without breaking compatibility.
- Generated agent instructions and docs explain the governed lifecycle.
- Focused, public-contract, and full-suite validation evidence is recorded.

## Implementation Summary

- Design choice: added a typed software-spec lifecycle model and
  `SoftwareSpecLifecycleService`, with `P2PWorkspace` kept as a thin facade for
  CLI/MCP compatibility.
- Compatibility impact: existing `p2p spec refresh`, `p2p spec export`, MCP
  `p2p_spec_refresh`, MCP `p2p_spec_export`, and generated output paths remain
  additive-compatible. Lifecycle diagnostics are added; blockers now fail before
  writing ungoverned spec/export artifacts.
- Behavior changes: added the built-in `software_project` vertical, read-only
  `p2p spec lifecycle`, read-only MCP `p2p_spec_lifecycle`, lifecycle preflight
  in refresh/export, advisory rendering, and agent-facing lifecycle policy.
- Files changed: `src/p2p_engine/core/`,
  `src/p2p_engine/services/`, `src/p2p_engine/storage/filesystem.py`,
  `src/p2p_engine/cli_commands/specs.py`, `src/p2p_engine/mcp/`,
  `src/p2p_engine/resources/verticals/software_project/`, `tests/`, and
  `docs/`.
- Risk: older projects without active `software_project` vertical receive
  advisories, not blockers. The blocking behavior is intentionally limited to
  missing/ungoverned/non-accepted Change Set source and known blocking choices.
- Follow-up: no separate docs text test was added because the updated docs are
  explanatory rather than parsed public output; CLI/MCP/agent-facing contracts
  are covered by tests.

## Validation Evidence

- `.venv/bin/python -m pytest tests/test_project_verticals.py tests/test_software_spec_service.py tests/test_spec_export_service.py tests/test_software_spec_lifecycle_service.py -q`
  - Result: `31 passed`
- `.venv/bin/python -m pytest tests/test_cli.py -k "spec or vertical or definition" -q`
  - Result: `5 passed, 108 deselected`
- `.venv/bin/python -m pytest tests/test_mcp_registry.py tests/test_mcp_work_spec_handler.py tests/test_mcp.py -k "spec or vertical or registry" -q`
  - Result: `19 passed, 57 deselected`
- `.venv/bin/python -m pytest tests/test_agent_instructions_service.py -q`
  - Result: `19 passed`
- `git diff --check`
  - Result: passed
- `.venv/bin/python -m pytest -q`
  - Result: `572 passed`
