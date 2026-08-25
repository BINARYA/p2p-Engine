# Inventory - Project Shape Before Project-Owned Structure

## Purpose

This inventory records the schema-4 coupling reviewed before introducing the
canonical `ProjectStructure`. It distinguishes state that defines the live
project shape from source-release and transitional compatibility artifacts.

## Existing Assumptions And Resolution

| Area | Previous assumption | Step-3 resolution |
| --- | --- | --- |
| Initialization | Generic or exact vertical selection remained the live shape. | Resolve one effective source and copy it into revision 1 of the project-owned structure. |
| Active vertical | `.p2p/project/vertical.yml` identified current sections. | Current section reads use `ProjectStructure`; active vertical state is transitional release metadata only. |
| Vertical lock | `.p2p/project/vertical.lock.yml` guarded the live structure. | `StructureOrigin` records immutable provenance; the lock is optional and non-canonical in schema 4. |
| Definition | Section and field validation resolved the active pack. | Definition state records structure ID, revision and checksum and validates IDs against the current structure. |
| Rubrics | Rubrics were selected from starter or vertical state. | Effective criteria are copied into the structure; readiness rebasing is deferred to `rebase-readiness-on-project-structure`. |
| Questions | Question declarations came from the selected pack. | Effective questions are copied with stable IDs; question workflow convergence remains a later consumer update. |
| Artifacts | Expected artifacts were read from the active pack. | Effective artifact declarations are copied into the structure. |
| Section reads | `project sections` listed active/fallback vertical sections. | Unqualified reads adapt the current project structure; explicit vertical reads remain catalog inspection. |
| Snapshot | Project snapshot exposed active vertical and lock only. | Snapshot also exposes canonical structure identity, revision, checksum, origin and active counts. |
| Validation | Workspace validity depended conditionally on vertical lock files. | Structure and event ledger are canonical; active vertical, lock and definition files are optional schema-4 artifacts. |
| Mutation authority | No capability existed for direct project-shape edits. | Add, metadata update and reorder require `project.structure.edit`. |
| Mutation durability | Shape changes used vertical lifecycle-specific transactions. | Simple changes atomically commit structure, event and compact mutation receipt. |

## Canonical Private Layout

The public contract does not expose these paths. Schema 4 persists the logical
aggregate as:

```text
.p2p/project/structure.yml
.p2p/project/structure-events.yml
```

`structure.yml` contains the complete normalized aggregate. The event ledger is
append-only evidence with one event per structure revision. A successful simple
mutation writes both files and its receipt in one workspace transaction.

## Identity And Normalization

- Structure and element IDs are bounded lower-case identifiers.
- Section, question, criterion and artifact IDs are project-wide within their
  kind; field IDs are scoped by section and therefore identified by
  `(section_id, field_id)`.
- Editable text is trimmed, internal whitespace is normalized and control
  characters are rejected.
- Booleans and integer ordering fields are parsed strictly.
- Active section order is the exact contiguous range `0..n-1`.
- Generated IDs use a deterministic SHA-256 suffix when a source slug exceeds
  the public ID bound.

## Semantic Checksum

The checksum is SHA-256 over canonical JSON semantics containing structure ID
and the ordered section, field, question, criterion and artifact collections.
It excludes revision and origin so provenance metadata cannot alter structural
meaning. Storage serialization is complete; public serialization is bounded
and reports `total`, `returned` and `truncated` for every collection.

## Deliberately Deferred Coupling

The following consumers still have dedicated later features and are not
silently redefined here:

- memory classification and unassigned content;
- referenced-element retirement and impact disposition;
- readiness v2 and classification debt;
- vertical export, replacement, merge and restore;
- final removal of transitional active-vertical CLI/MCP guidance.

No schema-3 workspace adapter or old-memory fallback is introduced.
