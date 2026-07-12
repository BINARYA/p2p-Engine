# Requirements - PROP-096 Readiness Evidence Quality And Question State Normalization

## Scope

Implement accepted `PROP-096` as a focused readiness bug fix.

The feature fixes two small but trust-damaging readiness behaviors:

- composed evidence can be marked placeholder when meaningful primary evidence
  is concatenated with a placeholder-only supplemental artifact;
- already-applied proposal questions can still be reported as
  `answered_not_applied` when `state` and `applied_to_proposal` disagree.

## Origin

- Source proposal: `PROP-096 - Readiness Evidence Quality and Question State Normalization`
- Decision: accepted
- Discovered while finalizing: `PROP-095`
- Related:
  - `PROP-082 - Readiness Assessment Refresh And Review Workflow`
  - `PROP-089 - Readiness Question State Convergence`
- Local quality policy:
  - `AGENTS-p2p-dev-specs.md`
  - `specs/skills/ENGINEERING_QUALITY_SKILL.md`
  - `specs/skills/TEST_QUALITY_SKILL.md`

## In Scope

- Artifact-aware readiness evidence aggregation.
- Placeholder-only supplemental artifact handling.
- Preservation of strict placeholder detection for primary evidence.
- Owner question state classification or normalization for already-applied
  answered questions.
- Regression tests reproducing the PROP-095 failure modes.

## Out Of Scope

- New readiness profile version.
- Changes to readiness weights, thresholds, labels, or owner override policy.
- Broad artifact coverage redesign.
- New governance semantics.
- New public proposal workflow commands.
- Direct `.p2p` YAML editing as a supported repair path.
- Changes to normal answered-unapplied question apply behavior.

## Public Surface And MCP Impact

- CLI behavior impact: `p2p proposal readiness assess`,
  `p2p proposal readiness explain`, and possibly
  `p2p proposal questions reassess` become more accurate.
- Storage impact: no schema change is required for readiness or question state.
- MCP impact: no MCP surface change is required. MCP tools that expose readiness
  should benefit from the service behavior without schema changes.
- Agent-facing behavior: agents should see fewer false readiness gaps and fewer
  false answered-unapplied prompts.

## Functional Requirements

### Composed Evidence Quality

- R001: THE SYSTEM SHALL evaluate primary proposal-section evidence separately
  from supplemental artifact evidence before aggregating criterion quality.
- R002: WHEN primary evidence is meaningful and supplemental evidence is
  placeholder-only, THE SYSTEM SHALL NOT classify the aggregate criterion as
  `placeholder`.
- R003: WHEN primary evidence is meaningful and supplemental evidence is
  placeholder-only, THE SYSTEM MAY report a supplemental artifact warning outside
  the criterion quality result.
- R004: WHEN primary evidence is missing or placeholder-only and no meaningful
  supplemental evidence exists, THE SYSTEM SHALL continue to classify the
  criterion as `missing` or `placeholder`.
- R005: WHEN all evidence for a criterion is placeholder-only, THE SYSTEM SHALL
  classify the criterion as `placeholder`.
- R006: WHEN all evidence for a criterion is absent, THE SYSTEM SHALL classify
  the criterion as `missing`.
- R007: THE SYSTEM SHALL preserve existing readiness profile weights, thresholds,
  labels, and quality caps.

### Acceptance Criteria Evidence

- R008: THE SYSTEM SHALL treat `proposal.md` Acceptance Criteria as primary
  evidence for `acceptance_criteria_quality`.
- R009: THE SYSTEM SHALL treat `execution-plan.md` as supplemental evidence for
  `acceptance_criteria_quality`.
- R010: WHEN `proposal.md` Acceptance Criteria are meaningful and
  `execution-plan.md` contains only the default placeholder line, readiness
  SHALL NOT report `acceptance_criteria_quality` as missing or placeholder.
- R011: WHEN `proposal.md` Acceptance Criteria are missing or placeholder-only
  and `execution-plan.md` is also missing or placeholder-only, readiness SHALL
  report `acceptance_criteria_quality` as missing or placeholder.

### Owner Question State

- R012: THE SYSTEM SHALL NOT report a question as `answered_not_applied` when it
  has `applied_to_proposal: true` and a non-empty `applied_at`.
- R013: THE SYSTEM SHALL classify such already-applied answered questions as
  closed for readiness purposes, or SHALL normalize them through a supported
  reassess/apply path.
- R014: THE SYSTEM SHALL preserve existing `p2p proposal questions apply`
  behavior for answered questions where `applied_to_proposal` is false.
- R015: THE SYSTEM SHALL NOT infer applied status solely from non-empty answer
  text.
- R016: THE SYSTEM SHALL NOT convert ordinary answered questions into applied
  questions unless a durable applied marker is already present.

### Artifact State Interaction

- R017: THE SYSTEM SHALL keep criterion readiness and artifact coverage as
  separate concepts.
- R018: A criterion MAY be ready from meaningful primary evidence while a
  supplemental artifact remains weak.
- R019: Artifact coverage warnings SHALL NOT create false criterion missing
  findings when criterion evidence is meaningful.

## Non-Functional Requirements

- N001: The fix SHALL be localized to readiness evidence aggregation and
  proposal question state classification or normalization.
- N002: The fix SHALL NOT change readiness profile defaults.
- N003: The fix SHALL NOT change public YAML schema unless unavoidable.
- N004: Tests SHALL be focused and reproduce the observed failure modes.
- N005: Existing readiness and question-state tests SHALL continue to pass.

## Acceptance Criteria

- AC001: A proposal with meaningful Acceptance Criteria and an
  `execution-plan.md` containing only the default placeholder line is not marked
  missing or placeholder for `acceptance_criteria_quality`.
- AC002: A proposal whose Acceptance Criteria evidence is actually absent or
  placeholder-only is still marked missing or placeholder.
- AC003: A structured question with `state: answered`,
  `applied_to_proposal: true`, and non-empty `applied_at` is not reported under
  `answered_not_applied`.
- AC004: A structured question with `state: answered` and
  `applied_to_proposal: false` is still reported as `answered_not_applied` and
  is still handled by `p2p proposal questions apply`.
- AC005: Regression tests cover composed evidence and question-state
  normalization.
- AC006: `p2p validate` continues to pass with no new errors.
