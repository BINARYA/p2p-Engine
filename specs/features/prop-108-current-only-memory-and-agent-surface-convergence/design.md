# Design - Current-Only Memory And Agent Surface Convergence

## Requirements Covered

- Public surfaces and agent guidance: R001-R014.
- Template generation and diagnostics: R015-R024.
- Current-only memory contract: R025-R046.
- Release and canonical project: R047-R051.
- Quality constraints: N001-N006 and AC001-AC015.

## Decision Summary

Implementation is split into two release-gated blocks:

1. **Surface convergence** establishes derived CLI/MCP inventories, an explicit
   capability catalog and product-generation-aware adapter diagnostics.
2. **Memory convergence** inventories each persisted authority and removes every
   obsolete interpretation or write path after current behavior is protected by
   focused tests.

Block A is completed first because it provides the checks used to prove that
Block B does not leave stale commands, tools, templates or packaged resources.
The release is not complete until both blocks and installed-wheel verification
pass.

## Key Decisions

### D001 - Runtime Registries Are Ground Truth For Existence

CLI command existence is collected from the registered Typer application. MCP
tool existence is collected from the MCP registry used by the server. Tests and
documentation checks do not maintain independent full command lists.

Rationale: manually synchronized command inventories caused the drift found by
the audit.

### D002 - Intent Is Declared In A Capability Catalog

A small structured catalog maps conceptual agent operations to registered CLI
paths, MCP tools and exposure policy. Runtime introspection proves existence;
the catalog records intent that cannot be inferred from registration alone.

Each capability record contains:

```yaml
id: vertical.registry.pull
cli:
  - p2p vertical registry pull
mcp: []
exposure: cli_only
authority: authenticated_user
reason: Remote registry installation is not exposed by the local MCP server.
templates: [generic, codex, claude]
```

Allowed exposure values are `cli_and_mcp`, `cli_only`, `mcp_only`,
`local_administration`, `owner_governed` and `intentionally_unavailable`.
Catalog validation rejects missing registered targets, duplicate ownership and
unclassified agent-relevant operations.

### D003 - Structured Documentation Regions, Not Prose Scraping

Maintained command and MCP references use delimited generated/checkable regions
or structured source data. CI checks those regions against runtime registries.
General prose and explicitly historical documents are not parsed as if every
code span were a public contract.

Rationale: broad Markdown command extraction is brittle and would make release
notes containing old commands fail.

### D004 - Generation Identity Is Separate From Content Hash

Every current template definition has:

- stable `template_id` for the logical file kind;
- `generation_id` for the current shipped semantics;
- rendered content hash recorded per project file.

`generation_id` is derived from canonical template semantics and the referenced
capability-catalog generation, or is an explicit deterministic version whose
change is enforced by a semantic-hash test. It never contains time data.

The managed state in `.p2p/agent-integrations.yml` records both IDs and the
content hash. Generated Markdown headers carry the IDs needed for diagnosis.
`.p2p/agent-policy.yml` is generated under the same contract.

### D005 - Drift Is A Two-Axis State

The shared diagnostic model records:

```text
content:     clean | modified | missing
generation:  current | obsolete | unknown
```

Presentation may expose convenient aggregate labels, but must not collapse a
modified obsolete file into one ambiguous status. `AgentInstructionsService`
owns this classification and is reused by CLI, validation and MCP handlers.

`agent doctor` and validation are read-only. `agent update` renders candidates,
checks existing recorded hashes and refuses modified targets unless the caller
uses the existing explicit force/conflict path. Updating an obsolete but clean
file is safe and refreshes both IDs and hash atomically.

### D006 - Current-Only Means One Authority, Not One File

A memory family may contain an authoritative structured artifact plus
non-authoritative narrative evidence. Only one representation may determine
state. For example, `questions.yml` may be authoritative while a narrative
discussion remains readable evidence; the narrative cannot substitute for a
missing `questions.yml`.

Each family inventory records:

```text
family
current schema/contract
authoritative paths
derived or narrative paths
readers
writers
validators
CLI commands
MCP tools
facade methods
fixtures/examples
obsolete paths and disposition
```

### D007 - Recognition For Rejection Is Not Compatibility

Current-only preflight may inspect a version marker, forbidden filename or
minimal shape signature to return a useful unsupported-form error. It must not
interpret old semantics, produce a current domain model, or write normalized
state.

Existing family-specific unsupported codes remain where already public, such
as workspace and vertical-pack schema errors. Other families use one stable
current-memory error carrying `family`, `observed_form`, `expected_contract`
and `recovery` details. Recovery tells development users to recreate state or
restore an external archive; it does not advertise a runtime converter.

### D008 - Remove Entry Points From The Inside Out

For each family:

1. identify and characterize the current contract;
2. add current happy-path and obsolete zero-write rejection tests;
3. remove obsolete service readers/writers and state variants;
4. remove facade wrappers;
5. remove CLI and MCP registrations, handlers and schemas;
6. remove obsolete docs, templates, fixtures and package resources;
7. run the public-surface inventory check.

This order avoids leaving a registered command that calls deleted behavior or a
hidden service reachable through one adapter.

### D009 - MCP Remains A Governed Subset

MCP is not wrapped around every CLI leaf. Existing current tools keep their
protocol-native payloads and permission/consent behavior. Obsolete MCP tools are
deleted from catalog, registry, handlers, docs and tests together. CLI-only
vertical registry and draft operations are explained in generated agent
guidance through the capability catalog.

### D010 - Canonical Project Reset Is Release Verification

The existing canonical project is archived outside the active project root.
A repository-only audit command or documented shell procedure records semantic
counts and identities, but no converter is added to `src/p2p_engine` or package
data.

A fresh project is initialized with the built release-candidate wheel. Required
project direction is re-established through public CLI commands. The old archive
remains historical evidence and is never opened by the released runtime during
normal operation.

## Architecture

### Block A - Surface Convergence

```text
Typer app registry -----------+
                              |
MCP TOOL_NAMES/catalog -------+--> PublicSurfaceInventory
                              |        |
Agent capability catalog -----+        +--> invariant checks
Release/package constants ----+        +--> template context
                                       +--> docs check data

AgentTemplateCatalog --> renderer --> generated project files
         |                                |
         +--> current generation IDs      +--> physical content hashes
                          \                /
                           AgentInstructionsService
                            |       |       |
                           CLI   validate   MCP
```

Suggested ownership:

- `services/public_surface_inventory.py`: registered CLI/MCP collection and
  validation.
- `resources/agent-capabilities.yml` or an equivalently typed package catalog:
  operation intent and exposure classification.
- `services/agent_templates.py`: current logical templates and generation IDs.
- `services/agent_instructions.py`: managed records, two-axis drift and update
  orchestration.
- `cli_commands/agents.py`: text/JSON presentation only.
- `mcp/catalog/agents.py` and corresponding handler: the same read model, if an
  agent inspection tool is currently exposed.
- documentation test/generator support under repository scripts or tests; no
  second runtime command registry.

No new public command group is required. Existing agent inspection, validation
and version surfaces are sufficient unless implementation proves a separately
accepted public command is necessary.

### Block B - Memory Convergence

The initial family map is in `compatibility-inventory.md`. Implementation must
expand it to every discovered path before deletion starts. Primary ownership
areas include:

- `core/workspace_schema.py`, `services/workspace_schema.py`, runtime CLI;
- `core/runtime_contract.py`, `services/runtime_contract.py`;
- `core/proposal_artifact_state.py`, `services/proposal_artifact_state.py`;
- `core/proposal_decision_events.py`, decision ledger/authority services;
- `core/project_questions.py`, `services/project_questions.py`;
- permissions and governance-policy services;
- decision-context source/topology/authority services;
- registry, software-spec, publication, readiness, context-packet, workspace-
  status and derived-freshness services;
- `storage/filesystem.py` facade methods;
- CLI registration, MCP catalogs/handlers/registry, docs, examples and tests.

Independent schema constants remain near their owning domain modules. There is
no global schema number that changes every file family together.

## Current Family Outcomes

The implementation inventory must confirm these outcomes before code deletion:

| Family | Current outcome | Obsolete outcome removed |
| --- | --- | --- |
| Workspace | schema 3 only | migration plan/apply/recovery runtime tree |
| Vertical packs | schema 2, package format 1 | old pack readers and implicit defaults |
| Runtime contract | explicit current contract | `legacy_undeclared` adoption path |
| Proposal artifacts | explicit current artifact state | `legacy_absent`, `absent_legacy`, mark-legacy |
| Proposal decisions | decision event ledger | legacy projection adapter and resolution |
| Project questions | structured question authority | definition-question migration/bindings |
| Permissions | explicit permissions authority | governance-role fallback |
| Relations | canonical relation enum values | compatibility aliases and normalization |
| Registries | verifiable bundle manifest | `legacy_unverifiable` state |
| Software specs | current provenance contract | legacy generated origin/freshness |
| Publications | current edition paths | runtime legacy path aliases |
| Readiness/derived state | current typed states | informational/current-legacy fallbacks |

If discovery shows that one listed item is actually required current semantics,
the implementation must update requirements and design before retaining it. A
comment in code is not sufficient to override this accepted scope.

## Error Handling And Atomicity

- Unsupported memory is rejected during preflight before mutation candidate
  construction.
- Detection returns stable structured detail in CLI JSON and protocol-native MCP
  errors through existing adapters.
- Removed commands fail as unknown commands/tools; they are not retained as
  stubs that point to migration guidance.
- Template update keeps existing atomic/precondition behavior for multiple
  managed files.
- Read-only diagnostics never repair or regenerate state implicitly.
- Installed-wheel checks run without network access; remote vertical guidance
  is validated structurally and transport behavior remains covered by existing
  registry tests.

## Documentation Contract

Current maintained surfaces include at least:

- `README.md`;
- `docs/INSTALL.md`;
- `docs/CLI-GUIDE.md` and `docs/CLI-CONTRACT.md`;
- `docs/MCP.md`;
- `docs/AGENT-INTEGRATION.md`;
- `docs/WORKSPACE-SCHEMA.md`;
- current examples and generated agent templates;
- `CHANGELOG.md` current release section.

Historical development reviews and completed feature specs may retain old
terms. Any executable examples they still present as current must be corrected
or explicitly marked historical.

## Test Strategy

Following `specs/skills/TEST_QUALITY_SKILL.md`:

1. service tests prove registry extraction, capability validation, two-axis
   drift and family preflight behavior;
2. focused CLI tests prove text/JSON agent diagnostics and removed commands;
3. MCP registry/catalog/handler tests prove current tools and removed aliases;
4. documentation contract tests prove maintained reference convergence;
5. zero-write tree-hash tests prove obsolete forms cannot mutate state;
6. source and built-wheel tests prove identical resources and clean init;
7. the full suite detects hidden compatibility consumers.

Tests whose only assertion is successful legacy interpretation are deleted, not
renamed. Replacement tests assert current behavior or explicit rejection.

## Migration And Compatibility

There is no shipped migration. This release intentionally breaks old project
state, old generated template generations and obsolete CLI/MCP aliases.

The canonical development project uses archive, semantic inventory and clean
recreation. WaveKit alignment, worker pinning and any remote registry/device
endpoint work occur later in the separate WaveKit repository.

## Risks And Mitigations

- **Current semantics hidden in adapters**: characterize current behavior before
  deleting each family and require an inventory disposition.
- **Over-broad legacy search**: classify historical evidence separately and use
  reachability, not vocabulary alone.
- **Template updates overwrite user work**: preserve independent content drift
  and require explicit conflict handling.
- **Docs checks become brittle**: validate structured current regions, not all
  Markdown code spans.
- **MCP security regression**: classify omissions and retain current permission
  and consent tests.
- **Wheel/source divergence**: compare capability and generation semantic hashes
  after installing the built wheel.
- **Canonical state loss**: archive and inventory before clean recreation.

## Out Of Scope

- WaveKit source and protocol implementation.
- A compatibility feature flag.
- A hidden environment variable that re-enables old loaders.
- Automatic project archive conversion.
- Full CLI/MCP parity.
