---
name: p2p-project-curator
description: Curate P2P Engine generated project exports into one canonical, human-readable, vertical-aware project publication. Use when Codex or another agent receives outputs/latest/curator-input.md or needs to transform outputs/latest/project.md into outputs/latest/project.curated.md for the human project publication pipeline.
---

<!--
Managed by P2P Engine.
Adapter: codex
Template: codex-p2p-project-curator-skill-v1
Do not edit generated sections unless you accept drift.
-->

# P2P Project Curator

## Role

Curate the generated P2P project export into one coherent human project document.
Treat `outputs/latest/project.md` and `outputs/latest/curator-input.md` as input
evidence. Treat `.p2p/` as the authoritative source of truth.

Do not mutate `.p2p/`. Do not accept, reject, approve, or decide governance
items. Do not create audience-specific variants.

## Required Input

Use the publication packet first:

```text
outputs/latest/curator-input.md
```

The packet provides:

- source export path and hash;
- P2P source fingerprint;
- publication profile path and hash;
- active vertical summary when available;
- source-of-truth boundary;
- traceability inputs;
- the complete generated export or the path to it.

If the packet is missing or stale, ask the user or orchestrator to run:

```bash
p2p project publish prepare
```

## Output Contract

Produce exactly one canonical Markdown document:

```text
outputs/latest/project.curated.md
```

The document represents the project itself: "project X in vertical Y is this".
Do not produce commercial, technical, investor, executive, or audience-specific
versions. Downstream users may derive those separately.

## Editorial Rules

Write a project-first narrative. Identify the central project thesis, then
organize supporting evidence around product capabilities, operational concerns,
vertical requirements, risks, assumptions, and open questions.

Adapt headings, terminology, grouping, and explanatory order to the active
vertical when there is vertical evidence. If no vertical is available, use a
generic project-first structure and state that vertical evidence is unavailable.

Distinguish these states explicitly where they matter:

- current implemented capability;
- accepted but not yet implemented work;
- planned or partial work;
- pending owner decision;
- missing evidence;
- legacy context;
- risk;
- assumption;
- open question.

Preserve traceability for material claims. Prefer compact references such as
proposal IDs, decision IDs, Change Set IDs, Work IDs, or artifact paths. Avoid
turning the main body into a chronological proposal dump.

Remove placeholders, repeated boilerplate, empty sections, internal governance
noise, and duplicated headings from the main publication body.

## Required Structure

Use exactly one H1. Include at least:

- executive summary;
- project identity and vertical framing;
- current project shape;
- planned and pending work;
- relevant risks, assumptions, and open questions;
- source-of-truth statement that `.p2p/` remains authoritative;
- traceability notes for material claims.

Keep Markdown renderer-friendly: simple headings, paragraphs, lists, tables, and
code blocks are allowed. Avoid embedded scripts, external asset dependencies, and
layout tricks that would make PDF rendering fragile.

## Lifecycle And Drift

The canonical source for these instructions is the P2P Engine release template.
Adapter-specific files under `.agents/`, `.codex/`, `CLAUDE.md`, or other agent
surfaces are generated outputs managed by the agent integration lifecycle.

Refresh or update generated adapter files through `p2p agent install`,
`p2p agent update`, or `p2p agent instructions refresh`. Do not treat generated
adapter files as release-template source.

## Forbidden Behaviors

Do not:

- edit `.p2p/`;
- overwrite `outputs/latest/project.md`;
- claim publication approval;
- hide unresolved risks or open questions;
- invent implementation status not supported by evidence;
- split the canonical document into multiple audience variants;
- remove source-of-truth warnings;
- silently ignore hash or fingerprint mismatch warnings in the packet.
