# Traceability - Multilingual Human Project Publication And Editorial Curation

This matrix is implementation state, not a final-gate reconstruction exercise.
Update the affected rows after every slice with exact source paths, test names,
evaluation records, benchmark evidence, and status.

Status values: `planned`, `in_progress`, `verified`, `blocked`, `not_applicable`.

## Verified Evidence Bundles

Every row below retains its requirement-specific design/tasks and evidence
description. The exact implementation/test bundle for its section is:

- A: [edition contracts](../../../src/p2p_engine/core/project_publication.py),
  [contract tests](../../../tests/test_project_publication_contracts.py),
  [service tests](../../../tests/test_project_publication_service.py), and
  CLI/MCP tests in [test_cli.py](../../../tests/test_cli.py) and
  [test_mcp.py](../../../tests/test_mcp.py).
- B: [evidence service](../../../src/p2p_engine/services/project_publication_evidence.py),
  [model codecs](../../../src/p2p_engine/services/project_publication_contracts.py),
  [evidence tests](../../../tests/test_project_publication_evidence.py),
  [model tests](../../../tests/test_project_publication_model_contracts.py), and
  [scale tests](../../../tests/test_project_publication_scale.py).
- C: [curator templates](../../../src/p2p_engine/services/agent_templates.py),
  [packet service](../../../src/p2p_engine/services/project_publication.py),
  [agent lifecycle tests](../../../tests/test_agent_instructions_service.py),
  [editorial contract tests](../../../tests/test_project_publication_editorial_evaluation.py),
  and [blind evaluation records](editorial-evaluations.md).
- D: the evidence/model/validation sources above plus contribution cases in
  [evidence tests](../../../tests/test_project_publication_evidence.py) and
  [service tests](../../../tests/test_project_publication_service.py).
- E: [publication service](../../../src/p2p_engine/services/project_publication.py),
  [strict codecs](../../../src/p2p_engine/services/project_publication_contracts.py),
  and atomicity/freshness cases in
  [service tests](../../../tests/test_project_publication_service.py).
- F: [validator](../../../src/p2p_engine/services/project_publication_validation.py),
  [validator/service tests](../../../tests/test_project_publication_service.py),
  [render tests](../../../tests/test_project_publication_rendering.py), and
  [blind evaluation records](editorial-evaluations.md).
- G: publication service/validator/renderer plus
  [workspace facade](../../../src/p2p_engine/storage/filesystem.py),
  [CLI commands](../../../src/p2p_engine/cli_commands/project_ops.py),
  [MCP handlers](../../../src/p2p_engine/mcp/handlers/project.py),
  [CLI tests](../../../tests/test_cli.py),
  [MCP tests](../../../tests/test_mcp_project_handler.py),
  [docs tests](../../../tests/test_project_publication_docs.py), and
  [agent tests](../../../tests/test_agent_instructions_service.py).
- N/X/AC: the row-specific source/test bundle above, package/runtime evidence in
  [implementation.md](implementation.md), and performance/evaluation evidence
  in [editorial-evaluations.md](editorial-evaluations.md) and
  [benchmark-project-publication.py](../../../scripts/benchmark-project-publication.py).

`verified` means direct source plus automated or recorded evaluation evidence
exists. `G-R020` and `AC024` remain `in_progress` because implementation is
complete but live repository alignment is intentionally deferred to M.

## A - Edition Identity, Language, And Paths

| Requirement | Design | Owning tasks | Verified evidence | Status |
| --- | --- | --- | --- | --- |
| A-R001 | D002-D004 | S1-T001..T003, S7-T002 | default CLI/service tests | verified |
| A-R002 | D002-D004 | S1-T001, S7-T001..T004 | command/facade option tests | verified |
| A-R003 | D003 | S1-T002, S1-T009 | language normalization matrix | verified |
| A-R004 | D004 | S1-T003, S1-T010 | output-name/path attack tests | verified |
| A-R005 | D003-D004 | S1-T001..T004 | immutable edition contract tests | verified |
| A-R006 | D004 | S1-T003..T004, S1-T009 | collision/property tests | verified |
| A-R007 | D002, D014 | S1-T007..T008, S7-T001..T004 | edition isolation and list tests | verified |
| A-R008 | D002, D014 | S1-T009, S4-T009..T012 | cross-edition freshness tests | verified |
| A-R009 | D014 | S1-T005, S1-T008, S4-T008 | deterministic catalog tests | verified |
| A-R010 | D002 | S1-T006, S5-T013 | cross-language scope evaluation | verified |

## B - Evidence And Project Model

| Requirement | Design | Owning tasks | Verified evidence | Status |
| --- | --- | --- | --- | --- |
| B-R001 | D005-D006 | S2-T001, S2-T003, S2-T013 | evidence generation/idempotence tests | verified |
| B-R002 | D005-D007 | S2-T002..T003, S2-T016 | source-catalog inclusion golden | verified |
| B-R003 | D005-D006 | S2-T001, S2-T004 | stable evidence ID/hash tests | verified |
| B-R004 | D006-D007 | S2-T005 | classification fixture matrix | verified |
| B-R005 | D006 | S2-T005, S2-T007 | active-unmapped retention test | verified |
| B-R006 | D007 | S2-T005, S2-T014 | historical authority tests | verified |
| B-R007 | D007 | S2-T005, S2-T016 | process-only exclusion tests | verified |
| B-R008 | D005-D006 | S2-T007, S2-T015 | no-truncation/scale tests | verified |
| B-R009 | D005 | S2-T008, S3-T004 | packet-size and no-embed tests | verified |
| B-R010 | D005-D006 | S2-T006, S3-T004 | packet contract golden | verified |
| B-R011 | D008-D009 | S3-T001 | model codec/required-field tests | verified |
| B-R012 | D008 | S3-T002 | claim-evidence integrity tests | verified |
| B-R013 | D008 | S3-T003 | exact evidence-set tests | verified |
| B-R014 | D008 | S3-T002..T003 | used/excluded disposition tests | verified |
| B-R015 | D008, D014 | S3-T001, S3-T005, S4-T003 | binding/freshness tests | verified |
| B-R016 | D007-D009 | S3-T006..T009, S5-T010..T012 | adaptive-outline evaluations | verified |
| B-R017 | D009 | S2-T006, S3-T001..T003 | vertical coverage disposition tests | verified |
| B-R018 | D009 | S2-T006, S5-T012 | generic fallback evaluation | verified |

## C - Editorial Curation

| Requirement | Design | Owning tasks | Verified evidence | Status |
| --- | --- | --- | --- | --- |
| C-R001 | D005-D008 | S3-T004, S3-T006 | packet/skill knowledge-boundary test | verified |
| C-R002 | D017 | S3-T009, S3-T013..T014, S5-T012 | contamination-trap evaluation | verified |
| C-R003 | D005, D008 | S3-T003, S3-T006, S5-T010 | complete accounting evidence | verified |
| C-R004 | D008 | S3-T006, S3-T013 | model-before-prose skill test | verified |
| C-R005 | D007-D011 | S3-T006..T009, S5-T010..T014 | reader autonomy evaluation | verified |
| C-R006 | D002-D003 | S3-T006, S5-T013 | language consistency evaluation | verified |
| C-R007 | D009 | S3-T006..T008, S5-T010..T012 | cross-vertical outline evaluation | verified |
| C-R008 | D009 | S3-T006, S5-T009..T014 | reader usefulness rubric | verified |
| C-R009 | D007, D011 | S3-T008..T009, S5-T003..T005 | governance-noise tests/evaluation | verified |
| C-R010 | D011 | S3-T008, S5-T004, S5-T014 | internal-ID and autonomy tests | verified |
| C-R011 | D007 | S2-T005, S3-T008, S5-T010 | authority-vs-prose evaluation | verified |
| C-R012 | D007 | S3-T009, S5-T010, G-T003 | no implementation inference evidence | verified |
| C-R013 | D007-D008 | S3-T006, S5-T010..T012 | uncertainty rendering evaluation | verified |
| C-R014 | D011 | S5-T014 | citation-erasure review records | verified |
| C-R015 | D017 | S3-T006..T007, S3-T012 | skill size/reference validation | verified |
| C-R016 | D017 | S3-T010..T012, S7-T010 | agent lifecycle resource tests | verified |
| C-R017 | D010 | S3-T004, S3-T015, S7-T013 | candidate path consistency tests | verified |
| C-R018 | D013, D017 | S3-T001, S3-T006, S5-T008 | rubric record schema/evaluation | verified |

## D - Contributions

| Requirement | Design | Owning tasks | Verified evidence | Status |
| --- | --- | --- | --- | --- |
| D-R001 | D012 | S1-T006, S2-T012, S7-T002 | profile/CLI policy tests | verified |
| D-R002 | D006, D012 | S2-T002, S2-T009 | active-source selection tests | verified |
| D-R003 | D012 | S2-T010 | Unicode/name identity tests | verified |
| D-R004 | D012 | S2-T009..T011 | unattributed denominator tests | verified |
| D-R005 | D012 | S2-T011 | basis-point allocation property tests | verified |
| D-R006 | D012 | S2-T011 | tie ordering tests | verified |
| D-R007 | D012 | S2-T011, S5-T007 | limitation/data validation tests | verified |
| D-R008 | D012 | S2-T012 | auto behavior tests | verified |
| D-R009 | D012 | S2-T012, S4-T004 | include/omit failure tests | verified |
| D-R010 | D012 | S3-T006, S5-T007, S5-T013 | localized chapter evaluation | verified |

## E - Import, Provenance, And Freshness

| Requirement | Design | Owning tasks | Verified evidence | Status |
| --- | --- | --- | --- | --- |
| E-R001 | D008, D010 | S4-T001 | triplet import tests | verified |
| E-R002 | D010 | S3-T015, S4-T002 | exact/alternative safe path tests | verified |
| E-R003 | D008, D014 | S3-T001, S4-T002..T004 | parser/version/binding tests | verified |
| E-R004 | D008 | S3-T002..T003, S4-T004 | referential failure matrix | verified |
| E-R005 | D014 | S4-T005..T006, S4-T012 | fault-injection/atomicity tests | verified |
| E-R006 | D014 | S4-T003, S4-T007 | manifest hash-chain tests | verified |
| E-R007 | D014 | S4-T009 | shared/local invalidation tests | verified |
| E-R008 | D014 | S4-T009..T010 | manual edit detection tests | verified |
| E-R009 | D014 | S2-T013, S4-T011 | byte-equivalent idempotence tests | verified |
| E-R010 | D014 | S4-T006..T010, S7-T003..T004 | status-state tests | verified |
| E-R011 | D006 | S2-T003, S2-T015, S8-T005..T006 | operation-count benchmarks | verified |
| E-R012 | D001, D007 | S2-T002, S2-T016, S8-T004 | source-boundary regression | verified |

## F - Validation And Evaluation

| Requirement | Design | Owning tasks | Verified evidence | Status |
| --- | --- | --- | --- | --- |
| F-R001 | D008, D013-D014 | S4-T004, S5-T001..T002, S5-T007 | chain/contract validation tests | verified |
| F-R002 | D011, D013 | S5-T003..T004 | Markdown contract test matrix | verified |
| F-R003 | D011, D013 | S3-T008, S5-T003 | localized heading/no-boilerplate tests | verified |
| F-R004 | D013 | S5-T005 | heuristic finding tests | verified |
| F-R005 | D013 | S5-T001, S5-T006 | stable finding payload tests | verified |
| F-R006 | D013 | S5-T006, S6-T002 | render gate severity tests | verified |
| F-R007 | D013 | S5-T005..T006, S7-T011 | docs/message honesty tests | verified |
| F-R008 | D013, D017 | S5-T008..T009 | rubric schema/threshold record | verified |
| F-R009 | D009, D013 | S5-T010..T013 | three-vertical forward evaluations | verified |
| F-R010 | D017 | S3-T013..T014, S5-T012 | isolation contamination evaluation | verified |

## G - Rendering, Review, Interfaces, And Compatibility

| Requirement | Design | Owning tasks | Verified evidence | Status |
| --- | --- | --- | --- | --- |
| G-R001 | D014 | S6-T001..T003 | edition render gate/path tests | verified |
| G-R002 | D003 | S6-T001, S6-T009 | HTML lang/title tests | verified |
| G-R003 | D002, D014 | S6-T002, S6-T005, S6-T009 | cross-edition render tests | verified |
| G-R004 | D018 | S6-T004..T005 | review hash-binding tests | verified |
| G-R005 | D018 | S6-T005, S6-T010 | cross-language approval tests | verified |
| G-R006 | D018 | S6-T004, S6-T006 | owner/publication boundary tests | verified |
| G-R007 | D003-D004 | S7-T001..T004, S7-T008 | CLI option/default tests | verified |
| G-R008 | D014 | S7-T003..T004, S7-T008 | list/status text/JSON tests | verified |
| G-R009 | D014 | S7-T005..T009 | MCP schema/parity tests | verified |
| G-R010 | D018 | S6-T006, S7-T005..T009 | no MCP review assertion | verified |
| G-R011 | D001-D004 | S1-T007, S7-T001, S8-T003 | default facade compatibility tests | verified |
| G-R012 | D015 | S8-T004 | workspace-v3 regression | verified |
| G-R013 | D015 | S1-T005..T006, S4-T007, S7-T012 | version identity tests/docs | verified |
| G-R014 | D015 | S8-T001..T003 | legacy classification tests | verified |
| G-R015 | D016 | S6-T007..T008, S8-T003 | default alias tests | verified |
| G-R016 | D016 | S6-T007..T008 | non-default no-alias tests | verified |
| G-R017 | D017 | S3-T010..T012, S7-T010, S8-T009..T010 | generated resource lifecycle/package tests | verified |
| G-R018 | D001-D018 | S7-T011..T013 | documentation consistency tests | verified |
| G-R019 | D017 | S8-T009..T012 | wheel/sdist/Python/PDF tests | verified |
| G-R020 | D015-D018 | G-T010..T011, M-T001..T011 | P..G no-write audit plus owner-confirmed EN/IT alignment, hash comparison, doctor and validation | verified |

## Non-Functional Requirements

| Requirement | Design | Owning tasks | Verified evidence | Status |
| --- | --- | --- | --- | --- |
| N001 | D001, D013 | S4-T001..T013, S5-T001..T007 | offline deterministic suite | verified |
| N002 | D014 | S1-T005, S2-T013, S4-T005..T008, S6-T002 | YAML/atomic write tests | verified |
| N003 | D003-D006, D014 | S1-T008, S2-T004, S4-T008 | reversed-enumeration tests | verified |
| N004 | D014 | S1-T008, S4-T010, S7-T003, S8-T007 | byte-invariance tests | verified |
| N005 | D004, D010 | S1-T003..T004, S4-T002, S8-T007 | traversal/symlink tests | verified |
| N006 | D001, component design | S7-T001..T006, S8-T008 | architecture/size audit | verified |
| N007 | D006, performance design | P-T006, S2-T015, S8-T005..T006 | scale benchmarks/counters | verified |
| N008 | D005-D006 | S2-T004, S2-T013..T015, S8-T007 | deterministic byte tests | verified |
| N009 | rejected alternatives | S6-T003, S8-T009..T013 | dependency/package audit | verified |
| N010 | D003-D004, D014 | S1-T002..T004, S4-T003, S7-T004 | diagnostic payload tests | verified |
| N011 | core contracts | S1-T001, S2-T001, S5-T001, S7-T004 | JSON serialization snapshots | verified |
| N012 | testing strategy | S8-T009..T012 | source/wheel/sdist parity | verified |
| N013 | testing strategy | P-T005, S1-T011, S7-T014, S8-T010..T012 | Python matrix results | verified |
| N014 | rollout boundary | P-T009..T010, S8-T013, G-T009 | diff/release side-effect audit | verified |

## Edge Cases

| Requirement | Design | Owning tasks | Verified evidence | Status |
| --- | --- | --- | --- | --- |
| X001 | D003 | S1-T002, S7-T002 | invalid/empty language tests | verified |
| X002 | D003 | S1-T002, S1-T009 | alias/equivalent identity tests | verified |
| X003 | D004 | S1-T003, S1-T010 | name attack tests | verified |
| X004 | D002, D014 | S1-T009, S4-T012 | execution-order tests | verified |
| X005 | D014 | S4-T009..T010 | shared/local drift tests | verified |
| X006 | D009 | S2-T006, S2-T014 | missing vertical tests | verified |
| X007 | D006 | S2-T007, S2-T014 | unmapped evidence tests | verified |
| X008 | D007-D008 | S2-T005, S3-T003, S4-T004 | historical claim rejection tests | verified |
| X009 | D008 | S3-T003, S4-T013 | incomplete accounting test | verified |
| X010 | D007-D008 | S3-T002..T003, S4-T013 | unknown/process-only claim tests | verified |
| X011 | D010 | S1-T010, S4-T002 | canonical-source rejection tests | verified |
| X012 | D014 | S4-T005..T006 | interrupted import tests | verified |
| X013 | D014, D018 | S4-T009..T010, S6-T005 | local stale-chain tests | verified |
| X014 | D015 | S1-T005, S4-T007, S8-T003 | future-version tests | verified |
| X015 | D012 | S2-T012, S4-T004, S5-T007 | contribution policy edge tests | verified |
| X016 | D012 | S2-T010 | suspicious identity tests | verified |
| X017 | D012 | S2-T011, S5-T007 | 100.00% property tests | verified |
| X018 | D003, D013 | S5-T003, S6-T009 | localized heading/render tests | verified |
| X019 | D011, D013 | S5-T004 | internal-ID rejection tests | verified |
| X020 | D007, D013 | S5-T004..T005 | product-term vs boilerplate tests | verified |
| X021 | D001 | S6-T003, S6-T009, S8-T010 | missing PDF capability tests | verified |
| X022 | D018 | S6-T005, S6-T010 | cross-language approval tests | verified |
| X023 | D015-D016 | S6-T008, S8-T001..T003 | legacy approval/alias tests | verified |
| X024 | D017 | S3-T010..T012, S7-T010 | partial/drifted skill repair tests | verified |

## Acceptance Criteria

| Criterion | Design | Owning tasks | Required evidence | Status |
| --- | --- | --- | --- | --- |
| AC001 | D002-D004 | S1-T009, S7-T008, G-T004 | en/it coexistence both orders | verified |
| AC002 | D004 | S1-T009, S6-T009, G-T004 | custom-name Markdown/PDF | verified |
| AC003 | D005 | S2-T008, S3-T004, G-T005 | bounded packet and path/hash assertions | verified |
| AC004 | D005-D007 | S2-T014..T016, G-T005 | complete deterministic index | verified |
| AC005 | D008, D014 | S3-T003, S4-T013, G-T005 | strict/atomic triplet import | verified |
| AC006 | D007-D011 | S5-T003..T005, S5-T014, G-T003 | autonomy and no-internal-ID evidence | verified |
| AC007 | D009, D017 | S3-T013..T014, S5-T010..T012, G-T003 | vertical-adaptive skill evaluations | verified |
| AC008 | D013 | S5-T009..T015, G-T005 | three-vertical rubric records | verified |
| AC009 | D002-D003 | S5-T013, S6-T009, G-T004 | English default and Italian E2E | verified |
| AC010 | D011, D013 | S5-T003..T004, G-T003 | localized/no-boilerplate validator tests | verified |
| AC011 | D012 | S2-T009..T012, S5-T007, G-T005 | contribution algorithm/property tests | verified |
| AC012 | D007 | S3-T009, S5-T010, G-T003 | no inference evaluation | verified |
| AC013 | D014 | S4-T009..T013, G-T004 | shared/local freshness graph tests | verified |
| AC014 | D003-D004 | S6-T001..T003, G-T004 | lang/title/path render evidence | verified |
| AC015 | D018 | S6-T004..T010, G-T004 | edition approval isolation | verified |
| AC016 | D014 | S7-T004..T009, G-T006 | CLI/MCP parity snapshots | verified |
| AC017 | D017 | S3-T010..T012, S7-T010, G-T006 | agent resource lifecycle | verified |
| AC018 | D015 | S7-T001, S8-T003..T004, G-T006 | default facade/workspace-v3 tests | verified |
| AC019 | D015-D016 | S8-T001..T003, G-T006 | legacy status/no approval transfer | verified |
| AC020 | testing strategy | S8-T009..T012, G-T007 | complete source/install matrix | verified |
| AC021 | D006, performance design | S2-T015, S8-T005..T006, G-T007 | structural scale evidence | verified |
| AC022 | public interface | S7-T011..T013, G-T006 | docs/help/path consistency | verified |
| AC023 | traceability rule | P-T003, every slice update, G-T002 | no planned/uncovered matrix rows | verified |
| AC024 | rollout | G-T009..T011, M-T001..T011 | owner-confirmed adapter and EN/IT publication alignment; schema/source hash invariance and residual legacy classification | verified |
