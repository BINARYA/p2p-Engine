# Implementation Evidence - Proposal Decision Revision And Revocation Lifecycle

## Purpose

This file records the implementation baseline and validation evidence for
`PROP-102` / `CHANGE-070`. It is local development documentation, not
canonical P2P state.

## Governed Origin

- Proposal: `PROP-102`, accepted, readiness `100/100`, confidence `high`.
- Change Set: `CHANGE-070`, status `planned` at implementation start.
- Generated software spec:
  `.p2p/outputs/software-spec/CHANGE-070`.
- Local implementation spec: `requirements.md`, `design.md`, `tasks.md`.
- Drift review: no conflict was found between the accepted proposal, Change
  Set, generated software spec and local feature documents. The local feature
  adds implementation detail without changing the governed direction.

## Baseline

Captured on 2026-07-17 before feature source edits:

| Item | Baseline |
| --- | --- |
| Source commit | `23dbd4f8a3945567ab852da839fbe842a9a4ab85` |
| Package version | `0.3.1` |
| Project runtime contract | `>=0.3.0,<0.4.0`, recommended `0.3.1` |
| Workspace schema | current v2, target v2, aligned |
| Python in `.venv` | CPython `3.14.4` |
| System `python3` | CPython `3.14.4` |
| Validation | 0 errors, 0 warnings, 0 infos |
| Registry | current; 102 proposals, 70 changes, 102 decisions |
| Derived freshness | `attention_required`; 12 attention nodes |
| Working tree | dirty before implementation; unrelated existing edits must be preserved |

The CLI has no top-level `--version` option. Package/runtime versions were
therefore captured through `p2p_engine.__version__` and `p2p runtime status`.

## Existing Behavior To Replace

- `ProposalDecisionService.record()` writes `decision.md` and then rewrites the
  `proposal.md` status without an atomic transaction.
- A second call can overwrite an accepted proposal with `rejected`, losing the
  prior accepted state from normal reads.
- `proposal accept`, `proposal reject`, `proposal defer` and `decision record`
  are immediate one-step mutations.
- MCP tools `p2p_proposal_accept`, `p2p_proposal_reject` and
  `p2p_proposal_defer` consume consent but call the same overwrite writer.
- Readiness override is currently written before acceptance and can therefore
  become orphaned when the later decision write fails.

## Public-Surface Inventory

### CLI

- `p2p proposal accept PROP --reason ... --approver ... [--override-readiness]`
- `p2p proposal reject PROP --reason ... --approver ...`
- `p2p proposal defer PROP --reason ... --approver ...`
- `p2p decision record PROP --outcome ... --reason ... --approver ...`

Current success strings are `Proposal decision recorded.` and
`Decision recorded.`. Current failures use the shared CLI `fail()` boundary.
The approved replacement keeps command names but removes one-step mutation:
without a token commands preview; apply requires a matching token and explicit
confirmation.

### MCP

- `p2p_proposal_accept` with consent operation `proposal_accept`
- `p2p_proposal_reject` with consent operation `proposal_reject`
- `p2p_proposal_defer` with consent operation `proposal_defer`

Current required fields are `proposal_id`, `actor_id`, `consent_id` and
`reason`. Existing response fields include proposal ID, outcome, reason,
approver, decision date, consumed consent and governance metadata.

### Storage And Consumers

The pre-implementation source inventory found 114 references involving
`proposal.md`, `decision.md`, proposal status or `DecisionOutcome`. They are
classified as follows:

| Class | Representative owners | Required treatment |
| --- | --- | --- |
| Proposal body parsing | readiness, proposal update, synthesis, vertical text matching | Keep body parsing; exclude projected status from semantic fingerprints |
| Schema-v2 compatibility | proposal views, validation, registries, migration | Route through the explicit legacy adapter |
| Projection display | proposal show/review, exporters, publication | Display lifecycle-derived projections |
| Authority bug | Change creation, project state/progress/maturity/assessment, vertical evidence, software-spec lifecycle, decision context, freshness | Consume the captured lifecycle-authority view |
| Separate domain | choice `decision.md`, branch accept/reject | Leave unchanged |

The authoritative implementation audit is repeated after S6; this baseline is
not used as proof of final consumer convergence.

## Workspace-Operation Inventory

The existing compatibility operation is `proposal_decision_record`, currently
schema-v1-safe. Schema-v3 introduces these classified write IDs:

- `proposal_decision_apply`
- `proposal_decision_projection_repair`
- `proposal_decision_ledger_repair`
- `proposal_decision_legacy_resolution`

All four require workspace schema v3. The old
`proposal_decision_record` identifier remains only as a compatibility entry
that cannot invoke the overwrite writer.

## Baseline Semantic Surfaces

The following current outputs were identified before implementation and must
receive additive lifecycle fields or consume lifecycle authority without
removing existing stable identities:

- proposal show/list/full review;
- proposal, decision, relation, artifact and readiness registries;
- Change creation and status;
- Work planning;
- software-spec lifecycle, generation and freshness;
- project state, progress, maturity, assessment and vertical evidence;
- decision context, topology, retrieval and context packets;
- managed next actions;
- derived freshness;
- visible export and publication packet.

## Diagnostic Allocation

`P2P360..P2P389` had no collisions in `src/`, `tests/` or `docs/` at baseline.
The feature owns this range for stable decision-ledger, lifecycle, preview,
impact, repair and legacy-resolution diagnostics.

## Test Baseline

The following command passed before implementation:

```bash
.venv/bin/pytest -q \
  tests/test_proposal_decision_service.py \
  tests/test_workspace_schema_service.py \
  tests/test_workspace_operation_compatibility.py \
  tests/test_workspace_migration_service.py \
  tests/test_mutation_preview_and_writer.py
```

Result: `51 passed in 6.94s`.

## Focused Command Catalog

The focused commands are maintained in `tasks.md` under
`Planned Focused Commands`. Slice-specific additions:

```bash
.venv/bin/pytest -q tests/test_proposal_decision_ledger.py
.venv/bin/pytest -q tests/test_proposal_lifecycle_authority_service.py
.venv/bin/pytest -q tests/test_workspace_v3_migration.py
.venv/bin/pytest -q tests/test_proposal_decision_impact.py
.venv/bin/pytest -q tests/test_proposal_decision_cli.py
.venv/bin/pytest -q tests/test_proposal_decision_mcp.py
./scripts/test-public.sh -q
./scripts/test-full.sh -q
```

## Implementation Decisions Confirmed At Gate P

- Canonical path: proposal-local `decision-events.yml`.
- Target workspace schema: v3.
- Runtime delivery line: `0.4.x`; no package version bump before release gate.
- Event identity: canonical semantic payload plus operation-key and predecessor
  binding; no mtime, Git or absolute-path input.
- Authority: CLI actor must be the declared owner; MCP executor remains
  distinct and requires owner-approved, preview-token-bound consent.
- Compatibility commands: preview without token, apply only with token and
  confirmation, no one-step fallback.
- Migration ownership: ledger, normalized proposal/decision projections and
  workspace schema; derived artifacts are refreshed later by their owners.
- Repair: projection repair derives from a valid ledger; ledger repair cannot
  remove or rewrite a valid prefix.

## Implemented Engine Contract

- Package version is `0.4.0`; the runtime supports workspace schema v3 while
  retaining schema-v2 reads and an adjacent v2-to-v3 migration.
- Each schema-v3 proposal owns one append-only `decision-events.yml`; the
  proposal status and `decision.md` are deterministic current-state
  projections.
- The lifecycle distinguishes accepted, conditionally accepted, deferred,
  withdrawn, rejected, revoked, superseded, split, merged and reinstated
  states. Rejected or withdrawn direction is reconsidered through a new linked
  proposal, not by overwriting history.
- All decision writes use one owner-governed preview/apply service. Exact retry,
  stale preview, conflicting head, readiness override, process concurrency and
  transaction recovery have separate tested behavior.
- Revocation preview captures the complete dependency graph before pagination.
  Applying a decision changes only the ledger and projections, plus readiness
  only for an explicit atomic acceptance override.
- Projection repair derives from a valid ledger. Ledger repair accepts exact
  restoration or a valid suffix and rejects removal, reorder, changed prefix,
  broken continuity and future contracts.
- Unknown legacy authority remains preserved and blocks normal decisions until
  an owner runs the explicit resolution preview/apply operation.
- Proposal, registry, Change, Work, software-spec, project, vertical, export,
  publication and decision-context consumers use the lifecycle authority view.
- CLI and MCP expose the same core status, history, preview, impact, apply and
  repair results. Existing accept/reject/defer entry points no longer perform a
  one-step overwrite.

## Consumer Source Audit

The post-implementation `rg` inventory classified remaining proposal
`decision.md` and status reads as:

| Class | Remaining use |
| --- | --- |
| Schema-v2 compatibility | legacy adapter and guarded fallbacks used only when no v3 lifecycle provider exists |
| Projection display | proposal detail, visible export and publication rationale |
| Drift validation | global validation and lifecycle projection comparison |
| Proposal-body evidence | vertical and maturity text extraction; no status authority is inferred |
| Separate domain | choice `decision.md` and managed branch lifecycle |

Schema-v3 authority selection in registries, Change creation, Work planning,
software specs, project projections, progress/maturity/assessment, vertical
evidence, freshness and decision context resolves through
`ProposalLifecycleAuthorityService`. No authority-changing production writer
bypasses `ProposalDecisionService`: `ProposalDocumentService` only creates the
empty undecided ledger, while migration and the two repair modes use their
explicit candidate-validation and atomic-write paths.

## Late Review Corrections

The final review found and corrected four gaps:

1. real spawn-process decision apply initially exposed a race with the global
   migration lock; decision mutations now wait boundedly for an already-running
   decision transaction while preserving non-blocking defaults elsewhere;
2. artifact impact authority now uses lifecycle `active`/`ever_active`, so a
   revoked historical impact remains owner-controlled even if projections
   drift;
3. rejected/withdrawn lifecycle status exposes the linked-proposal
   reconsideration command and diagnostic without creating anything;
4. MCP apply rechecks that the consent approver is still a project owner and a
   consumed receipt replay verifies proposal, operation key, preview token,
   event ID and committed head binding.

`EVENT_INTEGRITY_POLICY_VERSION = 1` is explicit and participates in event-ID
derivation. The YAML event contract remains version 1.

## Technical Gate Evidence

The following checks were run from the implementation worktree:

| Check | Result |
| --- | --- |
| Integrated feature/consumer gate | `339 passed in 41.69s` |
| Ledger/lifecycle/service group after integrity-policy update | `165 passed in 6.96s` |
| Migration/context/consumer group after integrity-policy update | `26 passed in 15.91s` |
| MCP hardening group | `7 passed in 2.45s` |
| Public suite | `259 passed, 949 deselected in 127.70s` |
| Full suite | `1208 passed in 298.26s` |
| Compile | `python -m compileall -q src tests`, clean |
| Version/release contract tests | `5 passed in 0.35s` |
| Diff whitespace | `git diff --check`, clean |

Pre-release package candidate before the exact release commit:

| Artifact | Evidence |
| --- | --- |
| Wheel | `/tmp/p2p-engine-0.4.0-final-candidate.cgLbVh/p2p_engine-0.4.0-py3-none-any.whl` |
| Wheel SHA-256 | `72ba01e25d1d36df12ed851b7ec9cd4e04eb33a8e30a7afe3a0dcc6bd72ab595` |
| Sdist | `/tmp/p2p-engine-0.4.0-final-candidate.cgLbVh/p2p_engine-0.4.0.tar.gz` |
| Sdist SHA-256 | `d6735815812804fe03e1bf13894bdc3ebb9a774d6e3c321f480b75cf3e515cbb` |
| Contents | verified as version `0.4.0`; 232 wheel files and 453 sdist files |
| Isolated import | loaded from `/tmp/p2p-engine-0.4.0-final-installed.BJpWxj`, version `0.4.0`, schema `3` |
| Installed smoke | fresh schema-v3 workspace validation is clean; decision lifecycle and migration commands are present |

The `Failed to create stream fd: Operation not permitted` messages emitted by
the isolated runner are environment telemetry warnings; import and test
processes exited successfully.

## Governed Gate Progress

On 2026-07-18, the local `v0.3.1` tag was extracted into a temporary runner and
executed with the repository's existing Python environment. The runner imported
version `0.3.1` from the temporary source tree and reported the project runtime
contract as compatible.

Through that supported CLI, `CHANGE-070` followed both required lifecycle
transitions:

1. `planned -> implementation_ready`
2. `implementation_ready -> in_progress`

The current source-checkout runtime then re-ran the read-only implementation
spec lifecycle preflight. It reported no blocker or advisory. The first
governed refresh attempt was correctly rejected before writing because runtime
`0.4.0` was outside the project's `>=0.3.0,<0.4.0` contract.

The owner subsequently approved the exact runtime-contract preview generated
by P2P. The compatible `v0.3.1` runner applied a range-only transition to
`>=0.3.0,<0.5.0`, retained `recommended: 0.3.1`, regenerated `P2P-SETUP.md`
and bound the audit to `PROP-102`. No schema migration occurred. Runtime 0.4.0
then passed compatibility preflight and refreshed the generated software spec
through `p2p spec refresh --change CHANGE-070`. Its freshness is `current` and
`provenance.yml` contains the lifecycle decision binding for `PROP-102`.

Repository validation exposed four legacy proposals with incomplete authority
fields. A late gate correction fixed their accidental classification as
nonexistent invalid ledgers: validation now reports the intended
`P2P360_DECISION_LEGACY_AUTHORITY_UNRESOLVED` against each `decision.md` and
points to the v2-to-v3 migration plan. These were the four cases visible
through schema-v2 validation; the later M-T005 dry-run applied the stricter
owner-identity rule to every proposal and found 98 migration candidates that
require legacy authority resolution. The four validation findings do not
prevent schema-v2 reads or unrelated compatible writes.

G-T013, G-T014 and G-T015 are complete. No compatibility check was bypassed
and no `.p2p` file was edited manually.

## Runtime Release And Deployment Evidence

- Target release: P2P Engine `0.4.0`, wheel and sdist via the GitHub Release
  attached to tag `v0.4.0`.
- On 2026-07-18 the owner explicitly authorized the complete D-T004 operation:
  create the audited release commit on `main`, test its exact SHA, create and
  push annotated tag `v0.4.0`, push `main`, and allow the tag-triggered GitHub
  workflow to publish wheel and sdist. The authorization includes the explicit
  raw-Git escape hatch needed only for pushing the release tag.
- Supported test endpoints: Python 3.11 and 3.14 in the release workflow.
- The workflow validates a fresh schema-v3 workspace rather than incorrectly
  running runtime 0.4 against this repository before its governed migration.
- Release archive verification now requires the proposal-decision lifecycle,
  decision-context ledger and v2-to-v3 migration modules, plus their critical
  sdist tests.
- The complete worktree audit found only governed `PROP-102` / `CHANGE-070`
  state, the two completed local feature specifications, their source/tests,
  generated vertical-pack conversion and associated documentation/release
  changes. No unexplained manual `.p2p` mutation was identified.
- The release implementation commit is
  `6db2d36fc5465e3484f780a4428bc41ae10399e8`. The final tagged commit is
  `ae1324c75e43d21cbf2c88ec88eb19e1e2549750`, which adds the verified CI test
  runner correction.
- Exact-candidate local/container evidence:
  - Python 3.11 public: `259 passed, 955 deselected`;
  - Python 3.11 full: `1213 passed, 1 skipped`;
  - Python 3.14 public: `259 passed, 955 deselected`;
  - Python 3.14 full: `1214 passed`;
  - test-script and release-workflow regressions: `14 passed`.
- The first tag-triggered run `29640020457` stopped before tests because the
  scripts assumed `.venv/bin/pytest` in GitHub Actions. It did not publish a
  release. The correction makes every test script fall back to the active
  `pytest`, sets `PYTEST_BIN=pytest` explicitly in the release matrix and adds
  regression coverage.
- The owner authorized replacing the unpublished failed tag. `v0.4.0` was
  moved with a remote `--force-with-lease` bound to the known failed tag object;
  no unrelated remote update could be overwritten.
- GitHub Actions run `29640890775` completed successfully for Python 3.11,
  Python 3.14 and the build/publish job. Tag/version validation, release
  contract tests, fresh schema-v3 validation, archive verification and GitHub
  Release creation all passed.

Published release:

| Item | Evidence |
| --- | --- |
| Release | `https://github.com/BINARYA/p2p-Engine/releases/tag/v0.4.0` |
| Tag target | `ae1324c75e43d21cbf2c88ec88eb19e1e2549750` |
| Wheel | `p2p_engine-0.4.0-py3-none-any.whl`, 592328 bytes |
| Wheel SHA-256 | `72ba01e25d1d36df12ed851b7ec9cd4e04eb33a8e30a7afe3a0dcc6bd72ab595` |
| Sdist | `p2p_engine-0.4.0.tar.gz`, 781247 bytes |
| Sdist SHA-256 | `6a096b82f993b5d6c64a8eb84801bb723828029eca7d32982f958dc8a0faf980` |
| Archive contract | 232 wheel files and 454 sdist files |
| Published install | version `0.4.0`, imported from an isolated temporary `site-packages` |

The wheel installed successfully from the public GitHub Release URL without
using or modifying the repository `.venv`. A fresh workspace initialized by
that installed runtime is schema v3 and validates cleanly after registry
refresh.

Source-checkout and published-wheel comparison against the still-schema-v2
repository produced identical normalized payload hashes:

| Surface | SHA-256 |
| --- | --- |
| Runtime status | `8605df77d96b9318c8a903565497ad73c209ec92b0960fdcca9a80fcb4378fdb` |
| Workspace schema status | `0a5a80d22e2bf883dd9696d5856aaf23c051fafbd42d3dda872b9bac72caa5a2` |
| `PROP-102` legacy decision status | `2ce6104ec5f39444d8e875a908a993feadd855e34b2d7d47684a82e93eccc7fc` |
| V2-to-v3 migration plan | `c3c0b76cf96ee75fd922c14b60e5149c472cb501826140cd9c4d990d79b68749` |

The decision-help diff contains only the expected executable label:
`python -m p2p_engine` for the checkout and `p2p` for the installed wheel.
The installed runtime reports the repository contract as compatible, schema
state `upgrade_available`, current schema 2 and target schema 3. The read-only
plan is applicable, contains 308 operations and has fingerprint
`78b8058d1da2391cc98cd16b9571bcb529f0f8789059c4ea8c31bcfefdf6bfef`.

The development `.venv` still has stale distribution metadata from its old
editable installation even though it imports source `__version__ == 0.4.0`.
M-T003 must therefore select the verified published 0.4.0 executable or
explicitly reinstall the project environment before migration; it must not
infer runtime identity from that stale metadata.

D-T001 through D-T009 are complete. The repository `.p2p` workspace remains
schema v2 and no D operation changed canonical workspace state.

## S9-T014 Generated Agent Refresh

On 2026-07-18, generated agent instructions were refreshed with the published
P2P Engine `0.4.0` wheel installed in an isolated temporary environment. The
runtime reported package and source version `0.4.0`, imported from
`site-packages`, and was compatible with the repository's
`>=0.3.0,<0.5.0` contract. The repository remained schema v2 with no recovery
transaction.

The pre-refresh inventory contained exactly `generic`, `codex` and `claude`;
all were clean. The first `p2p agent update all` call revealed that `all`
expands to every supported adapter rather than only installed adapters.
`cursor`, `copilot`, `gemini` and `opencode` were removed immediately through
their supported `p2p agent uninstall` operations. No generated file or `.p2p`
registry was repaired manually.

The final operation used:

```bash
p2p agent instructions refresh --profile generic
```

That primitive merged the already declared `generic`, `codex` and `claude`
profiles, refreshed their shared and adapter-specific instructions and rebuilt
the integration registry without installing extra adapters. Final inventory:

- `generic`, `codex`, `claude`: installed, health `clean`, drift `clean`;
- `cursor`, `copilot`, `gemini`, `opencode`: not installed;
- agent doctor service: target `all`, health `clean`, zero findings;
- repeated joint instruction refresh: no changes.

Generated changes add the schema-v3 proposal decision lifecycle, two-phase
decision writes, rejection-versus-revocation guidance, workspace migration
boundaries and current project-readiness commands to `AGENTS.md`,
`CLAUDE.md`, the Codex project skills and `.p2p/agent-policy.yml`. Registry
hashes were regenerated by the lifecycle command. The CLI also normalized one
existing `.p2p/project.yml` audit timestamp representation without changing
its semantic value.

Focused evidence:

| Check | Result |
| --- | --- |
| Agent instructions, selection, hygiene and validation tests | `55 passed in 3.05s` |
| Generated file/registry doctor | `health=clean`, zero findings |
| Adapter inventory | only `generic`, `codex`, `claude` installed; all clean |
| Diff whitespace | `git diff --check`, clean |
| Workspace schema | current 2, target 3, no recovery required |
| Global validation | only the four expected `P2P360` legacy cases plus `P2P308` upgrade info |

The exercise exposed one non-blocking runtime `0.4.0` defect:
`p2p agent update <adapter>` can preserve an unchanged file owned by another
installed adapter with registry drift `missing` instead of `clean`. The files
remain present and hash-correct. The final joint instruction refresh restores
the correct registry state. Until the preservation logic is corrected and
released, multi-profile projects should use the joint instruction refresh
rather than sequential single-adapter updates. This defect does not affect the
workspace v2-to-v3 migration primitives.

S9-T014 is complete. No schema migration, decision lifecycle write, derived
artifact rebuild or publication approval occurred.

## M Pre-Apply Baseline And Dry-Run

On 2026-07-19 the owner separately confirmed the repository runtime-contract
update and the intent to proceed with the schema-v2-to-v3 migration gate. The
published P2P Engine `0.4.0` wheel was installed in an isolated temporary
environment and used for every M command. It reported:

- Python `3.14.4`;
- distribution and source version `0.4.0`;
- import path under the isolated environment's `site-packages`;
- release tag `v0.4.0` at `ae1324c75e43d21cbf2c88ec88eb19e1e2549750`;
- repository HEAD `78519e7b4ff28c063725e6d118ad28bfcda4b5a6`.

The owner-authorized runtime contract preview/apply changed
`.p2p/project/runtime.yml` and managed `P2P-SETUP.md` from
`requires >=0.3.0,<0.5.0`, recommended `0.3.1`, to
`requires >=0.4.0,<0.5.0`, recommended `0.4.0`. The apply was atomic, used
actor `mrjungle`, left the active runtime compatible and did not perform any
subsequent governed mutation.

The read-only pre-migration baseline is:

| Surface | Baseline |
| --- | --- |
| Workspace schema | current 2, target 3, aligned, upgrade available, no recovery |
| Validation | 4 `P2P360` errors, 0 warnings, 1 `P2P308` info |
| Proposal sources | 102 |
| Legacy lifecycle view | 96 accepted, 2 draft, 3 other terminal/historical, 1 unknown legacy |
| Registries | current: 102 proposals, 102 decisions, 70 changes, 2 choices, 140 relations, 2,357 artifacts, 102 readiness |
| Change Sets | 67 completed; `CHANGE-068` and `CHANGE-069` implementation-ready; `CHANGE-070` in progress |
| Work | 4 terminal manifests: 3 retired and 1 cleaned |
| Software specs | 13 generated; `CHANGE-070` current and 12 current through legacy fallback |
| Project progress | definition 40/43 (93.02%); declared evidence 13/19 (68.42%) |
| Assessment and maturity | readiness 76/100; stored maturity 100/100 |
| Derived freshness | attention required; 12 nodes require refresh or owner action |
| Publication | source/packet/curation/validation/render stale; review missing; approval false |
| Pre-migration Git diff | 12 modified files after S9-T014 evidence and the runtime-contract update |

The no-owner-patch command
`p2p workspace migrate plan --to 3 --format json` is applicable and
deterministic with fingerprint:

```text
78b8058d1da2391cc98cd16b9571bcb529f0f8789059c4ea8c31bcfefdf6bfef
```

Plan structure:

- 308 operations;
- 102 canonical ledger creations;
- 102 canonical `proposal.md` projection updates;
- 102 canonical `decision.md` projection updates;
- one canonical workspace-schema update;
- one non-canonical derived-refresh advisory;
- 307 candidate files in total;
- the schema update is the final canonical operation and depends on all earlier
  canonical operations;
- every candidate operation is applicable and source preimages/candidate
  semantic hashes are present;
- 190 `P2P326` degraded findings identify preserved legacy intake, prompt,
  software-spec and export artifacts that are outside this migration's target
  ownership; none is rewritten or deleted.

The plan exposed a material discrepancy with the earlier four-case estimate.
It would create:

- 98 ledgers with `authority_resolution=unknown_legacy`, no event and preserved
  source hashes/values;
- 2 resolved empty ledgers for draft `PROP-063` and `PROP-098`;
- 2 resolved accepted ledgers for `PROP-101` and `PROP-102`.

The 98 unknown-authority sources are grouped as follows:

| Legacy approver | Count | Source statuses |
| --- | ---: | --- |
| `local` | 69 | 67 accepted, 1 deferred, 1 superseded |
| `owner` | 18 | 17 accepted, 1 superseded |
| `bootstrap maintainer` | 3 | accepted |
| `unknown_legacy` | 3 | accepted |
| `davide` | 3 | 2 accepted, 1 accepted-with-changes |
| `codex` | 2 | accepted |

These identities are not current declared owner `mrjungle`; the migration
correctly refuses to infer that they represent the same person. Registering
generic or agent identities as owners merely to make migration pass would
fabricate authority and is not an acceptable workaround.

Applying the plan now would reduce the resolved active proposal authority from
the current lifecycle view's 96 proposals to only `PROP-101` and `PROP-102`
until 98 separate legacy-resolution preview/apply operations were reviewed and
completed. The schema apply is therefore intentionally paused before M-T008.
No ledger, proposal projection, decision projection or workspace-schema file
has been written by the migration.

## H Pre-Migration Owner Attestation Hardening

The M dry-run demonstrated that runtime `0.4.0` could preserve unresolved
legacy authority but had no governed bulk input for a current owner to attest
exact historical sources. H adds that missing capability without changing
migration target ownership or bypassing the existing plan/apply transaction.

Implemented surfaces:

- `normalize_owner_inputs` accepts a closed
  `proposal_decisions.authority_attestations` contract version 1;
- migration input YAML now rejects duplicate keys and payloads above 4 MiB;
- every attestation binds current owner ID, legacy status/approver/date and
  exact `proposal.md` plus `decision.md` SHA-256 hashes;
- `accepted_with_changes` requires bounded structured conditions;
- `MigrationAttestationTemplate` and
  `WorkspaceCompatibilityService.proposal_decision_attestation_template`
  generate a deterministic read-only review packet;
- `WorkspaceV2ToV3ProposalDecisionLedgerHandler` creates an initial event with
  channel `workspace_migration_owner_attestation`, current-owner authority and
  separately preserved legacy provenance;
- unsupported predecessor/lineage outcomes remain `unknown_legacy`;
- `p2p workspace migrate attestation-template --to 3 --owner OWNER` exposes the
  template through CLI text and JSON without writing a file;
- apply requires the same normalized patch and fingerprint, and rejects source
  edits both before and after lock acquisition.

Repository dogfooding with owner `mrjungle` remained read-only and retained the
original no-input plan fingerprint
`78b8058d1da2391cc98cd16b9571bcb529f0f8789059c4ea8c31bcfefdf6bfef`.
The generated template classified:

| Class | Count | Proposals/reason |
| --- | ---: | --- |
| Immediately attestable | 91 | aligned simple outcomes with complete legacy authority and exact source hashes |
| Structured conditions required | 1 | `PROP-084` |
| Historical lineage required | 2 | `PROP-007`, `PROP-008` |
| Legacy sources diverge | 1 | `PROP-001` |
| Legacy authority incomplete | 3 | `PROP-009`, `PROP-010`, `PROP-013` |

This corrects the earlier estimate of 95 immediately attestable sources. The
four divergent/incomplete proposals must remain owner-curated; migration must
not manufacture missing rationale, date or source agreement.

Full-suite load also exposed two pre-existing race windows in decision apply.
An active decision transaction was temporarily surfaced as migration recovery,
and a competing commit between head check and preview rebuild could produce a
transition error. `ProposalDecisionService` now distinguishes a live decision
PID from stale recovery and repeats exact-retry/head checks around preview
rebuild. Deterministic tests cover identical and conflicting commits in that
window.

Validation evidence:

| Check | Result |
| --- | --- |
| Focused migration/service/CLI | `51 passed` |
| Focused decision service | `34 passed` |
| Public CLI/MCP contract | `260 passed, 973 deselected` |
| Final full local suite, Python 3.14.4 | `1233 passed` |
| Compile and whitespace | `compileall` clean; `git diff --check` clean |
| Optional static tools | `ruff` and `mypy` are not installed in `.venv`; no implicit dependency installation was performed |

H is technically complete in source. The repository still uses schema v2 and
no migration apply occurred. Because these changes are newer than published
runtime `0.4.0`, D2 must produce and install an owner-authorized `0.4.x` patch
before M-T008 can resume.

## D2 Patch Candidate Preflight

Patch version `0.4.1` was selected on 2026-07-19. Package and source metadata,
version consistency tests, changelog, install links and release examples now
agree on that version. Schema-v2 compatibility remains available and the
v2-to-v3 inspect/plan/apply range remains `>=0.4.0,<0.5.0`.

The release verifier now requires the attestation CLI, strict schema loader,
compatibility/planner/handler integration, filesystem facade and corresponding
regression suites in wheel and sdist. It also requires the decision service
concurrency regression suite in the sdist.

Pre-commit candidate checks:

| Check | Result |
| --- | --- |
| Version and release contract | `11 passed` |
| Python 3.14.4 public suite | `260 passed, 974 deselected` |
| Python 3.14.4 full suite | `1234 passed` |
| Python 3.11.15 public suite | `260 passed, 974 deselected` |
| Python 3.11.15 full suite | `1233 passed, 1 skipped` |
| Python 3.11 wheel/sdist verification | `232` wheel members; `454` sdist members |
| Isolated wheel smoke | installed/imported `0.4.1`; CLI and migration apply help available |
| Installed attestation smoke | `review_required`; 91 included and 7 manual-review sources |
| Compile and whitespace | `compileall` and `git diff --check` clean |

The first Python 3.11 container attempt used the minimal `python:3.11-slim`
image without Git. Its 58 public failures were all Git-dependent tests and are
not counted as product failures. Repeating the matrix with Git `2.47.3`, as
available on GitHub runners, produced the green results above.

Temporary pre-commit build hashes were:

```text
wheel  0907339afdfdd9fa1ed1915dd6ec76d650d32f25ea4ef785150322dc953729eb
sdist  c47eadfa7b3f6b794d0af1da9d8680972e586ba23f411c7f80ee850f7e305d63
```

These hashes identify only the disposable preflight build and are not claimed
as published release hashes. D2-T002 remains open because its contract requires
the same checks from the exact committed candidate.

Complete diff review found no schema-v3 migration apply, ledger creation,
migration lock/journal, `.p2p` repair, derived registry/project/publication
rebuild or publication approval. Workspace schema remains aligned at v2 with no
recovery transaction. `p2p validate` continues to report only the four expected
manual legacy-authority errors for `PROP-001`, `PROP-009`, `PROP-010` and
`PROP-013`, plus the schema-v3 upgrade information.

### Published Patch And Active Runtime

The owner reviewed version `0.4.1`, base and candidate hashes, test/package
evidence and the exact GitHub target. Commit, tag, branch push and tag push were
authorized as separate steps. The resulting release identity is:

| Surface | Identity |
| --- | --- |
| Commit | `af10120865ded4f9a4666ad5b6e5c222144e2bc7` |
| Commit message | `feat: harden legacy decision migration attestations` |
| Tag | `v0.4.1` (annotated tag object `da59c20f3c7b134cbf401dff7c8ff63096fc96a6`) |
| Remote | `git@github.com:BINARYA/p2p-Engine.git`, branch `main` |
| Workflow | GitHub Actions `29685780911`, all Python 3.11, Python 3.14 and build/publish jobs successful |
| Release | `https://github.com/BINARYA/p2p-Engine/releases/tag/v0.4.1` |
| Wheel | 597,330 bytes; SHA-256 `0907339afdfdd9fa1ed1915dd6ec76d650d32f25ea4ef785150322dc953729eb` |
| Sdist | 791,580 bytes; SHA-256 `c47eadfa7b3f6b794d0af1da9d8680972e586ba23f411c7f80ee850f7e305d63` |

Both published digests match the disposable exact-commit build. The published
wheel was first installed in an isolated temporary environment and then, after
separate owner authorization, installed into the repository `.venv` with
`--force-reinstall --no-deps`. This replaced stale editable package metadata
`0.1.9` without changing Python or dependency versions.

The active runtime now reports:

- package and module version `0.4.1`;
- module and distribution metadata under the repository `.venv`
  `site-packages`;
- direct artifact binding to the published wheel SHA-256 above;
- compatible runtime contract `>=0.4.0,<0.5.0`;
- aligned workspace schema v2 with upgrade to v3 available;
- no migration recovery transaction.

Source and active installed runtime produced byte-identical outputs:

| Output | SHA-256 |
| --- | --- |
| Attestation template JSON | `d5603f10a2d31fed5cfeacae668bb4e0491be625b824ef846e164d95238b8c7d` |
| No-input migration plan JSON | `1adb7bba6b9ae5a1b74d8b2ed04bf7841e7493c72b723f3b18970cb9a4afa876` |
| Migration apply help | `bb2ca50c74183f3aad112ca8d67d641a2397abd520b2ab9faff3ad73c1f98be8` |

Template and plan agree on fingerprint
`78b8058d1da2391cc98cd16b9571bcb529f0f8789059c4ea8c31bcfefdf6bfef`;
the no-input plan remains applicable with 308 operations, 91 proposals are
immediately attestable and 7 require manual review. D2 is complete and M may
resume, but no migration apply has occurred.

## M Owner-Attested Re-Plan

For M-T008 the owner confirmed one structured `PROP-084` condition:

```text
C001: L’autorità di PROP-084 è limitata al contratto runtime minimo,
P2P-SETUP.md, runtime status, validation e blocco delle scritture governate
incompatibili. Restano esclusi setup obbligatori, install/reconcile manager,
release resolver, metadata wheel/digest/source, mutazioni dell’ambiente e
fallback automatici.
```

The generated 91-entry owner input was extended only with `PROP-084`, bound to
legacy approver `davide`, decision date `2026-07-12`, status
`accepted_with_changes`, condition `C001` and exact current proposal/decision
source hashes. The resulting temporary 92-entry input has SHA-256:

```text
9b27ebdcb74535ab1ce14eec93b2e99ab569dcdd088bee5edc238f4d60b60233
```

The input remains local scratch under `/tmp`; it is not canonical project state
and has not been copied into `.p2p`.

The installed `0.4.1` runtime produced an applicable attested plan with
fingerprint:

```text
14829c8f80c672a37315dc1c52bc23f39b6219c9761802dd408c1d4e181bc642
```

Attested/no-input comparison:

- both plans contain the same 308 operation identities, targets, kinds,
  ownership classes, ordering and dependencies;
- exactly 276 operation records change, consisting only of candidate semantic
  hashes for the ledger, proposal projection and decision projection of each
  of the 92 attested proposals;
- the schema update remains operation index 306, depends on all 306 earlier
  canonical operations and is followed only by a non-applicable derived-refresh
  advisory;
- 190 `P2P326` findings remain unchanged for out-of-scope legacy durable
  artifacts;
- exactly six `P2P360` findings remain:
  `PROP-001`, `PROP-007`, `PROP-008`, `PROP-009`, `PROP-010` and `PROP-013`;
- there is one expected `P2P308` schema-upgrade information finding;
- no migration recovery transaction or lock exists.

The six residual proposals preserve their sources as `unknown_legacy`.
`PROP-007` and `PROP-008` require typed historical lineage; the other four
require individual owner legacy resolution after migration. No relation,
authority fact or missing source value was inferred.

## M Applied Migration And Canonical Verification

The owner explicitly confirmed attested plan fingerprint
`14829c8f80c672a37315dc1c52bc23f39b6219c9761802dd408c1d4e181bc642`
and actor `mrjungle`. Installed runtime `0.4.1` applied that exact plan in an
exclusive transaction:

```text
transaction_id: migration-6fc36d34399ec5c9
source_version: 2
target_version: 3
status: applied
recovery_required: false
```

The transaction changed the 306 proposal ledger/projection targets and the
schema contract. It did not run the non-applicable derived-refresh advisory.
The schema history records `workspace-v2-to-v3`, actor `mrjungle`, application
time `2026-07-19T12:36:54Z` and the confirmed fingerprint.

Immediate canonical verification:

- workspace schema is current v3, layout current and alignment aligned;
- migration recovery and exclusive lock are absent;
- 102 proposal directories contain exactly 102 `decision-events.yml` ledgers;
- `PROP-084` is `accepted_with_changes` with one event dated `2026-07-12`;
- all ledger chains and proposal/decision projections pass `p2p validate`;
- validation reports zero errors, zero warnings and zero information findings;
- exactly `PROP-001`, `PROP-007`, `PROP-008`, `PROP-009`, `PROP-010` and
  `PROP-013` remain `unknown_legacy`, each with zero events.

No interruption occurred, so recovery resume/rollback was not required.

The initial read-only capability probe for `PROP-007` correctly rejected a
`superseded` legacy resolution without lineage using
`P2P369_DECISION_LINEAGE_INVALID`. A subsequent contract review established
that the missing lineage options on the dedicated legacy-resolution command are
intentional rather than a runtime gap. R-F5-013 and R-F5-026 prohibit converting
a terminal legacy history directly into one lineage event because that would
fabricate its accepted predecessor and authority interval. The supported flow
is a current owner legacy resolution followed by a normal, independently
previewed lineage-closing event with complete impact capture.

## M Owner Curation And No-Op Verification

The owner confirmed that all historical aliases refer to the same sole project
owner. Each residual proposal was still reviewed independently; ownership did
not substitute for missing state, date, rationale or lineage evidence.

Four proposals required one owner legacy-resolution event:

| Proposal | Effective state | Event | Decision date |
| --- | --- | --- | --- |
| `PROP-001` | `accepted` | `PDE-61f7c7e703420d7d5c4ad807` | `2026-05-19` |
| `PROP-009` | `accepted` | `PDE-4ba6bc02e77a0d2b6ed47313` | `2026-05-26` |
| `PROP-010` | `accepted` | `PDE-1d5b2741827957b057d0364f` | `2026-05-26` |
| `PROP-013` | `accepted` | `PDE-20b6debbe45862ae86007979` | `2026-05-26` |

The owner explicitly confirmed each event type, rationale and date after a
token-bound preview. Every apply changed only that proposal's ledger and two
engine-owned projections. Preserved legacy evidence and source hashes remain in
each first event's migration provenance.

The two terminal legacy histories used two current, append-only events so no
accepted predecessor was fabricated:

- `PROP-007` first received owner resolution event
  `PDE-eedddf147d179409aaa26ab5`, then event
  `PDE-7dc3b675d8b005864a265c26` closed the recovered interval as `split` into
  active `PROP-017` and `PROP-025`. Impact was complete with zero dependents.
- `PROP-008` first received owner resolution event
  `PDE-29096c07d7e0643eefaaa82e`, then event
  `PDE-2bb422381ef86784c09435db` closed the recovered interval as `superseded`
  by active `PROP-091`. Impact was complete with two review-only dependents:
  stale derived freshness and the generated publication packet. Decision apply
  did not mutate either dependent.

Validation after every curation batch reported zero errors, warnings and
information findings. The final 102-proposal distribution is:

```text
accepted: 96
accepted_with_changes: 1
deferred: 1
draft: 2
split: 1
superseded: 1
unknown_legacy: 0
```

The final workspace schema status is current v3, aligned, with no migration
lock or recovery transaction. A second plan to target v3 returned `no_op`, no
migration IDs and one read-only `workspace-schema-no-op` operation:

```text
fingerprint_sha256:
6d2d82a2b3c784ccb485035e8e4ebcbcdb613d2b88d9b900440ef29e04deb491
```

M is complete. Canonical ledgers and projections are valid and owner-curated;
derived registries, project views, decision context, exports and publication
remain intentionally separate work under A.

## A Derived Artifact Alignment

All writes used the owning P2P primitive. No `.p2p` file was repaired or
normalized manually.

| Surface | Final evidence |
| --- | --- |
| Registries | current: 102 proposals, 102 decisions, 70 Change Sets, 2 choices, 140 relations, 2,459 artifacts and 102 readiness records |
| Project projection | current for 97 active proposals; historical `PROP-007` split and `PROP-008` supersession excluded from active authority |
| Decision context | latest measured build: 1,486 sources, 3,249 evidence records, 2,495 semantic records, 716 nodes, 1,019 valid relations and zero diagnostics |
| Progress | definition 40/43 (93.02%); declared evidence 13/19 (68.42%); axes remain separate |
| Assessment and maturity | 76/100 `needs_review`, high confidence; 100/100 `well_defined` |
| Software specs | `CHANGE-070` current; 12 legacy specs explicitly `unknown_origin` |
| Next actions | 17 stable generated actions, zero curated; the two active Change Sets are included and completed `CHANGE-070` is absent |
| Visible export | `outputs/latest/project.md`, SHA-256 `cc5f0c70ef678245b96086ccf936a0707d8f80e054abe8a7e1c5337c37f162ad` |
| Curated publication | SHA-256 `0b4a46693d2a47b0b3fb360807260564b614e5bb515603b139d8151f85f74805` |
| Publication validation | passed with zero findings |
| Publication PDF | SHA-256 `3dc7d22d6d62f6d526c4439d6dcfc96f74a1b733f901a3e01fb4f4d48a86ad89` |
| Publication review | missing by design; `approved_for_publication=false` |

The final publication manifest reports source export, profile, curator packet,
curated Markdown, validation and render as ready. The general freshness graph
still reports inherited attention because the 12 legacy software specs are
partial. The downstream publication stages are current according to their
own source-bound manifest; the general graph conservatively propagates the
legacy uncertainty. This is an explicit review classification, not a request
to overwrite those specs.

The final post-brief freshness check uses canonical fingerprint
`6f4eb251acc8a1c4e814bef5faf22eed7530534cde07bdf291a3fc92296b032d`.
Canonical sources, registries, project projections and request-scoped decision
context are `current`; assessment, operational brief and the final 17 managed
next actions are `current_legacy_fallback`. The remaining graph attention is
fully explained by the 12 `unknown_origin` specs, their conservative downstream
propagation and the missing owner publication review.

The final freshness audit exposed one false stale result in `next_actions`.
The node previously treated the append-only `next-actions-log.yml` as a
refresh output and compared the oldest audit-log mtime with current
dependencies. `NODE_CATALOG` now owns only active `next-actions.yml` for that
node. Regression
`test_next_action_audit_log_age_does_not_stale_refreshed_active_actions`
proves an old audit log cannot invalidate a successful refresh.

Additional alignment corrections discovered and tested:

- one request-scoped freshness snapshot is reused across decision remediation
  actions;
- project assessment reuses its computed next-action snapshot;
- decision impact accepts a supplied freshness snapshot and emits the real
  `p2p project freshness` remediation command;
- readiness gaps emit the current
  `p2p project readiness questions ...` commands;
- project vertical diagnostics use the same current readiness command family.

Real-repository timing remains a residual performance risk:

- full freshness: approximately four minutes;
- next-action refresh/list: approximately six minutes;
- publication preparation: approximately four minutes.

Snapshot reuse removes repeated graph construction inside one request, but the
single global source enumeration remains expensive and requires a separate
performance feature rather than an unreviewed cache in this lifecycle change.

## A Pre/Post Comparison

| Axis | Before migration/alignment | Final |
| --- | --- | --- |
| Workspace schema | v2 | v3, aligned, no lock/recovery |
| Proposal ledgers | absent as canonical authority | 102 valid ledgers |
| Unknown legacy authority | 6 after automatic migration | 0 after owner curation |
| Active proposal basis | 97 | 97 |
| Historical lineage | legacy projection | typed split/supersession events |
| Definition progress | 40/43 | 40/43 |
| Declared evidence | 13/19 | 13/19 |
| Publication | stale/missing after export archive | all technical stages ready |
| Publication approval | false | false |
| Repeated v3 plan | not applicable before migration | no-op fingerprint `6d2d82...deb491` |

Decision apply did not mutate Change Set, Work, software-spec, vertical, code,
Git or publication lifecycle state. Derived surfaces changed only through
their explicit owner commands.

## Final Validation

All final commands imported local implementation through `PYTHONPATH=src`, so
the installed `0.4.1` package could not hide post-release source changes.

| Check | Final result |
| --- | --- |
| Alignment-focused regressions | `49 passed in 45.86s` |
| Public suite | `260 passed, 978 deselected in 123.65s` |
| Full suite | `1238 passed in 311.64s` |
| Version/release contract | `11 passed in 0.17s` |
| Compile | `python -m compileall -q src tests`, clean |
| Diff whitespace | `git diff --check`, clean |
| Repository validation | 0 errors, 0 warnings, 0 infos |
| Repeated migration plan | schema-v3 `no_op`, fingerprint `6d2d82...deb491` |
| Final wheel | SHA-256 `97eed5a59b848f1bc9f312a1e8389960d2c2240ef357a2cf256ae93de7ded8f0` |
| Final sdist | SHA-256 `b6154102e8cb7571fff4a618196d2db28a603d2509365eaa3b817c3701fe4f8a` |
| Package contents | wheel 232 files, sdist 454 files |
| Installed smoke | isolated Python 3.14 runtime `0.4.1`, fresh schema v3, clean validation |

`PROP-102`, `CHANGE-070`, the generated P2P software spec and local
requirements/design/tasks were re-read after alignment. No semantic drift or
spec lifecycle blocker exists. Source audits still classify direct legacy
reads as compatibility, display, validation or proposal-body evidence; MCP
decision apply remains consent-bound to `PROP-XXX@preview-token`.

## Final Lifecycle And Handoff

On 2026-07-20 the owner explicitly confirmed both terminal delivery
transitions. The P2P CLI applied and verified:

1. `CHANGE-070: in_progress -> in_review`
2. `CHANGE-070: in_review -> completed`

The completion did not infer proposal, publication or dependent lifecycle
decisions. The generated software spec was refreshed and is `current`; project
assessment is 76/100, managed next actions were reduced from 18 to 17 and no
longer target `CHANGE-070`, and the operational brief was imported through its
supported primitive.

The visible export, curator packet, curated Markdown, validation and PDF were
then rebuilt in order. The final publication manifest binds source fingerprint
`f83544654dee8db3979aa11e95a5e3308a690db85fa63b5c641672612c404c5a`
to export, packet, curated, validation and render stages, all `ready`.
Validation passed with zero findings. Publication review remains `missing` and
`approved_for_publication` remains `false`.

Public compatibility remains intentional: schema-v2 decision reads are
supported, schema-v2 event writes are blocked pending migration, and schema-v3
uses token-bound append-only decision events. This repository is migrated to
schema v3 with 102 valid ledgers and no unknown authority.

## Residual Owner Or Manual Actions

- `CHANGE-068` and `CHANGE-069` remain `implementation_ready` and are outside
  the lifecycle decision for this feature.
- Twelve legacy software specs remain `unknown_origin`; each requires
  provenance evidence or explicit review, not deterministic overwrite.
- Publication review remains missing and approval remains false.
- Project question `PRQ-7070e7a631b1df44` and assumptions `A001`/`A002`
  require separate owner input.
- The post-release alignment corrections are present in local source and the
  verified temporary package, but no commit, tag, push or new release was
  authorized by this gate.

A and F are complete. AC029 and AC030 have direct owner-controlled migration,
ledger/projection, lifecycle and publication evidence. No publication approval,
commit, tag, push or new release was inferred.
