# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Environment variable resolver — read os.environ as lazy Bag nodes.

Mount environment variables into a Bag with optional caching::

    from genro_bag import Bag
    from genro_bag.resolvers import EnvResolver

    bag = Bag()
    bag['db_host'] = EnvResolver('DATABASE_HOST', default='localhost')
    bag['db_host']  # reads os.environ['DATABASE_HOST'] or 'localhost'

With ``cache_time=0`` (default) the variable is re-read on every access,
so runtime changes to the environment are immediately visible.
With ``cache_time=N`` the value is cached for N seconds.
"""

from __future__ import annotations

import os
from typing import Any

from ..resolver import BagResolver


class EnvResolver(BagResolver):
    """Resolver that reads an environment variable."""

    class_kwargs: dict[str, Any] = {
        "cache_time": 0,
        "read_only": False,
        "default": None,
    }
    class_args: list[str] = ["var_name"]
    internal_params: set[str] = {
        "cache_time", "read_only", "retry_policy", "as_bag", "default",
    }

    def load(self) -> str | None:
        """Read the environment variable, return default if unset."""
        return os.environ.get(self._kw["var_name"], self._kw["default"])
