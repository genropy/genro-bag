# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""Tests for interval (background refresh) in BagResolver."""

import asyncio

import pytest

from genro_bag import Bag
from genro_bag.resolver import BagCbResolver


class TestActiveCacheSyncRejection:
    """interval must raise RuntimeError in sync context."""

    def test_active_cache_raises_in_sync(self):
        """interval=N in sync context raises RuntimeError."""
        bag = Bag()
        with pytest.raises(RuntimeError, match="requires an async context"):
            bag.set_item("data", BagCbResolver(lambda: 1, interval=1))

    def test_passive_cache_works_in_sync(self):
        """cache_time > 0 in sync context works normally."""
        bag = Bag()
        bag.set_item("data", BagCbResolver(lambda: 42, cache_time=5))
        assert bag["data"] == 42

    def test_no_cache_works_in_sync(self):
        """cache_time=0 in sync context works normally."""
        bag = Bag()
        bag.set_item("data", BagCbResolver(lambda: 42, cache_time=0))
        assert bag["data"] == 42

    def test_infinite_cache_works_in_sync(self):
        """cache_time=False in sync context works normally."""
        bag = Bag()
        bag.set_item("data", BagCbResolver(lambda: 42, cache_time=False))
        assert bag["data"] == 42


class TestActiveCacheBasic:
    """interval starts background refresh in async."""

    @pytest.mark.asyncio
    async def test_active_cache_updates_value(self):
        """interval=N triggers periodic background refresh in async."""
        counter = [0]

        async def incrementing():
            counter[0] += 1
            return counter[0]

        bag = Bag()
        bag.set_item("data", BagCbResolver(incrementing, interval=1))

        # First access triggers load
        first = await bag["data"]
        assert first == 1

        # Wait for background refresh
        await asyncio.sleep(1.5)

        # Value should have been updated by background timer
        second = bag.get_item("data", static=True)
        assert second > 1

        # Cleanup
        bag.get_node("data").resolver.parent_node = None

    def test_active_cache_read_only_rejected(self):
        """interval with read_only=True raises ValueError at construction."""
        with pytest.raises(ValueError, match="read_only"):
            BagCbResolver(lambda: 1, interval=1, read_only=True)

    def test_cache_time_false_no_timer(self):
        """cache_time=False (infinite cache) does NOT start timer."""
        resolver = BagCbResolver(lambda: 1, cache_time=False)
        bag = Bag()
        bag.set_item("data", resolver)

        assert resolver._timer_id is None

    def test_cache_time_zero_no_timer(self):
        """cache_time=0 does NOT start timer."""
        resolver = BagCbResolver(lambda: 1, cache_time=0)
        bag = Bag()
        bag.set_item("data", resolver)

        assert resolver._timer_id is None

    def test_cache_time_positive_no_timer(self):
        """cache_time > 0 (passive cache) does NOT start timer."""
        resolver = BagCbResolver(lambda: 1, cache_time=5)
        bag = Bag()
        bag.set_item("data", resolver)

        assert resolver._timer_id is None


class TestActiveCacheLifecycle:
    """Active cache lifecycle: start on attach, stop on detach."""

    @pytest.mark.asyncio
    async def test_timer_starts_on_attach(self):
        """Timer starts when resolver is attached to a node in async."""
        resolver = BagCbResolver(lambda: 1, interval=1)
        assert resolver._timer_id is None

        bag = Bag()
        bag.set_item("data", resolver)

        assert resolver._timer_id is not None

        # Cleanup
        resolver.parent_node = None

    @pytest.mark.asyncio
    async def test_timer_stops_on_detach(self):
        """Timer stops when resolver is detached from node."""
        resolver = BagCbResolver(lambda: 1, interval=1)
        bag = Bag()
        bag.set_item("data", resolver)

        assert resolver._timer_id is not None

        resolver.parent_node = None
        assert resolver._timer_id is None

    @pytest.mark.asyncio
    async def test_replace_resolver_stops_old_timer(self):
        """Replacing resolver on a node stops the old resolver's timer."""
        old_resolver = BagCbResolver(lambda: 1, interval=1)
        new_resolver = BagCbResolver(lambda: 2, interval=1)

        bag = Bag()
        bag.set_item("data", old_resolver)
        assert old_resolver._timer_id is not None

        # Replace resolver
        bag.get_node("data").resolver = new_resolver

        assert old_resolver._timer_id is None
        assert new_resolver._timer_id is not None

        # Cleanup
        new_resolver.parent_node = None

    @pytest.mark.asyncio
    async def test_error_in_background_load_keeps_timer(self):
        """Error during background load does not stop the timer."""
        counter = [0]

        async def failing_after_first():
            counter[0] += 1
            if counter[0] > 1:
                raise RuntimeError("simulated error")
            return counter[0]

        resolver = BagCbResolver(failing_after_first, interval=1)
        bag = Bag()
        bag.set_item("data", resolver)

        # First access succeeds
        assert await bag["data"] == 1

        # Wait for background refresh (which will fail)
        await asyncio.sleep(1.5)

        # Timer should still be running
        assert resolver._timer_id is not None

        # Cached value should still be the last successful one
        assert bag.get_item("data", static=True) == 1

        # Cleanup
        resolver.parent_node = None

    @pytest.mark.asyncio
    async def test_first_access_triggers_load(self):
        """First access with active cache triggers immediate load."""
        calls = []

        async def tracked():
            calls.append(1)
            return len(calls)

        bag = Bag()
        bag.set_item("data", BagCbResolver(tracked, interval=1))

        result = await bag["data"]
        assert result == 1
        assert len(calls) == 1

        # Cleanup
        bag.get_node("data").resolver.parent_node = None


class TestInfiniteCache:
    """cache_time=False replaces the old interval=1 for infinite cache."""

    def test_infinite_cache_loads_once(self):
        """cache_time=False loads once and never expires."""
        calls = []

        def tracked():
            calls.append(1)
            return len(calls)

        resolver = BagCbResolver(tracked, cache_time=False)
        resolver()
        resolver()
        resolver()

        assert len(calls) == 1

    def test_infinite_cache_reset_allows_reload(self):
        """reset() on infinite cache allows reload on next access."""
        calls = []

        def tracked():
            calls.append(1)
            return len(calls)

        resolver = BagCbResolver(tracked, cache_time=False)
        resolver()
        assert len(calls) == 1

        resolver.reset()
        resolver()
        assert len(calls) == 2
