# Project Runtime Contract Update Lifecycle

## Provenance

- Proposal: PROP-095
- Source: .p2p/proposals/PROP-095-project-runtime-contract-upgrade-lifecycle

## Problem

PROP-084 allows a P2P-managed project to declare the P2P Engine runtime range it trusts, recommend a runtime version to collaborators, expose compatibility diagnostics, and block governed writes when the declared runtime contract cannot be trusted.

The project still lacks an explicit lifecycle for changing that contract after initialization.

An owner may intentionally move a project to another P2P Engine version or runtime line. Editing `.p2p/project/runtime.yml` manually is unsafe because it bypasses validation, can leave generated setup guidance stale, provides no deterministic preview of collaborator impact, and does not define how the PROP-084 governed-write gate may be crossed when the active runtime is outside the old compatible range.

The project-level decision to change the required runtime must remain distinct from installing, upgrading, downgrading, or reconciling the runtime installed on a collaborator's machine.

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

## Decision

# Decision - PROP-095

## Status

`accepted`

## Outcome

accepted

## Event Type

accepted

## Effective State

accepted

## Reason

Owner accepts the runtime contract update lifecycle after readiness reached decision_ready with all Q001-Q016 decisions applied and no missing evidence.

## Date

2026-07-13

## Approver

mrjungle

## Owner

mrjungle

## Ledger Head

PDE-72b6ee4f2bee15dc3c351628

## Decision Fingerprint

d17f5f4ade0dd04f0fd3e15570e68332029d78029fbc6958a251dbc651f889fa

## Lineage

None.

## Canonical Source

decision-events.yml
