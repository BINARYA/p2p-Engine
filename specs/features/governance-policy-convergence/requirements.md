# Requirements - Governance Policy Convergence

## Origin And Scope

Source proposal: `PROP-091 - Governance Policy Convergence`.

This feature translates the accepted governance direction into local
implementation requirements for the runtime codebase. It is a development spec
only. It does not mutate P2P governance state and does not replace the accepted
proposal.

The feature covers:

- deterministic governance preflight for choices;
- owner-final governance semantics with transparent advisory votes;
- actor and role resolution from the permissions policy;
- explicit warning versus blocking-error classification;
- deterministic precedent lookup;
- governance artifact validation;
- read-only/low-risk CLI and MCP surfaces for the first implementation phase.

Out of scope for this feature:

- changing the owner-final governance model;
- adding AI/fuzzy precedent inference to core CLI behavior;
- making MCP tools decide choices, record votes, or record precedents;
- changing existing proposal, choice, consent, sync, or managed Git ownership
  rules beyond the governance preflight contract.

## Functional Requirements

### R001 - Governance Preflight Contract

WHEN a caller requests a governance preflight for a choice, THE SYSTEM SHALL
return a deterministic machine-readable contract with these top-level fields:
`schema_version`, `target`, `governance`, `actor`, `selection`, `result`,
`blocking_errors`, `warnings`, `vote_summary`, `blockers`, and `precedents`.

### R002 - Stable Schema Version

THE SYSTEM SHALL set the initial preflight schema version to
`governance-preflight/v1`.

### R003 - No Mutation From Preflight

WHEN a caller runs governance preflight, governance status, governance
validation, vote status, or precedent search, THE SYSTEM SHALL NOT create,
update, delete, refresh, or repair any `.p2p` artifact.

### R004 - Owner Final Decision Model

IF no governance mode is configured, THEN THE SYSTEM SHALL interpret governance
as `owner_decides`.

### R005 - Advisory Vote Semantics

WHEN votes exist for a target, THE SYSTEM SHALL report vote counts, total votes,
winner, tie state, and whether the selected option aligns with the vote result.

### R006 - Vote Conflict Warning

IF the owner-selected option conflicts with the advisory vote result, THEN THE
SYSTEM SHALL return a warning and SHALL NOT classify the conflict as a blocking
error by default.

The vote alignment value for this case SHALL be `conflicts`.

### R007 - Vote Tie Warning

IF advisory votes are tied, THEN THE SYSTEM SHALL return a warning and SHALL NOT
block owner finalization by default.

### R008 - Actor Resolution Primary Source

WHEN `permissions.yml` exists, THE SYSTEM SHALL resolve actor identity, role,
kind, and display name from `.p2p/project/permissions.yml`.

### R009 - Actor Resolution Fallback

IF `permissions.yml` is absent, THEN THE SYSTEM SHALL use legacy governance role
artifacts only as a compatibility fallback and SHALL report that fallback in the
preflight actor evidence.

### R010 - Role Mismatch Warning

IF legacy role artifacts and `permissions.yml` disagree for the same actor,
THEN THE SYSTEM SHALL report a warning and SHALL use `permissions.yml` as the
authoritative source.

### R011 - Owner Authorization

IF an operation requires an owner decision and the resolved actor is not an
owner, THEN THE SYSTEM SHALL return a blocking error with a stable diagnostic
code.

### R012 - Unknown Actor Handling

IF the requested actor cannot be resolved, THEN THE SYSTEM SHALL return a
blocking error with a stable diagnostic code and actionable recovery guidance.

### R013 - Active Explicit Blockers

WHEN a target has active explicit blockers, THE SYSTEM SHALL include them in
the preflight `blockers` field and classify normal finalization as blocked.

### R014 - Owner Override Visibility

IF active explicit blockers exist, THEN THE SYSTEM SHALL indicate whether owner
override is possible and whether explicit rationale is required.

### R015 - Non-Overrideable Errors

THE SYSTEM SHALL classify malformed artifacts, missing required target data,
invalid selected options, invalid actor policy, and unsupported governance modes
as non-overrideable blocking errors.

### R016 - Warning Classification

THE SYSTEM SHALL classify vote conflict, vote tie, missing optional governance
artifacts, legacy role fallback, and role mismatch as warnings unless another
requirement classifies the same condition as a blocking error.

### R017 - Deterministic Precedent Lookup

WHEN searching decision precedents, THE SYSTEM SHALL match only explicit
precedent ids, related proposal ids, related choice ids, or declared tags.

### R018 - No Fuzzy Precedent Matching

THE SYSTEM SHALL NOT match precedents using title similarity, fuzzy text
similarity, embeddings, LLM inference, or implicit semantic matching in the core
CLI/MCP implementation.

### R019 - Precedent Evidence

WHEN precedent matches are found, THE SYSTEM SHALL return the matched
precedent id, source path, match reason, related target reference, and summary
metadata.

### R019A - Related Precedent Warning

WHEN governance preflight finds deterministic related precedent matches, THE
SYSTEM SHALL return a warning with stable code `P2P_GOV_RELATED_PRECEDENTS`
and SHALL NOT classify the match as a blocking error by default.

### R020 - Governance Artifact Validation

WHEN repository validation runs, THE SYSTEM SHALL validate governance artifacts
needed by this feature, including `governance.yml`, `roles.yml`,
`decision-precedents.yml`, and proposal-local `votes.yml`.

### R021 - Validation Diagnostics

IF governance artifacts are invalid, THEN THE SYSTEM SHALL return validation
findings with stable codes, severity, path, message, and suggested recovery
command where one is available.

### R021A - Preflight Governance Artifact Errors

IF governance preflight reads a present governance artifact that is
structurally invalid, THEN THE SYSTEM SHALL return a structured blocking error
instead of failing with an uncaught exception.

For `.p2p/governance/governance.yml`, absence SHALL default to
`owner_decides`, but a present file whose `governance` value is not a mapping
SHALL produce `P2P_GOV_MALFORMED_GOVERNANCE`.

For `.p2p/governance/decision-precedents.yml`, malformed precedent structure
SHALL produce `P2P_GOV_MALFORMED_PRECEDENTS` in preflight.

### R022 - CLI Governance Status

WHEN `p2p governance status` is run, THE SYSTEM SHALL continue to report the
current governance status and SHALL preserve existing default text behavior.

### R023 - CLI Governance Validate

WHEN `p2p governance validate` is run, THE SYSTEM SHALL report governance-only
validation diagnostics without mutating project state.

### R024 - CLI Choice Governance Preflight

WHEN `p2p choice governance-preflight CHOICE-XXX --option <option> --actor
<actor>` is run, THE SYSTEM SHALL return preflight status for the requested
choice and selected option without deciding the choice.

### R025 - CLI Machine Output

WHEN governance status, governance validation, choice governance preflight, vote
status, or precedent search support `--format json` or `--format yaml`, THE
SYSTEM SHALL emit parseable machine output without Rich markup.

### R026 - Existing CLI Compatibility

THE SYSTEM SHALL preserve existing governance, vote, precedent, and choice CLI
commands and their default behavior unless this feature explicitly adds
backward-compatible output.

### R027 - MCP Governance Status Tool

THE SYSTEM SHALL expose a read-only MCP tool for governance status that returns
the same core data as the service contract.

### R028 - MCP Governance Validate Tool

THE SYSTEM SHALL expose a read-only MCP tool for governance validation that
returns structured diagnostics and does not mutate state.

### R029 - MCP Choice Governance Preflight Tool

THE SYSTEM SHALL expose a read-only MCP tool for choice governance preflight
that returns the `governance-preflight/v1` contract and does not decide the
choice.

### R030 - MCP Vote Status Tool

THE SYSTEM SHALL expose a read-only MCP tool for vote status and SHALL NOT
record votes through this phase-one MCP surface.

### R031 - MCP Precedent Search Tool

THE SYSTEM SHALL expose a read-only MCP tool for deterministic precedent search
and SHALL NOT record precedents through this phase-one MCP surface.

### R032 - MCP Deferred Write Tools

THE SYSTEM SHALL NOT add MCP tools for vote recording, precedent recording, or
choice decision in this feature.

### R033 - Facade Compatibility

THE SYSTEM SHALL expose new runtime behavior through `P2PWorkspace` only as
thin delegation methods to dedicated services.

### R034 - Existing Artifact Compatibility

THE SYSTEM SHALL tolerate repositories that do not yet have optional governance
artifacts and SHALL report missing optional state as fallback evidence or
warnings, not as automatic validation errors.

### R035 - Deterministic Output Ordering

THE SYSTEM SHALL sort diagnostics, blockers, precedents, and vote output by
stable keys so repeated runs over unchanged state produce identical payloads.

### R036 - Preflight Result Status Values

THE SYSTEM SHALL use only these `result.status` values in
`governance-preflight/v1`:

- `ready`;
- `requires_rationale`;
- `requires_owner_override`;
- `blocked`.

Malformed artifacts, invalid input, unknown actors, non-owner actors, and
unsupported governance modes SHALL be represented as `blocked` with detailed
`blocking_errors`.

## Non-Functional Requirements

### N001 - Responsibility Boundary

Domain and application logic for governance preflight SHALL live in a cohesive
service or service-owned helpers, not in CLI command functions, MCP handlers, or
`src/p2p_engine/mcp/tools.py`.

### N002 - Public Compatibility

Existing CLI command names, MCP tool names, persisted file layout, YAML
schemas, and choice lifecycle behavior SHALL remain compatible unless a change
is explicitly listed as additive in this spec.

### N003 - Read-Only Discipline

Read-only operations SHALL be tested against unintended filesystem writes where
the operation touches persisted project state.

### N004 - Stable Diagnostics

Blocking errors and warnings SHALL use stable codes suitable for assertions,
MCP clients, and future automation.

### N005 - Structured Data First

Internal code SHALL use typed dataclasses or structured mappings for preflight
results, diagnostics, vote summaries, blockers, and precedent matches instead
of parsing rendered CLI text.

### N006 - Lowest Useful Test Layer

Tests SHALL prove governance behavior at the lowest useful layer first and add
CLI/MCP tests only for public contract behavior.

### N007 - Incremental Delivery

Implementation SHALL be split into small, reversible phases that can be
validated independently before adding the next public surface.

### N008 - No Broad Cleanup

Implementation SHALL NOT include unrelated refactoring of choices, permissions,
validation, MCP registry, or filesystem storage.

## Acceptance Criteria

### AC001 - Preflight Service Contract

Focused service tests prove that choice governance preflight returns
`governance-preflight/v1` with target, governance, actor, selection, result,
diagnostics, vote summary, blockers, and precedents.

### AC002 - Owner And Vote Semantics

Focused service tests prove owner-selected options can proceed despite advisory
vote conflicts while reporting warnings.

### AC003 - Actor Resolution

Focused service tests prove permissions-first actor resolution, legacy fallback,
role mismatch warnings, unknown actor blocking errors, and non-owner blocking
errors.

### AC004 - Blocker Semantics

Focused service tests prove active explicit blockers block normal finalization,
owner override rationale is signaled, and malformed artifacts remain
non-overrideable.

### AC005 - Deterministic Precedents

Focused service tests prove precedent search uses only explicit ids, target
links, and tags, and rejects fuzzy/title-only matches.

### AC005A - Related Precedent Warning

Focused service tests prove deterministic related precedent matches are listed
in `precedents` and also reported through `P2P_GOV_RELATED_PRECEDENTS` warning.

### AC006 - Governance Validation

Validation tests prove invalid governance mode, malformed role payloads,
duplicate precedent ids, malformed votes, and invalid vote choices produce
stable diagnostics.

### AC006A - Preflight Malformed Governance Artifacts

Focused preflight tests prove malformed present `governance.yml` and
`decision-precedents.yml` return structured blocking errors and do not crash the
CLI/MCP preflight path.

### AC007 - CLI Public Contract

Targeted CLI tests prove the new governance validation, choice preflight, vote
status, and precedent search outputs are correct, parseable where machine
formats are supported, and existing defaults remain compatible.

### AC008 - MCP Public Contract

Targeted MCP tests prove the phase-one tools are registered, schema-valid,
read-only, and return the expected structured payloads.

### AC009 - No Read-Only Writes

Service, CLI, or integration tests prove read-only governance operations do not
write, repair, refresh, or regenerate `.p2p` files.

### AC010 - Repository Validation

Repository validation and the relevant focused/public/full test commands pass
before the feature is marked complete.
