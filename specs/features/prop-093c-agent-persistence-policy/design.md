# PROP-093C Agent Persistence Policy Design

## Design Summary

`PROP-093C` adds a durable agent-facing persistence policy to generated
instructions and `.p2p/agent-policy.yml`. The implementation should be centered
in the agent template/service layer, not scattered across CLI and MCP handlers.

The policy separates reasoning from writes. Agents can analyze freely, but
meaningful persistent writes require classification and an action preview unless
the owner already requested the exact operation and artifact.

## Key Decisions

### D001: Policy is generated from shared blocks

The write-class, preview, placement, and routing guidance should be implemented
as shared template blocks in the agent template module or a cohesive companion
module. Adapter-specific templates should reference or embed those blocks
instead of maintaining separate divergent prose.

### D002: Structured payload is authoritative for tests

The markdown output is for agents. The structured `.p2p/agent-policy.yml`
payload should carry the same policy concepts in machine-checkable form.

Tests should assert structured payload fields and a small set of essential
prose snippets.

### D003: Preview rule applies to meaningful persistent writes

The preview rule should avoid blocking normal read-only analysis and exact owner
requests. It applies when the agent is about to create, update, delete, export,
import, or invoke an external side effect that persists beyond chat.

### D004: Stable documentation remains outside P2P governance by default

`stable_documentation` is a classification and preview requirement. It is not a
claim that P2P owns every durable repository document.

### D005: Runtime enforcement is instruction-level for this slice

This slice updates generated policy and tests. It does not add a runtime
authorization layer for arbitrary filesystem writes.

### D006: Placement policy is strict but not an artifact schema

The core placement policy should be strict: agents must not invent durable write
locations, and unknown durable destinations should trigger preview and owner
confirmation or a stop-and-report outcome for governed artifacts without a
primitive.

That strictness should stay at the write-class routing layer. The placement
policy defines mandatory zones such as `.p2p/`, `outputs/`, `drafts/`, and
`docs/`; it does not define every evaluable artifact name. Exact output names
for artifacts that need evaluation, regeneration, references, or agent
consumption should come from P2P artifact contracts, explicit vertical
primitives, or exact owner requests.

### D007: Exact owner requests are interpreted narrowly

Skipping redundant preview is allowed only when the owner specifies the
operation, target path or P2P object, artifact kind, and intended durable
destination. Ambiguous requests remain subject to preview and routing.

### D008: Canonicality is explicit in placement policy

Generated exports are derived by default. Stable documentation is durable
repository documentation, not canonical P2P state unless explicitly imported or
declared. Local scratch is temporary and cannot become project memory until it
is promoted, imported, or otherwise classified.

## Components

### `src/p2p_engine/services/agent_templates.py`

Likely owns most behavior for this slice.

Expected changes:

- add shared markdown block for persistent write classes;
- add shared markdown block for action preview;
- add shared markdown block for artifact placement;
- add compact routing playbook;
- add structured policy fields under `agent_policy()`;
- include equivalent rules in generic, Codex, Claude, Cursor, Copilot, Gemini,
  and shared-only OpenCode coverage.

### `src/p2p_engine/services/agent_instructions.py`

Owns refresh, install, update, uninstall, registry, drift, and hash behavior.

Expected changes:

- template hashes change as generated content changes;
- existing non-destructive refresh and drift behavior should remain unchanged;
- no new write safety bypasses.

### CLI agent/init surfaces

Likely touched modules:

- `src/p2p_engine/cli.py`;
- `src/p2p_engine/cli_commands/agents.py`.

Expected changes:

- no command shape changes required;
- output may mention refreshed policy only if useful;
- CLI tests should verify generated content through filesystem outputs.

### MCP maintenance/project handlers

Likely touched modules:

- `src/p2p_engine/mcp/handlers/maintenance.py`;
- `src/p2p_engine/mcp/handlers/project.py`.

Expected changes:

- no new MCP write tools;
- generated files from MCP init/refresh should match CLI service behavior.

### Documentation

Likely touched docs:

- `docs/AGENT-INTEGRATION.md`;
- `docs/INSTALL.md` if bootstrap text references generated policy;
- any local agent policy docs if present.

## Structured Policy Shape

The exact YAML can follow existing style, but it should expose these concepts:

```yaml
write_policy:
  analysis_without_write: allowed
  preview_required_for:
    - meaningful_persistent_write
    - external_side_effect
  preview_can_be_skipped_when: owner_requested_exact_operation_and_artifact
  exact_request_requires:
    - operation
    - target
    - artifact_kind
    - durable_destination
  preview_fields:
    - operation
    - target
    - artifact_kind
    - write_class
    - canonical_or_derived
    - reason
    - reversibility
  classes:
    read_only:
      surface: none
    chat_only:
      surface: chat
    local_scratch:
      surface: local_temp_or_draft
    p2p_canonical:
      surface: p2p_cli_or_explicit_mcp_write_tool
    p2p_generated_narrative:
      surface: p2p_generate_or_import_primitive
    p2p_imported_artifact:
      surface: p2p_import_primitive
    generated_export:
      surface: p2p_export_or_repository_output
    stable_documentation:
      surface: repository_docs
    external_side_effect:
      surface: external_system
placement_policy:
  mode: strict
  governed_state:
    path: .p2p/
    write_surface: p2p_cli_or_explicit_mcp_write_tool
    manual_edit: forbidden_except_explicit_repair
  generated_outputs:
    path: outputs/
    status: derived
    canonical: false
    naming: must_follow_artifact_contract
  preliminary_drafts:
    paths:
      - drafts/
      - docs/drafts/
    status: temporary_or_working
    canonical: false
    promotion_required_for_project_memory: true
  stable_documentation:
    path: docs/
    status: durable_repository_documentation
    canonical_p2p_state: false_unless_imported_or_declared
    requires_owner_intent: true
  local_scratch:
    status: temporary_only
    durable_project_memory: false
    promotion_required_for_project_memory: true
  unknown_destination:
    behavior: preview_and_ask_or_stop
artifact_contract_policy:
  placement_policy_is_not_complete_artifact_schema: true
  exact_evaluable_output_names_from:
    - p2p_artifact_contract
    - explicit_vertical_primitive
    - exact_owner_request
  agent_must_not_invent_durable_output_paths: true
routing_playbook:
  proposal_authoring: p2p proposal/contribution/question/import primitives
  implementation_work: repository specs/src/tests/docs outside .p2p
```

Tests should allow harmless wording changes but protect key names and semantics.

## Markdown Output Shape

Generic `AGENTS.md` should include:

1. source of truth and missing primitive rules;
2. persistent write classes;
3. action preview rule;
4. strict artifact placement policy;
5. placement versus artifact-contract boundary;
6. routing playbook;
7. existing governance, readiness, MCP, managed Git, and token-budget rules.

Adapter-specific files may use a shorter form:

- follow `AGENTS.md` and `.p2p/agent-policy.yml`;
- do not edit `.p2p/` directly;
- preview meaningful persistent writes;
- use placement/routing policy.
- do not invent durable output paths.

## Error Handling

No new runtime errors are expected except normal template path safety and
registry drift handling.

If structured policy serialization fails, existing init or refresh should fail
with a normal service/CLI error instead of writing partial policy content.

## Migration Strategy

No migration is required.

Existing projects receive the new policy through existing lifecycle operations:

- new `p2p init`;
- `p2p agent instructions refresh`;
- `p2p agent update <adapter>` where safe.

Drifted or unmanaged files are skipped unless force behavior is explicitly used.

## Test Strategy

Use focused tests at the service/template layer first:

- generated `AGENTS.md` contains write classes and preview rule;
- generated `.p2p/agent-policy.yml` contains structured policy;
- structured placement policy is strict, includes unknown-destination behavior,
  and describes generated outputs as derived;
- generated policy distinguishes placement buckets from artifact contracts and
  forbids invented durable output paths for governed or evaluable artifacts;
- adapter-specific files contain equivalent boundary references;
- refresh skips drifted/unmanaged files as before.

Add CLI/MCP tests only for public init/refresh outputs or schema-visible
behavior. No full runtime enforcement tests are expected in this slice.

## Risks And Mitigations

### Generated instructions become too long

Mitigation: use a compact short form in generated files and keep detailed docs
in maintained documentation.

### Policy text diverges across adapters

Mitigation: generate from shared template blocks and assert common snippets in
tests.

### Structured payload and prose diverge

Mitigation: assert structured payload as the primary contract and prose as
essential cues.

### Users expect hard filesystem enforcement

Mitigation: document that this slice is instruction/policy hardening, while
tool-enforced writes remain limited to CLI/MCP primitives.

### Placement policy is mistaken for a complete artifact registry

Mitigation: state that placement policy only defines write-class zones. Exact
names for evaluable or reusable outputs must come from artifact contracts,
vertical primitives, or exact owner requests.
