# P2PWorkspace Refactoring Closure Assessment Design

## Current Largest Files

| File | Lines | Classification | Closure Assessment |
| --- | ---: | --- | --- |
| `storage/filesystem.py` | 1,276 | Compatibility facade and service composition root | Keep. Splitting requires an explicit public API partition strategy. |
| `services/work_branches.py` | 932 | Domain service | Keep. It owns a complex Work branch lifecycle, not mixed presentation/facade code. |
| `services/proposal_branches.py` | 931 | Domain service | Keep. It owns a complex proposal branch lifecycle, not mixed presentation/facade code. |
| `services/agent_templates.py` | 624 | Template renderer service | Optional future candidate only if template groups need independent ownership. |
| `services/spec_export.py` | 560 | Export service | Keep. It owns cohesive export rendering/validation behavior. |
| `services/readiness.py` | 525 | Readiness service | Keep. It owns a cohesive proposal readiness domain. |
| `mcp/handlers/collaboration_proposals.py` | 457 | MCP proposal collaboration handler | Optional future candidate. It is large but now has one operational domain. |
| `services/project_maturity.py` | 438 | Project maturity service | Keep. Cohesive assessment/rubric behavior. |
| `services/choices.py` | 416 | Choice lifecycle service | Keep. Cohesive domain behavior. |
| `services/agent_instructions.py` | 414 | Agent instruction orchestration service | Keep. Cohesive generated-agent behavior. |
| `services/intake.py` | 413 | Intake lifecycle service | Keep. Cohesive intake behavior. |
| `services/next_actions.py` | 407 | Next action service | Keep. Cohesive next-action behavior. |

## Assessment

The original refactoring objective was to move behavior out of large mixed
runtime surfaces such as `P2PWorkspace`, `mcp/tools.py`, `mcp/registry.py`, and
large CLI modules into cohesive services, handlers, catalog modules, and command
modules.

That objective is satisfied:

- `P2PWorkspace` remains a compatibility facade and composition root.
- MCP tool definitions are split into domain catalogs.
- MCP collaboration handling is split into remote/consent, sync, and proposal
  collaboration modules.
- CLI command registration is split by command domain.
- Shared file helpers are consolidated in `foundation.files`.
- Runtime behavior is covered by focused and full-suite tests after each step.

The remaining large files are primarily cohesive domain services. Further
splitting them only by line count would raise churn and risk without a clear
ownership improvement.

## Closure Decision

The main structural refactoring phase is complete.

Future refactors should be treated as new focused work, not continuation of the
current broad extraction, unless they identify one of these concrete conditions:

- a domain service contains two independent lifecycles with separate tests;
- a handler mixes unrelated MCP tool families again;
- a CLI module grows past its current domain and starts owning unrelated command
  groups;
- repeated helper logic emerges across services after new features are added.

## Recommended Remaining Work

No mandatory runtime split remains for the current objective.

Recommended follow-up before commit/PR:

- review the large dirty worktree as one refactoring batch;
- run final validation/full suite once more before commit;
- prepare a concise commit/PR summary grouped by service extraction, MCP split,
  CLI split, and tracking specs.
