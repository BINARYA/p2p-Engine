# Assumptions

- P2P CLI and explicit MCP write tools remain the public write interface for governed state.
- Existing generated narrative artifacts can be made safer without removing all human-readable files from `.p2p/`.
- The first implementation slice can choose between omitting placeholders, marking generated files, or adding explicit import/edit primitives.
- The decision root may differ from current working directory, but repository topology is local setup and not core product direction.
- Software-specific specs remain in PROP-094 and should not drive this core proposal.
