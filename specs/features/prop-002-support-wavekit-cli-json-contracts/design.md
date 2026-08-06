# Design - Support WaveKit CLI JSON Contracts

## Requirements Covered

- R001-R055
- N001-N007
- AC001-AC010

## Decision Summary

WaveKit's worker should be a deterministic server process, not an agent. It
therefore talks to P2P Engine through an allowlisted CLI JSON contract. The
contract extends the existing `p2p-cli/v1` envelope and adds missing domain
payloads, operation-key receipts and read models for the exact project,
proposal and contribution workflows WaveKit needs.

The feature is intentionally narrower than "JSON everywhere". Commands outside
the WaveKit worker, Angular overview, proposal detail and structured
contribution workflows remain unchanged unless they are part of the explicit
inventory.

## Key Decisions

- D001: Reuse `p2p-cli/v1` as the transport envelope.
  Rationale: `PROP-107` already introduced the versioned transport contract.
  WaveKit needs new domain payloads, not another envelope.

- D002: Treat `--operation-key` as the WaveKit-facing name for retry identity.
  Rationale: WaveKit already persists `ProjectOperation`; the CLI input should
  map directly to that operation identity. Existing `--idempotency-key` support
  can remain as an alias where already present.

- D003: Accept `wavekit:<uuid>` as an opaque bounded operation key for
  WaveKit-facing writes.
  Rationale: decision ledger keys such as `P2POP-<24 hex>` are governance
  event ids, not the right public shape for WaveKit worker retries.

- D004: Build `p2p project snapshot --format json` as a summarized read model,
  not as a raw dump.
  Rationale: Angular needs one overview read, while detail pages can call
  dedicated list/show commands. The snapshot must stay bounded.

- D005: Proposal-bound structured contributions are P2P memory.
  Rationale: a direct P2P/MCP agent must see suggestions, objections, findings,
  open questions and alternatives attached to a proposal. Generic project chat
  and mediator conversations remain WaveKit application data.

- D006: Do not use MCP stdio as the WaveKit worker transport.
  Rationale: MCP stdio is useful for agents that reason through tools. A server
  worker needs a simpler retryable command boundary with receipts and stable
  process exits.

- D007: Defer the implementation version bump until behavior exists.
  Rationale: the source tree should not advertise `0.4.10` before the contract
  is implemented and tested. A release task will then bump all guarded current
  references together.

## Components

- `src/p2p_engine/cli_contract.py`: keep the envelope, parser normalization,
  stable error helpers and JSON output primitives.
- `src/p2p_engine/cli.py`: extend `p2p init` with JSON output and
  `--operation-key`; register `p2p project snapshot` if implemented at the
  root project app level.
- `src/p2p_engine/cli_commands/project_ops.py`: host project snapshot CLI and
  project read-model presentation.
- `src/p2p_engine/services/project_initialization.py`: return an init result
  that can be fingerprinted, receipted and serialized to JSON.
- `src/p2p_engine/services/project_state.py`,
  `src/p2p_engine/services/project_progress.py`,
  `src/p2p_engine/services/project_readiness_convergence.py`,
  `src/p2p_engine/services/project_publication.py`,
  `src/p2p_engine/services/derived_freshness.py`: likely snapshot inputs.
- `src/p2p_engine/cli_commands/proposal_core.py`: add JSON and operation-key
  support for proposal list/show/create/update.
- `src/p2p_engine/services/proposals.py` and proposal document/review services:
  provide typed proposal read/write results.
- `src/p2p_engine/cli_commands/proposal_contributions.py`: add JSON,
  operation-key support, filters and optional review command.
- `src/p2p_engine/core/contribution.py`: add review-state model only if
  moderation is implemented.
- `src/p2p_engine/core/mutation_receipts.py` and
  `src/p2p_engine/services/mutation_receipts.py`: generalize receipt support
  for init/proposal/contribution operation keys and `wavekit:<uuid>`.
- `src/p2p_engine/cli_commands/mutations.py`: expose status lookup for
  `--operation-key`.
- `src/p2p_engine/mcp/catalog/*` and `src/p2p_engine/mcp/handlers/*`: preserve
  protocol-native behavior and update descriptions/parity tests where needed.
- `src/p2p_engine/services/agent_capabilities.py` and generated templates:
  update agent-facing guidance.
- `docs/`, `README.md`, `CHANGELOG.md`: document the 0.4.10 contract and
  release.
- `tests/`: add focused service, CLI, MCP/catalog, contract, wheel and version
  tests.

## Data And Contracts

### Success Envelope

All WaveKit-facing JSON commands return:

```json
{
  "contract_version": "p2p-cli/v1",
  "ok": true,
  "operation": "project.snapshot",
  "data": {},
  "warnings": [],
  "error": null
}
```

Failures keep the same envelope and set `ok: false`, `data: null` and
`error.code`, `error.message`, `error.details`.

### Operation Keys

WaveKit supplies:

```text
--operation-key wavekit:<uuid>
```

The raw key is never persisted in paths. Receipt storage hashes the key and
binds a canonical request fingerprint. The fingerprint includes operation id,
semantic inputs, actor/owner fields that affect output, target proposal or
contribution identifiers and expected state tokens when relevant.

The receipt result statuses are:

- `applied`
- `already_applied`
- `conflict`
- `postcondition_drift`
- `incomplete`
- `corrupt`
- `not_found`

Existing `--idempotency-key` can remain for previous vertical lifecycle
commands, but WaveKit-facing new commands expose `--operation-key`.

### Project Snapshot Data

The snapshot read model should be structured as:

```text
project_snapshot:
  project
  runtime
  workspace_schema
  transactions
  vertical
  sections
  readiness
  proposals
  decisions
  outputs
  derived_state
  limits
```

`proposals`, `decisions` and `outputs` are summaries. Detail screens call
dedicated list/show commands.

### Proposal Data

Proposal list returns summaries. Proposal show returns:

```text
proposal_detail:
  proposal_id
  title
  status
  core_sections
  decision
  readiness
  artifact_state
  questions
  contributions
  next_actions
  limits
```

Contribution groups may be included in detail, but must be bounded and mark
truncation.

### Contribution Data

Contribution list returns:

```text
contributions:
  proposal_id
  filters
  items[]
  counts_by_type
  limits
```

Each item includes stable id, contribution type, relevance, author, text, and
created/review metadata when available.

If review state is implemented, use an append-only or auditable model:

```text
review:
  status: proposed | relevant | rejected
  actor
  reason
  reviewed_at
```

Review must never erase the original contribution text.

## Public Surface And MCP Parity

CLI is the authoritative machine boundary for WaveKit worker retries. MCP stdio
does not receive the `p2p-cli/v1` envelope and does not become the WaveKit
server-worker transport.

MCP parity for this feature means:

- existing project/proposal/contribution MCP descriptions must not contradict
  the CLI contract;
- direct P2P agents must understand which proposal and contribution operations
  are available;
- if an existing MCP tool exposes the same domain read, its payload should stay
  semantically coherent with the CLI read model;
- if MCP lacks an equivalent operation, the generated guidance must state that
  the operation is CLI-only for now.

## Error Handling

Use stable codes, not parsed messages. Expected classes:

- invalid request: missing/malformed operation key, invalid filter, invalid
  contribution type, empty proposal update;
- not found: missing proposal or contribution id;
- conflict/precondition: divergent replay, incompatible existing init state,
  stale expected state, unsupported schema, pending recovery;
- internal: unexpected exceptions after the CLI boundary catches JSON mode.

Errors should be safe for WaveKit audit records. They should not include raw
operation keys, full request payloads, secrets, registry credentials or
filesystem internals beyond governed relative evidence paths.

## Migration And Compatibility

No historical workspace compatibility is added. The current runtime supports
workspace schema 3 only.

The feature is additive for human users. Machine users get new stable JSON
surfaces under `p2p-cli/v1`. Existing vertical lifecycle idempotency remains
compatible. New WaveKit-facing commands standardize on `--operation-key`.

Version references are bumped to `0.4.10` only after implementation evidence
exists. The release block updates:

- `pyproject.toml`
- `src/p2p_engine/__init__.py`
- `README.md`
- `docs/INSTALL.md`
- `docs/CLI-GUIDE.md`
- `docs/CLI-CONTRACT.md`
- `docs/WORKSPACE-SCHEMA.md`
- `CHANGELOG.md`
- version-consistency tests

## Risks And Tradeoffs

- The feature is broad because WaveKit needs both read models and safe writes.
  The implementation should still land in internal blocks.
- Adding contribution review state could expand persistence scope. If it is too
  large for 0.4.10, the implementation must explicitly document that WaveKit UI
  promote/reject controls remain unsupported instead of shadowing status in
  PostgreSQL.
- Init receipts are harder than post-init receipts because `.p2p` may not
  exist yet. The design should place receipt creation inside the bootstrap
  candidate and fail closed when an existing workspace conflicts.
- Snapshot composition can become expensive. The read model must be bounded and
  should reuse existing services rather than loading unbounded history.
- Maintaining release version references is currently manual but guarded by
  tests. A future release tooling feature may centralize or generate more of
  those references.

## Out Of Scope

- WaveKit server/client implementation.
- MCP HTTP OAuth/device-flow behavior.
- AI mediator behavior.
- Git/delivery workflow management.
- Universal JSON coverage for every P2P command.
