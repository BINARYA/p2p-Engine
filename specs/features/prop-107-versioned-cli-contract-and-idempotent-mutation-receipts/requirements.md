# Requirements - Versioned CLI Contract And Idempotent Mutation Receipts

## Origin

- Accepted P2P proposal: `PROP-107`.
- Owner decision: accepted by `mrjungle` on 2026-08-03.
- Target release: P2P Engine `0.4.6`.
- Uniform JSON is an explicitly approved coordinated breaking change for
  machine consumers, including WaveKit.

## Goal

Give every machine-facing CLI response one versioned transport envelope, expose
runtime and persistence contract versions directly, and make vertical apply
operations safely retryable after response loss through durable atomic
idempotency receipts.

## In Scope

- Inventory and normalization of every CLI command supporting JSON output.
- Common success/error envelope and stable exit policy.
- Parser/argument errors normalized when JSON mode is requested.
- `p2p version --format json`.
- Idempotency keys and receipts for vertical install/adopt/migrate apply.
- Mutation receipt lookup and response-loss/crash/replay tests.
- WaveKit golden fixtures and migration guidance.

## Out Of Scope

- One universal domain payload for all operations.
- Converting human help/text output to JSON.
- Time-based preview expiry.
- Retrofitting idempotency to every historical mutation in 0.4.6.
- Registry transport and draft lifecycle semantics.

## Functional Requirements

### JSON Envelope

- R001: Every successful CLI response requested as JSON SHALL contain exactly
  the transport fields `contract_version`, `ok`, `operation`, `data`,
  `warnings` and `error`, plus explicitly documented future additive fields.
- R002: `contract_version` SHALL equal `p2p-cli/v1` for release 0.4.6.
- R003: Successful responses SHALL set `ok: true`, `error: null`, a stable
  operation identifier and command-specific typed `data`.
- R004: Failed responses SHALL set `ok: false`, preserve the operation when
  known, set `data: null`, and include `error.code`, `error.message` and typed
  `error.details`.
- R005: `warnings` SHALL always be an array and SHALL not be used for fatal
  errors.
- R006: JSON mode SHALL emit one complete JSON document to stdout and no human
  prose, progress or Rich formatting to stdout.
- R007: Diagnostics not represented in the envelope MAY go to stderr but SHALL
  contain no secret material.

### Parser And Exit Behavior

- R008: Invalid options, missing arguments and type conversion failures SHALL
  use the JSON error envelope when the invocation requests JSON.
- R009: Stable exit classes SHALL distinguish success, invalid request,
  conflict/precondition, authorization, unavailable dependency/transport and
  internal failure.
- R010: Domain error codes SHALL remain stable independently of human messages
  and command-specific payload evolution.
- R011: Text-mode command output and help SHALL remain human-oriented.

### Version Discovery

- R012: `p2p version` SHALL report the installed engine version in text mode.
- R013: `p2p version --format json` SHALL report engine version, CLI contract,
  current workspace schema, current vertical-pack schema and portable package
  format in the common envelope.
- R014: Version discovery SHALL be read-only and SHALL work outside a project
  root.
- R015: Version values SHALL come from the same constants used by runtime
  validation and package metadata.

### Idempotency Request

- R016: Vertical install/adopt/migrate apply SHALL require a non-empty caller-
  supplied idempotency key in addition to current token, confirmation and actor
  inputs.
- R017: The request fingerprint SHALL bind operation, normalized semantic
  inputs, actor, preview-token hash and relevant exact target identity.
- R018: Idempotency keys SHALL be treated as opaque, length-bounded values and
  SHALL not be used directly as filesystem names.
- R019: Preview SHALL remain read-only and SHALL not reserve an idempotency key.
- R020: Preview validity SHALL depend on semantic state/token preconditions and
  SHALL NOT expire only because wall-clock time elapsed.

### Durable Receipts

- R021: A successful apply SHALL persist a compact receipt containing key hash,
  operation, actor, request fingerprint, preview-token hash, completion status,
  result summary and resulting postcondition hashes.
- R022: The receipt SHALL be committed in the same durable workspace
  transaction as the project mutation.
- R023: Receipt persistence SHALL use a hashed path under
  `.p2p/.internal/mutation-receipts/` and SHALL never expose the raw key in the
  path.
- R024: Replaying the same key and exact request SHALL return success status
  `already_applied` and the recorded result without repeating side effects.
- R025: Reusing a key with a different fingerprint SHALL fail with
  `P2P_IDEMPOTENCY_CONFLICT` and no writes.
- R026: A receipt whose declared postconditions no longer match current state
  SHALL return `P2P_IDEMPOTENCY_POSTCONDITION_DRIFT` rather than replaying.
- R027: Recovery SHALL distinguish no receipt, committed receipt, incomplete
  transaction and corrupt receipt with stable states.
- R028: Receipts SHALL not be removed by normal successful transaction cleanup
  and SHALL have no time-based expiry in 0.4.6.

### Status Command

- R029: `p2p mutation status --idempotency-key KEY` SHALL return receipt state
  without mutating project state.
- R030: Status SHALL disclose operation, actor, completion status, result and
  postcondition match but SHALL not disclose the raw key, request payload or
  preview token.
- R031: Missing receipts SHALL return a successful `not_found` lookup result;
  corrupt/inconsistent receipts SHALL return a typed failure.

### Integration

- R032: WaveKit SHALL be able to use its operation UUID as the idempotency key
  and recover a response-lost apply with one exact replay or status lookup.
- R033: JSON fixtures for vertical install/adopt/migrate and mutation status
  SHALL be stable and documented.
- R034: Existing MCP tools SHALL keep their protocol-native payloads; CLI
  envelope normalization SHALL not wrap MCP protocol responses.

## Acceptance Criteria

- AC001: Every registered CLI `--format json` success and representative error
  parses as `p2p-cli/v1` with no preceding/following prose.
- AC002: Parser errors requested as JSON use the common envelope and a stable
  non-zero exit.
- AC003: Version works outside a project and values match package/runtime
  constants.
- AC004: Simulated response loss followed by exact replay returns
  `already_applied` and creates no duplicate mutation.
- AC005: Same key with changed coordinate, mapping, actor or token fails with
  `P2P_IDEMPOTENCY_CONFLICT`.
- AC006: Simulated failure cannot leave mutation without receipt or receipt
  without committed mutation.
- AC007: Mutation status distinguishes not found, applied, postcondition drift,
  incomplete and corrupt states.
- AC008: Focused transaction/CLI tests, public tests, wheel smoke and full suite
  pass.

## Public Surface Impact

- CLI: breaking JSON envelope, new version and mutation status commands, new
  required idempotency option on three apply commands.
- MCP: no envelope change; shared services gain receipt support.
- Storage: durable compact receipts under project internal state.
- Docs: CLI contract v1, exit policy, retry/recovery and WaveKit migration.
- Tests: command inventory, parser normalization, golden payload and fault
  injection coverage.

