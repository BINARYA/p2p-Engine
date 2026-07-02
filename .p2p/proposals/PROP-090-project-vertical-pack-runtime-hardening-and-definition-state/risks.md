# Risks - PROP-090

## Risk: Vertical Logic Leaks Into Core

Domain-specific behavior could move into services or CLI code instead of
remaining in packs.

Mitigation:
- keep sections, questions, rubrics, examples, and artifacts in data packs;
- core services only load, validate, resolve, lock, expose, and update typed
  state;
- test with unrelated verticals.

## Risk: Scope Is Too Large

The proposal spans pack schema, resolver, lockfile, init, rubrics, definition
state, JSON APIs, agent behavior, validation, and migration.

Mitigation:
- implement through phased local specs and tasks;
- keep Wavekit and the full next-action engine deferred;
- preserve compatibility with current MVP behavior.

## Risk: definition.yml Duplicates Governance Decisions

Project definition state could be confused with proposal decisions.

Mitigation:
- definition.yml stores project-definition answers, assumptions, section
  completeness, missing fields, and open project questions;
- proposal acceptance, rejection, and decisions remain P2P governance artifacts.

## Risk: Agents Treat Pack Text As Instructions

Vertical pack text may include instruction-like content.

Mitigation:
- pack text has no instruction authority;
- validators use severity-dependent checks;
- unsafe override/tool/safety/governance text is a hard error;
- ambiguous wording in examples/templates is a warning.

## Risk: Lockfiles Make Projects Brittle

Pinned vertical sources may become unavailable.

Mitigation:
- report actionable diagnostics;
- provide explicit repair/migration/fallback commands;
- never silently fall back after a lockfile exists.

## Risk: Rubric Regeneration Overwrites Owner Choices

Changing profiles, sections, or pack versions can change rubric defaults.

Mitigation:
- preserve enabled flags by stable criterion id;
- add new criteria with vertical defaults;
- treat removed criteria as orphaned or remove them only with confirmation.

## Risk: Init Becomes Too Long

Vertical selection could turn p2p init into a full project interview.

Mitigation:
- init configures project vertical/profile/modules/rubric scope only;
- section interview happens later through agent guidance.

## Risk: Custom Generated Verticals Are Low Quality

Generated project-local packs may look authoritative but be incomplete.

Mitigation:
- mark generated packs as project-local scaffolds;
- inherit from base_project;
- validate structure;
- require later refinement for production use.

## Risk: next-action Logic Is Premature

A full next-action engine may overfit before state semantics stabilize.

Mitigation:
- defer p2p project next-action --json;
- expose JSON context and optional next_suggested_action field first.

