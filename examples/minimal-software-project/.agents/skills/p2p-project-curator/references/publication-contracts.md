<!--
Managed by P2P Engine.
Adapter: codex
Template: codex-p2p-project-curator-publication-contracts-v3
Generation: agent-template-generation-v2:agent-capabilities-v5:codex-p2p-project-curator-publication-contracts-v3
Do not edit generated sections unless you accept drift.
-->

# Publication Contracts

The packet declares all candidate paths and the exact binding contract. Do not
rename them. Because a packet cannot embed its own physical hash, compute
`curator_packet_sha256` from the prepared packet file exactly as instructed.

## Project Model

Use these exact field names and nesting; values in angle brackets are
instructions, not literal output:

```yaml
schema_version: 2
edition:
  key: <edition key>
  language: <canonical language>
  output_name: <output name>
bindings:
  curator_packet_sha256: <physical packet hash>
  evidence_index_sha256: <prepared evidence semantic hash>
  source_export_sha256: <prepared source export hash>
  source_fingerprint_sha256: <prepared source fingerprint>
  profile_sha256: <prepared profile hash>
project:
  title: <reader-facing title>
  thesis: <evidence-supported thesis>
  vertical_id: <prepared vertical id or generic>
reader_questions:
  - id: RQ-001
    question: <localized question>
    answered_by: [CLM-001]
claims:
  - id: CLM-001
    statement: <evidence-supported statement>
    evidence_ids: [EVD-...]
outline:
  - id: OUT-001
    role: <semantic role>
    heading: <localized heading>
    claim_ids: [CLM-001]
vertical_coverage:
  - section_id: <required section id>
    disposition: covered
    outline_ids: [OUT-001]
editorial_assessment:
  rubric_version: publication-editorial-rubric-v2
  results:
    - dimension: autonomy
      score: 4
      evaluator: self
```

The model contains:

- `edition` with matching `key` and canonical `language`;
- `bindings` copied exactly from the packet contract, including the computed
  packet hash and the prepared evidence semantic hash;
- `project.title`, `project.thesis`, and the prepared `project.vertical_id`;
- `project.vertical_guidance_unavailable_reason` when `vertical_id` is `generic`;
- unique `reader_questions` with `answered_by` claim IDs;
- unique `claims` with statements and evidence IDs or explicit owner-input
  provenance;
- unique adaptive `outline` sections with role, localized heading, and claim IDs;
- one `vertical_coverage` disposition for every required vertical section;
- `editorial_assessment.results` with exactly one `self` row scored 4 or 5 for
  each dimension: `autonomy`, `vertical_coherence`, `evidence_use`,
  `language_consistency`, `structure`, and `reader_usefulness`;
- `contributions` only when the profile requires it, with prepared data
  unchanged plus a localized `reader_limitation` used verbatim in the document.

## Evidence Accounting

Use this exact field naming and nesting:

```yaml
schema_version: 2
edition_key: <edition key>
bindings:
  model_sha256: <physical hash of completed candidate model>
  evidence_index_sha256: <prepared evidence semantic hash>
evidence:
  - evidence_id: EVD-...
    disposition: used
    claim_ids: [CLM-001]
    reason: <optional for used/supporting_context; required otherwise>
```

The mapping contains one unique `evidence` record for every evidence ID.
Allowed dispositions are `used`, `supporting_context`, `historical`, `duplicate`,
`contradictory`, `insufficient`, `not_applicable`, and `process_only`.

`used` records require claim IDs. Excluded records require reasons and no claim
IDs. Process-only evidence must remain process-only. Every claim/evidence link is
bidirectional between model and accounting.

## Reader Markdown

Use UTF-8, exactly one H1, balanced fenced code blocks, renderer-friendly
Markdown, and the selected language. Render the title outline heading as the H1
and every other outline heading exactly once as an H2 or H3. Internal workflow
IDs and traceability metadata belong only in the YAML sidecars. Use the natural
Unicode orthography of the selected language; do not transliterate diacritics
as ASCII apostrophes. Keep proper names and protocol acronyms when needed, but
translate generic descriptive terms consistently.
