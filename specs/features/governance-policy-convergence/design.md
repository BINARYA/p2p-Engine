# Design - Governance Policy Convergence

## Design Goals

This design implements `PROP-091` as a runtime governance coordination layer
while preserving existing public behavior.

The central design choice is to add a dedicated service-owned preflight
contract and keep CLI/MCP as presentation layers. This matches the current
P2PWorkspace direction: `P2PWorkspace` remains the compatibility facade, while
domain behavior lives behind cohesive services.

## Relevant Existing Code

- `src/p2p_engine/services/governance.py` owns basic governance status, vote
  recording/status, and precedent recording.
- `src/p2p_engine/services/choices.py` owns project choice lifecycle, choice
  details, selected options, and explicit blockers.
- `src/p2p_engine/services/permissions.py` owns `permissions.yml` identity and
  role handling.
- `src/p2p_engine/services/validation.py` owns repository validation findings.
- `src/p2p_engine/storage/filesystem.py` exposes `P2PWorkspace` facade
  delegation for services.
- `src/p2p_engine/cli_commands/governance.py` and
  `src/p2p_engine/cli_commands/choices.py` own current CLI wiring.
- `src/p2p_engine/mcp/catalog/*.py` and `src/p2p_engine/mcp/handlers/*.py` own
  MCP tool schemas and dispatch.

## Decisions

### D001 - Add A Governance Policy Service

Add `GovernancePolicyService` under `src/p2p_engine/services/` or extend the
existing governance service only if the resulting file remains cohesive.

Preferred placement: `src/p2p_engine/services/governance_policy.py`.

Rationale:

- preflight coordinates governance, choices, permissions, votes, blockers, and
  precedents;
- it is reused by service tests, CLI, MCP, and future governance workflows;
- it avoids adding application logic to CLI commands, MCP handlers, or
  `P2PWorkspace`.

Covers: R001-R019, R033, N001, N005.

### D002 - Keep Existing Write Operations Where They Are

Existing `record_vote`, `vote_status`, and `record_precedent` behavior can
remain compatible. This feature adds read-only governance policy/preflight
behavior around them rather than rewriting write paths first.

Rationale:

- reduces behavior drift risk;
- allows focused validation of new semantics;
- avoids combining broad refactor and behavior change.

Covers: R003, R026, R032, N002, N007, N008.

### D003 - Use Typed Result Models

Represent preflight data with dataclasses or equivalent structured models:

- `GovernancePreflightResult`
- `GovernanceTarget`
- `GovernanceContext`
- `ResolvedGovernanceActor`
- `GovernanceSelection`
- `GovernanceDecisionResult`
- `GovernanceDiagnostic`
- `VoteSummary`
- `ExplicitBlockerSummary`
- `PrecedentMatch`

Each model must serialize through existing `to_jsonable` or a local
service-owned conversion helper.

Rationale:

- keeps CLI/MCP from parsing text;
- gives stable test fields;
- gives future agents a clear contract.

Covers: R001-R002, R035, N004-N005.

### D004 - Use Stable Diagnostic Codes

Use stable diagnostic codes for warnings and blocking errors. Initial codes
should be specific enough for tests and clients, for example:

- `P2P_GOV_UNSUPPORTED_MODE`
- `P2P_GOV_UNKNOWN_ACTOR`
- `P2P_GOV_NON_OWNER_ACTOR`
- `P2P_GOV_INVALID_SELECTION`
- `P2P_GOV_ACTIVE_BLOCKER`
- `P2P_GOV_VOTE_CONFLICT`
- `P2P_GOV_VOTE_TIE`
- `P2P_GOV_LEGACY_ROLE_FALLBACK`
- `P2P_GOV_ROLE_MISMATCH`
- `P2P_GOV_MALFORMED_VOTES`
- `P2P_GOV_DUPLICATE_PRECEDENT`

Rationale:

- human text can evolve;
- CLI/MCP clients and tests need stable fields.

Covers: R011-R016, R020-R021, N004.

### D005 - Permissions First, Legacy Roles As Fallback

Actor resolution order:

1. read `.p2p/project/permissions.yml` when present;
2. resolve actor id using `PermissionsService.identity_slug`;
3. validate role/kind against existing permission constants;
4. only if `permissions.yml` is absent, use legacy governance roles as fallback
   evidence;
5. if both sources exist and disagree, return a warning and use
   `permissions.yml`.

Rationale:

- `permissions.yml` is already the structured project permission policy;
- legacy governance roles remain useful for old repositories and display.

Covers: R008-R012, R034.

### D006 - Treat Votes As Advisory Evidence

Vote data is never the final authority in `owner_decides` mode. The preflight
compares selected option against `VoteStatus` and reports:

- total votes;
- counts by option;
- winner if not tied;
- tied state;
- alignment: `aligned`, `conflicts`, `tied`, `no_votes`, or
  `not_applicable`.

Vote conflict and tie become warnings, not blockers.

Covers: R004-R007.

### D007 - Explicit Blockers Block Normal Finalization

For choice targets, load active blockers from `ChoiceLifecycleService.show`.
Active blockers produce blocking diagnostics. In owner-final governance mode,
the result must explicitly show whether the block is overrideable and whether a
rationale is required.

Malformed blocker artifacts are non-overrideable errors.

Covers: R013-R016.

### D008 - Deterministic Precedent Search

Precedent search reads `.p2p/governance/decision-precedents.yml` and matches
only explicit fields:

- precedent id requested by the caller;
- related proposal id;
- related choice id;
- declared tag.

No title similarity, fuzzy matching, embedding search, or LLM inference belongs
in the CLI/MCP core path. An external intermediary may propose related
precedents later, but it must persist explicit links before the core engine
treats them as matches.

Covers: R017-R019.

### D009 - Validation Integration

Extend `ValidationService` with governance artifact validation helpers for:

- `.p2p/governance/governance.yml`;
- `.p2p/governance/roles.yml`;
- `.p2p/governance/decision-precedents.yml`;
- `.p2p/proposals/*/votes.yml`.

Missing optional governance artifacts should not fail validation. Invalid
present artifacts should produce stable diagnostics.

Covers: R020-R021, R034.

### D010 - CLI Additive Surfaces

Add CLI behavior additively:

- preserve `p2p governance status` default text;
- add `p2p governance validate`;
- add `p2p choice governance-preflight CHOICE-XXX --option <option> --actor
  <actor>`;
- keep `p2p vote status` and optionally add machine output;
- add `p2p precedent search` for deterministic precedent lookup.

Machine formats should be added only where they are part of the public
contract for this feature. Text output remains human-oriented and stable enough
for existing tests.

Covers: R022-R026.

### D011 - MCP Phase One Is Read-Only/Low-Risk

Expose only these MCP tools in phase one:

- `p2p_governance_status`;
- `p2p_governance_validate`;
- `p2p_choice_governance_preflight`;
- `p2p_vote_status`;
- `p2p_precedent_search`.

Do not expose MCP vote recording, precedent recording, or choice decision in
this feature.

MCP responses should include explicit evidence that no decision or mutation was
performed where useful, for example `decision_made: false` and
`mutation_performed: false`.

Covers: R027-R032, AC008.

## Preflight Flow

1. Resolve target choice by id.
2. Load target details, options, selected option input, existing selected
   option, and active blockers.
3. Load governance mode, defaulting to `owner_decides` if absent.
4. Resolve actor from `permissions.yml` or fallback legacy roles.
5. Validate whether the actor can perform an owner-controlled finalization.
6. Load vote status and compute advisory alignment.
7. Load deterministic precedent matches from explicit ids, target references,
   or tags.
   If the precedent artifact is present but structurally invalid, return a
   structured blocking diagnostic instead of raising an uncaught exception.
8. Classify diagnostics as non-overrideable blocking errors, overrideable
   blockers, or warnings.
9. Compute result status:
   - `ready` when no blocking errors or rationale-required warnings exist;
   - `requires_rationale` when advisory signals require owner rationale but do
     not block;
   - `blocked` when blocking errors exist;
   - `requires_owner_override` when only overrideable explicit blockers exist
     and the actor is an owner.
10. Return `governance-preflight/v1` without writing files.

## Data Contract Sketch

```yaml
schema_version: governance-preflight/v1
target:
  type: choice
  id: CHOICE-001
  title: Initial AI Strategy
governance:
  mode: owner_decides
  source: .p2p/governance/governance.yml
  defaulted: false
actor:
  id: davide
  role: owner
  kind: person
  source: .p2p/project/permissions.yml
selection:
  requested_option: C
  resolved_option: C
  valid: true
result:
  status: requires_owner_override
  owner_final: true
  can_finalize_normally: false
  owner_override_allowed: true
  override_rationale_required: true
blocking_errors: []
warnings:
  - code: P2P_GOV_VOTE_CONFLICT
    message: Selected option differs from advisory vote winner.
vote_summary:
  total_votes: 3
  counts:
    A: 2
    C: 1
  winner: A
  tied: false
  alignment: conflicts
blockers:
  - source: .p2p/choices/CHOICE-001-.../links.yml
    target_type: proposal
    target: PROP-091
    reason: Active blocker.
precedents:
  - id: DP001
    source: .p2p/governance/decision-precedents.yml
    match_reason: related_choice
```

The exact field names may be refined during implementation, but the top-level
contract and semantics in the requirements must remain stable.

### D012 - Malformed Present Governance Artifacts Fail Closed

Defaulting is safe only when optional governance artifacts are absent. If an
artifact exists, the core should treat it as intentional project state and fail
closed when it is structurally unreadable.

Recommended behavior:

- missing `.p2p/governance/governance.yml`: warning plus default
  `owner_decides`;
- present `governance.yml` with non-mapping `governance`: blocking diagnostic
  `P2P_GOV_MALFORMED_GOVERNANCE`, `governance.mode: invalid`, and
  `result.status: blocked`;
- present `.p2p/governance/decision-precedents.yml` with non-list
  `precedents`: blocking diagnostic `P2P_GOV_MALFORMED_PRECEDENTS`,
  `precedents: []`, and `result.status: blocked`;
- malformed governance artifacts should still be reported by
  `p2p governance validate` and repository validation with validation-specific
  `P2P25x` codes.

Rationale:

- read-only preflight remains a stable machine contract even for invalid state;
- validation and preflight agree that present malformed artifacts are invalid;
- older repositories without optional governance files remain compatible.

## Error And Warning Policy

Blocking errors:

- unsupported governance mode;
- missing or invalid choice target;
- invalid selected option;
- unknown actor;
- non-owner actor for owner-controlled finalization;
- malformed required target artifacts;
- malformed present governance artifacts needed for reliable evaluation.

Overrideable blocker:

- active explicit blocker where an owner can proceed only with explicit
  rationale.

Warnings:

- advisory vote conflict;
- advisory vote tie;
- deterministic related precedents;
- no votes;
- missing optional governance artifacts;
- legacy role fallback;
- role mismatch between permissions and legacy roles;
- no matching precedents.

## Compatibility And Migration

No automatic migration is required.

Repositories without optional governance artifacts continue to work. New
read-only operations report default/fallback evidence but do not create missing
files. Existing write commands continue to use their existing behavior unless a
task explicitly changes them in an additive, tested way.

## Test Strategy

Use the lowest useful layer first:

- service tests for preflight classification, actor resolution, vote alignment,
  blocker handling, precedent matching, validation helper behavior, and no-write
  read-only guarantees;
- CLI tests only for command names, options, exit behavior, text output, and
  parseable machine output;
- MCP tests only for tool registration, schemas, payload shape, read-only
  semantics, and deferred write-tool absence;
- validation tests for repository validation findings;
- full suite only at the end or before commit/push/release.

Avoid duplicating the same governance scenario across service, CLI, and MCP
unless each layer protects a different public contract.

## Risks And Mitigations

Risk: preflight becomes a hidden decision path.

Mitigation: preflight returns evidence and status only. It does not call
`decide_choice`, `record_vote`, or any write operation.

Risk: fuzzy precedent matching makes CLI output non-deterministic.

Mitigation: only explicit ids, links, and tags are accepted in core.

Risk: validation becomes too strict for older repositories.

Mitigation: missing optional governance artifacts are tolerated; malformed
present artifacts are diagnosed.

Risk: behavior spreads across CLI and MCP handlers.

Mitigation: all classification is service-owned and tested at service layer.

Risk: tests become broad and slow.

Mitigation: each task names the focused subset first, then public/full
validation only where the layer contract changes.
