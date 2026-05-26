# Requirements

## Functional Requirements

### PROP-031 - Multi-Branch Work Scan MVP

Add p2p work scan to read local branches matching p2p/work/* through Git plumbing, discover .p2p/work/WORK-XXX/manifest.yml files on those branches, and write an aggregated .p2p/registries/work.yml. The command must be read-only with respect to Git: no checkout, fetch, branch creation, commit, PR, or merge.

## Non-Goals / Exclusions

- Automatic Git commits, branches, tags, or merges.

## Constraints

Do not treat raw proposal discussion as implementation requirements without accepted scope.

## Open Questions

Not specified yet.
