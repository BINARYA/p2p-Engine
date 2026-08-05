# Implementation - Typed Project Vertical Transition Impact

## Governance And Release

This implementation realizes accepted `PROP-001` and targets P2P Engine
`0.4.8`. The global CLI envelope remains `p2p-cli/v1`; the new domain contracts
are `p2p-vertical-transition-impact/v1` and
`p2p-vertical-transition-plan/v1`. Vertical mutation receipts advance to the
current-only schema `2`.

The immutable replacement baseline is tag `v0.4.7`, commit
`6bc23d2cac2af9f9a249bc2504e7e87331659226`. Its public behavior is captured in
`tests/fixtures/vertical_transition/legacy-0.4.7-characterization.json`.

## Source Ownership

Typed contracts are owned by:

- `core/vertical_transition_impact.py`: operation-specific impacts, domain
  references, issues, evidence dispositions and bounded collections;
- `core/vertical_transition_plan.py`: strict canonical plans, unique decisions
  and semantic fingerprints;
- `services/vertical_evidence_classifier.py`: the single immutable
  empty/populated evidence snapshot;
- `services/vertical_transition_analysis.py`: read-only structural, field,
  rubric, question, lock and artifact analysis;
- `services/vertical_transition_materialization.py`: explicit plan-driven
  candidate construction in the owning memory family;
- `services/vertical_lifecycle.py`: preview/apply orchestration, token binding
  and operation-specific semantic postconditions;
- `services/mutation_receipts.py`: strict schema-2 persistence, replay and safe
  status projection.

The generic 0.4.7 `_has_meaningful_evidence`, loose `_parse_mapping`, implicit
`_migrated_definition` and public generic preview-path projection are removed
from the vertical lifecycle. Current receipts reject old generic result shapes.

## Contract Behavior

Install, adoption and migration expose distinct typed impacts. Every material
collection is deterministic and bounded to 128 entries; analysis fails closed
when a collection exceeds 128 or total transition material exceeds 512.
Canonical plans contain at most 128 exact decisions. Receipt serialization is
limited to 65,536 bytes.

Classification includes meaningful `0` and `false`, assumptions, blockers,
existing definition orphans, owner question evidence and rubric customization
against the exact active lock baseline. Invalid definition, lock or rubric
artifacts fail with stable source-state diagnostics.

Migration is a two-preview workflow. The first blocked preview returns all
required decisions and no token. A complete current plan is validated for
analysis fingerprint, exact source, compatible target and exclusive target
ownership. The second preview binds contract, analysis, plan, actor, target,
profile, modules, sources and candidate semantics. Apply repeats the full
analysis before comparing the token.

Definition values, assumptions and blockers remain definition memory. Rubric
customization remains rubric memory. Owner question evidence remains question
memory. The mixed integration test proves all five decision kinds can be
mapped in one operation and that materialization reuses the exact question
candidate produced by analysis.

Install apply reports only installed-pack postconditions and does not claim to
activate it. Adoption and migration report active coordinate plus lock,
definition, question and rubric semantic postconditions. Internal receipts
retain physical paths/hashes for drift detection; apply, replay and mutation
status do not publish them.

## CLI, Agents And MCP

Registered install/adopt/migrate command paths and `p2p-cli/v1` operation IDs
are unchanged. `--mapping` now accepts only the canonical transition plan and
rejects duplicate YAML keys, old loose roots, unknown fields and stale hashes.
Text output contains counts, decisions, blockers and recovery guidance without
raw evidence or workspace paths.

Capability catalog version 3 and generated generic, Codex and Claude guidance
teach classify, preview, plan, re-preview, replacement token, apply and receipt
recovery. Vertical lifecycle mutation remains owner-governed CLI-only. No MCP
stdio mutation tool was added; WaveKit continues to orchestrate the CLI behind
its authenticated MCP HTTP surface.

## Fixtures And WaveKit Handoff

`tests/fixtures/vertical_transition/manifest-v1.json` binds engine, CLI,
impact, plan and receipt versions, limits and SHA-256 checksums for sanitized
install, adoption and migration preview/apply fixtures. Release verification
requires the typed runtime modules, fixtures, manifest and
`docs/development/wavekit-vertical-transition-handoff.md` in the sdist/wheel as
appropriate.

WaveKit can close its remaining `7.8` assertions from CLI JSON alone: exact
empty/populated routing and complete preservation/mapping decisions. WaveKit
retains authorization, preview expiry, queue concurrency, crash supervision,
audit persistence, post-apply product validation and user presentation.

## Verification Evidence

Final verification on 2026-08-05:

- focused transition/project/receipt/release matrix: `95 passed`;
- `./scripts/test-public.sh -q`: `277 passed, 1162 deselected`;
- release build: `p2p_engine-0.4.8-py3-none-any.whl` and
  `p2p_engine-0.4.8.tar.gz`;
- release artifact verifier: wheel `262` files, sdist `572` files;
- installed-wheel transition matrix: `45 passed`, importing from the isolated
  `/tmp` wheel target rather than the source checkout;
- installed-wheel smoke matrix: `16 passed, 1423 deselected`;
- `./scripts/test-full.sh -q`: `1439 passed` with no failures or skips;
- `git diff --check` and Python compilation completed without errors.

No release tag, commit or push is part of this implementation step.
