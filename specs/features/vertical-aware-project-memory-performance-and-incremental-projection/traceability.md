# Traceability - Vertical-Aware Project Memory Performance And Incremental Projection

The matrix records the final evidence after each slice update. `verified` means
direct code plus test or measurement evidence exists. `pending-owner` is
reserved for repository alignment.

| Requirement | Owning slice | Design | Test/evidence | Status |
| --- | --- | --- | --- | --- |
| A-R001 | P | D001 | provenance/baseline | verified |
| A-R002 | P | D001 | provenance/baseline | verified |
| A-R003 | P | D001 | provenance/baseline | verified |
| A-R004 | P | D001 | provenance/baseline | verified |
| A-R005 | A1 | D002-D004 | read-context/source-capture | verified |
| A-R006 | A1 | D002-D004 | read-context/source-capture | verified |
| A-R007 | A1 | D002-D004 | read-context/source-capture | verified |
| A-R008 | A1 | D002-D004 | read-context/source-capture | verified |
| A-R009 | A1 | D002-D004 | read-context/source-capture | verified |
| A-R010 | A1 | D002-D004 | read-context/source-capture | verified |
| A-R011 | A1 | D002-D004 | read-context/source-capture | verified |
| A-R012 | A1 | D002-D004 | read-context/source-capture | verified |
| A-R013 | A1 | D002-D004 | read-context/source-capture | verified |
| A-R014 | A2 | D005-D006 | schema/lifecycle parity | verified |
| A-R015 | A2 | D005-D006 | schema/lifecycle parity | verified |
| A-R016 | A2 | D005-D006 | schema/lifecycle parity | verified |
| A-R017 | A2 | D005-D006 | schema/lifecycle parity | verified |
| A-R018 | A2 | D005-D006 | schema/lifecycle parity | verified |
| A-R019 | A2 | D005-D006 | schema/lifecycle parity | verified |
| A-R020 | A3 | D006-D007 | vertical batch parity | verified |
| A-R021 | A3 | D006-D007 | vertical batch parity | verified |
| A-R022 | A3 | D006-D007 | vertical batch parity | verified |
| A-R023 | A3 | D006-D007 | vertical batch parity | verified |
| A-R024 | A3 | D006-D007 | vertical batch parity | verified |
| A-R025 | A3 | D006-D007 | vertical batch parity | verified |
| A-R026 | A5 | D007-D008 | fast-path provider counts | verified |
| A-R027 | A5 | D007-D008 | fast-path provider counts | verified |
| A-R028 | A5 | D007-D008 | fast-path provider counts | verified |
| A-R029 | A5 | D007-D008 | fast-path provider counts | verified |
| A-R030 | A5 | D007-D008 | fast-path provider counts | verified |
| A-R031 | A5 | D007-D008 | fast-path provider counts | verified |
| A-R032 | A5 | D007-D008 | fast-path provider counts | verified |
| A-R033 | A5 | D007-D008 | fast-path provider counts | verified |
| A-R034 | A5 | D007-D008 | fast-path provider counts | verified |
| A-R035 | A5 | D007-D008 | fast-path provider counts | verified |
| A-R036 | A4 | D009-D010 | registry atomicity/freshness | verified |
| A-R037 | A4 | D009-D010 | registry atomicity/freshness | verified |
| A-R038 | A4 | D009-D010 | registry atomicity/freshness | verified |
| A-R039 | A4 | D009-D010 | registry atomicity/freshness | verified |
| A-R040 | A4 | D009-D010 | registry atomicity/freshness | verified |
| A-R041 | A4 | D009-D010 | registry atomicity/freshness | verified |
| A-R042 | A4 | D009-D010 | registry atomicity/freshness | verified |
| A-R043 | A4 | D009-D010 | registry atomicity/freshness | verified |
| A-R044 | A6 | D011 | YAML/deep-validation parity | verified |
| A-R045 | A6 | D011 | YAML/deep-validation parity | verified |
| A-R046 | A6 | D011 | YAML/deep-validation parity | verified |
| A-R047 | A6 | D011 | YAML/deep-validation parity | verified |
| A-R048 | A6 | D011 | YAML/deep-validation parity | verified |
| B-R001 | B1/B2 | D012-D014 | vertical-memory contracts/full builder | verified |
| B-R002 | B1/B2 | D012-D014 | vertical-memory contracts/full builder | verified |
| B-R003 | B1/B2 | D012-D014 | vertical-memory contracts/full builder | verified |
| B-R004 | B1/B2 | D012-D014 | vertical-memory contracts/full builder | verified |
| B-R005 | B1/B2 | D012-D014 | vertical-memory contracts/full builder | verified |
| B-R006 | B1/B2 | D012-D014 | vertical-memory contracts/full builder | verified |
| B-R007 | B1/B2 | D012-D014 | vertical-memory contracts/full builder | verified |
| B-R008 | B1/B2 | D012-D014 | vertical-memory contracts/full builder | verified |
| B-R009 | B2 | D015-D016/D024 | vertical-memory contracts/full builder | verified |
| B-R010 | B2 | D015-D016/D024 | vertical-memory contracts/full builder | verified |
| B-R011 | B2 | D015-D016/D024 | vertical-memory contracts/full builder | verified |
| B-R012 | B2 | D015-D016/D024 | vertical-memory contracts/full builder | verified |
| B-R013 | B2 | D015-D016/D024 | vertical-memory contracts/full builder | verified |
| B-R014 | B2 | D015-D016/D024 | vertical-memory contracts/full builder | verified |
| B-R015 | B2 | D015-D016/D024 | vertical-memory contracts/full builder | verified |
| B-R016 | B2 | D015-D016/D024 | vertical-memory contracts/full builder | verified |
| B-R017 | B2 | D015-D016/D024 | vertical-memory contracts/full builder | verified |
| B-R018 | B2 | D015-D016/D024 | vertical-memory contracts/full builder | verified |
| B-R019 | B3 | D017 | impact/full-incremental equivalence | verified |
| B-R020 | B3 | D017 | impact/full-incremental equivalence | verified |
| B-R021 | B3 | D017 | impact/full-incremental equivalence | verified |
| B-R022 | B3 | D017 | impact/full-incremental equivalence | verified |
| B-R023 | B3 | D017 | impact/full-incremental equivalence | verified |
| B-R024 | B3 | D017 | impact/full-incremental equivalence | verified |
| B-R025 | B3 | D017 | impact/full-incremental equivalence | verified |
| B-R026 | B4 | D018 | atomicity/recovery | verified |
| B-R027 | B4 | D018 | atomicity/recovery | verified |
| B-R028 | B4 | D018 | atomicity/recovery | verified |
| B-R029 | B4/B5 | D019-D020 | status/fallback/public surface | verified |
| B-R030 | B4/B5 | D019-D020 | status/fallback/public surface | verified |
| B-R031 | B4/B5 | D019-D020 | status/fallback/public surface | verified |
| B-R032 | B4/B5 | D019-D020 | status/fallback/public surface | verified |
| B-R033 | B4/B5 | D019-D020 | status/fallback/public surface | verified |
| B-R034 | B4/B5 | D019-D020 | status/fallback/public surface | verified |
| B-R035 | B4/B5 | D019-D020 | status/fallback/public surface | verified |
| B-R036 | B4/B5 | D019-D020 | status/fallback/public surface | verified |
| B-R037 | B4/B5 | D019-D020 | status/fallback/public surface | verified |
| B-R038 | B2/B5 | D024 | compactness/pagination | verified |
| B-R039 | B2/B5 | D024 | compactness/pagination | verified |
| B-R040 | B2/B5 | D024 | compactness/pagination | verified |
| B-R041 | B5 | D025 | accelerator-fallback parity | verified |
| B-R042 | B1/B2 | D010/D013 | accelerator-fallback parity | verified |
| C-R001 | C1 | D021 | readiness/progress parity | verified |
| C-R002 | C1 | D021 | readiness/progress parity | verified |
| C-R003 | C1 | D021 | readiness/progress parity | verified |
| C-R004 | C1 | D021 | readiness/progress parity | verified |
| C-R005 | C1 | D021 | readiness/progress parity | verified |
| C-R006 | C1 | D021 | readiness/progress parity | verified |
| C-R007 | C1 | D021 | readiness/progress parity | verified |
| C-R008 | C1 | D021 | readiness/progress parity | verified |
| C-R009 | C1 | D021 | readiness/progress parity | verified |
| C-R010 | C2 | D022 | context budgets/retrieval | verified |
| C-R011 | C2 | D022 | context budgets/retrieval | verified |
| C-R012 | C2 | D022 | context budgets/retrieval | verified |
| C-R013 | C2 | D022 | context budgets/retrieval | verified |
| C-R014 | C2 | D022 | context budgets/retrieval | verified |
| C-R015 | C2 | D022 | context budgets/retrieval | verified |
| C-R016 | C3 | D002/D022 | next-action identity/provider counts | verified |
| C-R017 | C3 | D002/D022 | next-action identity/provider counts | verified |
| C-R018 | C3 | D002/D022 | next-action identity/provider counts | verified |
| C-R019 | C3 | D002/D022 | next-action identity/provider counts | verified |
| C-R020 | C3 | D002/D022 | next-action identity/provider counts | verified |
| C-R021 | C4 | D012/D021 | vertical rendering/freshness | verified |
| C-R022 | C4 | D012/D021 | vertical rendering/freshness | verified |
| C-R023 | C4 | D012/D021 | vertical rendering/freshness | verified |
| C-R024 | C4 | D012/D021 | vertical rendering/freshness | verified |
| C-R025 | C4 | D012/D021 | vertical rendering/freshness | verified |
| X-R001 | X | D023 | persistence evaluation measurements/audit | verified |
| X-R002 | X | D023 | persistence evaluation measurements/audit | verified |
| X-R003 | X | D023 | persistence evaluation measurements/audit | verified |
| X-R004 | X | D023 | persistence evaluation measurements/audit | verified |
| X-R005 | X | D023 | persistence evaluation measurements/audit | verified |
| X-R006 | X | D023 | persistence evaluation measurements/audit | verified |
| X-R007 | X | D023 | persistence evaluation measurements/audit | verified |
| X-R008 | X | D023 | persistence evaluation measurements/audit | verified |
| X-R009 | X | D023 | persistence evaluation measurements/audit | verified |
| N001 | A/B/G | D002-D020 | cross-cutting focused/gate evidence | verified |
| N002 | P/A/B/C | D002-D020 | cross-cutting focused/gate evidence | verified |
| N003 | A4/B4 | D002-D020 | cross-cutting focused/gate evidence | verified |
| N004 | A2/B2 | D002-D020 | cross-cutting focused/gate evidence | verified |
| N005 | A1/A4/B4 | D002-D020 | cross-cutting focused/gate evidence | verified |
| N006 | A1/B1 | D002-D020 | cross-cutting focused/gate evidence | verified |
| N007 | A4/B4 | D002-D020 | cross-cutting focused/gate evidence | verified |
| N008 | A1/B5 | D002-D020 | cross-cutting focused/gate evidence | verified |
| N009 | B5/C | D002-D020 | cross-cutting focused/gate evidence | verified |
| N010 | P/G | D002-D020 | Python 3.11.15 container and Python 3.14.4 full suites | verified |
| N011 | A6/G | D002-D020 | cross-cutting focused/gate evidence | verified |
| N012 | A4/B4 | D002-D020 | cross-cutting focused/gate evidence | verified |
| N013 | A-G/C-G | D001/D023-D025 | cross-cutting focused/gate evidence | verified |
| N014 | A-G/C-G | D001/D023-D025 | cross-cutting focused/gate evidence | verified |
| N015 | P/A-G/G | D001/D023-D025 | cross-cutting focused/gate evidence | verified |
| N016 | P/X/G | D001/D023-D025 | cross-cutting focused/gate evidence | verified |
| N017 | P/B/X/G | D001/D023-D025 | cross-cutting focused/gate evidence | verified |
| N018 | B2/G | D001/D023-D025 | cross-cutting focused/gate evidence | verified |
| E001 | A1/B4 | D004/D010/D018-D020 | failure injection/diagnostic matrix | verified |
| E002 | A2 | D004/D010/D018-D020 | failure injection/diagnostic matrix | verified |
| E003 | A3/B2 | D004/D010/D018-D020 | failure injection/diagnostic matrix | verified |
| E004 | A4/B2 | D004/D010/D018-D020 | failure injection/diagnostic matrix | verified |
| E005 | A4 | D004/D010/D018-D020 | failure injection/diagnostic matrix | verified |
| E006 | A4/B4 | D004/D010/D018-D020 | failure injection/diagnostic matrix | verified |
| E007 | B4 | D004/D010/D018-D020 | failure injection/diagnostic matrix | verified |
| E008 | B1/B2/B5 | D004/D010/D018-D020 | failure injection/diagnostic matrix | verified |
| E009 | B2/C | D004/D010/D018-D020 | failure injection/diagnostic matrix | verified |
| E010 | B5 | D004/D010/D018-D020 | failure injection/diagnostic matrix | verified |
| E011 | B4/C | D004/D010/D018-D020 | failure injection/diagnostic matrix | verified |
| E012 | A4/B1/B4 | D004/D010/D018-D020 | failure injection/diagnostic matrix | verified |
| AC001 | P | acceptance criteria mapped above | direct gate evidence | verified |
| AC002 | A1 | acceptance criteria mapped above | direct gate evidence | verified |
| AC003 | A2 | acceptance criteria mapped above | direct gate evidence | verified |
| AC004 | A2/A3/B | acceptance criteria mapped above | direct gate evidence | verified |
| AC005 | A5 | acceptance criteria mapped above | direct gate evidence | verified |
| AC006 | A6 | acceptance criteria mapped above | direct gate evidence | verified |
| AC007 | A4 | acceptance criteria mapped above | direct gate evidence | verified |
| AC008 | A4/B4 | acceptance criteria mapped above | direct gate evidence | verified |
| AC009 | B2 | acceptance criteria mapped above | direct gate evidence | verified |
| AC010 | B2 | acceptance criteria mapped above | direct gate evidence | verified |
| AC011 | B2/C1 | acceptance criteria mapped above | direct gate evidence | verified |
| AC012 | B3 | acceptance criteria mapped above | direct gate evidence | verified |
| AC013 | B4 | acceptance criteria mapped above | direct gate evidence | verified |
| AC014 | B5 | acceptance criteria mapped above | direct gate evidence | verified |
| AC015 | C1 | acceptance criteria mapped above | direct gate evidence | verified |
| AC016 | C2 | acceptance criteria mapped above | direct gate evidence | verified |
| AC017 | C3 | acceptance criteria mapped above | direct gate evidence | verified |
| AC018 | C4 | acceptance criteria mapped above | direct gate evidence | verified |
| AC019 | P/A/B/C | acceptance criteria mapped above | direct gate evidence | verified |
| AC020 | A-G/C-G | acceptance criteria mapped above | direct gate evidence | verified |
| AC021 | G | acceptance criteria mapped above | direct gate evidence | verified |
| AC022 | X | acceptance criteria mapped above | direct gate evidence | verified |
| AC023 | B2/B5 | acceptance criteria mapped above | direct gate evidence | verified |
| AC024 | B5 | acceptance criteria mapped above | direct gate evidence | verified |
| AC025 | B1/B2 | acceptance criteria mapped above | direct gate evidence | verified |

## Slice Exit Evidence

| Slice | Code | Focused evidence | Public/deep evidence | Measurement/evidence | Status |
| --- | --- | --- | --- | --- | --- |
| P | provenance/test runners/fixtures | `test_test_scripts`, harness tests | source and installed smoke | baseline and import records | verified |
| A1 | document store/read context | document-store/read-context tests | context/workspace regressions | one-read/retry counters | verified |
| A2 | preflight/lifecycle batch | lifecycle/schema tests | migration/decision full suites | 1 preflight, N parses | verified |
| A3 | vertical batch/progress | vertical coverage/progress tests | readiness/vertical suites | linear coverage timings | verified |
| A4 | atomic registry bundle | registry/failure tests | CLI/MCP/validation suites | current status without reconstruction | verified |
| A5 | fast read surfaces | `test_fast_read_paths` | CLI/MCP public suite | current cold and MCP timings | verified |
| A6 | shared YAML contracts | `test_yaml_loaders` | 1,332 tests in both loader modes | 26-call justified audit | verified |
| A-G | integrated A block | all A focused tests | source full/public/package | current, scale, and Python 3.11 | verified |
| B1 | typed contracts/ownership | contract tests | serializer/freshness suites | compact schema evidence | verified |
| B2 | full builder | memory service tests | lifecycle/conflict/vertical suites | full-build/output measurements | verified |
| B3 | impact/incremental | incremental tests | post-commit/full regressions | byte equivalence at all scales | verified |
| B4 | materialization/fallback | atomicity/concurrency tests | freshness/recovery suites | status/load/fallback timings | verified |
| B5 | CLI/MCP/hooks | post-commit and handler tests | public/docs/template suites | bounded pagination evidence | verified |
| B-G | integrated B block | all B focused tests | source full/public/package | scratch current candidate, scale, and Python 3.11 | verified |
| C1 | readiness/progress adapter | readiness-memory tests | readiness/question suites | materialized/fallback parity | verified |
| C2 | bounded context | context/fast-path tests | targeted retrieval CLI/MCP | 100/1k/10k timings | verified |
| C3 | typed next inputs | next-action tests | decision/change/context suites | provider reuse and stable order | verified |
| C4 | vertical-first rendering | project-state golden tests | export/publication/freshness suites | source-bound rendering | verified |
| C-G | integrated C block | all C focused tests | source full/public/package | final current/scale and Python 3.11 | verified |
| X | no persistence implementation | audits/harness tests | full suites | `filesystem_sufficient` report | verified |
| G | final source gate | 1,332 tests both loaders | wheel/sdist and installed smoke | diff/audit/performance/Python 3.11 | verified |
| M | no source code | supported registry/project refresh | validation/freshness/context/next/status | current manifests, diff and performance comparison | verified |
