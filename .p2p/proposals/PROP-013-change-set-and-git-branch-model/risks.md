# Risks - PROP-013

## R1 - Hidden Git operations surprise users

Risk:

If P2P creates commits, branches, merges, or tags silently, users may be surprised by repository state changes.

Mitigation:

Start with metadata-only policy. Add managed Git operations gradually. Expose internal operations through:

```text
p2p status --verbose
p2p doctor
p2p internals git-policy
```

Additional controls:

- Default MVP mode is `metadata_only`.
- No automatic commit, branch, merge, or tag without explicit opt-in.
- Normal output mentions that Git is managed, but does not expose low-level details.
- Verbose output shows planned/internal Git operations.
- Doctor/debug output explains repository state and policy decisions.

## R2 - Git policy becomes arbitrary

Risk:

The system may inconsistently decide when to create branches/commits/tags.

Mitigation:

Use explicit `git_policy.yml` criteria derived from impact/conflict data.

The policy decision should be explainable:

```text
Policy result:
  internal_branch: recommended

Reasons:
  - proposal touches public CLI behavior
  - proposal modifies governance/project artifacts
  - proposal has conflict relation CONFLICT-002
```

## R3 - Too many change sets

Risk:

Every accepted proposal may become a separate change set, causing fragmentation.

Mitigation:

Allow one change set to include multiple accepted proposals and decisions.

## R4 - Git history becomes the only memory

Risk:

Important decision context may live only in branch/PR history.

Mitigation:

Persist proposal, decision, impact, conflict, and change-set metadata in `.p2p/`.

## R5 - AI bypasses P2P Engine

Risk:

An AI agent may manipulate Git directly, bypassing proposal/change/decision artifacts.

Mitigation:

P2P skills and agent instructions must require agents to use P2P CLI commands by default. Direct Git should be limited to debug/repair flows.

## R6 - Git adapter becomes too complex too early

Risk:

Building a full Git adapter may distract from the core proposal/change/project workflow.

Mitigation:

Introduce the adapter in layers:

```text
Layer 1 - metadata only
  record intended Git policy and planned operations

Layer 2 - read-only diagnostics
  inspect branch/status/log without changing Git state

Layer 3 - safe write operations
  explicit commits/tags behind opt-in

Layer 4 - managed branches and merges
  only after policy and recovery tooling are mature
```

## R7 - Managed Git creates recovery burden

Risk:

If P2P performs Git operations, users need a way to understand and recover from failed operations.

Mitigation:

Before enabling write operations, implement:

```text
p2p doctor
p2p status --verbose
p2p internals git-log
p2p internals git-policy
```

The first adapter implementation should be transactional where possible and should never hide failures.

## R8 - Non-technical UX hides too much from technical users

Risk:

Hiding Git details by default may frustrate advanced users who need auditability and control.

Mitigation:

Expose details through progressive disclosure:

```text
normal
  P2P concepts only

verbose
  planned/internal Git operations

doctor/debug
  repository state, policy reasoning, repair hints
```
