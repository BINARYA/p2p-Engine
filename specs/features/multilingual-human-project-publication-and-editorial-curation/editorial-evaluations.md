# Editorial Forward Evaluations

## Protocol

The forward evaluations ran on 2026-07-21 in isolated temporary repositories.
Each repository contained a minimal `.p2p` fixture, a prepared publication v2
packet/evidence index/profile, and the curator skill materialized from the
current source templates. The curator received only the skill and exact packet
path. Prompts did not contain expected prose and prohibited parent or adjacent
fixture reads.

Candidate triplets were accepted only after the real
`ProjectPublicationService.import_curated` and `validate` paths passed. A second
ephemeral Codex session then evaluated copies of the final Markdown files in a
directory containing no source evidence, models, accounting sidecars, or prior
attempts. The independent evaluator used Codex CLI 0.138.0 with model GPT-5.5.

## Final Documents

| Fixture | Edition | Markdown SHA-256 | Import/validation |
| --- | --- | --- | --- |
| software | `project-en` | `5ba18d678872f87954f2cbe347529f4be43b7248f11de2ab3170ab5443318ef8` | imported, passed, no findings |
| board game | `project-en` | `08d0c4b25f36e5a4afcf19945fc7eb211b741ef1103201d1fccf4f02d2488243` | imported, passed, no findings |
| generic fallback | `project-en` | `283e52d835eb6f12f69b6abe480bb479810db4356441f0e5365a740ff5dfd3cf` | imported, passed, no findings |
| software | `project-it` | `497854374afb46507e053451604ec6c6a36a962cea5762688308a93b0ba490b5` | imported, passed, no findings |

The contamination fixture placed the unrelated name `WaveKit` only in a
`process_only` evidence record. It appeared in none of the final documents.
Reader prose contained no proposal, decision, Change Set, Work, evidence, claim,
hash, path, readiness, or governance-chronology identifiers.

## Independent Rubric

Scores use the predefined 1..5 rubric and require every dimension to be at
least 4 with no zero-tolerance failure.

| Fixture | Autonomy | Vertical | Evidence | Language | Structure | Usefulness | Result |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| software EN | 4 | 5 | 5 | 5 | 5 | 4 | passed |
| board game EN | 4 | 5 | 5 | 5 | 5 | 4 | passed |
| generic fallback EN | 4 | 4 | 5 | 5 | 4 | 4 | passed |
| software IT | 5 | 5 | 5 | 5 | 5 | 5 | passed |

All evaluation payloads passed the strict
`validate_editorial_evaluation` codec. Their SHA-256 values were:

- software EN: `d25b1ac61edbc32ad290cafe230145c807e558eaede74bd0a1dd9dff97c96b50`;
- board game EN: `804009b436b5a19857f4fed0a60f609ef10d0fc5fcc5376d8781f98f9b285baa`;
- generic fallback EN: `633bb3a86e14439ab71b37f0ceb8eab129c01c06cbd849931a4c7e122f3bbcd2`;
- software IT: `415f4156966cc43121e0626c447f926626ad0f598f5252a21029140c1c31bb69`.

Citation erasure passed for all four documents: each remained understandable
without its sidecars. The independent EN/IT comparison recorded
`same_project_scope: true`, no actual scope drift, and hash
`c8f46790b8854bc5fe86befc5b500552add2ebb360701652a62858299690965d`.
The Italian edition elaborated quality constraints already present in the same
evidence; it did not add a new product capability or audience.

## Defects Found And Corrected

1. The first agent run omitted `curator_packet_sha256` because the packet did
   not explain how to compute its self-binding. The packet now declares the
   exact binding contract and the skill explains physical versus semantic hashes.
2. The next run invented equivalent-looking model/accounting keys because the
   reference described concepts but not exact nesting. The reference now includes
   exact structural YAML examples and accepted dimensions.
3. Board-game title coverage produced a false advisory because the validator
   recognized outline headings only at H2+. It now accepts the title at H1.
   Generic fallback prose omitted its non-title outline headings; the skill now
   requires every non-title outline heading exactly once as H2 or H3.
4. The first Italian attempt used mixed ASCII apostrophe accents and avoidable
   English fragments. The skill now requires natural UTF-8 orthography and
   consistent localization of generic terms while preserving proper names and
   protocol acronyms.

Every affected fixture was regenerated from a clean candidate surface after the
correction. Deterministic contracts were not weakened to admit failed samples.

## Limits

These evaluations prove contract usability and representative editorial
behavior, not universal prose quality. The fixtures are intentionally small,
the curator and independent evaluator used one model family, and final owner
review remains a separate edition-specific decision. Contribution localization
is covered by deterministic English/Italian chapter tests; the blind fixtures
used `contributions: omit` and therefore do not add a separate agentic
contribution-chapter quality claim.
