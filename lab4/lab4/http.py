from __future__ import annotations

# HTTP message utilities used by both client and server.
#
# Limitation mapping summary:
# - HTTP/1.0 request/response format support.
# - Parsing headers and handling message body length.
# - Supports GET/POST request building and response parsing flow.

from dataclasses import dataclass
from pathlib import Path
from typing import Dict
from urllib.parse import unquote


@dataclass
class HttpRequest:
    # Request method, for example GET or POST.
    method: str
    # Raw request path from first line.
    path: str
    # HTTP version token, expected HTTP/1.0 in this lab.
    version: str
    # Request headers parsed into key/value mapping.
    headers: Dict[str, str]
    # Request payload/body bytes.
    body: bytes


@dataclass
class HttpResponse:
    # HTTP version token.
    version: str
    # Numeric status code (200, 404, ...).
    status_code: int
    # Text reason phrase (OK, NOT FOUND, ...).
    reason: str
    # Response headers.
    headers: Dict[str, str]
    # Response body bytes.
    body: bytes

    def to_bytes(self) -> bytes:
        # HTTP/1.0 serialization with default headers when missing.
        headers = dict(self.headers)
        headers.setdefault("Content-Length", str(len(self.body)))
        headers.setdefault("Connection", "close")
        head = [f"{self.version} {self.status_code} {self.reason}"]
        for key, value in headers.items():
            head.append(f"{key}: {value}")
        head.append("")
        head.append("")
        return "\r\n".join(head).encode("utf-8") + self.body


def build_request(method: str, path: str, body: bytes = b"", headers: Dict[str, str] | None = None) -> bytes:
    # Build a minimal HTTP/1.0 request line + headers + body.
    header_map = dict(headers or {})
    header_map.setdefault("Host", "localhost")
    header_map.setdefault("Content-Length", str(len(body)))
    header_map.setdefault("Connection", "close")
    lines = [f"{method.upper()} {path} HTTP/1.0"]
    for key, value in header_map.items():
        lines.append(f"{key}: {value}")
    lines.append("")
    lines.append("")
    return "\r\n".join(lines).encode("utf-8") + body


def parse_request(raw: bytes) -> HttpRequest:
    # Parse incoming raw bytes into structured request object.
    head, _, body = raw.partition(b"\r\n\r\n")
    lines = head.decode("utf-8", errors="replace").split("\r\n")
    if not lines or len(lines[0].split()) != 3:
        raise ValueError("invalid HTTP request line")
    method, path, version = lines[0].split()
    headers: Dict[str, str] = {}
    for line in lines[1:]:
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        headers[key.strip()] = value.strip()
    return HttpRequest(method=method.upper(), path=path, version=version, headers=headers, body=body)


def parse_response(raw: bytes) -> HttpResponse:
    # Parse response head/body and enforce Content-Length if present.
    head, _, body = raw.partition(b"\r\n\r\n")
    lines = head.decode("utf-8", errors="replace").split("\r\n")
    if not lines or len(lines[0].split(None, 2)) < 3:
        raise ValueError("invalid HTTP response line")
    version, status_code, reason = lines[0].split(None, 2)
    headers: Dict[str, str] = {}
    for line in lines[1:]:
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        headers[key.strip()] = value.strip()
    content_length = int(headers.get("Content-Length", len(body)))
    body = body[:content_length]
    return HttpResponse(version=version, status_code=int(status_code), reason=reason, headers=headers, body=body)


def resolve_path(root: Path, request_path: str) -> Path:
    # Map URL path to local filesystem path while blocking traversal.
    # Note: empty path defaults to index.html for convenience.
    normalized = unquote(request_path.split("?", 1)[0]).lstrip("/")
    if not normalized:
        normalized = "index.html"
    target = (root / normalized).resolve()
    root_resolved = root.resolve()
    if root_resolved not in target.parents and target != root_resolved:
        raise ValueError("path traversal blocked")
    return target


def build_response(status_code: int, reason: str, body: bytes, headers: Dict[str, str] | None = None) -> bytes:
    # Small helper that returns wire-format response bytes.
    return HttpResponse(
        version="HTTP/1.0",
        status_code=status_code,
        reason=reason,
        headers=headers or {},
        body=body,
    ).to_bytes()
