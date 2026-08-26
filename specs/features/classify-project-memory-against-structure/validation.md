# Validation - Classify Project Memory Against Structure

Validated on 2026-08-26 with local Python 3.14.4.

## Completed Checks

- Focused project-memory, decision, publication and installed-smoke tests:
  `89 passed`.
- Focused MCP registry, public inventory, agent guidance, CLI contract and
  release-artifact tests: `75 passed`.
- Public CLI/MCP contract suite: `287 passed`, `1309 deselected`.
- Full suite: `1596 passed`.
- Source and wheel distributions built with
  `python -m build --no-isolation`.
- Release artifacts verified: wheel `323` members, sdist `662` members.
- The final `p2p_engine-0.4.11-py3-none-any.whl` was installed into an isolated
  target and imported from that target's `site-packages` path.
- Installed-wheel smoke suite: `20 passed`, `1576 deselected`.
- Source compilation and `git diff --check` completed without errors.

## Contract Evidence

- Proposal creation persists explicit unassigned scope and its event ledger,
  including in a zero-section project. Missing or divergent scope state is
  `unknown`; it is never inferred as project-global or normalized from an old
  artifact.
- One receipt-backed mutation assigns multiple active sections,
  `project_global` or `unassigned`, bound to expected memory and structure
  revisions. Exact replay, divergent key reuse, response loss, rollback and
  concurrent structure changes are covered.
- Authority-creating decision previews and applies bind scope, scope-event
  ledger and canonical structure as atomic source preconditions. Unassigned,
  retired, unknown or concurrently changed scope cannot create authority.
- Classification is deterministic, bounded and separately identifies active,
  historical, global, unassigned, reassignment and unknown memory. Formal
  questions use their existing structure reference; proposal-local questions,
  contributions, evidence and artifacts inherit proposal scope.
- Project snapshots and publication evidence preserve explicit classification
  and scope kinds. Classification changes do not alter project readiness.
- CLI and MCP share the same scope/classification services. MCP mutation is
  consent-gated, and sanitized golden payloads guard the public contract.
- `project.memory.classify`, `proposal.decide` and
  `proposal.readiness.override` remain separate typed capabilities and cannot
  authorize one another implicitly.

## Ordered Convergence Note

The pre-rebase `vertical_coverage` reader remains temporarily available to the
existing readiness/publication implementation, but it is not scope authority,
cannot satisfy classification and cannot pass the decision gate. Its removal
belongs to the already ordered `rebase-readiness-on-project-structure` feature.
This is an internal sequencing dependency, not support for an obsolete memory
schema.

## Release Matrix Gate

Python 3.11 is not installed in the local environment. The release workflow
retains mandatory Python 3.11 and Python 3.14 execution. The package version
remains `0.4.11` while the ordered convergence features are implemented; the
planned release train advances to `0.5.0` after that sequence is complete.
