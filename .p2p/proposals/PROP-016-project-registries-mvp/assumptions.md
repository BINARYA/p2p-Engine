# Assumptions - PROP-016

- Registries are generated and versioned.
- Registries are not primary source artifacts.
- Registry refresh should be deterministic.
- AI prompts can use registries as compact context.
- Exporters should prefer registries for discovery, then load source artifacts for detail.
- The first implementation can remain YAML-only.
