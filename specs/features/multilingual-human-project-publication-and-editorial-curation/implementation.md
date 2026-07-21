# Implementation Evidence - Multilingual Human Project Publication And Editorial Curation

## Environment And Import Provenance

- Implementation baseline Git revision:
  `8450c0d75d41b12717cfd18f1a54aeb5897731e2`.
- Repository root:
  `/home/davide/dati/60_lavoro/060_p2p_engine`.
- Source imports used `PYTHONPATH=src` and resolved to
  `src/p2p_engine/__init__.py`.
- Development runtime: CPython 3.14.4 from `.venv/bin/python`.
- Supported-runtime verification: CPython 3.11.15 from
  `python:3.11-bookworm` with the repository mounted read-only.
- Package version remained `0.4.1`; workspace schema remained v3.
- Final local artifacts were built under
  `/tmp/p2p-publication-final-dist.jiFI3n`; nothing was copied to repository
  `dist/`, uploaded, tagged, committed, or released.
- Forward-evaluation root:
  `/tmp/p2p-publication-forward-current.tVKbPp`. Fixture identity and final
  content hashes are recorded in `editorial-evaluations.md`.

The worktree already contained broad owner/P2P changes before this feature.
Feature work preserved them and did not use a clean-tree assumption.

## Baseline And Compatibility Decisions

The v1 publication implementation had one unsuffixed profile, packet,
Markdown, validation, PDF, review, and manifest under `outputs/latest`.
Language was `project_default`, audience was `mixed`, the packet embedded the
complete visible export, import accepted Markdown only, validation required the
English heading `Executive Summary` plus visible `.p2p` authority wording, and
the renderer hard-coded HTML language `it` and `project.pdf`.

The implementation keeps v1 files as read-only legacy derived state. It does
not infer a missing model/accounting sidecar, import v1 content, or transfer a
legacy approval. Omitted public arguments remain compatible by selecting the
v2 default edition `(output_name=project, language=en)`. Default-English v1
Markdown/PDF names are write-only compatibility aliases after a successful v2
import/render and are never freshness inputs. Publication contract v2 is not a
workspace schema version.

## Delivered Slices

### P - Preparation

Recorded the v1 behavior inventory, focused baseline, exact compatibility
decisions, source/fixture boundaries, scale harness, package/runtime commands,
and no-write rollout boundary. Representative v1 states are generated in
isolated tests rather than copied from live `outputs/`.

### S1 - Edition Contracts

Added immutable edition/language/path/catalog contracts in
`core/project_publication.py`. Language normalization supports BCP 47 casing and
`eng -> en` / `ita -> it`; output names use a bounded ASCII slug. One symlink-
aware resolver owns shared, edition, candidate, canonical, PDF, review, and
legacy-alias paths. Catalog reads parse only committed edition manifests and do
not regenerate evidence.

### S2 - Evidence And Contributions

Added `ProjectPublicationEvidenceService` and strict evidence-index contracts.
One read context discovers complete project/vertical/proposal/uncertainty/
contribution/process sources, assigns stable evidence IDs, retains active
unmapped evidence, classifies historical and process-only material, and writes
one shared semantic-hash-bound index. The visible export is path/hash evidence,
not packet bytes.

Contribution shares use authoritative active records, preserve unattributed
records, normalize author text without guessed identity merges, allocate basis
points with deterministic largest remainder, total exactly 100.00%, and carry a
mandatory limitation that the figures do not measure effort, quality, merit,
ownership, authorship, or intellectual property.

### S3 - Project Model, Packet, And Curator Skill

Added strict v2 model/accounting codecs, exact-set and bidirectional claim links,
vertical coverage, generic fallback, and editorial self-assessment. The packet
is bounded and declares the selected edition, complete evidence boundary,
candidate triplet, exact physical/semantic bindings, and corrective command.

The release curator skill is concise and owns four one-level references:

- `references/editorial-workflow.md`;
- `references/publication-contracts.md`;
- `references/vertical-interpretation.md`;
- `references/editorial-rubric.md`.

The contract reference now includes exact YAML field names/nesting, title/H2-H3
outline materialization, natural UTF-8 localization, and no implicit adjacent-
project knowledge. Agent install/update/doctor/uninstall owns all resources for
both modern and legacy Codex skill roots.

### S4 - Import And Freshness

`import_curated` now imports Markdown, model, and accounting as one
edition-scoped transaction. It validates current packet/profile/source/evidence
bindings and all semantics before staging, rejects unsafe/canonical/symlinked or
colliding sources, atomically replaces targets, commits the manifest last, and
restores the prior current revision after injected failures.

Per-edition manifests bind profile, packet, model, accounting, Markdown,
validation, render, review, and aliases. Shared evidence drift invalidates every
edition; edition-local edits invalidate only the dependent edition. Idempotent
byte-equivalent writes preserve downstream state. Catalog discovery reports
invalid/future manifests without repairing them.

### S5 - Validation And Forward Evaluation

Validation now checks the complete hash/version chain and language-neutral
Markdown structure. Deterministic errors block render; warnings/advisories do
not. Internal workflow IDs in reader prose are errors, while evidenced generic
proposal/decision terminology remains allowed when it is project subject
matter. Heuristics report probable language mismatch, workflow narration,
placeholders, imbalance, weak structure, contribution wording, and model/prose
mismatch without claiming semantic proof.

Four blind curator runs and one independent citation-erasure evaluation passed.
The runs found four material instruction/heuristic defects, all corrected and
rerun. Exact documents, scores, hashes, scope comparison, and limits are in
`editorial-evaluations.md`.

### S6 - Rendering And Review

Rendering requires a current passed validation, uses model title plus canonical
language in escaped HTML metadata, writes `<edition-key>.pdf` atomically, and
records all dependent hashes. WeasyPrint remains optional and a missing PDF
capability leaves prior stages untouched.

Review remains owner-controlled and CLI-only. Approval binds one exact edition,
Markdown, PDF, validation, model, accounting, and language. No MCP review write
exists; no approval transfers across language, output name, regeneration, or
legacy state.

### S7 - Public Surfaces

Workspace facade, CLI, MCP catalog/handlers, status/list payloads, help, docs,
glossary, freshness, impact, and agent lifecycle expose the same edition
semantics. Every edition command accepts `--language` and `--output-name`;
prepare adds `--contributions`; import requires model and accounting candidates.
`publish list` is read-only and stable. Omitting new fields selects
`project-en`.

### S8 - Compatibility, Performance, Packaging, And Quality

Legacy state is classified as complete/partial/invalid/stale/approved without
mutation. Workspace schema/runtime/migration behavior is unchanged. Structural
tests cover duplicate-key YAML, C/Python loader parity, reversed enumeration,
restart determinism, symlinks, atomic failures, byte invariance, future
versions, and no evidence rebuild per edition.

Large publication orchestration was split into focused preparation, candidate
validation, transaction, and validator helpers. No database, network provider,
translation provider, language detector, or mandatory PDF dependency was added.
The repository declares no Ruff, mypy, or Pyright configuration/tool gate;
compileall, source audit, tests, and diff checks are recorded instead.

## Public Behavior

The canonical v2 default paths are:

- shared evidence/catalog: `outputs/latest/publication-evidence.yml` and
  `outputs/latest/publications.yml`;
- edition state: `outputs/latest/publications/<edition-key>/...`;
- reader Markdown/PDF: `outputs/latest/<edition-key>.md` and `.pdf`;
- curator candidates: `drafts/project-publication/<edition-key>.md`,
  `.model.yml`, and `.evidence.yml`.

Examples are `project-en`, `project-it`, and `outputxyz-en`. Language changes
translation/localization only; they do not create audience variants or alter
project scope. Reader prose explains the project and may include a truthful
Contributions chapter, but excludes P2P workflow traceability and governance
status.

## Editorial Evaluation Summary

Independent scores were:

| Fixture | Minimum score | Result |
| --- | ---: | --- |
| software EN | 4 | passed |
| board game EN | 4 | passed |
| generic fallback EN | 4 | passed |
| software IT | 5 | passed |

No zero-tolerance failure or unrelated-brand contamination was recorded. EN/IT
scope comparison reported `same_project_scope: true` and no actual drift.

## Performance

V1 baseline and final v2 measurements use the same generated 100/1,000/10,000
proposal fixture shape. Times are single-run wall seconds, intended to expose
algorithmic shape rather than establish service-level targets.

| Proposals | V1 prepare | V2 prepare | V1 status | V2 status | V2 list | V2 second edition |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 100 | 0.0935 | 0.1371 | 0.1080 | 0.0400 | 0.0024 | 0.0866 |
| 1,000 | 1.4640 | 2.4260 | 2.0600 | 0.7304 | 0.0048 | 1.0909 |
| 10,000 | 16.5999 | 24.5715 | 20.2123 | 7.4663 | 0.0051 | 11.3312 |

V1 packet size grew from 9,320 to 780,622 bytes. Final v2 packet size remains
3,345 bytes at all three scales; complete evidence grows separately from 70,234
to 6,741,946 bytes. Catalog list reads one file, parses one YAML document, and
uses about 45 KB peak memory at every scale.

Final prepare performs exactly `N+1` evidence source reads/hashes, one discovery
pass, one accepted-proposal provider call, one vertical provider call, no schema
deep validation, and no quadratic work. A second edition performs no accepted/
vertical provider call and does not rebuild evidence. Prepare is intentionally
slower than v1 because v2 builds complete evidence rather than embedding a
partial export; status and list are materially faster.

Accepted residual: status and second-edition prepare still verify O(N) physical
source hashes. At 10,000 proposals, prepare peaked near 123 MB and second-edition
prepare near 172 MB. This is linear and structurally bounded, but remains a
future optimization candidate if real workspaces reach that scale.

## Verification Matrix

| Gate | Final result |
| --- | --- |
| focused publication/agent/provenance | 163 passed in 9.31 s |
| public CLI/MCP/docs | 262 passed, 1,184 deselected in 114.24 s |
| full source, default/C YAML, Python 3.14 | 1,446 passed in 254.46 s |
| full source, forced Python YAML, Python 3.14 | 1,446 passed in 424.23 s |
| real optional PDF tests, Python 3.14 | 4 passed |
| release/docs/script checks | 25 passed |
| installed wheel focused, Python 3.14 | 163 passed |
| installed sdist focused, Python 3.14 | 163 passed |
| installed wheel full, Python 3.11 | 1,443 passed, 3 PDF skips in 413.15 s |
| installed wheel full, forced Python YAML, Python 3.11 | 1,443 passed, 3 PDF skips in 480.77 s |
| installed sdist focused, Python 3.11 | 160 passed, 3 PDF skips in 11.37 s |
| wheel/sdist archive contract | version 0.4.1; 241/490 files |
| compileall and diff whitespace | passed |

Python 3.11 artifact imports resolved under `/tmp/wheel-env` and
`/tmp/sdist-env`, never repository `src`. The three skips are tests requiring
the intentionally uninstalled PDF extra; the PDF-capable Python 3.14 run passed.
The sole Python 3.11 warning was pytest's inability to write `.pytest_cache` in
the deliberately read-only `/repo` mount.

## Residual Risks And Classified Diagnostics

- Editorial quality remains partly semantic; deterministic validation cannot
  replace independent evaluation or owner review.
- Forward fixtures are representative but small and used one model family.
- Contribution prose was tested deterministically in English/Italian; blind
  curator fixtures intentionally used `contributions: omit`.
- Status and second-edition source hashing remain linear as recorded above.
- Codex evaluation runs emitted unrelated local plugin/model-cache warnings;
  they did not alter fixture outputs or product behavior.
- Python 3.11 omitted the optional PDF extra by design; installed-package PDF
  behavior is covered by missing-capability tests and real PDF output by the
  Python 3.14 environment.
- Existing live `.p2p` and `outputs` modifications predated this feature and
  remain unclassified owner/P2P work until M baseline inspection.

## Repository Side-Effect Audit

- `git diff --check` passed.
- Build/test/evaluation outputs stayed under `/tmp`.
- No live `.p2p`, generated adapter, or publication output was refreshed by
  implementation gates P..G.
- No workspace schema, package version, dependency declaration, release
  metadata, database, provider, tag, commit, push, or publication changed.
- Source reads and list/status tests remained byte-invariant unless their
  explicit write command was under test in an isolated fixture.

## M Repository Alignment Results

The owner confirmed the exact persistent-write preview on 2026-07-21:

- editions `project-en` and `project-it`, both with output name `project`;
- contribution policy `auto` for both editions;
- update every installed adapter (`generic`, `codex`, and `claude`);
- render both PDFs;
- leave review absent and `approved_for_publication: false`.

### Baseline And Invariance

M-T001 found runtime `0.4.1` compatible with `>=0.4.0,<0.5.0`, workspace
schema v3 aligned, no migration recovery, three clean installed adapters, a
complete legacy publication, and no v2 edition. The source fingerprint was
`cc52e887730dd3c6ca238574f9c0f06f74a139077084ac7799d0eaeb76f759b9`.

The final comparison preserved that source fingerprint and the exact baseline
hashes of all project contracts:

| Artifact | SHA-256 before and after |
| --- | --- |
| `.p2p/project/runtime.yml` | `8cf3cfcebbbed10055db6f7f509594da85098d3fd1fcb774a045443c3a2e29ec` |
| `.p2p/project/workspace-schema.yml` | `017eaf5a7b4fc8985deab6182307277019c33a62c07bc5460bbb496a87368acd` |
| `.p2p/project.yml` | `e746ddb592564d7d7b235bfbaca80759da8f254944c816cf736552b5dc99f938` |
| `.p2p/agent-policy.yml` | `34b23ceb84e659228023a28c3b35cf0b7c11f1345d8557ec871c9e2bb3383223` |

No proposal, decision, Change Set, Work, vertical definition, runtime contract,
workspace schema, or other canonical project content changed during M. The
expected managed configuration change is `.p2p/agent-integrations.yml`, which
now records the generated v2 curator resource set.

### Agent Alignment And Regression Fix

Supported `p2p agent update` commands updated `AGENTS.md`, `CLAUDE.md`, both
project skills, both curator skills, and created four curator references under
each Codex skill root. Final doctor results are clean for `generic`, `codex`,
and `claude`.

Sequential adapter updates exposed a registry defect: unchanged files owned by
another installed adapter were classified as `missing`. The preservation logic
now distinguishes absent, hash-drifted, and byte-identical files. A regression
test updates Codex and Claude sequentially and requires both doctors to remain
clean; `tests/test_agent_instructions_service.py` passes with 23 tests.

### Publication Preparation And Curation

The first v2 prepare archived the complete prior `outputs/latest` directory to
`outputs/review-014` and rebuilt `outputs/latest/project.md`. The Italian
prepare reused the same source export and the shared evidence index. The final
shared evidence has:

- 2,474 complete evidence entries and semantic hash
  `848d5959c20c86ebd3509cec4ee5caf4bc6d9f56632bbaa0d7987d163e455579`;
- 19 required `software_project` vertical sections;
- one advisory requiring explicit accounting of active cross-cutting evidence;
- one catalog containing the two confirmed editions.

The curator inspected and accounted for every evidence record in each edition.
Both models contain the same 13 project claims, ten reader questions, adaptive
outline roles, all 19 vertical coverage rows, exact contribution figures, and
rubric scores of at least four. Each accounting contains 2,474 unique records:

| Disposition | Count per edition |
| --- | ---: |
| used | 33 |
| supporting context | 1,049 |
| process only | 1,060 |
| historical | 52 |
| duplicate | 161 |
| insufficient | 118 |
| contradictory | 1 |

The English document contains 1,170 words; the Italian document contains 1,276
words. Both have one H1 and eleven H2 headings. Pre-import contract checks found
no missing heading, internal proposal/change/work/decision/event ID, managed
path, readiness score, source-of-truth boilerplate, or unrelated project brand.

### Imported Editions

Both imports and deterministic validations passed with no findings:

| Edition | Markdown SHA-256 | Model SHA-256 | Validation | PDF SHA-256 |
| --- | --- | --- | --- | --- |
| `project-en` | `1e77a384f42f546bbd671012351a6e99aa4a7d8fdea4266021ebd3ce293b1c9a` | `5bdaaf7b8608bb906622b62d4a9dec1d4da98beb758c71b122ffad11f7bb80f2` | passed, no findings | `e9a1816c28b2422cfb87a90a75dc9015e0cfdab4d461d36e37bd2c8383b471e1` |
| `project-it` | `fa22a892444b33b3950a8be0eee747dd4362c2e51120e6b7fa5217cf1565ad9b` | `8dee2e7a2beea8bc01f5cc355bd2f89162ce105b04e510ad2cfaab245107329e` | passed, no findings | `61b541e59054324f102fceaed78adccac1885d7690e625ee890f7bea8dd08bd4` |

WeasyPrint produced nonblank A4 PDFs titled `P2P Engine`: four pages in English
and five in Italian. Text extraction preserves the selected language and
Italian Unicode. Default-English aliases are exact byte copies of
`project-en.md` and `project-en.pdf`.

### Review And Residual Legacy State

Both edition manifests report source, evidence, profile, packet, model,
accounting, Markdown, validation, and render as current. Review is explicitly
`missing` for both editions and `approved_for_publication` remains false.

The legacy status is intentionally `partial`: the prior complete v1 packet,
profile, manifest, validation, Markdown, and PDF are preserved under
`outputs/review-014`; only the documented default-English Markdown/PDF aliases
exist in the new `outputs/latest`. No legacy review existed and no stale legacy
file was deleted.

Final `p2p validate` reports zero errors, warnings, or infos. Workspace schema
status remains aligned at v3, all installed adapter doctors are clean, and the
publication catalog has no diagnostics. M performed no release, commit, push,
network operation, runtime installation, schema migration, or publication
approval.

## Pre-Commit Review

The final repository review exposed one intermittent diagnostic race in the
existing schema-v3 proposal decision apply path. When a competing process had
already committed a different decision but its transaction cleanup was still
observable, the losing request could report workspace recovery instead of the
more specific concurrent-head error. The apply path now rechecks exact replay
and ledger head after that schema-gate condition: it returns an exact retry for
the same event, reports `P2P367_DECISION_CONCURRENT_HEAD` for a conflicting
winner, and preserves `P2P307_WORKSPACE_MIGRATION_RECOVERY_REQUIRED` when the
ledger does not prove a completed competing decision.

The deterministic regression and the original separate-process race test pass,
the complete proposal-decision service suite passes with 35 tests, and the
final source suite passes with `1448 passed` in 284.03 seconds. Compileall,
`git diff --check`, workspace validation, and publication status checks remain
part of the pre-commit gate.
