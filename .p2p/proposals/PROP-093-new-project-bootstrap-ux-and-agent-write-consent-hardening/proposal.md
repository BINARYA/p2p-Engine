# PROP-093 - Agent Persistence Boundaries And Proposal Authoring Flow

## Status

`accepted`

## Problem

Real new-project and external-agent tests showed that P2P Engine installs and works, and that agents can use it to capture project reasoning as structured state. That early use of P2P is desirable.

The problem is not that agents use P2P too soon. The problem is that P2P currently gives agents and owners some ambiguous signals about persistent writes and proposal authoring.

An agent can create or modify durable project knowledge without first showing the owner exactly what will become persistent state. A second, deeper ambiguity is inside the proposal workspace itself: P2P scaffolds narrative markdown files such as `alternatives.md`, `findings.md`, and `open-questions.md`, while generated instructions also say not to edit `.p2p/` by hand. If the canonical input is structured contribution or question state, those markdown placeholders look like editable files but are not the right write interface.

A related ambiguity is the physical shape of proposal directories. Different workflows can materialize different files for valid reasons: one proposal may have conflict analysis or related-proposal artifacts, while another may not. That can make the CLI feel non-deterministic if owners or agents infer proposal completeness from `ls`. The deterministic surface should be a CLI/MCP-visible logical artifact schema, not a requirement that every proposal directory contains every possible file.

The feedback also shows a documentation gap. P2P already has README, concepts, CLI, MCP, and agent-integration documentation, but agents still need a compact operational routing guide that answers: what is P2P for, when should an agent stay in chat, when should it create or update P2P state, when should it use project definition, when should it create proposals or choices, when should it defer to an explicit vertical primitive such as the PROP-094 software-spec lifecycle, and when is a requested file outside P2P governance.

The new-project bootstrap issue needs a more precise direction than simply changing the default from broad to narrow. A broad default creates noise when every adapter is generated without owner intent. A narrow default creates a different failure mode when the owner later opens the same project with Claude, Cursor, Copilot, Gemini, OpenCode, or another supported agent and cannot easily discover how to add that integration.

The result is predictable: a capable agent may duplicate content, write directly under `.p2p/`, create external project documents, jump to a spec file, judge proposal completeness from filesystem shape, or fail to onboard a second agent because the engine does not make the canonical authoring flow, artifact status model, agent request-routing model, and integration lifecycle obvious enough.

The core product issue is therefore:

- persistent agent writes are not classified and previewed clearly enough;
- canonical P2P inputs and generated narrative artifacts are not visually and operationally distinct enough;
- proposal artifact status is not exposed as a deterministic logical catalog independent of physical file materialization;
- agents lack a concise operational playbook that maps owner requests to the correct P2P route;
- the proposal authoring flow is not discoverable enough from help text, scaffold output, and owner-facing views;
- agent integration bootstrap is too broad today, but a narrow default would be unsafe unless add/remove lifecycle commands are visible from init summaries and generated instructions;
- P2P's decision root must be explicit and robust, but this must not be misread as an endorsement of any specific repository topology such as sibling specification repositories.

## Context

A v0.1.9 new-project test installed the release wheel into a fresh project-local virtualenv, ran guided init, selected the `software` domain template, accepted the default `all` agent profile, accepted the MCP hint, and registered a Codex MCP server. Init produced the expected P2P files and agent adapters.

During follow-up design work, the agent created a preliminary project document, created a P2P proposal, initialized readiness, initialized question state, and generated vertical material. The P2P state creation was aligned with P2P's purpose, but the agent did not preview the persistent write set clearly before creating durable artifacts.

Later real-world feedback showed a second issue. In a project where P2P was used from an AI-assisted workflow, the agent eventually used the CLI and MCP successfully, but it was also tempted to edit generated proposal markdown under `.p2p/` directly. The scaffold made narrative artifacts look like the place to write, while the correct flow was structured input followed by synthesis/import.

Comparison between recent proposals showed a third issue: proposal directories do not always contain the same physical files. That is acceptable when files are materialized only by relevant workflows, but it is not acceptable for artifact coverage and completeness to be understood only by inspecting directory contents.

Reviewing the current documentation showed that the basic pieces exist, especially `README.md`, `docs/CONCEPTS.md`, `docs/CLI-GUIDE.md`, `docs/MCP.md`, and `docs/AGENT-INTEGRATION.md`. The missing piece is not another long manual. The missing piece is an agent-facing operational playbook that is short enough to embed in generated instructions and concrete enough to guide behavior during real sessions.

Current docs and CLI already expose agent lifecycle commands such as `p2p agent list`, `p2p agent install <adapter>`, `p2p agent update <adapter>`, `p2p agent doctor <adapter>`, `p2p agent uninstall <adapter>`, and `p2p agent instructions refresh --profile <adapter>`. The issue is that this lifecycle is not visible enough in the bootstrap path and generated project instructions, especially if the default no longer materializes every adapter file.

This feedback is not evidence that P2P should promote sibling repositories or external specification directories as a product model. It is evidence that P2P must support an explicit decision root independent of the current working directory, and must make its write interfaces, artifact status model, agent request-routing model, and integration lifecycle unambiguous wherever the decision root lives.

## Goals

- Make every meaningful persistent agent write classified, owner-visible, and tied to a P2P primitive or policy.
- Make canonical P2P state, structured proposal inputs, generated narrative artifacts, generated exports, stable documentation, scratch files, and external side effects distinct.
- Expose a deterministic proposal artifact schema independent of physical file materialization.
- Provide a compact agent-operational playbook that maps common owner requests to the correct P2P route.
- Prevent agents from treating scaffolded narrative markdown under `.p2p/` as a manual editing surface.
- Make proposal authoring discoverable: structured inputs first, then synthesis/import, then owner review and decision.
- Align contribution primitives with narrative artifacts, or stop scaffolding narrative placeholders that cannot be populated through supported commands.
- Provide an owner-friendly full proposal view so humans do not need to inspect internal proposal files manually.
- Make `p2p init` deterministic, adaptive, and explicit about which agent integrations were created and why.
- Preserve compatibility when the current agent cannot be reliably detected by falling back to the existing broad adapter setup with a concise warning.
- Make add/remove/update/doctor lifecycle commands for agent integrations visible in init summaries, generated instructions, and docs.
- Make runtime and MCP setup robust when the P2P decision root differs from the current working directory.
- Avoid codifying local repository topology choices, including sibling repositories, as official P2P product direction.

## Non-Goals

- Do not discourage agents from creating P2P proposals, readiness artifacts, question state, choices, contributions, imports, or generated P2P artifacts when useful.
- Do not force project reasoning to stay in chat.
- Do not make P2P Engine less proactive.
- Do not require every proposal directory to contain every possible artifact file.
- Do not create empty placeholder files only to make proposal directories look uniform.
- Do not make a long prose manual the primary agent control surface.
- Do not duplicate the full CLI guide inside generated agent instructions.
- Do not make agent routing so rigid that owner intent and explicit owner instructions are ignored.
- Do not remove support for all built-in agent adapters.
- Do not automatically remove existing adapter files from upgraded projects just because the new init default is adaptive.
- Do not require users to manually edit `.p2p/agent-integrations.yml` or delete generated agent files by hand.
- Do not invalidate projects generated by the current release merely because they lack new PROP-093 metadata, generated instructions, artifact-catalog state, or write-class labels.
- Do not define or recommend a sibling repository model.
- Do not require users to separate specification repositories from implementation repositories.
- Do not solve the software specification lifecycle in this proposal; that belongs to PROP-094 and the software vertical.
- Do not define file names such as `tech-stack.md`, `substrate.md`, or `phase0.md` as core P2P concepts.
- Do not implement MCP HTTP, hosted service deployment, or remove local-first CLI/filesystem-backed operation in this proposal.
- Do not implement remote MCP permissions, WaveKit hosted permissions, cloud collaboration authorization, or provider PR automation.
- Do not change owner authority over governance decisions.
- Do not require a full external artifact registry in the first implementation slice.

## Core Principles

### Scope hierarchy and scope lock

PROP-093 has a semantic core, an operational core, a bootstrap UX scope, and an opportunistic hygiene scope. This hierarchy is part of the proposal and should guide implementation ordering.

Semantic core:

- canonical write surfaces;
- persistent write classes and action preview;
- generated, imported, exported, stable, scratch, and external artifact boundaries;
- proposal authoring flow;
- logical proposal artifact status independent from physical file materialization;
- owner-friendly full proposal view;
- agent operational routing playbook.

Operational core:

- explicit decision root independent from the current working directory;
- robust CLI and MCP runtime hints that include the decision root;
- generated instructions that tell agents how to find and use the P2P root.

Bootstrap UX scope:

- adaptive agent integration default;
- visible integration lifecycle for add, update, doctor, refresh, and uninstall.

Opportunistic hygiene scope:

- non-destructive `.gitignore` guard for fresh projects;
- grouped init summary by purpose.

The proposal can be accepted as one product direction, but implementation should be split into additive slices rather than one large Change Set:

- 093-A: canonical proposal authoring;
- 093-B: artifact status and owner view;
- 093-C: agent persistence policy;
- 093-D: bootstrap and integration lifecycle;
- 093-E: root, MCP, and hygiene hardening.

The semantic and operational core should not be delayed by optional hygiene work, and bootstrap work should not redefine P2P's core model. MCP and `--root` hardening are not mere hygiene: they make the semantic core usable by agents in real workspaces.

### Explicit decision root, not repository topology

P2P has a decision root: the project root containing the governed `.p2p/` state. That root must be explicit and robust through CLI `--root`, MCP server configuration, generated hints, and agent instructions.

This is not the same as endorsing a sibling repository or any other repository layout. Same-repo, monorepo, mounted workspace, container, and separate checkout layouts are local deployment choices. P2P's core obligation is to make the decision root unambiguous.

### P2P write interface, not filesystem interface

Governed P2P state must be mutated through supported P2P write primitives, not through direct filesystem mutation.

In local mode, those primitives are exposed through the CLI and local MCP. In remote or HTTP MCP mode, they may be exposed through MCP HTTP or equivalent service APIs. The semantic contract is the same: typed write primitives, explicit canonical sources, generated or exported artifact boundaries, previewable persistent writes, and owner-readable artifact status.

The filesystem, when present, may remain the backing store, a compatibility surface, an import source, a generated export target, or a human-readable projection. It is not the normal agent write interface for governed P2P state.

### Canonical inputs before generated narrative

Structured P2P state is the canonical write surface. Proposal contributions, questions, choices, decisions, Change Sets, imports, and explicit vertical primitives are the supported way to mutate governed state. Domain artifacts are governed by P2P only when they are managed by an explicit P2P vertical, import primitive, export primitive, or cataloged artifact contract.

Narrative markdown artifacts under `.p2p/` are either generated artifacts, imported artifacts, or legacy-readable artifacts. They must not look like manual editing surfaces unless the engine explicitly provides a safe import or edit primitive for them.

### Deterministic artifact schema, controlled materialization

Every proposal should expose a stable logical artifact catalog. The catalog lists standard and applicable vertical-specific artifact slots with their expectation and status, for example `required`, `required_when_applicable`, `optional`, `generated`, `not_applicable`, `missing`, `satisfied`, or `deferred`.

Physical files should be created only when content exists, a workflow or import command produced them, or a generated artifact is needed. Empty files should not be created solely to make proposal directories uniform.

Proposal completeness must be read from CLI/MCP artifact state and owner-facing rendered views, not inferred from directory listings.

### Agent request routing before persistence

Agents need a short routing model before they choose a persistent write. The playbook should explain that P2P is the governed memory and decision layer for project intent, not a generic note folder, not a free-form spec repository, and not a replacement for owner decisions.

The playbook should map common owner intents to the default route:

| Owner intent | Default agent route | Persistence stance |
| --- | --- | --- |
| "Let's think" or "help me understand" | Discuss in chat, identify whether there is a P2P-worthy decision | No write unless requested |
| "Define the project" | Use project definition, vertical rubrics, focused questions, and proposals | P2P canonical state when persisted |
| "Create or refine a proposal" | Create/update proposal, contributions, questions, readiness | P2P canonical/imported state |
| "Compare options" | Use choices, alternatives, findings, risks, or proposal contributions | P2P canonical/imported state |
| "Write specs" in a software project | Follow the software vertical and PROP-094 lifecycle | Spec artifact is downstream unless explicitly provisional |
| "Implement this" | Inspect accepted proposals, decisions, Change Sets, and local development specs | Use Change Set/work/spec layer as applicable |
| "Create this exact file" | Preview path, write class, governance status, and reversibility | Stable docs, export, scratch, or outside P2P |
| "Do this outside P2P" | Respect the boundary and state that result is not P2P-governed | Outside P2P unless later imported |

This routing guide should be visible in generated agent instructions and maintained documentation, and should be concise enough for agents to follow during every session.

### Adaptive agent bootstrap and reversible integration lifecycle

`p2p init` should always install the `generic` baseline. When the current agent can be reliably detected, init should add the detected adapter by default. When no supported current agent can be detected, init should preserve backward-compatible usability by defaulting to `all` with a concise warning about the file footprint.

Explicit owner choices override detection. Users should be able to request a specific adapter, multiple adapters, or `all`.

Adding and removing integrations must be first-class lifecycle operations, not manual file edits:

```bash
p2p agent list
p2p agent install <adapter>
p2p agent update <adapter>
p2p agent doctor <adapter>
p2p agent uninstall <adapter>
p2p agent instructions refresh --profile <adapter>
```

Removal must be conservative: do not remove shared baseline files, do not remove unmanaged or drifted human-edited files silently, and never require manual edits to `.p2p/agent-integrations.yml`.

### Backward compatibility and migration guardrails

The implementation must not break projects initialized with the current release. PROP-093 may change defaults for new workflows and agent behavior, but existing `.p2p/` workspaces must remain readable, valid, and recoverable.

The compatibility guardrails are:

1. Existing workspaces remain valid.

   Older `.p2p/` layouts, registries, proposals, readiness files, generated instructions, and agent integration registries must continue to load. `p2p validate` must not fail only because a workspace lacks new optional metadata introduced by this proposal.

2. Init default changes affect new initialization only.

   Adaptive init applies to fresh `p2p init` runs. Upgraded projects must keep their installed adapter set until the owner explicitly installs, updates, refreshes, or uninstalls integrations. Unknown-agent fallback to `all` preserves current-release usability.

3. Agent instruction refresh is non-destructive.

   Existing `AGENTS.md`, `CLAUDE.md`, Codex skills, Cursor rules, Copilot instructions, Gemini files, and OpenCode shared consumers must not be overwritten silently. Drifted, unmanaged, or human-edited files should produce doctor/update guidance, not destructive replacement.

4. New write-class metadata is optional on read.

   Workspaces without `read_only`, `p2p_canonical`, `p2p_generated_narrative`, `generated_export`, or similar classifications must be interpreted through safe defaults such as `legacy`, `unknown`, or inferred class. Missing write-class fields must not invalidate old state.

5. Action preview is an agent policy, not a hard CLI compatibility break.

   Agents should preview meaningful persistent writes, but existing CLI/MCP write commands should not become unusable solely because an old workflow did not produce a preview artifact. Exact owner requests may still proceed under the policy exception.

6. Existing narrative proposal files are preserved.

   Existing `findings.md`, `alternatives.md`, `open-questions.md`, `risks.md`, `conflict-analysis.yml`, related-proposal files, or other proposal-local artifacts must not be deleted, renamed, or ignored destructively. They may be marked as legacy, generated, imported, or readable evidence while new scaffolds follow the clarified policy.

7. Artifact catalog is derived lazily.

   If a proposal lacks new artifact-catalog state, the CLI/MCP view should derive a logical catalog from existing files and known workflow state. Missing catalog files must not make older proposals invalid.

8. Contribution and question model changes are additive.

   New contribution/question types such as `finding`, `alternative`, `risk`, `constraint`, `objection`, or `open_question` must be added without renaming or removing existing accepted values. Renderers and MCP payloads should map legacy content forward where possible.

9. Existing CLI/MCP output contracts stay stable by default.

   Existing commands such as `p2p proposal show PROP-XXX`, current MCP setup forms such as `p2p-mcp-server`, and existing agent lifecycle commands must remain supported. Richer behavior should be additive through new flags, new commands, clearer summaries, or documented preferred commands.

10. Repository hygiene and adapter removal are non-destructive.

   `.gitignore` changes must be appended or offered safely, never overwrite user policy, and never ignore `.p2p/`. Agent uninstall must remove only safe, managed, unchanged, non-shared files and must never require manual edits to `.p2p/agent-integrations.yml`.

### Persistent write preview

Agents may analyze freely. Before meaningful persistent writes, the agent must preview:

- operation;
- target path or P2P object;
- artifact kind;
- write class;
- canonical source or derived status;
- reason;
- reversibility or cleanup path when relevant.

The preview may be skipped only when the owner explicitly requested the exact operation and artifact.

`stable_documentation` is a write class, not a claim that all stable project documentation is governed P2P state. P2P should require agents to preview and classify durable documentation writes, but only canonical P2P state and explicitly declared generated, imported, exported, or vertical-managed artifacts are governed by P2P. Ordinary repository documentation remains outside P2P governance unless the owner or a P2P primitive explicitly imports or catalogs it.

## Proposal

Implement a core hardening pass with eleven coordinated changes.

1. Agent action preview before meaningful persistent writes.

   Generated `AGENTS.md`, project skills, and shared policy should require action preview before meaningful persistent writes unless the owner explicitly requested the exact operation and artifact.

   Examples include creating a proposal, adding a contribution, importing exploration or synthesis output, initializing readiness, initializing questions, creating generated exports, writing stable documentation, or performing external side effects.

2. Persistent write classes.

   Generated policy should distinguish at least these classes: `read_only`, `chat_only`, `local_scratch`, `p2p_canonical`, `p2p_generated_narrative`, `p2p_imported_artifact`, `generated_export`, `stable_documentation`, and `external_side_effect`.

   Preview should be mandatory for `p2p_canonical`, `p2p_imported_artifact`, `generated_export`, `stable_documentation`, and `external_side_effect` writes unless the owner request is explicit and unambiguous.

   `stable_documentation` means durable documentation that should be previewed and classified before writing. It does not mean P2P owns every stable documentation file in the repository.

3. Agent operational playbook and request routing.

   Generated agent instructions, project skills, and `docs/AGENT-INTEGRATION.md` or an equivalent guide should include a compact playbook that explains what P2P Engine is for and how agents should route common owner requests.

   The playbook should distinguish chat-only exploration, project definition, proposals, choices, explicit vertical primitives such as the software-spec lifecycle defined by PROP-094, implementation work, generated exports, stable documentation, local scratch, and explicit outside-P2P work. It should be brief enough to embed in generated agent files and concrete enough to prevent agents from jumping directly to unmanaged documents.

4. Proposal authoring canonicality.

   The proposal workflow should clearly identify canonical write surfaces. If alternatives, findings, risks, objections, constraints, or open questions are meant to feed proposal synthesis, there must be supported structured primitives or import workflows for them.

   If `contributions.yml` or structured question state is canonical, scaffolded markdown files must not invite manual edits. They should either:

   - not be created until real content exists;
   - be marked as generated/read-only with a clear header and command hints;
   - or be editable only through an explicit CLI/MCP import primitive.

5. Deterministic artifact catalog and controlled materialization.

   P2P should expose a stable proposal artifact catalog through CLI and MCP surfaces. The catalog should list all standard artifact slots and any applicable vertical or feature-specific slots, with expectation and status metadata.

   Physical files may differ between proposals because different workflows have run. That difference is acceptable only when the logical catalog makes the state explicit: satisfied, missing, not applicable, deferred, optional, generated, imported, or required when applicable.

   P2P should not create empty placeholder files solely to make every proposal directory look identical. File presence is an implementation detail; artifact status is the source of truth.

6. Contribution and question type alignment.

   Contribution types should align with the narrative artifacts P2P exposes. If P2P creates or renders `findings.md`, `alternatives.md`, `risks.md`, or `open-questions.md`, the CLI/MCP surface should provide write-safe ways to add corresponding material, such as `finding`, `open_question`, `alternative`, `risk`, `constraint`, and `objection`, or an equivalent explicit import path.

7. Discoverable proposal flow.

   Proposal help text, scaffold output, and post-create guidance should show the typical flow:

   1. add structured inputs with contribution/question/choice commands;
   2. generate or request synthesis;
   3. import synthesized narrative;
   4. inspect a full proposal view;
   5. let the owner accept, reject, or defer.

   The guidance must not suggest editing `.p2p/` files directly.

8. Owner-friendly full proposal view.

   P2P should provide an owner-readable consolidated proposal view, such as `p2p proposal show PROP-XXX --full` or `p2p proposal render PROP-XXX`.

   The full view should include proposal metadata, decision status, problem, proposal, contributions, alternatives, findings, open questions, risks, objections where available, digest, readiness summary, artifact coverage, and suggested next action.

9. Adaptive init default, integration lifecycle guidance, and clearer init summary.

   Guided init should no longer silently optimize for all adapters when the current agent is known. It should always create the `generic` baseline, then add the reliably detected current agent by default. If no supported current agent can be detected, init should default to `all` for backward-compatible cross-agent usability and print a concise warning that this creates files for all built-in adapters.

   Explicit owner choices remain supported:

   ```bash
   p2p init "My Project" --agent claude
   p2p init "My Project" --agent codex --agent claude
   p2p init "My Project" --agent all
   ```

   After init, the CLI should group created files by purpose: P2P-governed state, generated policy/instructions, project rubric/permissions, optional agent integrations, repository hygiene, MCP setup hint, and next actions.

   The init summary and generated `AGENTS.md` should also show how to manage additional integrations later:

   ```bash
   p2p agent list
   p2p agent install <adapter>
   p2p agent update <adapter>
   p2p agent doctor <adapter>
   p2p agent uninstall <adapter>
   p2p agent instructions refresh --profile <adapter>
   ```

   Removal should be documented as conservative: it may remove only safe, managed, unchanged, non-shared files. The generic baseline remains installed and shared files must not be removed silently.

10. Repository hygiene guard.

   New projects should receive safe `.gitignore` protection or an explicit guided option. The implementation must not overwrite existing user content. It should ignore `.venv/`, Python caches, test caches, build outputs, and local runtime noise, while keeping `.p2p/` trackable.

11. Robust decision-root and MCP hints.

   Generated MCP and CLI hints should prefer robust commands that make the P2P decision root explicit. For project-local installs, the hint should prefer:

   ```bash
   codex mcp add p2p-<project-slug> -- \
     /path/to/project/.venv/bin/python \
     -m p2p_engine.mcp.server \
     --root /path/to/project
   ```

   The shorter `p2p-mcp-server` form can remain documented for users who have it on `PATH`.

   Docs may mention that `--root` lets P2P operate from a current working directory different from the decision root, but they must not present sibling repositories as a recommended architecture.

## Alternatives

- Keep current behavior and document it better. This is smallest but leaves contradictory affordances in place.
- Change the default to a strict minimal profile. This reduces file footprint but creates an onboarding failure for unsupported or undetected agents unless add/remove guidance is very strong.
- Detect the current agent and fall back to `all` when detection is unavailable. This is the recommended direction because it reduces noise when possible while preserving compatibility and cross-agent usability when detection cannot be trusted.
- Add only action-preview rules to agent templates. This improves consent but does not fix canonical authoring ambiguity.
- Document the playbook only in long-form docs. This helps humans but does not reliably reach agents during first-run sessions.
- Embed a compact routing playbook in generated agent instructions and maintain the longer explanation in docs. This is the recommended direction.
- Require every proposal directory to contain every possible artifact file. This makes `ls` look uniform but creates empty placeholders, manual-edit temptation, and false signal about what is actually applicable.
- Add a deterministic logical artifact catalog while materializing files only when needed. This preserves determinism without creating empty editable-looking artifacts.
- Remove narrative markdown scaffold files until generated content exists. This is clean but may reduce transparency for users who inspect files directly.
- Keep narrative placeholders but mark them generated/read-only with command hints. This preserves discoverability while reducing manual-edit risk.
- Add missing contribution types and keep the current scaffold. This aligns inputs with outputs but still needs clear generated-file boundaries.
- Implement only a full proposal view. This helps owners but does not stop agents from writing the wrong files.
- Treat sibling repositories as an official model. This is rejected because it confuses a local deployment topology with the core P2P concept of an explicit decision root.

## Impacts

- CLI: adaptive init detection, unknown-agent fallback to `all`, post-init summaries, agent lifecycle guidance, proposal help, contribution types, proposal full view/render, artifact catalog/status view, artifact import guidance, MCP hint printing.
- P2P memory model: clearer distinction between canonical state, logical artifact slots, generated narrative, imported artifacts, exports, stable docs, scratch, outside-P2P work, agent integration state, legacy state, and external side effects.
- Services: project initialization, agent detection, agent instruction generation, safe integration install/update/uninstall, proposal authoring/rendering, artifact state/catalog, compatibility adapters, contribution handling, and possibly import services.
- Agent templates: write-class/action-preview rules, no direct `.p2p/` edits, canonical proposal authoring flow, compact request-routing playbook, and integration lifecycle commands.
- MCP: parity for artifact catalog/status views and any new write-safe contribution/import/render operations where applicable.
- Documentation: install guide, MCP setup, agent integration lifecycle, proposal authoring flow, artifact canonicality, generated-file policy, artifact catalog semantics, decision-root usage, and an agent-operational playbook.
- Tests: CLI init tests, agent detection/fallback tests, agent install/update/uninstall guidance tests, agent template tests, playbook text tests, proposal help/scaffold tests, artifact catalog/status tests, contribution type tests, generated-file marker tests, proposal full-view tests, MCP parity tests where applicable.
- User workflow: first-run setup, later agent onboarding, proposal authoring, owner review, and agent-mediated project design conversations become less ambiguous.

## Risks

- Broadening from bootstrap to authoring flow increases implementation scope.
- Compatibility mistakes could break projects initialized by the current release; implementation must include migration and legacy-fixture tests before release.
- Agent detection can be wrong or unavailable; wrong detection creates missing adapter files, while unknown fallback to `all` preserves compatibility at the cost of file footprint.
- Falling back to `all` means the noise problem is not fully eliminated for unknown clients, so the warning and summary must be clear.
- Adapter removal can be risky if it deletes shared files or human edits; uninstall must remain conservative and registry-driven.
- Marking narrative files as generated/read-only may disrupt users who have been manually editing them.
- Adding contribution types without a clear rendering model could produce another ambiguous input layer.
- A full proposal view may become too verbose unless it supports compact and full modes.
- Strict action preview may slow rapid prototyping if phrased too rigidly.
- A routing playbook may become stale if it repeats too much CLI detail instead of describing stable intent-to-route behavior.
- A playbook that is too rigid could make agents over-process simple requests instead of using owner intent and explicit instructions.
- Artifact catalog status can become stale if physical artifact writes and logical state updates are not handled atomically.
- Docs that mention `--root` could still be misread as recommending separate repositories unless non-goals are explicit.
- If vertical-specific artifacts are discussed in core docs, users may confuse core P2P concepts with software-domain conventions.

## Open Questions

- Which runtime, environment, file, or MCP-client signals are reliable enough to detect the current agent?
- Should unknown-agent fallback to `all` apply equally in non-interactive scriptable init and guided interactive init, or should guided init ask while scriptable init preserves compatibility?
- Should `p2p agent instructions refresh --profile <adapter>` internally install missing adapter files, or remain only a refresh command over installed profiles?
- What concrete current-release fixture set should be kept in tests to prove upgrade compatibility?
- Should legacy write-class and artifact-catalog inference be persisted after first read, or remain purely derived until an explicit refresh/migration command runs?
- Should narrative proposal artifacts be omitted until content exists, or generated with explicit read-only headers?
- Should missing contribution types be added as first-class types, or should a generic categorized contribution model be used?
- Should the full proposal view be implemented as `proposal show --full`, `proposal render`, or both?
- Should generated-file headers be added to all generated `.p2p` markdown, or only proposal-local narrative artifacts?
- Should action preview apply to every governed write or only first writes, ambiguous writes, batch writes, stable documentation, generated exports, and external side effects?
- Should MCP write tools support dry-run or manifest previews before applying changes?
- What exact artifact catalog status vocabulary should be public API versus internal implementation detail?
- Which parts of the request-routing playbook should be generated into project-local agent files versus kept in maintained documentation?

## Acceptance Criteria

- Generated agent instructions require action preview before meaningful persistent writes unless the owner explicitly requested the exact artifact or operation.
- Generated policy defines persistent write classes and identifies which classes require preview.
- Generated instructions state that direct manual edits under `.p2p/` are forbidden unless an explicit repair is requested or a supported CLI/MCP import/edit primitive exists.
- Generated instructions or documentation explain that governed P2P state is mutated through supported P2P write primitives, while the filesystem is storage, compatibility, import, export, or human-readable projection rather than the normal agent write interface.
- Generated agent instructions or project skills include a compact explanation of what P2P Engine is for: governed project intent, owner decisions, proposal flow, structured context, and agent-safe memory.
- Generated agent instructions or project skills include request-routing guidance for chat-only exploration, project definition, proposals, alternatives/choices, software-spec lifecycle through PROP-094, implementation work, exact file requests, and outside-P2P work.
- Maintained documentation such as `docs/AGENT-INTEGRATION.md` includes the longer form of the same playbook without duplicating the full CLI guide.
- Proposal scope hierarchy is documented as semantic core, operational core, bootstrap UX scope, and opportunistic hygiene scope.
- Implementation planning is split into additive slices 093-A through 093-E, with canonical authoring and artifact visibility separated from bootstrap and hygiene work.
- Core documentation uses explicit vertical primitives for domain-specific artifacts, and does not treat software specs as a generic core P2P primitive.
- `stable_documentation` is documented as a write class requiring preview and classification, not as a claim that P2P governs every durable repository document.
- Proposal scaffold and help text explain the canonical authoring flow: structured inputs, synthesis/import, full review, owner decision.
- Narrative proposal artifacts are not presented as manual-edit placeholders; they are either absent until generated, marked generated/read-only with command hints, or writable only through explicit import/edit primitives.
- Every proposal exposes a deterministic logical artifact catalog through CLI/MCP or an equivalent artifact-state/full-view surface.
- Proposal completeness, missing material, optional material, not-applicable material, and next action can be assessed without relying on filesystem directory contents.
- Proposals with different workflow histories may have different physical files, but their logical artifact catalog reports consistent artifact slots and statuses.
- Empty placeholder files are not created solely to make proposal directories uniform.
- Contribution or question primitives cover the narrative concepts exposed by proposal artifacts, including alternatives, findings, risks, objections or constraints, and open questions, or the scaffold stops exposing unsupported concepts as writable-looking files.
- A consolidated owner-friendly proposal view exists and includes proposal text, contributions, narrative artifacts, digest, readiness, artifact coverage, and suggested next action.
- Fresh init always creates the generic baseline and adds the detected current adapter when detection is reliable.
- Fresh init falls back to `all` when no supported current agent can be detected, and clearly explains the file footprint.
- Explicit adapter selection remains available for one adapter, multiple adapters, or `all`.
- Existing projects keep installed adapter files after upgrade unless the owner runs safe uninstall commands.
- Init summary, generated `AGENTS.md`, and maintained docs explain how to list, add, update, inspect, refresh, and remove agent integrations through supported commands.
- Agent removal is conservative: shared baseline files, unmanaged files, and drifted human-edited files are not removed silently.
- Existing current-release workspaces remain loadable and valid after upgrade.
- Missing PROP-093 metadata, write-class labels, artifact-catalog files, or refreshed agent templates are treated as legacy-compatible state, not validation errors.
- Existing narrative proposal artifacts are preserved and rendered as legacy/generated/imported/readable evidence instead of being deleted or silently ignored.
- Existing CLI/MCP command behavior remains stable by default; richer behavior is exposed through additive commands, flags, summaries, or preferred-command documentation.
- Fresh interactive init protects common local artifacts with non-destructive gitignore handling, prints a robust decision-root-aware MCP hint, and groups created files by purpose.
- Documentation explains the difference between decision root and current working directory without recommending sibling repositories or any other repository topology.
- Tests cover adaptive init detection, unknown-agent fallback to `all`, explicit all-adapter selection, explicit narrow adapter selection, post-init integration lifecycle guidance, safe uninstall behavior, legacy workspace loading, legacy template drift handling, optional write-class inference, lazy artifact-catalog derivation, existing narrative artifact preservation, CLI/MCP output compatibility, gitignore handling, MCP hint generation, generated policy text, write-class policy, request-routing playbook text, proposal authoring guidance, deterministic artifact catalog semantics, generated narrative artifact handling, contribution/question type alignment, and full proposal rendering.

## Decision

Pending.
