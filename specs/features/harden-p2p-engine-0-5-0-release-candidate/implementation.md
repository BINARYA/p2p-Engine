# Implementation - Harden P2P Engine 0.5.0 Release Candidate

## Verdict

`READY_FOR_OWNER_REVIEW` as of 2026-08-27.

The 10A implementation hardening, stable release metadata and diagnostic
artifact gates are locally green. This verdict does not mean release `GO`:
`0.5.0` correctly remains `Unreleased`. The actual release date, final notes and
official exact-SHA candidate gate belong to the subsequent release step.

## Scope And Authority Boundary

- Work was limited to the `p2p-engine/` implementation repository.
- No change was made in `wavekit/`, `projects/p2p-engine-project/` or
  `projects/wavekit-project/`.
- P2P Engine runtime now treats source control, branches, commits, review, CI,
  tags and publication as external repository tooling.
- Caller-supplied repository, issue, pull-request, commit and release values are
  inert traceability metadata and never implementation evidence.
- `converge-project-structure-surfaces` is the predecessor. The optional
  coverage feature and `merge-and-restore-project-structure` are outside this
  gate.
- No branch, commit, push, tag, GitHub Release or asset upload was created.
  Read-only `git status`, `git diff`, `git rev-parse` and sibling-repository
  status inspection were used only as source evidence.
- The canonical P2P Engine design root remains
  `../projects/p2p-engine-project`; no local implementation `.p2p/` was created.

The inspected source baseline HEAD was
`14a9c7dfffdc802b642b2a855bbebd6d23999bf7`. This is only the pre-existing
checkout identity, not an approved candidate SHA or release authorization.

## Owner Decisions Recorded On 2026-08-27

- SPDX license expression: `GPL-3.0-or-later` for P2P Engine itself.
- Public author and maintainer identity: `mrjungle`; no email is published.
- Canonical repository: `https://github.com/BINARYA/p2p-Engine`, with matching
  Homepage, Issues and Changelog URLs.
- Version policy: keep `0.5.0 - Unreleased` until the later release step; record
  the actual date only when the release is finalized.
- Provenance policy: GitHub Artifact Attestations for the exact retained wheel,
  sdist and `SHA256SUMS`, generated only by the tag workflow. Normal pushes and
  pull requests require no attestation work or elevated permissions, and the
  owner manages no signing key.

## Audit Finding Closure

| Requirement/task family | Implementation evidence | Test/gate evidence |
| --- | --- | --- |
| R001-R008 / T006-T010 | shared raw JSON serializer used by runtime, validation and all direct CLI JSON renderers | `tests/test_cli_contract.py`; source renderer guard; public/full suites |
| R009-R017 / T011-T017 | path-free bundled/outside-root locks, P2P259 validation, regenerated examples, strict duplicate-key package parsing | `tests/test_project_verticals.py`, `tests/test_portable_verticals.py`, installed smoke |
| R040-R047 / T018-T022 | deterministic fixture generator, schema-3 manifest, 0.5.0 handoff and PROP-107 supersession note | generator `--check`, transition/convergence tests, packaged fixture read |
| R048-R055 / T023-T028 | implementation-specific root instructions, corrected install/security/agent/CLI/MCP/roadmap docs, historical inventory labels | `scripts/check-doc-links.py`, docs/public-surface tests |
| R056-R060 / T029-T032 | PEP 639 metadata, `mrjungle` identity and canonical URLs are stable; release-only validation separately requires the actual date and final notes | `tests/test_release_automation.py`, `tests/test_release_artifacts.py`; stable metadata passes and release mode reports exactly three deferred finalization findings |
| R061-R066 / T033-T035 | five zero-inbound modules removed after import/resource inventory | source/import/package member guards |
| R064-R066, R080-R090 / T036-T043 | Git-owned CLI groups/options, 25 MCP tools, handlers, consent operations, adapters/services and generated guidance removed; retained Work is logical only | `scripts/check-source-boundary.py`, `tests/test_source_control_boundary.py`, CLI/MCP/public inventory tests |
| R018-R027 / T044-T049 | exact-wheel isolated venv, external CWD, identity/dependency checks, failing Git and network sentinels, real CLI, schema-3/export workflows and bounded MCP stdio smoke | final diagnostic 0.5.0 wheel: 24 smoke tests passed; six injected failure modes exited non-zero with clean temporary roots |
| R028-R039 / T055-T060 | pre-tag CI, exact-SHA reusable candidate, SHA-pinned actions, least-privilege tag-only GitHub attestations, retained exact artifacts and create-only publisher | workflow static tests and fake-`gh` existing-release regression; tag workflow does not rebuild |
| R032-R038 / T050-T054 | all-text archive scan, narrow fail-unused allowlists, exact members/entry points, double-build comparison and stable checksums | synthetic unsafe-member, mismatch, extra-asset and allowlist tests; two diagnostic builds compared byte-for-byte |
| R069-R074 / T061-T066 | scoped Ruff, staged mypy, exact runtime dependency audit, `twine check`, path/secret/link scans | static gate green; runtime audit reported no known vulnerabilities; wheel/sdist `twine check` passed |
| R076-R090 / T067-T075 | exact MCP negative catalog, release tuple, current-only surface and no-Git initialization revalidated | public suite 253 passed; full suite 1562 passed |

PROP-107 T015-T018 remain unchecked in their original task file because final
release notes, official artifacts and commit-bound CI do not yet exist. Their
evidence and supersession are recorded in
`../prop-107-versioned-cli-contract-and-idempotent-mutation-receipts/implementation.md`.

## Environment And Toolchain

```text
Python 3.14.4
p2p-engine 0.5.0
build 1.5.0
hatchling 1.31.0
mypy 1.20.2
pip-audit 2.10.1
ruff 0.16.4
twine 6.2.0
pytest 9.1.1
```

Module version, distribution metadata and `p2p version --format json` all
reported `0.5.0`; the editable development module resolved to this checkout's
`src/p2p_engine/__init__.py`, as expected for the recreated development
environment. `keyring` and all other runtime dependencies imported, and
`python -m pip check` reported no broken requirements.

## Validation Record

```text
PYTHON_BIN=.venv/bin/python ./scripts/check-static.sh
  All Ruff checks passed; mypy found no issues in 5 staged source files.

.venv/bin/python scripts/generate-wavekit-transition-fixtures.py --check
  verified: engine=0.5.0 receipt_schema=3

.venv/bin/python scripts/check-source-boundary.py
  verified: removed_runtime=11 removed_orphans=5 removed_mcp=25

.venv/bin/python scripts/check-doc-links.py
  verified: 26 maintained Markdown files

.venv/bin/python scripts/verify-release-metadata.py
  release metadata verified: 0.5.0

.venv/bin/python scripts/verify-release-metadata.py --release
  expected stop: actual changelog date, removal of Unreleased and final notes

./scripts/test-public.sh -q
  253 passed, 1309 deselected

./scripts/test-full.sh -q
  1562 passed

scripts/test-installed.sh --wheel <diagnostic-0.5.0-wheel> -q
  24 passed, 1538 deselected; real p2p and p2p-mcp-server passed;
  bundled vertical, portable schema 3 and read-only export preview passed;
  outbound network and Git sentinel logs remained empty

P2P_TEST_FAILURE_MODE=<mode> scripts/test-installed.sh --wheel <diagnostic-wheel>
  install-failure, missing-dependency, malformed-cli-json, mcp-timeout,
  git-invocation and interrupted-smoke all exited non-zero; every dedicated
  temporary parent was empty afterward; interrupted-smoke exited 130

pytest -q tests/test_release_artifacts.py tests/test_release_automation.py tests/test_test_scripts.py
  57 passed

scripts/audit-wheel.sh --wheel <diagnostic-0.5.0-wheel>
  exact resolved runtime freeze; no known vulnerabilities found

python -m twine check <diagnostic-wheel> <diagnostic-sdist>
  PASSED for both artifacts

two SOURCE_DATE_EPOCH-bound diagnostic builds
  wheel bytes identical; sdist bytes identical

git diff --check
  clean
```

The final diagnostic artifact set is not a release candidate and its hashes are
not release identities. Diagnostic mode validates all stable metadata but
intentionally skips only the release-finalization checks, allowing 10A to test
the exact package while the version remains `Unreleased`. The self-contained
`SHA256SUMS` in the external diagnostic output directory records the exact local
bytes without creating the impossible requirement for an sdist to contain its
own hash. The official builder still rejects `Unreleased`, so no official
candidate or release hash is claimed.

Exact local diagnostic identity, retained outside the repository at
`/tmp/p2p-10a-diagnostic-20260827-final`:

```text
cd17497d2a4dce8ad7559f37f0cf66f30eb969a64de5ced33e07bcf36dbe188e  p2p_engine-0.5.0-py3-none-any.whl
345413e9503776df3acb1568705779df18de9f1078341d2802f96c7552ff376d  p2p_engine-0.5.0.tar.gz
211be802ca3d75dcc43e144ac2dc941fab52c63aa855cd78ef31f4c28e25632a  SHA256SUMS
```

`sha256sum --check SHA256SUMS`, the project artifact verifier, `twine check`, the
installed-wheel harness and the resolved dependency audit all passed for this
exact diagnostic set. It remains explicitly non-authoritative for publication.

Current generated-resource identities:

```text
47af6f7a98fd6ea402268007650e66860dc251c59fc3b2b28460dc4cc076d640  tests/fixtures/vertical_transition/manifest-v1.json
1595455dde1427835d4ea7727d6df7eeca6dacf18804cac2766cfd5132c95db7  src/p2p_engine/resources/contracts/wavekit-cli-fixtures-v1.json
```

No coverage command, threshold, report or artifact was used or generated.

## Reviewed Allowlists

`scripts/verify-release-artifacts.py` owns three fail-unused typed allowlists:

- removed product names only in negative guards/tests;
- discarded compatibility names only in archived inventories and negative
  current-only tests;
- synthetic private path/key markers only in negative verifier/path tests and
  in the verifier's own detector source.

`security-audit-exceptions.yml` uses schema 1 and is empty. Any future exception
requires advisory ID, owner, rationale and non-expired date; duplicate,
incomplete and expired entries fail. No vulnerability or provenance exception
was used.

## Repository Scope Review

Final read-only inspection found 163 changed/untracked/deleted paths in
`p2p-engine/`, all part of this broad clean-break hardening scope. The two
project-state repositories were clean. The sibling `wavekit/` checkout already
reported 45 status entries and was not written by this implementation. No
coverage artifact was present.

## Pending Post-10A Release Gate

There are no unresolved owner decisions for the 10A implementation. Exactly
three tasks remain intentionally unchecked because they require the later
release event:

1. T031: replace `Unreleased` with the actual date and finalize the maintained
   `0.5.0` notes;
2. T073: run the official build and installed-artifact gate for the exact
   release-finalization commit;
3. T079: close the complete feature only after commit-bound CI and the immutable
   release handoff exist.

These are release prerequisites, not reasons to make release a prerequisite of
10A. No task asserts that `0.5.0` has already been published.

## Owner Handoff

The owner may now review and commit 10A while `0.5.0` remains `Unreleased`;
normal push/PR CI needs no manual provenance action. In the subsequent release
step, record the actual date and final notes in a new commit, then run the
non-publishing candidate gate for that exact 40-character SHA:

```bash
gh workflow run release-candidate.yml \
  --ref main \
  -f ref=<approved-40-character-commit-sha>
```

Release `GO` exists only after that exact SHA has a green Python 3.11/3.14
candidate run and its official artifact hashes are recorded. Creating
`v0.5.0` then triggers re-verification, GitHub attestation and create-only
publication of the same retained artifacts; the tag workflow performs no
rebuild and requires no owner-managed signing key.
