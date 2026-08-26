---
name: p2p-project-curator
description: Build a vertical-aware, language-specific human project publication from a prepared P2P publication packet and complete evidence index.
---

<!--
Managed by P2P Engine.
Adapter: codex
Template: codex-p2p-project-curator-skill-v3
Generation: agent-template-generation-v2:agent-capabilities-v9:codex-p2p-project-curator-skill-v3
Do not edit generated sections unless you accept drift.
-->

# P2P Project Curator

## Purpose

Create one autonomous project document for a reader who has no knowledge of P2P.
The document explains the project itself. It does not explain the proposal,
decision, readiness, Change Set, Work, or governance process used to design it.

## Start

1. Use the exact edition packet emitted by `p2p project publish prepare`.
2. Verify every packet-declared path and hash before drafting.
3. Read these references directly:
   - [Editorial workflow](references/editorial-workflow.md)
   - [Publication contracts](references/publication-contracts.md)
   - [Vertical interpretation](references/vertical-interpretation.md)
   - [Editorial rubric](references/editorial-rubric.md)
4. Inspect every evidence-index entry and the current project structure before choosing an
   outline.
5. Write only the packet-declared candidate Markdown, project model, and
   evidence-accounting files, then stop.

## Hard Boundaries

- Use only packet-declared evidence. Never use implicit knowledge from another
  repository, product, brand, or earlier conversation.
- Do not infer whether planned work is implemented, shipped, or abandoned.
- Do not expose internal IDs, hashes, paths, readiness scores, or upstream
  workflow status in reader prose.
- Do not force software headings onto another vertical. Headings are localized
  and derived from reader questions, not section IDs.
- Use prepared contributor figures exactly; never recalculate or reinterpret
  them as effort, merit, ownership, authorship, or intellectual property.
- Do not edit `.p2p/`, canonical `outputs/latest` targets, or the visible source
  export. Do not import, render, review, or approve.
- Do not create audience-specific variants. Language editions preserve the same
  project scope.

If the packet is stale or evidence is insufficient, stop with the exact
corrective command or record the limitation in the model. Never fill a gap with
an unsupported claim.
