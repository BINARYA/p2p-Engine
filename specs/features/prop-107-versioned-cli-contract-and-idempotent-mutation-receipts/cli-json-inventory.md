# CLI JSON Inventory - PROP-107

## Baseline

The 0.4.6 command tree contains 96 commands with a `--format` option supporting
JSON. Before PROP-107, 80 emitted a command-specific raw object and 16 already
used an initial `p2p-cli/v1` envelope. Handler/domain failures normally exited
with 1, while Typer parser failures exited with 2 and rendered human output.

The pre-existing envelope group was: `version`; `vertical list`, `vertical
inspect`, all three `vertical registry` commands; and `project vertical`
schema, scaffold, inspect, package, install preview/apply, adopt preview/apply
and migrate preview/apply. Every other command below returned a raw domain
payload.

Known first-party consumers are the public CLI tests and generated agent
workflows. WaveKit consumes version discovery and the project-vertical
lifecycle. No other external consumer is declared during the pre-release
0.4.6 coordinated break.

## Reviewed Command Set

```text
choice governance-preflight
conflict preview-update
conflict show
conflict update
context
decision apply
decision history
decision impact
decision ledger-repair-apply
decision ledger-repair-preview
decision legacy-resolution-apply
decision legacy-resolution-preview
decision preview
decision projection-repair-apply
decision projection-repair-preview
decision record
decision status
governance status
governance validate
impact apply
impact preview
mutation status
precedent search
project context
project definition apply
project definition preview
project definition show
project definition update
project freshness
project memory show
project memory status
project metadata apply
project metadata preview
project metadata show
project progress
project publish import
project publish list
project publish prepare
project publish render
project publish review
project publish status
project publish validate
project readiness apply
project readiness gap
project readiness gaps
project readiness preview
project readiness questions answer
project readiness questions defer
project readiness questions mute
project readiness questions next
project readiness questions reconcile-apply
project readiness questions reconcile-preview
project readiness questions reopen
project readiness questions status
project readiness review
project rubrics show
project section
project sections
project vertical adopt apply
project vertical adopt preview
project vertical inspect
project vertical install apply
project vertical install preview
project vertical list
project vertical lock repair
project vertical lock show
project vertical migrate apply
project vertical migrate preview
project vertical package
project vertical scaffold
project vertical schema
project vertical select
project vertical show
project vertical validate
proposal accept
proposal defer
proposal reject
proposal vertical-coverage import
proposal vertical-coverage preview
proposal vertical-coverage show
proposal vertical-coverage suggest
runtime contract adopt
runtime contract apply
runtime contract preview
runtime status
validate
version
vertical inspect
vertical list
vertical registry add
vertical registry list
vertical registry remove
vote status
workspace schema status
workspace transaction resume
workspace transaction rollback
workspace transaction status
```

The eleven commands whose output defaults to JSON are `vertical inspect`,
`mutation status` and
`project vertical` schema, inspect, package, install preview/apply, adopt
preview/apply and migrate preview/apply. The other 86 default to text.

## Normalized Result

The root Typer boundary now assigns the dot-separated command path as the
operation ID and normalizes both raw and pre-enveloped handler output. A static
test snapshot covers all 97 operations. Any added or removed `--format` command
changes the snapshot and requires explicit contract review.

JSON parser failures use `P2P_CLI_INVALID_REQUEST` and exit 2. Stable domain
codes are classified into conflict, authorization and unavailable exit classes.
Text output and MCP protocol payloads are unchanged.

## Implementation Impact

- `VersionedJSONTyperGroup` is the only transport boundary. Command handlers
  continue to own typed domain payload construction.
- Existing raw JSON renderers remain internal implementation detail. Their
  stdout is captured only in JSON mode, decoded, and emitted once in the common
  envelope. Invalid or mixed handler output becomes
  `P2P_CLI_INVALID_JSON_OUTPUT` instead of leaking prose.
- The boundary recognizes explicit `--format json`, `--format=json`, and the
  eleven commands whose declared default is JSON.
- Error normalization does not parse human message text when a stable domain
  code already exists. Unclassified legacy failures use
  `P2P_CLI_OPERATION_FAILED` until their domain service gains a narrower code.
- Successful domain data moved down exactly one level to `data`. Existing
  failed status payloads are retained as typed `error.details.result` when the
  legacy handler exits non-zero after rendering structured diagnostics.
- Rich/text output, help and MCP JSON-RPC responses bypass this boundary.
- Mutation idempotency, durable receipts and `p2p mutation status` are covered
  by T008-T014. The post-baseline command inventory contains 97 operations.

## Verification Evidence

- all 97 reviewed command paths produce a `p2p-cli/v1` parser-error envelope;
- receipt, transaction, vertical and CLI contract group: 92 passed;
- complete source suite after T008-T014: 1423 passed in 256.40 seconds;
- wheel and sdist rebuilt from the T008-T014 source successfully in `/tmp`;
- release verifier: 248 wheel files and 502 sdist files;
- isolated installed-wheel smoke loaded P2P Engine from the target directory,
  returned the version envelope and resolved `mutation.status` as `not_found`.
