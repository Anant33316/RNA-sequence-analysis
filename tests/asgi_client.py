"""
Minimal in-process ASGI client for API tests.

Starlette's TestClient needs the third-party `httpx` package; this helper
needs nothing beyond the standard library, so the API tests run anywhere
the app itself runs. It drives the real ASGI app (middleware, routing,
validation, error handlers) exactly as uvicorn would.
"""

from __future__ import annotations

import asyncio
import json as _json
from urllib.parse import urlsplit


class Response:
    def __init__(self, status: int, headers: dict, body: bytes):
        self.status_code = status
        self.headers = headers
        self.content = body

    def json(self):
        return _json.loads(self.content)

    @property
    def text(self) -> str:
        return self.content.decode("utf-8", "replace")


def request(app, method: str, url: str, json=None, data: bytes | None = None, headers: dict | None = None) -> Response:
    parts = urlsplit(url)
    body = b""
    hdrs = {"host": "testserver"}
    if json is not None:
        body = _json.dumps(json).encode()
        hdrs["content-type"] = "application/json"
    elif data is not None:
        body = data
    hdrs.update({k.lower(): v for k, v in (headers or {}).items()})
    hdrs.setdefault("content-length", str(len(body)))
    scope = {
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": method.upper(),
        "scheme": "http", "path": parts.path, "raw_path": parts.path.encode(), "query_string": parts.query.encode(),
        "root_path": "", "headers": [(k.encode(), v.encode()) for k, v in hdrs.items()],
        "client": ("127.0.0.1", 50000), "server": ("testserver", 80),
    }
    chunks = [{"type": "http.request", "body": body, "more_body": False}]
    status, out_headers, out_body = None, {}, []

    async def receive():
        if chunks:
            return chunks.pop(0)
        return {"type": "http.disconnect"}

    async def send(message):
        nonlocal status, out_headers
        if message["type"] == "http.response.start":
            status = message["status"]
            out_headers = {k.decode().lower(): v.decode() for k, v in message.get("headers", [])}
        elif message["type"] == "http.response.body":
            out_body.append(message.get("body", b""))

    asyncio.run(app(scope, receive, send))
    return Response(status, out_headers, b"".join(out_body))


def multipart(fields: dict[str, tuple[str, bytes, str]]) -> tuple[bytes, str]:
    """Encode {name: (filename, content, content_type)} as multipart/form-data."""
    boundary = "----rnatocboundary7MA4YWxk"
    lines = []
    for name, (filename, content, ctype) in fields.items():
        lines.append(f"--{boundary}\r\n".encode())
        lines.append(f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode())
        lines.append(f"Content-Type: {ctype}\r\n\r\n".encode())
        lines.append(content + b"\r\n")
    lines.append(f"--{boundary}--\r\n".encode())
    return b"".join(lines), f"multipart/form-data; boundary={boundary}"
