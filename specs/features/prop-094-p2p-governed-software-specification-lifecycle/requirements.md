# PROP-094 P2P-Governed Software Specification Lifecycle Requirements

## Status

`planned`

## Traceability

- P2P proposal: `PROP-094 - P2P-Governed Software Specification Lifecycle`
- Decision: accepted by owner
- Related local specs:
  - `specs/features/legacy-software-spec-export/`
  - `specs/features/domain-aware-visible-project-definition-export/`
  - `specs/features/project-vertical-pack-runtime-hardening-and-definition-state/`
  - `specs/features/prop-093c-agent-persistence-policy/`
  - `specs/features/prop-093e-root-mcp-hygiene/`

## Problem

P2P already has software-spec generation and export commands, but an owner or
agent can still treat "prepare specs" as a direct file-writing task. That can
produce durable files that look authoritative while the governed project
definition, proposals, choices, readiness, and Change Sets do not explain the
spec's source or unresolved assumptions.

The accepted `PROP-094` policy requires software specs to be routed through a
governed lifecycle. Exploratory work may stay in chat or proposal material, but
implementation-oriented specs and downstream exports must be derived from
accepted or explicitly provisional P2P artifacts.

## Goals

- Make software-spec request routing explicit for agents and humans.
- Add a software vertical contract that exposes the ingredients a useful
  software specification needs.
- Add a read-only/advisory lifecycle view that explains the correct route,
  persistent artifact class, preconditions, and next commands.
- Guard implementation-spec generation and downstream exports with clear
  preflight diagnostics without silently changing owner governance state.
- Keep existing software-spec generation and export commands compatible.
- Keep CLI and MCP behavior aligned for agent-facing lifecycle information.

## Non-Goals

- Do not create, accept, reject, defer, merge, finalize, or cleanup governance
  artifacts automatically.
- Do not add raw `.p2p/` file write surfaces.
- Do not replace existing `p2p spec refresh/export` output locations in this
  slice.
- Do not remove legacy software-spec or spec-export compatibility behavior.
- Do not make `p2p init` run a full software-spec interview.
- Do not infer requirements from draft proposals unless the owner explicitly
  marks them provisional through a supported artifact or command.
- Do not implement provider PR/MR automation.

## Scope

In scope:

- a built-in software project vertical or equivalent vertical contract;
- lifecycle route classification for common spec requests;
- preflight checks for implementation-oriented software specs;
- CLI output for lifecycle route/preflight guidance;
- MCP parity for lifecycle route/preflight guidance;
- generated agent instruction and policy updates;
- documentation and focused test coverage.

Out of scope:

- changing `.p2p/` by hand;
- generated code or external tool execution;
- speculative broad refactors of `P2PWorkspace`, CLI, or MCP dispatch;
- automatic migration of existing projects to a software vertical;
- new downstream export targets.

## Functional Requirements

### R001: Software spec lifecycle routes are explicit

THE SYSTEM SHALL define a deterministic software-spec lifecycle route model for
these owner intents:

- `chat_exploration`;
- `project_definition`;
- `architecture_comparison`;
- `implementation_spec`;
- `downstream_export`;
- `exact_file_request`.

Each route SHALL declare whether the expected persistent artifact is none, a
P2P proposal/question/choice artifact, a Change Set, a P2P-native software spec,
a generated export, stable documentation, or an explicit external/repository
file.

### R002: Ambiguous "specs" requests do not imply durable files

WHEN a request is ambiguous, such as "prepare the specs" or "organize the
specs", THE SYSTEM SHALL route it to lifecycle guidance instead of assuming a
durable file path.

The guidance SHALL explain which missing P2P or vertical ingredients must be
defined before a P2P-native implementation spec or export is treated as
authoritative.

### R003: Software vertical ingredients are visible

THE SYSTEM SHALL provide a software-specific vertical contract that covers these
specification ingredients:

- product or system objective;
- intended users, actors, and stakeholders;
- scope, MVP boundaries, and non-goals;
- core use cases and workflows;
- domain concepts and data model;
- integrations and external dependencies;
- constraints, non-functional requirements, and operating assumptions;
- acceptance criteria and validation strategy;
- unresolved risks, alternatives, and owner decisions.

### R004: Software vertical data remains declarative

THE SYSTEM SHALL treat software vertical content as declarative project-domain
data only. It SHALL NOT allow vertical pack text to override system, developer,
repository, governance, safety, or tool-permission instructions.

### R005: Software vertical availability is observable

WHEN project verticals are listed, shown, validated, or read through project
context, THE SYSTEM SHALL expose the software vertical like other built-in
verticals without requiring automatic activation.

### R006: Implementation-spec preflight checks accepted direction

WHEN an implementation-oriented software spec is requested for a Change Set, THE
SYSTEM SHALL verify that the Change Set exists and references accepted proposals
or another supported explicit provisional source.

IF the Change Set has no accepted or supported provisional source, THEN THE
SYSTEM SHALL report a blocking diagnostic before generating a P2P-native
software spec.

### R007: Implementation-spec preflight checks blocking choices

WHEN the project state exposes unresolved choices that block the requested
Change Set or its source proposals, THE SYSTEM SHALL report those choices as
blocking diagnostics before generating a P2P-native software spec.

IF the current codebase cannot determine a blocking relationship, THEN THE
SYSTEM SHALL report a non-blocking advisory note rather than inventing a
relationship.

### R008: Project-definition gaps are advisory unless explicitly blocking

WHEN a software vertical is inactive, missing, or has incomplete definition
coverage, THE SYSTEM SHALL report advisory diagnostics and next commands.

The implementation SHALL NOT fail existing compatible `p2p spec refresh` flows
solely because an older project has no active software vertical.

### R009: Spec refresh uses preflight diagnostics

WHEN `p2p spec refresh --change CHANGE-XXX` runs, THE SYSTEM SHALL evaluate the
implementation-spec preflight before writing generated software-spec artifacts.

IF the preflight has blocking failures, THEN THE SYSTEM SHALL fail without
writing new software-spec files and SHALL print actionable recovery commands.

IF the preflight has only advisory warnings, THEN THE SYSTEM MAY generate the
spec and SHALL surface the warnings in CLI/MCP output.

### R010: Spec export uses preflight diagnostics

WHEN `p2p spec export --change CHANGE-XXX --target TARGET` runs, THE SYSTEM
SHALL evaluate the same implementation/export preflight before writing target
exports.

Blocking failures SHALL prevent export writes. Advisory warnings SHALL be
returned with the export result.

### R011: Existing software-spec compatibility remains intact

THE SYSTEM SHALL preserve existing commands, MCP tool names, output paths, and
required artifact filenames for:

- `p2p spec status`;
- `p2p spec show`;
- `p2p spec prompt`;
- `p2p spec import`;
- `p2p spec refresh`;
- `p2p spec export`;
- `p2p spec export-status`;
- `p2p spec export-show`;
- `p2p spec export-validate`.

Any new fields or warnings SHALL be additive.

### R012: Lifecycle guidance is available through CLI

THE SYSTEM SHALL provide a CLI surface that returns software-spec lifecycle
guidance for an explicit route or request intent.

The CLI output SHALL include route id, persistent artifact class, preconditions,
blocking diagnostics, advisory diagnostics, suggested commands, and whether the
operation writes durable state.

### R013: Lifecycle guidance has MCP parity

IF CLI exposes software-spec lifecycle guidance, THEN MCP SHALL expose the same
read-only/advisory lifecycle guidance with stable machine-readable fields.

MCP write tools for spec refresh/export SHALL include additive preflight
diagnostics when they generate or export artifacts.

### R014: Generated agent instructions explain the lifecycle

Generated agent instructions and policy payloads SHALL tell agents:

- ambiguous spec requests should be classified before writing files;
- exploratory spec work can stay in chat or proposal material;
- project-definition work starts from vertical context and definition state;
- architecture comparisons should use choices or competing proposals;
- implementation specs require accepted/provisional direction and a Change Set;
- downstream exports derive from a P2P-native spec;
- exact file requests must follow the persistent-write preview policy unless
  the owner specified the exact operation, target, artifact kind, and durable
  destination.

### R015: Diagnostics identify next commands

Lifecycle and preflight diagnostics SHALL include next commands where possible,
such as:

- `p2p project vertical list`;
- `p2p project vertical show software_project`;
- `p2p project vertical select software_project --actor owner`;
- `p2p project context --format json`;
- `p2p project definition show --format json`;
- `p2p proposal show PROP-XXX`;
- `p2p change show CHANGE-XXX`;
- `p2p spec refresh --change CHANGE-XXX`;
- `p2p spec export --change CHANGE-XXX --target TARGET`.

### R016: No governance decisions are inferred

Lifecycle guidance, preflight, spec refresh, and spec export SHALL NOT accept,
reject, defer, decide, merge, finalize, cleanup, or otherwise complete
owner-controlled governance actions.

### R017: Documentation reflects software-spec lifecycle

Maintained docs SHALL distinguish:

- visible project definition export;
- exploratory/proposal-level spec work;
- P2P-native implementation software specs;
- downstream generated exports;
- stable documentation or exact owner-requested files.

## Non-Functional Requirements

### N001: Public compatibility

The implementation SHALL preserve existing CLI commands, MCP tool names,
persisted artifact layout, and YAML/Markdown schemas unless an explicitly
additive field is introduced.

### N002: Responsibility boundaries

New lifecycle logic SHALL live in a cohesive service, renderer, data model, or
validator. `P2PWorkspace`, CLI modules, and MCP handlers SHALL remain facade or
presentation layers.

### N003: Determinism

Lifecycle route and preflight results SHALL be deterministic from local project
state and explicit inputs. They SHALL NOT depend on network access, ambient
branch state, local usernames, or current working directory beyond the injected
project root.

### N004: Side-effect discipline

Lifecycle route/status/read operations SHALL NOT mutate project state.
Generation/export operations SHALL make their writes explicit and SHALL fail
before writing when blocking preflight checks fail.

### N005: Testability

The implementation SHALL be testable through service-level tests first, with CLI
and MCP tests added only for public contract behavior.

## Edge Cases And Errors

- E001: IF the requested Change Set does not exist, THEN preflight SHALL report
  a blocking `change_not_found` diagnostic.
- E002: IF the Change Set exists but has no accepted or supported provisional
  source, THEN preflight SHALL report a blocking `missing_governed_source`
  diagnostic.
- E003: IF a source proposal referenced by a Change Set is not accepted and is
  not explicitly provisional through a supported mechanism, THEN preflight SHALL
  report a blocking `source_not_accepted` diagnostic.
- E004: IF a software vertical is not active, THEN preflight SHALL report an
  advisory `software_vertical_not_active` diagnostic with a suggested command.
- E005: IF software vertical definition state is missing or incomplete, THEN
  preflight SHALL report advisory coverage diagnostics instead of inventing
  missing requirements.
- E006: IF an owner asks for an exact file path, THEN lifecycle guidance SHALL
  classify the request as `exact_file_request` and state that the file is not
  P2P-governed unless imported or declared by a supported contract.
- E007: IF MCP receives unsupported lifecycle intent values, THEN it SHALL
  return an actionable error listing supported intents.

## Public Surface Impact

### CLI

- Add a read-only/advisory software-spec lifecycle command.
- Add preflight diagnostics to spec refresh/export output.
- Preserve existing command names, arguments, and output paths.

### MCP

- Add read-only/advisory lifecycle guidance parity.
- Add additive preflight diagnostics to spec refresh/export payloads.
- Preserve existing tool names and schemas unless additive fields are added.

### Storage

- Add an internal built-in software vertical resource.
- Do not migrate existing projects automatically.
- Do not change `.p2p/outputs/software-spec/...` or
  `.p2p/outputs/spec-export/...` layouts in this slice.

### Docs

- Update CLI/MCP/agent integration docs with the governed lifecycle.
- Preserve legacy workflow documentation as compatibility behavior.

### Tests

- Add service tests for lifecycle routing, preflight, and software vertical
  contract.
- Add CLI tests for lifecycle command and refresh/export diagnostics.
- Add MCP tests for lifecycle parity and additive diagnostics.
- Run focused, public, and full validation before implementation completion.

## Acceptance Criteria

- The software vertical is available, validates cleanly, and exposes required
  software-spec ingredients.
- Lifecycle route guidance classifies common spec intents without writing state.
- `p2p spec refresh` and `p2p spec export` run preflight before writing.
- Blocking preflight failures prevent writes and include recovery commands.
- Advisory software vertical/project-definition gaps are surfaced without
  breaking compatible older projects.
- CLI and MCP expose equivalent lifecycle guidance.
- Generated agent instructions include the PROP-094 routing policy.
- Existing software-spec and export compatibility tests still pass.
