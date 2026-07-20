# Project Vertical Pack Runtime Hardening And Definition State

## Provenance

- Proposal: PROP-090
- Source: .p2p/proposals/PROP-090-project-vertical-pack-runtime-hardening-and-definition-state

## Problem

PROP-085 introduced pluggable project verticals and the first local implementation delivered an MVP: packaged vertical data, project-local override, active vertical state, CLI/MCP operations, readiness review, proposal-to-vertical coverage, and agent guidance. That MVP proves the direction, but it is not yet a production-grade vertical runtime.

The current implementation still relies on a compact single-file vertical model, does not persist an exact resolved vertical lockfile, does not persist durable project definition state, does not expose a complete JSON contract for agent-guided project construction, and does not yet formalize compatibility between selected verticals, generated rubrics, enabled rubric criteria, section completion, assumptions, and agent updates.

Without a stronger contract, verticals may remain useful templates rather than a reliable operating layer for project definition. Agents can inspect available vertical data, but they cannot durably record what the owner has answered, what remains missing, what is assumed, which section is blocked, or which question should be asked next. Pack updates or local overrides may also change behavior unexpectedly if the project does not pin the resolved pack version and checksum.

This proposal completes and hardens PROP-085 by defining the production-grade contracts for project vertical pack shape, source resolution, lockfiles, project definition state, CLI JSON access, agent-guided progressive interview behavior, validation, security, rubric regeneration, and future Wavekit-compatible installation.

## Proposal

Introduce a production-grade project vertical runtime layer as a follow-up to PROP-085.

This proposal is organized around four production contracts plus explicit scope, alternative, risk, owner-question, acceptance, and overlap analysis. The owner-review questions Q001-Q006 have been resolved and are incorporated in the direction below.

Contract 1: Project Vertical Pack Contract
A project vertical pack is a declarative data package that describes a project skeleton for a class of projects. The canonical production pack is multi-file for maintainability:
- manifest.yml
- vertical.yml
- sections/
- profiles/
- modules/
- rubrics.yml
- artifacts/
- examples/

Minimum valid production pack:
- manifest.yml
- vertical.yml
- sections/
- rubrics.yml

The loader must continue accepting the current MVP single-file vertical.yml shape as a compatibility input and normalize it into the same typed model. The canonical pack can split section specs, rubrics, artifact metadata, examples, and profiles into separate files. A section spec should define purpose, required fields, interview questions, assisted answer behavior, examples or answer templates, completion criteria, dependencies, common mistakes, suggested artifacts, and maturity gates where available.

manifest.yml should contain stable identity and package metadata: id, name, version, publisher/source, schema_version, description, categories/tags, compatibility p2p_min_version, entrypoints, declared profiles, declared sections, artifact ids, license/trust metadata, and optional checksum/signature fields for future remote packs.

vertical.yml should define the project skeleton: id, name, version, goal, extends/base, default_profile, maturity levels, section list with stable ids and spec paths, interview policy, completion policy, enabled status defaults, and supported statuses.

profiles allow one vertical to support different project intentions without separate vertical ids. modules are optional vertical-local extensions. rubrics.yml provides default criteria for .p2p/project/rubrics.yml. Artifact templates are optional and partial artifact generation must mark missing or assumed content.

Contract 2: Project Configuration And Resolution Contract
The selected project vertical remains project state. Keep .p2p/project/vertical.yml, but evolve its schema from a minimal active-id record into richer selected-vertical configuration while remaining backward-compatible with MVP files.

Keep the project-local pack path .p2p/project/verticals/<vertical-id>/ for compatibility. Installed local packs are resolved from both P2P_HOME/verticals and ~/.p2p/verticals. If P2P_HOME is configured, P2P_HOME/verticals has precedence over ~/.p2p/verticals; otherwise ~/.p2p/verticals is the default installed-local directory. If both installed-local locations contain the same pack id/version, the P2P_HOME source wins. Packaged seed resources remain inside package resources. Future Wavekit packs should be installed into an installed-local source and resolved by the same resolver.

Resolution order is deterministic:
- explicit path or vertical reference passed by the owner;
- project-local packs under .p2p/project/verticals/;
- installed local packs under P2P_HOME/verticals, when configured;
- installed local packs under ~/.p2p/verticals;
- packaged seed vertical resources;
- future configured Wavekit/registry source;
- base_project fallback only during initial selection or explicitly allowed repair.

base_project remains the canonical fallback vertical for this implementation. Do not introduce generic_project in the first implementation. generic_project was terminology from the revision source and may be reconsidered later as a non-breaking alias only if there is a clear usability need after resolver, lockfile, and pack identity rules are stable.

After initialization or explicit project vertical selection, resolve through .p2p/project/vertical.lock.yml. The lockfile records id, name, version, source, resolved_from, package coordinate, checksum, schema version, p2p compatibility, selected/installed metadata, and optional trust/signature metadata. If a locked pack cannot be found or its checksum does not match, P2P must report a clear error and suggest explicit remedies. It must not silently fall back to base_project after a lockfile exists.

For existing projects that already have active vertical state but no lockfile, do not generate vertical.lock.yml implicitly during validation, readiness, export, or ordinary reads. Validation should report an actionable warning. A dedicated explicit repair/migration command should generate the lockfile after resolving the active vertical. If the active vertical cannot be resolved, that command must fail without writing and must not silently fall back to base_project.

Contract 3: Project Definition State Contract
Add .p2p/project/definition.yml as durable project definition state. This file records how far the owner has progressed in defining the project according to the active vertical. It is separate from vertical.yml and rubrics.yml.

The definition state includes schema_version, vertical_id, vertical_version, selected profile, optional lock reference, per-section status, structured field data, missing required fields, assumptions, open questions, project-definition decisions when relevant, blockers, next_suggested_action when deterministic, and history/provenance.

Recommended section statuses: missing, partial, assumed, complete, blocked, not_applicable. Recommended assumption statuses: to_validate, validated, rejected, superseded.

The agent may propose assumptions, but assumptions must be recorded explicitly. Assumptions must not silently satisfy completion criteria unless section completion policy explicitly allows assumed fields.

The first production slice must implement definition-state writes through a narrow structured patch/update contract. Do not expose arbitrary editing. Supported write paths must validate section_id, field_id, status, assumptions, missing fields, provenance/history, and must write atomically through service/CLI/MCP paths. Defer full interactive editing, sophisticated next-action computation, complex long-answer merge behavior, advanced state migrations, and broad writer surfaces.

Contract 4: Agent Guidance Runtime Contract
The agent is generic. It should not hardcode board-game, software, research, business, or other domain structures. It loads active project context, vertical configuration, section specs, enabled rubrics, and definition state through CLI/MCP data surfaces.

Runtime modes: interview, review, audit, generate_artifact, roadmap, diagnostic.

In interview mode the agent works progressively: choose the next important incomplete or blocking section, retrieve the section spec, ask one primary question, explain why it matters, offer examples/templates, summarize the answer, record decisions and assumptions, update or emit a structured patch for definition state, report remaining gaps, then continue. The agent is strict about completeness but gentle in interaction. It does not mark sections complete unless completion criteria are satisfied. It distinguishes selected project rubric maturity from full default vertical baseline coverage.

CLI And MCP JSON Contract
Keep p2p project vertical ... as the production namespace. Add or refine project-scoped JSON surfaces:
- p2p project vertical list --json
- p2p project vertical show <vertical-id> --json
- p2p project vertical validate <path-or-id> --json
- p2p project vertical add <path> --json
- p2p project vertical select <vertical-id> --json
- p2p project vertical lock --json, if explicit lock inspection/repair is needed
- p2p project context --json
- p2p project sections --json
- p2p project section <section-id> --json
- p2p project rubrics --json
- p2p project definition --json
- p2p project definition update --json or equivalent structured patch import/update

Defer the full p2p project next-action --json command until definition state semantics are stable. In the first production slice, expose enough structured data through project context, sections, section detail, and definition JSON so the agent can compute a best-effort next question. The first slice may include a lightweight next_suggested_action field inside definition.yml, but not a full standalone next-action engine.

A top-level p2p vertical namespace is not required for the first production implementation. It may be introduced later as an alias if there is a strong usability reason.

Init And PROP-057 Integration
p2p init remains lightweight and deterministic. Interactive init may ask project name, domain/intent, vertical selection, profile selection, optional section/module selection, and rubric customization. It writes vertical.yml, vertical.lock.yml, initial definition.yml, and rubrics.yml generated from vertical defaults. After rubric generation, PROP-057 guided selection runs so the owner controls enabled and disabled criteria. Non-interactive init remains scriptable with flags such as --vertical, --profile, and --no-rubric-customization. If no vertical is specified, the deterministic default is base_project unless a documented domain-to-vertical mapping exists.

Rubric Regeneration And Maturity Scope
When profile, enabled sections, modules, or vertical version changes require rubric regeneration, preserve existing enabled flags by criterion id where possible. New criteria use vertical defaults. Removed criteria are orphaned or removed only with explicit confirmation. Maturity refresh evaluates enabled criteria only and reports source vertical, version, enabled count, disabled count, total default criteria where known, and selected_project_rubric scope.

Versioning, Upgrade, And Migration
Vertical packs use semantic versioning. Projects pin resolved version and checksum in vertical.lock.yml. Upgrades are explicit and show current version, target version, changed sections, added/removed sections, changed rubric criteria, changed artifact templates, guidance policy changes, and definition-state migration impacts. No ordinary command silently upgrades the pack, creates a lockfile, or migrates definition state.

Security And Trust
Vertical packs are declarative data. Allowed formats initially include YAML, JSON, Markdown, and plain text templates. Packs must not contain executable scripts.

Validation uses severity by field and content. Explicit attempts to override system, developer, safety, governance, repository, or tool-permission rules; execute code; escape pack/project paths; force tool execution; modify permissions; or instruct agents to ignore higher-priority instructions are hard errors. Ambiguous instruction-like language in descriptive examples, templates, or explanatory fields is a warning. Ordinary domain questions, examples, completion criteria, common mistakes, artifact templates, and domain suggestions are allowed. Internal seed packs should validate cleanly; project-local packs may be allowed with warnings; future remote/Wavekit packs should use stricter trust validation. In all cases, vertical pack content remains domain data, not authoritative agent instruction.

Scope Boundaries
In scope: production hardening of PROP-085; canonical multi-file pack schema; compatibility loading for single-file packs; vertical.lock.yml; definition.yml; project-scoped JSON CLI/MCP surfaces; narrow definition-state writes; lightweight init integration; PROP-057 rubric preservation; validation, safety, version pinning, upgrade diagnostics, migration semantics; generated generic agent guidance.

Out of scope for the first production slice: Wavekit remote search/install/update/publish; executable vertical plugins; required p2p vertical namespace; moving packs out of .p2p/project/verticals/; breaking base_project rename; full interviews inside p2p init; automatic upgrades; implicit retroactive lockfile generation; silent fallback after lockfile creation; full next-action engine; domain-specific agent skills for each vertical.

Alternatives Considered
Alternative A: Modify PROP-085 directly. Rejected because PROP-085 is accepted and already has an MVP implementation. PROP-090 is a follow-up proposal.
Alternative B: Create an unrelated proposal. Rejected because this is the completion of PROP-085.
Alternative C: Adopt the revision literally with p2p vertical ... and .p2p/verticals/. Rejected for the first slice because p2p project vertical ... and .p2p/project/verticals/ already exist.
Alternative D: Keep only single-file vertical.yml. Rejected because production packs need maintainable section specs, profiles, rubrics, artifacts, examples, and trust metadata.
Alternative E: Keep project definition state conversational only. Rejected because guided project construction must persist across sessions.
Alternative F: Silently fall back to base_project when a locked vertical is missing. Rejected because it changes project behavior unexpectedly.
Alternative G: Generate lockfiles automatically for existing projects during validation/readiness/export. Rejected because it mutates project state without an explicit owner repair/migration action.

Tradeoff Analysis
Keeping p2p project vertical ... favors compatibility over brevity. Keeping .p2p/project/verticals/ favors current project-state conventions over the revision source path. Keeping base_project favors implementation continuity over generic_project terminology. Adding vertical.lock.yml increases state complexity but prevents behavior drift. Adding definition.yml and a narrow writer increases persistence and validation responsibility but enables durable agent guidance. Supporting both single-file and multi-file packs increases loader complexity but avoids a migration cliff. Supporting both P2P_HOME/verticals and ~/.p2p/verticals adds resolver precedence complexity but supports isolated environments, CI, containers, and normal user installs. Deferring Wavekit and the full next-action engine sacrifices remote catalog and automated prioritization functionality in this slice but stabilizes local contracts first.

Risk Coverage
Risk: vertical domain logic leaks into core. Mitigation: keep domain content in packs; core only loads, validates, resolves, locks, exposes, and updates typed state.
Risk: proposal scope is too large. Mitigation: implement through phased local specs and tasks.
Risk: definition.yml duplicates governance decisions. Mitigation: definition.yml stores project-definition state only; proposal decisions remain governance artifacts.
Risk: agents treat pack text as instructions. Mitigation: vertical text has no instruction authority; validators warn/reject unsafe guidance by severity.
Risk: lockfiles make projects brittle. Mitigation: provide explicit repair/migration/fallback commands and actionable diagnostics.
Risk: rubric regeneration overwrites owner choices. Mitigation: preserve enabled flags by criterion id and require confirmation for orphan removal.
Risk: init becomes too long. Mitigation: init configures vertical/profile/rubric scope only.
Risk: custom generated verticals are low quality. Mitigation: mark as project-local scaffolds, validate them, and inherit from base_project.
Risk: next-action logic is premature. Mitigation: expose enough structured JSON for best-effort agent selection and defer the formal engine.

Assumptions And Constraints
Assumptions: PROP-085 remains the accepted baseline; the owner wants hardening rather than a second vertical system; existing public commands and paths should be preserved; base_project remains the fallback pack; Wavekit compatibility matters but remote behavior is deferred; agents need durable state; maturity remains governed by .p2p/project/rubrics.yml and enabled flags.

Constraints: do not edit .p2p files by hand during implementation; use supported service/CLI/MCP write paths; do not add domain behavior to large compatibility files when a service boundary is appropriate; keep packs declarative and non-executable; keep owner governance decisions outside vertical packs and agent runtime.

Owner Questions Resolution
Resolved and incorporated:
- Q001: Implement definition-state writes in the first production slice through a narrow structured patch/update contract.
- Q002: Defer the full next-action engine; expose JSON context and optionally next_suggested_action in definition.yml.
- Q003: Omit generic_project from the first implementation; keep base_project canonical.
- Q004: Resolve installed packs from both P2P_HOME/verticals and ~/.p2p/verticals with P2P_HOME precedence.
- Q005: Use severity-dependent unsafe guidance validation.
- Q006: Generate lockfiles automatically for new init/select flows; existing projects require explicit repair/migration.

Acceptance Criteria Quality
Acceptance criteria must be verified by implementation evidence: service tests for loader normalization, resolver precedence, lockfiles, and definition-state validation; CLI tests for JSON commands, init integration, lock inspection, explicit lock repair/migration, and definition-state read/update behavior; MCP parity tests where applicable; validation tests for malformed packs, unsafe paths/content, stale locks, orphaned rubrics, and inconsistent definition state; regression tests for current p2p project vertical commands and single-file packs; docs for pack layout, compatibility, lockfile semantics, definition.yml, agent guidance, and deferred Wavekit/next-action behavior; p2p validate with zero errors.

Impact And Overlap Analysis
PROP-085 overlap is direct: PROP-090 is its production hardening layer, not a competing system. The completed local feature specs/features/pluggable-project-verticals-and-readiness-orchestration remains the MVP baseline; PROP-090 should produce a new local hardening feature rather than reopening completed MVP tasks. PROP-057 remains the owner-controlled rubric selection flow. PROP-071 remains compatible with custom domain definition. PROP-082 and PROP-089 may consume definition-state data, but proposal readiness question state remains separate from project definition state. PROP-083 exports may include vertical and definition-state summaries additively. Expected code impact is concentrated in project vertical core models, ProjectVerticalService, project initialization, maturity/rubric services, validation, CLI project command modules, MCP project handlers/catalog, agent templates, docs, tests, and possibly visible project export. P2PWorkspace remains a facade.

## Decision

# Decision - PROP-090

## Status

`accepted`

## Outcome

accepted

## Event Type

accepted

## Effective State

accepted

## Reason

Owner reviewed the refined production hardening proposal, confirmed no further changes are needed, and accepts it as the follow-up to PROP-085 for project vertical pack runtime hardening and definition-state production readiness.

## Date

2026-07-02

## Approver

mrjungle

## Owner

mrjungle

## Ledger Head

PDE-677c1d9bff19a26b755298d7

## Decision Fingerprint

48632dd4c6beebbe284ffd2c8b3106a8c03b022b6e2e74b268a5d8517018007d

## Lineage

None.

## Canonical Source

decision-events.yml
