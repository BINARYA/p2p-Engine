# Execution Plan - Agent Persistence Boundaries And Proposal Authoring Flow

## Scope Lock

Semantic core:

- canonical proposal write surfaces;
- persistent write classes and preview rules;
- generated/imported/exported/stable/scratch/external artifact boundaries;
- deterministic logical proposal artifact status;
- owner-friendly full proposal view;
- compact agent request-routing playbook.

Operational core:

- explicit decision root independent from the current working directory;
- CLI and MCP runtime hints that include `--root`;
- generated instructions that help agents locate and use the governed P2P root.

Bootstrap UX scope:

- adaptive init default: `generic` plus detected current agent, with `all` fallback when detection is unavailable;
- visible integration lifecycle: list, install, update, doctor, refresh, uninstall.

Opportunistic hygiene scope:

- non-destructive `.gitignore` guard;
- init summary grouped by purpose.

Implementation must be additive and compatibility-preserving. Existing projects initialized by the current release remain valid, readable, and non-destructively upgradable.

## 093-A - Canonical Proposal Authoring

1. Update proposal create/scaffold/help guidance so the canonical flow is visible:
   structured contribution/question/choice input, synthesis/import, full review, owner decision.
2. Remove editable-looking narrative placeholders from new scaffolds, or mark generated narrative artifacts read-only with command hints.
3. Preserve existing narrative artifacts as legacy/generated/imported/readable evidence; do not delete or rename current files.
4. Align contribution and question primitives with rendered concepts such as finding, alternative, risk, constraint, objection, and open question using additive schema changes only.
5. Ensure generated instructions keep direct `.p2p/` file edits forbidden except explicit repair or supported CLI/MCP import/edit primitives.

Verification:

- scaffold/help tests cover canonical flow text;
- contribution/question tests cover additive types or equivalent categorized input;
- compatibility fixtures prove existing narrative files remain visible and valid.

## 093-B - Artifact Status And Owner View

1. Add or extend a deterministic logical proposal artifact catalog/status view.
2. Derive artifact status lazily for legacy proposals that lack new catalog metadata.
3. Represent physical-file differences as logical statuses such as satisfied, missing, optional, not applicable, deferred, generated, imported, or required when applicable.
4. Add an owner-friendly full proposal view through `proposal show --full`, `proposal render`, or an equivalent additive command/flag.
5. Include proposal text, contributions, narrative artifacts, digest, readiness, artifact coverage, and suggested next action in the full view.

Verification:

- artifact status tests prove proposal completeness does not depend on directory listings;
- legacy tests prove missing catalog metadata does not invalidate current-release proposals;
- CLI/MCP tests cover compact and full views without breaking existing default output.

## 093-C - Agent Persistence Policy

1. Update generated `AGENTS.md`, project skills, and shared policy with persistent write classes:
   `read_only`, `chat_only`, `local_scratch`, `p2p_canonical`, `p2p_generated_narrative`, `p2p_imported_artifact`, `generated_export`, `stable_documentation`, and `external_side_effect`.
2. Require action preview for meaningful persistent writes unless the owner explicitly requested the exact operation and artifact.
3. Make preview include operation, target path or P2P object, artifact kind, write class, canonical/derived status, reason, and reversibility or cleanup path when relevant.
4. Clarify that `stable_documentation` is a write class requiring preview and classification, not a claim that P2P governs every durable repository document.
5. Add a compact routing playbook to generated instructions and maintained docs. It should route chat-only exploration, project definition, proposals, choices, explicit vertical primitives such as the PROP-094 software-spec lifecycle, implementation work, exact file requests, generated exports, stable documentation, local scratch, and outside-P2P work.

Verification:

- agent template tests cover write classes, preview rule, stable-documentation caveat, direct `.p2p` boundary, and routing playbook;
- documentation checks prove the longer guide matches the generated short form without duplicating the full CLI guide.

## 093-D - Bootstrap And Integration Lifecycle

1. Implement adaptive init selection:
   always create `generic`; add detected current agent when reliable; fallback to `all` with warning when detection is unavailable.
2. Preserve explicit owner selection for one adapter, multiple adapters, and `all`.
3. Update init summaries and generated instructions to show:
   `p2p agent list`, `p2p agent install <adapter>`, `p2p agent update <adapter>`, `p2p agent doctor <adapter>`, `p2p agent uninstall <adapter>`, and `p2p agent instructions refresh --profile <adapter>`.
4. Keep integration refresh and uninstall non-destructive. Do not silently remove shared baseline files, unmanaged files, or drifted human-edited files. Never require manual edits to `.p2p/agent-integrations.yml`.

Verification:

- init tests cover detected-agent default, unknown-agent fallback to `all`, explicit adapter selection, explicit `all`, and integration lifecycle guidance;
- lifecycle tests cover install/update/doctor/uninstall, conservative removal, drift protection, shared baseline preservation, and registry consistency;
- compatibility tests prove existing adapter files remain after upgrade unless the owner runs safe lifecycle commands.

## 093-E - Root, MCP, And Hygiene Hardening

1. Update MCP hints to prefer project-local Python with `--root`, while keeping shorter `p2p-mcp-server` forms supported when available on `PATH`.
2. Document `--root` as explicit decision-root selection, not as a sibling-repository recommendation.
3. Ensure generated agent instructions explain how to find and use the governed P2P root when the current working directory differs.
4. Add non-destructive `.gitignore` handling for fresh projects or an explicit guided option.
5. Ignore `.venv/`, Python caches, test caches, build outputs, and local runtime noise.
6. Never overwrite user `.gitignore` content and never ignore `.p2p/`.
7. Keep repository hygiene independently releasable from root/MCP hardening when necessary.

Verification:

- MCP and docs tests prove `--root` is decision-root selection, not a topology recommendation;
- agent instruction tests cover decision-root discovery and root-aware MCP hints;
- gitignore tests prove append/offer behavior is non-destructive and keeps `.p2p/` trackable;
- init summary tests prove repository hygiene is grouped separately from governed P2P state and agent integrations.

## Cross-Slice Verification

- Current-release workspace fixtures remain loadable, valid, and renderable.
- Missing PROP-093 metadata, write-class labels, artifact-catalog files, or refreshed template hashes are treated as legacy-compatible state.
- Existing CLI/MCP output remains stable by default; richer behavior is additive through new commands, flags, summaries, or preferred-command documentation.
- `p2p validate` passes after implementation.
