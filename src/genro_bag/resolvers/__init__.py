# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Concrete BagResolver implementations.

This module provides ready-to-use resolver implementations:

- DirectoryResolver: Lazily loads directory contents as a Bag
- EnvResolver: Reads an environment variable (with optional caching)
- FileResolver: Lazily loads file content with format detection
- TxtDocResolver: Lazily loads text file content
- BagCbResolver: Calls a callback function (sync or async)
- UuidResolver: Generates a UUID string (cached by default)
- UrlResolver: Loads content from HTTP URL (requires httpx)
- OpenApiResolver: Loads OpenAPI spec and organizes by tags (requires httpx)

Example:
    from genro_bag import Bag
    from genro_bag.resolvers import DirectoryResolver, BagCbResolver, UrlResolver

    # Directory resolver
    bag = Bag()
    bag['docs'] = DirectoryResolver('/path/to/docs', ext='txt')

    # Callback resolver
    from datetime import datetime
    bag['now'] = BagCbResolver(datetime.now)

    # URL resolver (fetch XML as Bag)
    bag['rates'] = UrlResolver(
        'https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml',
        as_bag=True
    )

    # OpenAPI resolver (organized by tags)
    from genro_bag.resolvers import OpenApiResolver
    bag['api'] = OpenApiResolver('https://petstore3.swagger.io/api/v3/openapi.json')
"""

from ..resolver import BagCbResolver
from .directory_resolver import DirectoryResolver, SerializedBagResolver, TxtDocResolver
from .env_resolver import EnvResolver
from .file_resolver import FileResolver
from .openapi_resolver import OpenApiResolver
from .url_resolver import UrlResolver
from .uuid_resolver import UuidResolver

__all__ = [
    "BagCbResolver",
    "DirectoryResolver",
    "EnvResolver",
    "FileResolver",
    "OpenApiResolver",
    "SerializedBagResolver",
    "TxtDocResolver",
    "UrlResolver",
    "UuidResolver",
]
