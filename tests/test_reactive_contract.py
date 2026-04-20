# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""Tests for push-reactive resolvers (issue #45).

Covers three concerns:
    - reset(refresh: bool) primitive: lazy (default) vs eager+notify
    - reactive=True flag: auto-trigger reset(refresh=True) on param change
    - Coalescing of multiple triggers within the same sync turn
"""

import asyncio

import pytest

from genro_bag import Bag
from genro_bag.resolver import BagCbResolver


class TestResetRefreshFalseSilent:
    """reset() default is lazy: no event, next pull reloads."""

    def test_reset_default_no_event(self):
        """reset() on a passive resolver does not emit event."""
        bag = Bag()
        bag.set_backref()
        bag.set_item("data", BagCbResolver(lambda: 42, cache_time=False))

        events = []
        bag.subscribe("watcher", update=lambda **kw: events.append(kw))

        _ = bag["data"]  # prime cache
        bag.get_node("data").resolver.reset()

        assert events == []

    def test_reset_invalidates_cache(self):
        """reset() clears _cache_last_update so next pull reloads."""
        counter = [0]

        def incrementing():
            counter[0] += 1
            return counter[0]

        bag = Bag()
        bag.set_item("data", BagCbResolver(incrementing, cache_time=False))

        assert bag["data"] == 1
        assert bag["data"] == 1  # cached

        bag.get_node("data").resolver.reset()
        assert bag["data"] == 2


class TestResetRefreshTrueEager:
    """reset(refresh=True) reloads immediately and emits update event."""

    @pytest.mark.asyncio
    async def test_reset_refresh_true_emits_event(self):
        """reset(refresh=True) emits update via node mutation channel.

        Uses an incrementing callback so the second load produces a value
        different from the first — set_value suppresses the event when the
        new value equals the old.
        """
        counter = [0]

        def incrementing():
            counter[0] += 1
            return counter[0]

        bag = Bag()
        bag.set_backref()
        bag.set_item("data", BagCbResolver(incrementing, cache_time=False))

        _ = bag["data"]  # prime: value=1

        events = []
        bag.subscribe("watcher", update=lambda **kw: events.append(kw))

        bag.get_node("data").resolver.reset(refresh=True)

        # Refresh is scheduled for next tick
        for _ in range(4):
            await asyncio.sleep(0)

        assert len(events) >= 1

        # Cleanup
        bag.get_node("data").resolver.parent_node = None

    @pytest.mark.asyncio
    async def test_reset_refresh_true_updates_cached_value(self):
        """reset(refresh=True) writes new value to node after next tick."""
        counter = [0]

        async def incrementing():
            counter[0] += 1
            return counter[0]

        bag = Bag()
        bag.set_item("data", BagCbResolver(incrementing, cache_time=False))

        # Prime cache via pull
        assert await bag["data"] == 1

        bag.get_node("data").resolver.reset(refresh=True)
        for _ in range(4):
            await asyncio.sleep(0)

        assert bag.get_item("data", static=True) == 2

        # Cleanup
        bag.get_node("data").resolver.parent_node = None

    def test_reset_refresh_readonly_raises(self):
        """reset(refresh=True) on a read_only resolver raises ValueError."""
        resolver = BagCbResolver(lambda: 1, cache_time=0, read_only=True)
        with pytest.raises(ValueError, match="read_only"):
            resolver.reset(refresh=True)

    def test_reset_refresh_sync_context_raises(self):
        """reset(refresh=True) with no event loop raises RuntimeError."""
        bag = Bag()
        bag.set_item("data", BagCbResolver(lambda: 42, cache_time=False))

        with pytest.raises(RuntimeError, match="async context"):
            bag.get_node("data").resolver.reset(refresh=True)


class TestReactiveFlag:
    """reactive=True: param change triggers reset(refresh=True) automatically."""

    def test_reactive_construction_ok(self):
        """reactive=True can be set at construction."""
        resolver = BagCbResolver(lambda: 1, reactive=True)
        assert resolver.reactive is True

    def test_reactive_default_false(self):
        """reactive defaults to False."""
        resolver = BagCbResolver(lambda: 1)
        assert resolver.reactive is False

    def test_reactive_plus_readonly_raises(self):
        """reactive=True with read_only=True is rejected at construction."""
        with pytest.raises(ValueError, match="read_only"):
            BagCbResolver(lambda: 1, reactive=True, read_only=True)

    def test_reactive_setter_mutates(self):
        """reactive can be toggled after construction."""
        resolver = BagCbResolver(lambda: 1)
        assert resolver.reactive is False
        resolver.reactive = True
        assert resolver.reactive is True

    def test_reactive_setter_readonly_raises(self):
        """Setting reactive=True on read_only resolver raises."""
        resolver = BagCbResolver(lambda: 1, cache_time=0, read_only=True)
        with pytest.raises(ValueError, match="read_only"):
            resolver.reactive = True

    @pytest.mark.asyncio
    async def test_reactive_triggers_on_attr_change(self):
        """reactive=True + set_attr on domain param -> update event."""
        async def compute(x=0, y=0):
            return x + y

        bag = Bag()
        bag.set_backref()
        bag.set_item("sum", BagCbResolver(compute, x=1, y=2, reactive=True))

        # Prime cache
        assert await bag["sum"] == 3

        events = []
        bag.subscribe("watcher", update=lambda **kw: events.append(kw))

        bag.set_attr("sum", x=10)
        for _ in range(4):
            await asyncio.sleep(0)

        assert len(events) >= 1
        assert bag.get_item("sum", static=True) == 12

        # Cleanup
        bag.get_node("sum").resolver.parent_node = None

    @pytest.mark.asyncio
    async def test_reactive_internal_params_no_trigger(self):
        """Changing an internal param does NOT trigger reactive refresh."""
        calls = []

        async def tracked(x=0):
            calls.append(x)
            return x

        bag = Bag()
        bag.set_backref()
        bag.set_item("data", BagCbResolver(tracked, x=1, cache_time=False, reactive=True))

        assert await bag["data"] == 1
        baseline = len(calls)

        value_events = []
        def only_value_changes(**kw):
            if kw.get("evt") in ("upd_value", "upd_value_attr"):
                value_events.append(kw)

        bag.subscribe("watcher", update=only_value_changes)

        # Setting an internal param via attr must NOT trigger refresh.
        # internal_params filter is inherited from #46; this is a regression guard.
        bag.set_attr("data", cache_time=30)
        for _ in range(4):
            await asyncio.sleep(0)

        assert len(calls) == baseline
        assert value_events == []

        # Cleanup
        bag.get_node("data").resolver.parent_node = None

    def test_reactive_without_async_no_immediate_trigger(self):
        """Attaching a reactive resolver in sync does not itself trigger refresh.

        Refresh only on param change. Until set_attr is called, resolver is
        inert - consistent with today's behavior: attach never loads.
        """
        calls = []

        def tracked():
            calls.append(1)
            return 42

        bag = Bag()
        resolver = BagCbResolver(tracked, cache_time=False, reactive=True)
        bag.set_item("data", resolver)

        # No load triggered by attach alone
        assert calls == []


class TestReactiveCoalesce:
    """Multiple triggers in the same sync turn coalesce into one load."""

    @pytest.mark.asyncio
    async def test_multiple_set_attr_coalesce(self):
        """Ten set_attr in the same sync turn -> at most one load."""
        calls = []

        async def tracked(a=0, b=0, c=0):
            calls.append((a, b, c))
            return a + b + c

        bag = Bag()
        bag.set_backref()
        bag.set_item("sum", BagCbResolver(tracked, a=0, b=0, c=0, reactive=True))

        # Prime
        assert await bag["sum"] == 0
        baseline = len(calls)

        # Ten rapid changes in the same sync turn
        for i in range(10):
            bag.set_attr("sum", a=i)

        for _ in range(4):
            await asyncio.sleep(0)

        loads_during_burst = len(calls) - baseline
        assert loads_during_burst == 1, (
            f"Expected exactly one coalesced load, got {loads_during_burst}"
        )

        # Final value reflects the last set_attr
        assert bag.get_item("sum", static=True) == 9

        # Cleanup
        bag.get_node("sum").resolver.parent_node = None


class TestReactiveCascade:
    """Reactive refresh propagates down a chain of dependencies."""

    @pytest.mark.asyncio
    async def test_three_level_cascade(self):
        """A -> B -> C: change A, both B and C refresh.

        price depends on code; total depends on price (wired via node subscriber
        that copies price.value into total's unit attr). Changing the code
        should propagate to both price and total.
        """
        async def price_of(code="X"):
            return {"X": 10, "Y": 20}.get(code, 0)

        async def total(unit=0, qty=1):
            return unit * qty

        bag = Bag()
        bag.set_backref()
        bag.set_item("price", BagCbResolver(price_of, code="X", reactive=True))
        bag.set_item("total", BagCbResolver(total, unit=0, qty=3, reactive=True))

        # Prime: price=10
        assert await bag["price"] == 10

        # Wire price -> total only after priming so subscriber fires on refresh.
        # Use static_value: node.value would re-enter the resolver, static_value
        # returns the freshly written _value synchronously.
        def on_price_update(node=None, **_kw):
            bag.set_attr("total", unit=node.static_value)

        bag.get_node("price").subscribe("wire", on_price_update)

        # Initial total with current price
        bag.set_attr("total", unit=10)
        assert await bag["total"] == 30

        # Change A: price code. price refresh -> subscriber -> total.unit
        # -> total refresh.
        bag.set_attr("price", code="Y")

        # Allow multiple ticks for the two-step cascade.
        for _ in range(8):
            await asyncio.sleep(0)

        assert bag.get_item("price", static=True) == 20
        assert bag.get_item("total", static=True) == 60

        # Cleanup
        bag.get_node("price").resolver.parent_node = None
        bag.get_node("total").resolver.parent_node = None


class TestIntervalRegression:
    """interval (from #46) still works after reset(refresh=True) refactor."""

    @pytest.mark.asyncio
    async def test_interval_still_emits_events(self):
        """Regression: interval timer continues to emit update events."""
        counter = [0]

        async def incrementing():
            counter[0] += 1
            return counter[0]

        bag = Bag()
        bag.set_backref()
        bag.set_item("data", BagCbResolver(incrementing, interval=1))

        events = []
        bag.subscribe("watcher", update=lambda **kw: events.append(kw))

        await asyncio.sleep(1.2)

        assert len(events) >= 1

        # Cleanup
        bag.get_node("data").resolver.parent_node = None
