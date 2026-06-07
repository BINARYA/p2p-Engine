# P2PWorkspace Context Packet Service Extraction Design

## Current Runtime Shape

`storage/filesystem.py` still owns `context_packet()` and related helper
methods:

- `_default_context_artifacts()`;
- `_context_artifact()`;
- `_context_allowed_commands()`;
- `_short_text()`.

This behavior is read-only, but it coordinates many services through the
workspace facade and is consumed by CLI and MCP context commands.

## Target Shape

Add `src/p2p_engine/services/context_packets.py` with:

- `ContextPacket`;
- `ContextPacketService`;
- local `_short_text()` helper;
- default artifact selection;
- target artifact selection;
- allowed command calculation.

`P2PWorkspace.context_packet()` remains the compatibility facade and delegates
to the service.

## Service Dependencies

The service receives callbacks for:

- validation;
- registry status;
- project state status;
- proposal summaries and proposal details;
- choice statuses and choice details;
- change statuses and change details;
- work summaries and work details;
- next actions;
- project name.

The service does not write files and does not import CLI/MCP modules.

## Compatibility Rules

- Preserve budget values: `small`, `medium`.
- Preserve uppercase target normalization.
- Preserve target prefix support and error message.
- Preserve compact context guidance strings.
- Preserve exact command strings in context packets.

## Verification Map

```bash
.venv/bin/pytest tests/test_context_packet_service.py
.venv/bin/pytest tests/test_cli.py -k "context"
.venv/bin/pytest tests/test_mcp.py -k "context"
.venv/bin/p2p validate
.venv/bin/pytest
```

## Implementation Evidence

Implemented in `src/p2p_engine/services/context_packets.py`.

`P2PWorkspace.context_packet()` now delegates to `ContextPacketService`. The
service receives callbacks to existing runtime services and remains read-only.

Verification completed:

```bash
.venv/bin/pytest tests/test_context_packet_service.py
.venv/bin/pytest tests/test_cli.py -k "context"
.venv/bin/pytest tests/test_mcp.py -k "context"
.venv/bin/p2p validate
.venv/bin/pytest
```

Result: focused tests passed, validation reported 0 findings, and the full
suite passed with 351 tests.
