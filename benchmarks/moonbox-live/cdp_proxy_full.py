#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import os
import signal
import sys
import urllib.parse


HEADER_LIMIT_BYTES = 65536
RESPONSE_HEADER_LIMIT_BYTES = 65536
DISCOVERY_BODY_LIMIT_BYTES = 1048576
BUFFER_SIZE = 65536
DISCOVERY_PATHS = {"/json", "/json/", "/json/list", "/json/version"}
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


def request_metadata(data: bytes) -> tuple[str, str | None, bool]:
    header, separator, _ = data.partition(b"\r\n\r\n")
    if not separator:
        return "", None, False

    lines = header.split(b"\r\n")
    request_parts = lines[0].decode("latin-1").split()
    if len(request_parts) < 2:
        return "", None, False
    path = urllib.parse.urlsplit(request_parts[1]).path

    public_host: str | None = None
    connection_tokens: set[str] = set()
    upgrade = ""
    for line in lines[1:]:
        name, separator, value = line.partition(b":")
        if not separator:
            continue
        name_text = name.decode("latin-1").strip().lower()
        value_text = value.decode("latin-1").strip()
        if name_text == "host" and public_host is None:
            public_host = value_text
        elif name_text == "connection":
            connection_tokens.update(token.strip().lower() for token in value_text.split(","))
        elif name_text == "upgrade":
            upgrade = value_text.lower()
    return path, public_host, "upgrade" in connection_tokens and upgrade == "websocket"


def rewrite_debugger_url(value: str, public_host: str, upstream_port: int) -> str:
    try:
        parsed = urllib.parse.urlsplit(value)
        port = parsed.port
        public = urllib.parse.urlsplit(f"//{public_host}")
        public_hostname = public.hostname
    except ValueError:
        return value
    if (
        parsed.scheme not in {"ws", "wss"}
        or parsed.hostname not in LOOPBACK_HOSTS
        or port != upstream_port
        or public_hostname is None
    ):
        return value
    scheme = "ws" if public_hostname.lower() in LOOPBACK_HOSTS else "wss"
    return urllib.parse.urlunsplit((scheme, public_host, parsed.path, parsed.query, parsed.fragment))


def rewrite_debugger_urls(value: object, public_host: str, upstream_port: int) -> bool:
    changed = False
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "webSocketDebuggerUrl" and isinstance(item, str):
                rewritten = rewrite_debugger_url(item, public_host, upstream_port)
                if rewritten != item:
                    value[key] = rewritten
                    changed = True
            elif rewrite_debugger_urls(item, public_host, upstream_port):
                changed = True
    elif isinstance(value, list):
        for item in value:
            if rewrite_debugger_urls(item, public_host, upstream_port):
                changed = True
    return changed


def rewrite_discovery_response(
    data: bytes,
    request_path: str,
    public_host: str | None,
    upstream_port: int,
) -> bytes:
    if request_path not in DISCOVERY_PATHS or not public_host:
        return data

    header, separator, body = data.partition(b"\r\n\r\n")
    if not separator or len(header) > RESPONSE_HEADER_LIMIT_BYTES or len(body) > DISCOVERY_BODY_LIMIT_BYTES:
        return data

    lines = header.split(b"\r\n")
    content_length: int | None = None
    content_length_index: int | None = None
    for index, line in enumerate(lines[1:], start=1):
        name, field_separator, value = line.partition(b":")
        if not field_separator:
            continue
        name = name.strip().lower()
        if name == b"transfer-encoding":
            return data
        if name == b"content-length":
            try:
                content_length = int(value.strip())
            except ValueError:
                return data
            content_length_index = index
    if content_length is None or content_length < 0 or content_length != len(body):
        return data

    try:
        payload = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return data
    if not rewrite_debugger_urls(payload, public_host, upstream_port):
        return data

    rewritten_body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()
    assert content_length_index is not None
    original_name = lines[content_length_index].split(b":", 1)[0]
    lines[content_length_index] = original_name + b": " + str(len(rewritten_body)).encode("ascii")
    return b"\r\n".join(lines) + separator + rewritten_body


def rewrite_host_header(data: bytes, upstream_host: str, upstream_port: int) -> bytes:
    header, separator, body = data.partition(b"\r\n\r\n")
    if not separator:
        return data

    host = f"Host: {upstream_host}:{upstream_port}".encode("ascii")
    lines = header.split(b"\r\n")
    rewritten: list[bytes] = []
    replaced = False
    for line in lines:
        if line.lower().startswith(b"host:"):
            rewritten.append(host)
            replaced = True
        else:
            rewritten.append(line)
    if not replaced and rewritten:
        rewritten.insert(1, host)
    return b"\r\n".join(rewritten) + separator + body


async def read_initial_request(reader: asyncio.StreamReader) -> bytes:
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = await reader.read(4096)
        if not chunk:
            break
        data += chunk
        if len(data) > HEADER_LIMIT_BYTES:
            raise RuntimeError("CDP request header is too large")
    return data


def response_content_length(header: bytes) -> int | None:
    content_length: int | None = None
    for line in header.split(b"\r\n")[1:]:
        name, separator, value = line.partition(b":")
        if not separator:
            continue
        name = name.strip().lower()
        if name == b"transfer-encoding":
            return None
        if name == b"content-length":
            try:
                content_length = int(value.strip())
            except ValueError:
                return None
    return content_length


async def read_discovery_response(reader: asyncio.StreamReader) -> tuple[bytes, bool]:
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = await reader.read(4096)
        if not chunk:
            return data, False
        data += chunk
        if len(data) > RESPONSE_HEADER_LIMIT_BYTES:
            raise RuntimeError("CDP response header is too large")

    header, separator, buffered_body = data.partition(b"\r\n\r\n")
    content_length = response_content_length(header)
    if content_length is None:
        return data, False
    if content_length < 0 or content_length > DISCOVERY_BODY_LIMIT_BYTES:
        raise RuntimeError("CDP discovery response body is too large")
    if len(buffered_body) > content_length:
        raise RuntimeError("CDP discovery response contains trailing bytes")
    if len(buffered_body) < content_length:
        buffered_body += await reader.readexactly(content_length - len(buffered_body))
    return header + separator + buffered_body, True


async def pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        while True:
            chunk = await reader.read(BUFFER_SIZE)
            if not chunk:
                break
            writer.write(chunk)
            await writer.drain()
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass


async def handle_client(
    client_reader: asyncio.StreamReader,
    client_writer: asyncio.StreamWriter,
    upstream_host: str,
    upstream_port: int,
) -> None:
    upstream_writer: asyncio.StreamWriter | None = None
    try:
        initial = await read_initial_request(client_reader)
        if not initial:
            return

        request_path, public_host, is_upgrade = request_metadata(initial)

        upstream_reader, upstream_writer = await asyncio.open_connection(upstream_host, upstream_port)
        upstream_writer.write(rewrite_host_header(initial, upstream_host, upstream_port))
        await upstream_writer.drain()

        if request_path in DISCOVERY_PATHS and public_host and not is_upgrade:
            response, complete = await read_discovery_response(upstream_reader)
            if response:
                client_writer.write(
                    rewrite_discovery_response(response, request_path, public_host, upstream_port)
                    if complete
                    else response
                )
                await client_writer.drain()
            if not complete:
                await pipe(upstream_reader, client_writer)
            return

        await asyncio.gather(
            pipe(client_reader, upstream_writer),
            pipe(upstream_reader, client_writer),
        )
    except Exception as exc:
        print(f"project-cdp-proxy connection failed: {exc}", file=sys.stderr)
    finally:
        client_writer.close()
        try:
            await client_writer.wait_closed()
        except Exception:
            pass
        if upstream_writer is not None and not upstream_writer.is_closing():
            upstream_writer.close()
            try:
                await upstream_writer.wait_closed()
            except Exception:
                pass


async def amain() -> None:
    listen_host = os.getenv("CDP_PROXY_LISTEN_HOST", "0.0.0.0")
    listen_port = int(os.getenv("CDP_PROXY_LISTEN_PORT", "9223"))
    upstream_host = os.getenv("CDP_PROXY_UPSTREAM_HOST", "127.0.0.1")
    upstream_port = int(os.getenv("CDP_PROXY_UPSTREAM_PORT", "9222"))

    server = await asyncio.start_server(
        lambda reader, writer: handle_client(reader, writer, upstream_host, upstream_port),
        listen_host,
        listen_port,
    )

    loop = asyncio.get_running_loop()
    stop = loop.create_future()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set_result, None)

    sockets = ", ".join(str(sock.getsockname()) for sock in server.sockets or [])
    print(f"project-cdp-proxy listening on {sockets}, upstream={upstream_host}:{upstream_port}", flush=True)
    async with server:
        await stop


if __name__ == "__main__":
    asyncio.run(amain())
