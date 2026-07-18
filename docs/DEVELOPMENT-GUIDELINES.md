# P2P Engine Development Guidelines

## Purpose

This document is the local development contract for the P2PWorkspace modular
refactoring work derived from `PROP-059`.

It is not P2P governance state and it does not authorize runtime behavior
changes by itself. It explains how future code changes should be structured so
the project can reduce the current monolith while preserving public behavior.

Use this guide together with:

- `AGENTS.md`
- `AGENTS-p2p-dev-specs.md`
- `specs/features/p2pworkspace-modular-refactoring-contract/`
- `specs/features/p2pworkspace-refactoring-inventory-and-extraction-map/`

## Current Architecture

The current runtime shape is intentionally compatibility-first but too
concentrated.

| Area | Current responsibility | Refactoring concern |
| --- | --- | --- |
| `src/p2p_engine/cli.py` | Typer application, command groups, command options, console output, error handling, calls into `P2PWorkspace` | Presentation and orchestration are mixed in a large file. |
| `src/p2p_engine/storage/filesystem.py` | `P2PWorkspace`, dataclasses, storage paths, proposal lifecycle, readiness, permissions, consent, Git-facing workflows, registries, project state, specs/export, rendering, validation, YAML/Markdown helpers | Primary monolith; mixes facade, use cases, persistence, rendering, validation, and helper logic. |
| `src/p2p_engine/mcp/tools.py` | MCP tool definitions, schemas, dispatch, JSON conversion, permission-gated operation orchestration, consent audit helpers | Schema, transport, routing, consent, and operation orchestration are coupled. |
| `src/p2p_engine/storage/git.py` | Thin Git subprocess adapter | Useful boundary, but callers still hold most guard logic. |
| `src/p2p_engine/core/` | Core dataclasses and small domain models | Should remain presentation-free and reusable. |
| `src/p2p_engine/exporters/` | Export-related helpers | Should stay deterministic and avoid hidden state reads. |
| `src/p2p_engine/prompts/` | Prompt renderers | Natural renderer boundary; prompt generation should remain advisory. |
| `tests/test_cli.py` | CLI compatibility, storage, and workflow tests | Main guard for user-visible CLI behavior. |
| `tests/test_mcp.py` | MCP tool, consent-gated, and JSON payload tests | Main guard for agent-visible MCP behavior. |

## Target Architecture

`P2PWorkspace` remains the stable compatibility facade. Existing CLI, MCP, and
library callers should continue to call it unless a separate proposal changes
the public API.

Future behavior should move behind internal boundaries:

| Layer | Owns | Must not own |
| --- | --- | --- |
| Domain models/helpers | Ids, statuses, dataclasses, pure normalization, domain rules | CLI printing, MCP schemas, filesystem side effects |
| Services/use cases | Proposal, readiness, permissions, consent, project state, registries, spec export, Work, choices, next actions | Typer/Rich output, MCP transport, raw subprocess plumbing |
| Adapters | Filesystem path/read/write primitives, Git subprocess operations, future provider APIs | Governance decisions, domain lifecycle rules |
| Renderers | Markdown/YAML/text output from prepared context | `.p2p` state discovery or writes |
| Validators | Shape and compatibility checks | File writes or side effects |
| Facade | Stable `P2PWorkspace` public methods and service delegation | New unrelated domain behavior when a service boundary exists |
| CLI presentation | Typer commands, options, console output, exit behavior | Business logic or storage layout decisions |
| MCP presentation/transport | Tool schemas, routing, JSON conversion, permission classes | Core domain behavior or consent receipt storage |

## Module Ownership Rules

Default placement for future code:

- `src/p2p_engine/services/`: cohesive internal application services.
- `src/p2p_engine/adapters/`: filesystem, Git, provider, or external system
  adapters.
- `src/p2p_engine/renderers/`: deterministic markdown/YAML/text renderers.
- `src/p2p_engine/validators/`: validation helpers that do not write state.
- `src/p2p_engine/parsers/`: markdown, frontmatter, YAML, and id parsing helpers
  when shared ownership is clear.
- `src/p2p_engine/cli_commands/`: only after services exist and CLI command
  splitting becomes presentation-only.
- `src/p2p_engine/mcp/registry.py` or domain MCP handler modules: only after
  services and consent-audit boundaries are stable.

Do not add new unrelated domain behavior directly to:

- `src/p2p_engine/cli.py`
- `src/p2p_engine/storage/filesystem.py`
- `src/p2p_engine/mcp/tools.py`

Allowed exceptions:

- facade delegation in `P2PWorkspace`;
- small CLI command glue that calls existing facade methods;
- MCP schema/routing glue that calls existing facade methods;
- compatibility fixes required by tests;
- narrow orchestration needed while a service extraction is in progress.

## Anti-Patterns

Avoid these patterns:

- adding more unrelated lifecycle logic to `filesystem.py`;
- putting business logic in Typer command handlers;
- coupling MCP schemas, dispatch, consent checks, and domain operations in one
  new block;
- duplicating YAML, Markdown, frontmatter, slug, or id parsing in multiple
  places;
- letting renderers read `.p2p` state directly;
- letting validators write files;
- hiding Git failures or changing guard order without tests;
- bypassing consent checks for permission-gated MCP operations;
- changing CLI/MCP/storage behavior as part of a refactor without a separate
  proposal-derived spec.

## Compatibility Contract

The following surfaces are compatibility-sensitive.

CLI compatibility:

- command names and grouping;
- argument and option names;
- default values;
- human-readable output asserted by tests;
- JSON output where present;
- exit behavior and clean error messages.

MCP compatibility:

- tool names;
- schemas;
- read-only, write-safe, and permission-gated classifications;
- JSON payload shapes;
- JSON-RPC behavior;
- consent id, actor, operation, and target requirements.

Storage compatibility:

- `.p2p` paths;
- YAML keys and markdown sections;
- proposal, choice, Change Set, Work, consent, intake, and next-action id
  formats;
- generated registries;
- project refresh outputs;
- validation findings and error messages.

Consent, Git, and sync compatibility:

- requested consent does not authorize execution;
- granted consent must match operation, target, actor, status, and expiry;
- consumed and used-with-error receipt transitions remain intact;
- MCP audit commits and optional pushes remain intact;
- branch names, lifecycle statuses, merge/finalize/cleanup behavior, and
  conflict continue/abort semantics remain intact;
- sync status, fetch, pull, push, remote URL mismatch, and clean-worktree guards
  remain intact.

Breaking changes to these surfaces require a separate accepted proposal or an
explicit local feature spec derived from one.

## Derived Artifact Contracts

Bundled verticals are canonical package resources. Each bundled pack owns one
`manifest.yml`, metadata-only `vertical.yml`, `rubrics.yml`, and ordered split
section files. Semantic checksums are computed from normalized typed content,
not resource paths or mtimes. External single-file packs remain a separate
compatibility input.

`SoftwareSpecService` owns exact source collection, pure candidate rendering,
versioned provenance, per-spec freshness and atomic complete-set writes. New
renderer inputs must be added to both the candidate model and source manifest;
workspace-wide fingerprints are not an acceptable shortcut. Status paths must
remain read-only.

`NextActionService` composes complete action families before dedupe and limit.
Change Set terminal states and active ordering come from
`services/changes.py`; decision context may enrich an action but cannot suppress
an active registry record. Generated actions remain derived and must not be
written to curated next-action storage.

`ProposalDecisionService` owns all proposal authority mutations. Workspace
schema v3 stores one append-only proposal-local ledger and derives proposal and
decision projections from it. CLI and MCP adapters must use the same
preview/apply request, token, retry and transition rules. A read, preview or
failed apply must not write state. MCP consent binds the exact proposal and
preview token and must not collapse owner authority into executor identity.
Dependent Change, Work, spec, vertical, project or publication lifecycles are
reported as impact and remediation work; decision apply never rewrites them.

## Testing Expectations

For every extraction:

- keep existing compatibility tests unchanged;
- add focused tests when moving normalization, validation, transition, or guard
  behavior that is currently covered only end-to-end;
- run CLI tests for touched commands;
- run MCP tests for touched tools, schemas, payloads, consent, or permission
  behavior;
- run storage/validation tests for `.p2p` artifact changes;
- run Git/sync tests for branch, remote, commit, publish, merge, cleanup,
  consent audit, or conflict behavior.

No test should be weakened or removed to make an extraction pass.

## Refactoring Roadmap

The roadmap is embedded here rather than split into a separate
`docs/REFACTORING-ROADMAP.md` so agents have one maintained development guide.

Follow the detailed map in:

- `specs/features/p2pworkspace-refactoring-inventory-and-extraction-map/inventory.md`

Service-before-presentation order:

1. Complete the architecture contract and inventory.
2. Extract `services.permissions`.
3. Extract `services.consent`.
4. Extract `services.remote_profile`.
5. Extract pure renderers and validators where ownership is clear.
6. Extract `services.software_specs`.
7. Extract `services.project_definition` and `services.spec_exports`.
8. Extract proposal document/contribution behavior, excluding branches.
9. Extract readiness behavior.
10. Extract non-branch proposal governance decisions.
11. Extract Work planning metadata.
12. Extract project state and registries.
13. Extract sync behavior.
14. Extract proposal branch lifecycle.
15. Extract Work branch lifecycle.
16. Extract MCP consent-audit helper behavior.
17. Split MCP registry/tool handlers.
18. Split CLI command modules.

First future extraction:

- `permissions` and `consent` are the first implementation candidates.
- The boundary is clear: permission policy in `.p2p/project/permissions.yml`
  and consent receipts in `.p2p/consents/CONSENT-XXX/consent.yml`.
- Safety value is high because consent protects permission-gated MCP
  operations.
- Presentation exposure is lower than CLI/MCP modularization.
- Existing CLI/MCP tests already cover the main compatibility behavior.

Do not start with CLI or MCP file splitting. Those files should become thinner
after service boundaries exist, not before.

## Future Feature Done Criteria

An extraction feature is done only when:

- `P2PWorkspace` still exposes the same public method signatures and return
  shapes;
- CLI and MCP behavior remain unchanged;
- `.p2p` paths and artifact shapes remain unchanged;
- moved behavior lives behind the boundary named in the local feature spec;
- focused tests cover moved logic where existing coverage was too broad;
- mapped compatibility tests pass;
- no unrelated generated `.p2p` state or local specs are changed accidentally.
