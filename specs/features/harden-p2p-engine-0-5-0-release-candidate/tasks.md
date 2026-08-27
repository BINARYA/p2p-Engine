# Tasks - Harden P2P Engine 0.5.0 Release Candidate

All tasks start unchecked. A task may be marked complete only when its stated
source, test, documentation or observed-command evidence exists and has been
reviewed. Passing the full suite does not by itself complete a task that owns a
package, fixture, legal, CI or release-immutability contract.

Task completion certifies implementation readiness only. It never authorizes the
implementation agent to create a branch/commit, push, tag or publish. CI tasks
are complete when the workflow contract and local validation exist; the owner
must later run that workflow for an approved commit before the release gate can
return `GO`.

## Phase 0 - Boundary, Baseline And Release Decision Inputs

- [x] T001 [R001-R090, N009-N015, D014, D019-D020] Re-read workspace/repository
  instructions, this feature, `converge-project-structure-surfaces`, PROP-107,
  the external source-control boundary, the optional coverage feature and
  current release docs. Completion evidence: `implementation.md` records the
  exact scope boundary, predecessor, coverage exclusion, Git/runtime separation
  and operational exclusions before source edits begin.
- [x] T002 [R018-R027, R071, N006-N008, D005-D006] Recreate or reinstall the
  development environment from current `.[dev]` metadata before using it as
  release evidence. Completion evidence: module version, distribution metadata
  and CLI version all report `0.5.0`, `p2p_engine.__file__` is explained, all
  runtime dependencies including `keyring` import, and `pip check` passes.
- [x] T003 [R001-R017, R040-R090, D014, D019] Capture the audit baseline as executable
  regressions or a reproducible command record: malformed runtime JSON,
  collapsed validation details, bundled lock host path, stale installed
  environment, mixed fixture versions, release `--clobber`, root setup drift and
  orphan modules, plus Git-owned CLI/MCP/services/init/consent/templates.
  Completion evidence: each finding maps to a later task and no finding is
  represented only by prose.
- [x] T004 [R028-R039, R056-R060, R075, D007-D009, D012] Obtain and record the
  owner decisions required before publication: exact SPDX license expression,
  legal author/maintainer identity, canonical URLs, provenance policy and
  release date policy. Completion evidence: dated decision inputs in
  `implementation.md`; no value is inferred by the implementer.
- [x] T005 [R031, R039, R087, N009, N015, AC025, D008, D020] Record the
  implementation-agent boundary: read-only `git status`/`git diff` inspection is
  allowed, but no branch, commit, push, tag, GitHub Release, asset upload or
  cross-repository write is allowed. Completion evidence: checks are limited to
  `p2p-engine/`, no Git mutation occurred and owner source-control/CI/publication
  actions are a separate handoff.

## Phase 1 - Machine-Safe CLI JSON

- [x] T006 [R001-R008, AC001-AC002, D001-D002] Add failing regression tests for
  `runtime status --format json` with missing, invalid, unsupported and
  incompatible contracts at normal and narrow terminal widths. Cover in-process
  Typer and real subprocess stdout parsing, exit behavior and ANSI absence.
- [x] T007 [R001-R003, R007-R008, D001] Inventory every CLI direct JSON output
  call (`console.print`, `console.out`, `typer.echo`, `print` and helper
  renderers), classify safe/unsafe paths and add a guard against new
  Rich-mediated machine JSON. Completion evidence: reviewed inventory plus
  passing source guard.
- [x] T008 [R001-R004, R007, D001-D002] Move runtime-status JSON to the shared raw
  serializer and preserve diagnostic states as successful structured data.
  Completion evidence: T006 regressions pass without changing text rendering.
- [x] T009 [R001-R003, R005-R006, D001-D002] Move validation JSON to the shared
  serializer and preserve the complete result in structured failure details.
  Add multiple-error/warning/long-suggested-command tests proving no nested JSON
  string and stable first-error identity.
- [x] T010 [R001-R008, R079, N005-N007, AC001-AC002, AC020] Run the complete JSON
  command inventory through success and representative parser/domain failure
  cases. Completion evidence: one envelope per command, stable CLI contract v1,
  no width/color/TTY dependence and no unexplained output exception.

## Phase 2 - Path-Free Vertical Locks And Examples

- [x] T011 [R009-R013, D003] Implement one shared source-path classification and
  serialization rule for internal, project-relative, external-local, portable
  and registry sources. Cover POSIX, macOS, Windows drive, UNC, traversal and
  symlink-escape inputs without depending on the host OS.
- [x] T012 [R009-R012, D003] Change bundled/internal lock projection to keep
  package and logical `resolved_from` while writing an empty physical `path`.
  For outside-root local sources, preserve coordinate/checksum identity without
  persisting the absolute resolution path.
- [x] T013 [R013, R015, N003-N004, D003] Add source-tree initialization and
  read-only validation tests for every bundled vertical plus inside/outside-root
  local sources. Prove forbidden current lock paths produce a deterministic
  finding and validation does not alter bytes.
- [x] T014 [R013-R014, AC003, D003] Regenerate maintained example projects through
  their owning current initialization/generation workflow. Completion evidence:
  byte review of changed example state and no manually edited lock-only shortcut.
- [x] T015 [R009-R017, AC003-AC004, D003-D004] Add path-privacy assertions to
  fresh source and installed-wheel project tests, including exact byte
  invariance of unrelated project structure, readiness, origin and authority
  state.

## Phase 3 - Strict Portable Vertical Parsing

- [x] T016 [R067-R068, N003-N005, D015] Route every portable-package YAML member
  through `UNIQUE_LOADER_CONTRACT` before canonicalization. Preserve the existing
  package service and public error family; do not add a second parser/renderer.
- [x] T017 [R067-R068, AC018, D015] Add directory, archive and installed-wheel
  tests for duplicate keys in manifest, rubrics, section and nested mappings.
  Prove deterministic member-safe errors, unchanged source bytes, no partial
  output and parity with valid canonical packages.

## Phase 4 - Current WaveKit Fixture Generation And PROP-107 Closure

- [x] T018 [R040-R046, N001, D010] Implement one deterministic fixture generator
  with write and `--check` modes for current vertical-transition golden outputs
  and the manifest. Use supported services/CLI contracts, fixed canonical
  inputs and explicit test clocks rather than output-text scrubbing.
- [x] T019 [R041-R045, D010] Regenerate current install/adopt/migrate transition
  fixtures for engine `0.5.0`, CLI v1 and mutation receipt schema 3. Review every
  payload diff for contract intent and recompute the manifest from actual bytes.
- [x] T020 [R041, R043, R046, D010] Keep
  `legacy-0.4.7-characterization.json` explicitly historical and ensure no
  legacy payload is indexed as current. Correct the WaveKit transition handoff
  to identify the exact 0.5.0 current bundle and its historical input boundary.
- [x] T021 [R040-R046, R079, AC010-AC011, D010, D017] Bind the checked-in golden
  manifest, packaged `wavekit-cli-fixtures-v1.json`, release contract constants
  and convergence inventory to one testable tuple. Add generator drift,
  missing/extra member, hash, path, secret and installed-resource tests.
- [x] T022 [R047, R065, AC012, D019] Reconcile PROP-107 T015-T018 using exact
  fixture, docs, command and validation evidence from current implementation.
  Add its missing implementation note or explicit supersession links; do not
  check tasks whose original acceptance criteria remain unmet.

## Phase 5 - Repository Boundary And Documentation Repair

- [x] T023 [R048-R051, R088, D011, D014] Remove stale root `P2P-SETUP.md` from the
  implementation repository and replace/generated-status-correct root
  `AGENTS.md` and `CLAUDE.md` with repository-specific instructions. Preserve
  generated user-project templates in runtime resources and tests, but remove
  their P2P-managed Git instructions under T042.
- [x] T024 [R050-R051, N009, D011] Correct `README.md`, `CONTRIBUTING.md`,
  `specs/README.md` and relevant steering files so implementation checks target
  source/tests and optional P2P governance commands require an explicit external
  project-state root.
- [x] T025 [R052, R055, D011] Reconcile `docs/INSTALL.md` and `SECURITY.md` around
  the GitHub Release wheel channel, supported Python versions, integrity
  verification and source-install status. Remove mutually contradictory
  source-only language.
- [x] T026 [R001-R008, R041-R046, R053, R081-R089, D001-D002, D010, D014, D019] Update maintained
  CLI contract/guide, MCP, agent integration, testing and WaveKit handoff docs
  for corrected diagnostic envelopes, real installed smoke and current fixture
  semantics. Document the exact removed Git product surfaces, preserve external
  source-repository Git only, make historical CLI inventory scope unambiguous
  and remove its `workspace migrate` current/removed contradiction.
- [x] T027 [R054, R064-R066, R088-R089, D014, D019] Update `ROADMAP.md` and maintained
  current-surface inventory to show completed 0.5.0 work, this mandatory gate,
  WaveKit handoff, removed Git runtime surfaces, external source-control
  boundary, superseded historical features and deferred merge/restore without
  claiming implementation.
- [x] T028 [R048-R055, R074, AC013-AC014, AC023, D011] Run relative-link,
  copy-paste command and stale-version/path scans over maintained docs. Add
  narrow historical allowlists with reasons and fail unused exceptions.

## Phase 6 - Legal, Package And Release Metadata

- [x] T029 [R056-R058, D012] After the owner decision in T004, add PEP 639 SPDX
  license metadata, approved author/maintainer identity, canonical URLs and
  non-deprecated classifiers to `pyproject.toml`. Keep license tooling in build
  metadata, not runtime dependencies.
- [x] T030 [R056-R058, AC015, D012] Update README license/copyright wording and
  add tests comparing pyproject, module, wheel METADATA and sdist PKG-INFO. Prove
  the full license file and exact expression are packaged.
- [ ] T031 [R059-R060, D008-D009, D012] Finalize the 0.5.0 changelog section with
  the owner-approved release date and complete clean-break summary. Replace the
  release-note stub with deterministic notes derived from that section plus
  install, compatibility, checksum and provenance information.
- [x] T032 [R030, R056-R060, AC015, D008-D012] Add a release metadata gate that
  rejects `Unreleased`, tag/version disagreement, missing legal fields,
  conflicting URLs, deprecated license classifiers and release notes for the
  wrong version before build/upload.

## Phase 7 - Obsolete Runtime And External Source-Control Boundary

- [x] T033 [R061-R063, R065-R066, D013, D019] Repeat static import, entry-point,
  dynamic-import, resource and documentation inventory for the five audited
  orphan modules and all other zero-inbound package modules. Record every
  intentional entry-point/resource false positive.
- [x] T034 [R061, D013] Remove `core/project.py`, `core/task.py`, `core/plan.py`,
  `exporters/markdown.py` and `exporters/openspec.py` when T033 confirms they are
  unsupported. If a maintained consumer exists, stop deletion for that module
  and add the explicit API/docs/tests required by R061.
- [x] T035 [R062-R063, AC016, D013, D017] Add source and wheel guards for removed
  modules plus Ruff/static checks for orphan imports/resources. Completion
  evidence: no import failure, stale docs reference or packaging member.
- [x] T036 [R064-R066, R080-R090, AC017, AC026-AC029, D014, D019] Produce an exact
  source-control removal inventory covering CLI commands/options, MCP tools,
  handlers/routes, consent operations, P2PWorkspace methods, services/adapters,
  initialization, diagnostics, permissions, Change Set/Work state, receipts,
  templates, docs, resources, tests and package members. Classify every hit as
  `remove`, `neutralize`, `external_repository_tooling` or `historical`, with a
  reason and owning follow-up task; no unclassified `git` execution path remains.
- [x] T037 [R064, R081, R084-R085, AC017, AC026, D014] Remove the `sync` CLI group;
  proposal branch lifecycle commands; Git-backed Work lifecycle commands;
  `project remote`; `change policy`; init repository/provider/remote options and
  output; agent-instruction repository-mode overrides; and doctor Git status.
  Preserve proposal decision-event commands plus neutral Work
  plan/list/status/retire/show, then update help/public-surface snapshots to
  prove exact absence without aliases or tombstones.
- [x] T038 [R076-R082, R085, AC021, AC026-AC027, D014, D018] Remove all Git-owned
  MCP definitions, registry names, routes, handlers and consent operations,
  including sync, project remote, proposal draft/branch lifecycle and Work branch
  lifecycle tools. Remove repository-mode and Git-hygiene fields from retained
  init/agent schemas and responses. Preserve retained decision/spec/Work-read
  schemas and add an exact negative catalog contract for every removed name.
- [x] T039 [R064, R080, R083, R089-R090, AC027, D014] Remove `storage/git.py`,
  sync/proposal-branch/Work-branch/proposal-draft-commit/`.gitignore` services and
  all facade imports, caches, callbacks and operation-compatibility entries.
  Extract a helper only when a direct non-Git caller/test proves neutral ownership;
  add an AST/reference guard against runtime `git` subprocess execution.
- [x] T040 [R083-R085, R089, AC027, AC029, D014] Rework retained consent audit,
  initialization, permissions, Change Set, Work planning, context packets,
  receipts, project metadata and agent integration data so writes are
  filesystem/receipt based and contain no repository mode, Git policy,
  branch/commit/push/merge or provider-permission semantics. Keep caller-supplied
  repository/issue/PR/commit/release references as inert traceability only and
  test that they never imply implementation state.
- [x] T041 [R084, R086, R090, N003, N013, AC028, D006, D014] Add source and
  installed tests proving init/doctor/retained workflows pass in a non-Git root,
  create neither `.git` nor `.gitignore`, never invoke a failing `git` sentinel
  placed first on `PATH`, and leave a pre-existing opaque `.git` sentinel tree
  byte-identical.
- [x] T042 [R085, R088-R089, AC017, AC029, D011, D014] Regenerate maintained agent
  templates, example agent files, capability/operation inventories and current
  docs without P2P-managed Git guidance or Git-native positioning. Remove Git-only
  test markers and tests; label retained vision/history documents archival or
  superseded and prove they are not current instructions.
- [x] T043 [R086-R090, N013-N015, AC027-AC030, D007, D014, D020] Add source/wheel
  boundary guards that reject Git runtime modules, commands, tools, subprocesses,
  dependencies and generated guidance. Maintain a narrow reasoned allowlist only
  for external `.github/workflows`, explicitly classified developer/release
  tooling, source clone instructions and archival history; fail unused or
  broadened exceptions and prove no coverage command enters the candidate gate.

## Phase 8 - Isolated Installed-Wheel Harness

- [x] T044 [R018-R022, R027, D005] Rewrite `scripts/test-installed.sh` and any
  small helper so the exact wheel owns environment creation and identity checks.
  Remove silent `.venv/bin/pytest` fallback and define deterministic diagnostics
  for zero/multiple/wrong-version wheels.
- [x] T045 [R019-R022, R027, N006-N008, D005] Add explicit external-CWD,
  `PYTHONPATH`, user-site, module-path, metadata-version, dependency-import and
  `pip check` assertions. Add a regression fixture matching the audited stale
  0.4.6-metadata/current-source scenario and require rejection.
- [x] T046 [R023, R026, R084, R086, N013, AC006, AC028, D006, D014] Add real installed `p2p` subprocess smoke for
  version, init, runtime status, workspace schema status, registry refresh,
  validation and representative bundled/portable/offline workflows. Parse all
  JSON envelopes instead of checking substrings alone; prepend the failing `git`
  sentinel and assert its invocation log stays empty.
- [x] T047 [R024-R025, R077, R082, AC006, AC021, AC026, D006, D018] Add a bounded real
  `p2p-mcp-server` stdio initialize/tools-list smoke with timeout, clean shutdown
  and no orphan process. Assert exact catalog invariants and absence of
  export/replacement/package/publication writes and every removed Git tool.
- [x] T048 [R026, R086, N002, N013, D005-D006, D014] Deny outbound network during the installed
  product phase and prove bundled vertical, portable schema 3, fixture resource
  and MCP catalog behavior remain available without Git. Keep dependency
  installation as a separate explicitly online phase.
- [x] T049 [R018-R027, R037, R086, R090, AC005-AC006, AC028, D005-D006, D014] Test script cleanup and
  failure injection: install failure, missing dependency, malformed CLI JSON,
  MCP timeout, attempted Git invocation and interrupted smoke all remove temporary
  environments/processes and leave repository and `.git` sentinel bytes clean.

## Phase 9 - Artifact Verification, Reproducibility And Checksums

- [x] T050 [R014-R017, R062, R074, R086-R089, D004, D014, D017] Expand
  `verify-release-artifacts.py` to scan all bounded textual wheel/sdist members
  for host paths, secrets, discarded current tokens, forbidden roots and removed
  modules/Git product surfaces. Implement typed reasoned allowlists for archival
  and external release-tooling references and fail unused entries.
- [x] T051 [R032-R034, R056-R058, R072, R086-R089, D009, D012, D014, D017] Verify exact expected
  artifact set, package metadata, console entry points, dependencies, license,
  required resources/docs/tests and absence of stale root setup, dead modules and
  Git runtime modules/tools. Reject additional wheel/sdist files in the selected
  release output directory.
- [x] T052 [R032-R034, R038, N001, D009] Add clean double-build reproducibility
  automation that reports differing archive members/modes/metadata and produces
  stable `SHA256SUMS` only after wheel and sdist are byte-identical.
- [x] T053 [R035, R038, R075, D009] Constrain and record the release build
  toolchain so candidate verification and publication use the same backend/tool
  versions. Implement the owner-approved provenance decision and distinguish
  checksums from signatures/attestations in evidence and docs.
- [x] T054 [R016-R017, R032-R038, AC004, AC008-AC009, D004, D008-D009] Add focused
  verifier tests using synthetic safe/unsafe archives: old dist files, absolute
  POSIX/Windows/UNC paths, secret markers, unused allowlist, mismatched versions,
  extra assets, non-deterministic members and valid historical exceptions.

## Phase 10 - CI And Create-Only Release Automation

- [x] T055 [R028-R029, R087, N006-N008, N015, D007, D020] Add normal pre-tag CI for pull requests,
  main and manual execution on Python 3.11 and 3.14. Keep matrix environments
  isolated and run source/public/full gates without shared mutable `dist/`.
  Document this as external source-repository automation, not runtime behavior or
  permission for the implementation agent to commit.
- [x] T056 [R028-R030, R039, R087, D007, D020] Add a reusable/manual release-candidate
  workflow for one exact commit that performs build, standard/project artifact
  checks, reproducibility, installed-wheel smoke and security gates without
  publication, then records SHA and artifact hashes.
- [x] T057 [R030-R031, R039, D007-D008] Make the tag workflow use the same exact
  candidate gate and verify tag/package/changelog/fixture/release-contract
  version equality. Document that the owner tags only a previously green
  candidate SHA.
- [x] T058 [R031-R034, AC008, D008-D009] Replace release update/`--clobber` logic
  with create-only preflight and exact-name upload of wheel, sdist and
  `SHA256SUMS`. Add a testable dry-run/fake-`gh` path proving existing
  release/asset conflicts stop before upload.
- [x] T059 [R035-R037, R039, D007-D009] Pin third-party actions to commit SHAs,
  separate least-privilege permissions, use temporary paths with failure cleanup
  and add approved provenance/deferral handling. Review workflow YAML for
  untrusted tag/input shell expansion.
- [x] T060 [R028-R039, R059-R060, R087, N015, AC007-AC009, D007-D009, D020]
  Validate workflows with static tests, an available workflow linter and local
  dry-run/fake-provider tests. Record the exact owner command for running the
  candidate workflow after an approved commit exists. Task completion does not
  require or authorize the agent to create that commit; publication remains
  blocked until the later owner-run workflow is green for the exact SHA.

## Phase 11 - Static, Dependency And Distribution Quality Gates

- [x] T061 [R063, R069, D013, D016] Add a scoped Ruff dev dependency/config and
  CI command for syntax, undefined names, unused imports, import ordering and
  selected correctness rules. Fix findings without running a broad formatter or
  unrelated style rewrite.
- [x] T062 [R070, D016] Select and configure a staged type checker for the changed
  release-contract, serialization, fixture-generator and artifact-verifier
  modules. Document the exact target list and fix errors without a blanket
  repository-wide ignore or whole-codebase typing refactor.
- [x] T063 [R071, R075, N007-N008, D016] Add resolved-runtime dependency audit
  after clean wheel installation. Define owner, advisory ID, rationale and
  expiry schema for exceptional findings; prove an unapproved or expired
  exception fails the gate.
- [x] T064 [R072, D016-D017] Add a standards-based package metadata/long-description
  check such as `twine check` for the exact wheel/sdist and keep it separate from
  project-specific member verification.
- [x] T065 [R073, N011, N014, AC019, AC030, D016] Build and review a
  requirement-to-test matrix for every changed release-critical behavior. Add
  missing positive, negative, failure-path, byte-invariance, subprocess and
  installed-artifact cases. Prove candidate scripts/workflows create or consume
  no coverage command, percentage, threshold, XML/HTML report or coverage-based
  exception.
- [x] T066 [R074, AC019, D004, D016-D017] Add deterministic secret/private-key,
  path and documentation-link checks to the maintained quality command set.
  Review every allowlist entry and prove scans cannot dump secret-bearing file
  bodies into logs.

## Phase 12 - MCP, Contract Tuple And Boundary Revalidation

- [x] T067 [R025, R076-R078, R082, R089, D014, D018] Re-run source MCP catalog/registry/handler
  contract tests and inspect diffs to prove no new project-structure apply,
  export-writing, package destination or remote publication surface and no
  WaveKit implementation dependency. Prove every removed Git tool name is absent
  from definitions, registry, handlers, dispatch, consent and generated guidance.
- [x] T068 [R041, R046, R079, AC020-AC021, D010, D018] Verify the full release
  contract tuple is identical in CLI version, workspace status, MCP schema
  status, packaged fixture bundle and convergence inventory from source and
  installed wheel.
- [x] T069 [R064-R066, R076-R090, N009-N010, N013-N015, D014, D018-D020] Run
  current-only, public-surface and runtime-import inventories to prove Git product
  behavior is absent, external source/release tooling is narrowly classified,
  deferred/superseded operations remain absent and no file outside
  `p2p-engine/` changed.

## Phase 13 - Focused And Broad Validation

- [x] T070 [R001-R017, R040-R047, R067-R068, AC001-AC004, AC010-AC012, AC018]
  Run focused regression tests for CLI JSON, vertical locks, portable packs,
  fixture generation and convergence. Record exact node/file commands and
  results in `implementation.md`.
- [x] T071 [R048-R075, R080-R090, AC013-AC019, AC023, AC026-AC030] Run focused
  docs, version, package metadata, dead/Git-surface, Ruff, staged typing,
  dependency audit, standard package, no-Git sentinel and requirement-to-test
  checks. Review outputs rather than recording command exit alone; do not run or
  record coverage.
- [x] T072 [R001-R090, AC020-AC023, AC026-AC030] Run `./scripts/test-public.sh -q` and review
  CLI/MCP/public-surface failures or deselection counts. Completion evidence:
  passing public contract suite after all generated files are current.
- [ ] T073 [R018-R039, R056-R060, R072, R086-R090, AC005-AC009, AC015, AC021-AC022, AC027-AC028] Build
  clean artifacts, run project verifier, standard metadata check, convergence
  gate, double-build comparison, checksum generation and
  `./scripts/test-installed.sh --wheel <exact-wheel>` from the verified output
  with the failing `git` sentinel enabled.
- [x] T074 [R001-R090, N001-N015, AC001-AC030] Run `./scripts/test-full.sh -q` in
  the clean current environment and validate the Python 3.11/3.14 workflow
  contract. Do not substitute smoke/public suites for this local gate. Record
  that actual commit-bound CI remains an owner prerequisite for release `GO`.
- [x] T075 [N003-N004, N009-N015, AC023, AC025, AC028, AC030] Run generated-fixture `--check`, Markdown
  link validation, secret/path scan, `git diff --check` and final `git status`.
  Treat those Git commands as read-only external source inspection. Prove no
  test/verification mutated generated source unexpectedly, `.git`, or unrelated
  repositories and no coverage artifact was created.

## Phase 14 - Evidence, Owner Review Readiness And Handoff

- [x] T076 [AC024-AC025, D019-D020] Create this feature's `implementation.md` with
  requirement/task-to-file/test traceability, tool/interpreter versions,
  local source status/diff identity, artifact filenames/hashes, fixture manifest
  hashes, workflow contract evidence, owner CI handoff command, allowlists, legal
  decision reference and vulnerability/provenance exceptions. Do not invent a
  candidate commit or CI run ID before the owner supplies one.
- [x] T077 [N011-N015, AC024-AC025, AC030, D014, D019-D020] Classify every residual item as
  blocking, explicitly deferred with owner/rationale/expiry, or closed with
  evidence. Coverage is outside classification and cannot be used as debt or
  evidence. Any known required-behavior defect, runtime Git surface, malformed
  contract, path leak, ambiguous legal metadata, failed test/supported-Python
  contract, mutable release logic or unreviewed advisory is blocking and may not
  be deferred implicitly.
- [x] T078 [R028-R039, R087, N015, AC007-AC009, AC022-AC025, D007-D009, D020]
  Produce the implementation handoff verdict. `READY_FOR_OWNER_REVIEW` requires
  every implementation acceptance criterion and exact local artifact identity;
  `NOT_READY` names failed gates. State explicitly that release `GO` does not
  exist until owner-approved commit-bound Python 3.11/3.14 CI passes.
- [ ] T079 [R001-R090, N001-N015, AC001-AC030] Mark T001-T079 complete only after
  implementation evidence is present, re-run `git diff --check`, confirm the
  agent created no branch/commit/push/tag/release/asset, and hand the owner the
  exact review, commit-bound CI and separate immutable publication commands.
