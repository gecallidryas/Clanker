from __future__ import annotations

import argparse
import json
import sys
from typing import Any


def _read_message() -> dict[str, Any] | None:
    headers: dict[str, str] = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        stripped = line.decode("utf-8", errors="replace").strip()
        if not stripped:
            break
        if ":" in stripped:
            key, value = stripped.split(":", 1)
            headers[key.strip().lower()] = value.strip()
    try:
        content_length = int(headers["content-length"])
    except (KeyError, ValueError):
        return None
    body = sys.stdin.buffer.read(content_length)
    return json.loads(body.decode("utf-8"))


def _write_message(payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
    sys.stdout.buffer.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii"))
    sys.stdout.buffer.write(body)
    sys.stdout.buffer.flush()


def _tool_inventory(mode: str) -> list[dict[str, Any]]:
    if mode == "multi":
        return [
            {
                "name": "echo",
                "description": "Echo text back.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Text to echo"},
                    },
                },
            },
            {
                "name": "sum_numbers",
                "description": "Sum two integers.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "a": {"type": "integer", "description": "First integer"},
                        "b": {"type": "integer", "description": "Second integer"},
                    },
                },
            },
        ]
    return [
        {
            "name": "echo",
            "description": "Echo text back.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to echo"},
                },
            },
        }
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="success")
    args = parser.parse_args()

    if args.mode == "transport_fail":
        return 2

    while True:
        message = _read_message()
        if message is None:
            return 0

        method = message.get("method")
        request_id = message.get("id")
        params = message.get("params") or {}

        if method == "initialize":
            _write_message(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "fake-mcp", "version": "1.0"},
                    },
                }
            )
            continue

        if method == "tools/list":
            _write_message(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"tools": _tool_inventory(args.mode)},
                }
            )
            continue

        if method == "tools/call":
            name = str(params.get("name") or "")
            arguments = params.get("arguments") or {}
            if args.mode == "call_error":
                _write_message(
                    {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "isError": True,
                            "content": [{"type": "text", "text": "Remote failure"}],
                        },
                    }
                )
                continue
            if name == "sum_numbers":
                total = int(arguments.get("a") or 0) + int(arguments.get("b") or 0)
                _write_message(
                    {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "content": [{"type": "text", "text": f"sum={total}"}],
                            "structuredContent": {"sum": total},
                        },
                    }
                )
                continue
            text = str(arguments.get("text") or "")
            _write_message(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": f"echo:{text}"}],
                        "structuredContent": {"echo": text},
                    },
                }
            )
            continue

        if request_id is not None:
            _write_message(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": f"Unknown method {method}"},
                }
            )


if __name__ == "__main__":
    raise SystemExit(main())
