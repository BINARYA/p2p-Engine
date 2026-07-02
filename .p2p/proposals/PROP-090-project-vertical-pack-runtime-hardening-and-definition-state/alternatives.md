# Alternatives - PROP-090

## Preferred: Follow-up Hardening Proposal For PROP-085

Create PROP-090 as a dedicated follow-up that completes the accepted PROP-085
direction.

Benefits:
- preserves PROP-085 as the accepted MVP direction;
- avoids rewriting accepted governance history;
- gives production hardening its own scope, questions, and acceptance criteria;
- makes implementation easier to split into local specs and tasks.

Costs:
- adds another proposal to track;
- requires careful overlap documentation with PROP-085.

## Alternative: Modify PROP-085 Directly

Revise PROP-085 to include all production-hardening details.

Benefits:
- keeps all vertical runtime discussion in one proposal;
- avoids an extra proposal id.

Costs:
- blurs accepted MVP direction with new production scope;
- makes it harder to tell what was accepted originally;
- risks reopening completed local feature work.

Decision:
Rejected for the primary governance path. PROP-090 should be the follow-up.

## Alternative: Create An Unrelated New Proposal

Treat the vertical runtime hardening work as an independent initiative.

Benefits:
- clean standalone text;
- no need to reconcile with previous language.

Costs:
- factually inaccurate because the work extends PROP-085;
- may create a competing vertical system;
- weakens traceability to the implemented MVP.

Decision:
Rejected. PROP-090 is explicitly linked to PROP-085.

## Alternative: Adopt The Revision Literally

Use p2p vertical and .p2p/verticals exactly as the revision source suggested.

Benefits:
- shorter command namespace;
- more generic-looking path.

Costs:
- conflicts with implemented p2p project vertical commands;
- conflicts with current project-local .p2p/project/verticals path;
- increases migration and compatibility burden.

Decision:
Rejected for the first production slice. Keep project-scoped namespace and
paths.

## Alternative: Keep Only Single-File vertical.yml Packs

Continue using the MVP pack shape.

Benefits:
- lowest implementation cost;
- fewer files to validate.

Costs:
- poor maintainability for rich section specs;
- weak support for profiles, modules, artifacts, examples, and trust metadata;
- hard to scale to production-quality vertical packs.

Decision:
Rejected. Keep single-file packs only as compatibility input.

## Alternative: Conversation-Only Project Definition State

Let agents reason about project definition in chat without persistent
definition.yml.

Benefits:
- fewer project files;
- simpler first implementation.

Costs:
- loses project-definition progress across sessions;
- no durable missing-fields, assumptions, section status, or next suggested
  action;
- agents would be tempted to write .p2p state by hand or repeat interviews.

Decision:
Rejected. definition.yml is required.

## Alternative: Full next-action Engine In First Slice

Implement p2p project next-action --json immediately.

Benefits:
- gives agents a deterministic next-question source;
- improves orchestration ergonomics.

Costs:
- likely premature before definition state, dependencies, assumptions, and
  completion semantics are stable;
- risks encoding brittle prioritization rules.

Decision:
Deferred. The first slice exposes enough JSON for best-effort agent selection
and may include next_suggested_action in definition.yml.

## Alternative: Automatic Retroactive Lockfile Generation

Generate vertical.lock.yml for existing projects during validation, readiness,
export, or normal reads.

Benefits:
- quickly normalizes old projects;
- fewer explicit migration commands.

Costs:
- mutates project state without explicit owner action;
- can surprise users;
- may silently lock the wrong pack if active state is ambiguous.

Decision:
Rejected. Existing projects require explicit repair/migration.

