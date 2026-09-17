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

Pass ``dtype`` to convert the raw string value to a Python type via
``tytx_decode`` (uses the standard tytx codes: ``L`` long, ``R`` real,
``B`` boolean, ``D`` date, etc.)::

    bag['port'] = EnvResolver('GNR_ASGI_PORT', dtype='L')   # -> int
"""

from __future__ import annotations

import os
from typing import Any

from genro_tytx import from_tytx as tytx_decode

from ..resolver import BagSyncResolver


class EnvResolver(BagSyncResolver):
    """Resolver that reads an environment variable."""

    class_kwargs: dict[str, Any] = {
        "cache_time": 0,
        "read_only": False,
        "default": None,
        "dtype": None,
    }
    class_args: list[str] = ["var_name"]
    internal_params: set[str] = {
        "cache_time", "read_only", "retry_policy", "as_bag",
        "default", "dtype",
    }

    def load(self) -> Any:
        """Read the environment variable, optionally typed via tytx."""
        default: Any = getattr(self, 'default', None)
        value = os.environ.get(self.var_name, default)
        dtype = getattr(self, 'dtype', None)
        if dtype is not None and value is not None:
            return tytx_decode(f"{value}::{dtype}")
        return value
