# Design - Expose Receipt-Backed Proposal Readiness Assessment

## Requirements Covered

- R001-R052
- N001-N010
- AC001-AC012

## Decision Summary

P2P Engine will add one WaveKit-facing readiness mutation:

```text
p2p proposal readiness assess PROP \
  --actor ACTOR \
  --operation-key KEY \
  --format json \
  --root ROOT
```

The operation will calculate a complete readiness candidate without writing,
bind that candidate to a deterministic snapshot of all relevant inputs, and
commit `readiness.yml` plus a durable receipt through the existing atomic
workspace transaction mechanism.

Readiness remains proposal state managed by P2P Engine. WaveKit will later own
authentication, authorization, queueing, PostgreSQL projections and UI status,
but it will interact with project memory only through this CLI contract.

Project-level definition completeness remains a derived read model and is not
turned into a new mutation by this feature.

## Key Decisions

- D001: Extend `proposal readiness assess`, not `refresh` or `init`, as the
  WaveKit-facing recalculation command.
  Rationale: `assess` already performs the evidence-aware calculation that
  WaveKit users expect. `refresh` only recalculates stored criterion evidence,
  while `init` is a bootstrap concept.

- D002: Keep `p2p proposal show PROP --format json` as the canonical machine
  read for proposal readiness.
  Rationale: `p2p-proposal-detail/v1` already contains readiness, artifact
  state, questions and contributions. A second dedicated readiness-read
  contract would duplicate state and permit projection drift.

- D003: Split readiness calculation into pure planning and explicit commit.
  Rationale: current `assess()` calls a writing `initialize()` and later writes
  again. A pure plan is required to validate one final candidate and commit it
  atomically.

- D004: Reuse `MutationReceiptService` and `AtomicMutationWriter`.
  Rationale: proposal create, update and contribution add already establish the
  correct retry, conflict, journaling and recovery model. Readiness must not
  introduce a parallel transaction system.

- D005: Keep semantic request identity separate from evidence freshness.
  Rationale: operation-key replay identifies the caller's original request.
  Evidence may change after that request successfully commits. Such change
  makes readiness stale but must not rewrite history or turn the original
  receipt into a conflict.

- D006: Fingerprint the complete assessment source set.
  Rationale: score alone cannot tell whether readiness still represents the
  current proposal. A deterministic source fingerprint allows a read to expose
  `current` or `stale` without mutating state.

- D007: Include every read dependency as an atomic source precondition.
  Rationale: a transaction lock prevents P2P writers from committing
  concurrently, but source preconditions also detect external or pre-lock
  changes and prevent a mixed-snapshot assessment.

- D008: Preserve owner override metadata while recalculating computed fields.
  Rationale: an assessment updates advisory computation; it must not silently
  revoke an explicit owner governance override.

- D009: Treat missing fingerprint on an assessed snapshot as stale.
  Rationale: the runtime cannot prove which evidence produced an older result.
  Fail-safe stale classification is clearer than pretending it is current.

- D010: Keep JSON operation keys CLI-specific while sharing domain atomicity
  with MCP.
  Rationale: WaveKit needs durable process-level retry identity. Local MCP is a
  protocol-native agent surface and need not adopt the CLI envelope, but it
  should not retain the legacy multi-write behavior.

- D011: Do not create a project-readiness mutation.
  Rationale: vertical-based project definition and evidence progress are
  derived from current canonical state by existing read-only commands. A
  mutation would create unnecessary stale state and confuse it with the older
  operational `p2p assess refresh` artifact.

- D012: Target P2P Engine `0.4.11` while retaining `p2p-cli/v1`.
  Rationale: releases are immutable, but this is an additive command payload
  under the existing transport envelope rather than an envelope-breaking
  change.

## Current-State Gap

In `0.4.10`:

1. `p2p proposal readiness assess` has human text output only.
2. It accepts neither `--operation-key` nor an explicit audit actor.
3. `ReadinessService.assess()` writes through `initialize()` and then writes a
   second final snapshot.
4. Readiness receipts are not recognized by `MutationReceiptService`.
5. A proposal read returns stored readiness but cannot prove whether it was
   calculated from current evidence.
6. MCP assess calls the direct workspace method and inherits the same
   non-receipted write path.
7. The WaveKit-facing contract already says readiness reads belong inside
   `proposal_detail`; this feature must preserve that decision.

## Components

- `src/p2p_engine/services/readiness.py`
  - define a pure assessment plan/candidate;
  - centralize assessment source discovery and fingerprinting;
  - preserve owner overrides without intermediate writes;
  - derive read-only freshness.
- `src/p2p_engine/storage/filesystem.py`
  - expose atomic local assessment and operation-key assessment methods;
  - build receipt semantic inputs and transaction source preconditions;
  - normalize public mutation payloads.
- `src/p2p_engine/services/mutation_receipts.py`
  - allow and validate `proposal_readiness_assess` receipts;
  - validate the bounded result and canonical readiness postcondition;
  - expose a sanitized result through mutation status.
- `src/p2p_engine/services/workspace_transactions.py`
  - reuse the existing writer and recovery path; production changes should be
    unnecessary unless focused tests expose a missing generic capability.
- `src/p2p_engine/cli_commands/proposal_readiness.py`
  - add actor, operation key and JSON formatting options to `assess`;
  - preserve human-mode behavior.
- `src/p2p_engine/services/proposal_read_contract.py`
  - add freshness and fingerprint fields to proposal readiness detail.
- `src/p2p_engine/mcp/handlers/proposals.py`
  - route assessment through the shared atomic domain operation.
- `src/p2p_engine/mcp/catalog/proposals.py`
  - keep tool schema and description accurate.
- `src/p2p_engine/services/agent_templates.py`
  - explain assessment versus freshness and CLI versus MCP use.
- `docs/CLI-CONTRACT.md`, `docs/CLI-GUIDE.md`, `docs/MCP.md`,
  `docs/development/cli-primitive-inventory.md`, `README.md`, `CHANGELOG.md`
  - document the current contract and release.
- `tests/`
  - cover pure calculation, freshness, atomicity, receipts, CLI, MCP,
    recovery, public contracts and wheel behavior.

## Domain Model

### Assessment Plan

Introduce a typed internal result equivalent to:

```text
ProposalReadinessAssessmentPlan
  proposal_id
  readiness_payload
  candidate_path
  candidate_bytes
  source_preconditions[]
  source_fingerprint_sha256
  assessment_policy_version
  profile_id
  profile_version
```

The exact type may be a dataclass in `services/readiness.py` or a nearby
readiness module. It is an internal design object, not a public API.

Creating the plan must be side-effect free. In particular it must not:

- create the default profile;
- write a bootstrap readiness snapshot;
- update registries;
- refresh unrelated derived state;
- create transaction or receipt files.

### Source Inventory

The source snapshot uses stable logical identifiers rather than arbitrary
filesystem traversal:

```text
readiness_profile
proposal
suggested_scope
alternatives
findings
risks
assumptions
execution_plan
impact_map
proposal_questions
artifact_state
```

Each entry contributes:

```text
logical_id
relative_path
exists
physical_sha256 | null
```

The aggregate fingerprint is a semantic SHA-256 over:

```text
assessment_policy_version
proposal_id
profile_id
profile_version
sorted source entries
```

Raw source text is never stored in a receipt. Relative paths may remain
internal evidence metadata, but public JSON only requires aggregate hashes.

### Readiness Persistence

The readiness mapping gains:

```text
assessment_policy_version: 1
source_fingerprint_sha256: <sha256>
```

Existing computed and override fields remain unchanged. The source fingerprint
does not include `readiness.yml` itself, avoiding recursion. The transaction
still checks the previous readiness file as a source precondition because the
candidate may preserve owner override fields.

No workspace-schema bump is required for these additive readiness fields.
An assessed snapshot without them is readable but classified as stale until
reassessed by the current runtime.

## Atomic Mutation Flow

The keyed workspace operation follows this sequence:

```text
validate operation key and proposal id
        |
build semantic request fingerprint
        |
look for exact receipt replay
        |
validate runtime/schema/recovery state
        |
build pure assessment plan from one source snapshot
        |
build readiness result summary and receipt candidate
        |
AtomicMutationWriter acquires project lock
        |
recheck every source precondition
        |
validate final readiness candidate
        |
commit readiness.yml and receipt
        |
return applied mutation payload
```

If the writer does not return `applied`, the caller checks the receipt once
more. A concurrent exact retry may have completed the operation. Otherwise the
operation returns a stable busy, failed or recovery-required error.

### Why The Source Fingerprint Is Not The Request Fingerprint

The request fingerprint binds:

```text
operation = proposal_readiness_assess
proposal_id
actor
assessment policy selection
```

The source fingerprint binds the evidence used for the result.

This separation gives correct retry behavior:

- response is lost after commit;
- proposal evidence changes later;
- retry with the same operation key still returns the original applied result;
- `proposal show` reports that result as stale;
- a new operation key requests a new assessment of current evidence.

If current evidence were part of request identity, a legitimate response-loss
retry after later evidence changes would incorrectly become an idempotency
conflict.

## Receipt Contract

The internal receipt result is bounded to:

```text
operation: proposal_readiness_assess
operation_id: proposal.readiness.assess
proposal_id: PROP-001
readiness:
  status
  profile_id
  profile_version
  computed_score
  computed_label
  confidence
  failed_gates
  missing
  suggested_next
  owner_question_state
  assessment_policy_version
  source_fingerprint_sha256
changed_paths:
  - .p2p/proposals/PROP-001-.../readiness.yml
```

Receipt validation must enforce:

- exact supported fields;
- proposal id format;
- readiness path belongs to the same proposal;
- bounded lists and owner-question payload;
- score range `0..100` or null only when contractually allowed;
- known labels, confidence and status values;
- lowercase SHA-256 digests;
- sorted unique changed paths;
- no `.p2p/.internal` path in public postconditions.

The receipt file itself remains internal and is committed with the readiness
candidate, following the existing proposal mutation pattern.

## CLI Contract

### Success

```json
{
  "contract_version": "p2p-cli/v1",
  "ok": true,
  "operation": "proposal.readiness.assess",
  "data": {
    "proposal_readiness_assess": {
      "proposal_id": "PROP-001",
      "readiness": {
        "status": "assessed",
        "computed_score": 85,
        "computed_label": "strong",
        "confidence": "high",
        "freshness": "current",
        "assessment_policy_version": 1,
        "source_fingerprint_sha256": "<sha256>"
      }
    },
    "mutation": {
      "status": "applied",
      "operation_id": "proposal.readiness.assess",
      "actor": "wavekit-user",
      "changed_paths": [".p2p/proposals/PROP-001-example/readiness.yml"],
      "recovery_required": false,
      "message": "Proposal readiness assessment completed."
    }
  },
  "warnings": [],
  "error": null
}
```

The actual readiness object also includes the bounded fields required by R034.
The example is abbreviated, not permission to omit them.

### Replay

Exact replay returns the same domain result with:

```text
mutation.status = already_applied
```

It does not rerun the calculation, update `assessed_at`, or rewrite
`readiness.yml`.

### Failure Classes

Expected stable classes include:

- invalid request: missing or malformed operation key, actor or proposal id;
- not found: proposal or required readiness profile missing;
- invalid state: malformed questions, artifact state, profile or readiness;
- conflict: divergent key reuse or source precondition change;
- busy: another workspace transaction owns the lock;
- recovery required: interrupted transaction cannot be rolled back safely;
- receipt corrupt/drift: existing receipt cannot be trusted;
- runtime/schema: current runtime contract cannot write this workspace.

Error details must be sanitized for a server consumer. Raw operation keys and
full artifact contents are forbidden.

## Freshness Read Contract

`proposal_detail.readiness` remains the authoritative machine read and gains:

```text
freshness: not_assessed | current | stale
assessment_policy_version: integer | null
source_fingerprint_sha256: sha256 | null
current_source_fingerprint_sha256: sha256
```

Rules:

- no readiness file: `not_assessed`;
- assessed file with matching current fingerprint and policy: `current`;
- assessed file with missing or non-matching fingerprint/policy: `stale`;
- malformed canonical source: typed read failure, not a guessed freshness;
- reading freshness never writes.

The current fingerprint may be exposed because it is derived metadata, not
source content or a credential. It enables precise diagnostics and contract
tests.

## Human CLI And MCP

Human text mode remains:

```text
p2p proposal readiness assess PROP-001 --root ROOT
```

It uses the same pure plan and atomic readiness candidate but does not require a
caller operation key or create a WaveKit receipt.

`p2p_proposal_readiness_assess` remains protocol-native. It uses the same
atomic local assessment method and returns readiness plus existing governance
metadata. It does not emit a CLI envelope and is not called by WaveKit's
deterministic worker.

Adding optional MCP actor or retry metadata is permitted only if required to
keep its existing public schema truthful; it is not required to duplicate the
WaveKit operation-key contract.

## Project-Level Readiness

No new project-level write is designed.

WaveKit and other consumers should use:

```text
p2p project snapshot --format json
p2p project progress --format json
p2p project readiness review --format json
p2p project readiness gaps --format json
```

These calculate current vertical-based definition completeness, declared
evidence coverage and gaps. Their current read-only behavior is the desired
contract.

`p2p assess refresh` writes a separate general operational assessment. It is
not a substitute for the project progress axes and is not expanded here.

## Public Surface And MCP Parity

- CLI: add JSON, actor and operation-key behavior to readiness `assess` only.
- MCP: preserve tool name and protocol-native payload; converge implementation
  on the atomic readiness path.
- Proposal detail: add freshness metadata without a dedicated JSON readiness
  show command.
- Mutation status: add one receipt result operation.
- Human CLI: preserve existing invocation and output semantics.
- Generated guidance: show machine-worker and agent workflows separately.

## Error Handling

The service layer raises domain-specific stable errors or existing structured
`ValueError` codes. CLI JSON mode maps them through the shared contract failure
surface. Human CLI preserves concise diagnostic output.

Candidate planning must fail before any write for:

- missing proposal;
- missing or invalid profile;
- invalid questions;
- invalid artifact state;
- invalid existing readiness/override data.

Atomic commit failure must return only after complete rollback or explicit
recovery-required classification.

## Migration And Compatibility

- Baseline package: `0.4.10`.
- Target package: `0.4.11`.
- CLI envelope remains `p2p-cli/v1`.
- Workspace schema remains current schema `3` unless implementation proves an
  unavoidable persisted-layout incompatibility.
- New readiness fingerprint fields are additive.
- Existing assessed snapshots without a fingerprint are stale and become
  current after a successful reassessment.
- No historical workspace conversion command is added.
- Old release notes and immutable download links remain historical.
- Current version references are bumped only in the release phase.

## Risks And Tradeoffs

- Missing a readiness input from the explicit source inventory could label a
  result current after relevant evidence changed. Tests must mutate every
  declared source independently.
- Fingerprinting on every proposal detail read adds filesystem reads. The set is
  bounded to one proposal and its profile, avoiding repository-wide scans.
- A receipt remains applied when later evidence changes. This is intentional;
  freshness reports the current usefulness of its result.
- Preserving text and MCP calls without operation keys means those local calls
  are atomic but not retry-addressable after a lost process response. WaveKit
  uses the keyed JSON path for that stronger guarantee.
- Automatically assessing after every write might improve convenience but
  would create hidden mutations and operation chains. It is deferred to
  WaveKit policy after the explicit command is reliable.
- The existing readiness implementation mixes calculation and persistence.
  Refactoring must remain limited to the boundary needed for one final atomic
  candidate.

## Out Of Scope

- WaveKit implementation and deployment.
- OAuth, MCP HTTP and AI mediator behavior.
- Automatic readiness queues or scheduled reassessment.
- New readiness scoring criteria.
- Owner decision workflow changes.
- Project-level readiness persistence.
- Universal operation-key support for all readiness/question/artifact commands.

