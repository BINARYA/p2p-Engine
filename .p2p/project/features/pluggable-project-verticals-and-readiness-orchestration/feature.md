# Pluggable Project Verticals And Readiness Orchestration

## Provenance

- Proposal: PROP-085
- Source: .p2p/proposals/PROP-085-pluggable-project-verticals-and-readiness-orchestration

## Problem

Project initialization and project readiness currently rely on domain/rubric defaults that are useful but too static: P2P can suggest rubric criteria, but it does not yet model verticals as extensible project-specific packages with sections, maturity rules, questions, artifacts, examples, and agent guidance. This risks hardcoding a finite catalog of domains inside the engine, or leaving agents without enough structure to proactively define what a project should achieve in its chosen vertical.

## Proposal

Introduce pluggable project verticals. A vertical package defines its id, name, version, base extension, sections, section detail packs, maturity levels, rubric criteria, blocking/refinement questions, artifact templates, examples, profiles, and optional compatible modules. P2P Engine provides a generic loader/validator and a project orchestrator skill that reads these definitions, evaluates project readiness, proposes capisaldi, creates initial refinement questions, and guides a one-question-at-a-time interview. Vertical packages are pure data packages made of text files, primarily .md and/or .yaml, not executable code in the MVP. They contain the project skeleton for the vertical: chapters, sections, topics to address, vertical-specific peculiarities, rubrics, questions, and useful artifacts. The minimum MVP vertical pack requires vertical.yml with id, name, version, description, and base/extends; project sections/chapters; minimal completeness/readiness rubrics; initial blocking questions; and expected or suggested artifacts. Examples, profiles, compatible modules, and rich output templates are optional in the MVP. Default vertical packs are distributed internally with the project/package as versioned, testable data resources for the MVP. The design should stay registry-ready, but an external registry is not part of the first slice; a later registry can expose REST endpoints to list available packs and fetch pack details/versions. The CLI remains deterministic: p2p init may ask deterministic setup questions and persist project/init state, but it does not launch or embody the agent. The proactive behavior belongs to the agent instructions. When the agent detects an uninitialized project, an initialization state, or missing project capisaldi and initial questions, it must treat that as priority context work because it determines project readiness. The agent should know how to initialize the project with the CLI, use owner answers to populate init/project objects, propose the vertical-derived capisaldi, save initial questions when possible, interview one question at a time, and return to deferred core-definition work unless the owner explicitly silences it. When a requested vertical is missing, resolution order is project-local vertical packs, core/default packs, configured data registry/plugin packs, then base_project fallback. The fallback is not passive: the agent proposes a default/base vertical, enters customization mode, extracts the missing vertical information from the owner, creates or updates a project-local custom vertical with sections/capisaldi, minimal rubrics, blocking questions, and expected artifacts, and uses it only after owner confirmation. This proposal extends and reuses the existing project rubrics and project maturity/readiness artifacts rather than replacing them. Vertical packs provide structured inputs that specialize the current system; they must not create a parallel maturity engine. The explicit command for later review is p2p project readiness review: the command goal is project readiness/context strengthening, while verticals are the data source used by the review. It should reuse existing project rubrics/maturity, read packaged and project-local verticals, identify missing capisaldi, produce initial or follow-up project questions, and guide the agent on readiness priorities. Core should start with base_project and a small MVP set of high-quality verticals, while additional verticals live in an external registry or project-local custom directory. Initial implementation scope is base_project plus the vertical pack loader/validator, the project orchestrator skill, one complete demonstration vertical, and project readiness review integration. The five-vertical MVP set remains a follow-up target, not part of the first implementation slice.

## Decision

# Decision - PROP-085

## Status

`accepted`

## Outcome

accepted

## Event Type

accepted

## Effective State

accepted

## Reason

Accepted by owner after readiness reached decision_ready. The proposal defines pluggable pure-data project verticals, base_project, custom vertical candidate flow, project readiness review, and proposal-to-vertical traceability while preserving backward compatibility.

## Date

2026-06-09

## Approver

mrjungle

## Owner

mrjungle

## Ledger Head

PDE-bfc14622b8e2748a30b2db0a

## Decision Fingerprint

78b95a7dae26ba6445d034fabc2e1a951ba1a11ddcc75259011edead14d4dae3

## Lineage

None.

## Canonical Source

decision-events.yml
