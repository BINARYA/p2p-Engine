# Software Spec - CHANGE-013 - Software Spec Exporter MVP

## Summary

Add p2p spec export/status/show support for software spec export bundles. The MVP should export from .p2p/outputs/software-spec/CHANGE-XXX/ into .p2p/outputs/spec-export/CHANGE-XXX/TARGET/, starting with generic and openspec targets. Spec Kit remains a downstream target but is not implemented in this MVP unless the mapping becomes explicit.

## Source

- Change Set: `CHANGE-013`
- Change path: `.p2p/changes/CHANGE-013-software-spec-exporter-mvp`
- Included proposals: PROP-027

## Targets

- execution_domains: software
- implementation_targets: local_cli
- spec_targets: p2p_spec
- export_targets: openspec, speckit
