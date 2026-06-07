# P2PWorkspace Modular Refactoring Status

This is the local development tracker for the `P2PWorkspace` modular
refactoring. It is not P2P governance state.

## Roadmap Status

| # | Roadmap item | Status | Local feature |
| --- | --- | --- | --- |
| 1 | Architecture contract and inventory | Done | `p2pworkspace-modular-refactoring-contract`, `p2pworkspace-refactoring-inventory-and-extraction-map` |
| 2 | Extract `services.permissions` | Done | `p2pworkspace-permissions-consent-service-extraction` |
| 3 | Extract `services.consent` | Done | `p2pworkspace-permissions-consent-service-extraction` |
| 4 | Extract `services.remote_profile` | Done | `p2pworkspace-remote-profile-service-extraction` |
| 5 | Extract pure renderers and validators | Done | `p2pworkspace-renderers-validators-foundation` |
| 6 | Extract software spec behavior | Done | `p2pworkspace-software-spec-service-extraction` |
| 7 | Extract project definition and spec exports | Done | `p2pworkspace-project-definition-and-spec-export-extraction` |
| 8 | Extract proposal document/contribution behavior, excluding branches | Done | `p2pworkspace-proposal-document-service-extraction` |
| 9 | Extract readiness behavior | Done | `p2pworkspace-readiness-service-extraction` |
| 10 | Extract non-branch proposal governance decisions | Done | `p2pworkspace-proposal-decision-service-extraction` |
| 11 | Extract Work planning metadata | Done | `p2pworkspace-work-planning-service-extraction` |
| 12 | Extract project state and registries | Done | `p2pworkspace-project-state-service-extraction`, `p2pworkspace-registry-service-extraction`, `p2pworkspace-project-assessment-service-extraction` |
| 13 | Extract sync behavior | Done | `p2pworkspace-sync-service-extraction` |
| 14 | Extract proposal branch lifecycle | Done | `p2pworkspace-proposal-branch-lifecycle-service-extraction` |
| 15 | Extract Work branch lifecycle | Done | `p2pworkspace-work-branch-lifecycle-service-extraction` |
| 16 | Extract MCP consent-audit helper behavior | Done | `mcp-consent-audit-helper-extraction` |
| 17 | Split MCP registry/tool handlers | Done | `mcp-registry-tool-handler-split` |
| 18 | Split CLI command modules | Done | `cli-command-module-split` |
| 19 | Extract next actions service | Done | `p2pworkspace-next-actions-service-extraction` |
| 20 | Extract conflict memory service | Done | `p2pworkspace-conflict-memory-service-extraction` |
| 21 | Extract choice lifecycle service | Done | `p2pworkspace-choice-lifecycle-service-extraction` |
| 22 | Extract intake lifecycle service | Done | `p2pworkspace-intake-lifecycle-service-extraction` |
| 23 | Extract Change Set lifecycle service | Done | `p2pworkspace-change-set-lifecycle-service-extraction` |
| 24 | Extract validation service | Done | `p2pworkspace-validation-service-extraction` |
| 25 | Extract project maturity and rubrics service | Done | `p2pworkspace-project-maturity-service-extraction` |
| 26 | Extract agent instruction orchestration service | Done | `p2pworkspace-agent-instructions-service-extraction` |
| 27 | Extract agent template renderer module | Done | `p2pworkspace-agent-template-renderer-extraction` |
| 28 | Extract project initialization service | Done | `p2pworkspace-project-initialization-service-extraction` |
| 29 | Extract governance and vote service | Done | `p2pworkspace-governance-service-extraction` |
| 30 | Extract proposal prompt and artifact service | Done | `p2pworkspace-proposal-prompt-artifact-service-extraction` |
| 31 | Extract context packet service | Done | `p2pworkspace-context-packet-service-extraction` |
| 32 | Extract project context renderer service | Done | `p2pworkspace-project-context-renderer-service-extraction` |
| 33 | Extract registry record builder service | Done | `p2pworkspace-registry-record-builder-service-extraction` |
| 34 | Move spec export renderer ownership to service and remove legacy filesystem helpers | Done | `p2pworkspace-spec-export-renderer-service-ownership` |
| 35 | Remove private agent integration facade wrappers | Done | `p2pworkspace-agent-integration-facade-cleanup` |
| 36 | Move Work retirement ownership to Work planning service | Done | `p2pworkspace-work-retire-service-ownership` |
| 37 | Remove duplicated Work planning result types from filesystem facade | Done | `p2pworkspace-work-planning-result-type-cleanup` |
| 38 | Remove duplicated service-owned result types from filesystem facade | Done | `p2pworkspace-service-result-type-cleanup` |
| 39 | Remove duplicated governance-adjacent service result types from filesystem facade | Done | `p2pworkspace-governance-result-type-cleanup` |
| 40 | Extract workspace status/check/proposal summary service | Done | `p2pworkspace-workspace-status-service-extraction` |
| 41 | Extract proposal draft commit service | Done | `p2pworkspace-proposal-draft-commit-service-extraction` |
| 42 | Remove dead filesystem helper functions after service extraction | Done | `p2pworkspace-dead-filesystem-helper-cleanup` |
| 43 | Remove unused private filesystem facade wrappers | Done | `p2pworkspace-filesystem-facade-wrapper-cleanup` |
| 44 | Rewire filesystem facade callbacks to service-owned methods | Done | `p2pworkspace-filesystem-callback-rewiring` |
| 45 | Move Work review suggestion helper ownership to Work branch service | Done | `p2pworkspace-work-review-suggestion-helper-extraction` |
| 46 | Extract generic filesystem facade helpers to foundation module | Done | `p2pworkspace-foundation-file-helper-extraction` |
| 47 | Consolidate low-risk service YAML helpers onto foundation module | Done | `p2pworkspace-foundation-helper-service-consolidation-1` |
| 48 | Consolidate tolerant service YAML helpers onto foundation module | Done | `p2pworkspace-foundation-helper-service-consolidation-2` |
| 49 | Consolidate spec, registry, and agent instruction YAML helpers | Done | `p2pworkspace-foundation-helper-service-consolidation-3` |
| 50 | Consolidate proposal, readiness, and choice helpers onto foundation module | Done | `p2pworkspace-foundation-helper-service-consolidation-4` |
| 51 | Consolidate Change Set and Intake helpers onto foundation module | Done | `p2pworkspace-foundation-helper-service-consolidation-5` |
| 52 | Consolidate project maturity helpers with custom YAML error support | Done | `p2pworkspace-project-maturity-helper-consolidation` |
| 53 | Consolidate Work planning YAML helpers onto foundation module | Done | `p2pworkspace-work-planning-helper-consolidation` |
| 54 | Consolidate proposal branch local file helpers onto foundation module | Done | `p2pworkspace-proposal-branch-helper-consolidation` |
| 55 | Consolidate Work branch local file helpers onto foundation module | Done | `p2pworkspace-work-branch-helper-consolidation` |
| 56 | Reassess remaining facade, CLI, and MCP concentration after helper consolidation | Done | `p2pworkspace-facade-final-reassessment` |
| 57 | Split MCP registry catalog by tool domain | Done | `mcp-registry-domain-catalog-split` |
| 58 | Split MCP collaboration handler by operational domain | Done | `mcp-collaboration-handler-domain-split` |
| 59 | Split CLI Change Set, software spec, and Work command registration | Done | `cli-work-spec-command-domain-split` |
| 60 | Split CLI proposal command registration by proposal subdomain | Done | `cli-proposal-command-domain-split` |
| 61 | Split CLI collaboration command registration by project collaboration subdomain | Done | `cli-collaboration-command-domain-split` |
| 62 | Close main structural refactoring phase with final remaining-file assessment | Done | `p2pworkspace-refactoring-closure-assessment` |
| 63 | Complete final quality review, cleanup, and validation pass | Done | `p2pworkspace-final-quality-review` |

## Main Refactoring Phase Status

The main structural refactoring phase is complete. Remaining large files are
classified as compatibility facade, composition root, or cohesive domain
services. Future refactors should be opened as focused local features only when
new evidence shows mixed responsibilities, duplicated helper behavior, or
domain-specific testability problems.

Final quality review is complete. `.venv/bin/p2p validate` reports no findings
and the full automated test suite reports 371 passing tests.

## Extracted Services

- `services.permissions`
- `services.consent`
- `services.remote_profile`
- `foundation.markdown`
- `foundation.validators`
- `services.software_spec`
- `services.spec_export`
- `services.proposals`
- `services.readiness`
- `services.proposal_decisions`
- `services.work_planning`
- `services.registries`
- `services.project_state`
- `services.project_assessment`
- `services.sync`
- `services.proposal_branches`
- `services.work_branches`
- `services.next_actions`
- `services.conflicts`
- `services.choices`
- `services.intake`
- `services.changes`
- `services.validation`
- `services.project_maturity`
- `services.agent_instructions`
- `services.agent_templates`
- `services.project_initialization`
- `services.governance`
- `services.proposal_artifacts`
- `services.context_packets`
- `services.project_contexts`
- `services.registry_records`
- `services.spec_export` owns export renderers and validation metadata
- `services.agent_instructions` owns agent integration registry helpers
- `services.work_planning` owns Work retirement metadata updates
- `services.work_planning` owns Work planning result types
- Extracted services own their status/export/profile result types
- Extracted governance-adjacent services own their proposal/readiness/permission/consent result types
- `services.workspace_status` owns workspace status, check, and proposal summaries
- `services.proposal_drafts` owns proposal draft commit behavior and result type
- Dead legacy filesystem helpers removed after service extraction
- Unused private `P2PWorkspace` pass-through wrappers removed after facade
  reassessment
- Service constructor callbacks in `storage.filesystem` now point directly to
  service-owned methods where safe, removing the remaining private callback
  wrapper layer
- Work branch external review suggestion formatting is owned by
  `services.work_branches` instead of `storage.filesystem`
- Generic slug, identity slug, YAML read/dump, YAML mapping, and relative path
  helpers are available from `foundation.files`
- `services.conflicts`, `services.project_assessment`, and
  `services.next_actions` now consume `foundation.files` instead of local YAML
  helper copies
- `foundation.files` now exposes strict and tolerant YAML mapping readers;
  `services.remote_profile`, `services.permissions`, `services.consent`, and
  `services.project_state` consume foundation helpers instead of local copies
- `services.software_spec`, `services.registries`, and
  `services.agent_instructions` consume `foundation.files`; `services.project_maturity`
  remains local because its YAML non-mapping error message is intentionally
  distinct
- `foundation.files.slugify` supports explicit fallback values; `services.proposals`,
  `services.readiness`, and `services.choices` consume foundation helpers while
  preserving proposal `"project"` and choice `"item"` slug fallbacks
- `services.changes` and `services.intake` consume `foundation.files` while
  preserving strict YAML mapping semantics and Change Set `"item"` slug fallback
- `foundation.files.read_yaml_mapping` supports custom non-mapping error text;
  `services.project_maturity` consumes foundation helpers while preserving its
  `YAML document must be a mapping: <path>` message
- `services.work_planning` consumes `foundation.files` for strict YAML mapping
  reads and YAML serialization while preserving Work manifest behavior
- `services.proposal_branches` consumes `foundation.files` for local metadata
  YAML reads/dumps and slug normalization while keeping raw Git-ref YAML parsing
  local to the service
- `services.work_branches` consumes `foundation.files` for local Work manifest
  YAML reads/dumps while keeping raw Git-ref YAML parsing local to the service
- Final facade reassessment confirms that `storage.filesystem` should remain the
  `P2PWorkspace` compatibility facade for now; the next focused candidate is
  the MCP registry catalog, not another filesystem extraction.
- `mcp.registry` now remains a 35-line public compatibility assembler while MCP
  tool definitions live under `mcp.catalog` domain modules. `TOOL_NAMES` order
  now matches the ordered names returned by `tool_definitions()`.
- `mcp.handlers.collaboration` now remains a 22-line public router. Remote and
  consent tools live in `mcp.handlers.collaboration_remote`, sync tools live in
  `mcp.handlers.collaboration_sync`, and proposal branch collaboration flows
  live in `mcp.handlers.collaboration_proposals`.
- `cli_commands.work_specs` now remains a 17-line public compatibility wrapper.
  Change Set commands live in `cli_commands.changes`, software spec commands
  live in `cli_commands.specs`, and Work commands live in `cli_commands.work`.
- `cli_commands.proposals` now remains a 23-line public compatibility wrapper.
  Proposal core, readiness, branch lifecycle, decision, and contribution
  command surfaces live in focused proposal CLI modules.
- `cli_commands.collaboration` now remains a 27-line public compatibility
  wrapper. Governance, project analysis, registry, intake, and choice command
  surfaces live in focused CLI modules.

## Remaining Runtime Concentration

The main compatibility files still contain important behavior:

- `storage/filesystem.py`: remaining compatibility facade and composition
  helpers. Project
  initialization delegates to `services.project_initialization`; validation delegates to
  `services.validation`; project maturity/rubrics delegates to
  `services.project_maturity`; agent instruction orchestration delegates to
  `services.agent_instructions`; agent template rendering lives in
  `services.agent_templates`; governance and vote behavior delegates to
  `services.governance`; proposal prompt and artifact behavior delegates to
  `services.proposal_artifacts`; compact context assembly delegates to
  `services.context_packets`; intake and project brief context rendering
  delegates to `services.project_contexts`; registry record construction
  delegates to `services.registry_records`; software-spec generation delegates
  to `services.software_spec`; project-definition and spec-export rendering
  delegates to `services.spec_export`; agent integration registry behavior
  delegates to `services.agent_instructions`; Work planning and metadata-only
  retirement delegate to `services.work_planning`. `filesystem.py` is now
  approximately 1,716 lines after removing legacy spec export helpers,
  duplicated software-spec renderer helpers, private agent integration facade
  wrappers, Work retirement implementation, and duplicated Work planning result
  types plus duplicated service-owned status/export/profile and
  governance-adjacent result types. Workspace status, proposal summary scanning,
  and workspace bootstrap checks delegate to `services.workspace_status`.
  Proposal draft commits delegate to `services.proposal_drafts`.
  Dead legacy helpers from pre-service permission, consent, proposal renderer,
  exploration, status update, and conflict-marker code paths have been removed.
  Unused private pass-through wrappers for consent paths, project assessment
  compute, spec export project definitions, Work summaries/IDs, registry
  proposal lookup, proposal branch metadata, and sync remote selection have
  been removed. Remaining callback wrappers for proposal lookup, change lookup,
  Work lookup, duplicate proposal detection, permissions paths, and registry
  records have been rewired to service-owned methods and removed.
  Work review suggestion URL formatting has moved to `services.work_branches`.
  Generic slug/path/YAML helpers have moved to `foundation.files`; the only
  remaining module-level helper in `storage.filesystem` is the facade-local
  duplicate proposal ID message formatter. `filesystem.py` has no local
  dataclasses and is now approximately 1,276 lines.
- `mcp/tools.py`: compatibility dispatch facade only. Tool registry and schema
  definitions live in `mcp/registry.py`; runtime execution is split across
  `mcp/handlers/maintenance.py`, `project.py`, `proposals.py`,
  `collaboration.py`, and `work_specs.py`.
- `cli.py`: Typer command grouping, output formatting, and command glue.

## Next Recommended Order

1. Create `specs/features/mcp-registry-domain-catalog-split/` before changing
   runtime MCP registry code. The focused goal is to split
   `src/p2p_engine/mcp/registry.py` by tool domain while preserving
   `tool_definitions()`, `TOOL_NAMES`, tool names, descriptions, schemas, and
   required fields.
2. Keep `storage.filesystem` as the `P2PWorkspace` compatibility facade unless
   a future feature defines a deliberate facade partitioning strategy with
   compatibility tests.
3. Keep `cli.py` and `mcp/tools.py` as compatibility facades; add new behavior
   behind services, command modules, handlers, registries, or renderers.

Do not start a new runtime extraction without first updating local specs with a
focused feature scope and task checklist.
