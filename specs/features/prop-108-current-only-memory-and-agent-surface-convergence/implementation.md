# Implementation Note - PROP-108

## Scope

P2P Engine 0.4.7 exposes one current runtime and project-memory contract. The
implementation removes successful interpretation, mutation and recovery paths
whose only purpose was discarded state. Minimal recognition remains only where
it is needed to reject an unsupported version or shape without writes.

## Public And Agent Surfaces

- `services/public_surface_inventory.py` derives CLI leaves from the registered
  Typer app and MCP names from the server registry.
- `services/agent_capabilities.py` classifies standalone project, governance,
  local/remote vertical, draft and adoption workflows with authority and MCP
  omission reasons.
- Generic, Codex and Claude templates use generation v2 with capability catalog
  v2. Codex uses `.agents/skills/`; superseded `.codex/skills/` copies are not
  installed or retained.
- Managed file diagnosis reports content drift and template generation drift as
  independent axes. Read-only list/show/status/doctor/validation paths do not
  rewrite files.
- `docs/MCP.md` is checked against the exact MCP registry and generated template
  command/tool references are checked against registered surfaces.

## Current-Only Memory

Removed runtime entry points include workspace conversion, runtime adoption,
proposal artifact mark-legacy, proposal decision legacy resolution and the
`proposal_decision_legacy.py` adapter. Current-only convergence also removes
fallback authority from proposal questions, permissions, decision context,
registries, software-spec provenance, publication aliases, readiness and
derived freshness.

The exact authority, schema, readers/writers, public surfaces and rejected forms
for each family are recorded in `compatibility-inventory.md`. Vertical
install/adopt/migrate remains current domain behavior: it changes an active
vertical release and does not convert an obsolete P2P memory schema. Proposal
accept/reject/defer and `decision record` remain current convenience commands
over the same exact preview/apply ledger service.

## Documentation And Examples

README, install, CLI, MCP, agent integration and workspace schema guides agree
on 0.4.7 and the current-only contract. The old CLI and architecture snapshots
under `docs/development/` are explicitly historical and form the reviewed
allowlist.

Both checked-in examples were recreated with public 0.4.7 commands. They use
workspace schema 3, explicit runtime/permission/question state, current
vertical declarations, decision ledgers, verifiable registry manifests and
generation-v2 Codex skills. Each validates with zero findings.

## Verification

Automated closure is provided by:

- `tests/test_public_surface_inventory.py`;
- `tests/test_current_only_surface.py`;
- `tests/test_agent_instructions_service.py`;
- focused family rejection/current-flow tests;
- `tests/test_version_consistency.py`;
- `scripts/verify-release-artifacts.py` for wheel/sdist membership and discarded
  runtime token rejection.

Phase 8 evidence:

- focused surface, adapter, documentation, release and family tests: `107
  passed`; final archive/release closure selection: `25 passed`;
- complete suite: `1424 passed` in 281.70 seconds;
- release build: `p2p_engine-0.4.7-py3-none-any.whl` and
  `p2p_engine-0.4.7.tar.gz`;
- archive verification: 257 wheel members and 551 sdist members;
- isolated wheel: version reports engine 0.4.7, CLI contract `p2p-cli/v1`,
  workspace schema 3, vertical schema 2 and package format 1;
- source/wheel capability hash, public-surface hash, generation identity and
  rendered generic/Codex/Claude file hashes are identical;
- wheel-created project: Codex and Claude doctor health `clean`; validation has
  zero findings after explicit registry refresh.

## Canonical Project Archive

Before any destructive operation, `scripts/archive-project-state.py` captured
the complete canonical project repository and a read-only semantic inventory:

- archive: `/tmp/p2p-engine-project-pre-0.4.7-20260804.tar.gz`;
- inventory: `/tmp/p2p-engine-project-pre-0.4.7-20260804.inventory.json`;
- archive SHA-256:
  `e63cb5eeeab792e51adb6c2edc12bee262c6003ca9eb0dae3101294fafe50a4f`;
- 5,773 files with manifest SHA-256
  `a99867fc45bae849ec12a2046b160ceb23b3e594dc96933caf11d6e6a88c3373`;
- 108 proposals, one choice, 70 Change Sets and four Work records;
- active vertical `binarya/software_project@2.0.0`;
- pre-recreation validation captured with exit code 1 because the archived
  workspace contains the intentionally discarded migration and legacy memory
  forms.

The archive tool is deliberately not a converter. It preserves full recovery
evidence and records project, vertical, definition, proposal decision heads,
choices, Change Sets, Work, validation and a per-file content manifest.

## Canonical Project Recreation

The owner explicitly confirmed recreation after reviewing the archive scope.
The release-candidate wheel was installed with its declared dependencies under
`/tmp/p2p-047-rc2-20260804`; its public version response reports engine 0.4.7,
CLI contract `p2p-cli/v1`, workspace schema 3, vertical schema 2 and package
format 1.

The canonical repository was recreated through public 0.4.7 commands while
preserving `projects/p2p-engine-project/.git`. The displaced working tree is
also available at
`/tmp/p2p-engine-project-pre-0.4.7-working-tree-20260804`. Initialization used
owner `mrjungle`, `software_project@2.0.0`, and explicit generic, Codex, Claude,
Cursor, Copilot and Gemini adapters. A subsequent public `agent update all`
also installed the current OpenCode adapter. The project remote profile was
corrected from the implementation repository URL to its own Git remote,
`git@github.com:BINARYA/p2p-engine-project.git`.

A single owner-previewed and owner-confirmed definition patch re-established
the current product direction without direct `.p2p` editing. It preserves all
19 software-project sections and 27 populated fields. The 14 initialization
questions were answered, previewed and applied through the owner-governed
readiness workflow; a final owner-confirmed patch marked the now-explicit
assumptions section complete. All 19 sections are complete, definition
completeness is 100%, no caposaldo is missing and no question remains
`to_answer`. Declared proposal evidence is intentionally 0% because archived
proposal authority was not copied into the new current contract.

The following archived history was deliberately omitted from the recreated
canonical state:

- 108 proposals and their historical decision heads;
- one choice;
- 70 Change Sets;
- four Work records;
- migration history and every unsupported family-specific compatibility form;
- old optional briefs, specifications, publications and other derived output.

Current vertical memory, project projections, registries, assessment, brief
prompt, maturity assessment and visible project export were regenerated through
public commands. Optional curated outputs remain absent until a future governed
workflow creates them. The post-recreation evidence is:

- archive: `/tmp/p2p-engine-project-post-0.4.7-final-20260804.tar.gz`;
- inventory:
  `/tmp/p2p-engine-project-post-0.4.7-final-20260804.inventory.json`;
- archive SHA-256:
  `c1230b747edaf8546439dd08d7e773bbc4cdc54d8ad5ca5f2ab5b7ecb295be6b`;
- 2,675 files with manifest SHA-256
  `13e8b59e6064ced34eaeb3422752c24b8e92f8785c9da2a7900212a777125858`;
- workspace baseline `initialized_current`, exact active coordinate
  `binarya/software_project@2.0.0`, and zero proposals, choices, Change Sets or
  Work records;
- final validation: zero errors, warnings, infos or findings;
- all seven installed agent integrations: clean content and generation state;
- no superseded `.codex/skills` tree and no discarded runtime token in current
  generated project state.
