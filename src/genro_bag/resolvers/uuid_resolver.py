# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""UUID resolver — generate unique identifiers as lazy Bag nodes.

Assign a UUID to a Bag node on first access::

    from genro_bag import Bag
    from genro_bag.resolvers import UuidResolver

    bag = Bag()
    bag['id'] = UuidResolver()
    bag['id']  # '550e8400-e29b-41d4-a716-446655440000' (generated once)

With ``cache_time=-1`` (default) the UUID is generated once and never changes.
"""

from __future__ import annotations

import uuid
from typing import Any

from ..resolver import BagResolver


class UuidResolver(BagResolver):
    """Resolver that generates a UUID string."""

    class_kwargs: dict[str, Any] = {
        "cache_time": -1,
        "read_only": False,
        "version": "uuid4",
    }
    class_args: list[str] = ["version"]
    internal_params: set[str] = {
        "cache_time", "read_only", "retry_policy", "as_bag", "version",
    }

    _generators = {
        "uuid1": uuid.uuid1,
        "uuid4": uuid.uuid4,
    }

    def load(self) -> str:
        """Generate a UUID string."""
        version = self._kw["version"]
        generator = self._generators.get(version)
        if generator is None:
            raise ValueError(f"Unsupported UUID version: {version!r}. Use 'uuid1' or 'uuid4'.")
        return str(generator())
