# Requirements - Support WaveKit CLI JSON Contracts

## Origin

- Accepted P2P proposal: `PROP-002`, "Support WaveKit CLI JSON contracts".
- Owner decision: accepted by `mrjungle` on 2026-08-06.
- Decision event: `PDE-18fc8d4f7b74828934d28f6f`.
- Target release: P2P Engine `0.4.10`.
- Baseline release: P2P Engine `0.4.9`.

## Goal

Expose a stable, allowlisted CLI JSON contract that lets WaveKit's P2P worker
read and mutate project memory without parsing human text, importing P2P Python
internals, inspecting `.p2p` files, or routing deterministic server work
through MCP stdio.

## In Scope

- A documented WaveKit-facing CLI command inventory.
- `p2p project snapshot --format json`.
- `p2p init --format json --operation-key`.
- `p2p proposal list/show --format json`.
- `p2p proposal create/update --format json --operation-key`.
- Proposal readiness and question JSON reads needed by WaveKit.
- `p2p proposal contribution add/list --format json`.
- A governed contribution review or relevance surface if WaveKit needs
  promote/reject controls.
- Mutation status lookup for WaveKit operation keys.
- Stable JSON fixtures, parser/error tests, docs, generated agent guidance and
  MCP stdio descriptions.
- Release reference bump from `0.4.9` to `0.4.10` when the implementation is
  complete.

## Out Of Scope

- WaveKit Django, Angular, PostgreSQL, Redis, MCP HTTP or mediator code.
- WaveKit users, memberships, authorization, WebSocket or notification models.
- Direct `.p2p` parsing by WaveKit.
- Calling local P2P MCP stdio from the WaveKit worker.
- Adding `--format json` indiscriminately to the entire CLI.
- Git, branch, pull request, CI or delivery-workflow orchestration.
- Historical workspace compatibility beyond the current supported schema.

## Public Surface And MCP Impact

- CLI impact: additive JSON read surfaces and write-safe operation-key
  mutations under the existing `p2p-cli/v1` envelope.
- MCP impact: protocol-native MCP payloads are preserved. Existing MCP stdio
  proposal/project tools and generated guidance must describe the same project
  memory concepts and clearly state that WaveKit server-worker retry semantics
  use the CLI contract, not MCP stdio.
- Storage impact: compatible internal receipt records for new WaveKit-facing
  writes; no user-facing `.p2p` layout contract is exposed.
- Agent-facing behavior: updated generated skills/instructions explain the
  available CLI JSON surfaces for standalone P2P use and the MCP stdio boundary.
- MCP parity decision: no `p2p-cli/v1` envelope wrapping is added to MCP. If an
  existing MCP tool already exposes the same domain operation, its payload must
  remain coherent with the CLI read model, but idempotent WaveKit worker writes
  are CLI-first in this feature.

## Functional Requirements

### Command Inventory And Envelope

- R001: THE SYSTEM SHALL document the WaveKit-facing CLI command set and mark
  each command as read-only, write-safe, status/read-recovery, or explicitly
  out of scope.
- R002: Every WaveKit-facing JSON response SHALL use the existing
  `p2p-cli/v1` envelope fields `contract_version`, `ok`, `operation`, `data`,
  `warnings` and `error`.
- R003: WaveKit-facing JSON commands SHALL emit one complete JSON document to
  stdout and no Rich or human prose to stdout.
- R004: Command-specific payloads SHALL be typed and documented under `data`;
  consumers SHALL dispatch by `operation` and command-specific payload type.
- R005: Parser, validation and domain failures in JSON mode SHALL use stable
  error codes and exit classes, with no secret material in stdout or stderr.
- R006: The implementation SHALL not require WaveKit to inspect `.p2p`, parse
  human text, or import `p2p_engine` internals.
- R007: Existing human text output SHALL remain usable unless a task explicitly
  records a breaking CLI text change.

### Project Snapshot

- R008: `p2p project snapshot --format json` SHALL return a read-only,
  bounded project snapshot suitable for WaveKit's Angular overview.
- R009: The snapshot SHALL include project identity, runtime contract status,
  workspace schema status, transaction/recovery status, active vertical lock,
  selected structure sections, readiness summary, proposal counts and summaries,
  decision counts and summaries, output/publication status and derived-state
  freshness.
- R010: The snapshot SHALL include enough summary data for the project overview
  to render without immediate follow-up CLI calls.
- R011: The snapshot SHALL not include full proposal bodies, full contribution
  text collections or unbounded histories; detailed screens SHALL use dedicated
  list/show commands.
- R012: Snapshot summaries SHALL be deterministically ordered and bounded with
  documented limits and truncation metadata.
- R013: Snapshot data SHALL use stable identifiers for proposals, decisions,
  sections, outputs and active vertical coordinates.
- R014: Snapshot failure on incompatible runtime, unsupported schema or pending
  transaction recovery SHALL return a typed JSON error rather than partial
  ambiguous data.

### Idempotent Project Initialization

- R015: `p2p init` SHALL accept `--format json` for non-interactive use.
- R016: `p2p init` SHALL accept `--operation-key` for WaveKit-facing writes.
- R017: WaveKit-facing operation keys SHALL allow the opaque bounded format
  `wavekit:<uuid>`; existing receipt keys and compatibility aliases SHALL not
  force WaveKit to use decision-ledger `P2POP-<24 hex>` keys.
- R018: `p2p init --operation-key KEY --format json` SHALL persist a durable
  receipt in the same committed initialization boundary as the created `.p2p`
  state.
- R019: Replaying the same init operation key with the same semantic request
  SHALL return success status `already_applied` and the original result summary
  without repeating side effects.
- R020: Reusing an init operation key with different semantic inputs SHALL fail
  with a conflict code and no writes.
- R021: Init receipts SHALL include the operation, key hash, request
  fingerprint, actor/owner when supplied, result summary and postcondition
  hashes, without storing the raw operation key.
- R022: Init JSON data SHALL include created paths, selected agent profile,
  repository mode, remote profile status, selected vertical, warnings, MCP hint
  metadata and next-step hints.
- R023: Init SHALL fail safely if it sees an incompatible existing workspace,
  pending transaction recovery or unsupported schema.
- R024: Interactive init behavior SHALL remain available when no machine JSON
  invocation is requested.

### Proposal Reads

- R025: `p2p proposal list --format json` SHALL return bounded proposal
  summaries including proposal id, title, status, decision status, readiness
  summary, contribution counts, updated evidence hints and stable ordering.
- R026: `p2p proposal list --format json` SHALL support filters required by
  WaveKit screens, including status and decision state when available.
- R027: `p2p proposal show PROP --format json` SHALL return a typed proposal
  detail read model including core sections, decision, readiness, artifact
  state, question state, grouped contributions and next actions.
- R028: Full proposal bodies and contribution lists SHALL remain bounded and
  include truncation metadata when limits are applied.
- R029: Missing proposal ids SHALL return a stable not-found JSON error.

### Proposal Writes

- R030: `p2p proposal create --format json --operation-key KEY` SHALL create a
  proposal through the existing governed proposal service and return a durable
  receipt.
- R031: Replaying the same proposal create operation key with the same semantic
  request SHALL return `already_applied` and the same proposal identity.
- R032: Reusing a create operation key with different semantic inputs SHALL
  fail with an idempotency conflict and no new proposal.
- R033: `p2p proposal update --format json --operation-key KEY` SHALL update
  structured proposal sections through a durable idempotent mutation.
- R034: Proposal update SHALL reject empty updates, missing proposals,
  incompatible runtime state and divergent operation-key replays with stable
  JSON errors.

### Proposal Contributions

- R035: `p2p proposal contribution add --format json --operation-key KEY`
  SHALL append one structured contribution to a proposal through a durable
  idempotent mutation.
- R036: Contribution add SHALL preserve existing supported contribution types
  and SHALL explicitly support the WaveKit UI types `suggestion`, `objection`,
  `finding`, `open_question` and `alternative`.
- R037: Replaying the same contribution operation key with the same semantic
  request SHALL return `already_applied` and the same contribution identity.
- R038: `p2p proposal contribution list --format json` SHALL return typed,
  bounded contributions with id, type, author, relevance, text summary or text,
  created/updated metadata when available and deterministic ordering.
- R039: Contribution list SHALL support filtering by contribution type so
  WaveKit can render one card and one list per type.
- R040: If WaveKit needs promote/reject controls, THE SYSTEM SHALL expose a
  governed contribution review primitive or documented review fields rather
  than requiring WaveKit to store project-memory status only in PostgreSQL.
- R041: A contribution review primitive, if implemented, SHALL be idempotent
  with `--operation-key`, preserve audit actor/reason and support at least
  `relevant` and `rejected` states.
- R042: Contribution review SHALL not delete or rewrite original contribution
  text; rejection is a governed classification, not data loss.
- R042a: For 0.4.10, contribution review/promote/reject is explicitly
  unsupported. Contribution JSON payloads SHALL expose review capability as
  unsupported so WaveKit does not create PostgreSQL-only shadow project-memory
  status.
- R043: Chat and mediator conversations are outside P2P contribution memory
  unless WaveKit explicitly writes a structured proposal-bound contribution.
- R044: Standalone agents using P2P without WaveKit SHALL be able to discover
  and use the same contribution read/write CLI contract.

### Readiness, Questions And Mutation Status

- R045: Proposal readiness and proposal question commands required by WaveKit
  SHALL support `--format json` or be listed as already compliant with stable
  `p2p-cli/v1` fixtures.
- R046: `p2p mutation status` SHALL support WaveKit operation keys through
  `--operation-key` or a documented alias equivalent to `--idempotency-key`.
- R047: Mutation status SHALL classify `not_found`, `applied`,
  `already_applied`, `incomplete`, `corrupt`, `conflict` and
  `postcondition_drift` without exposing raw operation keys or request payloads.
- R048: All WaveKit-facing write errors SHALL be safe to surface in WaveKit
  audit logs and user-facing failure summaries after WaveKit applies its own
  authorization policy.
- R049: JSON golden fixtures SHALL cover success, replay, divergent-key
  conflict, missing target, stale state and parser errors for each write class.

### Documentation, Guidance And Release

- R050: `docs/CLI-CONTRACT.md`, `docs/CLI-GUIDE.md`, `docs/INSTALL.md` and
  `README.md` SHALL document the 0.4.10 WaveKit-facing contract and the
  supported retry pattern.
- R051: Generated agent capabilities and templates SHALL explain that P2P
  project memory is accessed through CLI/MCP tools, not direct `.p2p` edits,
  and SHALL list the proposal/contribution JSON surfaces relevant to agents.
- R052: MCP stdio catalog descriptions SHALL remain accurate for project,
  proposal and contribution operations and SHALL not imply that WaveKit worker
  idempotency is handled through MCP stdio.
- R053: Release references SHALL be bumped from `0.4.9` to `0.4.10` only when
  implementation evidence exists.
- R054: Version consistency tests SHALL guard `pyproject.toml`, package
  `__version__`, MCP server version, release URLs and current contract docs.
- R055: The feature SHALL include an implementation note that maps completed
  code, tests and docs back to `PROP-002`.

## Non-Functional Requirements

- N001: JSON payload ordering SHALL be deterministic where ordering affects
  tests or WaveKit diffs.
- N002: Read payloads SHALL be bounded and include truncation metadata when
  limits are reached.
- N003: Write retries SHALL be safe after response loss, process interruption
  or worker restart.
- N004: Receipt paths SHALL be derived from hashes and SHALL not expose raw
  operation keys.
- N005: The feature SHALL avoid broad refactors not needed for the WaveKit
  contract.
- N006: The implementation SHALL preserve Python 3.11+ compatibility.
- N007: Public contract tests SHALL run both from the source tree and from a
  built wheel where practical.

## Edge Cases And Errors

- Missing or malformed `--operation-key`.
- Same operation key with different semantic inputs.
- Response lost after mutation commit.
- Existing initialized workspace receives a conflicting init request.
- Unsupported workspace schema.
- Pending transaction recovery.
- Missing proposal id.
- Invalid contribution type.
- Contribution list filter with no matching items.
- Contribution review requested when the target status is already set.
- Snapshot requested while derived project state is stale.
- JSON mode parser errors before command handler execution.

## Acceptance Criteria

- AC001: The WaveKit CLI inventory is documented and guarded by tests.
- AC002: Snapshot, init, proposal read/write, contribution read/write and
  mutation status JSON responses parse as `p2p-cli/v1`.
- AC003: `p2p init` replay after simulated response loss returns
  `already_applied` and does not rewrite unrelated files.
- AC004: Proposal create/update replay and conflict behavior is covered by
  focused tests.
- AC005: Contribution add/list by type is covered by focused service and CLI
  tests.
- AC006: Contribution promote/reject capability is either implemented through a
  governed P2P primitive or explicitly documented as unsupported with no
  WaveKit-only shadow status.
- AC007: Parser and domain errors have stable codes and non-zero exits.
- AC008: MCP stdio docs/catalog and generated agent guidance match the final
  public surfaces.
- AC009: `pyproject.toml`, package `__version__`, README, install docs and
  current contract docs consistently reference `0.4.10`.
- AC010: Focused tests, public CLI/MCP contract tests, wheel smoke and the full
  suite pass or residual risk is explicitly recorded.
