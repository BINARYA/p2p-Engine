# Open Questions - PROP-099

## Resolved Owner Inputs

### Q001 - Should PROP-099 include PDF rendering?

Resolved. PROP-099 should define the full Human Project Publication Pipeline: complete export, curator skill, publication validation, owner review, and neutral PDF renderer.

### Q002 - Should the first slice overwrite `outputs/latest/project.md`?

Resolved. No. In the first slice `outputs/latest/project.md` remains the complete export, `outputs/latest/project.curated.md` is the curated candidate, and `outputs/latest/project.pdf` is rendered from the curated validated Markdown.

### Q003 - Should curation be deterministic or agentic?

Resolved. Curation should use a hybrid model. The engine prepares input and validates output; the skill performs semantic synthesis; the owner reviews; the renderer handles presentation only.

## Remaining Open Questions

No blocking owner questions remain for proposal refinement. Implementation details such as exact CLI names and renderer library can be resolved during local specs after acceptance.
