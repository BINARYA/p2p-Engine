# PROP-085 - Pluggable Project Verticals And Readiness Orchestration

## Status

`accepted`

## Problem

Project initialization and project readiness currently rely on domain/rubric defaults that are useful but too static: P2P can suggest rubric criteria, but it does not yet model verticals as extensible project-specific packages with sections, maturity rules, questions, artifacts, examples, and agent guidance. This risks hardcoding a finite catalog of domains inside the engine, or leaving agents without enough structure to proactively define what a project should achieve in its chosen vertical.

## Context

This proposal extends the direction opened by PROP-057, Guided Rubric Selection During Init. PROP-057 lets the owner confirm suggested rubric criteria during init. The next step is to treat a vertical as a data-driven package loaded by a generic project orchestrator skill: base_project plus optional verticals/modules/profiles that can live in core defaults, registries, or project-local custom packs. The attached discussion distinguishes a stable orchestrator skill from vertical definitions and section detail packs, recommends a small high-quality default set, and keeps broader growth in plugins/registries rather than hardcoding all possible verticals in P2P Engine.

## Goals

- Define a generic vertical package model for project init and project review, including sections, detail packs, rubric criteria, maturity levels, questions, artifacts, examples, profiles, and optional modules.
- Teach agents, through generated/local skills, to propose project capisaldi and focused refinement questions when the current project vertical or readiness information is weak, missing, or too generic.
- Support core defaults, external/plugin registries, and project-local custom verticals without requiring P2P Engine to hardcode every possible domain.
- Allow the same flow to run during interactive project init and later through an explicit project readiness review command.

## Non-Goals

- Do not ship a large catalog of superficial verticals in the engine.
- Do not require all verticals to be known at build time.
- Do not replace owner governance: the agent proposes verticals, capisaldi, rubric extensions, and questions, but the owner decides.
- Do not make regulated verticals such as medical or legal authoritative without explicit caution, provenance, and owner responsibility.

## Proposal

Introduce pluggable project verticals. A vertical package defines its id, name, version, base extension, sections, section detail packs, maturity levels, rubric criteria, blocking/refinement questions, artifact templates, examples, profiles, and optional compatible modules. P2P Engine provides a generic loader/validator and a project orchestrator skill that reads these definitions, evaluates project readiness, proposes capisaldi, creates initial refinement questions, and guides a one-question-at-a-time interview. Vertical packages are pure data packages made of text files, primarily .md and/or .yaml, not executable code in the MVP. They contain the project skeleton for the vertical: chapters, sections, topics to address, vertical-specific peculiarities, rubrics, questions, and useful artifacts. The minimum MVP vertical pack requires vertical.yml with id, name, version, description, and base/extends; project sections/chapters; minimal completeness/readiness rubrics; initial blocking questions; and expected or suggested artifacts. Examples, profiles, compatible modules, and rich output templates are optional in the MVP. Default vertical packs are distributed internally with the project/package as versioned, testable data resources for the MVP. The design should stay registry-ready, but an external registry is not part of the first slice; a later registry can expose REST endpoints to list available packs and fetch pack details/versions. The CLI remains deterministic: p2p init may ask deterministic setup questions and persist project/init state, but it does not launch or embody the agent. The proactive behavior belongs to the agent instructions. When the agent detects an uninitialized project, an initialization state, or missing project capisaldi and initial questions, it must treat that as priority context work because it determines project readiness. The agent should know how to initialize the project with the CLI, use owner answers to populate init/project objects, propose the vertical-derived capisaldi, save initial questions when possible, interview one question at a time, and return to deferred core-definition work unless the owner explicitly silences it. When a requested vertical is missing, resolution order is project-local vertical packs, core/default packs, configured data registry/plugin packs, then base_project fallback. The fallback is not passive: the agent proposes a default/base vertical, enters customization mode, extracts the missing vertical information from the owner, creates or updates a project-local custom vertical with sections/capisaldi, minimal rubrics, blocking questions, and expected artifacts, and uses it only after owner confirmation. This proposal extends and reuses the existing project rubrics and project maturity/readiness artifacts rather than replacing them. Vertical packs provide structured inputs that specialize the current system; they must not create a parallel maturity engine. The explicit command for later review is p2p project readiness review: the command goal is project readiness/context strengthening, while verticals are the data source used by the review. It should reuse existing project rubrics/maturity, read packaged and project-local verticals, identify missing capisaldi, produce initial or follow-up project questions, and guide the agent on readiness priorities. Core should start with base_project and a small MVP set of high-quality verticals, while additional verticals live in an external registry or project-local custom directory. Initial implementation scope is base_project plus the vertical pack loader/validator, the project orchestrator skill, one complete demonstration vertical, and project readiness review integration. The five-vertical MVP set remains a follow-up target, not part of the first implementation slice.

## Acceptance Criteria

- A pure-data vertical pack schema is defined and validated, with required fields for vertical metadata, sections/capisaldi, minimal readiness rubrics, blocking questions, and expected artifacts.
- base_project is available as the universal fallback and existing projects without vertical packs continue to work with current project rubrics and maturity/readiness behavior.
- Default MVP vertical packs are loaded from internal package/project resources, while project-local custom packs can override or extend them.
- A project readiness review command, p2p project readiness review, reads vertical packs, project-local custom packs, existing rubrics/maturity state, and project context to identify missing capisaldi and generate prioritized project questions.
- Project readiness review produces a vertical skeleton summary that maps vertical sections/capisaldi to relevant proposals, accepted decisions, gaps, risks, and unmapped proposals.
- Generated agent/project instructions explain that missing initialization, capisaldi, or initial project questions are priority context work and guide the agent to propose, confirm, and refine project-local custom verticals.
- The first implementation slice includes one complete demonstration vertical and does not require the later five-vertical set, remote registry, or executable plugin verticals.
- The design remains registry-ready by keeping pack identity/version metadata and a loader boundary that can later support REST list/detail endpoints without changing project-local pack semantics.

## Decision

Pending.
