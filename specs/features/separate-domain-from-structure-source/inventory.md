# Domain And Structure-Source Inventory

## Structural Domain Coupling Found

- `services/project_maturity.py`: closed domain enum, domain-owned rubric
  templates, unresolved-domain next actions and maturity wording.
- `services/project_initialization.py`: `project_domain` selects rubric content
  and is duplicated in `project.yml` and `project/domain.yml`.
- `storage/filesystem.py`: initialization fingerprints and replay compare the
  legacy scalar domain while vertical selection is a second independent source.
- `cli.py`: `--domain` is a closed template selector and may be combined with
  `--vertical` or `--vertical-pack`.
- `mcp/catalog/maintenance.py` and `mcp/handlers/maintenance.py`: the same
  closed template enum is exposed through `p2p_init_project`.
- `services/workspace_schema.py`: a software-domain fallback advisory assigns
  structural meaning to the domain.
- `services/project_snapshot.py`: reads the duplicated scalar domain from
  `project.yml` instead of a versioned domain contract.
- `resources/verticals`: specialized bundled structures use schema 2 and share
  `base_project` as a lineage ancestor.
- maintained CLI/install/concepts/MCP documentation and generated agent
  guidance still describe domain templates.

## Convergence Direction

- Canonical classification: `.p2p/project/domain.yml`, contract
  `p2p-project-domain/v1`.
- Canonical initialization provenance: `.p2p/project/structure-source.yml`,
  contract `p2p-structure-source/v1`.
- Initialization source: exactly one of `generic`, `empty`, or one resolved
  exact vertical release.
- Specialized structures: bundled schema-3 vertical releases with optional
  advisory domain metadata.
- Domain writes: shared typed-authority service, atomic writer and durable
  mutation receipt; no structure candidate is part of the mutation.
