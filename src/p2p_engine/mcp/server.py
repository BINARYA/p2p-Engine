from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, TextIO

from p2p_engine.mcp.tools import call_tool, tool_definitions

JSONRPC_VERSION = "2.0"


def main() -> None:
    parser = argparse.ArgumentParser(description="P2P Engine MCP stdio server")
    parser.add_argument("--root", default=str(Path.cwd()), help="Default P2P project root")
    args = parser.parse_args()
    serve(default_root=Path(args.root))


def serve(
    *,
    default_root: Path,
    stdin: TextIO = sys.stdin,
    stdout: TextIO = sys.stdout,
) -> None:
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        response = handle_message(line, default_root=default_root)
        if response is None:
            continue
        stdout.write(json.dumps(response, separators=(",", ":")) + "\n")
        stdout.flush()


def handle_message(message: str, *, default_root: Path) -> dict[str, object] | None:
    try:
        request = json.loads(message)
    except json.JSONDecodeError as exc:
        return _error(None, -32700, f"Parse error: {exc.msg}")
    if not isinstance(request, dict):
        return _error(None, -32600, "Invalid Request")

    request_id = request.get("id")
    method = str(request.get("method") or "")
    params = request.get("params", {})
    if params is None:
        params = {}
    if not isinstance(params, dict):
        return _error(request_id, -32602, "Invalid params")

    try:
        if method == "initialize":
            return _result(
                request_id,
                {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "p2p-engine", "version": "0.1.0"},
                    "capabilities": {"tools": {}},
                },
            )
        if method == "notifications/initialized":
            return None
        if method == "tools/list":
            return _result(request_id, {"tools": tool_definitions()})
        if method == "tools/call":
            tool_name = str(params.get("name") or "")
            arguments = params.get("arguments") or {}
            if not isinstance(arguments, dict):
                return _error(request_id, -32602, "Tool arguments must be an object")
            arguments.setdefault("root", default_root.as_posix())
            payload = call_tool(tool_name, arguments)
            return _result(
                request_id,
                {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(payload, sort_keys=True),
                        }
                    ],
                    "isError": False,
                },
            )
        return _error(request_id, -32601, f"Method not found: {method}")
    except ValueError as exc:
        return _error(request_id, -32602, str(exc))


def _result(request_id: Any, result: dict[str, object]) -> dict[str, object]:
    return {"jsonrpc": JSONRPC_VERSION, "id": request_id, "result": result}


def _error(request_id: Any, code: int, message: str) -> dict[str, object]:
    return {
        "jsonrpc": JSONRPC_VERSION,
        "id": request_id,
        "error": {"code": code, "message": message},
    }


if __name__ == "__main__":
    main()
