# PROP-006 - Multi-Agent Integration Model

## Status

`accepted`

## Problem

P2P Engine can already generate basic agent-facing instructions for generic, Codex, and Claude profiles, but it does not yet manage agent integrations as governed, inspectable, updateable project state. Project initialization should create the supported project-local agent file structures by default, but today there is no explicit registry of installed integrations, generated-file manifests, hashes, drift detection, safe update, safe uninstall, conflict detection, or precise adapter matrix for Cursor, Copilot, Gemini, OpenCode, Codex, Claude, and the generic baseline. A second gap is methodological: generated instructions do not yet force agents to turn weak proposal readiness, failed gates, and owner questions into concrete refinement actions, alternatives, recommendations, candidate edits, and readiness re-checks.

## Context

The original PROP-006 proposed an agent integration layer inspired by Spec Kit and OpenSpec. Subsequent work implemented the first layer through p2p init --agent, p2p agent instructions refresh, AGENTS.md, CLAUDE.md, .codex skills, .p2p/agent-policy.yml, and MCP bootstrap tools. The remaining gap is lifecycle governance for installed agent integrations and their generated files. Generated instructions, CLI, and MCP are separate layers: instructions define method and guardrails, CLI exposes textual commands, and MCP exposes the same P2P capabilities as structured tools for compatible agents. P2P should not choose or record a project-level preferred agent: collaborators may use different tools at the same time. Agent incisiveness is not a Codex-specific profile concern; it is a common P2P method behavior that must be carried by the generic baseline and inherited by every generated adapter file.

## Goals

- Create all supported project-local agent integrations by default during project init, unless the owner explicitly narrows the install set.
- Keep generic as the mandatory, unremovable common baseline from which agent-specific files are derived.
- Introduce a versioned project-local .p2p/agent-integrations.yml registry with generated-file manifests, ownership metadata, shared-file flags, template versions, SHA-256 hashes, and drift state.
- Use built-in package templates for the MVP and defer project-local template overrides.
- Support safe install, install all, list, show, update, doctor, and uninstall flows without active/default/preferred agent state.
- Define the initial adapter matrix for generic, Codex, Claude, Cursor, Copilot, Gemini, and OpenCode, including shared files and excluded legacy/conflicting targets.
- Define common method behavior for generated instructions so agents transform readiness gaps into alternatives, recommendations, owner questions, candidate edits, and readiness re-checks.
- Keep P2P CLI, MCP tools, .p2p state, validation, readiness, and owner decisions aligned over the same core behavior.

## Non-Goals

- Project-level preferred, default, current, switched, or active agent selection.
- Direct invocation of AI providers or hosted agent runtimes.
- Destructive uninstall of files that have been manually modified or are shared with other installed integrations.
- Automatic edits to user/global agent configuration outside the project without explicit consent.
- Generation of deprecated .cursorrules files or default opencode.json configuration in the MVP.
- Full implementation of dedicated readiness refinement commands unless covered by this proposal's implementation scope or a follow-up readiness proposal.

## Proposal

Introduce an Agent Integration Registry MVP. By default, p2p init creates the generic baseline and all supported project-local adapter files for generic, codex, claude, cursor, copilot, gemini, and opencode. The owner may request a narrower init set with repeated --agent options, but generic is always included and cannot be removed. P2P records installed integrations in .p2p/agent-integrations.yml using schema_version 1, baseline_profile: generic, adapter status, maturity, capabilities, template_version, generated file records, shared ownership, managed flag, template_id, SHA-256 hash over exact file bytes, and drift state. The registry must not contain active_agent, default_agent, preferred_agent, current_agent, use, or switch state. Built-in adapter templates live in package data under src/p2p_engine/templates/agents/<adapter>/ for the MVP; project-local template overrides are deferred. Generated Markdown files should include a short managed header as a human hint, while the registry remains authoritative. The CLI exposes p2p agent list, show, install, update, doctor, and uninstall; excluded commands are use, switch, current, and install --no-use. doctor validates registry shape, file existence, hashes, shared references, generic baseline, ownership conflicts, uninstall safety, and presence of the generic method behavior block. install all may install every supported project-local integration only when non-shared file targets do not conflict. Migration is conservative: known generated files become managed, unknown or changed files become unmanaged or drifted, and P2P never overwrites them silently. Generated files derive from minimal generic P2P governance content and may be adapted for host tools without weakening the rules. That generic content must include readiness-driven refinement behavior: when a proposal is weak, low-confidence, below target, or blocked by failed gates, the agent must explain each gap, propose concrete alternatives, recommend one when justified, identify owner decisions, draft candidate updates, and re-check readiness after refinement. Initial files are AGENTS.md and .p2p/agent-policy.yml for generic; AGENTS.md plus a shared agent-neutral .agents/skills/p2p-project/SKILL.md for Codex when safe, with .codex/skills preserved as compatibility/migration; CLAUDE.md for Claude; .cursor/rules/p2p.mdc for Cursor; .github/copilot-instructions.md for Copilot; GEMINI.md for Gemini; and AGENTS.md only for OpenCode in the MVP. opencode.json is not generated by default. CLI and MCP tools are implemented over the same core behavior, with MCP exposing structured equivalents for compatible agents. Future readiness refinement commands should live under p2p proposal readiness, but they are not required for accepting this proposal.

## Acceptance Criteria

- Default project init installs generic plus all supported project-local adapters: codex, claude, cursor, copilot, gemini, and opencode.
- A narrowed init can install only requested specific adapters, but generic is still created and remains unremovable.
- .p2p/agent-integrations.yml uses schema_version 1 with baseline_profile, adapters, capabilities, template_version, generated file records, shared ownership, managed flag, template_id, SHA-256 hash, and drift state.
- The registry records installed integrations and generated files without active_agent, default_agent, preferred_agent, current, use, or switch state.
- Built-in adapter templates live in package data for the MVP; project-local template overrides are deferred.
- The generic baseline defines the minimum P2P governance rules and all generated agent-specific files preserve those rules.
- Generated instructions include a readiness gap handling block that requires agents to explain failed gates, propose alternatives, recommend one option when justified, identify owner decisions, draft candidate updates, and re-check readiness.
- The adapter matrix documents exact generated files for each built-in adapter and excludes deprecated .cursorrules and default opencode.json generation.
- install all detects non-shared file target conflicts and refuses conflicting adapters instead of overwriting.
- Generated files are recorded with template version, ownership metadata, shared-file flag, and SHA-256 hash over exact file bytes.
- Updating an adapter refreshes unchanged generated files and refuses to silently overwrite drifted files.
- Uninstall removes only the target adapter's managed, unchanged, non-shared files and preserves generic, shared, modified, and unmanaged files.
- p2p agent doctor validates registry shape, file existence, hashes, shared references, generic baseline, ownership conflicts, uninstall safety, and method behavior presence.
- Existing projects migrate conservatively by marking known generated files as managed and unknown or changed files as unmanaged or drifted without overwriting them.
- The .agents/skills path is used only for agent-neutral P2P skill content or otherwise deferred to avoid Codex/OpenCode interpretation conflicts.
- CLI and MCP expose equivalent agent integration lifecycle operations through the same core behavior.
- Existing p2p agent instructions refresh behavior remains backward compatible.

## Decision

Pending.
