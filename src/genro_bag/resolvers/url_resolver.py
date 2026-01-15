# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
# ruff: noqa: SIM118
"""UrlResolver - resolver that loads content from an HTTP URL."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import httpx

from ..bag import Bag
from ..resolver import BagResolver


class UrlResolver(BagResolver):
    """Resolver that fetches content from an HTTP URL.

    Supports all HTTP methods and can convert responses to Bag automatically.
    Uses httpx.AsyncClient for async HTTP operations.

    Parameters (class_args):
        url: The URL to fetch (first positional argument).

    Parameters (class_kwargs):
        cache_time: Cache duration in seconds. Default 300.
        read_only: If True, value is not stored in node._value. Default True,
            but effectively False because cache_time=300 forces read_only=False.
            Set cache_time=0 if you need true read_only behavior.
        url: The URL to fetch (can also be passed as kwarg).
        method: HTTP method (get, post, put, delete, patch). Default 'get'.
        qs: Query string parameters as Bag or dict. None values are filtered out.
        body: Request body as Bag (for POST/PUT/PATCH). Converted via as_dict().
        timeout: Request timeout in seconds. Default 30.
        as_bag: If True, parse response as Bag based on content-type. Default False.

    Returns:
        If as_bag=True or read_only=False: Bag parsed from JSON/XML response.
        Otherwise: bytes (raw response content).

    Example:
        >>> # Simple GET
        >>> resolver = UrlResolver('https://api.example.com/data')
        >>> data = resolver()  # returns bytes
        >>>
        >>> # GET with query params, parse as Bag
        >>> resolver = UrlResolver('https://api.example.com/users',
        ...                        qs={'page': 1, 'limit': 10}, as_bag=True)
        >>> users = resolver()  # returns Bag
        >>>
        >>> # POST with body
        >>> body = Bag({'name': 'John', 'email': 'john@example.com'})
        >>> resolver = UrlResolver('https://api.example.com/users',
        ...                        method='post', body=body, as_bag=True)
    """

    class_kwargs = {
        "cache_time": 300,
        "read_only": True,
        "retry_policy": {
            "max_attempts": 3,
            "delay": 1.0,
            "backoff": 2.0,
            "jitter": True,
            "on": (ConnectionError, TimeoutError, OSError, httpx.TimeoutException),
        },
        "url": None,
        "method": "get",
        "qs": None,
        "body": None,
        "timeout": 5,
        "as_bag": False,
    }
    class_args = ["url"]

    async def async_load(self) -> Any:
        """Fetch URL content and optionally parse as Bag.

        Builds the full URL with query string, makes the HTTP request,
        and returns the response based on configuration.

        Returns:
            bytes: Raw response content (default).
            Bag: If as_bag=True or read_only=False, parses response based
                on content-type (application/json or application/xml).

        Raises:
            httpx.HTTPStatusError: If response status is 4xx or 5xx.
            ValueError: If read_only=False and response cannot be converted to Bag.
        """
        url = self._kw["url"]
        method = self._kw["method"]
        qs = self._kw["qs"]
        body: Bag | None = self._kw["body"]
        timeout = self._kw["timeout"]
        as_bag = self._kw["as_bag"]

        # Build URL with query string (filter None values)
        if qs:
            qs_dict = self._qs_to_dict(qs)
            if qs_dict:
                separator = "&" if "?" in url else "?"
                url = f"{url}{separator}{urlencode(qs_dict)}"

        async with httpx.AsyncClient() as client:
            request_method = getattr(client, method)
            kwargs = {"timeout": timeout}

            if body is not None:
                kwargs["json"] = body.as_dict()

            response = await request_method(url, **kwargs)
            response.raise_for_status()

            read_only = self._kw["read_only"]

            if not read_only:
                # Must store as Bag - convert or raise
                return self._convert_to_bag(response, must_convert=True)

            if as_bag:
                return self._convert_to_bag(response, must_convert=False)

            return response.content

    def _qs_to_dict(self, qs) -> dict:
        """Convert query string parameter source to dict, filtering None values.

        Args:
            qs: Query string parameters as Bag or dict.

        Returns:
            dict: Parameters with None values removed.
        """
        if isinstance(qs, Bag):
            return {k: qs[k] for k in qs.keys() if qs[k] is not None}
        return {k: v for k, v in qs.items() if v is not None}

    def _convert_to_bag(self, response, must_convert: bool = False) -> Any:
        """Convert HTTP response to Bag based on content-type.

        Args:
            response: httpx.Response object.
            must_convert: If True, raise ValueError for unsupported content-types.
                If False, default to JSON parsing.

        Returns:
            Bag: Parsed response content.

        Raises:
            ValueError: If must_convert=True and content-type is unsupported.
        """
        content_type = response.headers.get("content-type", "")
        text = response.text

        if "application/json" in content_type:
            return Bag.from_json(text)
        elif "application/xml" in content_type or "text/xml" in content_type:
            return Bag.from_xml(text)
        elif must_convert:
            raise ValueError(
                f"Cannot convert response to Bag: unsupported content-type '{content_type}'"
            )
        else:
            return Bag.from_json(text)  # default to JSON
