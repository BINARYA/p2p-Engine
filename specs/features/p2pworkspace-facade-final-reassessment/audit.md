# P2PWorkspace Facade Final Reassessment Audit

## Commands Used

```bash
rg --files src/p2p_engine | rg '\.py$' | xargs wc -l | sort -nr | head -40
rg -n "^    def |^def |^class " src/p2p_engine/storage/filesystem.py src/p2p_engine/cli.py src/p2p_engine/cli_shared.py src/p2p_engine/mcp/tools.py src/p2p_engine/mcp/registry.py
rg -n "^def |^class |^@" src/p2p_engine/cli_commands src/p2p_engine/mcp/handlers
```

## Result

The reassessment does not justify another immediate `P2PWorkspace` extraction.
`storage.filesystem` is still large, but it now mostly contains facade methods
and service construction. The remaining size is a compatibility cost, not clear
domain ownership leakage.

The strongest remaining candidate is `mcp/registry.py`, because it is a single
large compatibility catalog for all MCP tool definitions. Splitting it by tool
domain can reduce change risk for future MCP additions while keeping
`tool_definitions()` and `TOOL_NAMES` stable.

## Recommended Follow-Up Feature

Create `specs/features/mcp-registry-domain-catalog-split/` before touching
runtime code. The feature should define:

- domain-specific MCP catalog modules;
- exact preservation rules for tool names, descriptions, schemas, and required
  fields;
- tests comparing before/after tool definitions;
- a step-by-step migration order that keeps `mcp.registry` as the public import
  point.
