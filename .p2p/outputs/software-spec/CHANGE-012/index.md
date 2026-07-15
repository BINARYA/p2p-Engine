# Software Spec - CHANGE-012 - P2P Software Spec Generator MVP

## Summary

Add p2p spec refresh/status/show/prompt/import. The refresh command deterministically generates a minimal software spec from a Change Set. The prompt command generates an AI/human refinement prompt from the deterministic spec and source context. The import command validates and imports refined spec artifacts.

## Source

- Change Set: `CHANGE-012`
- Change path: `.p2p/changes/CHANGE-012-p2p-software-spec-generator-mvp`
- Included proposals: PROP-026

## Targets

- execution_domains: software
- implementation_targets: local_cli
- spec_targets: p2p_spec
- export_targets: openspec, speckit
