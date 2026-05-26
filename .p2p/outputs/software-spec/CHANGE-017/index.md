# Software Spec - CHANGE-017 - Multi-Branch Work Scan MVP

## Summary

Add p2p work scan to read local branches matching p2p/work/* through Git plumbing, discover .p2p/work/WORK-XXX/manifest.yml files on those branches, and write an aggregated .p2p/registries/work.yml. The command must be read-only with respect to Git: no checkout, fetch, branch creation, commit, PR, or merge.

## Source

- Change Set: `CHANGE-017`
- Change path: `.p2p/changes/CHANGE-017-multi-branch-work-scan-mvp`
- Included proposals: PROP-031

## Targets

- execution_domains: software
- implementation_targets: local_cli
- spec_targets: p2p_spec
- export_targets: openspec, speckit
