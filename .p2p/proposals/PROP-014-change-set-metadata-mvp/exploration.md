# Exploration - PROP-014

## Interpretation

PROP-014 implements the first Change Set slice from PROP-013. It must remain metadata-only: the CLI creates `.p2p/changes/CHANGE-XXX/` artifacts but does not create Git commits, branches, tags, or merges.

## MVP Commands

```bash
p2p change create --from PROP-013
p2p change status
p2p change policy CHANGE-001
```

## Key Constraint

`p2p change create` can only use accepted proposals as binding source. Draft proposals can be referenced later, but cannot create operational Change Sets.

## Generated Structure

```text
.p2p/changes/
  CHANGE-001-managed-git-adapter-and-change-set-model/
    change.md
    included-proposals.yml
    referenced-proposals.yml
    excluded-alternatives.yml
    included-decisions.yml
    impact-map.yml
    git-policy.yml
    execution-plan.md
    tasks.yml
```

## Git Policy

```yaml
git_policy:
  mode: managed
  operation_level: metadata_only
  expose_git_details: false
  commits:
    auto_commit: false
  branches:
    auto_create: false
  tags:
    auto_create: false
```
