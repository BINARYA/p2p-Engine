# Implementation Note - Governance Policy Convergence

## Design Choice

Implemented governance policy convergence as a dedicated read-only
`GovernancePolicyService` behind the existing `P2PWorkspace` facade.

The service owns governance preflight classification, actor resolution,
advisory vote alignment, explicit blocker handling, deterministic precedent
search, and governance-only validation. CLI and MCP layers only render or
dispatch the service-owned contracts.

## Framework / Project Convention Considered

The implementation follows the local P2PWorkspace extraction direction:

- no new domain logic was added to `src/p2p_engine/cli.py`,
  `src/p2p_engine/mcp/tools.py`, or `src/p2p_engine/storage/filesystem.py`;
- `P2PWorkspace` received only cached service construction and delegating facade
  methods;
- public CLI/MCP behavior is additive and read-only for the new governance
  preflight surfaces.

## Compatibility Impact

Existing governance, vote, precedent, choice, validation, CLI, and MCP behavior
is preserved.

Additive public surfaces:

- CLI:
  - `p2p governance validate`
  - `p2p choice governance-preflight`
  - `p2p precedent search`
  - `--format json|yaml` support for governance status, vote status, governance
    validation, preflight, and precedent search
- MCP:
  - `p2p_governance_status`
  - `p2p_governance_validate`
  - `p2p_choice_governance_preflight`
  - `p2p_vote_status`
  - `p2p_precedent_search`

Deferred MCP write tools remain absent:

- `p2p_vote_record`
- `p2p_precedent_record`
- `p2p_choice_decide`

## Behavior Changes

- Choice governance preflight returns `schema_version:
  governance-preflight/v1`.
- Choice governance preflight result statuses use the accepted contract values:
  `ready`, `requires_rationale`, `requires_owner_override`, and `blocked`.
- `permissions.yml` is the primary actor/role source when present.
- Legacy governance roles are fallback evidence only when `permissions.yml` is
  absent; mismatches are warnings.
- Votes are advisory evidence; vote conflicts and ties produce warnings, not
  blocking errors. Vote conflict alignment is reported as `conflicts`.
- Active explicit blockers block normal finalization and signal owner override
  requirements.
- Precedent search is deterministic and only matches explicit precedent ids,
  proposal ids, choice ids, or tags.
- Deterministic related precedents are listed in `precedents` and surfaced with
  `P2P_GOV_RELATED_PRECEDENTS`.
- Present malformed governance artifacts fail closed in preflight with
  structured blocking diagnostics.
- Repository validation now includes governance artifact diagnostics for present
  invalid governance artifacts while tolerating missing optional governance
  files.

## Files Changed

- `src/p2p_engine/services/governance_policy.py`
- `src/p2p_engine/services/validation.py`
- `src/p2p_engine/storage/filesystem.py`
- `src/p2p_engine/cli_commands/formatting.py`
- `src/p2p_engine/cli_commands/governance.py`
- `src/p2p_engine/cli_commands/choices.py`
- `src/p2p_engine/mcp/catalog/project.py`
- `src/p2p_engine/mcp/handlers/project.py`
- `src/p2p_engine/mcp/registry.py`
- `tests/test_governance_policy_service.py`
- `tests/test_validation_service.py`
- `tests/test_cli.py`
- `tests/test_mcp.py`
- `tests/test_mcp_registry.py`
- `docs/CLI-GUIDE.md`
- `docs/MCP.md`

## Tests Run

Focused service validation:

```bash
.venv/bin/pytest tests/test_governance_policy_service.py tests/test_validation_service.py tests/test_cli.py::test_cli_governance_policy_read_only_surfaces tests/test_cli.py::test_cli_precedent_search_matches_explicit_fields_only tests/test_mcp.py::test_mcp_governance_policy_read_only_tools tests/test_mcp.py::test_mcp_governance_preflight_reports_malformed_precedents tests/test_mcp_registry.py
```

Result: `39 passed`.

Validation-focused tests:

```bash
.venv/bin/pytest tests/test_validation_service.py tests/test_governance_policy_service.py
```

Result: `31 passed`.

Public CLI/MCP validation:

```bash
.venv/bin/pytest tests/test_governance_policy_service.py tests/test_validation_service.py tests/test_cli.py tests/test_mcp.py tests/test_mcp_registry.py
```

Result: `194 passed`.

Repository validation:

```bash
.venv/bin/p2p validate
```

Result: `errors: 0`, `warnings: 0`, `infos: 0`.

Full suite:

```bash
.venv/bin/pytest
```

Result: `491 passed`.

## Residual Risks

- Preflight currently summarizes proposal-local votes through the first related
  proposal on the choice. This matches the current artifact model, but a future
  proposal could introduce native choice-level vote artifacts.
- Governance preflight is read-only and does not enforce finalization itself.
  Future owner-controlled decision commands should call the same service before
  deciding if enforcement is required.

## Follow-Ups

- Consider adding native choice-level vote storage only if project-level choice
  voting becomes a supported governance workflow.
- Consider adding explicit owner override rationale capture to the future
  choice decision command path, separate from this read-only preflight feature.
