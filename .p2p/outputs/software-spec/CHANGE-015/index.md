# Software Spec - CHANGE-015 - Spec Export Validation MVP

## Summary

Add p2p spec export-validate CHANGE-XXX --target TARGET. The command validates that the export directory exists, manifest.yml is valid and coherent, index.md exists, and target-specific required files are present for generic, openspec, and speckit bundles.

## Source

- Change Set: `CHANGE-015`
- Change path: `.p2p/changes/CHANGE-015-spec-export-validation-mvp`
- Included proposals: PROP-029

## Targets

- execution_domains: software
- implementation_targets: local_cli
- spec_targets: p2p_spec
- export_targets: openspec, speckit
