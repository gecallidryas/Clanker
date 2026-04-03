from __future__ import annotations

import asyncio
import json
import os
from typing import Any


class MCPTransportError(RuntimeError):
    pass


def _frame_message(payload: dict[str, Any]) -> bytes:
    body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
    return f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body


async def _read_message(stream: asyncio.StreamReader) -> dict[str, Any]:
    headers: dict[str, str] = {}
    while True:
        line = await stream.readline()
        if not line:
            raise MCPTransportError("MCP server closed the stream.")
        stripped = line.decode("utf-8", errors="replace").strip()
        if not stripped:
            break
        if ":" in stripped:
            key, value = stripped.split(":", 1)
            headers[key.strip().lower()] = value.strip()

    try:
        content_length = int(headers["content-length"])
    except (KeyError, ValueError) as exc:
        raise MCPTransportError("Invalid MCP message headers.") from exc

    body = await stream.readexactly(content_length)
    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise MCPTransportError("Invalid JSON payload from MCP server.") from exc
    if not isinstance(payload, dict):
        raise MCPTransportError("MCP server returned a non-object payload.")
    return payload


async def _send_request(
    writer: asyncio.StreamWriter,
    reader: asyncio.StreamReader,
    *,
    request_id: int,
    method: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    request = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": params or {},
    }
    writer.write(_frame_message(request))
    await writer.drain()

    while True:
        response = await _read_message(reader)
        if response.get("id") != request_id:
            continue
        if "error" in response:
            error = response.get("error") or {}
            raise MCPTransportError(str(error.get("message") or "Unknown MCP error"))
        result = response.get("result")
        if not isinstance(result, dict):
            raise MCPTransportError("MCP server returned an invalid result.")
        return result


async def _send_notification(writer: asyncio.StreamWriter, *, method: str, params: dict[str, Any] | None = None) -> None:
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params or {},
    }
    writer.write(_frame_message(payload))
    await writer.drain()


async def _run_stdio_session(
    command: list[str],
    env: dict[str, str] | None,
    *,
    operation: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not command:
        raise MCPTransportError("MCP command is required.")

    process = await asyncio.create_subprocess_exec(
        *command,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={**os.environ, **(env or {})},
    )
    if process.stdin is None or process.stdout is None:
        raise MCPTransportError("Failed to start MCP stdio session.")

    try:
        await _send_request(
            process.stdin,
            process.stdout,
            request_id=1,
            method="initialize",
            params={
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "FemboiBot", "version": "1.0"},
            },
        )
        await _send_notification(process.stdin, method="notifications/initialized")
        result = await _send_request(
            process.stdin,
            process.stdout,
            request_id=2,
            method=operation,
            params=params,
        )
        return result
    finally:
        if process.stdin:
            process.stdin.close()
        try:
            await asyncio.wait_for(process.wait(), timeout=2.0)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()


async def list_tools(*, command: list[str], env: dict[str, str] | None = None) -> list[dict[str, Any]]:
    result = await _run_stdio_session(command, env, operation="tools/list")
    tools = result.get("tools")
    if not isinstance(tools, list):
        raise MCPTransportError("MCP tools/list returned no tools array.")
    normalized: list[dict[str, Any]] = []
    for item in tools:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "name": str(item.get("name") or "").strip(),
                "description": str(item.get("description") or "").strip(),
                "inputSchema": item.get("inputSchema") if isinstance(item.get("inputSchema"), dict) else {},
            }
        )
    return normalized


async def call_tool(
    *,
    command: list[str],
    env: dict[str, str] | None,
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    result = await _run_stdio_session(
        command,
        env,
        operation="tools/call",
        params={"name": tool_name, "arguments": arguments},
    )
    return result
