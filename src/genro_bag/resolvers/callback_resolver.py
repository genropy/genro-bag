# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BagCbResolver - resolver that calls a callback function."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from genro_toolbox import smartasync, smartawait

from ..resolver import BagResolver


class BagCbResolver(BagResolver):
    """Resolver that calls a callback function to get the value.

    The callback can be sync or async - handled automatically.

    Parameters (class_args):
        callback: Callable that returns the value. Can be sync or async.

    Parameters (class_kwargs):
        cache_time: Cache duration in seconds. Default 0 (no cache).
        read_only: If True, resolver acts as pure getter. Default True.

    Example:
        >>> from datetime import datetime
        >>> resolver = BagCbResolver(datetime.now)
        >>> resolver()  # returns current datetime
        datetime.datetime(2026, 1, 5, 10, 30, 45, 123456)

        >>> # With async callback
        >>> async def fetch_data():
        ...     await asyncio.sleep(0.1)
        ...     return {'status': 'ok'}
        >>> resolver = BagCbResolver(fetch_data)
        >>> await resolver()  # works in async context
        {'status': 'ok'}

        >>> # With caching
        >>> resolver = BagCbResolver(datetime.now, cache_time=60)
        >>> t1 = resolver()
        >>> t2 = resolver()  # same value, cached
        >>> t1 == t2
        True
    """

    class_kwargs = {'cache_time': 0, 'read_only': True}
    class_args = ['callback']

    @smartasync
    async def load(self) -> Any:
        """Call the callback and return its result.

        Uses @smartasync to work in both sync and async contexts.
        Uses smartawait to handle both sync and async callbacks.

        Returns:
            The value returned by the callback.

        Raises:
            TypeError: If callback is not callable.
        """
        callback: Callable[[], Any] = self._kw['callback']
        return await smartawait(callback())
