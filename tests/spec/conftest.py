# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Pytest configuration and fixtures for the spec suite."""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from genro_toolbox import reset_smartasync_cache

# Served by the http_server fixture. Shaped like a small nested document so
# a parsed Bag has something to navigate.
HTTP_FIXTURE_JSON = {
    "slideshow": {
        "title": "Sample Slide Show",
        "slides": [
            {"title": "Wake up to WonderWidgets!", "type": "all"},
            {"title": "Overview", "type": "all"},
        ],
    }
}


@pytest.fixture(autouse=True)
def reset_smartasync_caches():
    """Reset smartasync cache before each test.

    Ensures that async context detection starts fresh for each test,
    preventing state leakage between sync and async tests.
    """
    reset_smartasync_cache()
    yield


class _JsonHandler(BaseHTTPRequestHandler):
    """Answer every GET with HTTP_FIXTURE_JSON."""

    def do_GET(self):  # noqa: N802 — name imposed by BaseHTTPRequestHandler
        body = json.dumps(HTTP_FIXTURE_JSON).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):  # noqa: A002 — signature from the base class
        """Silence the per-request logging to stderr."""


@pytest.fixture(scope="session")
def http_server():
    """Serve HTTP_FIXTURE_JSON from localhost, yielding the base URL.

    The HTTP tests need a real request — socket, protocol, httpx — but not
    a real host: a public endpoint makes them fail whenever someone else's
    service is down, which is what httpbin.org used to do here.

    Port 0 lets the OS pick a free one, so parallel runs never collide.
    """
    server = HTTPServer(("127.0.0.1", 0), _JsonHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
