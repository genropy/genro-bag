# Copyright 2025 Softwell S.r.l. - Genropy Team
# Licensed under the Apache License, Version 2.0

"""Tests for BagCbResolver - callback resolver."""

import asyncio
from datetime import datetime

import pytest

from genro_bag import Bag
from genro_bag.resolvers import BagCbResolver


@pytest.fixture(autouse=True)
def reset_smartasync_cache():
    """Reset smartasync cache before each test.

    smartasync uses asymmetric caching - once async context is detected,
    it's cached forever. This can cause sync tests to fail if run after
    async tests. Reset the cache to ensure clean state.
    """
    # Reset before test - both load() and __call__() use @smartasync
    from genro_bag.resolver import BagResolver

    if hasattr(BagCbResolver.load, "_smartasync_reset_cache"):
        BagCbResolver.load._smartasync_reset_cache()
    if hasattr(BagResolver.__call__, "_smartasync_reset_cache"):
        BagResolver.__call__._smartasync_reset_cache()
    yield


class TestBagCbResolverSync:
    """Sync callback tests."""

    def test_sync_callback_returns_value(self):
        """Sync callback returns its value."""
        resolver = BagCbResolver(lambda: 42)
        assert resolver() == 42

    def test_sync_callback_datetime(self):
        """Sync callback with datetime.now."""
        resolver = BagCbResolver(datetime.now)
        result = resolver()
        assert isinstance(result, datetime)

    def test_sync_callback_called_each_time_no_cache(self):
        """Without cache, callback is called each time."""
        counter = {"value": 0}

        def increment():
            counter["value"] += 1
            return counter["value"]

        resolver = BagCbResolver(increment, cache_time=0)
        assert resolver() == 1
        assert resolver() == 2
        assert resolver() == 3

    def test_sync_callback_with_cache(self):
        """With cache, callback is called once until expired."""
        counter = {"value": 0}

        def increment():
            counter["value"] += 1
            return counter["value"]

        resolver = BagCbResolver(increment, cache_time=10)
        # First call loads
        assert resolver() == 1
        # Subsequent calls use cache, return cached value
        assert resolver() == 1
        assert resolver() == 1
        # Verify callback was only called once
        assert counter["value"] == 1

    def test_sync_callback_returns_bag(self):
        """Callback can return a Bag."""

        def make_bag():
            b = Bag()
            b["x"] = 1
            b["y"] = 2
            return b

        resolver = BagCbResolver(make_bag)
        result = resolver()
        assert isinstance(result, Bag)
        assert result["x"] == 1
        assert result["y"] == 2

    def test_sync_callback_in_bag(self):
        """BagCbResolver works when assigned to Bag node."""
        bag = Bag()
        bag["time"] = BagCbResolver(datetime.now)

        # Access triggers resolver
        node = bag.get_node("time")
        assert node.resolver is not None

        # Get value through resolver
        result = node.resolver()
        assert isinstance(result, datetime)


class TestBagCbResolverAsync:
    """Async callback tests."""

    @pytest.mark.asyncio
    async def test_async_callback_returns_value(self):
        """Async callback returns its value."""

        async def async_value():
            await asyncio.sleep(0.01)
            return "async_result"

        resolver = BagCbResolver(async_value)
        result = resolver()  # smartawait handles async in sync context
        # In async test, we should await if needed
        if asyncio.iscoroutine(result):
            result = await result
        assert result == "async_result"

    @pytest.mark.asyncio
    async def test_async_callback_datetime(self):
        """Async callback with datetime."""

        async def async_now():
            await asyncio.sleep(0.01)
            return datetime.now()

        resolver = BagCbResolver(async_now)
        result = resolver()
        if asyncio.iscoroutine(result):
            result = await result
        assert isinstance(result, datetime)

    @pytest.mark.asyncio
    async def test_async_callback_called_each_time(self):
        """Async callback called each time without cache."""
        counter = {"value": 0}

        async def async_increment():
            await asyncio.sleep(0.001)
            counter["value"] += 1
            return counter["value"]

        resolver = BagCbResolver(async_increment, cache_time=0)

        r1 = resolver()
        if asyncio.iscoroutine(r1):
            r1 = await r1

        r2 = resolver()
        if asyncio.iscoroutine(r2):
            r2 = await r2

        assert r1 == 1
        assert r2 == 2

    @pytest.mark.asyncio
    async def test_async_callback_returns_bag(self):
        """Async callback can return a Bag."""

        async def async_make_bag():
            await asyncio.sleep(0.01)
            b = Bag()
            b["async"] = True
            return b

        resolver = BagCbResolver(async_make_bag)
        result = resolver()
        if asyncio.iscoroutine(result):
            result = await result
        assert isinstance(result, Bag)
        assert result["async"] is True


class TestBagCbResolverCaching:
    """Cache behavior tests."""

    def test_cache_time_zero_no_caching(self):
        """cache_time=0 means no caching."""
        calls = []

        def tracked():
            calls.append(1)
            return len(calls)

        resolver = BagCbResolver(tracked, cache_time=0)
        resolver()
        resolver()
        resolver()
        assert len(calls) == 3

    def test_cache_time_negative_infinite_cache(self):
        """cache_time<0 means infinite cache."""
        calls = []

        def tracked():
            calls.append(1)
            return len(calls)

        resolver = BagCbResolver(tracked, cache_time=-1, read_only=False)
        resolver()
        resolver()
        resolver()
        # Only first call actually loads
        assert len(calls) == 1

    def test_cache_reset(self):
        """reset() invalidates cache."""
        calls = []

        def tracked():
            calls.append(1)
            return len(calls)

        resolver = BagCbResolver(tracked, cache_time=-1, read_only=False)
        resolver()
        assert len(calls) == 1
        resolver()
        assert len(calls) == 1  # Cached

        resolver.reset()
        resolver()
        assert len(calls) == 2  # Reloaded after reset


class TestBagCbResolverEquality:
    """Resolver equality tests."""

    def test_same_callback_same_fingerprint(self):
        """Same callback function produces same fingerprint."""

        def my_func():
            return 42

        r1 = BagCbResolver(my_func)
        r2 = BagCbResolver(my_func)
        assert r1 == r2

    def test_different_callback_different_fingerprint(self):
        """Different callbacks produce different fingerprints."""
        r1 = BagCbResolver(lambda: 1)
        r2 = BagCbResolver(lambda: 2)
        assert r1 != r2

    def test_same_callback_different_cache_time(self):
        """Same callback but different cache_time are different."""

        def my_func():
            return 42

        r1 = BagCbResolver(my_func, cache_time=0)
        r2 = BagCbResolver(my_func, cache_time=60)
        assert r1 != r2


class TestBagCbResolverSerialization:
    """Serialization tests."""

    def test_serialize_basic(self):
        """Resolver can be serialized."""

        def my_func():
            return 42

        resolver = BagCbResolver(my_func, cache_time=30)
        data = resolver.serialize()

        assert data["resolver_class"] == "BagCbResolver"
        assert "genro_bag.resolver" in data["resolver_module"]
        assert data["kwargs"]["cache_time"] == 30
