# WaveKit CLI Contract Inventory - 0.4.9 Gap Audit

## Purpose

This inventory freezes the WaveKit-facing P2P CLI contract before implementation
of `PROP-002`. It records what WaveKit needs, what P2P Engine `0.4.9` currently
exposes, and what must change for the target `0.4.10` release.

WaveKit must use only allowlisted CLI JSON commands to access P2P project
memory. It must not parse `.p2p`, parse human CLI output, import P2P Python
internals, or call local MCP stdio as the deterministic server-worker transport.

## Audit Inputs

- CLI help from the local `0.4.9` source environment.
- Automatic CLI JSON inventory from `json_command_inventory(get_command(app))`.
- Source modules:
  - `src/p2p_engine/cli.py`
  - `src/p2p_engine/cli_contract.py`
  - `src/p2p_engine/cli_commands/project_ops.py`
  - `src/p2p_engine/cli_commands/proposal_core.py`
  - `src/p2p_engine/cli_commands/proposal_contributions.py`
  - `src/p2p_engine/cli_commands/mutations.py`
  - `src/p2p_engine/core/contribution.py`
  - `src/p2p_engine/services/project_initialization.py`
- Existing contract docs:
  - `docs/CLI-CONTRACT.md`
  - `docs/CLI-GUIDE.md`
- Existing contract tests:
  - `tests/test_cli_contract.py`
  - `tests/test_mutation_receipts.py`
  - `tests/test_version_consistency.py`

## Current Automatic JSON Inventory Summary

`0.4.9` registers 106 command paths with a `--format` option. This is not the
same as WaveKit readiness. Several commands accept `--format json` explicitly
and are wrapped by `p2p-cli/v1`, but WaveKit-critical commands are absent.

Relevant already-registered JSON-capable surfaces:

| Surface | Current default | Current status for WaveKit |
| --- | --- | --- |
| `version` | text | usable startup probe with explicit `--format json` |
| `runtime.status` | text | usable runtime probe with explicit `--format json` |
| `workspace.schema.status` | text | usable schema probe with explicit `--format json` |
| `workspace.transaction.status` | text | usable recovery probe with explicit `--format json` |
| `project.progress` | text | useful snapshot input, not sufficient alone |
| `project.freshness` | text | useful snapshot input, not sufficient alone |
| `project.context` | text | useful snapshot input, not sufficient alone |
| `project.sections` | text | useful structure input, not sufficient alone |
| `project.publish.status` | text | useful output-status input, not sufficient alone |
| `project.vertical.* preview/apply` | json for lifecycle operations | already receipt-backed for vertical lifecycle |
| `proposal.accept/reject/defer` | text | JSON explicit exists, but owner decision workflow is not WaveKit MVP write path |
| `proposal.vertical-coverage.*` | text | JSON explicit exists on those commands, but not enough for proposal UI |
| `mutation.status` | json | operationally enveloped, but only exposes `--idempotency-key` |

Critical missing WaveKit-facing surfaces:

| Required surface | 0.4.9 state |
| --- | --- |
| `p2p init --format json --operation-key` | missing |
| `p2p project snapshot --format json` | missing |
| `p2p proposal list --format json` | missing |
| `p2p proposal show --format json` | missing |
| `p2p proposal create --format json --operation-key` | missing |
| `p2p proposal update --format json --operation-key` | missing |
| `p2p proposal contribution add --format json --operation-key` | missing |
| `p2p proposal contribution list --format json --type` | missing |
| `p2p proposal contribution review ... --operation-key` | missing; product decision still required in implementation |
| `p2p mutation status --operation-key` | missing alias; `--idempotency-key` exists |

Implementation progress in the current `0.4.10` branch:

- `p2p init --format json --operation-key` is implemented with durable
  receipt/replay/conflict behavior.
- `p2p project snapshot --format json` is implemented as a bounded read model.
- `p2p proposal list --format json` is implemented with status and
  decision-state filters.
- `p2p proposal show PROP --format json` is implemented as a bounded full
  proposal detail read model including readiness, artifact state, questions and
  contribution grouping.
- `p2p proposal create --format json --operation-key` is implemented with
  durable receipt/replay/conflict behavior.
- `p2p proposal update --format json --operation-key` is implemented with
  durable receipt/replay/conflict behavior.
- `p2p proposal contribution list --format json` is implemented with type
  filtering, bounded results and counts by type.
- `p2p proposal contribution add --format json --operation-key` is implemented
  with durable receipt/replay/conflict behavior.
- Contribution review/promote/reject remains explicitly unsupported in 0.4.10;
  JSON contribution payloads expose `review_capability.supported = false` so
  WaveKit does not store shadow project-memory review state in PostgreSQL.
- Proposal readiness and proposal question reads are covered for WaveKit by the
  bounded `p2p proposal show PROP --format json` detail model, with stable
  fixture coverage for uninitialized states.
- `p2p mutation status --operation-key KEY` is implemented as a WaveKit-facing
  alias of `--idempotency-key` and returns a redacted operation-key
  classification.

## Required WaveKit P0 Contract

### Runtime Startup And Preflight

| WaveKit need | Current 0.4.9 command | Target 0.4.10 command | Class | Gap |
| --- | --- | --- | --- | --- |
| Check engine and contract version | `p2p version --format json` | same | read-only | no functional gap |
| Check runtime compatibility | `p2p runtime status --format json` | same | read-only | verify fixture for WaveKit startup |
| Check workspace schema | `p2p workspace schema status --format json` | same | read-only | verify fixture for WaveKit startup |
| Check interrupted transactions | `p2p workspace transaction status --format json` | same | read-only | verify fixture for WaveKit startup |
| Inspect write receipt | `p2p mutation status --idempotency-key KEY` | `p2p mutation status --operation-key KEY` | status/read-recovery | implemented in T023-T024 |

Notes:

- `mutation.status` defaults `--format` to `json`. The command works for
  normal status lookup and the root JSON boundary wraps its payload in
  `p2p-cli/v1`.
- Default-json command help is explicitly excluded from JSON wrapping, so
  `p2p mutation status --help` remains normal Typer/Click help.

### Project Creation

| WaveKit need | Current 0.4.9 command | Target 0.4.10 command | Class | Gap |
| --- | --- | --- | --- | --- |
| Initialize a project workspace | `p2p init NAME ...` | `p2p init NAME ... --format json --operation-key wavekit:<uuid>` | write-safe | add JSON, operation key, durable receipt, replay and conflict behavior |
| Initialize with selected vertical | `p2p init --vertical ...` | same plus JSON/operation-key | write-safe | bind vertical selection to init receipt fingerprint |
| Initialize from local vertical pack | `p2p init --vertical-pack ... --expected-checksum ...` | same plus JSON/operation-key | write-safe | include closure/checksum in fingerprint |
| Initialize with remote pull | `p2p init --vertical ... --pull --registry ...` | same plus JSON/operation-key | write-safe plus transport | include registry/pull result in result data and errors |

Required `data` shape:

```text
init_result:
  status: applied | already_applied
  created_paths[]
  project
  runtime
  workspace_schema
  selected_vertical
  agent_selection
  repository
  remote
  mcp_hint
  warnings[]
  receipt
```

Open design detail:

- Init is special because `.p2p` may not exist yet. The implementation must
  either create the receipt inside the bootstrap candidate or define an
  equivalent atomic bootstrap boundary. It must not leave a successful `.p2p`
  init without a replayable result for WaveKit.

### Project Overview Snapshot

| WaveKit need | Current 0.4.9 command | Target 0.4.10 command | Class | Gap |
| --- | --- | --- | --- | --- |
| Render Angular project overview with one read | none | `p2p project snapshot --format json` | read-only | new command and read model |
| Show project readiness | multiple project readiness/progress commands | included summary in snapshot | read-only | compose bounded summary |
| Show active vertical/structure | `project context`, `project sections`, vertical lock commands | included summary in snapshot | read-only | compose and normalize |
| Show proposals/decisions counts | `proposal list` text, decision status per proposal | included summaries in snapshot | read-only | add proposal/decision aggregation |
| Show output/publication status | `project publish status --format json` | included summary in snapshot | read-only | compose existing data |
| Show stale derived-state warning | `project freshness --format json` | included summary in snapshot | read-only | compose existing data |

Target `data` shape:

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

Bounded behavior:

- Proposal, decision and output arrays must be summarized and capped.
- Full proposal bodies and full contribution histories stay in dedicated
  detail commands.
- Truncation must be explicit in `limits` or per-collection metadata.

### Proposal Reads

| WaveKit need | Current 0.4.9 command | Target 0.4.10 command | Class | Gap |
| --- | --- | --- | --- | --- |
| List proposals | `p2p proposal list` text only | `p2p proposal list --format json` | read-only | implemented in T011-T014 |
| Filter proposals by status | `--status` text only | same with JSON | read-only | implemented with filter metadata |
| Filter by decision state | no clear list filter | `--decision-state` | read-only | implemented in T011-T014 |
| Proposal detail | `p2p proposal show PROP` text only | `p2p proposal show PROP --format json` | read-only | implemented in T011-T014 |
| Full owner-facing view | `p2p proposal show PROP --full` text only | base JSON detail includes bounded full data | read-only | implemented without requiring `--full` in JSON mode |
| Artifact state | `p2p proposal artifact status PROP` text only | included in proposal show JSON or add `--format json` | read-only | included in proposal detail; dedicated command deferred |
| Proposal readiness | `proposal readiness show/assess` text only | included in proposal show JSON | read-only / assess write-derived? | implemented through proposal detail fixture |
| Proposal questions | `proposal questions status/list/next` text only | included in proposal show JSON | read-only | implemented through proposal detail fixture |

Target `proposal.list` data:

```text
proposals:
  filters
  items[]
  counts
  limits
```

Target `proposal.show` data:

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

### Proposal Writes

| WaveKit need | Current 0.4.9 command | Target 0.4.10 command | Class | Gap |
| --- | --- | --- | --- | --- |
| Create proposal from Angular/MCP HTTP | `p2p proposal create ...` text only | `p2p proposal create ... --format json --operation-key wavekit:<uuid>` | write-safe | implemented in T015-T017 |
| Update proposal structured sections | `p2p proposal update PROP ...` text only | `p2p proposal update PROP ... --format json --operation-key wavekit:<uuid>` | write-safe | implemented in T015-T017 |
| Safe retry after worker response loss | none | exact replay returns `already_applied` | write-safe | implemented in T015-T017 |
| Conflict on divergent retry | none | stable idempotency conflict | write-safe | implemented in T015-T017 |

Target create result:

```text
proposal_create:
  proposal
  created_paths
  next_steps
mutation:
  status: applied | already_applied
  changed_paths
```

Target update result:

```text
proposal_update:
  proposal_id
  path
  updated_sections
mutation:
  status: applied | already_applied
  changed_paths
```

### Proposal Contributions

| WaveKit need | Current 0.4.9 command | Target 0.4.10 command | Class | Gap |
| --- | --- | --- | --- | --- |
| Add suggestion/objection/finding/open question/alternative | `p2p proposal contribution add PROP TEXT --type ...` text only | same plus `--format json --operation-key wavekit:<uuid>` | write-safe | implemented in T018-T021 |
| List contributions | `p2p proposal contribution list PROP` text only | `p2p proposal contribution list PROP --format json` | read-only | implemented in T018-T021 |
| Filter by type for UI cards | no `--type` filter | `--type suggestion` etc. | read-only | implemented with counts and pagination |
| Promote/reject/relevance UI | no review primitive; only `relevance_hint` field at creation | explicit unsupported note in contribution JSON | deferred | review primitive intentionally not added in 0.4.10 |

Current supported contribution types already include all WaveKit UI P0 types:

- `suggestion`
- `objection`
- `finding`
- `open_question`
- `alternative`

Other existing types must remain valid unless a separate proposal narrows the
model.

Target contribution list data:

```text
contributions:
  proposal_id
  filters
  counts_by_type
  items[]
  limits
```

Target contribution add data:

```text
contribution_add:
  status: applied | already_applied
  proposal_id
  contribution
  receipt
```

Contribution review decision:

- Preferred if feasible in 0.4.10: add governed review state with
  `relevant` and `rejected`, append-only or auditable, receipt-backed with
  `--operation-key`.
- Minimum acceptable fallback: explicitly document that promote/reject is not
  supported by P2P in 0.4.10, and WaveKit must not create a PostgreSQL-only
  shadow status that direct P2P/MCP agents cannot see.

### Vertical And Registry Surfaces

WaveKit vertical selection and registry integration already depend on the
vertical work from earlier releases. For `PROP-002`, these surfaces are not the
primary gap, but the contract must verify they remain usable:

| WaveKit need | Current 0.4.9 command | Status |
| --- | --- | --- |
| List local/remote verticals | `p2p vertical list/search/pull`, `p2p project vertical list/show` | partially JSON-capable; verify fixtures |
| Install/adopt/migrate verticals | `p2p project vertical install/adopt/migrate preview/apply --format json` | already receipt-backed with `--idempotency-key` |
| Typed transition impact | `data.impact.contract_version = p2p-vertical-transition-impact/v1` | already implemented in 0.4.9 |

No new vertical behavior is required here unless snapshot or init needs to
reuse an existing vertical read result.

## Gap List For 0.4.10

### Remaining Gaps After T033

1. Contribution promote/reject is intentionally unsupported in 0.4.10 and is
   exposed as `review_capability.supported = false`.

### Explicit Non-Gaps

1. The `p2p-cli/v1` transport envelope exists.
2. Explicit JSON parser errors are normalized for registered JSON commands.
3. `p2p version --format json` works outside a project root.
4. Runtime/schema/transaction probes already have JSON-capable commands.
5. Vertical install/adopt/migrate apply already have durable receipt behavior,
   though they use `--idempotency-key`.
6. The contribution type enum already contains the WaveKit UI P0 types.
7. Proposal readiness and question data needed by WaveKit are available through
   `p2p proposal show PROP --format json`.
8. `p2p mutation status` accepts `--operation-key` and keeps help output
   outside the JSON envelope.
9. MCP proposal/contribution reads are protocol-native and semantically aligned
   with CLI read models; generated agent guidance describes the WaveKit CLI
   worker retry boundary.
10. Current package, docs, examples and version-consistency tests reference
    `0.4.10`.
11. Focused tests, public CLI/MCP tests, installed-wheel smoke and full suite
    are recorded in `implementation.md`.

## Implementation Guidance

Recommended order:

1. Fix command inventory and help/default-json behavior so new JSON surfaces do
   not reproduce the `mutation status --help` issue.
2. Add shared operation-key validation and aliasing for `wavekit:<uuid>`.
3. Implement snapshot read model before writes; it will clarify serializers.
4. Implement init receipt boundary.
5. Implement proposal read JSON.
6. Implement proposal write receipts.
7. Implement contribution JSON/filtering and decide review semantics.
8. Update docs, agent guidance, MCP descriptions and version references.

## Test Anchors

Expected focused test areas:

- `tests/test_cli_contract.py`: inventory, parser/help behavior, envelope
  shape and explicit JSON parser errors.
- `tests/test_mutation_receipts.py`: operation-key validation, status alias,
  replay/conflict/drift classification.
- `tests/test_project_initialization_service.py`: init result serialization,
  receipt fingerprinting and safe replay.
- `tests/test_cli.py` or new focused CLI tests: `p2p init`, `project snapshot`,
  `proposal list/show/create/update`, `proposal contribution add/list/review`.
- `tests/test_proposal_review_view_service.py`: proposal detail read model.
- `tests/test_mcp_registry.py` and MCP handler/catalog tests: description
  parity, not `p2p-cli/v1` wrapping.
- `tests/test_version_consistency.py`: release bump and docs consistency.
