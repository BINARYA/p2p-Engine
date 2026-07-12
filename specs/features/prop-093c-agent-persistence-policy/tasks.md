# PROP-093C Agent Persistence Policy Tasks

## Status

`implemented`

## Implementation Rules

- Keep policy generation in agent template/service boundaries.
- Do not add generic filesystem write tools.
- Do not weaken `.p2p/` direct-edit restrictions.
- Preserve drift and unmanaged-file safety behavior.
- Prefer structured policy assertions over brittle full-text tests.

## Tasks

- [x] C1. Inspect current agent template tests and identify assertions affected
      by generated template hash or content changes.

- [x] C2. Add service tests proving generated `AGENTS.md` includes all required
      persistent write classes.

- [x] C3. Add service tests proving generated `AGENTS.md` includes the action
      preview rule and all required preview fields.

- [x] C3a. Add service tests proving exact-owner-request skip behavior is
      described narrowly: operation, target, artifact kind, and durable
      destination are all required.

- [x] C4. Add service tests proving generated `AGENTS.md` includes placement
      boundaries for `.p2p/`, `outputs/`, `drafts/`, `docs/drafts/`, and
      `docs/`.

- [x] C4a. Add service tests proving generated `AGENTS.md` describes placement
      policy as strict and tells agents not to invent durable output paths.

- [x] C4b. Add service tests proving generated `AGENTS.md` distinguishes
      placement buckets from artifact contracts or vertical primitives for
      exact evaluable output names.

- [x] C5. Add service tests proving generated `AGENTS.md` includes the compact
      routing playbook.

- [x] C6. Add service tests proving `.p2p/agent-policy.yml` contains structured
      write policy, placement policy, and routing policy fields.

- [x] C6a. Add service tests proving structured `placement_policy` includes
      `mode: strict`, unknown-destination behavior, and governed-state write
      surface constraints.

- [x] C6b. Add service tests proving structured policy marks generated exports
      as derived/non-canonical, stable documentation as non-canonical unless
      imported or declared, and local scratch as non-durable project memory.

- [x] C6c. Add service tests proving structured policy requires exact durable
      output names to come from artifact contracts, explicit vertical
      primitives, or exact owner requests.

- [x] C7. Add or update shared template blocks for write classes, action
      preview, artifact placement, and request routing.

- [x] C7a. Add or update shared template block for strict placement versus
      artifact-contract naming, including "do not invent durable output paths".

- [x] C8. Update `agent_policy()` to emit structured write policy, placement
      policy, and routing policy payloads.

- [x] C8a. Update `agent_policy()` to emit canonicality fields for generated
      exports, stable documentation, local scratch, and unknown destinations.

- [x] C9. Update generic `AGENTS.md` generation to include the shared policy
      blocks without removing existing governance, readiness, MCP, Git, or token
      budget rules.

- [x] C10. Update Codex project skill generation so it exposes the same
       persistence boundary and references the structured policy.

- [x] C11. Update Claude, Cursor, Copilot, Gemini, and shared-only OpenCode
       coverage so adapter-specific instructions can discover the same boundary.

- [x] C12. Add regression tests proving refresh still skips drifted and
       unmanaged generated files.

- [x] C13. Update template IDs or hashes where the existing registry model
       requires template-version tracking.

- [x] C14. Add CLI init or agent refresh tests that verify generated policy is
       present through public commands.

- [x] C15. Add MCP init or agent refresh tests proving MCP uses the same service
       behavior and does not introduce new write capabilities.

- [x] C16. Update `docs/AGENT-INTEGRATION.md` with the full write-class,
       preview, placement, and routing explanation.

- [x] C16a. Document that strict placement is not a complete artifact schema:
       evaluable output names come from artifact contracts, explicit vertical
       primitives, or exact owner requests.

- [x] C17. Update install/bootstrap docs if they summarize generated agent
       policy.

- [x] C18. Run focused validation for agent template/service tests.

- [x] C19. Run public-contract validation for CLI/MCP init and agent refresh
       behavior.

- [x] C20. Record validation evidence and any intentional wording
       compatibility changes in the implementation summary.

## Implementation Summary

- Added shared persistence-policy helpers in `agent_templates.py` for write
  classes, preview fields, exact-request fields, strict placement,
  artifact-contract naming, canonicality semantics, and routing playbook.
- Extended `agent_policy()` with `write_policy`, `placement_policy`,
  `artifact_contract_policy`, and `routing_playbook`.
- Added the full policy to generated `AGENTS.md` and the compact boundary to
  Codex, Claude, Cursor, Copilot, and Gemini adapter outputs. OpenCode remains
  shared-only through `AGENTS.md`.
- Updated maintained docs with write classes, preview rules, placement,
  routing, and the explicit statement that strict placement is not a complete
  artifact schema.
- Template IDs were intentionally left unchanged: the existing registry stores
  content hashes and detects stale/drifted generated files from those hashes.

## Validation Evidence

- `.venv/bin/python -m pytest tests/test_agent_instructions_service.py -q`
  -> `18 passed`.
- `.venv/bin/python -m pytest tests/test_cli.py::test_cli_init_status_create_and_prompt_flow tests/test_cli.py::test_cli_agent_instructions_refresh_adds_profiles_without_removing_existing -q`
  -> `2 passed`.
- `.venv/bin/python -m pytest tests/test_mcp.py::test_mcp_write_safe_bootstrap_tools -q`
  -> `1 passed`.
- `.venv/bin/python -m pytest tests/test_cli.py -k agent -q`
  -> `12 passed, 94 deselected`.
- `.venv/bin/python -m pytest tests/test_mcp.py -k "agent or write_safe_bootstrap" -q`
  -> `6 passed, 53 deselected`.
- `git diff --check` -> passed.
