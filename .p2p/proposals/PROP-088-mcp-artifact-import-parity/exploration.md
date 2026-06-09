# Exploration - PROP-088

The real MCP test exposed a narrow parity gap rather than a general MCP failure.
The core CLI can already import impact and exploration outputs through public
commands, but MCP clients currently have only prompt generation and artifact
state tools. This means an agent can identify weak or missing artifacts, yet it
cannot complete the artifact content update through MCP.

The useful refinement is to add explicit MCP tools that call the same import
services as the CLI. This keeps `.p2p/` managed by P2P Engine, preserves
validation behavior, and avoids adding an arbitrary file-write surface.

