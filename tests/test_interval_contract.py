# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""Tests for the new `interval` parameter on BagResolver.

`interval=N` replaces `cache_time=-N` as the parameter for background
timer-driven refresh. `cache_time` is now reserved for cache expiration
semantics only (0 | N>0 | False).
"""

import asyncio

import pytest

from genro_bag import Bag
from genro_bag.resolver import BagCbResolver


class TestCacheTimeNegativeDeprecated:
    """cache_time < 0 is no longer a valid value; migration message raised."""

    def test_negative_cache_time_raises_at_construction(self):
        """cache_time=-5 raises ValueError with migration message."""
        with pytest.raises(ValueError, match="interval"):
            BagCbResolver(lambda: 1, cache_time=-5)

    def test_negative_cache_time_migration_message_mentions_interval(self):
        """Error message explicitly suggests using interval=abs(N)."""
        with pytest.raises(ValueError) as excinfo:
            BagCbResolver(lambda: 1, cache_time=-30)
        assert "interval" in str(excinfo.value)


class TestIntervalSyncRejection:
    """interval in sync context raises RuntimeError (requires event loop)."""

    def test_interval_raises_in_sync(self):
        """interval=1 in sync context raises RuntimeError."""
        bag = Bag()
        with pytest.raises(RuntimeError, match="requires an async context"):
            bag.set_item("data", BagCbResolver(lambda: 1, interval=1))

    def test_cache_time_zero_still_works_in_sync(self):
        """cache_time=0 (no cache) still works in sync."""
        bag = Bag()
        bag.set_item("data", BagCbResolver(lambda: 42, cache_time=0))
        assert bag["data"] == 42

    def test_cache_time_positive_still_works_in_sync(self):
        """cache_time>0 (TTL passive cache) still works in sync."""
        bag = Bag()
        bag.set_item("data", BagCbResolver(lambda: 42, cache_time=5))
        assert bag["data"] == 42

    def test_cache_time_false_still_works_in_sync(self):
        """cache_time=False (infinite cache) still works in sync."""
        bag = Bag()
        bag.set_item("data", BagCbResolver(lambda: 42, cache_time=False))
        assert bag["data"] == 42


class TestIntervalBasic:
    """interval=N triggers background refresh in async context."""

    @pytest.mark.asyncio
    async def test_interval_updates_value_in_background(self):
        """interval=1 triggers periodic background refresh."""
        counter = [0]

        async def incrementing():
            counter[0] += 1
            return counter[0]

        bag = Bag()
        bag.set_item("data", BagCbResolver(incrementing, interval=1))

        first = await bag["data"]
        assert first == 1

        await asyncio.sleep(1.5)

        second = bag.get_item("data", static=True)
        assert second > 1

        # Cleanup
        bag.get_node("data").resolver.parent_node = None

    @pytest.mark.asyncio
    async def test_interval_none_no_timer(self):
        """interval=None (default) does NOT start timer."""
        resolver = BagCbResolver(lambda: 1, cache_time=0)
        bag = Bag()
        bag.set_item("data", resolver)

        assert resolver._timer_id is None


class TestIntervalFirstTickImmediate:
    """The first tick of interval happens at the next loop tick (no delay)."""

    @pytest.mark.asyncio
    async def test_first_load_happens_at_next_tick(self):
        """With interval=10, the first load fires at the first loop tick,
        not after 10 seconds."""
        calls = []

        async def tracked():
            calls.append(1)
            return len(calls)

        bag = Bag()
        bag.set_item("data", BagCbResolver(tracked, interval=10))

        # Yield to the loop once. If initial_delay were 1 second or 10 seconds,
        # no call would have happened yet. With immediate first tick, at least
        # one call is expected after yielding.
        await asyncio.sleep(0.1)

        assert len(calls) >= 1, (
            "Expected at least one load after yielding to the loop; "
            f"got {len(calls)} calls"
        )

        # Cleanup
        bag.get_node("data").resolver.parent_node = None


class TestIntervalEmitsEvent:
    """interval background refresh emits update event on the node."""

    @pytest.mark.asyncio
    async def test_background_refresh_emits_update_event(self):
        """Background refresh driven by interval calls update subscribers."""
        counter = [0]

        async def incrementing():
            counter[0] += 1
            return counter[0]

        bag = Bag()
        bag.set_backref()
        bag.set_item("data", BagCbResolver(incrementing, interval=1))

        events = []
        bag.subscribe("watcher", update=lambda **kw: events.append(kw))

        # Yield to loop so the timer can fire at least once.
        await asyncio.sleep(1.2)

        assert len(events) >= 1, (
            f"Expected at least one update event, got {len(events)}"
        )

        # Cleanup
        bag.get_node("data").resolver.parent_node = None

    def test_pull_passive_no_event(self):
        """A passive pull (no interval) still does NOT emit event."""
        bag = Bag()
        bag.set_backref()
        bag.set_item("data", BagCbResolver(lambda: 42, cache_time=5))

        events = []
        bag.subscribe("watcher", update=lambda **kw: events.append(kw))

        # Pull the value (triggers load)
        _ = bag["data"]

        assert events == []


class TestIntervalLifecycle:
    """interval lifecycle: start on attach, stop on detach."""

    @pytest.mark.asyncio
    async def test_timer_starts_on_attach(self):
        """Timer starts when resolver with interval is attached to a node."""
        resolver = BagCbResolver(lambda: 1, interval=1)
        assert resolver._timer_id is None

        bag = Bag()
        bag.set_item("data", resolver)

        assert resolver._timer_id is not None

        resolver.parent_node = None

    @pytest.mark.asyncio
    async def test_timer_stops_on_detach(self):
        """Timer stops when resolver is detached."""
        resolver = BagCbResolver(lambda: 1, interval=1)
        bag = Bag()
        bag.set_item("data", resolver)

        assert resolver._timer_id is not None

        resolver.parent_node = None
        assert resolver._timer_id is None
