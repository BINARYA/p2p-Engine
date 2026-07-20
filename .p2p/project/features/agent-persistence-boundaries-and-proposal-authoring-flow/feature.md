# Agent Persistence Boundaries And Proposal Authoring Flow

## Provenance

- Proposal: PROP-093
- Source: .p2p/proposals/PROP-093-new-project-bootstrap-ux-and-agent-write-consent-hardening

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

## Decision

# Decision - PROP-093

## Status

`accepted`

## Outcome

accepted

## Event Type

accepted

## Effective State

accepted

## Reason

Owner accepted PROP-093 after scope-lock refinement, readiness score 100, and validation confirming the proposal is decision-ready for implementation.

## Date

2026-07-09

## Approver

mrjungle

## Owner

mrjungle

## Ledger Head

PDE-c12a5a5335a0654dc56448de

## Decision Fingerprint

705417572765e77e4d965759fa724879504b9b6e569ee06418d316cc41eb1cc8

## Lineage

None.

## Canonical Source

decision-events.yml
