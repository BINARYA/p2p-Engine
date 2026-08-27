# Requirements - Harden P2P Engine 0.5.0 Release Candidate

## Scope

Perform the mandatory pre-release hardening pass for P2P Engine `0.5.0` after
`converge-project-structure-surfaces` and before creation or publication of the
`v0.5.0` tag and before the final build/publication of the wheel, source
distribution or GitHub Release. The feature closes the concrete defects,
product-boundary violations and release-process gaps found by the 2026-08-27
repository audit and its owner review. It does not add a new product capability.

This feature is a release blocker. Passing the existing source-tree test suite
is necessary but not sufficient: the release candidate must also prove its
machine contracts on diagnostic paths, portable persisted state, installed
entry points, packaged fixtures, distribution metadata, absence of runtime Git
coupling and immutable release automation.

## Origin And Plan Position

- Source: owner-requested deep review of `p2p-engine/` before publishing the
  P2P Engine `0.5.0` wheel.
- Audit date: 2026-08-27.
- Predecessor: `converge-project-structure-surfaces`, completed as plan step 10.
- Plan position: mandatory P2P Engine hardening step immediately after step 10
  and immediately before the unnumbered `0.5.0` wheel release gate.
- Successor: WaveKit `align-wavekit-p2p-runtime-0.5.0` may start only from the
  immutable artifact produced after this feature passes.
- Deferred feature: `merge-and-restore-project-structure` remains post-0.5.0
  and is not pulled into this work.

## Audit Baseline

The feature starts from these observed facts, which must be captured by
regression tests before or together with each fix:

- the source-tree public suite and full suite pass;
- `p2p runtime status --format json` can emit
  `P2P_CLI_INVALID_JSON_OUTPUT` when the runtime contract is missing because
  Rich wraps an intermediate JSON document;
- `p2p validate --format json` can collapse structured validation findings into
  a generic error containing serialized JSON as text;
- initialization with a bundled vertical persists the physical installation
  path in `.p2p/project/vertical.lock.yml`;
- distributed examples contain developer-specific absolute paths;
- the release workflow can overwrite existing same-version assets with
  `--clobber` and runs its supported-Python gate only after a tag is pushed;
- the local `.venv` can import source version `0.5.0` while installed metadata
  still identifies `0.4.6` and a current runtime dependency is absent;
- the installed-wheel smoke selector can pass in that stale editable
  environment and does not exercise the real console-script entry points;
- the current WaveKit transition manifest mixes engine `0.5.0`, mutation
  receipt schema 2 and handoff guidance for engine `0.4.8`;
- repository-root bootstrap and contributor files assume a local `.p2p/` that
  intentionally does not exist in the implementation repository;
- release metadata and release notes are not finalized;
- five small runtime modules are packaged without any maintained importer,
  test or documented public contract;
- the installed product still exposes Git as product behavior through sync,
  proposal-branch, Work-branch, proposal-draft-commit, remote-profile,
  `.gitignore` hygiene, diagnostics, consent-audit and generated-agent surfaces;
- those paths can invoke the host `git` executable, inspect or mutate repository
  state, commit P2P writes, push branches or derive product state from Git;
- portable-pack YAML canonicalization accepts duplicate mapping keys through
  the default loader;
- lint, dependency-vulnerability and package-metadata checks are not release
  gates;
- coverage tooling exists as an optional developer diagnostic, but a coverage
  percentage neither proves product correctness nor belongs to this release
  decision.

## In Scope

- Machine-safe CLI JSON serialization and error-path contract tests.
- Host-path-free bundled vertical locks, examples, fixtures and distributions.
- Full-archive privacy/current-surface validation with reasoned allowlists.
- A self-verifying installed-wheel test flow using isolated environments and
  actual `p2p` and `p2p-mcp-server` entry points.
- Pre-tag CI, immutable release creation, deterministic artifact selection,
  checksums and release provenance policy.
- Current `0.5.0` WaveKit-facing fixtures generated from one maintained source.
- Repository-boundary corrections in root instructions and maintained docs.
- Final changelog, license, project metadata and release-note contracts.
- Removal or explicit supported disposition of confirmed dead packaged modules.
- Reconciliation of incomplete PROP-107 implementation tracking.
- Strict duplicate-key handling at portable vertical YAML boundaries.
- Minimal mandatory static, dependency and distribution quality gates.
- Complete removal or runtime isolation of Git-specific product behavior while
  preserving ordinary external Git management of the source repository.
- Removal of Git-derived initialization, consent, permission, agent-template,
  Change Set and Work semantics that imply source-control ownership by P2P.
- Requirement-to-test traceability and explicit behavioral proof for every
  release blocker, without a coverage metric as proxy evidence.
- Focused, public, installed-wheel, full-suite and artifact validation.

## Out Of Scope

- Publishing the actual tag or GitHub Release. This feature prepares and locally
  validates the implementation; owner-run commit-bound CI proves the release
  candidate and publication remains a separate owner action.
- Changes in `wavekit/` or any repository under `projects/`.
- Importing WaveKit routes, models, roles, policies, URLs or dependencies.
- Implementing `merge-and-restore-project-structure` or renumbering it into the
  0.5.0 train.
- Implementing the superseded historical features
  `stop-domain-template-overlay-on-init`,
  `edit-project-structure-through-derived-draft` or
  `expose-project-and-section-readiness`.
- Broad refactoring of `P2PWorkspace`, `storage/filesystem.py`, vertical
  lifecycle services or CLI modules unrelated to a finding in this feature.
- The owner's external source-control workflow for developing `p2p-engine/`,
  including clone, branch, commit, review, CI, tag and release operations.
- GitHub Actions and explicitly classified developer/release scripts used only
  to inspect, test, build or publish the source repository, provided they remain
  outside installed runtime behavior.
- Adding workspace-schema migration support for 0.4.x state.
- Changing domain, structure, authority, readiness, export or replacement
  semantics except where required to remove environment-specific path data.
- Running, recording, publishing or thresholding coverage as part of this
  feature or its release verdict. Optional developer coverage diagnostics remain
  outside 10A and cannot substitute for requirement-specific tests.
- Publishing to PyPI unless the owner separately selects that channel.

## Public Surface And MCP Impact

- CLI impact: corrective and externally observable. Non-Git JSON commands keep
  their names and `p2p-cli/v1` envelope, while diagnostic/error paths become
  valid, structured and terminal-width independent. Git-owned sync,
  proposal-branch, Work-branch, remote-profile and Change Set policy commands
  are removed as a deliberate pre-0.5 clean break.
- MCP impact: corrective removal plus verification. Git-owned collaboration,
  sync, remote-profile and branch/commit tools are removed from the catalog,
  registry and handlers. No replacement mutation tool is added.
- Storage impact: schema-4 vertical locks stop persisting physical bundled
  resource paths. Stable source type, logical origin, package, coordinate and
  checksums remain available.
- Packaging impact: release verification becomes stricter and may reject files
  previously accepted in an sdist.
- Documentation impact: repository implementation instructions, installation,
  security, release, historical inventories and WaveKit handoff are corrected.
- Agent-facing behavior: repository-root instructions stop treating
  `p2p-engine/` as its own governed project-state root. Generated instructions
  for normal user projects remain runtime-owned and tested separately, but no
  longer direct agents to P2P-managed Git operations.
- MCP parity decision: no new MCP parity is required because the feature adds
  no domain workflow. Retained MCP contracts must remain byte/schema compatible
  and must be exercised through the installed entry point; the removed Git tool
  names form an explicit negative contract.

## Functional Requirements

### A. Machine-Safe CLI JSON

- R001: Every command advertised as supporting `--format json` SHALL write
  exactly one UTF-8 JSON document to stdout on success, diagnostic state,
  expected domain failure, parser failure and unexpected handled failure.
- R002: Engine-controlled JSON stdout SHALL contain no ANSI escape sequences,
  Rich markup, line wrapping, progress output, human headings or text before or
  after the JSON document.
- R003: JSON serialization SHALL be independent of terminal width, color mode,
  TTY detection, redirection and the presence or absence of a project root.
- R004: `p2p runtime status --format json` SHALL treat `missing_contract`,
  `invalid_contract`, `unsupported_contract` and `incompatible` as inspectable
  runtime-status results, preserving the command's diagnostic read semantics
  and stable exit behavior instead of returning
  `P2P_CLI_INVALID_JSON_OUTPUT`.
- R005: `p2p validate --format json` with validation errors SHALL preserve the
  complete normalized validation result, including counts, ordered findings,
  paths, messages and suggested commands, in structured envelope details; it
  SHALL NOT embed the result as an escaped JSON string.
- R006: A validation failure SHALL use the existing deterministic first
  actionable error identity and existing exit class, while successful and
  warning-only validation SHALL remain successful.
- R007: Runtime status, validation and every other direct JSON renderer SHALL
  use the shared CLI contract serializer or an equivalently proven raw stdout
  serializer; Rich rendering SHALL remain restricted to human output.
- R008: Contract tests SHALL exercise both Typer's in-process runner and the
  installed `p2p` subprocess at narrow and normal terminal widths for valid,
  missing and malformed states.

### B. Portable And Private Vertical Source Metadata

- R009: A bundled `internal` vertical source SHALL never persist the physical
  package-resource path in project state, fixtures, examples, logs or receipts.
- R010: The lock for an internal vertical SHALL retain only stable logical
  source evidence, including source type, package, logical `resolved_from`,
  release identity and checksums required by the existing lock contract.
- R011: A local source path inside the project root MAY be persisted only as a
  normalized relative POSIX path with no `..` segment.
- R012: A local source outside the project root SHALL NOT cause an absolute host
  path to enter canonical or portable project state; durable identity SHALL use
  coordinate, artifact/semantic checksum and a non-physical source descriptor.
- R013: Fresh initialization for every bundled vertical SHALL produce no Unix
  home path, macOS user path, Windows drive/UNC path or current checkout path.
- R014: Existing maintained examples SHALL be regenerated through the owning
  initialization/generation workflow, not manually patched, and SHALL contain
  the same host-independent lock semantics as a fresh installed-wheel project.
- R015: Workspace validation SHALL report a deterministic, actionable finding
  for forbidden absolute source paths in current schema-4 vertical locks. It
  SHALL not silently rewrite state during read-only validation.
- R016: The artifact verifier SHALL scan every relevant textual wheel and sdist
  member, not only `src/p2p_engine`, for checkout paths, user-home paths,
  secrets and discarded current-only tokens.
- R017: Negative-test fixtures and immutable historical documents MAY contain a
  forbidden token only through a narrow path/pattern allowlist with an inline
  reason; blanket directory exclusions are forbidden.

### C. Installed-Wheel Proof

- R018: The installed-wheel validation entry point SHALL accept one exact wheel
  path/version and SHALL create or use an isolated environment in a way that
  cannot silently fall back to the repository's editable `.venv`.
- R019: Installed-wheel commands SHALL run from a temporary working directory
  outside the source checkout with `PYTHONPATH` unset and user site packages
  disabled.
- R020: Validation SHALL assert that `p2p_engine.__file__` resolves inside the
  isolated environment and outside `src/`, the repository root and any editable
  link to the checkout.
- R021: `p2p_engine.__version__`, `importlib.metadata.version("p2p-engine")`, the
  requested wheel filename and `p2p version --format json` SHALL all equal the
  exact release version.
- R022: The isolated environment SHALL pass `python -m pip check` and import all
  declared runtime dependencies, including `keyring`, before smoke tests start.
- R023: Installed smoke SHALL invoke the real `p2p` console script for version,
  initialization, runtime status, workspace schema status, registry refresh,
  validation and representative offline vertical export/replacement/package
  reads or workflows.
- R024: Installed smoke SHALL launch the real `p2p-mcp-server` entry point and
  complete a bounded stdio initialize/list-tools exchange, proving packaged MCP
  registration without leaving a server process running.
- R025: The installed MCP catalog assertion SHALL prove that project structure
  export/replacement MCP exposure remains read-only and contains no apply,
  package-writing, destination-path or remote-publication tool.
- R026: The offline phase SHALL fail any attempted external network access and
  SHALL prove bundled resources, portable schema 3, fixture bundle and vertical
  workflows operate from the installed artifact alone.
- R027: The installed test helper SHALL fail with a clear diagnostic when given
  a stale editable environment, mismatched metadata, missing dependency,
  source-tree import or wrong wheel version.

### D. CI, Build And Immutable Release Automation

- R028: Supported-Python validation SHALL run on pull requests, on the protected
  main branch and through a manual pre-release dispatch before any release tag
  is created.
- R029: The supported matrix SHALL include the minimum Python `3.11` and current
  target Python `3.14`; each job SHALL use an independent clean environment.
- R030: Release automation SHALL re-run or consume the same versioned gate for
  the exact tagged commit and SHALL refuse a tag that does not match package,
  runtime, fixture and changelog versions.
- R031: A GitHub Release or asset that already exists for the same version SHALL
  cause a hard failure. Release automation SHALL NOT use `--clobber`, update an
  existing release or silently reuse a published version.
- R032: Build output SHALL be created in a clean isolated directory and SHALL
  contain exactly one expected wheel and one expected sdist for the selected
  version before checksums are generated.
- R033: Upload commands SHALL name the exact wheel, sdist and checksum files;
  wildcard upload of a potentially dirty local `dist/` SHALL not be part of the
  maintained release procedure.
- R034: Release automation SHALL generate a deterministic `SHA256SUMS` covering
  the exact wheel and sdist and SHALL publish it with those artifacts.
- R035: The project SHALL make and document an explicit provenance decision:
  publish platform-supported build provenance for the exact artifacts when the
  repository permissions support it, or record a time-bounded owner-approved
  deferral without representing checksums as signatures.
- R036: Third-party GitHub Actions SHALL be pinned to immutable commit SHAs with
  readable version comments, and workflow permissions SHALL be least-privilege
  per job.
- R037: Temporary build/install environments SHALL use system temporary
  directories or ignored paths and SHALL be cleaned on success and failure;
  `.release-wheel-venv` SHALL not become repository state.
- R038: Two clean builds from the same commit and pinned release toolchain SHALL
  produce byte-identical wheel and sdist artifacts, or the release SHALL be
  blocked with the non-deterministic members identified.
- R039: Release automation SHALL not create the GitHub Release until source,
  public-contract, full, artifact, installed-wheel, metadata, vulnerability and
  reproducibility checks have all passed.

### E. WaveKit-Facing Fixture Coherence

- R040: Current WaveKit-facing fixtures SHALL be produced by one maintained,
  deterministic generator using the current engine contracts; manual hash or
  version editing SHALL be rejected by drift tests.
- R041: The current transition manifest, generated payloads, packaged
  `wavekit-cli-fixtures-v1.json`, release-contract tuple and handoff document
  SHALL all identify engine `0.5.0` and mutation receipt schema 3.
- R042: Current install/adopt/migrate fixtures SHALL be regenerated from current
  services/CLI semantics and SHALL preserve the documented CLI envelope,
  transition impact/plan contracts, idempotency and receipt expectations.
- R043: `legacy-0.4.7-characterization.json` and any other intentionally retained
  legacy fixture SHALL be explicitly named and tested as historical input; it
  SHALL not advertise itself as a current `0.5.0` output.
- R044: Fixture manifests SHALL contain deterministic SHA-256 hashes for every
  generated member and SHALL reject missing, extra, manually changed or
  unhashed members.
- R045: Generated fixtures SHALL be bounded, path-free, token-free, secret-free
  and independent from the local checkout and current clock except for fixed
  canonical fixture timestamps.
- R046: The packaged fixture bundle SHALL be readable through
  `importlib.resources` from the installed wheel and SHALL expose the same
  complete contract tuple reported by runtime version/status surfaces.
- R047: PROP-107 T015-T018 SHALL be completed with evidence or explicitly
  superseded by named tasks and implementation evidence from this feature; they
  SHALL not remain ambiguously unchecked at release time.

### F. Repository Boundary And Maintained Documentation

- R048: The implementation repository SHALL not ship a generated root
  `P2P-SETUP.md` that claims `.p2p/project/runtime.yml` exists locally or
  requires a pre-0.5 runtime.
- R049: Root `AGENTS.md` and `CLAUDE.md` SHALL be repository-specific
  implementation instructions, or SHALL clearly inherit such instructions,
  without claiming that `p2p-engine/` contains canonical project state.
- R050: Contributor and README checks SHALL use implementation-repository
  commands. Optional governance commands SHALL require an explicitly supplied
  separate project-state root and SHALL not assume that sibling repository is
  present in a normal public clone.
- R051: `README.md`, `CONTRIBUTING.md`, `specs/README.md` and steering guidance
  SHALL consistently state that implementation specs live under `specs/` and
  canonical P2P Engine project state lives outside this implementation repo.
- R052: Installation and security docs SHALL describe the `0.5.0` GitHub Release
  wheel as the supported transitional distribution channel and SHALL remove
  contradictory claims that current installation is source-only.
- R053: Historical architecture/CLI inventory documents SHALL either reflect
  current surfaces or carry an unambiguous archival scope; a document SHALL not
  simultaneously call a command removed and list it as current.
- R054: `ROADMAP.md` and maintained release documentation SHALL represent the
  completed 0.5.0 authority/structure/registry work, this hardening gate, the
  WaveKit handoff and the explicit post-0.5 merge/restore deferral.
- R055: Documentation links and copy-pasteable commands SHALL be checked from a
  clean public checkout model without relying on private absolute paths.

### G. Release Metadata And Legal Identity

- R056: Before publication, the owner SHALL explicitly select and record the
  SPDX license expression, including the choice between `GPL-3.0-only` and
  `GPL-3.0-or-later`; implementation SHALL not infer that legal choice solely
  from the generic GPL text.
- R057: `pyproject.toml`, wheel METADATA, sdist PKG-INFO and README SHALL agree on
  project name, version, Python requirement, SPDX license expression, license
  file, approved author/maintainer identity and canonical project/source/issue
  URLs.
- R058: Package classifiers SHALL describe supported Python versions,
  implementation and development status without using deprecated license
  classifiers that conflict with PEP 639 metadata.
- R059: `CHANGELOG.md` SHALL replace `0.5.0 - Unreleased` with the actual release
  date before the tag gate and SHALL summarize breaking clean-break,
  recreation, removed compatibility and new contract surfaces.
- R060: Generated release notes SHALL derive their substantive change summary
  from the `0.5.0` changelog section and SHALL include installation command,
  supported Python range, clean-break warning, artifact names, checksums and
  provenance statement.

### H. Obsolete Runtime And Product-Boundary Disposition

- R061: `core/project.py`, `core/task.py`, `core/plan.py`,
  `exporters/markdown.py` and `exporters/openspec.py` SHALL be removed from the
  runtime package unless inventory discovers a maintained importer or public
  contract; any exception SHALL add an explicit supported API, tests and docs.
- R062: Release artifact tests SHALL assert that modules classified as removed
  are absent from the wheel and SHALL prevent accidental reintroduction without
  a new feature decision.
- R063: A repeatable static/reference inventory SHALL classify zero-inbound
  runtime modules, unused imports and orphaned resources before release; false
  positives such as entry points and resource packages SHALL be reasoned.
- R064: Git-specific product surfaces SHALL be removed before `0.5.0`. They SHALL
  NOT be retained as transitional commands, compatibility aliases, hidden
  handlers or optional runtime paths. Their removal is an explicit owner-approved
  clean break, not dead-code inference.
- R065: Incomplete task files and historical inventories SHALL be reconciled by
  evidence, explicit supersession or clear deferral; completed work SHALL not be
  marked by assumption.
- R066: The three explicitly superseded historical features and deferred
  merge/restore SHALL remain non-executable and SHALL not gain new CLI/MCP
  surfaces during cleanup.

### I. Parser, Static, Dependency And Distribution Quality Gates

- R067: Portable vertical YAML entries SHALL use the existing unique-key loader
  contract before canonicalization; duplicate mapping keys in manifests,
  rubrics, sections or other YAML members SHALL fail deterministically.
- R068: Duplicate-key errors SHALL identify the offending package member with a
  stable `P2P_VERTICAL_INVALID_PACK`-family code and SHALL not disclose unrelated
  file content or mutate the source/output artifact.
- R069: A minimally scoped Ruff configuration SHALL gate syntax errors, undefined
  names, unused imports, import ordering and selected correctness rules without
  triggering unrelated repository-wide formatting churn.
- R070: Static typing SHALL gain a staged, documented gate over release-critical
  contract, serialization, artifact-verification and fixture-generation modules;
  a whole-repository typing rewrite is not required by this feature.
- R071: The exact resolved runtime dependency set installed for the release
  candidate SHALL be checked with `pip check` and a maintained vulnerability
  auditor. Unfixed findings SHALL block release unless an owner-approved,
  advisory-specific, expiring exception is documented.
- R072: Wheel and sdist metadata/long-description validation SHALL run through a
  standard package checker in addition to the project-specific artifact
  verifier.
- R073: Coverage percentage SHALL NOT be an input, artifact, acceptance
  criterion or release verdict for this feature. Test adequacy SHALL instead be
  established by requirement-to-test traceability and passing positive,
  negative, failure-path, installed-artifact and regression tests for each
  changed release-critical behavior.
- R074: Secret, private-key, credential, local-path and relative-document-link
  scans SHALL be deterministic release checks with reviewed narrow allowlists.
- R075: Release build/test tool versions SHALL be captured in CI evidence and
  constrained sufficiently to reproduce the candidate without silently changing
  build backend behavior between verification and publication.

### J. MCP And Product Boundary Preservation

- R076: No MCP tool added by this feature SHALL write project structure, create
  export drafts/packages, choose destination paths, publish releases or perform
  remote moderation/publication.
- R077: Installed MCP catalog and handler tests SHALL remain semantically equal
  to source-tree contracts and SHALL prove retained consent/authority rules are
  unchanged after Git-owned consent operations and commit/push audit coupling are
  removed.
- R078: P2P Engine source, tests, fixtures and release scripts SHALL not import
  WaveKit implementation code or require a WaveKit service/network connection.
- R079: The complete 0.5.0 release-contract tuple SHALL remain identical across
  `p2p version`, workspace status, MCP schema status, packaged fixture bundle
  and convergence inventory after hardening.

### K. External Source-Control Boundary

- R080: Source control SHALL be external to P2P Engine product behavior. Code
  under `src/p2p_engine/` SHALL NOT discover, initialize, inspect, branch,
  commit, fetch, pull, push, merge, reset, clean, tag or otherwise mutate a Git
  repository, directly or through an adapter.
- R081: The CLI SHALL remove `p2p sync`; proposal branch lifecycle commands
  `branch`, branch-backed `status`, `publish`, `request-review`, `accept-branch`,
  `reject-branch`, `merge`, `finalize`, `cleanup`, `retire-branch` and `scan`;
  Git-backed Work commands `scan`, `branch`, `submit`, `review`, `publish`,
  `request-review`, `accept`, `finalize` and `cleanup`; `p2p project remote`;
  Git-specific `p2p change policy`; and Git provider/remote/repository-mode
  options and output from `p2p init` and `p2p agent instructions refresh`.
  Proposal decision commands and neutral Work planning/read commands SHALL
  remain available.
- R082: MCP SHALL remove `p2p_sync_status`, `p2p_sync_fetch`, `p2p_sync_pull`,
  `p2p_sync_push`, `p2p_project_remote_show`,
  `p2p_project_remote_configure`, `p2p_proposal_draft_commit`,
  `p2p_proposal_branch`, `p2p_proposal_branch_status`,
  `p2p_proposal_publish`, `p2p_proposal_request_review`,
  `p2p_proposal_accept_branch`, `p2p_proposal_reject_branch`,
  `p2p_proposal_merge`, `p2p_proposal_finalize`, `p2p_proposal_cleanup`,
  `p2p_proposal_branch_scan`, `p2p_work_branch`, `p2p_work_submit`,
  `p2p_work_review`, `p2p_work_publish`, `p2p_work_request_review`,
  `p2p_work_accept`, `p2p_work_finalize` and `p2p_work_cleanup` from definitions,
  registry, routing, handlers, consent catalogs and generated instructions.
  Retained init/agent tools SHALL lose repository-mode and Git-hygiene fields.
  Decision-event tools and neutral Work/spec tools SHALL remain available.
- R083: `storage/git.py`, sync/proposal-branch/Work-branch/draft-commit and
  `.gitignore`-hygiene services, Git-backed consent-audit helpers and all
  `P2PWorkspace` wiring to them SHALL be removed unless a reviewed inventory
  proves a non-Git responsibility that is first extracted behind a neutral name
  and contract. Runtime code SHALL contain no subprocess call to `git`.
- R084: Initialization and diagnostics SHALL succeed in a normal non-Git
  directory. They SHALL NOT create or edit `.gitignore`, create `.git`, resolve a
  Git remote, report branch/HEAD/cleanliness or require a repository mode.
- R085: Permissions, Change Sets, Work records, context packets, receipts,
  project metadata and agent templates SHALL describe P2P authority and logical
  project state without branch, commit, push, merge, provider-permission or
  Git-policy semantics. Repository name, issue/pull-request URL, commit SHA and
  release identifier MAY remain only as caller-supplied opaque traceability
  metadata; P2P SHALL NOT resolve or use them to infer implementation status.
- R086: The wheel SHALL declare no Git runtime dependency and installed smoke
  SHALL run with a failing sentinel `git` executable placed first on `PATH`.
  Every retained representative CLI/MCP/offline workflow SHALL pass without
  invoking that sentinel.
- R087: Git and GitHub MAY be used by the owner outside P2P Engine to manage this
  source repository and by `.github/workflows` or explicitly classified
  developer/release scripts to inspect an approved source commit, run source
  checks and publish artifacts. Such use SHALL not be imported by runtime
  modules, exposed as a `p2p` command, required after wheel installation or
  represented as P2P project authority.
- R088: Maintained product documentation, generated agent files, CLI/MCP
  inventories, examples and packaged resources SHALL present filesystem-backed
  portable project state, not Git-native or P2P-managed Git behavior. Historical
  vision/spec documents MAY retain Git discussion only with explicit archival or
  superseded context and SHALL not be indexed as current instructions.
- R089: Source, public-surface and wheel guards SHALL fail if a removed Git
  command/tool/module, Git subprocess invocation, Git-owned consent operation or
  generated Git workflow guidance reappears. There SHALL be no tombstone command
  or compatibility stub that keeps the removed operation executable.
- R090: Running P2P inside a directory externally versioned by Git SHALL be
  supported, but P2P SHALL treat `.git` as opaque and leave its HEAD, index,
  configuration, refs and hooks untouched. Existing external Git versioning of
  changed `.p2p/` files remains the user's responsibility.

## Non-Functional Requirements

- N001: Every release artifact and generated fixture SHALL be deterministic for
  the same source commit, toolchain and canonical inputs.
- N002: All offline smoke phases SHALL remain fully functional with outbound
  network access denied after dependencies are installed.
- N003: Read-only status, validation, verification and catalog operations SHALL
  not mutate project state, examples, fixtures or the source checkout.
- N004: No secret, credential, access token, absolute checkout path or mutable
  provider state SHALL enter committed or distributed artifacts.
- N005: The implementation SHALL reuse the shared CLI envelope, YAML loader,
  release contracts, fixture resources and existing test-tier scripts rather
  than adding parallel serializers or package models.
- N006: Source-tree and installed-wheel behavior SHALL match on Python 3.11 and
  3.14 for every contract touched by this feature.
- N007: Failures SHALL be deterministic, actionable and identify the exact gate,
  member, command or contract that failed without leaking private content.
- N008: Release validation SHALL be isolated from the developer's editable
  environment, user site packages, cached project state and pre-existing
  `dist/` contents.
- N009: Changes SHALL remain limited to `p2p-engine/`; no file in `wavekit/` or
  `projects/*` may be modified.
- N010: The hardening implementation SHALL avoid broad architectural refactors
  and preserve domain behavior not explicitly corrected by a requirement.
- N011: Each task SHALL have traceable source, test, documentation or observed
  command evidence before it is checked.
- N012: Any known defect against a required `0.5.0` behavior, unresolved P0/P1
  audit finding, failed required test, ambiguous legal metadata, failed
  supported-Python job or unreviewed security exception SHALL keep the release
  gate closed. Severity changes triage priority, not permission to release a
  product that fails its required contract; only genuine out-of-scope
  enhancements or non-functional debt may be explicitly deferred.
- N013: Installed P2P Engine SHALL have no functional, packaging or executable
  dependency on Git and SHALL behave the same inside and outside an externally
  versioned directory, except for ordinary filesystem changes requested by the
  user.
- N014: Release confidence SHALL come from explicit contract and behavior tests,
  not a coverage percentage. A passing percentage SHALL never waive a failed or
  missing required test, and a low percentage alone SHALL never define failure.
- N015: The implementation agent SHALL perform no Git mutation or publication:
  no commit, branch, push, tag, release creation or asset upload. Read-only source
  inspection is allowed; owner-approved source-control and CI actions occur only
  after the implementation handoff.

## Edge Cases And Required Errors

- A missing runtime contract produces a long suggested command at a 40-column
  terminal.
- Validation returns multiple errors, warnings and suggested commands whose
  messages exceed terminal width.
- stdout is redirected, colors are forced, `NO_COLOR` is set or stderr is
  captured separately.
- A JSON command raises a Click parser error before its handler starts.
- An internal resource is resolved from an editable checkout, normal wheel,
  zip import or differently located virtual environment.
- A local vertical source lives inside the project, outside the project, on a
  Windows drive or behind a symlink.
- A malicious or stale example contains `/home/...`, `/Users/...`, a Windows
  drive path, UNC path, token-like value or repository checkout name.
- A historical negative fixture legitimately contains a forbidden token but is
  missing an allowlist reason.
- The installed test is launched from the repository root with an editable
  `.venv` already active.
- The wheel filename says `0.5.0` while METADATA, module version or CLI version
  differs.
- A declared dependency is absent but `pip check` examines stale older package
  metadata.
- The MCP server starts but hangs, emits non-protocol stdout or leaves a child
  process after the handshake timeout.
- Offline tests accidentally resolve a remote registry or dependency endpoint.
- `dist/` contains wheels and sdists from prior versions.
- A release workflow is retried after a GitHub Release was partially or fully
  created.
- The same tag points at a different commit or a release asset with the same
  name already exists.
- Wheel and sdist are individually valid but were built from different commits
  or toolchains.
- A second build differs only in archive timestamp, order, mode or generated
  metadata.
- Fixture engine version is updated without regenerating member hashes and
  payloads.
- A current fixture claims receipt schema 2 while runtime reports schema 3.
- An intentionally historical fixture is accidentally consumed as current.
- The legal license choice is unknown when the build otherwise passes.
- A supposedly dead module is loaded dynamically through an entry point or
  importlib resource lookup.
- A portable pack contains duplicate YAML keys at the root or nested mapping.
- Vulnerability scanning is unavailable, times out or reports an advisory with
  no fixed release.
- Every broad suite passes but one corrected requirement has no direct positive,
  negative or failure-path regression test; the gate remains closed until that
  behavioral evidence exists.
- A coverage report is available from optional developer tooling; the release
  gate neither runs nor consumes it.
- `git` is absent, inaccessible or replaced by a failing sentinel while installed
  CLI and MCP smoke tests run.
- P2P runs inside a directory containing a real or sentinel `.git` tree; runtime
  operations leave Git control files byte-identical.
- A removed Git command or MCP tool remains reachable through an alias, hidden
  registry entry, generated instruction or consent operation catalog.
- A caller records an opaque commit SHA or pull-request URL as implementation
  evidence; P2P stores/displays the value without invoking Git or inferring that
  implementation is complete.

## Acceptance Criteria

- AC001: Missing/malformed runtime status and failing validation produce one
  parseable `p2p-cli/v1` document with preserved structured diagnostics at
  narrow and normal terminal widths.
- AC002: Every maintained JSON command passes success/error envelope inventory
  tests with no Rich/ANSI contamination.
- AC003: Fresh projects initialized from source and installed wheel with every
  bundled vertical contain no absolute or checkout-specific source path.
- AC004: Maintained examples and both distribution archives pass full-text
  privacy/current-surface scans with only reasoned historical exceptions.
- AC005: `scripts/test-installed.sh` or its approved replacement rejects the
  stale editable-environment scenario observed by the audit.
- AC006: An isolated wheel environment proves matching version metadata,
  complete dependencies, actual CLI entry point, actual MCP handshake, packaged
  resources and offline vertical workflows.
- AC007: Local workflow contract tests prove that Python 3.11 and 3.14 pre-tag
  jobs enforce the complete candidate gate for one exact owner-approved commit.
  Running those jobs requires the later owner-only gate; it is not an
  implementation-agent task or permission to create a commit.
- AC008: Release automation cannot overwrite an existing version or asset and
  uploads only exact, verified artifact names plus `SHA256SUMS`.
- AC009: Two clean builds from the pinned release toolchain are byte-identical
  and the artifact verifier identifies no forbidden or missing member.
- AC010: Current WaveKit transition fixtures, packaged fixture bundle, handoff
  and runtime contract tuple all agree on engine 0.5.0 and receipt schema 3.
- AC011: Fixture drift, extra/missing members, changed hashes, local paths and
  secrets are rejected automatically.
- AC012: PROP-107 T015-T018 have traceable completion or explicit supersession
  evidence consistent with the current fixture/docs implementation.
- AC013: Root setup, agent and contributor documentation no longer treats
  `p2p-engine/` as a governed `.p2p` project-state repository.
- AC014: Installation, security, roadmap, CLI inventory and release docs are
  mutually consistent and contain no current source-only or removed-command
  contradiction.
- AC015: Owner-approved SPDX/legal metadata is present and identical in
  pyproject, wheel, sdist and README; changelog has a real release date.
- AC016: Confirmed dead modules are absent from source package and wheel, with no
  broken importer, entry point, docs link or test.
- AC017: Git/sync/branch/commit product surfaces are absent from runtime, CLI,
  MCP, generated agent guidance and release artifacts, while proposal decisions
  and neutral Work planning/read surfaces remain operational.
- AC018: Duplicate YAML keys are rejected before portable-pack canonicalization
  from both directory and archive/installed-wheel paths.
- AC019: Ruff, staged typing, dependency audit, package metadata validation and
  secret/path/link scans complete with reviewed output; every changed
  release-critical behavior has requirement-linked tests.
- AC020: Retained source CLI/MCP/public contracts, convergence inventory and
  complete release tuple remain stable except for explicitly corrected
  diagnostic envelopes, path-free lock representation and the approved removal
  of Git-owned product surfaces.
- AC021: MCP contains no new project-structure write/export/publication surface
  and its installed stdio process terminates cleanly after bounded tests.
- AC022: Focused regression tests, public tests, full tests, artifact verification
  and installed-wheel tests pass from an isolated candidate/build context with no
  stale outputs or editable-install leakage. A source commit is not required for
  the implementation agent's local run.
- AC023: `git diff --check`, documentation-link validation and generated-resource
  drift checks pass.
- AC024: The implementation note records commands, versions, artifact hashes,
  local source identity, supported-Python workflow contract results, allowlists,
  security exceptions and any explicitly deferred non-blocking debt. Owner-run
  CI later adds the exact approved commit and workflow-run identity.
- AC025: Completing implementation creates no Git commit/branch/push/tag, release
  asset or WaveKit change. The owner receives `READY_FOR_OWNER_REVIEW` or
  `NOT_READY`; only owner-run CI for an approved commit can later issue the
  release-candidate `GO` used for publication.
- AC026: The exact removed CLI and MCP inventories in R081-R082 are unreachable;
  help/catalog snapshots contain no aliases or tombstones, while retained
  proposal-decision and Work planning/read operations pass regression tests.
- AC027: Runtime source and wheel contain no Git adapter, Git-owned service,
  `git` subprocess path or Git-backed consent operation. Explicitly allowlisted
  repository/release tooling remains outside `src/p2p_engine/` and installed
  entry points.
- AC028: Fresh init and representative source/wheel workflows pass in a non-Git
  directory without creating `.git` or `.gitignore`; a failing `git` sentinel is
  never invoked and an existing `.git` sentinel tree remains byte-identical.
- AC029: Current docs, templates, permissions, Change Set/Work state and agent
  capability inventories contain no P2P-managed Git semantics. Opaque external
  implementation references remain inert traceability only.
- AC030: No coverage command, threshold, percentage or report participates in
  10A automation, evidence or verdict; direct requirement-to-test traceability
  is complete for all release blockers.

## Owner-Only Post-Implementation Release Gate

This gate is mandatory before publication but is not a 10A implementation task
and grants no Git authority to the implementation agent:

1. The owner reviews the `READY_FOR_OWNER_REVIEW` diff and local evidence.
2. The owner creates the 10A source commit through the repository's external
   Git workflow while `0.5.0` remains `Unreleased`.
3. In the later release step, the owner records the actual release date,
   finalizes the maintained notes and commits that finalization.
4. The owner runs the release-candidate workflow for that exact SHA; Python 3.11
   and 3.14, all behavioral/security/package gates and artifact identity must
   pass with no unresolved required-behavior defect.
5. Only that green run may issue release `GO` and retain one exact wheel, sdist
   and `SHA256SUMS` set bound to the approved SHA.
6. The owner creates `v0.5.0`; the tag workflow rechecks and attests that same
   artifact set, then starts create-only publication.

Failure or absence of any step leaves publication blocked. It does not reopen
Git as a P2P Engine runtime capability.
