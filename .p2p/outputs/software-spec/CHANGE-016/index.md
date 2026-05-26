# Software Spec - CHANGE-016 - Managed Work and Multi-Branch Visibility Policy

## Summary

Introduce P2P Work as the user-facing abstraction over future Git branches. Define levels from advisory to handoff plan, managed branch, managed commit, managed review, and owner-controlled merge. Implement p2p work plan/list/show to create and inspect .p2p/work/WORK-XXX/manifest.yml for validated spec exports. This first MVP must not create branches, commits, PRs, or merges.

## Source

- Change Set: `CHANGE-016`
- Change path: `.p2p/changes/CHANGE-016-managed-work-and-multi-branch-visibility-policy`
- Included proposals: PROP-030

## Targets

- execution_domains: software
- implementation_targets: local_cli
- spec_targets: p2p_spec
- export_targets: openspec, speckit
