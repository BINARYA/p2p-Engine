# Exploration - Project Readiness Convergence Workflow

## Observed Functional Gap

The current project-readiness path is a read-only diagnosis. It identifies incomplete required sections, declared proposal coverage and heuristic suggestions, but it does not own a durable convergence session. The repository exposes three incomplete definition sections, only one broad generated question, 88 intentionally legacy unmapped proposals and no managed next action focused on definition convergence.

## Code-Audit Findings

The existing building blocks require explicit adaptation:

- project-definition preview/apply validates and writes only `definition.yml`; it cannot be followed by a separate question write while claiming atomic convergence;
- `AtomicMutationWriter` already supports multiple targets and should be the single commit boundary;
- mutation preview tokens are deterministic but do not currently define actor-bound identity, expiry, consumption or exact committed retry;
- proposal-question operations accept caller-provided actor/source and therefore are a semantic reference, not an authority implementation that can be copied unchanged;
- workspace schema status distinguishes current/ahead/legacy but treats declared older versions as incomplete rather than explicitly upgradeable;
- the migration registry carries transition metadata, while the compatibility planner still renders legacy-to-v1 bootstrap operations for the selected path instead of dispatching transition-specific handlers;
- project-definition legacy questions have section-local ids and no complete lifecycle history;
- decision context classifies proposal questions as quality metadata and project definition as canonical semantic state, but has no project-question source kind.

## Required State Boundaries

Project question state owns interview lifecycle, answers, revisions and apply references. Project definition owns only applied content. Workspace schema owns whether the dedicated question artifact is valid. Decision context may retrieve pending question evidence but cannot activate it as a decision or definition constraint. Next actions, progress and freshness consume one convergence result and do not reproduce ranking or authority logic.

## Required Migration Boundary

Schema v2 cannot be implemented by adding only a registry row. The migration planner must dispatch adjacent transition handlers over candidate overlays. The v1-to-v2 handler owns question-state creation, deterministic legacy-question mapping, any explicit removal or compatibility normalization of definition open questions, schema history and validation. It must not rerun v0-to-v1 domain, permission, metadata or vertical bootstrap.

Legacy migration preserves every valid open question exactly once, creates no answer or applied state, generates declared/fallback questions for still-incomplete sections with no legacy question, and blocks ambiguous lossy mappings. A missing legacy question is not evidence of completed interview work.

## Required Mutation Boundary

Convergence preview renders both definition and question candidates from one immutable snapshot. Apply binds actor and both candidates to all canonical preimages and commits both through one durable transaction. Exact retry after commit returns `already_applied`; reuse against different state is rejected. Audit timestamps are excluded from semantic identity.

## Required Lifecycle Boundary

Steady states are `to_answer`, `answered`, `applied`, `deferred`, `muted`, `retired` and `superseded`. Reopen is an audited transition to `to_answer`. Wording-only changes preserve identity and state; semantic target changes supersede. Vertical drift invalidates previews and requires explicit deterministic reconciliation without copying answers.

## Delivery Shape

1. Immutable snapshot, typed gaps and priority policy.
2. Version-aware schema status and transition-handler migration architecture.
3. Project-question artifact, identity and v1-to-v2 mapping.
4. Question selection, lifecycle, operation authority and vertical reconciliation.
5. Multi-target preview/apply and durable rollback/recovery.
6. Exact retry, concurrency and semantic-hash hardening.
7. Next actions, progress, freshness and decision-context integration.
8. Bounded CLI, snapshot-bound pagination and MCP read parity.
9. Compatibility matrix, adversarial fixtures and repository pilot.

## Success Boundary

The feature succeeds when an owner can move from a reported project gap to an auditable applied update or explicit defer/mute outcome without manual `.p2p` edits; when a v1 workspace can be inspected, planned and upgraded to v2 without replaying unrelated bootstrap behavior; and when no pending answer, stale question, replayed token or partial write can be mistaken for applied project truth.
