# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Pytest configuration and fixtures for the spec suite."""

import json
import re
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from genro_toolbox import reset_smartasync_cache

# Served by GET /json. Shaped like a small nested document so a parsed Bag
# has something to navigate.
HTTP_FIXTURE_JSON = {
    "slideshow": {
        "title": "Sample Slide Show",
        "slides": [
            {"title": "Wake up to WonderWidgets!", "type": "all"},
            {"title": "Overview", "type": "all"},
        ],
    }
}

# A minimal OpenAPI 3.0 spec, served by GET /openapi.json.
MINIMAL_OPENAPI_SPEC = {
    "openapi": "3.0.0",
    "info": {
        "title": "Test API",
        "version": "1.0.0",
        "description": "Spec used for spec tests",
    },
    "servers": [{"url": "http://127.0.0.1:0", "description": "local"}],
    "paths": {
        "/pets": {
            "get": {
                "tags": ["pet"],
                "operationId": "listPets",
                "summary": "List all pets",
                "parameters": [
                    {"name": "limit", "in": "query", "schema": {"type": "integer"}},
                ],
                "responses": {"200": {"description": "OK"}},
            },
            "post": {
                "tags": ["pet"],
                "operationId": "createPet",
                "summary": "Create a pet",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {"type": "object"},
                        },
                    },
                },
                "responses": {"201": {"description": "Created"}},
            },
        },
        "/pets/{id}": {
            "get": {
                "tags": ["pet"],
                "operationId": "getPet",
                "summary": "Get pet by id",
                "parameters": [
                    {"name": "id", "in": "path", "required": True,
                     "schema": {"type": "integer"}},
                ],
                "responses": {"200": {"description": "OK"}},
            },
        },
        "/users": {
            "get": {
                "tags": ["user"],
                "operationId": "listUsers",
                "summary": "List all users",
                "responses": {"200": {"description": "OK"}},
            },
        },
    },
    "components": {
        "schemas": {
            "Pet": {
                "type": "object",
                "properties": {"id": {"type": "integer"}, "name": {"type": "string"}},
            },
        },
    },
}

_PET_PATH = re.compile(r"/pets/(?P<id>.+)")


@pytest.fixture(autouse=True)
def reset_smartasync_caches():
    """Reset smartasync cache before each test.

    Ensures that async context detection starts fresh for each test,
    preventing state leakage between sync and async tests.
    """
    reset_smartasync_cache()
    yield


class _SpecHandler(BaseHTTPRequestHandler):
    """Serve the endpoints the HTTP tests exercise.

    HTTP/1.1 with an explicit Content-Length on every reply, so httpx can
    keep the connection alive instead of waiting for the socket to close.
    """

    protocol_version = "HTTP/1.1"

    def _reply(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _reply_json(self, payload, status: int = 200) -> None:
        self._reply(status, json.dumps(payload).encode(), "application/json")

    def do_GET(self):  # noqa: N802 — name imposed by BaseHTTPRequestHandler
        path, _, raw_query = self.path.partition("?")
        query = dict(p.split("=", 1) for p in raw_query.split("&") if "=" in p)

        if path in ("/json", "/hello"):
            return self._reply_json(
                HTTP_FIXTURE_JSON if path == "/json" else {"hello": "world"}
            )
        if path == "/echo":
            return self._reply_json(
                {"method": "GET", "query": query, "headers": dict(self.headers)}
            )
        if path == "/raw":
            return self._reply(200, b"plain-bytes", "application/octet-stream")
        if path == "/openapi.json":
            return self._reply_json(MINIMAL_OPENAPI_SPEC)
        if path == "/boom":
            return self._reply(404, b"not found", "text/plain")
        if match := _PET_PATH.fullmatch(path):
            pet_id = match["id"]
            return self._reply_json({"id": pet_id, "name": f"pet-{pet_id}"})
        return self._reply(404, b"no route", "text/plain")

    def do_POST(self):  # noqa: N802 — name imposed by BaseHTTPRequestHandler
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        try:
            body = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            body = None
        return self._reply_json({"received": body})

    def log_message(self, format, *args):  # noqa: A002 — signature from the base class
        """Silence the per-request logging to stderr."""


class LocalServer:
    """Handle over the running test server."""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def make_url(self, path: str) -> str:
        return f"{self.base_url}{path}"


@pytest.fixture
def http_server() -> Iterator[LocalServer]:
    """Run a local HTTP server for the duration of the test.

    The HTTP tests need a real request — socket, protocol, httpx — but not
    a real host: a public endpoint makes them fail whenever someone else's
    service is down, which is what httpbin.org used to do here. Serving it
    ourselves also means asserting on a payload we control.

    Threading, so a request can be served while the test's event loop is
    awaiting it. Port 0 lets the OS pick a free one.

    Endpoints:
        GET  /json         -> HTTP_FIXTURE_JSON
        GET  /hello        -> {"hello": "world"}
        GET  /echo         -> echoes method, query, headers
        POST /echo_body    -> echoes posted JSON body
        GET  /pets/{id}    -> {"id": "<id>", "name": "pet-<id>"}
        GET  /boom         -> 404
        GET  /raw          -> binary bytes
        GET  /openapi.json -> MINIMAL_OPENAPI_SPEC
    """
    server = ThreadingHTTPServer(("127.0.0.1", 0), _SpecHandler)
    # poll_interval is how long shutdown() waits for the loop to notice;
    # the default 0.5s would dominate the runtime of a per-test fixture.
    thread = threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True
    )
    thread.start()
    try:
        yield LocalServer(*server.server_address)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
