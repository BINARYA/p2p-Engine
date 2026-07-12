# PROP-094 P2P-Governed Software Specification Lifecycle Design

## Status

`planned`

## Requirements Covered

- R001-R017
- N001-N005
- E001-E007

## Design Summary

`PROP-094` should be implemented as a policy and lifecycle layer around the
existing project vertical, software spec, export, CLI, MCP, and agent
instruction systems.

The implementation should not create a second software-spec generator. Existing
`SoftwareSpecService` and `SpecExportService` remain responsible for artifact
generation and export. A new lifecycle service should classify spec requests,
evaluate preflight state, and produce deterministic diagnostics that CLI, MCP,
docs, and generated instructions can share.

## Key Decisions

### D001: Add a software vertical contract

Add a built-in `software_project` vertical pack that extends `base_project`.

Rationale: `PROP-094` says the software vertical should make spec readiness
visible. The project vertical runtime already supports built-in packs, fields,
completion policies, questions, artifacts, validation, JSON views, and project
definition state. Reusing that runtime avoids a parallel spec-readiness model.

The vertical should cover the ingredients in R003 as sections/fields, with
rubrics, questions, and artifacts that support project readiness review.

### D002: Do not auto-migrate or silently activate software vertical

Do not automatically select `software_project` for existing projects. For new
projects, keep existing `--domain software` behavior unless an explicit init or
vertical-selection change is made in the implementation slice.

Rationale: silent vertical activation would mutate project state and could
surprise existing users/tests. Lifecycle diagnostics should recommend
`p2p project vertical select software_project --actor owner` when appropriate,
leaving the owner in control.

### D003: Add a read-only lifecycle service

Add a cohesive service, for example:

```text
src/p2p_engine/core/software_spec_lifecycle.py
src/p2p_engine/services/software_spec_lifecycle.py
```

The service should own route definitions, preflight checks, diagnostic severity,
and suggested commands. It must not write state.

Rationale: route/preflight behavior is shared by CLI, MCP, generated
instructions, and spec generation. Keeping it outside CLI/MCP avoids
duplicated policy and preserves presentation boundaries.

### D004: Keep generation services focused

`SoftwareSpecService` should remain focused on generating/importing/showing
P2P-native software-spec artifacts.

`SpecExportService` should remain focused on export targets and validation.

Lifecycle preflight may be orchestrated by a small application service or by
`P2PWorkspace` facade methods that delegate to the lifecycle and generation
services. Do not bury preflight policy in CLI output code.

### D005: Use blockers and advisories

Preflight should distinguish:

- blockers: generation/export must not write;
- advisories: generation/export may proceed, but output must explain the risk.

Blocking examples:

- Change Set missing;
- Change Set has no accepted or supported provisional source;
- referenced source proposal is not accepted and not supported as provisional;
- a known blocking choice prevents the Change Set or source proposal.

Advisory examples:

- software vertical is not active;
- software vertical definition state is missing or incomplete;
- blocking-choice relationships cannot be determined from current state;
- older compatibility project lacks new lifecycle metadata.

Rationale: this protects implementation specs from ungoverned sources without
breaking existing compatible projects solely because they predate the software
vertical.

### D006: Provide explicit CLI route guidance

Add a read-only/advisory CLI command under the existing `spec` namespace.

Preferred command:

```bash
p2p spec lifecycle --intent implementation_spec --change CHANGE-001
```

Supported `--intent` values should match the route model:

- `chat_exploration`;
- `project_definition`;
- `architecture_comparison`;
- `implementation_spec`;
- `downstream_export`;
- `exact_file_request`.

The command should print route, write class, canonical/derived status,
preconditions, blockers, advisories, and suggested commands.

### D007: Provide MCP parity as read-only/advisory

Add an MCP tool such as `p2p_spec_lifecycle` with the same route and preflight
fields.

Existing write-safe MCP tools `p2p_spec_refresh` and `p2p_spec_export` should
return additive lifecycle/preflight diagnostics when they run.

Rationale: the behavior is agent-facing and operational. The local quality
policy requires an explicit MCP parity decision. Here parity is required.

### D008: Update generated agent policy and human docs

Generated agent instructions should include the route table and exact-file
boundary from `PROP-094`, while preserving `PROP-093` persistent-write preview
policy.

Docs should distinguish:

- visible project definition export;
- proposal/project-definition work;
- P2P-native software specs;
- downstream exports;
- stable documentation and exact external file requests.

## Components

### `src/p2p_engine/core/software_spec_lifecycle.py`

New typed models:

```python
SpecLifecycleIntent
SpecLifecycleRoute
SpecLifecycleDiagnostic
SpecLifecyclePreflight
SpecLifecycleView
```

Expected stable fields:

- `intent`;
- `route`;
- `write_class`;
- `persistent_artifact`;
- `canonical_status`;
- `writes_state`;
- `change_id`;
- `blockers`;
- `advisories`;
- `preconditions`;
- `suggested_commands`;
- `next_step`.

String values should be stable because CLI tests, MCP payloads, and agent
instructions will reference them.

### `src/p2p_engine/services/software_spec_lifecycle.py`

New service responsibilities:

- route intent to lifecycle guidance;
- inspect Change Set state for implementation/export routes;
- inspect source proposal decision states;
- inspect active vertical and project definition state;
- inspect choice state only where the current code can determine blocking
  relationships;
- return deterministic diagnostics and suggested commands;
- never write project state.

Dependencies should be injected or passed from `P2PWorkspace`, such as:

- `show_change_set`;
- `show_proposal`;
- `active_project_vertical`;
- `project_definition_view`;
- choice/blocking lookup helpers if available.

### `src/p2p_engine/resources/verticals/software_project/`

Add a built-in software vertical pack. A single-file `vertical.yml` is
acceptable if it matches current seed-pack style, but a canonical multi-file
pack is preferred if packaging tests stay straightforward.

Required sections or fields:

- system objective;
- users and actors;
- scope and MVP boundaries;
- workflows and use cases;
- domain concepts and data model;
- integrations and dependencies;
- constraints and non-functional requirements;
- acceptance and validation;
- risks, alternatives, and owner decisions.

The pack must validate cleanly through existing vertical validation.

### `src/p2p_engine/storage/filesystem.py`

Add facade delegation only, for example:

```python
def software_spec_lifecycle(...): ...
def refresh_software_spec(...):  # calls lifecycle preflight before generation
def export_software_spec(...):   # calls lifecycle preflight before export
```

Do not add new core lifecycle logic directly to this file.

### `src/p2p_engine/cli_commands/specs.py`

Expected changes:

- register `p2p spec lifecycle`;
- render blockers/advisories and suggested commands;
- run preflight before refresh/export and display additive diagnostics.

CLI output should remain compact and stable enough for tests.

### `src/p2p_engine/mcp/catalog/work_specs.py`

Expected changes:

- add `p2p_spec_lifecycle` schema;
- keep existing spec tools compatible;
- document `p2p_spec_refresh` and `p2p_spec_export` as write-safe tools that
  run lifecycle preflight.

### `src/p2p_engine/mcp/handlers/work_specs.py`

Expected changes:

- handle `p2p_spec_lifecycle`;
- include additive `lifecycle` or `preflight` field in `p2p_spec_refresh` and
  `p2p_spec_export` results.

### `src/p2p_engine/services/agent_templates.py`

Expected changes:

- add a software-spec lifecycle policy payload;
- include route table and command guidance in generated instructions;
- preserve existing write-policy, placement-policy, project-vertical, and
  proposal-readiness sections.

### Documentation

Likely touched:

- `docs/CLI-GUIDE.md`;
- `docs/MCP.md`;
- `docs/AGENT-INTEGRATION.md`;
- optionally `docs/CONCEPTS.md` or `docs/GLOSSARY.md` if lifecycle terms need a
  stable explanation.

## Data And Contracts

### Route Model

| Intent | Route | Persistent artifact |
| --- | --- | --- |
| `chat_exploration` | discuss missing fields and questions | none |
| `project_definition` | inspect/update vertical context and proposals | project definition/proposal artifacts |
| `architecture_comparison` | create choices or competing proposals | choice/proposal artifacts |
| `implementation_spec` | preflight Change Set then refresh spec | P2P-native software spec |
| `downstream_export` | preflight spec then export target | generated export |
| `exact_file_request` | classify exact requested path/write class | stable doc or explicit file |

### Diagnostic Model

Diagnostics should include:

```yaml
code: missing_governed_source
severity: blocker
message: Change Set CHANGE-001 has no accepted proposal source.
artifact_id: CHANGE-001
suggested_command: p2p change show CHANGE-001
recoverable: true
```

Use `severity: blocker` for write-preventing failures and `severity: advisory`
for non-blocking guidance.

### Preflight View

Example:

```yaml
intent: implementation_spec
change_id: CHANGE-001
writes_state: true
write_class: p2p_generated_narrative
canonical_status: downstream_from_governed_p2p_state
blockers: []
advisories:
  - code: software_vertical_not_active
    suggested_command: p2p project vertical select software_project --actor owner
suggested_commands:
  - p2p change show CHANGE-001
  - p2p spec refresh --change CHANGE-001
```

## Error Handling

- Unsupported intents should fail with a message listing allowed values.
- Missing Change Set should fail preflight without creating output directories.
- Missing source proposals should fail before generation/export writes.
- Advisory-only states should be visible but should not change exit status.
- MCP errors should preserve structured payloads where existing handler
  conventions allow them.

## Migration And Compatibility

No automatic migration is required.

Existing projects may continue to use `base_project` fallback and legacy
software-spec commands. They should receive advisory lifecycle diagnostics until
the owner selects or defines a software vertical.

Existing `.p2p/outputs/software-spec/...` and `.p2p/outputs/spec-export/...`
layouts stay unchanged.

## MCP Parity Decision

MCP parity is required.

Reason: lifecycle routing and preflight are agent-facing operational behavior.
Agents using MCP need the same route/preflight guidance as CLI users, and
existing MCP spec refresh/export tools can write generated artifacts.

Scope:

- add read-only/advisory `p2p_spec_lifecycle`;
- add additive lifecycle/preflight payload fields to `p2p_spec_refresh` and
  `p2p_spec_export`;
- do not add raw file-write tools;
- do not add consent gating, because these remain write-safe generated artifact
  operations without owner governance decisions.

## Test Strategy

Use the lowest useful layer first:

- service tests for route mapping and preflight diagnostics;
- vertical tests for software pack availability, validation, fields, and review;
- CLI tests for lifecycle output and refresh/export write prevention;
- MCP tests for tool schema, payload parity, and additive diagnostics;
- generated-instruction tests for route policy text and payload fields;
- docs text checks only where docs are treated as public guidance.

Public-contract validation is required because CLI and MCP behavior changes.
Full-suite validation is required before commit/push/merge.

## Risks And Mitigations

### Risk: lifecycle checks become bureaucratic

Mitigation: block only unsafe implementation/export writes. Treat missing
software vertical coverage as advisory for older compatible projects.

### Risk: route classification becomes unreliable NLP

Mitigation: first implementation should use explicit intent enums and agent
guidance, not heuristic natural-language classification.

### Risk: CLI and MCP drift

Mitigation: one service owns route/preflight data; CLI/MCP only render or
serialize it. Add tests at both public surfaces.

### Risk: software vertical duplicates project-definition rubrics

Mitigation: model software-specific ingredients as vertical sections/fields and
rubrics inside the existing vertical runtime, not as a parallel readiness
engine.

### Risk: breaking legacy spec workflows

Mitigation: preserve existing commands and paths. Add additive diagnostics and
only block states that lack governed source evidence.
