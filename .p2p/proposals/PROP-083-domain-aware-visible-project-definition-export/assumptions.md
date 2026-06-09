# Assumptions

## Human-readable project definition is a primary output

The default export should serve humans first. It should be useful to an owner,
stakeholder, or implementing agent without requiring direct inspection of
managed `.p2p/` internals.

## P2P Engine must remain domain-generic

The default export cannot assume that the project is software. It must be able
to describe different verticals using the same generic project-definition
structure, while allowing vertical-specific profiles to add extra output forms.

## `outputs/` is an acceptable root-level convention

The MVP can use a fixed root-level `outputs/` directory. It does not need a
configurable destination yet because a single convention is clearer and reduces
implementation surface.

## `outputs/latest/project.md` is the canonical default export

The default project definition should be a single chaptered Markdown document.
Specialized profile exports can use additional folders and formats under
`outputs/latest/exports/`.

## Review history should be preserved

Each refresh should make it possible to inspect previous generated versions
through review directories such as `outputs/review-001`, `outputs/review-002`,
and later snapshots.

## Existing `.p2p/outputs` behavior may still be depended on

Even if current generated outputs appear disposable, compatibility must be
checked before removal or relocation. The proposal assumes implementation will
preserve or migrate existing public behavior deliberately.

## P2P memory contains enough structured input to synthesize the document

The first implementation can synthesize from accepted proposals, decisions,
requirements, risks, assumptions, choices, scope notes, readiness notes, and
related P2P artifacts. Gaps should be surfaced in the generated document rather
than silently invented.
