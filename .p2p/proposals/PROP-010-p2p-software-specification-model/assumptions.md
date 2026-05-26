# Assumptions - PROP-010

- P2P proposal artifacts remain the source of truth for discussion, governance, and decisions.
- `.p2p/project/` contains rationalized derived project state.
- The first software spec model can be Markdown-first, with YAML indexes only where needed.
- Exporters should consume normalized P2P project state rather than raw proposal directories.
- Automatic refresh should be deterministic and should not require AI by default.
- AI-assisted rationalization can be added later through prompt/import commands.
