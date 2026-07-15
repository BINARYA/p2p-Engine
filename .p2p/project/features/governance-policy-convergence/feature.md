# Governance Policy Convergence

## Provenance

- Proposal: PROP-091
- Source: .p2p/proposals/PROP-091-governance-policy-convergence

## Problem

P2P Engine already has governance-aware artifacts and helper utilities, but they
do not yet form a coherent operational governance policy. The project can store
`governance.yml`, `roles.yml`, `permissions.yml`, choices, votes, decision
precedents, explicit blockers, and owner-controlled decisions, but there is no
single structured evaluation that answers these questions before a decision:

- who is attempting to decide;
- whether that actor is allowed to decide;
- what target is being decided;
- which governance mode applies;
- whether the governance state is valid and readable;
- how the proposed decision relates to votes, blockers, and precedents;
- whether the decision can proceed normally, requires rationale, requires owner
  override, or must be blocked.

Without this layer, governance artifacts remain useful as audit records but weak
as decision support. Agents and external clients can see fragments of governance
state, yet they cannot consume a stable preflight contract that explains the
decision context in a deterministic way.

## Proposal

Introduce a Governance Policy Convergence layer.

The layer should evaluate governance state before finalization and return a
stable, versioned, deterministic, machine-readable preflight structure. The
preflight output is not a decision record. It represents a proposed selection
and the governance evaluation before the final owner decision.

The initial preflight contract should include:

- `schema_version`;
- `target`;
- `governance`;
- `actor`;
- `selection`;
- `result`;
- `blocking_errors`;
- `warnings`;
- `vote_summary`;
- `blockers`;
- `precedents`.

The `result.status` field should summarize one of:

- `ready`;
- `requires_rationale`;
- `requires_owner_override`;
- `blocked`.

Blocking errors and warnings should be structured objects with stable
machine-readable codes, human-readable messages, override or rationale metadata
when relevant, and optional references.

### Authority And Votes

`owner_decides` remains the operational default. The owner remains the final
decision maker. Votes are transparency and decision evidence. A proposed owner
decision that conflicts with the recorded vote winner should produce a strong
warning and make the contrast explicit, but it should not block finalization and
should not require a mandatory override reason in the current model.

### Actor And Role Resolution

Use a soft migration path:

- `permissions.yml` is the primary actor and role source whenever present;
- `governance/roles.yml` remains legacy/display/fallback;
- vote and preflight flows move toward actor-based input;
- when an actor exists in `permissions.yml`, the effective role is inferred from
  that file;
- legacy role fields may be tolerated during transition;
- mismatches between a supplied legacy role and the inferred role produce
  warnings.

### Precedents

Core precedent lookup is explicit and deterministic. The core considers
precedents related only when links are declared in versioned artifacts through
stable identifiers or explicit tags, such as `related_precedents`,
`applies_to.proposal_ids`, `applies_to.choice_ids`, or `governance_tags`.

The core must not infer precedent relationships from titles, keywords, fuzzy
matching, semantic similarity, embeddings, or AI-based search. Intermediary
tools may suggest links, but the core only considers those links after they are
written back as explicit artifact relations.

### Blocking And Warning Semantics

Warnings are valid governance signals that may influence the owner decision but
do not prevent finalization by themselves.

Blocking errors are conditions where the core cannot reliably establish the
decision actor, decision target, governance mode, or integrity of governance
state.

Initial non-overrideable blocking errors include:

- missing, unknown, or unauthorized decision actor;
- invalid required permissions or governance context;
- missing target proposal or choice;
- structurally invalid target artifacts;
- unsupported governance mode;
- structurally invalid governance artifacts;
- structurally invalid vote or precedent artifacts when present.

An explicit unresolved blocker attached to the target proposal or choice blocks
normal finalization. It may be overridden only by an authorized owner with
explicit rationale recorded in the final decision record.

Vote disagreement, ties, related precedents, reopened decisions, open concerns
not marked as blockers, weak consensus, no votes, and no related precedents are
warnings or neutral signals, not automatic blockers.

### MCP Phase 1

MCP phase 1 exposes governance visibility, validation, vote summaries,
deterministic precedent lookup, and governance preflight evaluation. It does not
expose governance mutation or final decision execution.

Included phase-1 tools:

- `p2p_governance_status`;
- `p2p_governance_validate`;
- `p2p_choice_governance_preflight`;
- `p2p_vote_status`;
- `p2p_precedent_search`.

Deferred tools:

- `p2p_vote_record`;
- `p2p_precedent_record`;
- `p2p_choice_decide`.

`p2p_choice_governance_preflight` may evaluate a proposed selection for a given
actor and target, but it must not persist decision records, mutate votes, create
precedents, or finalize choices/proposals.

## Decision

# Decision - PROP-091

## Status

`accepted`

## Outcome

accepted

## Reason

Accepted by owner after guided refinement. The proposal is decision-ready with readiness score 100, high confidence, no failed gates, no missing artifacts, no suggested next actions, and clean validation. It defines Governance Policy Convergence with owner_decides as default, deterministic preflight, explicit precedent lookup, warning/blocking semantics, actor-role migration, and read-only/low-risk MCP phase 1.

## Date

2026-07-02

## Approver

local
