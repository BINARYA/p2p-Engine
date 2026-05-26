# Software Spec - CHANGE-014 - Spec Kit Export Mapping MVP

## Summary

Add speckit as a supported p2p spec export target. Export to .p2p/outputs/spec-export/CHANGE-XXX/speckit/specs/CHANGE-XXX-slug/ with spec.md, plan.md, research.md, data-model.md, quickstart.md, tasks.md, contracts/README.md, and manifest.yml. The mapping should preserve P2P provenance and mark unresolved implementation details as NEEDS CLARIFICATION instead of inventing them.

## Source

- Change Set: `CHANGE-014`
- Change path: `.p2p/changes/CHANGE-014-spec-kit-export-mapping-mvp`
- Included proposals: PROP-028

## Targets

- execution_domains: software
- implementation_targets: local_cli
- spec_targets: p2p_spec
- export_targets: openspec, speckit
