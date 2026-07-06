# Design - MCP Artifact Import Parity

## Requirements Covered

- R001-R023
- N001-N009

## Key Decisions

- D001: Add explicit MCP tools per controlled import workflow instead of a
  generic import tool.
  Rationale: `PROP-088` requires total parity for known fixed-target CLI
  imports while keeping arbitrary artifact mutation deferred. Six explicit
  tools make the allowed write surface visible and avoid a generic file-write
  escape hatch.

- D002: Treat source-path import as the baseline contract and direct payload
  import as an additional input mode.
  Rationale: existing CLI services already define source-path behavior. MCP
  clients often hold generated content in memory, so payload mode avoids forcing
  clients to create temporary files outside the tool call.

- D003: Require exactly one input mode: `source`, `content`, or `artifacts`.
  Rationale: one mode per call keeps audit metadata clear and avoids ambiguous
  precedence between path and payload writes.

- D004: Keep artifact kind mapping and validation in
  `ProposalArtifactService` or a small adjacent service-owned helper.
  Rationale: MCP handlers are transport/presentation code. The domain service
  already owns import targets, allowed filenames, and validation.

- D005: Use `P2PWorkspace` only as a compatibility facade.
  Rationale: CLI, MCP, and tests already depend on the workspace facade, but
  new domain behavior should stay behind cohesive services.

- D006: Return structured MCP metadata and governance context.
  Rationale: MCP clients need machine-readable import results, while owner
  governance must remain explicit that no proposal decision occurred.

- D007: Do not auto-update artifact coverage state from content imports.
  Rationale: existing CLI imports write artifact content only. Artifact coverage
  state is a separate workflow with explicit tools for status, set, confirm,
  and legacy marking.

- D008: Keep prompt tools prompt-only.
  Rationale: existing MCP prompt tools are advisory and tested as not importing
  generated output. Import tools should be separate commands with write-safe
  names.

## Components

- `src/p2p_engine/services/proposal_artifacts.py`
  - Existing owner of prompt generation, exploration import, generated artifact
    import, impact import, target maps, and validation.
  - Add payload-capable import helpers or delegate to a small adjacent service
    helper without duplicating validation rules in MCP code.

- `src/p2p_engine/storage/filesystem.py`
  - Existing `P2PWorkspace` facade.
  - Add a delegating method only if MCP needs a stable facade call for
    proposal artifact content imports.

- `src/p2p_engine/mcp/catalog/proposals.py`
  - Add tool definitions for the import tools because these mutate proposal
    artifact content, not prompt state.

- `src/p2p_engine/mcp/registry.py`
  - Add tool names to `TOOL_NAMES` and ensure tool definitions remain complete,
    ordered, and duplicate-free.

- `src/p2p_engine/mcp/handlers/proposals.py`
  - Parse MCP arguments, enforce the one-input-mode rule, delegate to the
    workspace/service, and return JSON-compatible result metadata.

- `tests/test_proposal_artifact_service.py`
  - Cover target mapping, direct payload imports, allowlists, and validation at
    the service layer.

- `tests/test_mcp_proposal_handler.py`
  - Cover proposal-domain MCP handler behavior for new import tools.

- `tests/test_mcp.py`
  - Cover public tool listing, direct `call_tool`, prompt regression, and
    JSON-RPC behavior where useful.

- `tests/test_mcp_registry.py`
  - Cover tool registry completeness and expected names if the registry test
    owns that assertion.

- `docs/MCP.md`
  - Document supported tools, input modes, validation and audit boundaries,
    unsupported generic import, and artifact coverage state separation.

## Tool Contract

The MCP public surface should add these write-safe tools:

- `p2p_explore_import`
- `p2p_impact_import`
- `p2p_clarify_import`
- `p2p_synthesize_import`
- `p2p_plan_import`
- `p2p_tasks_import`

Common arguments:

```text
root: optional string
proposal_id: required string
source: optional string
content: optional string
artifacts: optional object mapping filename to string content
actor: optional string
```

Input-mode rules:

- exactly one of `source`, `content`, or `artifacts` must be provided;
- `source` preserves CLI parity;
- `content` writes the primary fixed target for the tool;
- `artifacts` is allowed only for exploration and impact imports;
- `artifacts` keys must be exact filenames from the allowlist.

Primary fixed targets for `content`:

| Tool | Target |
| --- | --- |
| `p2p_explore_import` | `exploration.md` |
| `p2p_impact_import` | `impact-map.yml` |
| `p2p_clarify_import` | `clarifications.md` |
| `p2p_synthesize_import` | `proposal.md` |
| `p2p_plan_import` | `execution-plan.md` |
| `p2p_tasks_import` | `tasks.yml` |

Exploration `artifacts` allowlist:

```text
exploration.md
findings.md
alternatives.md
open-questions.md
risks.md
assumptions.md
suggested-scope.md
```

Impact `artifacts` allowlist and validation:

```text
impact-map.yml          -> top-level key impact
related-proposals.yml   -> top-level key related_proposals
conflict-analysis.yml   -> top-level key conflicts
```

## Result Contract

Successful MCP imports should return a stable machine-readable shape:

```yaml
artifact_import:
  proposal_id: PROP-001
  kind: explore
  input_mode: content
  imported:
    - path: .p2p/proposals/PROP-001-example/exploration.md
      filename: exploration.md
      validated: true
  artifact_state_updated: false
governance:
  owner_decision_required: false
  decision_made: false
```

Notes:

- `imported[].path` should use repository-relative paths, matching existing
  service behavior.
- `validated` can be true for imports that passed explicit validation, and
  false or omitted only when no kind-specific validator exists.
- `artifact_state_updated` should remain false unless a separate accepted
  change makes coverage state updates part of import semantics.

## Source-Path Flow

1. MCP handler validates required arguments and input mode.
2. Handler maps tool name to import kind.
3. Handler delegates to `P2PWorkspace`.
4. Workspace delegates to `ProposalArtifactService`.
5. Existing source-path import method resolves the proposal directory,
   validates the source, writes fixed target files, and returns relative paths.
6. Handler formats the result payload and governance metadata.

## Direct Payload Flow

1. MCP handler validates required arguments and input mode.
2. Handler maps tool name to import kind.
3. Handler delegates raw payload strings to workspace/service code.
4. Service validates allowed filenames and kind-specific content before writing.
5. Service writes only fixed target files in the resolved proposal directory.
6. Handler returns structured metadata with `input_mode` set to `content` or
   `artifacts`.

Implementation options:

- Preferred: add service-owned helper methods that share the same target maps
  and validators used by existing import methods.
- Acceptable: stage payload content into controlled temporary files or
  directories and call the existing source-path import methods, provided
  validation, cleanup, and error behavior remain deterministic and tested.
- Avoid: implementing filename mapping, YAML validation, or proposal directory
  writes directly in MCP handlers.

## Public Surface And MCP Parity

- CLI contract: unchanged. Existing import commands remain the source-path
  baseline and must keep their current behavior.
- MCP contract: add six write-safe tools with explicit schemas.
- Storage contract: write only existing proposal artifact filenames.
- Documentation contract: update MCP documentation with tool examples and
  unsupported cases.
- Test contract:
  - service tests for file writes and validation;
  - MCP handler tests for schemas, payloads, errors, and governance metadata;
  - public tests for tool listing and JSON-RPC call behavior;
  - full-suite validation before handoff.

## Error Handling

Errors should fail before uncontrolled writes and should identify:

- import operation or tool name;
- proposal ID when available;
- input mode;
- unsupported filename or artifact kind;
- invalid source path;
- validation failure details from existing validators.

Expected rejected cases:

- missing `proposal_id`;
- proposal not found;
- no input mode;
- multiple input modes;
- invalid source path;
- directory source for single-file import tools;
- unsupported filename in `artifacts`;
- invalid impact YAML;
- invalid tasks YAML;
- generic arbitrary import request.

## Migration And Compatibility

- No migration is required.
- Existing `.p2p` proposal layout is unchanged.
- Existing CLI import commands are unchanged.
- Existing MCP prompt and artifact coverage state tools remain backward
  compatible.
- New MCP tools are additive.

## Risks And Tradeoffs

- Risk: payload-mode implementation could duplicate validation logic.
  Mitigation: keep validation in service helpers and add service tests.

- Risk: tool names could be confused with prompt tools.
  Mitigation: use `*_import` suffixes and document prompt tools as prompt-only.

- Risk: importing content may be mistaken for artifact coverage confirmation.
  Mitigation: return `artifact_state_updated: false` and document the separate
  coverage-state workflow.

- Risk: adding six tools increases registry maintenance.
  Mitigation: update registry tests and keep definitions explicit.

## Out Of Scope

- Generic artifact import.
- New CLI commands.
- Consent-gated import flow.
- Provider PR/MR behavior.
- Proposal decisions or owner overrides.
- Artifact coverage state mutation from content import.
- Refactoring the whole MCP dispatcher or proposal artifact service.
