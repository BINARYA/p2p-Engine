# Compatibility Inventory - PROP-108 Baseline

## Purpose

This is the implementation baseline discovered before `PROP-108` acceptance.
It is not proof that cleanup is complete. Task T002 must expand every row to the
exact reader, writer, validator, facade, CLI, MCP, test, documentation and
package paths before deletion begins.

Disposition values:

- `remove`: obsolete behavior or representation must be deleted.
- `replace_current`: replace with the one current contract and tests.
- `regenerate`: recreate from the current template/catalog.
- `historical_review`: retain only if it is clearly historical and unreachable.
- `retain_current`: current semantics; the final inventory must record why it is
  unrelated to format compatibility.

## Agent And Public Surfaces

| ID | Surface | Observed gap | Primary locations | Disposition | Required proof |
| --- | --- | --- | --- | --- | --- |
| S001 | Generic instructions | Generated project `AGENTS.md` references removed workspace migration and project vertical propose/add commands | `services/agent_templates.py`, generated examples/projects | regenerate | Every current command resolves against Typer registry |
| S002 | Codex skills | Current project skills repeat removed commands and use superseded `legacy` template IDs/paths | `services/agent_templates.py`, `tests/test_agent_instructions_service.py` | replace_current | Fresh Codex install contains only current skill IDs and paths |
| S003 | Claude guidance | Guidance does not cover the complete remote registry and draft lifecycle | `services/agent_templates.py`, adapter tests | regenerate | Current remote/local vertical capability scenarios are present |
| S004 | Agent health | Hash equality reports an older shipped template as clean | `services/agent_instructions.py` | replace_current | Old generation plus matching hash reports `template_obsolete` |
| S005 | Agent policy | Policy still declares schema-v2 event-write and legacy-consent compatibility states | `services/agent_templates.py`, `.p2p/agent-policy.yml` renderer | remove | Fresh policy contains only current decision/write rules |
| S006 | CLI reference | Development inventory presents commands removed by 0.4.6 as current rows | `docs/development/cli-primitive-inventory.md`, `docs/CLI-GUIDE.md` | regenerate | Structured current CLI reference equals registered leaves |
| S007 | MCP reference | MCP documentation is broadly aligned but still documents legacy decision and artifact tools | `docs/MCP.md`, `mcp/catalog/*`, `mcp/registry.py` | remove | Current catalog/docs contain no discarded tools |
| S008 | CLI/MCP boundary | Top-level remote vertical and draft capabilities are omitted from generated guidance; CLI/MCP omissions are implicit | capability catalog to add, templates, MCP docs | replace_current | Every agent-relevant operation has exposure and reason |
| S009 | Release metadata | README, install guide, changelog and runtime recommendation disagree on release versions | `README.md`, `docs/INSTALL.md`, `CHANGELOG.md`, runtime resources/templates | replace_current | Source and wheel report one release/current-contract set |
| S010 | Examples | Checked-in example adapters can remain on an old generation indefinitely | `examples/*`, generated root adapters | regenerate | Example-generation/check test passes from source and wheel |

## Persisted Memory Families

| ID | Family | Current authority | Obsolete behavior found | Primary locations | Disposition |
| --- | --- | --- | --- | --- | --- |
| M001 | Workspace schema | workspace schema 3 declaration | migration models, plan/apply/recovery remnants and stale docs | `core/workspace_schema.py`, `services/workspace_schema.py`, `cli_commands/workspace_schema.py`, docs/tests | remove |
| M002 | Vertical pack | pack schema 2 and package format 1 | any surviving implicit/default or old-pack branch | `core/project_verticals.py`, `services/project_verticals.py`, portable package tests | remove |
| M003 | Runtime contract | explicit current `runtime.yml` contract | `legacy_undeclared`, adoption workflow and permissive write status | `core/runtime_contract.py`, `services/runtime_contract.py`, runtime CLI/tests/docs | remove |
| M004 | Proposal artifact state | explicit current artifact-state contract | `legacy_absent`, `absent_legacy`, mark-legacy command/tool and fallback reads | `core/proposal_artifact_state.py`, `services/proposal_artifact_state.py`, proposal CLI/MCP/tests | remove |
| M005 | Proposal decisions | current decision-event ledger | legacy projection adapter, `unknown_legacy`, resolution preview/apply and consent aliases | `services/proposal_decision_legacy.py`, decision core/services/CLI/MCP/tests | remove |
| M006 | Project questions | structured project/proposal question state | migration and owner binding from definition `open_questions` | `core/project_questions.py`, `services/project_questions.py`, question/workspace compatibility tests | remove |
| M007 | Permissions | explicit `permissions.yml` identity/role authority | governance-role fallback and conflict resolver | `services/permissions.py`, `services/governance_policy.py`, permission tests | remove |
| M008 | Decision-context relations | canonical `RelationType` values | compatibility aliases and normalization of non-canonical terms | `services/decision_context_topology.py`, source/extractor fixtures | remove |
| M009 | Decision context source catalog | current source/record policy | legacy source-catalog version and `legacy_unclassified` records | decision-context core/services/tests | remove |
| M010 | Registries | current verifiable bundle manifest | `legacy_unverifiable` states and manifest-less registry reads | `services/registries.py`, registry tests/docs | remove |
| M011 | Software specs | current software-spec lifecycle and provenance | `LEGACY_GENERATED`, `CURRENT_LEGACY` and ambiguous origin fallback | software-spec core/services/tests/docs | remove |
| M012 | Publications | current edition contract and paths | runtime `legacy_*` latest-path aliases and fallback reads | `core/project_publication.py`, publication services/tests | remove |
| M013 | Readiness | current typed gaps and structured evidence | `INFORMATIONAL_LEGACY` and narrative question authority fallback | readiness core/services/tests/docs | remove |
| M014 | Derived freshness | current source-bound freshness | `current_legacy_fallback` for software specs, visible export, brief and next actions | `services/derived_freshness.py`, context/workspace status consumers/tests | remove |
| M015 | Context packets | current artifact and derived-state read models | exported `legacy_state`/`legacy_reason` fallback fields | `services/context_packets.py`, related tests | remove |
| M016 | Vertical coverage | explicit schema-2 owner-confirmed mapping | `absent_legacy` status and schema-1/default authority | project-vertical core/services, proposal artifact service/tests | remove |
| M017 | Project overview/state | current vertical coverage and definition | legacy unmapped active-proposal projection | project-state/vertical-memory services and tests | remove or replace_current after semantic review |
| M018 | Spec export prompts | current export profiles | prompts offering legacy bundle compatibility flags | `services/spec_export.py` and export tests | remove |

## Public Entry Points Requiring Explicit Deletion Review

| ID | Entry point group | Examples observed | Disposition rule |
| --- | --- | --- | --- |
| E001 | Workspace migration CLI | `p2p workspace migrate ...` references/services | Remove registry, handler, services and docs; retain no stub |
| E002 | Runtime adoption CLI | runtime contract adoption for undeclared projects | Remove if its only input is missing/legacy contract state |
| E003 | Artifact legacy CLI/MCP | `proposal artifact mark-legacy`, `p2p_proposal_artifact_mark_legacy` | Remove command/tool/facade/state enum together |
| E004 | Decision legacy CLI/MCP | legacy-resolution preview/apply and legacy consent aliases | Remove command/tool/facade/diagnostics together |
| E005 | Proposal decision shortcuts | accept/reject/defer surfaces described as compatibility aliases | Classify as current convenience or remove; retention requires a current semantic rationale and spec update |
| E006 | Removed vertical commands in docs/templates | project vertical propose/add | Remove references; do not reintroduce aliases |
| E007 | Relation aliases | `extends`, `overlaps`, `related`, and other normalized terms | Persist canonical values only; update current producers before alias removal |

## Historical Evidence Review

These locations may legitimately describe old behavior but must not be consumed
as current contracts:

- completed feature specs and implementation notes;
- historical changelog entries;
- architecture reviews that explicitly discuss prior versions;
- archived canonical-project inventory;
- tests dedicated to ensuring an obsolete form is rejected without writes.

Current guides, generated templates, examples, CLI/MCP catalogs and package
resources are never exempt merely because they predate `PROP-108`.

## Completion Rule

The inventory is complete only when:

1. every search hit is classified by reachability and authority, not only by
   the presence of the word `legacy`;
2. every `remove` row has no registered or facade-reachable entry point;
3. every `retain_current` row records a non-compatibility rationale;
4. every current family has happy-path and obsolete zero-write rejection tests;
5. source-tree and wheel scans produce the same classifications.
