# Requirements - Expose Receipt-Backed Proposal Readiness Assessment

## Origin

- Source: owner-requested technical analysis of P2P Engine and WaveKit.
- Baseline release: P2P Engine `0.4.10`.
- Target release: P2P Engine `0.4.11`.
- Related implemented feature:
  `prop-002-support-wavekit-cli-json-contracts`.
- Motivation: WaveKit can read proposal readiness through
  `p2p proposal show PROP --format json`, but P2P Engine `0.4.10` does not
  expose a receipt-backed JSON mutation for recalculating that readiness.

## Goal

Expose one robust proposal-readiness recalculation operation that WaveKit can
invoke through the allowlisted CLI boundary without parsing human output,
accessing `.p2p` directly, importing P2P Engine internals, or risking duplicate
or partially committed writes after retries and worker failures.

The same domain implementation must keep standalone CLI and MCP use coherent,
while WaveKit-specific authentication, authorization, queuing and operational
revision control remain outside P2P Engine.

## In Scope

- A receipt-backed JSON form of `p2p proposal readiness assess`.
- A stable `proposal.readiness.assess` operation under `p2p-cli/v1`.
- `--operation-key` and `--actor` support for the WaveKit-facing mutation.
- A pure assessment plan that calculates the final readiness candidate without
  writing intermediate state.
- Atomic commit of `readiness.yml` and its durable mutation receipt.
- Exact replay, divergent-key conflict, receipt status and recovery behavior.
- A deterministic fingerprint of all canonical inputs used by the assessment.
- Read-time readiness freshness classification in the proposal detail contract.
- Preservation of owner override metadata during recalculation.
- Coherent behavior for human CLI and local MCP readiness assessment.
- Focused service, transaction, receipt, CLI, MCP and public-contract tests.
- Documentation and generated agent guidance needed by the new surface.
- Release reference convergence from `0.4.10` to `0.4.11` after implementation.

## Out Of Scope

- WaveKit Django models, migrations, APIs, workers, PostgreSQL projections,
  Angular controls, WebSocket delivery or operation polling.
- Using MCP stdio as the WaveKit worker transport.
- Direct WaveKit access to `.p2p` files or P2P Engine Python internals.
- Automatic recalculation after every proposal, contribution, question or
  artifact mutation.
- A background timer or polling loop that mutates readiness automatically.
- A new mutating command for overall project readiness.
- Changing proposal acceptance, rejection, deferral or owner-override policy.
- Receipt-backed conversion of every existing proposal readiness command.
- Broad redesign of readiness scoring criteria or thresholds.
- Historical workspace conversion or support for non-current workspace schemas.
- WaveKit fixture and projection corrections, which require a follow-up WaveKit
  implementation after the P2P Engine release exists.

## Public Surface And MCP Impact

- CLI impact: additive write-safe JSON mutation for
  `p2p proposal readiness assess`; existing human output remains supported.
- MCP impact: preserve the protocol-native
  `p2p_proposal_readiness_assess` tool and route it through the same atomic
  domain implementation. MCP does not receive a `p2p-cli/v1` wrapper and does
  not become the WaveKit retry transport.
- Storage impact: compatible additions to proposal readiness metadata and a new
  supported internal mutation-receipt operation. No new public `.p2p` layout is
  exposed.
- Agent-facing behavior: guidance must distinguish assessment, stored result,
  freshness and project-level progress.
- MCP parity decision: required for domain semantics and atomicity, but not for
  the CLI-specific operation-key transport contract.

## Functional Requirements

### Assessment Semantics

- R001: `proposal readiness assess` SHALL recalculate proposal readiness from
  the current canonical proposal artifacts, structured proposal questions,
  proposal artifact state and selected readiness profile.
- R002: The assessment SHALL produce the same readiness criteria, score, label,
  confidence, failed gates, missing evidence, suggested next actions and owner
  question state currently exposed by the evidence-aware assessment.
- R003: Assessment SHALL remain advisory and SHALL NOT accept, reject, defer,
  override or otherwise decide a proposal.
- R004: Assessment SHALL NOT require owner decision authority. The supplied
  actor is audit identity and part of the mutation request identity, not an
  impersonated project owner.
- R005: Existing owner override fields SHALL be preserved exactly when the
  computed assessment is recalculated.
- R006: Assessing a proposal without a previous `readiness.yml` SHALL create one
  final assessed snapshot without first persisting a `not_assessed` or
  bootstrap-only intermediate snapshot.

### Pure Planning And Source Fingerprint

- R007: The readiness service SHALL expose or internally use a pure assessment
  planning step that returns the final validated readiness candidate without
  changing project state.
- R008: The assessment plan SHALL identify every source whose contents can
  affect the computed result, including the readiness profile and relevant
  proposal narrative, question and artifact-state inputs.
- R009: Missing optional source files SHALL be represented explicitly in the
  source snapshot so absence and an empty file cannot be confused.
- R010: The plan SHALL calculate a deterministic aggregate
  `source_fingerprint_sha256` from logical source identifiers, source presence,
  physical content hashes and the assessment policy version, without including
  raw source contents.
- R011: The source fingerprint SHALL cover at least `proposal.md`,
  `suggested-scope.md`, `alternatives.md`, `findings.md`, `risks.md`,
  `assumptions.md`, `execution-plan.md`, `impact-map.yml`, `questions.yml`,
  `artifact-state.yml` and the active readiness profile.
- R012: The existing readiness file SHALL be a transaction source precondition
  because override metadata may be preserved from it, but SHALL NOT be included
  recursively in the evidence source fingerprint.
- R013: The persisted readiness snapshot SHALL record the assessment policy
  version and the source fingerprint used to calculate it.

### Freshness

- R014: Proposal readiness reads SHALL classify freshness as exactly one of
  `not_assessed`, `current` or `stale`.
- R015: An assessed readiness snapshot SHALL be `current` only when its stored
  source fingerprint matches a newly calculated fingerprint of current
  canonical sources under the same assessment policy.
- R016: A stored assessed snapshot without the new source fingerprint SHALL be
  classified as `stale`, not silently treated as current.
- R017: `p2p proposal show PROP --format json` SHALL expose freshness and the
  stored and current source fingerprints inside `proposal_detail.readiness`.
- R018: Freshness inspection SHALL be read-only and SHALL NOT create a profile,
  readiness snapshot or any other project-state file.
- R019: A mutation receipt SHALL remain `applied` when later proposal evidence
  changes; later evidence drift affects readiness freshness, not the historical
  fact that the recorded mutation completed successfully.

### Receipt-Backed Atomic Mutation

- R020: JSON assessment SHALL require a non-empty bounded `--operation-key`
  accepted by the existing WaveKit-facing operation-key validator.
- R021: The mutation request fingerprint SHALL bind the operation, proposal id,
  actor and assessment policy inputs, while the result SHALL separately record
  the evidence source fingerprint used for the calculation.
- R022: Replaying the same operation key with the same semantic request SHALL
  return `already_applied` and the original result without recalculating or
  rewriting readiness.
- R023: Reusing an operation key with a different proposal, actor or other
  semantic request input SHALL fail with `P2P_IDEMPOTENCY_CONFLICT` and no
  writes.
- R024: The readiness candidate and mutation receipt SHALL commit in one
  `AtomicMutationWriter` transaction guarded by the workspace transaction lock.
- R025: Every source used by the calculation SHALL be registered as a source
  precondition so a concurrent source change before commit fails without
  publishing a readiness result calculated from a mixed snapshot.
- R026: The receipt SHALL use operation `proposal_readiness_assess`, public
  operation id `proposal.readiness.assess`, the proposal id, actor, bounded
  readiness summary, source fingerprint and canonical changed paths.
- R027: The receipt SHALL persist only a hash of the operation key and SHALL NOT
  persist the raw key or full source contents.
- R028: `p2p mutation status --operation-key KEY --format json` SHALL recognize
  readiness-assessment receipts and return a sanitized public result.
- R029: A lost response after commit SHALL be recoverable by exact retry or
  mutation-status lookup without applying the assessment twice.
- R030: Transaction interruption SHALL use the existing workspace recovery
  classification and SHALL never leave a final readiness file without either a
  matching committed receipt or an explicitly recoverable transaction.

### CLI JSON Contract

- R031: The CLI SHALL support:
  `p2p proposal readiness assess PROP --actor ACTOR --operation-key KEY
  --format json --root ROOT`.
- R032: The JSON response SHALL use the existing `p2p-cli/v1` envelope and
  operation `proposal.readiness.assess`.
- R033: Successful response data SHALL contain `proposal_readiness_assess` and
  `mutation` objects with stable documented fields.
- R034: `proposal_readiness_assess` SHALL include proposal id, readiness status,
  profile id/version, computed score/label, confidence, failed gates, missing
  evidence, suggested next actions, owner question state, policy version and
  source fingerprint.
- R035: `mutation` SHALL expose `applied` or `already_applied`, operation id,
  actor, canonical changed paths, recovery requirement and a safe message.
- R036: JSON stdout SHALL contain exactly one complete JSON document and no
  human or Rich output.
- R037: JSON parser, validation, domain, transaction and receipt failures SHALL
  use stable error codes and non-zero exits without exposing operation keys,
  source contents, credentials or unsafe absolute paths.
- R038: `--operation-key` SHALL be required for JSON mutation mode and SHALL
  remain unnecessary for the existing human text mode.
- R039: Existing human `proposal readiness assess` output SHALL remain usable,
  but the underlying write SHALL use the same single-candidate atomic domain
  implementation.

### MCP And Standalone Use

- R040: `p2p_proposal_readiness_assess` SHALL calculate the same readiness
  result as the CLI operation for the same project state.
- R041: MCP assessment SHALL use the shared atomic assessment implementation
  and SHALL NOT call a direct multi-write legacy path.
- R042: MCP output SHALL remain protocol-native and SHALL continue to state
  that no owner governance decision or override was performed.
- R043: Existing standalone P2P users SHALL remain able to assess readiness
  without WaveKit, Django, Redis, PostgreSQL or a cloned WaveKit repository.

### Project-Level Readiness Boundary

- R044: This feature SHALL document that project definition completeness and
  declared evidence coverage are derived read models, not persisted proposal
  readiness snapshots.
- R045: Existing `p2p project snapshot --format json`,
  `p2p project progress --format json` and
  `p2p project readiness review --format json` SHALL remain read-only.
- R046: This feature SHALL NOT add a generic project-readiness recalculation
  mutation merely to refresh a WaveKit screen.
- R047: `p2p assess refresh` SHALL remain a separate operational project
  assessment and SHALL NOT be documented as equivalent to vertical-based
  project definition completeness.

### Documentation And Release

- R048: CLI contract, CLI guide, MCP documentation, primitive inventory and
  generated agent guidance SHALL describe the implemented assessment and
  freshness behavior consistently.
- R049: Documentation SHALL continue to direct machine consumers to
  `p2p proposal show PROP --format json` for readiness reads.
- R050: Documentation SHALL direct WaveKit-style deterministic workers to the
  receipt-backed JSON assess command for readiness recalculation.
- R051: Current release references SHALL move from `0.4.10` to `0.4.11` only
  after source, tests and documentation provide implementation evidence.
- R052: Historical release notes and immutable old release examples SHALL not be
  rewritten merely to remove valid historical `0.4.10` references.

## Non-Functional Requirements

- N001: The final readiness mutation SHALL be atomic, crash-recoverable and
  safe under concurrent source changes.
- N002: Exact retries SHALL be idempotent after response loss, worker restart
  and client timeout.
- N003: Read-only freshness inspection SHALL have no persistent side effects.
- N004: Public payloads SHALL be deterministic, bounded and safe for WaveKit
  logs after WaveKit applies its own authorization policy.
- N005: The implementation SHALL reuse the current receipt and workspace
  transaction architecture rather than create a second mutation mechanism.
- N006: The implementation SHALL keep readiness calculation independent from
  CLI formatting, MCP transport and WaveKit concepts.
- N007: The implementation SHALL preserve Python 3.11+ compatibility.
- N008: The feature SHALL avoid unrelated readiness scoring, proposal lifecycle
  or workspace-schema refactors.
- N009: Focused tests SHALL use temporary roots and deterministic fixtures, with
  fault injection at the atomic transaction boundary where useful.
- N010: Public-contract behavior SHALL be tested from the source tree and from a
  built wheel before release.

## Edge Cases And Errors

- Missing or malformed operation key in JSON mode.
- Same operation key used by a different actor or proposal.
- Missing proposal.
- Proposal without an existing readiness snapshot.
- Existing assessed readiness without a source fingerprint.
- Missing, invalid or changed readiness profile.
- Missing optional narrative artifacts.
- Invalid structured questions or artifact-state data.
- Owner override present while readiness is recalculated.
- Source changed between assessment planning and lock-protected commit.
- Active or interrupted workspace transaction.
- Process interruption before journal creation, during replacement, after
  readiness replacement or after receipt replacement.
- Response lost after successful commit.
- Receipt missing, corrupt or in postcondition drift.
- Exact retry after later proposal evidence changed.
- New operation key with unchanged proposal evidence.
- Unsupported runtime or workspace schema.
- Proposal detail read on `not_assessed`, `current` and `stale` readiness.

## Acceptance Criteria

- AC001: `p2p proposal readiness assess ... --format json --operation-key
  wavekit:<uuid>` returns a valid `p2p-cli/v1` success envelope.
- AC002: One assessment writes only the final readiness candidate and receipt
  in one atomic transaction; no intermediate readiness snapshot is observable.
- AC003: Exact replay returns `already_applied`; divergent key reuse fails with
  no additional readiness write.
- AC004: Mutation status recognizes a completed readiness assessment and
  returns its sanitized result without the raw key.
- AC005: Fault-injection tests prove complete rollback or explicit recovery for
  every interruption point that can occur after replacement begins.
- AC006: A concurrent source change is detected before commit and no readiness
  result from mixed source versions is published.
- AC007: Owner override metadata survives reassessment unchanged.
- AC008: Proposal detail reports `not_assessed`, `current` and `stale`
  accurately without writing project state.
- AC009: Human CLI and MCP assessment return semantically equivalent readiness
  results and use the shared atomic domain implementation.
- AC010: Project snapshot, project progress and project readiness review remain
  read-only and no global readiness mutation is introduced.
- AC011: CLI/MCP docs, generated guidance and primitive inventory match the
  implemented surface and keep the WaveKit CLI/MCP transport boundary clear.
- AC012: Focused tests, public-contract tests, installed-wheel smoke and the
  full suite pass, or any residual risk is explicitly recorded before release.

