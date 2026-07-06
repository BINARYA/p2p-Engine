# Requirements - MCP Artifact Import Parity

## Scope

Add MCP write-safe proposal artifact content imports with parity to the existing
controlled CLI import primitives.

The feature closes the gap where MCP clients can generate proposal workflow
prompts and update artifact coverage state, but cannot import generated
long-form artifact content such as exploration output, impact maps,
clarifications, synthesized proposal text, execution plans, or task YAML.

This is a local development spec only. It translates the accepted P2P direction
into implementation requirements and does not mutate P2P governance state.

## Origin

- Source proposal: `PROP-088 - MCP Artifact Import Parity`.
- Accepted Change Set: `CHANGE-066 - MCP Artifact Import Parity`.
- Accepted direction: total MCP parity with existing controlled CLI import
  primitives that have fixed targets and validation.
- Existing behavioral baseline:
  - `p2p explore import`
  - `p2p impact import`
  - `p2p clarify import`
  - `p2p synthesize import`
  - `p2p plan import`
  - `p2p tasks import`

## In Scope

- MCP write-safe import tools for:
  - exploration artifacts;
  - impact artifacts;
  - clarifications;
  - synthesized proposal content;
  - execution plans;
  - task YAML.
- Source-path import parity with the existing CLI behavior.
- Direct content payload imports for MCP clients that already hold generated
  content in the tool call.
- Explicit allowlists for supported artifact kinds and filenames.
- Reuse of existing import validation for tasks YAML and impact YAML.
- Structured MCP result metadata for written files and governance boundaries.
- Tests for service behavior, MCP schemas, MCP handler payloads, validation
  failures, and public tool listing/calling.
- Documentation for supported tools, input modes, validation, unsupported
  artifact imports, and relationship to artifact coverage state.

## Out Of Scope

- Generic arbitrary artifact import or update.
- New CLI import commands or CLI behavior changes.
- Importing SWOT, digest, comments, votes, decisions, governance files, Change
  Set artifacts, Work artifacts, project state, or generated exports.
- Accepting, rejecting, deferring, merging, finalizing, or otherwise deciding
  proposals.
- Consent-gating these write-safe local imports in the first implementation.
- Changing proposal artifact coverage state as an automatic side effect of
  content import.
- Changing `.p2p` proposal directory layout or existing artifact filenames.
- Reworking prompt generation.
- Broad MCP dispatcher refactoring unrelated to this feature.

## Public Surface And MCP Impact

- CLI impact: preserve existing write-safe CLI import behavior.
- MCP impact: add write-safe proposal artifact content import tools.
- Storage impact: compatible writes to existing proposal artifact files only.
- Agent-facing behavior: new MCP workflow for importing generated proposal
  artifact content.
- MCP parity decision: required and implemented in this feature because
  `PROP-088` exists specifically to close CLI/MCP parity for controlled artifact
  imports.

## Functional Requirements

- R001: WHEN an MCP client lists tools, THE SYSTEM SHALL expose write-safe
  proposal artifact import tools for exploration, impact, clarification,
  synthesis, plan, and tasks imports.

- R002: WHEN `p2p_explore_import` is called with a valid `proposal_id` and
  `source`, THE SYSTEM SHALL import from the source file or source directory
  with the same target mapping as `p2p explore import`.

- R003: WHEN `p2p_impact_import` is called with a valid `proposal_id` and
  `source`, THE SYSTEM SHALL import from the source file or source directory
  with the same target mapping and YAML-key validation as `p2p impact import`.

- R004: WHEN `p2p_clarify_import` is called with a valid `proposal_id` and
  `source`, THE SYSTEM SHALL import the source file into `clarifications.md`
  with the same behavior as `p2p clarify import`.

- R005: WHEN `p2p_synthesize_import` is called with a valid `proposal_id` and
  `source`, THE SYSTEM SHALL import the source file into `proposal.md` with the
  same behavior as `p2p synthesize import`.

- R006: WHEN `p2p_plan_import` is called with a valid `proposal_id` and
  `source`, THE SYSTEM SHALL import the source file into `execution-plan.md`
  with the same behavior as `p2p plan import`.

- R007: WHEN `p2p_tasks_import` is called with a valid `proposal_id` and
  `source`, THE SYSTEM SHALL import the source file into `tasks.yml` only after
  applying the same tasks YAML validation as `p2p tasks import`.

- R008: WHEN an exploration import tool is called with `content`, THE SYSTEM
  SHALL write that content to the fixed `exploration.md` target for the
  proposal.

- R009: WHEN an impact import tool is called with `content`, THE SYSTEM SHALL
  validate the content as impact YAML and write it to the fixed
  `impact-map.yml` target for the proposal.

- R010: WHEN a clarify, synthesize, plan, or tasks import tool is called with
  `content`, THE SYSTEM SHALL write the content to its fixed target and SHALL
  apply kind-specific validation before writing when validation exists.

- R011: WHEN an exploration import tool is called with `artifacts`, THE SYSTEM
  SHALL accept only the existing exploration artifact filenames:
  `exploration.md`, `findings.md`, `alternatives.md`, `open-questions.md`,
  `risks.md`, `assumptions.md`, and `suggested-scope.md`.

- R012: WHEN an impact import tool is called with `artifacts`, THE SYSTEM SHALL
  accept only `impact-map.yml`, `related-proposals.yml`, and
  `conflict-analysis.yml`, and SHALL validate each artifact against its
  required top-level YAML key before writing.

- R013: IF an import call supplies none of `source`, `content`, or `artifacts`,
  THEN THE SYSTEM SHALL reject the request before writing files.

- R014: IF an import call supplies more than one of `source`, `content`, or
  `artifacts`, THEN THE SYSTEM SHALL reject the request before writing files.

- R015: IF an import call supplies an artifact filename that is not supported
  for the requested import tool, THEN THE SYSTEM SHALL reject the request before
  writing files.

- R016: IF a `source` path does not exist or is not valid for the requested
  import kind, THEN THE SYSTEM SHALL reject the request with the same domain
  error semantics as the existing CLI-backed service path.

- R017: IF a proposal ID does not resolve to an existing proposal, THEN THE
  SYSTEM SHALL reject the request and SHALL NOT create proposal directories or
  invented proposal IDs.

- R018: WHEN an import succeeds, THE SYSTEM SHALL return structured MCP
  metadata including proposal ID, import kind, input mode, imported file paths,
  and governance metadata stating that no proposal decision was made.

- R019: WHEN an import fails validation, THE SYSTEM SHALL return an error
  without partial writes for payload modes that can be validated before writing.

- R020: THE SYSTEM SHALL NOT accept, reject, defer, merge, finalize, publish, or
  decide a proposal as a side effect of any artifact import tool.

- R021: THE SYSTEM SHALL NOT update artifact coverage state as a side effect of
  content import unless the existing CLI import behavior is explicitly changed
  by a separate accepted feature.

- R022: THE SYSTEM SHALL preserve existing prompt tools as prompt-only tools;
  `p2p_explore_prompt`, `p2p_clarify_prompt`, `p2p_synthesize_prompt`,
  `p2p_plan_prompt`, `p2p_tasks_prompt`, and `p2p_impact_prompt` SHALL NOT
  import generated output.

- R023: THE SYSTEM SHALL keep unsupported artifact-content mutations as missing
  primitive errors rather than falling back to arbitrary file writes.

## Non-Functional Requirements

- N001: THE SYSTEM SHALL keep import validation and target mapping in service or
  domain helper code, not in MCP transport handlers.

- N002: THE SYSTEM SHALL preserve `P2PWorkspace` as a compatibility facade and
  add only delegating facade methods when needed.

- N003: THE SYSTEM SHALL keep the MCP handler small: parse arguments, select the
  import kind, delegate to workspace/service behavior, and format structured
  JSON-compatible results.

- N004: THE SYSTEM SHALL preserve existing CLI command names, options, output,
  and validation semantics.

- N005: THE SYSTEM SHALL preserve existing MCP tool payloads and schemas unless
  adding the new import tools.

- N006: THE SYSTEM SHALL not introduce broad refactors of MCP registry,
  proposal services, storage, CLI command modules, or validation helpers in the
  same implementation slice.

- N007: THE SYSTEM SHALL keep all path handling rooted in explicit project or
  temporary paths and SHALL NOT hardcode local machine paths.

- N008: THE SYSTEM SHALL expose errors that are useful to both humans and MCP
  clients, including operation, artifact kind, and rejected input mode when
  practical.

- N009: THE SYSTEM SHALL test public MCP contracts at the MCP layer and test
  validation and file-write behavior at the service layer.

## Edge Cases And Errors

- E001: A valid exploration source file imports to `exploration.md`.
- E002: A valid exploration source directory imports only known exploration
  artifacts.
- E003: An empty exploration source directory is rejected.
- E004: A valid impact source file imports to `impact-map.yml`.
- E005: A valid impact source directory imports all known impact artifacts that
  are present.
- E006: Impact YAML without the expected top-level key is rejected.
- E007: Tasks YAML without a top-level `tasks` list is rejected.
- E008: Direct `content` imports work for each single-target import kind.
- E009: Direct `artifacts` imports work for exploration and impact multi-file
  imports.
- E010: Direct `artifacts` includes a disallowed filename.
- E011: Direct payload request includes both `source` and `content`.
- E012: Direct payload request includes no import input.
- E013: Proposal ID is missing, blank, or not found.
- E014: Source path points to a directory for a single-file-only import kind.
- E015: Prompt tools still generate prompts and do not import output.

## Acceptance Criteria

- AC001: MCP tool listing includes the six supported import tools with schemas
  that require `proposal_id` and support exactly one import input mode.
- AC002: MCP source-path tests prove parity with existing CLI-controlled import
  targets for exploration, impact, clarification, synthesis, plan, and tasks.
- AC003: MCP direct-content tests prove generated content can be imported
  without first writing a caller-managed source file.
- AC004: MCP multi-artifact payload tests prove exploration and impact imports
  allow only supported filenames and preserve validation.
- AC005: Service tests prove import target mapping and validation are shared
  with or equivalent to the existing CLI-backed import behavior.
- AC006: Error tests prove missing input, multiple input modes, invalid paths,
  unsupported filenames, invalid impact YAML, and invalid tasks YAML fail before
  uncontrolled writes.
- AC007: Prompt tool regression tests prove existing prompt tools still do not
  import outputs.
- AC008: Documentation explains supported tools, input modes, validation,
  unsupported generic import, and the distinction between content import and
  artifact coverage state.
- AC009: Focused service, MCP, public-contract, and full-suite validation pass
  before implementation is marked complete.
