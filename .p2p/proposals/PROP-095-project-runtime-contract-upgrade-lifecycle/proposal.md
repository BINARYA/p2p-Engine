# PROP-095 - Project Runtime Contract Update Lifecycle

## Status

`accepted`

## Problem

PROP-084 allows a P2P-managed project to declare the P2P Engine runtime range it trusts, recommend a runtime version to collaborators, expose compatibility diagnostics, and block governed writes when the declared runtime contract cannot be trusted.

The project still lacks an explicit lifecycle for changing that contract after initialization.

An owner may intentionally move a project to another P2P Engine version or runtime line. Editing `.p2p/project/runtime.yml` manually is unsafe because it bypasses validation, can leave generated setup guidance stale, provides no deterministic preview of collaborator impact, and does not define how the PROP-084 governed-write gate may be crossed when the active runtime is outside the old compatible range.

The project-level decision to change the required runtime must remain distinct from installing, upgrading, downgrading, or reconciling the runtime installed on a collaborator's machine.

## Context

PROP-084 introduced a project runtime contract, `P2P-SETUP.md` guidance, runtime status states, and a governed-write gate. That solves fresh-clone alignment and day-to-day diagnostics, but it does not define how the owner safely changes the runtime policy later.

PROP-095 defines that update lifecycle. It updates the runtime contract and the P2P-managed setup guide together. It does not install software, choose an environment, download releases, resolve packages, or reconcile collaborator machines.

The lifecycle must remain usable from an older runtime when the only problem is that the active runtime is outside a valid, supported old contract range. It must not become a generic bypass for invalid, missing, unsupported, unmanaged, or undeclared runtime-contract states.

## Goals

- Give the owner an explicit, preview-first operation for changing the project runtime contract.
- Expose separate read-only and mutating command surfaces.
- Update `.p2p/project/runtime.yml` and managed `P2P-SETUP.md` as one coordinated policy change.
- Classify upgrade, downgrade, range widening, range tightening, runtime-line change, recommended-only change, no-op, and active-runtime exclusion.
- Preserve PROP-084 write-gate safety while allowing a narrow runtime-contract update exception for valid incompatible old contracts.
- Allow agents and non-owner collaborators to produce read-only previews for owner review.
- Require owner authority, explicit confirmation, stale-preview protection, and structured reasons where the impact is material.
- Provide deterministic human-readable and JSON output for humans, agents, CI, and scripts.
- Keep runtime installation, upgrade, downgrade, package resolution, remote lookup, and release availability enforcement out of scope.

## Non-Goals

- Do not install, upgrade, downgrade, select, or reconcile a local P2P Engine runtime.
- Do not query GitHub, download release metadata, resolve wheels, or verify installability through the network.
- Do not make release metadata from PROP-080 a blocking dependency for runtime contract updates.
- Do not overwrite, adopt, merge, rename, back up, or replace unmanaged `P2P-SETUP.md` files.
- Do not implement contract repair, schema migration, contract recovery, or legacy adoption workflows.
- Do not add MCP mutation in the first implementation.
- Do not create Git commits, branches, pushes, pull requests, merges, or provider handoffs.
- Do not perform unrelated governed mutations after a new contract makes the active runtime incompatible.

## Proposal

Define an explicit runtime contract update lifecycle with two CLI subcommands:

```text
p2p runtime contract preview
p2p runtime contract apply
```

`preview` is strictly read-only. It validates the proposed contract, evaluates current contract state, evaluates authority for diagnostic purposes, classifies impact when the current state can be trusted, reports planned file changes, reports release availability diagnostics, and returns a deterministic `expected_state_token` only when an applicable update can later be applied.

`apply` is the only mutating command. It requires the same proposed `requires` and `recommended` values used during preview, the same structured reason and optional linked decision, a valid `expected_state_token`, current owner or permission authority, and explicit `--confirm`.

The first implementation shall not provide a single-command mode that previews and applies in one invocation. A future interactive convenience wrapper may be added only if it delegates to the same preview and apply services and preserves the same security semantics.

### Runtime Contract Values

The update operation supports changes to:

- `requires`, the compatible runtime range that may operate the project
- `recommended`, the runtime version recommended for setup guidance

Every proposed contract must satisfy:

```text
recommended in requires
```

The owner may update `recommended` without changing `requires`, provided the proposed recommended version still satisfies the unchanged compatible range.

If `requires` and `recommended` are both unchanged, the operation returns `no_change`, produces no applicable token, requires no apply operation, consumes no consent, and modifies no file.

### Supported Range Grammar

The first implementation of the update lifecycle supports this restricted grammar:

```text
==VERSION
>=LOWER,<UPPER
```

Versions and ranges use the PEP 440-compatible semantics selected for the runtime contract.

Arbitrary compound expressions, exclusions, wildcards, environment markers, and package-resolution expressions are outside the first implementation of this update lifecycle. This restriction keeps impact classification deterministic. It does not globally constrain all future runtime-contract parsing or schema evolution.

### Impact Classification

The stable initial labels are:

- `recommended_only`
- `range_widening`
- `range_tightening`
- `runtime_line_change`
- `current_runtime_excluded`

Multiple labels may apply.

`recommended_only` applies only when the compatible range is unchanged and only the recommended version changes.

Range changes are classified by the set of accepted versions, not by textual string differences:

- add `range_widening` when the proposed range accepts at least one version not accepted by the current range
- add `range_tightening` when the current range accepts at least one version not accepted by the proposed range

Partially overlapping ranges and disjoint ranges therefore receive both `range_widening` and `range_tightening`. Preview output should separately report whether the ranges overlap. No stable `range_shift` label is required in the first implementation.

`runtime_line_change` is based on the normalized `major.minor` line of the recommended version.

`current_runtime_excluded` means the runtime executing the command will be incompatible after the proposed update. It is independent from range labels and may combine with `recommended_only`, `runtime_line_change`, `range_widening`, or `range_tightening`.

Comparative labels require a valid and supported current contract. They are omitted when the current contract state is untrusted.

### Current State Behavior

The lifecycle distinguishes current runtime contract states:

| Current state | Preview behavior | Token | Apply |
| --- | --- | --- | --- |
| `compatible` | applicable preview | yes, unless no-op or structural blocker | allowed with authority, token, confirm |
| `incompatible` caused only by active runtime outside a valid old range | applicable preview through limited exception | yes, unless no-op or structural blocker | allowed with authority, token, confirm |
| `invalid_contract` | diagnostic-only preview of proposed values | no | blocked |
| `unsupported_contract` | diagnostic-only preview of proposed values | no | blocked |
| `missing_contract` | diagnostic-only preview of proposed values | no | blocked |
| `legacy_undeclared` | diagnostic-only preview of proposed values | no | blocked |

For untrusted states, preview may validate and normalize the proposed `requires` and `recommended` values and may report whether the active runtime would satisfy the proposed range as a hypothetical diagnostic. It shall not produce an applicable token, `apply_allowed: true`, an apply command, a mutation plan, or transition impact labels.

The result shall identify the separate workflow required before update:

- `invalid_contract`: contract repair
- `unsupported_contract`: contract schema migration
- `missing_contract`: contract recovery
- `legacy_undeclared`: contract adoption

Those workflows remain outside PROP-095.

### Preview

`p2p runtime contract preview` remains executable as read-only diagnostics without requiring project-owner authority.

Preview shall report:

- current and proposed `requires`
- current and proposed `recommended`
- normalized proposed values
- active runtime version
- proposed contract validation findings
- whether `recommended` satisfies `requires`
- impact labels when the current state can be trusted
- active-runtime compatibility after update
- setup-guide state and planned action
- release availability status
- files planned for mutation
- reason requirement
- whether authority is required for apply
- whether the current actor can be resolved
- whether the current actor appears authorized
- whether apply would currently be blocked for authority reasons
- `expected_state_token` when an applicable update can later be applied

Lack of authority shall not invalidate or prevent preview. This allows agents and non-owner collaborators to prepare a complete change request for an authorized owner.

Preview shall not:

- consume consent receipts
- mutate permission, governance, audit, project, token, or environment state
- treat the expected-state token as authorization
- expose unnecessary sensitive permission details
- return an applicable token for invalid proposals, untrusted current contracts, unmanaged setup guides, structural apply blockers, or no-op updates

### Apply

`p2p runtime contract apply` is the only mutating command.

It requires:

- the same proposed `requires` and `recommended` values used during preview
- the same structured reason and optional linked decision used during preview
- a valid `expected_state_token`
- current owner or permission authority
- explicit `--confirm`

`apply` shall:

1. re-read protected project state
2. revalidate the proposed contract
3. recalculate impact
4. recompute the expected-state token
5. verify current authority
6. require explicit confirmation
7. abort without mutation if state or proposed values do not match the preview
8. build the proposed runtime contract and setup guide in memory
9. prepare all required outputs before activating the new contract
10. perform the coordinated write

The authority check returned by preview is advisory only. `apply` shall always perform a fresh and binding authority check.

### Expected-State Token

The first implementation uses a deterministic stateless expected-state token.

The token is an optimistic-concurrency and proposal-binding mechanism. It is not:

- proof of owner or permission authority
- explicit confirmation
- a consent receipt
- an audit record
- a secret bearer capability

`preview` calculates and returns the token without persisting project, governance, audit, consent, or token-lifecycle state. `apply` reconstructs the same canonical input from current project state and supplied proposal values and proceeds only when the recalculated token matches the supplied token.

The versioned token input shall bind at least:

- operation identifier
- token-format version
- exact current runtime-contract content or digest
- exact managed setup-guide content, absence state, or unmanaged state
- relevant required-contract and managed-file marker state
- normalized proposed `requires` and `recommended`
- structured reason
- any linked decision
- impact-classification algorithm version
- calculated impact labels

A token mismatch fails as `stale_preview` without modifying files.

Tokens are not persisted, consumed, marked as used, given expiry, or bound to an actor in the first implementation. Reuse of the same token for identical state and proposal is acceptable because authority and confirmation are independently checked during every apply operation.

Single-use, expiry, actor binding, or persistent operation-intent semantics may be added later through PROP-066 consent or another explicit governed operation lifecycle.

### Authority, Decision Link, Reason, And Audit

Runtime contract updates are owner-controlled governed operations, but the first implementation shall not require a linked P2P proposal or decision.

Owner authority, explicit confirmation, stale-preview protection, and a structured reason are sufficient for execution.

The command may optionally link an existing P2P decision for traceability. It shall not create one automatically and shall not block execution solely because no decision is linked. A future project policy may require an accepted decision for selected project-level impacts, especially `runtime_line_change` and `range_tightening`. `current_runtime_excluded` alone shall not trigger that policy because it also describes the local execution environment.

A structured reason is mandatory when any of these labels apply:

- `range_tightening`
- `runtime_line_change`
- `current_runtime_excluded`

A reason is normally optional for:

- `recommended_only`
- pure `range_widening`

If a generic governed-change audit primitive exists, PROP-095 should reuse it. PROP-095 does not introduce a runtime-specific audit file. When no generic audit primitive exists, historical audit remains Git or external workflow and output shall report:

```text
reason_persisted: false
audit_mode: external
```

If a generic governed audit write is part of the same authorized operation, it must complete before the final runtime-contract replacement or participate in the coordinated write procedure.

### Setup Guide Handling

`P2P-SETUP.md` is derivative guidance generated from the runtime contract.

The first implementation handles setup-guide states as follows:

| Setup guide state | Preview | Apply |
| --- | --- | --- |
| missing | planned action `generate` | generate managed guide |
| managed aligned | planned action `regenerate` when contract changes | regenerate managed guide |
| managed drifted | planned action `regenerate`, `drift_repair: true` | regenerate managed guide during real contract update |
| present unmanaged | `preview_blocked`, `blocked_reason: unmanaged_setup_guide` | always blocked |

When `P2P-SETUP.md` contains the stable managed marker but its generated content has drifted, PROP-095 may repair that drift only as a side effect of a real runtime contract update. Preview shall report:

- `setup_guide_state: managed_drifted`
- `setup_guide_action: regenerate`
- `drift_repair: true`
- the managed file among planned file changes
- that the drift will be replaced by deterministic content rendered from the proposed runtime contract

Managed-guide drift is a repair side effect. It shall not by itself add a runtime-contract impact label or require a structured reason.

If `requires` and `recommended` are unchanged and the only difference is setup-guide drift, PROP-095 reports `no_change` plus a drift finding and performs no repair-only mutation. Repair-only belongs to a separate command.

When `P2P-SETUP.md` exists without the stable P2P-managed marker, apply shall always stop before mutation. No `--replace-unmanaged-setup-guide` flag is provided. PROP-095 shall not overwrite, adopt, merge, rename, back up, or replace user-owned setup documentation.

An unmanaged setup guide preview may validate the proposed contract but shall not return an applicable expected-state token.

### Coordinated Write

`.p2p/project/runtime.yml` remains the source of truth. `P2P-SETUP.md` remains derivative.

Confirmed apply shall:

1. verify token, authority, confirmation, and reason requirements
2. validate the proposed runtime contract
3. render the managed setup guide from the same proposed data
4. prepare all required contents in memory
5. prepare any generic governed audit mutation that belongs to the same operation
6. write temporary replacement files
7. replace `P2P-SETUP.md`
8. complete any coordinated accessory mutation that must occur before contract activation
9. replace `.p2p/project/runtime.yml` last
10. perform only narrowly scoped verification of the exact artifacts just written
11. return a structured final result

If setup guide replacement fails, `runtime.yml` must remain unchanged. If `runtime.yml` replacement fails after setup guide replacement, the command reports partial failure and leaves `runtime.yml` as source of truth; PROP-084 validation detects any resulting guide drift. PROP-095 does not claim crash-proof transactional semantics across files.

If the setup guide changes after preview, apply fails as `stale_preview` without mutation. If the managed marker is removed after preview, apply fails as `unmanaged_setup_guide`.

### Active Runtime Exclusion After Apply

The operation may successfully update the contract to one that excludes the active runtime.

When the new contract causes the active runtime to fall outside the compatible range, apply shall complete only the already authorized coordinated update. After the new `runtime.yml` is in effect, apply shall not perform further governed mutations, including:

- registry or index refresh
- proposal, contribution, change, work, or governance writes
- synchronization or managed-branch updates
- migration or reconciliation
- audit writes not already included in the coordinated operation
- Git commit, branch, push, or pull-request automation

The command may perform narrowly scoped read-only verification of the exact artifacts it just wrote, such as re-reading bytes or checking expected digests. It shall not automatically invoke broad project validation or other operations that traverse unrelated governed state after the active runtime has become incompatible.

The final result shall report:

- contract update succeeded
- active runtime is now incompatible
- subsequent governed writes are blocked
- no post-update governed mutation was performed
- full project validation is deferred until a compatible runtime is used
- recommended next action and `P2P-SETUP.md` guidance

### Release Availability

PROP-095 always validates the proposed runtime contract syntactically and semantically.

The first implementation shall not require network access, package resolution, installation, or remote release lookup in order to update the contract.

When trusted official release metadata is already available locally or packaged with P2P Engine, preview and apply may use it to report:

```text
release_availability: verified_available
```

When no sufficiently authoritative metadata is available, an otherwise valid update may proceed with:

```text
release_availability: unverified
```

`unverified` is a warning, not a contract validation failure. Absence from incomplete, stale, or optional local metadata shall not be treated as proof that a release does not exist. A blocking `verified_unavailable` state may be introduced later only if P2P gains access to an authoritative complete release catalog with defined freshness semantics.

PROP-080 metadata may enrich availability diagnostics but is not a blocking dependency for PROP-095.

## Alternatives

- Manual edit plus validation. Rejected because it bypasses coordinated setup-guide regeneration, preview, authority checks, stale-preview protection, and agent-safe outputs.
- Single `update` command with mode-dependent flags. Rejected for the first implementation because it makes read-only and mutating behavior depend on flag combinations and is harder to explain, test, and permission.
- Separate `preview` and `apply` commands. Selected because command names communicate risk: preview never mutates; apply is the only mutating path.
- Interactive single-process wrapper. Deferred. It may be added later only as a convenience wrapper over the same preview/apply services.
- Mandatory linked proposal or decision. Rejected for the first implementation because it creates disproportionate governance overhead and can create circular write-gate problems.
- Optional linked decision. Selected for traceability without blocking autonomous owner-authorized maintenance.
- Persisted or single-use preview token. Rejected for the first implementation because preview must remain read-only and token lifecycle belongs better to consent or future operation-intent primitives.
- Stateless deterministic token. Selected because it protects against stale state and proposal changes without persisting state.
- Automatic runtime installation or upgrade. Rejected because it conflates project policy with local environment management.
- Blocking release availability lookup. Rejected because contract update must remain deterministic and local; release metadata can enrich diagnostics but not gate the update.
- Replacing unmanaged `P2P-SETUP.md`. Rejected because it would decide the fate of user-owned documentation and requires a separate adoption or replacement capability.
- Blocking on managed setup-guide drift. Rejected for real contract updates because managed generated drift can be repaired as part of the coordinated operation.
- Adding a `range_shift` label. Rejected because `range_widening` plus `range_tightening` expresses both effects precisely.

## Impacts

- PROP-084: PROP-095 builds on runtime contract parsing, status states, setup guide generation, drift detection, and the governed-write gate. It adds the governed update path for the contract itself.
- PROP-084 write-path inventory: the new apply command must be classified as a guarded runtime-contract update exception, allowed only for compatible state or valid incompatible old range state.
- PROP-078: runtime installation, upgrade, downgrade, and environment reconciliation remain outside PROP-095.
- PROP-080: release metadata may enrich diagnostics but is not required.
- PROP-066: future MCP mutation or single-use/actor-bound operation semantics should use consent receipts instead of changing expected-state token semantics.
- Public CLI: adds `p2p runtime contract preview` and `p2p runtime contract apply`.
- Public JSON: preview and final result require stable fields for current/proposed contracts, status, impacts, setup guide state, release availability, token, authority, reason, files, and blocker diagnostics.
- Generated setup guidance: managed `P2P-SETUP.md` is regenerated from the proposed contract during real updates.
- Collaboration workflow: non-owners and agents can preview and hand a token to an owner; owners apply after independent authority verification.
- Post-update behavior: if the active runtime becomes incompatible, broad validation and further governed writes are deferred until a compatible runtime is used.

## Risks

- Backdoor around the write gate. Mitigation: allow the exception only for compatible state or valid supported incompatible state caused solely by active runtime outside old range.
- Hidden environment mutation. Mitigation: prohibit installation, package resolution, remote lookup, and environment reconciliation.
- Confusing token with authorization. Mitigation: define token as stateless optimistic concurrency only; authority and confirmation are checked independently during apply.
- Agent executes unseen mutation. Mitigation: separate preview and apply commands; apply requires token, authority, and explicit confirmation.
- Owner authority confusion. Mitigation: preview is advisory; apply repeats fresh binding authority check.
- Overwriting human documentation. Mitigation: unmanaged `P2P-SETUP.md` blocks apply and no override flag exists in the first implementation.
- Managed setup-guide drift persists after update. Mitigation: regenerate managed drifted guide as part of real contract update and bind drifted bytes in the token.
- Repair-only mutation hidden as no-op. Mitigation: no-op reports drift finding but does not repair; repair-only is separate.
- Partial file update. Mitigation: prepare in memory, replace setup guide before runtime contract, write runtime contract last, and report handled failures.
- Audit after incompatible contract activation. Mitigation: any audit write in the same operation must happen before final `runtime.yml` replacement or participate in coordinated write.
- Release availability false negatives. Mitigation: best-effort local verified availability only; `unverified` is non-blocking.
- Ambiguous range classification. Mitigation: compare accepted version sets under supported grammar and allow both widening and tightening.
- Post-update side effects with incompatible runtime. Mitigation: after final contract replacement, no further governed mutations occur.

## Assumptions

- PROP-084 provides runtime contract status, setup-guide marker handling, setup-guide rendering, drift detection, and governed-write gate behavior.
- The first implementation can parse and compare `==VERSION` and `>=LOWER,<UPPER` ranges under PEP 440-compatible semantics.
- Existing project owner or permission authority can be checked for apply.
- Read-only preview can evaluate authority enough to report whether apply appears blocked without exposing sensitive permission details.
- Managed `P2P-SETUP.md` has a stable marker format.
- Generic governed audit may exist; if not, Git or external workflow remains the audit trail and the result reports that explicitly.
- Non-owner agents may share preview output and token with an owner.
- The active runtime can perform the limited update exception when the old contract is valid, supported, and only excludes the active runtime by version range.
- Release availability metadata, if consumed, is local or packaged and official enough to support a positive `verified_available` diagnostic.
- Full project validation after an incompatible update is performed later with a compatible runtime.

## Resolved Questions

- Q001: Structured reasons are supported; required for tightening, runtime-line changes, and active-runtime exclusion; audit uses generic mechanisms if available, otherwise Git/external audit is reported.
- Q002: Apply is owner-controlled; authority means supported owner role or permission authority plus explicit confirmation; future MCP mutation must use PROP-066 consent.
- Q003: JSON preview and result output are required for agent workflows.
- Q004: Stable impact labels are `recommended_only`, `range_widening`, `range_tightening`, `runtime_line_change`, and `current_runtime_excluded`.
- Q005: Linked P2P proposal or decision is optional, not mandatory; future policy may require it for selected impacts.
- Q006: Runtime contract updates use a logically two-phase workflow.
- Q007: Release availability is best-effort local diagnostic; `unverified` is non-blocking; no network, install, or resolver behavior.
- Q008: First implementation exposes separate `preview` and `apply` commands.
- Q009: Preview does not require owner authority; apply does.
- Q010: Unmanaged `P2P-SETUP.md` blocks apply absolutely in the first implementation.
- Q011: Untrusted current contract states get diagnostic-only preview and no applicable token or apply.
- Q012: Expected-state token is deterministic and stateless.
- Q013: Recommended-only updates are valid when the new recommended version satisfies the compatible range.
- Q014: Managed setup-guide drift is regenerated during a real contract update, but drift alone is not repaired by no-op.
- Q015: Partially overlapping and disjoint ranges receive both widening and tightening labels when they add and remove accepted versions.
- Q016: If the new contract excludes the active runtime, apply performs no further governed mutations after final `runtime.yml` replacement.

## Acceptance Criteria

### Command Surface

- WHEN a user runs `p2p runtime contract preview`, THE SYSTEM SHALL perform a read-only preview and SHALL NOT modify project, governance, audit, consent, token, or environment state.
- WHEN a user runs `p2p runtime contract apply`, THE SYSTEM SHALL treat it as the only mutating runtime contract update command.
- THE FIRST IMPLEMENTATION SHALL NOT provide a single-command preview-and-apply mode.
- WHEN preview output is requested as JSON, THE SYSTEM SHALL include the stable machine-readable fields required by agents.
- WHEN apply output is requested as JSON, THE SYSTEM SHALL include status, files changed, final compatibility, release availability, audit mode, and blocker fields when applicable.

### Proposed Contract Validation

- WHEN proposed `requires` is outside the supported grammar, THE SYSTEM SHALL fail closed without producing an applicable token.
- WHEN proposed `recommended` does not satisfy proposed `requires`, THE SYSTEM SHALL fail closed without producing an applicable token.
- WHEN proposed `requires` and `recommended` are unchanged, THE SYSTEM SHALL return `no_change`, no applicable token, no apply operation, no reason requirement, no consent consumption, and no file changes.
- WHEN only `recommended` changes and it satisfies unchanged `requires`, THE SYSTEM SHALL classify the update as `recommended_only` unless other independent labels also apply.

### Impact Classification

- WHEN proposed range accepts versions not accepted by the current range, THE SYSTEM SHALL add `range_widening`.
- WHEN current range accepts versions not accepted by the proposed range, THE SYSTEM SHALL add `range_tightening`.
- WHEN ranges partially overlap but neither is a subset of the other, THE SYSTEM SHALL add both `range_widening` and `range_tightening`.
- WHEN ranges are disjoint, THE SYSTEM SHALL add both `range_widening` and `range_tightening` and report that ranges do not overlap.
- WHEN the normalized recommended `major.minor` line changes, THE SYSTEM SHALL add `runtime_line_change`.
- WHEN the active runtime does not satisfy the proposed range during an applicable transition, THE SYSTEM SHALL add `current_runtime_excluded`.
- WHEN `range_tightening`, `runtime_line_change`, or `current_runtime_excluded` is present, THE SYSTEM SHALL require a structured reason for apply.

### Current State Handling

- WHEN current runtime status is `compatible`, THE SYSTEM SHALL allow applicable preview and apply subject to validation, structural blockers, token, authority, reason, and confirmation.
- WHEN current runtime status is `incompatible` only because the active runtime is outside a valid, supported old range, THE SYSTEM SHALL allow the limited update exception subject to the same checks.
- WHEN current runtime status is `invalid_contract`, `unsupported_contract`, `missing_contract`, or `legacy_undeclared`, THE SYSTEM SHALL return diagnostic-only preview, no applicable token, no apply plan, and blocked apply.
- WHEN current state is untrusted, THE SYSTEM MAY validate proposed values and MAY report whether the active runtime would satisfy the proposed range as hypothetical diagnostics, but SHALL NOT emit transition impact labels.

### Authority And Governance

- WHEN preview is run by a non-owner or unresolved actor, THE SYSTEM SHALL still produce read-only diagnostics and report whether apply appears blocked for authority reasons.
- WHEN apply is run, THE SYSTEM SHALL perform a fresh binding authority check and SHALL NOT rely on preview's authority assessment.
- WHEN apply lacks owner or permission authority, THE SYSTEM SHALL fail without modifying files.
- WHEN apply lacks explicit `--confirm`, THE SYSTEM SHALL fail without modifying files.
- WHEN a linked decision is omitted, THE SYSTEM SHALL NOT block solely for that reason.
- WHEN a linked decision is provided, THE SYSTEM SHALL bind it into the expected-state token and report it in output.

### Expected-State Token

- WHEN preview is applicable, THE SYSTEM SHALL return a deterministic stateless expected-state token.
- WHEN apply is invoked, THE SYSTEM SHALL recompute the token from current state and supplied proposal values before mutation.
- WHEN the supplied token does not match, THE SYSTEM SHALL fail as `stale_preview` with no file changes.
- THE TOKEN SHALL NOT be treated as authority, confirmation, consent, audit, secret bearer capability, or persisted operation intent.
- THE TOKEN SHALL NOT be persisted, consumed, marked used, expired, or actor-bound in the first implementation.
- WHEN the proposed contract is invalid, current contract is untrusted, setup guide is unmanaged, another structural blocker exists, or the update is no-op, THE SYSTEM SHALL NOT return an applicable token.

### Setup Guide

- WHEN `P2P-SETUP.md` is missing and update is otherwise applicable, THE SYSTEM SHALL plan and generate a managed setup guide.
- WHEN `P2P-SETUP.md` is managed and aligned, THE SYSTEM SHALL regenerate it from the proposed contract during a real update.
- WHEN `P2P-SETUP.md` is managed and drifted, THE SYSTEM SHALL report drift, bind current drifted content in the token, and regenerate it during a real update.
- WHEN `P2P-SETUP.md` is present but unmanaged, THE SYSTEM SHALL block apply before mutation and SHALL NOT produce an applicable token.
- THE SYSTEM SHALL NOT provide an override flag to replace unmanaged setup guides in the first implementation.
- WHEN only managed setup-guide drift exists and contract values are unchanged, THE SYSTEM SHALL report `no_change` plus drift finding and SHALL NOT perform repair-only mutation.

### Coordinated Write

- BEFORE the first write, THE SYSTEM SHALL validate token, authority, confirmation, reason, contract, and setup-guide plan.
- THE SYSTEM SHALL prepare runtime contract and setup guide content in memory before writing.
- THE SYSTEM SHALL replace managed `P2P-SETUP.md` before replacing `.p2p/project/runtime.yml`.
- THE SYSTEM SHALL replace `.p2p/project/runtime.yml` last.
- WHEN setup guide replacement fails, THE SYSTEM SHALL leave `.p2p/project/runtime.yml` unchanged.
- WHEN a handled failure occurs, THE SYSTEM SHALL report the failure and files changed without claiming crash-proof transaction semantics.

### Active Runtime Exclusion

- WHEN the new contract excludes the active runtime, THE SYSTEM SHALL allow the update if all apply requirements are satisfied.
- WHEN the final runtime contract has been replaced and the active runtime is now incompatible, THE SYSTEM SHALL perform no further governed mutations.
- THE SYSTEM SHALL NOT automatically refresh registries, write proposal/contribution/change/work/governance state, sync, migrate, reconcile, audit after activation, or invoke Git automation after the active runtime becomes incompatible.
- THE SYSTEM MAY perform narrowly scoped read-only verification of the files just written.
- THE RESULT SHALL report that subsequent governed writes are blocked and full project validation is deferred until a compatible runtime is used.

### Release Availability

- WHEN trusted official local or packaged release metadata confirms the proposed recommended version, THE SYSTEM MAY report `release_availability: verified_available`.
- WHEN no authoritative local metadata is available, THE SYSTEM SHALL allow an otherwise valid update with `release_availability: unverified`.
- THE SYSTEM SHALL NOT query GitHub, download release metadata, resolve wheels, or install anything.
- THE SYSTEM SHALL NOT treat absence from incomplete, stale, or optional local metadata as proof that a release does not exist.

### Scope Protection

- PROP-095 SHALL NOT implement runtime installation, upgrade, downgrade, selection, or environment reconciliation.
- PROP-095 SHALL NOT implement unmanaged setup-guide adoption or replacement.
- PROP-095 SHALL NOT implement invalid contract repair, unsupported schema migration, missing contract recovery, or legacy contract adoption.
- PROP-095 SHALL NOT add MCP mutation in the first implementation.
- PROP-095 SHALL NOT create commits, branches, pull requests, pushes, merges, or provider handoffs.

## Decision

Pending.
