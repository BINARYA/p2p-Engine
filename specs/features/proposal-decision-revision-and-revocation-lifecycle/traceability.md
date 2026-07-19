# Live Traceability - Proposal Decision Revision And Revocation Lifecycle

## Rule

This matrix records the implementation evidence available at the engine gate.
An inclusive range is used only when every identifier in that range is covered
by the same implementation surface and focused evidence. Release, repository
migration and derived alignment remain separate owner-confirmed gates.

## Functional Requirements

| Requirements | Design | Tasks | Direct implementation and evidence | Status |
| --- | --- | --- | --- | --- |
| R-F1-001..005 | D001-D006; Ledger Contract | S1-T001..005 | `core/proposal_decision_events.py`; `ProposalDecisionLedgerCodec`; strict round-trip, duplicate-key and future-contract tests in `test_proposal_decision_ledger.py` | complete |
| R-F1-006..010 | D007-D008; Identity And Fingerprints | S1-T006..012 | versioned proposal/decision/event payloads, predecessor validation and deterministic identities; tamper, normalization, date and identity tests | complete |
| R-F1-011..018 | D002-D005; Projection Rendering | S1-T013..018, S3-T004..005 | centralized proposal/decision renderers, schema-v3 creation and artifact ownership; projection and fresh-v3 tests | complete |
| R-F1-019..022 | D008, D021; Binding And Limits | S1-T015..019, S6-T002, S6-T019 | lifecycle binding diagnostics, semantic-update gate, bounded parser and legacy truncation; corruption, oversize and divergence tests | complete |
| R-F2-001..007 | D009, D016-D017; Lifecycle And Authority | S2-T001..004, S2-T008..017 | exhaustive state/event matrix and lifecycle reducer in `lifecycle_authority.py`; `test_complete_transition_matrix` | complete |
| R-F2-008..014 | D009; Reconsideration, Reinstatement And Lineage | S2-T005..007, S4-T021..022 | linked-proposal reconsideration guidance, typed lineage and explicit reinstatement/legacy-resolution paths; lifecycle and owner-resolution tests | complete |
| R-F2-015..022 | D017, D021; Authority Intervals And Update Policy | S2-T003..017, S6-T002, S6-T019..020 | derived intervals, active/ever-active state, proposal binding and in-place rewrite prevention; revoke/reinstate consumer tests | complete |
| R-F3-001..008 | D010-D012; Preview And Apply | S4-T001..011 | one typed request, read-only preview, owner/executor authority and complete token binding in `ProposalDecisionService`; preview/apply tests | complete |
| R-F3-009..016 | D007, D010-D012; Atomicity, Retry And Recovery | S4-T008..015 | one atomic writer call, exact retry, stale/replay distinction, cross-day retry and process lock wait; failure injection and spawn-process tests | complete |
| R-F3-017..023 | D020; Compatibility And Repair | S4-T016..025 | old writer removed, compatibility commands two-phase, projection/ledger repair and atomic readiness override; CLI, branch and repair tests | complete |
| R-F4-001..007 | D013; Impact Model | S5-T001..011 | immutable complete snapshot, one-pass indexed traversal, deterministic identity and bounded page; impact completeness/staleness tests | complete |
| R-F4-008..014 | D014; Remediation Actions | S5-T012..018 | dependent byte invariance and stable next-action candidates for revoke/reinstate; integration and 100-chain scale tests | complete |
| R-F5-001..008 | D001, D005-D006, D015-D016; Schema V3 Migration | S3-T001..009 | schema v3, adjacent v2-to-v3 handler, fresh empty ledger and aligned initial-event migration; migration matrix tests | complete |
| R-F5-009..016 | D019-D020; Preservation And Candidate Validation | S3-T010..015, S4-T018..022 | loss-aware unknown legacy, stable target ownership, schema-last plan and owner resolution; deterministic dry-run and curation tests | complete |
| R-F5-017..023 | D001, D015-D016; Recovery And Compatibility | S3-T016..024 | rollback/resume/no-op, v0/v1 composition, v2 readable/v3 write gate and validation diagnostics; migration/recovery suites | complete |
| R-F5-024..031 | D022-D026; Pre-Migration Owner Attestation | H-T001..014 | closed input normalization, `MigrationAttestationTemplate`, `WorkspaceCompatibilityService.proposal_decision_attestation_template`, attested v2-to-v3 event construction, exact source/owner checks and CLI template; 51 focused migration tests plus decision-concurrency regressions | complete in source; patch release D2 pending |
| R-F6-001..007 | D016-D017; Core Consumer Convergence | S6-T001..010 | shared lifecycle map, additive proposal/registry fields and head-bound Change creation; corruption and Change binding tests | complete |
| R-F6-008..014 | D012, D017; Work, Spec And Project Consumers | S6-T009..018 | inactive-source diagnostics, Work/spec preconditions, active project/vertical evidence and lifecycle-bound freshness; consumer integration tests | complete |
| R-F6-015..019 | D014, D017, D021; Exports And Corruption | S6-T016..023 | lineage quarantine, historical export/publication inputs and no projection-authority fallback; source audit plus revoke/reinstate tests | complete |
| R-F7-001..006 | D017; Ledger Decision Context | S7-T001..007 | schema-aware source catalog, event records, intervals and typed relations in `decision_context_ledger.py`; catalog/extraction tests | complete |
| R-F7-007..012 | D007-D009; Retrieval And Freshness | S7-T008..017 | active/historical ranking, head/lineage/fingerprint fields, semantic invalidation and 100-proposal determinism; retrieval/context tests | complete |
| R-F8-001..006 | D010, D018; CLI Contract | S8-T001..009, S8-T012..018 | status/history/impact, generic preview/apply and three repair modes; `test_proposal_decision_cli.py` and full CLI suite | complete |
| R-F8-007..010 | D010-D011; MCP Contract | S9-T001..009 | shared serialization, token-bound consent, current-owner recheck and exact consumed-result binding; `test_proposal_decision_mcp.py` and MCP suite | complete |
| R-F8-011..015 | Diagnostics And Documentation | S9-T010..017 | P2P360..P2P389 registry, CLI recovery rendering, validation, docs, source templates, generated adapter refresh and hygiene tests | complete; residual single-adapter drift classification defect recorded |
| R-F8-016..017 | D018; Compatibility Commands | S8-T010..018, S9-T006 | old CLI/MCP names return bound preview or require matching apply; readiness override stays atomic; compatibility tests | complete |
| R-F9-001..004 | Release And Repository Dogfooding | D-T001..009 | owner-authorized `v0.4.0` release at `ae1324c`; GitHub run `29640890775`, published wheel/sdist hashes, isolated install and source/published parity evidence | complete |
| R-F9-005..009 | Repository Migration | H-T001..014, D2-T001..006, M-T001..016 | attestation hardening and `0.4.1` preflight are complete; exact-commit release verification, deployment and this repository's schema-v2 migration remain pending | pending D2 release and owner migration gates |
| R-F9-010..014 | Derived Alignment | A-T001..014 | consumer implementations are ready; registries/projections/context/publication have not been rebuilt against a migrated repository | pending migration and alignment gates |

## Cross-Cutting Requirements

| Requirements | Tasks | Direct evidence | Status |
| --- | --- | --- | --- |
| N001..005 | S1, S4, S5 | typed immutable models, centralized policy, versioned fingerprints, read-only preview and bounded normalization tests | complete |
| N006..010 | S2, S3, S7 | explicit schema compatibility, no Git/mtime inference, recovery journal and 100-proposal deterministic fixtures | complete |
| N011..015 | S4, S6, S8, S9 | byte invariance, additive JSON, two-phase public writes and dependent-state preservation tests | complete |
| N016..020 | G-T006..012, D-T002..008 | compile/version checks, Python 3.11/3.14 public/full suites, verified published wheel/sdist and installed-artifact smoke | complete at release gate |
| E001..005 | S1, S3 | malformed/duplicate/future ledger and unknown-legacy migration tests | complete |
| E006..010 | S1, S2 | chain, transition, date, authority and binding failure tests | complete |
| E011..015 | S2, S4, S5 | lineage, stale impact, replay, concurrent head and failure-injection tests | complete |
| E016..020 | S3, S4 | migration recovery, unknown legacy and reinstatement mismatch tests | complete |
| E021..025 | S5, S6 | malformed dependency, projection corruption and complete ledger-repair rejection matrix | complete |
| E026..030 | S8, S9, G | compatibility exit behavior, exact consent binding, future contract, strict YAML and package verification | complete at local engine gate |
| AC001..005 | S1, S2 | fresh ledger, integrity, exhaustive transitions, lifecycle semantics and reconsideration command tests | complete |
| AC006..010 | S2, S4 | binding, owner authority, atomicity, exact retry and separate-process concurrency tests | complete |
| AC011..015 | S3, S5 | complete impact, bounded rendering, dependent invariance and deterministic migration planning | complete |
| AC016..020 | S3, S4, S6 | migration classification, no-op/recovery, repairs and consumer convergence tests | complete |
| AC021..025 | S7, S8, S9 | retrieval goldens, CLI/MCP contract tests, diagnostics and 100-proposal/100-chain fixtures | complete |
| AC026..028 | G, D | public `259 passed`; full Python 3.11 `1213 passed, 1 skipped`; full Python 3.14 `1214 passed`; verified published artifacts and installed-package smoke | complete |
| AC029..030 | D, M, A, F | owner-authorized runtime deployment is complete; repository migration and final derived-state comparison remain separate gates | partial; M/A/F pending |
| AC031..034 | H-T010..014, D2-T001..006 | exact/missing/stale attestation, conditional acceptance, unsupported lineage, no-write template, CLI, lock-time source drift and atomic apply tests; Python 3.14 `1234 passed`, Python 3.11 `1233 passed, 1 skipped`, verified preflight wheel/sdist and isolated template smoke | complete in source; exact-commit release and installed parity pending D2 |

## Slice Evidence

| Slice | Status | Evidence |
| --- | --- | --- |
| P | complete | baseline and regressions complete; `CHANGE-070` transitioned through governed commands |
| S1 | complete | ledger/codec/fingerprint/projection tests |
| S2 | complete | exhaustive transition, authority, legacy and scale tests |
| S3 | complete | schema/migration/rollback/resume/compatibility tests |
| S4 | complete | preview/apply/atomicity/retry/concurrency/repair tests |
| S5 | complete | impact/remediation/invariance/scale tests |
| S6 | complete | proposal/registry/Change/Work/spec/project/export consumer tests and source audit |
| S7 | complete | ledger context, retrieval, topology, freshness and scale tests |
| S8 | complete | CLI and compatibility contract tests |
| S9 | complete | MCP/consent/diagnostics/docs/template tests and runtime-0.4.0 generated refresh; residual single-adapter drift classification defect recorded |
| G | complete | technical checks, governed spec refresh and `CHANGE-070` lifecycle update complete |
| D | complete | `v0.4.0` published and verified from exact tag `ae1324c` |
| H | complete | source-bound owner attestation template/input/planner flow and deterministic decision race handling; 91 automatic repository attestations and 7 manual-review cases identified read-only |
| D2 | in progress | `0.4.1` metadata, pre-commit Python 3.11/3.14 matrix, package verification, installed smoke and diff review complete; exact-commit rerun, authorization, publication and installation pending |
| M | pending | repository workspace remains schema v2 |
| A | pending | no post-migration derived rebuild |
| F | pending | depends on D, M and A |
