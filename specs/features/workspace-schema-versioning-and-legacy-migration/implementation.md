# Implementation Evidence - Workspace Schema Versioning And Legacy Migration

This document records implementation and repository-migration evidence for the
feature. It contains no owner approval by implication: owner-controlled inputs
and migration actions remain explicitly identified.

## Preparation

### Reused Boundaries

- `P2PWorkspace` remains the public service facade and common governed-write
  preflight.
- `RuntimeContractService` remains authoritative for engine/runtime
  compatibility; workspace schema compatibility is a separate dimension.
- `ProjectVerticalService` remains authoritative for vertical resolution,
  lock, definition and rubric formats.
- `PermissionsService`, `ProjectInitializationService` and project maturity
  helpers remain authoritative for permission, bootstrap and domain formats.
- `ProposalArtifactService`, `ConflictMemoryService` and
  `ProjectDecisionContextService` remain authoritative for proposal semantic
  artifacts, conflict memory and decision-context parsing.
- `RegistryService`, `ProjectStateService`, assessment, maturity and publication
  services remain authoritative for their derived outputs.
- `foundation.files` remains the shared atomic-write boundary and is extended
  with containing-directory durability reporting.

### Known Direct-Write Boundaries At Start

The baseline source scan found direct `Path.write_text` calls in initialization,
proposal artifacts, project state, maturity, permissions, conflict memory,
registries, next actions, specification exports and branch/work services.
Feature-owned multi-file mutations must use the durable transaction helper.
All existing governed facade mutations must also observe the migration lock,
even while their owner services retain their current internal writers.

### Initial Public Compatibility Matrix

| Surface | Baseline behavior before implementation |
| --- | --- |
| Runtime status/write gate | Declared by `.p2p/project/runtime.yml`; independent of workspace layout |
| Global validation | Fixed unconditional path list plus runtime/vertical validators |
| Vertical context/definition | Fallback vertical supported; lock and definition are separate reads |
| Permissions/domain | Fresh initialization materializes them; legacy workspaces may rely on fallback |
| Assessment/maturity | Existing single-purpose outputs; no independent evidence-coverage axis |
| Registry/project refresh | Separate commands and source fingerprints; accepted filtering is not shared |
| Doctor/project status/context/next | No workspace-schema, recovery or full freshness summary |
| Publication/spec exports | Existing staged workflows; no unified freshness graph |
| Package/runtime release | Source, package metadata and MCP report `0.1.9` |

### Baseline Verification

| Scope | Command | Result |
| --- | --- | --- |
| Collection | `.venv/bin/python -m pytest --collect-only -q` | 744 tests collected |
| Full baseline | `./scripts/test-full.sh` | 744 passed in 111.25s |

### Planned Focused Commands

| Slice | Command |
| --- | --- |
| F1-F3 | `.venv/bin/python -m pytest tests/test_workspace_schema_service.py tests/test_workspace_compatibility_service.py tests/test_workspace_migration_service.py tests/test_cli_workspace_migration.py` |
| F6 | `.venv/bin/python -m pytest tests/test_decision_context_sources.py tests/test_decision_context_service.py tests/test_proposal_artifact_service.py tests/test_conflict_memory_service.py` |
| F4-F5-F7 | `.venv/bin/python -m pytest tests/test_project_verticals.py tests/test_project_metadata_service.py tests/test_vertical_coverage_service.py` |
| F8 | `.venv/bin/python -m pytest tests/test_project_progress_service.py tests/test_project_assessment_service.py tests/test_project_maturity_service.py` |
| F9 | `.venv/bin/python -m pytest tests/test_derived_freshness_service.py tests/test_project_state_service.py tests/test_registry_record_builder_service.py` |
| Public contracts | `./scripts/test-public.sh` |
| Full validation | `./scripts/test-full.sh` |

### Preparation Review

The implementation introduces supported read, preview, apply and recovery
primitives. Repository dogfooding will use those primitives only. Vertical,
owner identity, metadata and semantic relation choices are never inferred by
the migration engine.

## Slice Evidence

### Preparation And Shared Contracts

- Public constants and typed result contracts live in `core/workspace_schema.py`,
  `core/mutation_preview.py`, `core/project_metadata.py`,
  `core/project_progress.py` and `core/derived_freshness.py`.
- Synthetic workspace factories live in
  `tests/workspace_migration_fixtures.py`; historical Markdown/YAML corpora
  continue to use `tests/decision_context_fixtures.py`.
- `tests/filesystem_assertions.py` provides a reusable exact tree snapshot for
  no-write assertions. The mutation-free gate was also run with
  `PYTHONDONTWRITEBYTECODE=1`.
- Runtime compatibility and workspace layout compatibility remain separate
  services and result dimensions. `layout_status=current` does not imply
  semantic alignment.

### F1-F3 - Schema, Planning And Transactions

- Fresh initialization writes schema contract/layout version `1`; undeclared,
  malformed, unsupported, ahead and incomplete fixtures remain distinguishable.
- The legacy-to-v1 registry is adjacent and forward-only. Inspect, plan and
  apply require P2P Engine `>=0.2.0,<0.3.0` and declared transaction
  capabilities.
- Planning captures normalized inventory bytes once, preserves unknown durable
  artifacts, separates semantic/physical hashes and writes no cache, lock,
  transaction or export.
- Apply requires resupplied owner inputs, actor, confirmation and reviewed plan
  fingerprint; it recomputes before and under its exclusive process lock.
- Candidate validation uses `CandidateWorkspaceView`; replacement is
  deterministic, schema/history is last, and every target preimage is checked.
- Failure coverage includes pre-staging, pre-candidate-validation, every replace
  position, post-replace crashes and the pre-lock-cleanup crash boundary.
  Resume/rollback preserve external edits and clean only transaction-owned
  state.
- Runtime contract plus managed `P2P-SETUP.md` now use the same rollback-safe
  multi-file writer with a narrow repository-target allowlist.

### F4-F7 - Semantic Alignment Primitives

- Vertical migration renders and validates active state, lock, definition and
  rubrics as one candidate set. Semantic rubric collisions require explicit
  mapping; unmatched criteria remain visible as `legacy_unmapped`.
- Project definition and bounded metadata expose stateless preview/apply with
  owner authority, resupplied patches and stale-token rejection. Protected
  project/runtime/remote/repository fields are retained byte-for-byte.
- Decision extraction prefers recognized Status and retains free-form Outcome
  as content. Collection-valued conflict targets are normalized and ambiguous
  relation aliases remain explicit diagnostics.
- Impact and conflict corrections have complete validation, atomic commit and
  rollback tests. Proposal vertical coverage distinguishes heuristic suggestion
  from imported declared authority and commits coverage plus artifact state
  together.
- `F7-T010` is intentionally satisfied by deferral: MCP coverage import was not
  added because schema v1 keeps new semantic writes on the owner-confirmed CLI
  boundary. MCP show/suggest parity is read-only.

### F8-F9 - Progress And Freshness

- Project progress exposes definition completeness and declared evidence as
  separate reproducible ratios. Heuristic suggestions are advisory and cannot
  increase declared evidence coverage.
- The freshness graph covers canonical sources, registries, owned project
  projections, decision context, assessment, maturity/progress, brief stages,
  next actions, specs, visible export and all publication stages.
- Projection ownership uses shared lifecycle policy, includes
  `accepted_with_changes`, removes only declared generated outputs and preserves
  unknown/manual directories.
- Context packets reuse one request snapshot for registry, proposal and decision
  summaries when deriving freshness; no duplicate broad scan is performed.
- Recovery, migration and deterministic freshness actions have explicit next
  priority. Status, doctor and compact context expose additive summaries.
- `F9-T010` remains an intentional optional deferral: status and ordered rebuild
  actions are complete, while automatic orchestration is withheld until a
  separate owner-confirmed execution contract is justified.

### Verification Results

| Scope | Command | Result |
| --- | --- | --- |
| Combined F1-F9 | Focused 26-module command from this implementation session | 276 passed in 49.98s |
| F3 failure/recovery | `.venv/bin/python -m pytest -q tests/test_workspace_migration_service.py` | 21 passed in 4.00s |
| Mutation-free | `PYTHONDONTWRITEBYTECODE=1 ... pytest` over plan, scale, MCP reads and freshness CLI | 4 passed in 1.73s |
| Public CLI/MCP | `./scripts/test-public.sh -q` | 244 passed, 578 deselected in 95.16s |
| Full repository | `./scripts/test-full.sh -q` | 829 passed in 151.84s |
| Static syntax | `.venv/bin/python -m compileall -q src tests` | passed |
| Patch hygiene | `git diff --check` | passed |

### Scale Evidence

The deterministic 100-proposal legacy fixture produced an applicable two-step
plan in 0.0481s on this development host. Source counters were:

```text
files_discovered=216
files_read=216
bytes_read=73625
yaml_parses=2
files_written=0
```

The count proves one inventory pass without per-proposal workspace rescans; the
test enforces a conservative 10-second ceiling rather than treating the local
timing as a portable performance promise.

### Public Surface And Release Gate

- CLI help was reviewed for workspace schema, plan/apply/recovery, progress,
  freshness, vertical coverage and semantic correction commands.
- MCP exposes schema status, migration plan, progress, freshness and coverage
  show/suggest only. Registry tests prove migration apply, resume and rollback
  tools are absent.
- `docs/WORKSPACE-MIGRATION.md`, `docs/CLI-GUIDE.md`, `docs/MCP.md`, README and
  generated agent instruction templates describe inspection, owner input,
  recovery and the prohibition on manual `.p2p` repair.
- Source, package metadata and MCP server report `0.2.0`. Existing exact-pinned
  workspaces must use runtime-contract preview/apply before migration; P2P does
  not change the installed environment automatically.
- The reusable engine gate authorizes preparation of M1, but does not provide
  owner inputs or approval for repository migration.

## Repository Migration Evidence

### M1 - Repository Baseline And Runtime Alignment

M1 started on branch `main`. The worktree was already dirty with the complete
F1-F9 implementation and feature documentation; no unrelated changes were
discarded. Before runtime alignment, the only governed-state write observed for
M1 was absent.

#### Compatibility Baseline

| Dimension | Baseline | After approved runtime alignment |
| --- | --- | --- |
| Runtime contract | `==0.1.9`, recommended `0.1.9`; active runtime `0.2.0`; `incompatible` | `>=0.2.0,<0.3.0`, recommended `0.2.0`; `compatible` |
| Workspace schema | `legacy_undeclared`, layout `legacy`, alignment `owner_input_required`, version `0`, target `1` | unchanged pending migration |
| Transition support | inspect/plan/apply available for `>=0.2.0,<0.3.0`; candidate overlay, durable transactions, exclusive lock, semantic hashes and stateless preview | unchanged |
| Validation | one runtime error plus schema info | zero errors, zero warnings, one expected legacy-schema info |
| Recovery | no recovery; migration lock absent | no recovery; migration lock absent |

The owner approved the runtime preview with token
`runtime-contract-update-v1:ece39f383e0c1f0fb3d2013c6076949ab885b51aa110633ac27f0a40c1501edc`.
The first apply performed no write because the common runtime preflight blocked
`runtime_contract_update` while the old contract was incompatible. This was a
circular engine defect: contract repair cannot be gated by the contract being
repaired. `P2PWorkspace.runtime_contract_update_apply` now retains migration
lock enforcement and delegates current/proposed-contract validation to
`RuntimeContractService`. A public-facade regression test starts from an
incompatible contract and proves repair. Runtime and migration focused tests:
51 passed. The unchanged approved preview was then applied successfully and
atomically changed `.p2p/project/runtime.yml` plus managed `P2P-SETUP.md`.

#### Project And Vertical Baseline

- Active vertical resolution uses the internal `base_project` fallback. No
  `.p2p/project/vertical.yml`, vertical lock or project definition exists.
- The intended candidate `software_project` is available at version `1.0.0`.
  It contains 19 required sections: 10 base sections and 9 software-specific
  sections from `system_objective` through
  `risks_alternatives_decisions`.
- Project profile is `default`; enabled modules are empty. Rubrics are the
  13-criterion software template and all criteria are enabled.
- `.p2p/project/domain.yml` and `.p2p/project/permissions.yml` are absent.
  Current reads therefore expose compatibility values: software domain from
  existing rubric/maturity evidence and owner/contributor permission defaults.
- Governance is materialized as `owner_decides`, with one role and no recorded
  precedents.
- Bootstrap metadata remains owner-reviewable and unchanged: status
  `bootstrap_manual`, workflow phase `bootstrap_manual`, current objective
  `implement_minimal_cli`. Repository, remote and runtime hashes are protected.

#### Canonical And Derived Baseline

- Proposal lifecycle: 100 total; 94 `accepted`, 1
  `accepted_with_changes`, 2 `draft`, 2 `superseded`, 1 `deferred`.
- Proposal artifact-state files: 16 active schema-v1 states and 84 explicit
  legacy-absent reads; 112 materialized records comprise 104 satisfied, 5
  missing, 2 weak and 1 not-applicable. The seven missing/weak records all
  belong to draft `PROP-098`.
- Full artifact catalog: 2,000 slots; 662 satisfied, 524 missing, 813 weak and
  1 not-applicable. Vertical coverage is absent for all 100 proposals.
- Decision context: `partial`; 1,353 sources, 2,813 evidence records, 2,171
  semantic records, 531 nodes and 581 relations. It has no fatal diagnostic and
  25 warnings: 2 authority/status divergences, 9 ambiguous relation types, 2
  invalid free-text targets and 12 unsupported relation types. Affected relation
  sources are `PROP-060`, `PROP-082`, `PROP-084`, `PROP-089`, `PROP-091`,
  `PROP-092`, `PROP-095` and `PROP-100`; authority warnings affect draft
  `PROP-063` and `PROP-098`.
- Registries are current: 100 proposals, 100 decisions, 68 changes, 2 choices,
  136 relations, 2,276 artifacts and 100 readiness records.
- Existing rationalized state reports 95 committed proposals, 82 features, an
  available operational brief and 5 next actions.
- Legacy assessment reports readiness 80/100 and maturity 100/100. Project
  progress correctly reports definition uninitialized and declared vertical
  evidence 0/10 rather than reusing that legacy maturity percentage.
- Freshness is `attention_required`: canonical sources, registries and decision
  context are current; 13 downstream nodes need refresh or owner action.
  Publication source, curator packet, curated document, validation and render
  are stale; owner publication review is missing and no publication approval is
  claimed.

At this baseline checkpoint, M1 still required explicit owner values and a
reviewed no-write plan; the following subsection records their resolution.

#### Owner Input And Applicable Plan

The owner selected `software_project`, profile `default`, no modules, no rubric
id remapping, persistent owner identity `mrjungle`, active/delivery project
metadata and the workspace-schema migration as the current objective. The
structured input remains temporary at
`/tmp/p2p-workspace-migration-input.yml`; it is not project memory.

The first JSON/text plan was correctly non-applicable because nine ambiguous
`PROP-100` relation terms required repository curation. The owner approved this
complete normalization without direction or rationale changes:

- `enables` to `references` for `PROP-017`;
- `informs` to `references` for `PROP-023`, `PROP-044`, `PROP-083`, `PROP-088`
  and `PROP-094`;
- `constrained_by` to `depends_on` for `PROP-025`, `PROP-055` and `PROP-089`.

The complete three-file impact package was validated and previewed as actor
`owner`, the legacy technical owner exposed while explicit permissions are
absent. Preview token:
`2fba9ec5c07b9f14789f28eea9dcd5ce60815c4f2a493e8be24d81d86bb27422`.
`impact-map.yml` retained physical hash
`9d75be2b1af5decca3e2b37759c7c2a462f36bb0b844fa4ab7472b039a3c58d0`
and `conflict-analysis.yml` retained
`0916d2bb4ed44618dbf8bdb477087bf2bf291400f1dc950c25300ac2f8d6652f`.
Only `related-proposals.yml` changed, from physical hash
`f64332ff60eb6b9d27c396f1bef152a1c758af479e0940b4e9b0ed1c16ea2ad4`
to `384c626ac16bc462570aaf87c34b7cbb22603cd4c055bcc1d5d18ffd20c8db42`.
The atomic apply required no recovery. A missing-permissions regression was
fixed so accepted-proposal corrections use exactly the same technical `owner`
fallback as `PermissionsService.show`; 46 focused artifact, compatibility and
migration tests passed.

After correction, decision relations increased from 581 to 590 and all nine
ambiguous diagnostics disappeared. Fourteen non-fatal historical diagnostics
remain for bounded M3 review: 12 unsupported relation terms and two invalid
free-text targets. The migration plan is now applicable and repeated no-write
invocations produce the same fingerprint:
`a4272623498d6b3597f2bb10e2613fd9cb2a48ef1b3e4a645472eeec0eda4bf4`.

| Canonical operation | Target | Before physical hash | Candidate semantic hash |
| --- | --- | --- | --- |
| create domain | `.p2p/project/domain.yml` | absent | `e318ad3ccc63d4672712bccc8bce82ea0053327ac039820c21a230d6c1c44f05` |
| create permissions | `.p2p/project/permissions.yml` | absent | `58980cd2d346a83f0d8b3db387175d47ace0bb719878b3dc33127f503a8fc29c` |
| update metadata | `.p2p/project.yml` | `c190b8c819c46401564dc40e69d28d1e636e0127bceb797126561e786b0b2c08` | `f535704f1d4c334718eb2fdacacaf11435a44b5438d39c8dbc373947399a6ea9` |
| create definition | `.p2p/project/definition.yml` | absent | `c4c6d278f1915fdb538573f94ba1cd586ad8b3efd12b767f3f9bb70374cd88c2` |
| update rubrics | `.p2p/project/rubrics.yml` | `88278a603498ccf80ae467f24a5033ab77e4806232376d9bf4ba0f5239f43a93` | `466eeb774073241da59f1d10dd0713360d4468f479b9358e49e18198372fe0f9` |
| create vertical lock | `.p2p/project/vertical.lock.yml` | absent | `1454b239a5b4b522fd4e95969df657a380addbdc2d192cbff8d24dea5f2c9c4d` |
| create vertical state | `.p2p/project/vertical.yml` | absent | `c5d8840f7d3c027f364fdac3b6c961398b324b094d4b67dcc50346b2fed9c75f` |
| create schema last | `.p2p/project/workspace-schema.yml` | absent | `b7b4249a0abeb63a8bb80e136b33f7e4608c949d6f96621d9a0414f71fe3da53` |

The plan preserves 162 legacy files without writing them: 23 under intake, 71
software-spec outputs, 26 spec-export outputs and 42 prompts. It records one
post-migration derived refresh action but does not execute it during apply.
Every canonical target has a validator and rollback to its captured preimage or
removal when newly created.

### M2 - Schema Apply And Definition Batches

#### Schema Transaction

The owner approved and applied fingerprint
`a4272623498d6b3597f2bb10e2613fd9cb2a48ef1b3e4a645472eeec0eda4bf4`
as actor `mrjungle`. Transaction `migration-7097de622e0e6ea4` committed the
eight reviewed canonical targets, restored none and required no recovery.
Post-apply checks show schema version 1 with `layout_status=current` and
`alignment_status=aligned`, a valid `software_project` lock, explicit software
domain, owner identity `mrjungle`, active/delivery metadata, 19 truthful missing
definition sections and no validation findings. The migration lock and scratch
transaction state are absent.

#### Definition Batch 1 - Vision And Objective

- Source patch: `/tmp/p2p-definition-batch-1.yml`; actor `mrjungle`; source
  evidence `README.md`.
- Source definition physical hash:
  `f55d9f177e29e19ee4b58a88021833296fa7832e26825d71090c1372a127c750`.
- Semantic transition:
  `eae2408f1c6269b95f18e1221ee328a8979036ad543ac25e4dc7b04662ddc161`
  to `22e4e378ab475ce980ba5340a3e9c16ddef85d303db479ffa03e3dfa650959d1`.
- Owner-approved preview token:
  `b76f27a17dfd1db99d9ad37fce0dc64093afd1489837c6d3b2ffc66f682697ab`.
- Apply status `applied`; final physical hash
  `215f51ec64362890f007023be39533afa90241348a095983d203685588ea899b`;
  no recovery required.
- `vision`, `objective` and `system_objective` are complete with all required
  fields and their corresponding open questions closed. Definition progress is
  7/43 (16.28%); declared proposal coverage remains independently 0/19.
- `project definition show`, context, progress and global validation passed
  after apply with zero errors or warnings.

Definition batch 2 preview targeted only
`stakeholders`, `users_and_actors` and `workflows_use_cases`; candidate semantic
hash `5a836bdea81b772e66c60a71b68e39d47737083de8a8e65212fed91d318b0b1f`,
source physical hash
`215f51ec64362890f007023be39533afa90241348a095983d203685588ea899b` and
preview token
`929613bb68b440d3ef5b35bf37b6bc57fbc5321ffed643f92d3141b5c2266ff7`.

#### Definition Batch 2 - Stakeholders Users And Workflows

- The owner approved the previously recorded preview without source changes.
  Apply status `applied`; final physical hash
  `be204a0f3aee9bd6f243633c07d92b6d9bac1faf9b178572e2a88f1d4a49ca63`;
  no recovery required.
- `stakeholders`, `users_and_actors` and `workflows_use_cases` are complete.
  Evidence comes from `README.md` and explicit project permissions.
- Definition progress is 13/43 (30.23%) with six complete sections; declared
  evidence remains 0/19. Definition show, context, progress and validation pass.

Definition batch 3 is previewed but not yet applied. It targets only `scope`
and `mvp_scope`, with source evidence from README and CLI/MCP documentation.
Source physical hash:
`be204a0f3aee9bd6f243633c07d92b6d9bac1faf9b178572e2a88f1d4a49ca63`;
semantic transition
`5a836bdea81b772e66c60a71b68e39d47737083de8a8e65212fed91d318b0b1f`
to `51549cc7d24ce7c41c17cf639f0a56c7e605c839f2857b72811874b08d6876db`;
preview token
`de472fa71c84f96ea1c910e63c2d558d50da33157f417f0c85314f769cb3f5c8`.

#### Definition Batch 3 - Scope And MVP Boundaries

- The owner approved the recorded preview without source drift. Apply status
  `applied`; final physical hash
  `7c143ac2f16cc72cfabd97699dcc8ce8eff7fce7826c7373fd4f82c2a0cde23c`;
  no recovery required.
- `scope` and `mvp_scope` are complete, including explicit current non-goals.
  Definition progress is 18/43 (41.86%) with eight complete sections; declared
  coverage remains 0/19. All four post-batch checks passed.

#### Definition Batch 4 - Data Model And Integrations

- The patch targeted only `data_model` and `integrations_dependencies`, using
  current source contracts, README, package metadata and installation/MCP
  documentation. Source physical hash:
  `7c143ac2f16cc72cfabd97699dcc8ce8eff7fce7826c7373fd4f82c2a0cde23c`.
- Semantic transition:
  `51549cc7d24ce7c41c17cf639f0a56c7e605c839f2857b72811874b08d6876db`
  to `71286490a1246c57944ba481f7f6e9305baf870ae965833f96bb94e6bb36afa4`;
  owner-approved preview token
  `d3c7beabcc4d2f4a027cf5715b9caf8ff8a5b912b41e2c0a80895be3828bf8b7`.
- The owner approved the recorded preview without source drift. Apply status
  `applied`; final physical hash
  `4d26b70e00b1a8429c8b92df468eb6fcfe1ea4065373840e9f350d4394386f5d`;
  no recovery required.
- `data_model` and `integrations_dependencies` are complete. Definition
  progress is 22/43 (51.16%) with ten complete sections; 12 required fields
  remain missing and declared proposal coverage remains 0/19. Definition show,
  context, progress and validation passed with no definition issue or global
  validation finding.

#### Definition Batch 5 - Constraints And Validation

- The patch targeted only `constraints_nfrs` and `acceptance_validation`; the
  validation question was closed only by the reviewed acceptance and test
  strategy. Source physical hash:
  `4d26b70e00b1a8429c8b92df468eb6fcfe1ea4065373840e9f350d4394386f5d`.
- Semantic transition:
  `71286490a1246c57944ba481f7f6e9305baf870ae965833f96bb94e6bb36afa4`
  to `fa0a9201410a5f0f21a4b98833392f7da3b7bb73c2202d18a406672783c7c9e5`;
  owner-approved preview token
  `74ee5c6ccc6cc9be635ecd73e4a265989d82246fcdebe85632abeece5da80945`.
- The source hash was identical before and after preview. Apply status
  `applied`; final physical hash
  `a1a6d32a1fe598bb58fd6487836b190ae71d444460f762bf3b056d0997605516`;
  no recovery required.
- Both sections are complete. Definition progress is 28/43 (65.12%) with 12
  complete sections; eight required fields remain missing and declared proposal
  coverage remains 0/19. Definition show, context, progress and validation pass;
  the only open questions now concern expected artifacts and remaining owner
  decisions. Migration lock and recovery state are absent.

#### Definition Batch 6 - Risks Decisions And Delivery State

- The patch targeted the seven remaining definition sections and deliberately
  used mixed statuses: `assumptions=assumed`, `decisions=partial`,
  `risks_alternatives_decisions=partial`, with complete risk register,
  milestones, definition-of-done and expected-artifact descriptions. Source
  physical hash:
  `a1a6d32a1fe598bb58fd6487836b190ae71d444460f762bf3b056d0997605516`.
- Semantic transition:
  `fa0a9201410a5f0f21a4b98833392f7da3b7bb73c2202d18a406672783c7c9e5`
  to `dd0464eb6f29d0cbf1934e0185dbd9828cbfa82e8d1226d4c4d25c8710f7d543`;
  owner-approved preview token
  `805c630a45cecf734c06de19c876e7703904c4ed03dc27198bdf8aecc4a452cd`.
- A deliberate apply attempt with the previous batch token returned
  `stale_preview`, changed no path and preserved source physical hash
  `a1a6d32a1fe598bb58fd6487836b190ae71d444460f762bf3b056d0997605516`.
  The matching token then applied atomically with final physical hash
  `eb6fcc08f0a52693228072c7d369809a8043ee432baffa8cfc9802758f98fb78`;
  no recovery required.
- Final M2 definition state is valid with zero missing required fields: 16
  sections are `complete`, one is `assumed` and two are `partial`. Progress is
  40/43 (93.02%), not a false 100%; three assumptions retain their explicit
  statuses and two owner questions remain visible. The stale vision suggestion
  now points to relation curation question `Q001`.
- Definition show, context, progress, readiness review and global validation
  pass. Workspace schema remains current/aligned and no migration lock or
  recovery exists. Readiness review reports all 19 capisaldi without proposal
  evidence because declared vertical coverage remains 0/19; this is the
  independent M4 evidence axis, not missing definition content.

#### M2 Exit

All six owner-reviewed definition batches have matching source, semantic,
preview and physical-result evidence. M2 leaves no unsupported field marked
complete and carries relation, coverage and publication decisions forward as
explicit owner work.

### M3 - Historical Relation Alignment

#### PROP-095 Decision And Preview

The decision-context rebuild after M2 remains `partial` with 1,353 sources,
2,822 evidence records, 2,171 semantic records, 531 nodes and 590 relations.
Its 16 warnings are two intentional draft/pending authority divergences, two
invalid free-text targets in `PROP-095`, and 12 unsupported historical relation
terms across six other proposals.

The owner confirmed that `future setup-guide adoption workflow` and
`future runtime installation workflow` are capability boundaries, not proposal
identities. They are therefore removed only from `related-proposals.yml`; their
scope remains in `impact-map.yml` features, dependencies and overlaps, and no
placeholder proposal or duplicate `PROP-084` relation is introduced.

The complete temporary impact package is
`/tmp/p2p-prop-095-impact-correction-v1`. Preview actor is `mrjungle`; source
physical hashes are:

- `impact-map.yml`:
  `dfbdde56a9af538c4c6bbe25df1f678be9fd20644e750da6dd7f58574131292d`;
- `related-proposals.yml`:
  `d2701bdced14c7ca285612fed5473ccd726c48ac04e9147c52d1c351cca457b1`;
- `conflict-analysis.yml`:
  `8bbd5b3eb87018b0ad3d253e32705ab0e34f5938e32860f9cd1fe3c70e7b2c91`.

Impact-map and conflict semantic hashes are unchanged. Related-proposals changes
from semantic hash
`128dd88a052e4ababa41eaa8d1bc5f3cec2a20adfa6c6e74985ec7f6d2cb7e2c`
to `ac8e540b45121071e9a22f72f4d5a973fdd8aae1ff96c138889d373a9a1dd772`.
Preview token:
`59a788257467258e5f6eda203941c1b55b3e2b2ae5c9a92fd9a262685c9f91af`.
All three canonical hashes were unchanged after preview.

Before repository apply, focused tests proved that an invalid impact set and a
canonical source changed after preview both leave every target untouched:

```text
.venv/bin/python -m pytest -q \
  tests/test_proposal_artifact_service.py::test_impact_validation_rejects_invalid_set_before_any_target_write \
  tests/test_proposal_artifact_service.py::test_impact_apply_rejects_changed_canonical_source_without_overwriting_it
2 passed in 0.21s
```

The owner approved the exact preview. Apply status is `applied` with no recovery
and final physical hashes:

- `impact-map.yml` unchanged at
  `dfbdde56a9af538c4c6bbe25df1f678be9fd20644e750da6dd7f58574131292d`;
- `related-proposals.yml` changed to
  `7a04b40fcbca56d112d8e24a953dfe2123fdf08d62d7b1ac0a8cb3d6e6fee549`;
- `conflict-analysis.yml` unchanged at
  `8bbd5b3eb87018b0ad3d253e32705ab0e34f5938e32860f9cd1fe3c70e7b2c91`.

The immediate rebuild removed both `DC-RELATION-INVALID-TARGET` warnings and
introduced no diagnostic. Evidence count changed from 2,822 to 2,820 because
the two invalid assertions were removed; records, nodes and valid relations
remain 2,171, 531 and 590. The 14 residual warnings are 12 unsupported relation
terms and two intentional draft/pending authority divergences. Global
validation remains clean.

#### PROP-060 Preview

The owner approved the remaining 12-term normalization matrix. The first
deterministic package, `/tmp/p2p-prop-060-impact-correction-v1`, changes only
`supports` and `distinguishes` to canonical `references`; both reasons remain
unchanged. Actor `mrjungle`, preview token:
`f12732c34c19516923217ca7ae3612baf723c068da58a6adcc27e2882ec7c826`.

Source physical hashes are `357c138f...77f50f` for impact-map,
`cbb384ec...3e8e67` for related-proposals and `d8b4cb1b...3f5ef` for conflict
analysis. Impact and conflict semantic hashes are unchanged;
related-proposals changes from
`d42ac2a2d1a6ce13186db7f05d9f6aec92e7d6012f9f316961586631ae558c04`
to `0b45c346e38f6ef5387eda50e1c54767f983440a2d86b67dd939db9a7e812f2a`.
Preview performed no canonical write.

The owner approved the exact `PROP-060` preview. Apply status is `applied`, no
recovery; related-proposals final physical hash is
`c1a5519981d5c361c1e4c10732b266b9e11e17bb555642afb94f0b13d0a4d9c7`
while the other two physical hashes remain unchanged. The immediate rebuild
reduced unsupported relation diagnostics from 12 to 10, increased valid
relations from 590 to 592 and evidence from 2,820 to 2,822, with no authority
or validation regression.

#### PROP-082 Preview

Package `/tmp/p2p-prop-082-impact-correction-v1` changes only `informed_by` to
canonical `derived_from`, retaining the reason. Actor `mrjungle`, preview token:
`0a2a9cfbb102dcb7786aa0435f5b2334dd5e9bc57f4d19eb1fedf6011d8e1803`.
Impact and conflict semantic hashes are unchanged; related-proposals changes
from `3da20862ad221a7b5cd795224eb42fe3446433a84106bc53b29d13209910546c`
to `be6e12a76486fc61988de0a68786db797b1a148ad8b97631e5719eadd52dd6f1`.
All source physical hashes remained unchanged after preview.

The owner approved `PROP-082`; apply is `applied` with no recovery and final
related-proposals physical hash
`64e6e579cd404ebb6de9fca9aa741a466a516c1a3feab9ae318d64e7590c9409`.
The immediate rebuild reduced unsupported diagnostics from 10 to 9, increased
valid relations from 592 to 593 and evidence from 2,822 to 2,823; validation
remains clean.

#### PROP-084 Preview

Package `/tmp/p2p-prop-084-impact-correction-v1` changes the two `adjacent`
relations to canonical `references`; existing dependencies and all reasons are
unchanged. Actor `mrjungle`, preview token:
`ef51ed0a57bcba6b7d5ac3e9691cbf3cd569ffb0178b3cfe32f0739e767e8d78`.
Impact and conflict semantic hashes are unchanged; related-proposals changes
from `dc1c3b0bc88e7a0d610f67cb003d062a3371cb040723463dae01d97b82de0152`
to `e5596a69348c1d241a8a9e50b2688210352c784635249104ec30bc1c44ac8242`.
All source physical hashes remained unchanged after preview.

The owner approved `PROP-084`; apply is `applied` with no recovery and final
related-proposals physical hash
`fbc17abe5e998f723be2f7e044dcefb6625009750ea7b2a78b02f124b64defdb`.
The immediate rebuild reduced unsupported diagnostics from 9 to 7, increased
valid relations from 593 to 595 and evidence from 2,823 to 2,825; validation
remains clean.

#### PROP-089 Preview

Package `/tmp/p2p-prop-089-impact-correction-v1` changes only `triggered_by` to
canonical `derived_from`; reason, impact boundary and every other relation are
unchanged. Actor `mrjungle`, preview token:
`0a6c93d46a7233c7b10453945c32ab93e409aeae5ec78a1acd123da33df9c761`.
Impact and conflict semantic hashes are unchanged; related-proposals changes
from `0f6e254c32adc743f75608bb22e9c7aea4d64c37977dfbe3a7f6d470280edb42`
to `711ac324fa275ca3344685406d266b39b01a00b22e9db501cd5870693187817b`.
All source physical hashes remained unchanged after preview.

The owner approved `PROP-089`; apply is `applied` with no recovery and final
related-proposals physical hash
`8ce1b0a686800a5f82f6c42df7c8006cb1674b80a9102e106b968acca40f6aa2`.
The immediate rebuild reduced unsupported diagnostics from 7 to 6, increased
valid relations from 595 to 596 and evidence from 2,825 to 2,826; validation
remains clean.

#### PROP-091 Preview

Package `/tmp/p2p-prop-091-impact-correction-v1` changes
`supersedes_remaining_scope` to `supersedes`, and `compatible_pattern` plus
`adjacent` to `references`; all reasons are unchanged. Actor `mrjungle`, preview
token: `7ada2ebab040c7980cd2e4884c2fef4c4537ebc360a915b3adfd4b8738cda32c`.
Impact and conflict semantic hashes are unchanged; related-proposals changes
from `407aa4a5f7e002dc739a87ec662c9bd8ee3a539414ecc09f9d1c1f48b1b4fb92`
to `63c07614b8197e355dfa8994cb338602aa617cbc1b3ef5b32bbcccc357ea3366`.
All source physical hashes remained unchanged after preview.

The owner approved `PROP-091`; apply is `applied` with no recovery and final
related-proposals physical hash
`c04fa20982607864a538acd114ea8a964225c43d877b4b7dd1338d906f5fdef3`.
The immediate rebuild reduced unsupported diagnostics from 6 to 3, increased
valid relations from 596 to 599 and evidence from 2,826 to 2,829; validation
remains clean.

#### PROP-092 Preview

Package `/tmp/p2p-prop-092-impact-correction-v1` changes
`implements_boundary` to `depends_on`, `aligns_with` toward `PROP-081` to
`references`, and `aligns_with` toward `PROP-091` to `depends_on`. All reasons
are unchanged. Actor `mrjungle`, preview token:
`f7e4a1f7896a099db817f55bab8b4bfc8f097af98a786eff0d5fe91b24424c33`.
Impact and conflict semantic hashes are unchanged; related-proposals changes
from `77287ce38f6b81555a7df4c4373b6e2e729122c50e5b51e171e31489ad24f2c8`
to `355a4c77bfa1d9eaed8daa7fd54a09bae3413fc6acbdd29e7bf81a6d44f595e6`.
The physical diff also removes one terminal blank line; no additional semantic
field changes. All canonical source hashes remained unchanged after preview.

The owner approved `PROP-092`; apply is `applied` with no recovery and final
related-proposals physical hash
`ff77ee8754859c70b76bc94e1af366fc282fd36bc11acf04893e86abbf4374ca`.
The final M3 relation rebuild has 1,353 sources, 2,832 evidence records, 2,171
semantic records, 531 nodes and 602 valid relations. Invalid, ambiguous and
unsupported relation diagnostics are all zero. The only two source diagnostics
are intentional `DC-AUTHORITY-STATUS-DIVERGENCE` warnings for draft `PROP-063`
and `PROP-098`, whose decision outcome remains `pending`; no source repair is
warranted while those proposals remain drafts.

Representative medium-budget retrieval for `PROP-095` and `PROP-092` retained
active accepted-decision authority for their leading neighborhoods. Their only
packet advisories are deterministic budget truncation and index partiality from
the two draft/pending sources. Global validation is clean and migration
recovery remains absent. No project conflict-memory correction was necessary.

The M3 definition-convergence patch updates only `decisions`, `milestones` and
`risks_alternatives_decisions`, closes owner question `Q001`, retains truthful
partial statuses and advances the next action to coverage question `Q002`.
Source physical hash:
`eb6fcc08f0a52693228072c7d369809a8043ee432baffa8cfc9802758f98fb78`;
semantic transition
`dd0464eb6f29d0cbf1934e0185dbd9828cbfa82e8d1226d4c4d25c8710f7d543`
to `cc4ecb33d134147a090e59aad8b493afe16b2ba663bc222d70d19f8c4bc6ddc4`;
preview token
`2d241b40b718e4b705c897cfa6ea40f848bcb9c0b27be240a148eb547e33fe65`.
The owner approved the exact preview and apply completed atomically. Final
definition physical hash is
`cbb2230dead3dd006e68182982b00bbd96d4432e0f6306aaef57987891c7f53b`.
Definition progress remains truthfully 40/43 (93.02%); `Q002` is the only open
question, global validation has zero findings and no migration recovery is
active.

#### M3 Exit

All approved relation corrections and the separate definition convergence are
applied. Invalid, ambiguous and unsupported relation diagnostics are zero. The
decision index remains partial only for the two documented draft/pending
authority divergences in `PROP-063` and `PROP-098`; these are intentional source
states rather than parser or migration defects. Every correction used a complete
artifact set and no apply produced a partial write.

### M4 - Selective Vertical Coverage

#### Selection Policy And First Batch

M4 deliberately selects a bounded 12-proposal batch rather than mapping all 100
historical proposals. Selection requires at least one of four responsibilities:
foundational project identity, active Change Set relevance, vertical/runtime or
governance contracts, and recent decision-memory architecture. The exact batch
is:

| Responsibility | Proposals | Inclusion basis |
| --- | --- | --- |
| Foundational product surfaces | `PROP-001`, `PROP-006`, `PROP-044`, `PROP-055` | CLI foundation, agent integration, MCP access and bounded context discipline |
| Runtime and project-definition contracts | `PROP-084`, `PROP-085`, `PROP-090`, `PROP-091`, `PROP-094`, `PROP-095` | Runtime compatibility, verticals, definition state, governance, software specifications and runtime updates |
| Current accepted delivery | `PROP-099` | Accepted source of active `CHANGE-068`; all associated Work is terminal but the publication lifecycle remains current project direction |
| Recent decision-memory architecture | `PROP-100` | Accepted source for the derived decision-context and proposal-neighborhood architecture |

The other 88 proposals remain legacy/unmapped unless a later reviewed batch is
justified. No empty coverage artifact will be created for them.

#### Suggestion Review

Read-only JSON suggestions were run for all 12 proposals. The operation changed
no coverage or artifact-state path. Manual review rejected confidence as a
sufficient authority signal: ubiquitous terms such as `accepted`, `decision`,
`status`, `artifact`, `first` and `owner` caused broad matches across base and
software sections. Candidate mappings are retained only where proposal scope
materially defines the section, with proposal/decision artifacts recorded as
evidence; generic acceptance boilerplate and inherited vertical terminology are
not enough.

Dogfooding also exposed a transport defect: the vertical-coverage CLI serialized
JSON through Rich, which could insert line breaks inside long path strings.
`proposal_vertical_coverage._print` now uses the shared plain structured emitter.
`test_vertical_coverage_cli_json_suggestion_preserves_long_paths` covers a long
proposal slug; the complete focused module passes with `6 passed`. Suggestions
for the complete first batch then parsed successfully as JSON. This correction
changes no canonical project artifact.

At the suggestion checkpoint the curated replacement payloads and their exact
section rationales remained pending owner review. No declared vertical coverage
had yet been imported, so project evidence coverage was 0/19 and `Q002` remained
open.

#### Initial Import Batch A

The owner approved three conservative complete payloads prepared under
`/tmp/p2p-m4-coverage-batch-a`. They are disposable review input, not project
memory. All previews resolved actor `mrjungle` as `owner_confirmed`, found both
targets absent, required confirmation and reported no blocker.

| Proposal | Approved direct sections | Preview token | Final coverage hash | Final artifact-state hash |
| --- | --- | --- | --- | --- |
| `PROP-001` | `system_objective`, `mvp_scope`, `workflows_use_cases` | `27e4783879d6715dac1d0fd375ec51e5af6760229261f4cd9cfcf24c6f178f32` | `d9d25892e654d47a4730437cf4e6171205818d575fba566b0ccd5b50dff9322a` | `901be694b2123152ec72c8b588eba3f7d866a5d2a5fa9a2a1a856e4c70f1971e` |
| `PROP-006` | `users_and_actors`, `data_model`, `integrations_dependencies`, `workflows_use_cases`, `constraints_nfrs` | `653d5271789baba171dec82fec668f672678a4ba87bf9e2962b51dcb2082ed56` | `0b032c137e6aad162fef3ecd97621628a027a6bd9113a781df4d21b6d09e603a` | `e3c8ed630453ce877296fd00f43186028354a1e0d47e758a17fe36b6dde30b95` |
| `PROP-044` | `mvp_scope`, `workflows_use_cases`, `integrations_dependencies` | `97c7cae2c5113a6a877ef246e0b52ec69f919f8708a6a93d07640aadcad1b238` | `c299b40b62b7049e9196c0235ee6ef59187a9d7af7b0d89fdf08603c16d4f5fe` | `14043db615f9c757cf998e7635d864422d01c93cedcc1678e7f4fcec04fc4d5f` |

Each import returned `applied`, changed exactly coverage plus artifact-state,
restored no path and required no recovery. Coverage status is valid schema v2
with per-section rationale and source evidence. Artifact state records
`vertical_coverage` as `satisfied`, actor `mrjungle`, source
`vertical_coverage_import` and confirmation `owner_confirmed`; materializing the
previously absent state also truthfully classifies each proposal's other legacy
artifact gaps without claiming they were repaired.

Project definition remains 40/43 (93.02%). Declared evidence advanced from
0/19 to 7/19 (36.84%) for exactly `system_objective`, `users_and_actors`,
`mvp_scope`, `workflows_use_cases`, `data_model`,
`integrations_dependencies` and `constraints_nfrs`. The heuristic exclusion
count decreased from 525 to 501 because suggestions are no longer computed for
the three proposals with declared coverage; heuristics did not increase the
declared numerator.

The first real retrieval exposed a cross-feature authority loss: coverage and
artifact-state both retained `owner_confirmed`, but the decision-context source
resolver labeled canonical vertical evidence as `system_state` because it only
consulted artifact confirmation for `governed_evidence` sources. The resolver
now treats tracked vertical coverage as a canonical semantic source whose
authority may be refined by its atomically committed artifact-state. The
authority policy version advanced from `decision-context-authority-v1` to
`decision-context-authority-v2`, forcing old manifests and packets stale rather
than reusing an unchanged semantic fingerprint.

Focused source, topology, retrieval, freshness and coverage tests pass with 85
tests. Real medium-budget packets for all three proposals now expose vertical
evidence as `canonical`, `owner_confirmed_evidence`, `active`, and retrieve
shared-section neighborhoods where retained by budget. Semantic packet
fingerprint is
`1b3744d1f27968938bec1fb0d582d019bf7abab94936301d79fa2cba6fd5da78`.
The index remains partial only for the two intentional draft/pending authority
divergences; budget truncation remains advisory. Global validation has zero
findings and workspace migration recovery is absent. The M4 continuation gate
is clean; `Q002` remains open until the complete reviewed batch is finished.

#### Import Batch B

The second owner-approved batch used complete payloads under
`/tmp/p2p-m4-coverage-batch-b`:

| Proposal | Approved direct sections | Preview token | Final coverage hash | Final artifact-state hash |
| --- | --- | --- | --- | --- |
| `PROP-055` | `mvp_scope`, `workflows_use_cases`, `constraints_nfrs` | `100613db50cceffe16cded0810ba57a5f5f8abfc649cf6941cccf7fccc3b545f` | `1998f15d805720f90ace442536b9933cb35ff3baf8e8132e432bc51877e6a381` | `da248593a8c4e0fe447f33d6466b95da2f13b508c601ea095607ece96b0ca58d` |
| `PROP-084` | `mvp_scope`, `workflows_use_cases`, `data_model`, `integrations_dependencies`, `constraints_nfrs` | `74fe3e7af78ed7fd43f4ee2912362d8c45086fb9b3d859a8ca0ba3d60c6bcf06` | `851efa2f57de6c4a143e901002dad1d43d510c181a831ca8072bd5f531934369` | `7e79386cfefb6070f11a54e2bf050ca1947a82503e9144ae8f15b461f4cac4fd` |
| `PROP-085` | `system_objective`, `mvp_scope`, `data_model`, `workflows_use_cases`, `definition_of_done`, `artifacts` | `52e38d8e3f965681a37d5d6fe1ba3a6b1f4f3d0fed28667fc7527a4af6c2a3e0` | `937d492ed170b14afe47c0cd3549d8c4d36abb820051b9b438d931c2aa59a361` | `7e3a62ed9dc5bacfb6c40824f5ef45e2e448e465c6532759f6fd5d4ba3d58ab4` |

The initial `PROP-084` preview correctly stopped because its active
artifact-state predated F7 and lacked the new `vertical_coverage` record. A
separate `p2p proposal artifact init` would have introduced an avoidable
preliminary canonical mutation and broken the intended atomic import boundary.
`render_satisfied_artifact_candidate` now appends only a missing known artifact
definition to the in-memory candidate before satisfying it. Unknown artifact ids
still fail, existing records remain untouched and coverage plus provenance still
commit together. The regression exercises preview, apply and exact preservation
of an existing proposal record; proposal artifact-state plus coverage tests pass
with 14 tests.

The refreshed `PROP-084` preview bound existing artifact-state preimage
`8dc130ffe4f430fd46f80e0c7ae7912228cf2a59cdb5d8391b4dc1f438471908`.
Its committed diff changes only the container `updated_at` and appends the
owner-confirmed vertical record; all seven historical records remain unchanged.
All three applies changed exactly two targets, restored none and require no
recovery.

Declared evidence advanced from 7/19 to 9/19 (47.37%) by adding
`definition_of_done` and `artifacts`. Definition remains 40/43 (93.02%). The
heuristic exclusion count decreased from 501 to 471 solely because the three
newly declared proposals no longer contribute suggestions. `PROP-084` is
correctly included in committed evidence under the shared lifecycle policy for
`accepted_with_changes`.

Real retrieval exposes the new sources as canonical, active,
`owner_confirmed_evidence`; after this batch its semantic packet fingerprint is
`7fb61911fa2c3d1350c451769b27bcdcb490463c4b7256cb7517f6ec5263226b`.
Only budget truncation and the two documented draft/pending divergences remain
advisory. Global validation has no finding and migration recovery is absent, so
the bounded continuation gate remains clean.

#### Import Batch C

The third owner-approved batch used complete payloads under
`/tmp/p2p-m4-coverage-batch-c`:

| Proposal | Approved direct sections | Preview token | Final coverage hash | Final artifact-state hash |
| --- | --- | --- | --- | --- |
| `PROP-090` | `workflows_use_cases`, `data_model`, `integrations_dependencies`, `constraints_nfrs`, `definition_of_done`, `acceptance_validation`, `risks_alternatives_decisions` | `ee85a37c6ba82506c82fe29a0fe9297e1949723137be76b8729c471ebef721b3` | `4abfb7dfcda1fe69f0d8947d446a6d32a36ebf1cdabd22e31b169456cb73d062` | `9eac980cbb9452ba26dbe66797a184b735285013212a29b1cec34ea3726dd74f` |
| `PROP-091` | `users_and_actors`, `workflows_use_cases`, `data_model`, `constraints_nfrs`, `decisions`, `risks_alternatives_decisions` | `6d28f80a0961bdeec4c3d35a959999c79c5d3e7888209142d5da084407fc2362` | `1a746f22b869d29cf95d66623d8d4040e10f8c7a0812470b2929a40c955955a0` | `1dda1eb6fb05d48e137a75df8f2896193e6cf132b2f7dc419d4ff9243ee69bf6` |
| `PROP-094` | `system_objective`, `mvp_scope`, `workflows_use_cases`, `data_model`, `integrations_dependencies`, `artifacts`, `acceptance_validation`, `risks_alternatives_decisions` | `dd871a86d735073af46a6cc70f846148db5757cd61861dd64852b17b1e6a8390` | `5cbeb1b581eecd59c9445ef3e6b46042a4a2801df71947bfe35aa6fe047d4992` | `06866f983f2550875c9e62b8b8c7ed3456260ee6990774a6545b57c29dfb87f5` |

All previews bound existing artifact-state preimages and all applies committed
exactly coverage plus artifact-state with no restore or recovery. Git numstat is
`21` additions and `1` replacement for each state file, matching one appended
record plus the container timestamp; no historical record changed.

Declared evidence advanced from 9/19 to 12/19 (63.16%) by adding the previously
uncovered `decisions`, `acceptance_validation` and
`risks_alternatives_decisions` sections. Definition remains 40/43 (93.02%),
heuristic exclusions decreased from 471 to 428, warnings remain empty and Q002
remains open pending the last reviewed group.

The representative `PROP-091` packet uses shared declared sections with
`PROP-094` as an explainable ranking contribution. All retained vertical
evidence is canonical, active and owner-confirmed. Semantic packet fingerprint
after this batch is
`b9ccb4a67bcf47083751807516cedefe27df39dd961a294697c9aee2912e261f`;
only expected budget truncation and the two intentional draft/pending source
diagnostics remain. Validation and migration recovery stay clean.

#### Import Batch D And Coverage Result

The final owner-approved group used complete payloads under
`/tmp/p2p-m4-coverage-batch-d`:

| Proposal | Approved direct sections | Preview token | Final coverage hash | Final artifact-state hash |
| --- | --- | --- | --- | --- |
| `PROP-095` | `workflows_use_cases`, `data_model`, `integrations_dependencies`, `constraints_nfrs`, `acceptance_validation`, `risks_alternatives_decisions` | `3c2f1bead927b6fe21a70037d73b9e5841e0d58ee9a3fe45c72912dd52560848` | `f2815385b5263a366db73725875234a5a447bd6bd752253f9f29382f8ed6f3fa` | `2b04744a65b8b36a3adc6c0a72ffe0ddb8265b02642159d90301dad6b4ee6f95` |
| `PROP-099` | `mvp_scope`, `workflows_use_cases`, `data_model`, `artifacts`, `acceptance_validation`, `risks_alternatives_decisions` | `53277a534e01714662c9b653837032e6dad92bc1fb9e8a958811f5bc4969b43a` | `b819890d716d0eee5d286b72f283df53700d96901063fb14b0b477e37e81b0ca` | `ddf79244aace66556e611ecc3479ef01b832feb165f0eadf79836dd96e2701fa` |
| `PROP-100` | `assumptions`, `workflows_use_cases`, `data_model`, `integrations_dependencies`, `constraints_nfrs`, `acceptance_validation`, `risks_alternatives_decisions` | `af4466ccb2af7c938ac000e552fc051045dd9082e84dea7f647f4dc61d2cdf44` | `4458c76b898cdd2236d7492a8c74e5eadf9a26b024259632e4793e98a26c951c` | `eae498009a0f8a735fc64093e6f89f0cb898e932ddb777097258811340f746ce` |

All applies changed exactly two targets, restored none and require no recovery.
Each artifact-state numstat is again 21 additions and one timestamp replacement.
All 12 selected coverage artifacts are valid schema v2, owner-confirmed and
carry direct section rationale plus source evidence.

Final M4 selection evidence is 13/19 required sections (68.42%); definition
completeness remains independently 40/43 (93.02%). The final heuristic exclusion
count is 390 and does not contribute to the declared numerator. The six sections
without declared proposal evidence are `vision`, `objective`, `stakeholders`,
`scope`, `risks` and `milestones`. They are deliberately not backfilled from
generic keywords because their project definition is already supported by
README, repository documentation and reviewed migration evidence rather than a
single responsibility-bearing proposal.

The remaining 88 proposals are explicitly recorded as legacy/unmapped by the
readiness review. No empty coverage artifact, placeholder rationale or heuristic
promotion was created for them. A later batch requires the same owner-reviewed
selection and import process.

The final representative `PROP-100` packet has source fingerprint
`37eba673c7d534c52991dbb9e7bfab30fbc1b19cdcf4e1cb4a8bc6aaf79e067d`
and semantic fingerprint
`25403f58f1a23f14977e5bb838ca4d217c551bf481d2989ed44d21d3daf597df`.
Its retained neighborhood uses shared declared sections with `PROP-095`,
`PROP-099` and `PROP-094`; all vertical evidence is canonical, active and
owner-confirmed. Only deterministic budget truncation and the two intentional
draft/pending authority diagnostics remain.

#### Readiness Axis Correction

The first post-batch readiness review exposed an axis-conflation defect: a
section with complete definition but no declared proposal was labeled `missing`
and regenerated vertical questions that the owner had already answered.
`project_readiness_review` now calculates definition status before evidence
status. Such sections report `defined` with
`missing_proposal_coverage`; only genuinely incomplete definition sections enter
`missing_capisaldi` or generate questions. The text renderer exposes both
`definition` and `evidence` states on each row. Project vertical, progress and
coverage tests pass with 35 tests. The correction changes no canonical project
artifact and preserves the 13/19 evidence denominator.

After correction, the six deliberately uncovered sections report
`definition: complete / evidence: defined`. The remaining incomplete definition
statuses are the already truthful `assumptions=assumed`, `decisions=partial` and
`risks_alternatives_decisions=partial`; only Q002 still requires closure for M4,
while publication review remains later owner work. Validation is clean and no
migration recovery exists.

#### Definition Closure And M4 Exit

The separately reviewed M4 definition patch records the exact 12-proposal
owner-confirmed batch, its 13/19 section result, the intentional 88-proposal
legacy/unmapped remainder and the six definition-complete sections without
proposal evidence. It updates only `decisions`, `milestones` and
`risks_alternatives_decisions`, closes `Q002`, retains truthful partial statuses
and advances the next suggested action to the read-only M5 freshness command.

The preview bound source physical hash
`cbb2230dead3dd006e68182982b00bbd96d4432e0f6306aaef57987891c7f53b`,
changed semantic hash
`cc4ecb33d134147a090e59aad8b493afe16b2ba663bc222d70d19f8c4bc6ddc4`
to
`6177ea3aaf7f9cd70760b250dba70340a169b2e6051b4d86d412d8aa6c6b9adf`
and produced preview token
`00df704b5b9e5176dbc4d92ede2e258e4b40dc68c7acd6f365cd54edf39a95ea`.
The owner confirmed the exact preview; apply completed atomically with final
physical hash
`8f5934ed64a72dbbdafc6a38a82b2a0eb06bfc56cc53ba8cbe0fb6b4c8e9185a`,
no restored path and no recovery requirement.

Post-apply definition state is valid and has no open question. Progress remains
truthfully split between 40/43 definition units (93.02%) and 13/19 declared
evidence sections (68.42%), with 390 heuristic suggestions excluded. Readiness
reports the six uncovered complete sections as `defined`, lists exactly 88
legacy/unmapped proposals and does not promote heuristic evidence. Global
validation reports zero errors, warnings or infos, and migration lock and
transaction state are absent.

The final M4 focused gate ran project vertical, progress, coverage, proposal
artifact and decision-context source/retrieval/freshness/topology modules:
`138 passed in 21.24s`. Every materialized coverage mapping is owner-confirmed,
valid and traceable, no empty coverage artifact exists, and M4 is complete.

### M5 - Repository Rebuild And Baseline Comparison

#### Freshness Baseline And Frozen Rebuild Order

The read-only `p2p project freshness --format json` inspection after M2-M4
reports graph version 1 and canonical fingerprint
`095f40c820932556c6e2255f7b95047f48acb493c3dd3c786cf96cbba9c27617`.
The 16 catalogued nodes split into three current nodes, nine stale nodes and four
agent/owner-action nodes:

| State | Nodes |
| --- | --- |
| Current | `canonical_sources`, `decision_context`, `registries` |
| Stale | `project_projections`, `assessment`, `brief_context_prompt`, `maturity_progress`, `software_specs`, `visible_export`, `publication_packet`, `publication_validation`, `publication_render` |
| Agent or owner action | `operational_brief`, `next_actions`, `curated_publication`, `publication_review` |

`project_projections` is stale because 82 decision/feature projections exist
while the shared committed-authority policy expects 95. Downstream deterministic
nodes are stale through dependency propagation and legacy mtime fallback. The
request-scoped decision-context index is current; the catalog truthfully records
the optional missing `durable_decision_context_snapshot_refresh` primitive and
does not block request-scoped rebuild or retrieval.

The frozen rebuild order is:

1. `project_projections` via `p2p project refresh`.
2. `assessment` via `p2p assess refresh`.
3. `brief_context_prompt` via `p2p project brief prompt`.
4. `maturity_progress` via `p2p assess maturity refresh`.
5. `software_specs` via per-change `p2p spec refresh` preflight and refresh.
6. `operational_brief` via the agent-curated brief import lifecycle.
7. `visible_export` via `p2p project export`.
8. `next_actions` via owner-reviewed `p2p next refresh`.
9. `publication_packet` via `p2p project publish prepare`.
10. `curated_publication` via the project-curator import lifecycle.
11. `publication_validation` via `p2p project publish validate`.
12. `publication_render` via `p2p project publish render`.
13. `publication_review`, retained as a separate owner action.

Although registries are already current, M5 retains the explicit registry
refresh and count reconciliation before step 1 as the repository migration
gate required by `M5-T002`. Freshness inspection itself performed no persistent
write.

#### Registry Reconciliation

The owner confirmed `p2p registry refresh` after review of the current registry
status and pre-refresh hashes. The refresh retained 100 proposals, 100
decisions, 68 changes, 2 choices, 136 relations and 100 readiness records.
Artifact records increased from 2,276 to 2,293, exactly reflecting the M2-M4
definition, coverage and artifact-state materialization. The public Work surface
reports four canonical manifests (`WORK-001` through `WORK-004`). The canonical
freshness fingerprint remained
`095f40c820932556c6e2255f7b95047f48acb493c3dd3c786cf96cbba9c27617`,
proving that the derived refresh did not change canonical source state.

Changes, choices and relations remained byte-identical. Proposals, decisions,
artifacts and readiness changed as expected from the migrated canonical inputs.
Registry status is current and global validation remains clean.

Repository execution exposed an ownership overclaim in the freshness catalog:
the registry node used `.p2p/registries/*.yml`, which included `work.yml` even
though that file is the local branch-scan output of `WorkBranchService` and is
updated by `p2p work scan`, not by `p2p registry refresh`. The catalog now
derives its exact seven output paths from `REGISTRY_DEFINITIONS`. A regression
proves that another service's file under the same directory is excluded.
Freshness now reports seven current RegistryService outputs; `work.yml` remains
byte-identical and the four canonical Work counts are verified through
`p2p work list`. Focused freshness/registry/CLI selection passes with 16 tests;
`git diff --check` and global validation pass. Ruff is not installed in the
project virtual environment, so no Ruff command was available at this gate.

#### Project Projection Reconciliation

Before refresh, the public project status reported 95 committed-authority
proposals but only 82 generated feature directories. Each existing directory
contained the expected `feature.md`, `actions.yml` and `tasks.yml`; no manual or
unknown feature directory was present, and no projection ownership manifest
existed. The owner confirmed `p2p project refresh` after this review.

The atomic refresh produced 95 decision-map records and 95 feature directories,
each with the three expected files. The decision basis is exactly 94 `accepted`
plus one `accepted_with_changes` (`PROP-084`). Thirteen previously missing
projections were added and no manual path or obsolete owned path required
deletion. `projection-manifest.yml` now records manifest version 1,
`ProjectStateService` ownership, lifecycle-authority policy version 1, source
fingerprint
`ddf52475287ed532542d0ac09cd98229d156c1e029aad4480648db5ef12c1b13`
and 95 accepted projections.

The exact owned output set contains 291 paths: 285 per-feature files, decision
map, overview, problem, scope, SWOT and the manifest itself. Freshness reports
`project_projections=current` with
`projection_manifest_matches_current_sources` and fingerprint
`71b30e754c1ee4d8130126b542e722a2bef9468ee6ad175709b05e8d151e5196`.
The canonical fingerprint remains
`095f40c820932556c6e2255f7b95047f48acb493c3dd3c786cf96cbba9c27617`;
global validation is clean and migration recovery is absent.

Dogfooding found two output-contract omissions. Freshness did not include
`project-swot.md` although the service writes and owns it, and the refresh
result omitted `projection-manifest.yml` although it was committed. The catalog
now includes SWOT, a regression compares freshness output paths with the
manifest's complete `owned_paths`, and both applied and idempotent refresh
results return the manifest. Focused project-state/freshness/CLI selection
passes with 13 tests, the complete project-state/freshness/registry group passes
with 16 tests, and `git diff --check` passes.

The first real idempotence check exposed a related reconciliation-order defect:
the prior manifest was compared against an expected set that did not yet include
the manifest itself, so a second refresh deleted it as stale. The service now
adds the manifest to the complete owned set before stale-path calculation. A
double-refresh regression verifies byte-identical manifest preservation and
result-path reporting. After restoring through the supported command, two
successive real-repository refreshes retain manifest hash
`9bdd1b565bb2824b9370bb677477033888b1f8afbc449e27d82af832dd609883`
and decision-map hash
`ff59537daa2ea2e5a2a9d88e9f8d9fd1377817f00b1580a31ec501d2521179ec`.
The expanded project-state/freshness/CLI selection passes with 14 tests.

#### Request-Scoped Decision Context Rebuild

Decision context has no durable snapshot refresh primitive, so M5 rebuilds it
through the public request-scoped facade rather than inventing a file. The
freshness node is current and explicitly retains the advisory
`missing_optional_primitive:durable_decision_context_snapshot_refresh`.

The rebuilt global index reports:

| Measure | M1 baseline | After M3 | M5 |
| --- | ---: | ---: | ---: |
| Sources | 1,353 | 1,353 | 1,353 |
| Evidence | 2,813 | 2,832 | 2,944 |
| Semantic records | 2,171 | 2,171 | 2,218 |
| Nodes | 531 | 531 | 544 |
| Valid relations | 581 | 602 | 667 |
| Source diagnostics | 25 | 2 | 2 |

The index uses schema `decision-context-v1`, authority policy
`decision-context-authority-v2` and relation policy
`decision-context-relations-v2`. Source fingerprint is
`a5760461cd3dd0a6dc09ecc18a9ff4679d2c4df4582abbe2a07b0734b8b09bf8`
and semantic fingerprint is
`c5dc4c28793dca2b18e13ff4740e095d354400aaacbb39fa3117bae20496903a`.
Completeness remains truthfully `partial` solely because `PROP-063` and
`PROP-098` retain intentional draft/pending authority divergences. Both
diagnostics are `DC-AUTHORITY-STATUS-DIVERGENCE`; neither is fatal. Invalid,
ambiguous and unsupported relation diagnostics remain zero. Extraction uses one
discovery pass.

Medium retrieval for `PROP-100` found 45 candidates and retained 12, led by
`PROP-095`, `PROP-099` and `PROP-094`; explicit relations, accepted authority
and shared declared vertical sections are visible ranking signals. Reciprocal
retrieval for `PROP-095` found 25 candidates and retained 12, led by
`PROP-100`, `PROP-099` and `PROP-094`. Retained leading hits are active accepted
decisions, and imported vertical evidence remains canonical and
owner-confirmed. Each bounded packet reports only
`DC-RETRIEVAL-TRUNCATED` and `DC-INDEX-PARTIAL`, matching the budget and the two
intentional source diagnostics. The rebuild performed no persistent write.

#### Assessment, Maturity And Progress

The owner confirmed sequential deterministic refresh of assessment and maturity
after review of their 2026-06-03 legacy state. Readiness changed from 80/100 to
84/100 because current data contains two draft proposals and one active Change
Set, with no validation, registry, choice, blocked-change or active-Work
penalty. The output explicitly labels completion as
`legacy_deterministic_readiness`, maturity as `heuristic_keyword_rubric` and
`authoritative_project_definition: false`. Assessment hash changed from
`336feaa51535272fbaadd2d391da4f2e7007f1c28dbd0a95e44f88430357df37`
to
`40c36532e588dff064d58a5da6761f2fac680f346f901cf6a51debf5cfc6addd`.

Maturity regenerated against `project_vertical:software_project` with 27
selected criteria. Its rubric score remains 100/100, but the artifact declares
`scope_label: selected_project_rubric`, `basis: heuristic_keyword_rubric` and
`authoritative_definition_completeness: false`; it therefore cannot be read as
project-definition completion. Maturity hash changed from
`df71b63630c8304c7e5c35d21e58907331f0b6f8206425c97e3fcef0e9c57227`
to
`6775a6467a0fcab3f890e6f2833707bc2998642df65ec70ba215cf9d83dd5156`.

The independent request-scoped progress result remains 40/43 definition units
(93.02%) and 13/19 owner-declared evidence sections (68.42%), with 390 heuristic
suggestions excluded, two assumptions still `to_validate` and no open question.
Freshness reports both persisted nodes as `current_legacy_fallback`, explicitly
using content hash plus legacy mtime because these older artifact schemas do not
record source fingerprints; maturity also records that progress is
request-scoped. Global validation remains clean.

#### Brief, Next Actions, Specs, Export And Publication Packet

All 11 existing software-spec lifecycles passed preflight without blockers or
advisories. Ten existing specs were refreshed and `CHANGE-068` was generated
through the supported per-change command. Each generated spec contains the
seven required files. Freshness reports 77 owned files and
`software_specs=current_legacy_fallback` with fingerprint
`a21052254d7c099f701578590da1dfa9239d7c1ac785ce4f5575e05feedf3dab`.
Dogfooding found that the prior glob also claimed the optional legacy
`CHANGE-012/spec-refine.prompt.md`, which belongs to the separate prompt
lifecycle. The catalog now derives exact owned files from the shared
`SOFTWARE_SPEC_REQUIRED_FILES` contract and preserves the optional prompt. The
software-spec lifecycle/freshness selection passes with 18 tests.

The owner reviewed and imported an updated operational brief through
`p2p project brief import`. It records runtime/schema alignment, the 95-proposal
committed basis, `CHANGE-068` as the only active Change Set, independent 93.02%
definition and 68.42% evidence axes, the 88 intentionally unmapped proposals,
the two draft authority diagnostics and the remaining publication stages. A
second bounded import removed the now-completed self-referential import action.
The final brief hash is
`2a4a7cb52035c4f9361f32c918c28451bc811e2473f56878f21a583fc5499e92`.

Real-repository verification exposed a manual-stage freshness defect:
`operational_brief` and `next_actions` remained permanently
`owner_action_required` after successful supported writes, causing
`NEXT-DERIVED-FRESHNESS` to recommend the same brief import forever. The
legacy fallback now treats only those two nodes as current when their outputs
exist and are newer than current dependencies. Missing, older or upstream-
blocked outputs still require action. Publication review is deliberately
excluded and cannot become current from file presence alone. The focused
freshness/next-action selection passes with 21 tests.

The owner retired curated `NEXT-006` because its assertion that no active Change
Set existed was false after `CHANGE-068` became `implementation_ready`. The
audit log records the retirement and generated `NEXT-FALLBACK-001` now carries
the current continuation action. `p2p next refresh` reports zero active curated
and four generated actions. Next-action hashes are
`b0c47d0c48845fd23edd4dd72b12db1673d698b653a89ad20e53e5cfbd6158b7`
and
`bc8b7d4984c329adcdb30cf8e48755b2f0043ea346ddb0511d1209e4e54da2b8`
for active and log files respectively. Freshness reports both brief and next
actions as `current_legacy_fallback`.

The visible project export was regenerated through `p2p project export`. It now
states the live 95-proposal basis rather than the stale 93-proposal count, has
hash
`671c6355d8863fc0e05afd264d941b89aa470d281e189523ceca7f2c0536027e`
and is `current_legacy_fallback`. The command preserved the previous publication
bundle under `outputs/review-004`. Publication preparation then archived the
intermediate latest state under `outputs/review-005` and produced a current
packet with source fingerprint
`8b3c645679a359a99b96108a90701d2146544e146a59d5cc24b22810269f5054`.
Profile, curator packet and manifest hashes are respectively
`c47e93a77090506689c9cc3bc78bf524245e5c01a828fcf764a1ee5170336e78`,
`22958b00f018306d1a3c56b393d216a8043fae14d13c2ea6971562f3f7559e43`
and
`5652d1229a34b5a86e41b3b71dc1a3fa5c0cf99e4c8fce2f7901ae0694b98022`.

Publication status reports source export, profile and curator packet as ready;
curated Markdown, validation, render and review remain missing. Approval remains
false. The freshness graph now advances to `curated_publication` without
claiming any curator or owner action complete. `M5-T006` is complete.

#### Curated Publication, Validation And Render

The current publication packet was processed through the generated
`p2p-project-curator` contract. The new project-first document uses one H1,
adapts its structure to the valid `software_project` vertical and separates
governed memory, decision context, delivery, CLI/MCP boundaries, specifications,
migration and publication. It corrects the archived publication's stale
`base_project`, 93-proposal and draft-PROP-100 claims. It records the live
95-proposal committed basis, independent progress axes, `CHANGE-068`, the two
remaining draft proposals, the two assumptions to validate and the source-of-
truth boundary without a chronological proposal dump.

The draft was staged under `drafts/`, imported only through
`p2p project publish import` and removed after verification. Deterministic
validation passed with zero findings. The neutral WeasyPrint renderer produced
a valid, unencrypted PDF 1.7 with six A4 pages, no JavaScript and readable text
from the opening summary through final traceability. Visual samples of the
first, middle/table and final pages showed no overlap, clipping or unreadable
table layout.

The first render review caught an editorial self-staleness issue: the document
still described curation, validation and render as pending. A bounded second
import changed only the publication table and remaining-migration paragraph,
then validation and render were rerun. Final hashes are:

- curated Markdown:
  `6bb66ec8828c8e3f32f0470f3f8a1cf2b85f13811c4013c254b9d51c06569914`;
- validation result:
  `0ef3f4b34da892d9dcf6137e705743f4e1dd9c9961a682936a83e444b0fad3c8`;
- PDF:
  `556119d5482a286bedb4536d6abe3846c21baa2191b1eccd324739c97aeb4fa5`;
- publication manifest:
  `1bf43e7b49e7e35608a961f28952824b7e41c176e4f1661d405265c2ace02a01`.

Publication status reports source export, profile, packet, curated Markdown,
validation and render as ready. `validation_status=passed`,
`render_status=rendered`, `review_status=missing` and
`approved_for_publication=false`. Freshness retains exactly
`publication_review=owner_action_required`; no review file or approval was
created. `M5-T007` is complete.

#### Post-Rebuild Operational Diagnostics

The read-only M5 operational gate reports runtime `0.2.0` compatible with
`>=0.2.0,<0.3.0` and recommended version `0.2.0`. Workspace schema status is
`current`, layout is `current`, semantic alignment is `aligned`, current and
target versions are both 1, migration is not required and the applied migration
record retains plan fingerprint
`a4272623498d6b3597f2bb10e2613fd9cb2a48ef1b3e4a645472eeec0eda4bf4`.

Global validation reports zero errors, warnings and infos. Doctor confirms the
project-local CLI, Python package and MCP server are available, the repository
is on `main`, remote sync configuration is ready and workspace recovery is not
required. `p2p` is not globally on PATH, but the documented discovery path
correctly selects `.venv/bin/p2p`; this is not a runtime incompatibility. The
working tree is intentionally dirty because implementation and migration output
are not yet committed.

Project status reports 95 generated features, an available operational brief
and four generated next actions. Compact context reports 100 proposals, 95
committed-authority proposals, two drafts, 68 Change Sets, one active Change Set
and four Work items. The active `software_project` vertical lock is valid with
checksum
`aa9fd9691890053c2abf390853b920c43b1b29160169f39539ac9f0fc7ad6d67`;
definition state is valid with no missing required field, 16 complete sections,
two partial sections and one assumed section. Progress remains 40/43 (93.02%)
definition units and 13/19 (68.42%) declared evidence sections.

Every derived node through publication render is current or explicitly
`current_legacy_fallback`. The only attention node and rebuild action is
`publication_review=owner_action_required`. Recovery status independently
reports `required=false`, migration lock `absent`, blank transaction and journal
state and no available recovery action. The physical migration transaction
directory contains no scratch file, and curator staging under `drafts/` is
empty. `M5-T008` is complete without changing owner review state.

#### Focused Post-Migration Test Gate

The M5 focused gate ran 16 schema/migration, decision-context,
vertical/coverage/progress, project-state, freshness/next-action and publication
modules. This includes scale/performance, stale-plan, transaction,
rollback/recovery, topology, ranking, output ownership and publication lifecycle
regressions. The result is `205 passed in 42.02s`. Tests used temporary fixture
workspaces and left the migrated repository state unchanged. `M5-T009` is
complete.

#### Full Post-Migration Test Gate

The repository-standard `./scripts/test-full.sh -q` gate passes with
`841 passed in 166.58s`. This is 97 tests above the 744-test M1 baseline and 12
above the 829-test post-implementation/pre-migration gate, reflecting the
completed feature coverage and the regressions added during real-repository
rebuild. No test failed or was skipped by an early exit. `M5-T010` is complete.

#### M1 To M5 Baseline Comparison

| Dimension | M1 baseline | M5 result |
| --- | --- | --- |
| Runtime | Contract initially pinned to incompatible `0.1.9`; aligned during M1 | `0.2.0`, `>=0.2.0,<0.3.0`, compatible |
| Workspace schema | `legacy_undeclared`, layout `legacy`, owner input required | v1, layout `current`, alignment `aligned`, migration recorded |
| Vertical | `base_project` fallback; no state or lock | `software_project` 1.0.0, valid state and lock |
| Definition | Absent and uninitialized | Valid; 16 complete, 2 partial, 1 assumed; 40/43 units |
| Domain/permissions | Files absent; compatibility fallback reads | Explicit software domain and owner `mrjungle` permission contract |
| Proposal lifecycle | 100 total: 94 accepted, 1 conditional, 2 draft, 2 superseded, 1 deferred | Unchanged canonical lifecycle and authority distribution |
| Vertical evidence | No proposal coverage; progress fallback 0/10 | 12 owner-confirmed proposals covering 13/19 sections; 88 intentionally unmapped |
| Decision context | 1,353 sources, 2,813 evidence, 2,171 records, 531 nodes, 581 relations, 25 diagnostics | 1,353 sources, 2,944 evidence, 2,218 records, 544 nodes, 667 relations, 2 intentional diagnostics |
| Registries | 100 proposals/decisions, 68 changes, 2 choices, 136 relations, 2,276 artifacts, 100 readiness | Same domain counts; 2,293 artifacts after governed migration evidence |
| Project projections | 95 committed proposals but 82 feature projections; no ownership manifest | 95 decisions/features and 291-path ownership manifest; unknown paths preserved |
| Progress | Definition uninitialized; evidence 0/10; legacy maturity 100 could mislead | Definition 40/43 (93.02%) and evidence 13/19 (68.42%) exposed independently |
| Assessment/maturity | Readiness 80; maturity 100 without authoritative definition basis | Readiness 84; maturity 100 explicitly heuristic and non-authoritative |
| Operational brief/actions | Stale brief claimed all Change Sets complete; 5 actions | Current brief identifies CHANGE-068; 0 curated and 4 generated actions; stale NEXT-006 audited as retired |
| Software specs | 71 files: 10 required seven-file specs plus one optional legacy prompt | 11 generated seven-file specs (77 owned files); optional prompt preserved but excluded from ownership |
| Publication | Export, packet, curated Markdown, validation and render stale; review missing | Export, packet, curated Markdown, passed validation and PDF current; review still explicitly missing |
| Freshness | 13 downstream nodes stale or requiring owner/agent work | Every node through render current/current-fallback; only owner review requires action |
| Full tests | 744 passed | 841 passed |

The comparison separates migration improvements from unchanged governance.
Proposal decisions, draft authority and publication review were not normalized
for a cleaner report. The reduction from 25 to two decision diagnostics comes
from reviewed relation corrections and richer evidence, not from suppressing
errors. The final single freshness action is an intentional owner decision,
not residual schema misalignment. `M5-T011` is complete.

#### Intentional Residual State

The following state remains intentionally visible after migration:

- 88 proposals have no declared vertical-coverage artifact. They remain valid
  legacy project history and are not counted as current vertical evidence.
  Heuristic suggestions (390 matches) remain read-only and no empty placeholder
  coverage files were created.
- Six definition-complete sections have no proposal evidence. Their definition
  is complete; their evidence numerator remains uncovered by design.
- `PROP-063` and `PROP-098` remain draft/pending. Their two authority/status
  divergences keep decision-context completeness `partial` without creating a
  fatal diagnostic or changing proposal authority.
- Assumptions `A001` (writable local filesystem/Git audit substrate) and `A002`
  (available accountable owner) remain `to_validate`; `A003` rebuildability is
  validated.
- The optional legacy `CHANGE-012/spec-refine.prompt.md` remains present but is
  outside `SoftwareSpecService` refresh ownership. Existing intake, prompt and
  downstream spec-export history preserved by the migration plan is not
  rewritten merely to adopt schema v1.
- Assessment, maturity, brief, next-action and software-spec formats without
  source manifests retain explicit `current_legacy_fallback` status rather than
  false fingerprint authority.
- Decision context remains request-scoped and reports the optional missing
  durable snapshot refresh primitive. A persistent cache, database-backed
  storage and cache invalidation policy remain deferred to measured follow-up.
- MCP coverage apply, automatic freshness orchestration, remote fleet migration
  and automatic curator/owner stages remain intentionally deferred. Existing
  read and suggestion surfaces continue to expose the required state.
- `CHANGE-068` remains `implementation_ready`; implementation artifacts do not
  complete its governed lifecycle automatically.
- Publication review remains missing and `approved_for_publication=false`.
  Curated Markdown, passed validation and a rendered PDF are not owner review.
- Generated archives under `outputs/review-001` through `outputs/review-005`
  remain publication history owned by the output lifecycle.

None of these residuals requires manual `.p2p` repair for normal operation.
They are legacy history, explicit partial evidence, deferred product scope or
owner-controlled decisions. `M5-T012` is complete.

#### Final Diff Classification

The post-migration worktree remains intentionally dirty and was reviewed without
discarding any pre-existing work. Tracked diff statistics report 103 files,
10,120 insertions and 1,388 deletions before accounting for untracked additions.
Every path falls into an expected class:

- F1-F9 implementation under `src/p2p_engine`, its CLI/MCP/public facade wiring,
  version metadata and focused/full regression tests;
- feature and stable documentation, including
  `specs/features/workspace-schema-versioning-and-legacy-migration`,
  `docs/WORKSPACE-MIGRATION.md`, README, CLI/MCP guidance, setup and changelog;
- governed P2P writes produced by supported runtime/schema, metadata,
  definition, relation, coverage, artifact-state and next-action primitives;
- deterministic registries, 95 project projections with ownership manifest,
  assessment/maturity/brief outputs and 11 software specifications;
- visible export, publication packet, curated Markdown, validation, PDF and
  lifecycle-owned `outputs/review-004` and `outputs/review-005` archives.

The only tracked deletion is the stale
`outputs/latest/exports/project-curator-import.md`; the publication/export
lifecycle archived it in the review bundles and did not reproduce it as a
current profile export. No canonical source was deleted. The 13 newly generated
feature directories correspond exactly to the gap from 82 to 95 committed
projections. New coverage files correspond exactly to the 12 owner-confirmed
proposals. No temporary migration input, transaction journal, curator staging
file or test output appears in Git status. `git diff --check` passes.

The review found no unrelated change that should be reverted and no unexplained
manual `.p2p` mutation. `M5-T013` is complete.

#### Layout And Semantic Alignment Interpretation

Workspace status reports schema state `current`, layout status `current` and
alignment status `aligned`. This means the v1 schema contract, runtime,
vertical, lock, definition, domain, permissions and required structural
relationships are present and mutually valid. It does not mean every project
section has complete evidence, every proposal is mapped or decided, every
derived legacy format has a source manifest, every Change Set is terminal or
the publication is approved.

The independent semantic/project advisories remain explicit: definition is
40/43, declared evidence is 13/19, 88 proposals are intentionally unmapped, two
draft authority divergences keep decision context partial, two assumptions are
to validate, `CHANGE-068` is active and publication review is missing. None is a
workspace-layout defect, so manufacturing `alignment_required` would be as
misleading as manufacturing a fully complete project result. `M5-T015` is
complete.

#### Final Authority, Ownership And Freshness Ledger

The live committed-authority basis is 95 proposals, not the feature draft's
historical 94-item example: 94 are `accepted` and `PROP-084` is
`accepted_with_changes`. Two proposals are draft, two superseded and one
deferred. Project refresh reconciled exactly 95 decision records and feature
directories. Its manifest owns 291 paths: 285 per-feature files, decision map,
overview, problem, scope, SWOT and the manifest. The refresh added the 13
missing feature directories, found no unknown/manual path to remove and retained
stable manifest and decision-map hashes across repeated refresh.

Runtime is `0.2.0`, requires `>=0.2.0,<0.3.0` and is compatible. Workspace
schema v1 is current/aligned, migration recovery is not required, lock state is
absent, transaction and journal identifiers are empty, and the physical
migration directory contains no scratch file.

| Freshness node | M5-T001 state | Final state | Final interpretation |
| --- | --- | --- | --- |
| `canonical_sources` | current | current | Canonical fingerprint collected |
| `decision_context` | current | current | Request-scoped index rebuilt; two intentional diagnostics |
| `registries` | current | current | Exact RegistryService-owned outputs |
| `project_projections` | stale | current | 95 projections match the 291-path manifest |
| `assessment` | stale | current_legacy_fallback | Readiness 84 with explicit non-authoritative basis |
| `brief_context_prompt` | stale | current_legacy_fallback | Prompt/context rebuilt from current project state |
| `maturity_progress` | stale | current_legacy_fallback | Heuristic maturity separated from request-scoped progress |
| `software_specs` | stale | current_legacy_fallback | 11 generated specs, 77 exact owned files |
| `operational_brief` | owner action | current_legacy_fallback | Reviewed brief imported through supported lifecycle |
| `visible_export` | stale | current_legacy_fallback | Export regenerated from 95 committed proposals |
| `next_actions` | owner action | current_legacy_fallback | Stale curated action retired; four generated actions |
| `publication_packet` | stale | current | Packet bound to current source fingerprint |
| `curated_publication` | owner/agent action | current | Curated Markdown imported and hash-bound |
| `publication_validation` | stale | current | Validator passed with zero findings |
| `publication_render` | stale | current | Neutral six-page PDF rendered |
| `publication_review` | owner action | owner_action_required | Intentionally missing; approval remains false |

The graph moved from three current, nine stale and four owner/agent nodes to 15
current/current-fallback nodes plus one explicit owner-review action. It does
not hide the optional request-scoped snapshot primitive or legacy fallback
bases. `M5-T016` is complete.

#### Final Acceptance Gate

| AC | Direct evidence |
| --- | --- |
| AC001 | Runtime reports `compatible`; workspace schema independently reports v1 `current/aligned`. |
| AC002 | Legacy plan fixtures are deterministic and no-write; the real reviewed plan retained fingerprint `a427262...4bf4`. |
| AC003 | Adjacent legacy-to-v1 apply reached v1; repeat-plan/apply and idempotence tests prove no-op behavior. |
| AC004 | Pre-write validation, every replace boundary, crash, rollback, resume and recovery paths have failure-injection tests. |
| AC005 | Legacy status, collection conflict and supported-alias fixtures pass without the original avoidable diagnostics. |
| AC006 | Ambiguous relations blocked the first real plan and remained diagnostics until owner-reviewed curation. |
| AC007 | Atomic vertical apply produced matching active state, valid lock, definition and 27 enabled rubrics. |
| AC008 | Domain and owner permission contracts were materialized from reviewed legacy evidence without rerunning init. |
| AC009 | Suggestions remained no-write; 12 reviewed proposal packages were imported with provenance and artifact state. |
| AC010 | Progress reports 40/43 definition and 13/19 evidence with independent bases and excluded heuristics. |
| AC011 | The 16-node graph detected the 82/95 projection divergence and ordered every rebuild through review. |
| AC012 | Owner reviewed the complete applicable dry-run, target hashes, inputs and fingerprint before canonical apply. |
| AC013 | Decision map and feature projections contain exactly the live 95 committed-authority proposals. |
| AC014 | Final context has zero invalid, ambiguous or unsupported relation diagnostic; only two intentional draft divergences remain. |
| AC015 | Every `.p2p` mutation used runtime/schema, artifact, coverage, definition, brief, next, refresh or spec CLI primitives. |
| AC016 | Focused gate: 205 passed; full gate: 841 passed; validation 0/0/0; recovery absent; freshness reduced to owner review only. |
| AC017 | Concurrency, durable directory sync, lock ownership and recovery tests pass; real transaction area is empty. |
| AC018 | Definition, impact/conflict and coverage changes used complete preview tokens, fresh source hashes and protected apply. |
| AC019 | Doctor, project status, compact context and next actions exposed schema/recovery/freshness state read-only. |
| AC020 | Shared lifecycle authority drives 95 projections; exact registries/spec/manifest ownership and brief/action freshness are tested. |
| AC021 | Runtime contract and managed setup guidance use one rollback-safe writer; incompatible-contract repair regression passes. |
| AC022 | Per-target preimage and rollback-ownership tests stop before overwriting concurrent external edits. |
| AC023 | Governed facade writes reject active migration ownership; required status/context/validation reads remain available. |
| AC024 | Apply recomputes plans from resupplied input and semantic patches from resupplied packages; no durable preview cache exists. |

The final repository operates on workspace schema v1 through supported public
primitives and requires no manual `.p2p` repair. Remaining draft, evidence,
legacy-fallback, active-Change-Set and publication-review states are truthful
project work, not failed migration gates. `M5-T014` and the repository migration
are complete.
