# Implementation Note - Expose Receipt-Backed Proposal Readiness Assessment

## Outcome

P2P Engine `0.4.11` exposes:

```text
p2p proposal readiness assess PROP \
  --actor ACTOR \
  --operation-key KEY \
  --format json \
  --root ROOT
```

The command calculates one final readiness candidate from an explicit source
snapshot and commits that candidate plus its mutation receipt atomically. The
existing human command and MCP tool share the atomic domain path but remain
free of the WaveKit-specific CLI receipt envelope.

## Contract Evidence

- Operation: `proposal.readiness.assess` under `p2p-cli/v1`.
- Data objects: `proposal_readiness_assess` and `mutation`.
- Receipt operation: `proposal_readiness_assess`.
- Retry: exact request returns `already_applied`; divergent proposal or actor
  returns `P2P_IDEMPOTENCY_CONFLICT`.
- Recovery: uncertain writes are visible through `p2p mutation status` and the
  existing workspace transaction recovery commands.
- Freshness: proposal detail reports `not_assessed`, `current`, or `stale` plus
  stored/current source fingerprints without writing.
- Governance: recalculation preserves owner override fields and never accepts,
  rejects, defers, overrides, or otherwise decides a proposal.

The observed complete success payload is fixed in
`tests/fixtures/cli_contract/proposal-readiness-assess-v1.json`; only the
source fingerprint is normalized because canonical source artifacts contain
runtime timestamps.

## Source And Test Mapping

See `implementation-inventory.md` for requirement-level ownership. The focused
contract suite is `tests/test_proposal_readiness_write_contract.py`. It covers
success, replay, divergent reuse, invalid requests/sources, busy workspaces,
receipt corruption and drift, every declared source, unrelated files, owner
override preservation, rollback, recovery-required interruption, source drift,
MCP parity and the project-readiness read-only boundary.

## Acceptance Criteria

- AC001-AC004: covered by JSON, receipt, replay/status and conflict tests.
- AC005-AC006: covered by injected rollback/recovery and source-drift tests.
- AC007-AC008: covered by owner override and freshness source-table tests.
- AC009: covered by human CLI regression and MCP semantic parity.
- AC010-AC011: covered by project-readiness read-only and generated-guidance
  tests plus maintained documentation.
- AC012: completed by focused, public, installed-wheel and full-suite evidence
  recorded below before handoff.

## Verification Record

The completed implementation was verified with:

- focused readiness, read-contract, receipt, transaction, MCP, agent and
  project-readiness tests: `162 passed`;
- installed/smoke marker suite: `17 passed`;
- public CLI/MCP contract suite: `281 passed`;
- final source/syntax and whitespace checks: `compileall` and
  `git diff --check` passed;
- final release build: `p2p_engine-0.4.11-py3-none-any.whl` and
  `p2p_engine-0.4.11.tar.gz` built successfully;
- release artifact verification: version `0.4.11`, `265` wheel files and
  `582` sdist files;
- installed-wheel public readiness smoke: `1 passed`, with the import resolved
  from the unpacked `0.4.11` wheel rather than `src/`;
- full repository suite: `1511 passed`.

No WaveKit source was changed by this feature.

## Residual Risks

- A receipt correctly becomes `postcondition_drift` if a later readiness
  recalculation replaces its recorded readiness postcondition. Evidence-only
  changes do not invalidate the historical receipt; they only make readiness
  stale.
- Freshness is a point-in-time read. A following mutation can immediately make
  a just-read `current` result stale, so server clients must still use their
  normal project revision and operation ordering.
- P2P Engine does not authenticate WaveKit users. WaveKit remains responsible
  for authentication, authorization, serialized per-project execution and
  actor selection before invoking this CLI operation.
