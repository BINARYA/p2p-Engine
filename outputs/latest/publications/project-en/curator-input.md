# Human Project Publication Curator Input

## Edition

- key: `project-en`
- language: `en`
- output_name: `project`
- audience_variant: `false`
- reader_knowledge_of_p2p: `none`

## Complete Evidence Boundary

- source_export: `outputs/latest/project.md`
- source_export_sha256: `f7a8d13d0471d4845d4e55e5a9bc0acf6233b1427ee0c1d1a8ec63d53352e009`
- source_fingerprint_sha256: `cc52e887730dd3c6ca238574f9c0f06f74a139077084ac7799d0eaeb76f759b9`
- evidence_index: `outputs/latest/publication-evidence.yml`
- evidence_index_sha256: `5685fc281c49701a8e9f62fde31e2bf68a9a68eba253f35d0de6b7abcf3aa433`
- evidence_index_semantic_sha256: `848d5959c20c86ebd3509cec4ee5caf4bc6d9f56632bbaa0d7987d163e455579`
- profile: `outputs/latest/publications/project-en/profile.yml`
- profile_sha256: `11cb02e9d4a2f1a5d0967e7808153dcb390c69bf440d22ce9cc5b2d9fb25c587`

The source export is available for complete research but is not the document outline.
The evidence index contains complete payloads or complete hash-bound source locators.
Use no implicit knowledge from adjacent projects, brands, or prior conversations.

## Exact Candidate Outputs

- markdown: `drafts/project-publication/project-en.md`
- project_model: `drafts/project-publication/project-en.model.yml`
- evidence_accounting: `drafts/project-publication/project-en.evidence.yml`

## Candidate Binding Contract

Set the project-model bindings exactly as follows:

- `curator_packet_sha256`: physical SHA256 of `outputs/latest/publications/project-en/curator-input.md`
- `evidence_index_sha256`: `848d5959c20c86ebd3509cec4ee5caf4bc6d9f56632bbaa0d7987d163e455579`
- `source_export_sha256`: `f7a8d13d0471d4845d4e55e5a9bc0acf6233b1427ee0c1d1a8ec63d53352e009`
- `source_fingerprint_sha256`: `cc52e887730dd3c6ca238574f9c0f06f74a139077084ac7799d0eaeb76f759b9`
- `profile_sha256`: `11cb02e9d4a2f1a5d0967e7808153dcb390c69bf440d22ce9cc5b2d9fb25c587`

The packet cannot embed its own physical hash. Compute it from the packet file
after prepare has completed. In evidence accounting, set `model_sha256` to the
physical SHA256 of the completed candidate model and reuse the evidence semantic
hash above as `evidence_index_sha256`.
Use the exact model and accounting field names from
`references/publication-contracts.md`; do not substitute equivalent-looking keys.

## Editorial Contract

1. Read the active vertical and every evidence-index entry.
2. Build the project model before writing prose.
3. Account for every evidence ID exactly once.
4. Write an autonomous project document for a reader who does not know P2P workflow.
5. Do not expose internal IDs, hashes, paths, readiness, or upstream governance status.
6. Explain proposal or lifecycle concepts only when they are evidenced subject matter of the project.
7. Use the selected language consistently and keep project scope invariant across editions.
8. Use the prepared contributor figures exactly when the profile includes Contributions.
9. Complete the editorial rubric and write only the candidate triplet.
10. Do not import, render, review, approve, or edit `.p2p/`.

## Import Command

```bash
p2p project publish import drafts/project-publication/project-en.md \
  --model drafts/project-publication/project-en.model.yml \
  --evidence-accounting drafts/project-publication/project-en.evidence.yml \
  --language en --output-name project
```
