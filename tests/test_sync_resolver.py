# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for BagSyncResolver — always sync, even in async context."""

import asyncio

import pytest

from genro_bag import Bag
from genro_bag.resolver import BagSyncResolver


class CountingResolver(BagSyncResolver):
    """Test resolver that counts load() calls and returns a Bag."""

    class_args = ["label"]
    class_kwargs = {"cache_time": 0, "read_only": False}

    load_count = 0

    def load(self):
        CountingResolver.load_count += 1
        bag = Bag()
        bag[self._kw["label"]] = CountingResolver.load_count
        return bag


class TestBagSyncResolverSync:
    """BagSyncResolver in sync context."""

    def setup_method(self):
        CountingResolver.load_count = 0

    def test_returns_value_directly(self):
        """load() returns a plain value, not a coroutine."""
        bag = Bag()
        bag.set_item("data", CountingResolver("item"))
        result = bag["data"]
        assert isinstance(result, Bag)
        assert result["item"] == 1

    def test_load_called_each_access(self):
        """With cache_time=0, load() is called on every access."""
        bag = Bag()
        bag.set_item("data", CountingResolver("item"))
        bag["data"]
        bag["data"]
        assert CountingResolver.load_count == 2


class TestBagSyncResolverAsync:
    """BagSyncResolver in async context — must NOT return coroutine."""

    def setup_method(self):
        CountingResolver.load_count = 0

    @pytest.mark.asyncio
    async def test_returns_value_not_coroutine(self):
        """In async context, load() still returns a plain value."""
        bag = Bag()
        bag.set_item("data", CountingResolver("item"))
        result = bag["data"]
        # The key assertion: result is NOT a coroutine
        assert not asyncio.iscoroutine(result)
        assert isinstance(result, Bag)
        assert result["item"] == 1

    @pytest.mark.asyncio
    async def test_nested_access_in_async(self):
        """Nested path access works without await in async context."""
        bag = Bag()
        bag.set_item("data", CountingResolver("child"))
        result = bag["data.child"]
        assert not asyncio.iscoroutine(result)
        assert result == 1

    @pytest.mark.asyncio
    async def test_multiple_access_in_async(self):
        """Multiple accesses in async context all return plain values."""
        bag = Bag()
        bag.set_item("data", CountingResolver("v"))
        results = [bag["data.v"] for _ in range(5)]
        assert all(not asyncio.iscoroutine(r) for r in results)
        assert all(isinstance(r, int) for r in results)


class TestBagSyncResolverInheritance:
    """BagSyncResolver inherits all BagResolver features."""

    def test_is_subclass(self):
        from genro_bag.resolver import BagResolver
        assert issubclass(BagSyncResolver, BagResolver)

    def test_cache_works(self):
        """Passive cache (cache_time > 0) works with BagSyncResolver."""
        counter = [0]

        class CachedSync(BagSyncResolver):
            class_kwargs = {"cache_time": 60, "read_only": False}
            def load(self):
                counter[0] += 1
                return counter[0]

        bag = Bag()
        bag.set_item("data", CachedSync())
        first = bag["data"]
        second = bag["data"]
        assert first == second == 1
        assert counter[0] == 1
