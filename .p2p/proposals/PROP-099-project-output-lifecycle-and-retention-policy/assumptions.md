# Assumptions - PROP-099

## Assumptions

- `.p2p/` remains the governed source of truth.
- `p2p project export` remains the deterministic complete export surface.
- The first implementation should not automatically replace the complete export with the curated document.
- `outputs/latest/project.curated.md` is the first owner-review candidate.
- `outputs/latest/project.pdf` is rendered from validated curated Markdown.
- The active vertical and project definition provide enough structure to guide document adaptation.
- A neutral PDF theme is sufficient for the first slice.
- Software specification and downstream export pipelines remain separate from human project publication.
- Manual owner review is acceptable in the first slice.
- Pipeline stages must remain separately reviewable so export, curation, validation, review, and rendering can be inspected or revised independently.
- The agentic curator is the main quality driver for a comprehensible document and for a robust narrative around the selected vertical and its specific characteristics.
- Deterministic preparation, validation, and rendering constrain and review the curator output, but do not replace semantic editorial judgment.
