# Design - Harden P2P Engine 0.5.0 Release Candidate

## Requirements Covered

- R001-R090
- N001-N015
- AC001-AC030

## Decision Summary

Treat `0.5.0` as an immutable release candidate whose correctness must be proved
at six separate boundaries: source behavior, persisted portable state,
installed distribution, external worker fixtures, absence of runtime
source-control coupling and publication automation.
The existing full suite remains the broad regression gate, but dedicated tests
must cover defects that can remain invisible while source imports and in-process
Typer calls succeed.

The implementation reuses existing contracts and services. It does not create a
second CLI envelope, vertical lock model, package renderer or fixture schema.
It deliberately removes Git-owned CLI/MCP/runtime surfaces before they become a
0.5 contract. Release scripts orchestrate retained components from clean
environments and reject ambiguity rather than repairing published state.

## Release Blocker Matrix

| Audit finding | Required correction | Blocking evidence |
|---|---|---|
| Rich can corrupt diagnostic JSON | raw shared JSON serializer and error-path tests | installed subprocess output parses at narrow width |
| internal vertical lock leaks installation path | logical source descriptor and path-free generator | fresh source/wheel projects and archives contain no host path |
| release assets can be overwritten | create-only release flow | existing release/asset fixture fails before upload |
| tests run only after tag | reusable pre-tag candidate workflow | green 3.11/3.14 candidate run for exact SHA |
| installed smoke can use editable source | script-owned isolated environment | metadata/path/dependency assertions and real entry points |
| WaveKit fixtures mix 0.4.8/schema 2/0.5.0 | one current generator and explicit legacy fixture | generator drift test and installed resource test |
| implementation repo claims local `.p2p` | repository-specific instructions | clean-clone command/doc tests and no root setup artifact |
| release metadata unfinished | owner-approved legal/package metadata | pyproject/wheel/sdist/README equality check |
| orphan modules ship in wheel | remove or explicitly support | static inventory plus wheel absence/API evidence |
| runtime owns Git workflows | remove CLI/MCP/services/wiring and keep source control external | negative public-surface guards plus installed smoke with failing `git` sentinel |
| duplicate YAML keys collapse silently | unique-key loader at package boundary | source/archive/wheel rejection tests |
| no static/dependency/package gate | focused release quality toolchain | Ruff/type/audit/Twine results recorded |

## Key Decisions

### D001 - JSON Is Serialized Outside Rich

Machine output uses `p2p_engine.cli_contract.print_json` or the same canonical
`json_text` serializer written directly to captured stdout. Rich remains the
human renderer only. Pretty indentation is not required by the public contract;
one compact canonical document reduces width-dependent behavior and makes the
outer envelope the only JSON transport boundary.

The audit covers all direct `json.dumps` output in CLI command modules. A direct
renderer may remain only if tests prove it does not wrap, colorize or bypass the
outer envelope. New ad hoc renderers are rejected by a source inventory test.

### D002 - Diagnostic State Is Data; Failed Validation Is Structured Failure

`runtime status` is a read-only diagnostic. Missing, malformed, unsupported or
incompatible runtime declarations are returned as a successful envelope whose
`data.state` describes the project. This preserves the text command's existing
inspectability and allows workers to decide what to do without parsing a
transport error.

`validate` differs: validation errors retain exit code 1 and become an error
envelope. The first deterministic error finding supplies `error.code` and
`error.message`; `error.details.result` carries the complete normalized
validation object. Warnings-only validation remains successful. The result is
never serialized a second time into `error.message`.

Illustrative missing-runtime output:

```json
{
  "contract_version": "p2p-cli/v1",
  "ok": true,
  "operation": "runtime.status",
  "data": {
    "state": "missing_contract",
    "contract_path": ".p2p/project/runtime.yml",
    "findings": [
      {"code": "P2P266_RUNTIME_CONTRACT_MISSING", "severity": "error"}
    ]
  },
  "warnings": [],
  "error": null
}
```

Illustrative failed-validation envelope:

```json
{
  "contract_version": "p2p-cli/v1",
  "ok": false,
  "operation": "validate",
  "data": null,
  "warnings": [],
  "error": {
    "code": "P2P266_RUNTIME_CONTRACT_MISSING",
    "message": "Current projects require .p2p/project/runtime.yml.",
    "details": {
      "result": {
        "ok": false,
        "errors": 2,
        "warnings": 1,
        "infos": 0,
        "findings": []
      }
    }
  }
}
```

### D003 - Bundled Sources Have Logical, Not Physical, Identity

The vertical lock keeps the existing `source` mapping but gives `path` strict
diagnostic semantics:

```yaml
source:
  type: internal
  resolved_from: p2p_engine.resources.verticals/base_project
  path: ""
  package: p2p_engine
```

- `internal`: `path` is empty and `resolved_from` is the stable package-resource
  name.
- local source inside project root: `path` is root-relative and normalized.
- local source outside project root: `path` is empty; durable identity comes
  from coordinate/checksums and a non-physical logical source label.
- portable or registry source: identity remains coordinate and exact checksums;
  cache/extraction paths are never durable state.

Keeping the key with an empty string minimizes shape churn while removing host
identity. Readers already treat it as non-authoritative diagnostic data. A
shared path classifier recognizes POSIX absolute paths, Windows drive paths,
UNC paths, parent traversal and symlink escapes on every host platform.

### D004 - Archive Scanning Is Content-Aware And Reasoned

`scripts/verify-release-artifacts.py` expands from a package-source token scan
to a bounded scan of textual members in both archives. It checks:

- forbidden archive roots/cache/bytecode;
- exact required and forbidden members;
- current checkout and user-home path signatures;
- generic POSIX/macOS/Windows absolute path signatures in maintained fixtures,
  examples and generated state;
- credential/private-key markers and known operation-token formats;
- removed current-runtime tokens;
- package metadata and entry points.

Binary files and large files are bounded before decoding. A typed allowlist maps
`archive member + rule + optional exact token` to a non-empty reason. Tests fail
unused allowlist entries so exceptions cannot outlive their need. Historical
specs excluded by Hatch do not weaken scanning of distributed docs/tests.

### D005 - Installed-Wheel Validation Owns Its Environment

`./scripts/test-installed.sh` remains the supported user-facing command, but it
no longer chooses `.venv/bin/pytest`. It receives the exact wheel path or derives
the single exact current-version wheel from a clean supplied distribution
directory, creates a temporary virtual environment and installs the wheel plus
test-only smoke dependencies.

The implementation may delegate orchestration to a Python script, but the shell
entry point remains small and fail-fast. The helper records:

- interpreter and pip versions;
- wheel path and SHA-256;
- installed distribution metadata;
- resolved runtime dependency versions;
- module import path;
- console-script paths;
- smoke command results.

It then changes directory to an external temporary root, unsets `PYTHONPATH`,
sets `PYTHONNOUSERSITE=1` and executes tests. A caller-provided interpreter or
pytest binary is not accepted as proof unless an explicit internal CI mode first
passes all identity assertions.

### D006 - Installed Smoke Uses Real Process Boundaries

In-process service and Typer tests remain useful but no longer define installed
smoke alone. The smoke harness invokes:

1. `p2p version --format json` outside any project;
2. `p2p init` into a temporary project;
3. runtime/workspace/status/validate JSON reads;
4. registry refresh with no remote provider;
5. bundled-resource and portable-schema-3 operations;
6. representative structure export/replacement eligibility or offline
   round-trip operations already marked as smoke;
7. `p2p-mcp-server` through a bounded JSON-RPC initialize and tools/list
   exchange.

The MCP subprocess receives protocol input through stdin, must emit only framed
protocol output on stdout, must expose the expected catalog, and is terminated
gracefully with a hard timeout fallback. Tests assert no orphan process remains.

Network denial begins after environment installation. Test adapters reject
socket/HTTP access while allowing local subprocess and filesystem operations.
This proves product offline behavior without pretending dependency installation
itself is offline.

The harness also prepends a sentinel executable named `git` that records an
invocation and exits non-zero. All retained smoke operations must pass and the
sentinel log must remain empty. A second case uses a project root containing an
opaque `.git` sentinel tree and proves P2P leaves those bytes unchanged.

### D007 - Pre-Tag And Tag Gates Share One Definition

CI is split by responsibility:

- normal CI runs source/public/full checks on pull request and main for Python
  3.11 and 3.14;
- a reusable release-candidate workflow builds, verifies, reproducibility-tests
  and installed-tests one exact commit without publishing;
- manual dispatch provides the owner with pre-tag release-candidate evidence;
- the tag-triggered workflow invokes the same reusable gate for the tagged SHA
  and publishes only after it succeeds.

Repository branch protection is an external GitHub setting, so docs identify it
as required release policy and CI emits enough SHA/run evidence to audit the
owner's tag decision. The workflow never assumes a tag's existence proves that
pre-tag validation happened.

These workflows belong to maintenance of the P2P Engine source repository. They
do not expose product commands, do not enter the wheel's runtime import graph and
do not permit the implementation agent to commit or publish. Local feature
completion validates workflow structure and hands the owner an exact command;
the owner-run workflow supplies commit-bound evidence afterward.

### D008 - Published Versions Are Create-Only

The release job checks, in order:

1. tag format and exact package version;
2. tag commit equals the verified candidate SHA;
3. changelog section is dated and not `Unreleased`;
4. no GitHub Release exists for the tag;
5. no same-version release assets exist;
6. artifact hashes match verified build outputs.

Any conflict stops publication. There is no `--clobber`, update branch or
automatic delete/recreate path. Recovery from a partial publication is an owner
operation with explicit inspection; automation does not guess which artifact is
authoritative.

### D009 - One Build Lineage, Exact Names And Checksums

Release-candidate builds occur in clean directories with a constrained build
toolchain. The workflow builds twice for reproducibility but designates one
verified artifact pair as the upload pair only after byte comparison succeeds.
Artifact names are computed from normalized project/version metadata and passed
explicitly to verification and upload.

`SHA256SUMS` uses a stable filename order and conventional two-space separator.
Checksums prove downloaded-byte identity, not publisher identity. GitHub
Artifact Attestations provide the selected provenance policy. The candidate
workflow retains the exact verified wheel, sdist and checksum file; the tag-only
workflow downloads that same set, rechecks it, attests all three files and only
then publishes them. Normal pushes and pull requests never receive attestation
permissions. Third-party actions are commit-SHA pinned and GitHub manages the
Sigstore signing identity, so the owner has no recurring signing-key operation.

### D010 - Current Fixtures Are Generated, Legacy Fixtures Are Labeled

`tests/fixtures/vertical_transition/` remains the current 0.5.0 WaveKit handoff
set. Its generated manifest and payloads are regenerated from the same contract
constants used by runtime and the packaged resource. The only retained old
behavior in that directory is explicitly named characterization input, such as
`legacy-0.4.7-characterization.json`.

A generator script supports write and `--check` modes. It uses deterministic
IDs, actors, keys, roots, clocks and ordering through supported service inputs or
explicit fixture-only injected clocks. It never rewrites arbitrary output text
to hide nondeterminism. The manifest is written last from actual member bytes.

The packaged `wavekit-cli-fixtures-v1.json` is generated or validated from the
same release convergence model, so it cannot report receipt schema 3 while a
supposedly current golden manifest reports schema 2.

### D011 - The Implementation Repository Has Manual Repository Instructions

`p2p-engine/` is source, tests, docs, scripts and local implementation specs. It
does not contain canonical P2P Engine project state. Therefore:

- stale generated root `P2P-SETUP.md` is removed;
- root agent instruction files are maintained as repository instructions rather
  than generated project instructions tied to absent state;
- implementation checks use pytest/release scripts;
- governance examples require an explicit external project root and are not
  assumed available in a standalone clone;
- runtime tests continue to prove that normal user projects receive generated
  P2P setup and agent files.

This decision corrects the implementation-repository documentation boundary.
The separate D014 boundary removes Git-specific behavior from `p2p init` while
preserving generation of normal P2P setup and agent files in target projects.

### D012 - Legal Metadata Requires An Owner Decision

The implementation must stop before final metadata changes if the owner has not
selected `GPL-3.0-only` versus `GPL-3.0-or-later` and the legal author/maintainer
identity. The full GPL text alone is not interpreted as that choice.

Once selected, PEP 639 metadata is the machine source of truth. README and
package metadata reflect it; deprecated license classifiers are not used.
Canonical URLs are verified against the actual repository and issue tracker.

### D013 - Confirmed Orphan Modules Are Removed Before They Become Accidental API

The five audited modules have no maintained imports, tests or current docs. The
implementation first repeats static, runtime-entry-point and importlib-resource
inventory. If the result remains empty, it deletes the modules and asserts their
absence from the wheel. Compatibility aliases are not added for undocumented
alpha-only modules.

If a real maintained consumer is discovered, the task stops removal for that
module and requires a documented supported contract and direct tests. This is a
classification result, not permission to leave an ambiguous package surface.

### D014 - Source Control Is External To The Product

The owner decision supersedes the earlier transitional classification. Git is
used to develop and release the `p2p-engine/` source repository in the same way
as for any other software, but it is not a P2P Engine project primitive. Version
`0.5.0` therefore removes the current Git-owned runtime slice before publication.

The removal boundary includes:

- the `sync` CLI group and all sync MCP tools;
- proposal draft commit and proposal branch create/status/publish/review/
  accept-branch/reject-branch/merge/finalize/cleanup/retire/scan operations;
- Git-backed Work scan/branch/submit/review/publish/request-review/accept/
  finalize/cleanup operations, while preserving neutral Work planning/read
  commands;
- project Git remote configuration, Git-derived init options/output, doctor Git
  status and automatic `.gitignore` mutation;
- the Git subprocess adapter, branch/sync/draft-commit services, P2PWorkspace
  wiring, Git-backed consent audit and corresponding operation/capability lists;
- Git-policy, branch/commit/provider-permission semantics in generated Change
  Set/Work/permission state and agent instructions.

This is an explicit pre-0.5 clean break. Removed commands do not survive as
aliases, disabled plugins or tombstones. Proposal decision-event governance,
logical Change Sets, neutral Work plans, AuthorityContext, receipts and opaque
external implementation references remain product behavior.

The allowed Git boundary is outside installed runtime: maintainers may use Git
and GitHub to review source changes, CI may bind a candidate to an approved SHA,
and release automation may publish a tag's artifacts. No module under
`src/p2p_engine/` imports that tooling or invokes `git`.

### D015 - Portable YAML Uses The Existing Unique-Key Contract

`VerticalPackageService._canonical_content` passes YAML members through
`UNIQUE_LOADER_CONTRACT`. The same parser behavior applies when packaging a
directory and inspecting an archive. Duplicate keys fail before canonical bytes
or an output archive are written. Error projection preserves the public
portable-pack error family and includes only the member name and safe parser
diagnostic.

JSON duplicate-key policy is not broadened in this feature because the audit
finding and established loader contract concern YAML. A later cross-format
strictness feature may evaluate JSON without hiding that scope expansion here.

### D016 - Quality Gates Are Minimal, Staged And Evidence-Based

The initial mandatory tool set is:

- Ruff for syntax, imports, undefined names, unused imports and selected
  correctness rules, without repository-wide formatting;
- a staged type checker target for changed release/contract/serialization
  modules, with its target list documented and no blanket silent ignore;
- `pip check` and a vulnerability audit against the resolved release runtime;
- `twine check` or equivalent standards-based wheel/sdist metadata validation;
- project-specific artifact, fixture drift, link, secret and path checks.

Coverage is excluded from this feature's commands, artifacts and verdict. The
accepted advisory feature may remain available as optional developer tooling,
but 10A neither runs nor records it. Test adequacy is demonstrated by a reviewed
requirement-to-test matrix and direct positive, negative, failure-path,
installed-artifact and regression tests. A percentage cannot compensate for a
missing test or a failing behavior.

### D017 - Project-Specific Verification Complements Standard Tools

Standard package tools do not know P2P's bundled verticals, MCP contract,
current-only policy or WaveKit fixture tuple. `verify-release-artifacts.py`
remains authoritative for those project-specific rules and is expanded rather
than replaced. Conversely, it does not reimplement dependency vulnerability or
PEP metadata validation already owned by standard tools.

### D018 - MCP Preserves Domain Contracts And Removes Git Tools

No new MCP catalog or handler is added. The existing Git-owned collaboration,
sync, project-remote, proposal-branch and Work-branch tools are deleted from
catalog definitions, the registry, dispatch and handlers. Retained domain tools
remain semantically stable. Project structure export/replacement remains
eligibility/preview read-only in MCP; package writes, destination paths, apply
and remote vertical publication remain CLI/local-service boundaries.

### D019 - Task And Historical Reconciliation Is Evidence-Based

Unchecked PROP-107 tasks are not marked complete merely because later features
exist. Each is linked to current files/tests/commands or marked superseded by an
exact hardening task and rationale. Historical documents remain historically
accurate, but their banners and tables may be corrected when they currently
claim contradictory status.

### D020 - Implementation Hands Off; The Owner Controls Git And Publication

The implementation agent may inspect `git status`/`git diff` as external
development evidence, but performs no Git mutation: no branch creation, commit,
push, tag, release or upload. Local completion produces
`READY_FOR_OWNER_REVIEW` or `NOT_READY` plus verified local artifacts.

After review, the owner may externally create or approve a source commit while
the changelog and maintained release notes remain `Unreleased`. This completes
the implementation handoff, not the release. In the later release step the
owner records the actual date, finalizes the notes in a new approved commit and
runs the pre-tag candidate gate for that exact finalization SHA. Only that gate
can produce release-candidate `GO`; the owner then creates `v0.5.0` and starts
publication. This avoids making the release a prerequisite of its own
preparation, while preserving commit-bound CI and keeping Git outside P2P
runtime.

## Components And Ownership

### Runtime And Serialization

- `src/p2p_engine/cli_contract.py`: canonical JSON serialization and envelope
  handling.
- `src/p2p_engine/cli_commands/runtime.py`: diagnostic status rendering.
- `src/p2p_engine/cli_commands/project_status.py`: validation rendering and
  structured failure preservation.
- Other `src/p2p_engine/cli_commands/*.py`: direct JSON renderer inventory only;
  edits are limited to paths that violate R001-R008.

### Source-Control Boundary Removal

- `src/p2p_engine/cli.py`, `cli_commands/proposals.py`,
  `cli_commands/proposal_branches.py`, `cli_commands/work.py`,
  `cli_commands/work_specs.py`, `cli_commands/project_ops.py`,
  `cli_commands/changes.py` and `cli_commands/doctor.py`: remove Git-owned
  command registration/options/output while retaining neutral domain commands.
- `src/p2p_engine/storage/git.py`: remove from source and wheel.
- `src/p2p_engine/services/sync.py`, `proposal_branches.py`,
  `work_branches.py`, `proposal_drafts.py` and `gitignore_hygiene.py`: remove
  after extracting any independently justified non-Git helper.
- `src/p2p_engine/services/remote_profile.py`: remove the Git remote profile; a
  future provider-neutral hosted-service configuration requires its own
  contract and is not inferred from this service.
- `src/p2p_engine/storage/filesystem.py`: remove imports, lazy service caches,
  public facade methods and operation-compatibility entries for removed Git
  behavior.
- `src/p2p_engine/mcp/catalog/collaboration.py`, `catalog/work_specs.py`,
  `catalog/project.py`, `catalog/maintenance.py`, matching handlers including
  maintenance/proposal dispatch, `mcp/registry.py`, `mcp/tools.py` and
  `mcp/consent_audit.py`: remove tool definitions/routes and make retained
  consent consumption filesystem/receipt based, never commit based.
- `src/p2p_engine/services/project_initialization.py`, `permissions.py`,
  `changes.py`, `work_planning.py`, `context_packets.py`,
  `mutation_receipts.py`, `project_metadata.py`, `agent_templates.py`,
  `agent_instructions.py` and `workspace_operation_compatibility.py`: eliminate
  repository mode, `.gitignore`, Git policy, branch/commit capability and
  generated Git workflow semantics while preserving neutral P2P state.
- `pyproject.toml`: remove Git-only test taxonomy/runtime claims and keep only
  source-development metadata that is not installed product behavior.

### Vertical Source And Package Safety

- `src/p2p_engine/services/project_verticals.py`: stable source projection and
  lock serialization.
- `src/p2p_engine/core/project_verticals.py`: source/lock contract only if
  strict path semantics require a typed invariant.
- `src/p2p_engine/services/vertical_packages.py`: unique-key parsing before
  canonicalization.
- `src/p2p_engine/foundation/yaml_loaders.py`: reuse existing loader contract;
  no parallel loader.
- `examples/*/.p2p/project/vertical.lock.yml`: regenerated path-free examples.

### Fixtures And Contract Convergence

- `src/p2p_engine/core/release_contracts.py`: current contract tuple.
- `src/p2p_engine/services/release_convergence.py`: fixture/convergence model.
- `src/p2p_engine/resources/contracts/wavekit-cli-fixtures-v1.json`: packaged
  current worker fixture inventory.
- `tests/fixtures/vertical_transition/`: current golden outputs plus explicitly
  historical characterization input.
- `scripts/generate-wavekit-transition-fixtures.py` or a coherently named
  equivalent: deterministic generator/check mode.

### Packaging And Release Automation

- `pyproject.toml`: metadata, build toolchain constraints and dev quality tools.
- `scripts/verify-release-artifacts.py`: complete archive and metadata checks.
- `scripts/verify-convergence-gate.py`: unchanged contract gate unless a drift
  test requires added hardening evidence.
- `scripts/test-installed.sh`: isolated installed-artifact orchestrator.
- Optional focused helper under `scripts/`: MCP stdio smoke or release
  environment verification, kept private to developer/release tooling.
- `.github/workflows/ci.yml`: source pre-tag matrix if introduced.
- `.github/workflows/release-candidate.yml`: reusable/manual candidate gate if
  introduced.
- `.github/workflows/release.yml`: create-only tagged publication.

`.github/workflows/**` and explicitly classified developer/release scripts,
including import-provenance or benchmark metadata helpers when retained, may use
Git/GitHub metadata because they manage or inspect the source repository
externally. They are excluded from runtime-import permissions, not from source
control, and are never installed entry points.

### Documentation And Tracking

- `AGENTS.md`, `CLAUDE.md`: implementation repository instructions.
- `P2P-SETUP.md`: removed from the implementation repo and sdist.
- `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, `ROADMAP.md`.
- `docs/INSTALL.md`, `docs/TESTING.md`, `docs/CLI-CONTRACT.md`,
  `docs/CLI-GUIDE.md`, `docs/MCP.md`, `docs/AGENT-INTEGRATION.md`.
- `docs/development/cli-primitive-inventory.md` and
  `docs/development/wavekit-vertical-transition-handoff.md`.
- Current product-boundary and command inventories remove Git-native positioning;
  retained `docs/vision/**` Git history is labeled archival/superseded.
- `CHANGELOG.md` and generated release notes.
- PROP-107 `tasks.md` plus an implementation note or exact supersession links.
- This feature gains `implementation.md` during execution with evidence; it is
  not created as completed evidence during specification authoring.

### Tests

- `tests/test_cli_contract.py`: envelope and width-independent serializer rules.
- `tests/test_cli.py`: runtime/validate diagnostic regressions.
- `tests/test_project_verticals.py`: source projection and fresh lock privacy.
- `tests/test_portable_verticals.py`: duplicate-key and installed/offline pack
  behavior.
- `tests/test_vertical_transition_impact.py`: generated current fixture tuple.
- `tests/test_release_convergence.py`: packaged bundle and operation inventory.
- `tests/test_release_artifacts.py`: archive members, metadata, path/secret scan,
  dead-module/Git-runtime absence and exact artifacts.
- `tests/test_version_consistency.py`: version/changelog/metadata alignment.
- `tests/test_current_only_surface.py`: historical allowlist and removed Git
  surface negative contract.
- A focused `tests/test_no_runtime_git.py` or coherently named equivalent:
  command/tool/module absence, no subprocess invocation, non-Git initialization,
  opaque `.git` invariance and inert external traceability metadata.
- A focused installed-entrypoint test module if keeping subprocess cases out of
  broad source tests improves isolation.

## Installed-Wheel Execution Contract

The supported script shape is intentionally explicit:

```text
./scripts/test-installed.sh --wheel dist/p2p_engine-0.5.0-py3-none-any.whl
```

Optional CI controls may select a temporary base or package index, but may not
disable identity checks. The script returns non-zero for:

- zero or multiple candidate wheels;
- wheel/version/metadata mismatch;
- source-tree or editable import;
- missing console script or dependency;
- any invocation of the failing `git` sentinel or mutation of opaque `.git`
  sentinel bytes;
- failed `pip check`;
- malformed CLI JSON;
- MCP handshake timeout/protocol contamination;
- network access during offline phase;
- failed smoke test or leaked child process.

The script prints a compact human summary only after subprocess outputs have
been parsed and verified. Secrets and full environment dumps are excluded.

## Release Workflow State Machine

```text
implementation agent: local hardening + diagnostic artifact gates
-> READY_FOR_OWNER_REVIEW (no commit/push/tag/release)
owner/source repository: review and create the 10A source commit
-> normal CI while 0.5.0 remains Unreleased
-> later release step records the actual date and final release notes
-> owner commits that finalization and dispatches candidate gate for exact SHA
-> source CI green on 3.11 and 3.14
-> clean build A and clean build B
-> byte equality and project/standard artifact verification
-> isolated installed-wheel smoke with no usable Git
-> vulnerability and metadata checks
-> release-candidate GO records owner-approved SHA + artifact hashes
-> owner creates v0.5.0 tag at the verified SHA
-> tag workflow consumes the retained exact candidate artifact set
-> GitHub attests wheel, sdist and SHA256SUMS for the tag identity
-> verify no existing release/assets
-> create release once with those exact attested artifacts and checksums
```

No state transition points backward by overwriting an asset. A failed or partial
publication stops for owner inspection.

## Artifact Identity

The owner-run release evidence binds:

- Git commit SHA;
- tag and semantic version;
- Python/build tool versions;
- wheel filename and SHA-256;
- sdist filename and SHA-256;
- `SHA256SUMS` bytes/hash;
- wheel METADATA version/license/dependencies/entry points;
- complete P2P release-contract tuple;
- current fixture manifest hashes;
- test/gate workflow run identifiers.

The commit SHA and tag are supplied by the external repository/CI context. P2P
runtime does not discover them. This evidence is release tooling output, not P2P
project-state governance.

## Error Handling

- CLI serialization defects produce focused test failures naming command,
  terminal width, stdout and parse position.
- Unsafe source paths fail validation/package verification with member/path
  category but do not echo secrets or arbitrary file bodies.
- Duplicate YAML fails before output creation and leaves source bytes unchanged.
- Installed identity mismatch reports all compared versions/paths after
  normalizing paths but does not print environment secrets.
- A runtime attempt to invoke `git` fails the no-Git sentinel test and reports
  the invoking command/test boundary without executing a real repository action.
- Dependency advisories report package, installed version, advisory and fixed
  versions; exceptions require owner, rationale and expiry.
- Existing release/assets fail before any upload command.
- Reproducibility failure reports differing archive members and metadata rather
  than replacing one build with another.
- Fixture drift reports missing/extra/hash-mismatched members and instructs use
  of the generator, not manual edits.
- Unknown license choice blocks metadata finalization and publication.

## Migration And Compatibility

- Version remains `0.5.0`; this is a pre-publication correction, not `0.5.1`.
- Retained CLI command names, top-level envelope version and release contract
  versions do not change. Git-owned commands/tools listed in R081-R082 are
  deliberately removed before the public `0.5.0` contract is published.
- Runtime diagnostic JSON becomes usable where it was previously malformed.
- Schema-4 lock shape retains its source mapping and empty `path` key but no
  longer persists physical paths. No 0.4.x migration is introduced.
- Current examples and fixtures are regenerated. Explicit historical inputs
  remain read-only and clearly versioned.
- Removed orphan modules have no promised public contract. Discovery of a real
  consumer changes that module's disposition before deletion.
- Existing pre-release Git branch/sync metadata has no migration path in this
  current-only runtime. It is not scanned, converted or automatically deleted;
  affected pre-release workspaces must be recreated under the documented 0.5
  clean-break policy.
- Retained MCP names, schemas, permissions and mutation boundaries remain
  unchanged; Git-owned MCP names are an explicit negative contract.

## Validation Matrix

| Boundary | Required proof |
|---|---|
| CLI source | valid/missing/malformed runtime and validate JSON at multiple widths |
| structure storage | bundled/internal, root-local, external-local and Windows-style path cases |
| portable package | duplicate YAML, canonical bytes, no partial output, offline behavior |
| fixtures | generator `--check`, hashes, current tuple, historical separation |
| MCP source | registry/schema/permission contract tests |
| wheel | metadata/path/dependency/resource/entry-point assertions |
| installed CLI | real subprocess version/init/status/validate/vertical workflow |
| installed MCP | bounded stdio handshake and catalog invariants |
| source-control boundary | exact CLI/MCP/module/operation absence and no runtime Git calls |
| opaque external repository | `.git` sentinel byte invariance and inert traceability refs |
| sdist/wheel | full member, path, secret, obsolete-token and metadata scan |
| reproducibility | two clean byte-identical builds |
| quality | Ruff, staged typing, pip check, vulnerability audit, Twine check and requirement-to-test review; no coverage input |
| broad regressions | focused, public and full suites on supported Python versions |
| release | create-only dry-run/fixture tests and exact-name checksum generation |

## Implementation Sequence

1. Capture failing CLI/path/installed-environment regressions.
2. Correct shared serialization and vertical source projection.
3. Add strict pack parsing and regenerate examples.
4. Build the deterministic fixture generator and reconcile PROP-107.
5. Replace installed smoke with isolated real-entry-point proof.
6. Remove Git-owned CLI/MCP/runtime/state/template surfaces and add no-Git
   installed guards.
7. Expand artifact verification and remove confirmed orphan modules.
8. Correct repository/docs/legal/package metadata after owner license decision.
9. Add staged quality gates and reusable pre-tag CI.
10. Make tagged release create-only with exact artifacts/checksums/provenance.
11. Run the complete local matrix, write implementation evidence and report
    `READY_FOR_OWNER_REVIEW` or `NOT_READY`; owner CI later reports release `GO`.

This order prevents release automation from being declared green while known
runtime and artifact defects are still present.

## Risks And Tradeoffs

- Risk: changing JSON rendering alters fixture formatting.
  Mitigation: the envelope is semantic JSON, not whitespace; regenerate only
  fixtures that intentionally bind exact bytes and document that contract.
- Risk: path-free locks remove useful local diagnostics.
  Mitigation: keep stable logical source/package/checksum evidence and allow
  ephemeral physical paths only in non-persisted process diagnostics.
- Risk: installed tests download dependencies and become flaky.
  Mitigation: separate install from offline phase, constrain tooling, record
  resolved dependencies and keep bounded retries at package-index level only.
- Risk: static tooling creates broad cleanup churn.
  Mitigation: start with correctness/import rules and targeted typing; do not run
  a repository-wide formatter in this feature.
- Risk: vulnerability database availability blocks a release unexpectedly.
  Mitigation: pre-run in candidate CI, cache only advisory data safely and use
  explicit expiring owner exceptions rather than silently skipping.
- Risk: fixture regeneration changes fields not consumed by WaveKit yet.
  Mitigation: bind generated output to documented current CLI contracts and
  review diffs; do not modify WaveKit in this feature.
- Risk: deleting orphan modules breaks an unknown external import.
  Mitigation: repeat static/dynamic/public inventory and retain only with an
  explicit supported API decision.
- Risk: removing Git-owned commands breaks users of unpublished/pre-release
  surfaces.
  Mitigation: treat removal as an explicit owner-approved 0.5 clean break,
  preserve neutral proposal decisions and Work planning, list every removed
  command/tool in the changelog and do not ship misleading compatibility stubs.
- Risk: Git coupling survives indirectly through consent, initialization,
  templates or facade wiring after obvious commands are deleted.
  Mitigation: combine exact negative inventories, import/subprocess guards,
  generated-resource scans and installed smoke with a failing `git` sentinel.
- Risk: GitHub workflow reuse becomes complex.
  Mitigation: keep source, candidate and publication responsibilities separate
  and pass immutable artifacts/evidence rather than duplicating shell blocks.
- Risk: legal metadata cannot be inferred technically.
  Mitigation: make owner selection a hard prerequisite, not an implementation
  guess.

## Out Of Scope

- Actual tag/release publication.
- WaveKit implementation or fixture consumption changes.
- New P2P domain behavior or MCP mutation tools.
- Workspace migration or legacy compatibility runtime.
- External Git management of the `p2p-engine/` source repository, including the
  owner's commit/review/tag actions and GitHub repository settings.
- Whole-repository typing or formatting conversion.
- Coverage collection, reports, artifacts, thresholds or percentage-based
  release policy.
- PyPI account/token/publication setup.
