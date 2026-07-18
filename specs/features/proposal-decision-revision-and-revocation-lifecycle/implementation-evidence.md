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

Final package candidate:

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
points to the v2-to-v3 migration plan. These four cases are explicit M-T007
inputs; they do not prevent schema-v2 reads or unrelated compatible writes.

G-T013, G-T014 and G-T015 are complete. No compatibility check was bypassed
and no `.p2p` file was edited manually.

## Deployment Preparation

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
- D-T002 remains open until the authorized release commit exists and the clean
  suites can be attributed to that exact commit.

## Explicitly Deferred Gates

The following are intentionally not implementation side effects:

- no P2P-generated agent adapter was refreshed;
- `CHANGE-070` is `in_progress`; no completion state was inferred;
- no commit, tag, push or package publication was performed;
- this repository recommends runtime `0.3.1` while temporarily accepting
  `>=0.3.0,<0.5.0` before release;
- this repository's `.p2p` workspace remains schema v2;
- no registry, project projection, decision-context, export or publication
  rebuild was run for a schema-v3 repository;
- publication approval was not inferred or changed.

These operations remain under slices `D`, `M`, `A` and `F` and require the
corresponding supported P2P primitives and owner confirmations.
