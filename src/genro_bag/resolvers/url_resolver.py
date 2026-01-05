# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
# ruff: noqa: SIM118
"""UrlResolver - resolver that loads content from an HTTP URL."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode

from genro_toolbox import smartasync

from ..resolver import BagResolver

if TYPE_CHECKING:
    from ..bag import Bag


class UrlResolver(BagResolver):
    """Resolver that fetches content from an HTTP URL.

    Parameters (class_kwargs):
        url: The URL to fetch.
        method: HTTP method (get, post, put, delete, patch). Default 'get'.
        qs: Query string parameters as dict. Default None.
        body: Request body as Bag (for POST/PUT/PATCH). Default None.
        timeout: Request timeout in seconds. Default 30.
        as_bag: If True, parse response as Bag. Default False.
    """

    class_kwargs = {
        'cache_time': 300,
        'read_only': True,
        'url': None,
        'method': 'get',
        'qs': None,
        'body': None,
        'timeout': 30,
        'as_bag': False,
    }

    @smartasync
    async def load(self) -> Any:
        """Fetch URL content."""
        import httpx

        url = self._kw['url']
        method = self._kw['method']
        qs = self._kw['qs']
        body: Bag | None = self._kw['body']
        timeout = self._kw['timeout']
        as_bag = self._kw['as_bag']

        # Build URL with query string (filter None values)
        if qs:
            qs_dict = self._qs_to_dict(qs)
            if qs_dict:
                separator = '&' if '?' in url else '?'
                url = f"{url}{separator}{urlencode(qs_dict)}"

        async with httpx.AsyncClient() as client:
            request_method = getattr(client, method)
            kwargs = {'timeout': timeout}

            if body is not None:
                kwargs['json'] = body.to_dict()

            response = await request_method(url, **kwargs)
            response.raise_for_status()

            read_only = self._kw['read_only']

            if not read_only:
                # Must store as Bag - convert or raise
                return self._convert_to_bag(response, must_convert=True)

            if as_bag:
                return self._convert_to_bag(response, must_convert=False)

            return response.content

    def _qs_to_dict(self, qs) -> dict:
        """Convert qs (Bag or dict) to dict, filtering None values."""
        from ..bag import Bag
        if isinstance(qs, Bag):
            return {k: qs[k] for k in qs.keys() if qs[k] is not None}
        return {k: v for k, v in qs.items() if v is not None}

    def _convert_to_bag(self, response, must_convert: bool = False) -> Any:
        from ..bag import Bag
        from ..serialization import from_json

        content_type = response.headers.get('content-type', '')
        text = response.text

        if 'application/json' in content_type:
            return from_json(text)
        elif 'application/xml' in content_type or 'text/xml' in content_type:
            return Bag.from_xml(text)
        elif must_convert:
            raise ValueError(
                f"Cannot convert response to Bag: unsupported content-type '{content_type}'"
            )
        else:
            return from_json(text)  # default to JSON
