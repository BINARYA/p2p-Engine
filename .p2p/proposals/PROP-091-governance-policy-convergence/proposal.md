# PROP-091 - Governance Policy Convergence

## Status

`accepted`

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

## Context

`PROP-008` delivered the technical and documental MVP for governance artifacts:
governance initialization, role files, proposal-local vote recording, decision
precedent storage, and SWOT prompt support. Later work added project choices,
choice blockers, permission identities, consent receipts, owner-controlled
decision boundaries, and MCP safety metadata.

The remaining production-grade gap is not a full democratic governance system.
The required next step is a convergence layer that makes existing governance
state readable, validable, deterministic, and useful to the owner before
finalization.

## Goals

- Keep `owner_decides` as the current operational default.
- Preserve owner authority as the final decision source for now.
- Make votes, blockers, and precedents transparent decision context rather than
  automatic decision makers.
- Introduce a deterministic governance preflight contract for proposed
  selections and decision attempts.
- Use `permissions.yml` as the primary actor and role source when available.
- Keep `governance/roles.yml` as a legacy, display, or fallback artifact during
  migration.
- Make vote disagreement, ties, related precedents, reopened decisions, weak
  consensus, and non-blocking concerns visible as warnings.
- Treat structural invalidity, unauthorized actors, unknown targets, unsupported
  governance modes, and corrupt governance artifacts as blocking errors.
- Treat explicit unresolved blockers as normal-flow blockers that can be
  overridden only by an authorized owner with recorded rationale.
- Expose first-phase MCP parity through read-only or low-risk governance status,
  validation, vote status, precedent lookup, and preflight tools.

## Non-Goals

- Do not implement a full democratic governance system.
- Do not introduce quorum, weighted voting, delegation, complex voting
  deadlines, or automatic vote enforcement.
- Do not make votes automatically accept, reject, or decide proposals or
  choices.
- Do not allow agents or MCP tools to bypass owner-controlled governance.
- Do not use fuzzy matching, semantic similarity, embeddings, title inference,
  keyword guessing, or AI search in the core precedent lookup.
- Do not expose MCP tools that mutate governance state or finalize decisions in
  phase 1.
- Do not remove compatibility for existing governance artifacts without a
  migration path.

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

## Acceptance Criteria

- Governance status reports configured mode, effective owner identities,
  artifact presence, warnings, and validation problems.
- Governance preflight emits a stable `schema_version`.
- Governance preflight output is deterministic for the same repository state
  and command input.
- Governance preflight distinguishes proposed `selection` from final decision
  records.
- Governance preflight includes actor resolution, resolved roles, capabilities,
  and `can_decide`.
- Governance preflight includes `result.status` with one of `ready`,
  `requires_rationale`, `requires_owner_override`, or `blocked`.
- Blocking errors and warnings use stable machine-readable codes.
- Vote summaries are included when vote data exists or is relevant.
- Vote disagreement with the selected option produces a warning, not a blocking
  error.
- Active explicit blockers are listed and block normal finalization.
- Owner override of explicit blockers requires rationale recorded in the final
  decision record.
- Explicit precedents and deterministic tag-declared matches are listed
  separately.
- Precedent lookup uses only explicit artifact relationships or declared tags.
- Project validation includes structural checks for `governance.yml`,
  `roles.yml`, `decision-precedents.yml`, and `votes.yml`.
- MCP phase 1 tools do not modify project artifacts, votes, precedents, choices,
  proposals, or decision records.
- MCP phase 1 exposes governance status, validation, choice preflight, vote
  status, and deterministic precedent lookup.

## Decision

Pending.
