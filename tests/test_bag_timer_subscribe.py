# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""Tests for timer subscription events."""

import asyncio

import pytest

from genro_bag import Bag


class TestTimerSubscription:
    """Timer subscription basic functionality."""

    @pytest.mark.asyncio
    async def test_timer_callback_called(self):
        """Timer callback is called periodically."""
        bag = Bag()
        events = []

        bag.subscribe("t1", timer=lambda **kw: events.append(kw["evt"]), interval=0.1)
        await asyncio.sleep(0.35)
        bag.unsubscribe("t1", timer=True)

        assert len(events) >= 2
        assert all(e == "tmr" for e in events)

    @pytest.mark.asyncio
    async def test_unsubscribe_stops_timer(self):
        """Unsubscribe with timer=True stops the timer."""
        bag = Bag()
        events = []

        bag.subscribe("t1", timer=lambda **kw: events.append(1), interval=0.1)
        await asyncio.sleep(0.25)
        bag.unsubscribe("t1", timer=True)
        count_at_stop = len(events)
        await asyncio.sleep(0.25)

        assert len(events) == count_at_stop

    @pytest.mark.asyncio
    async def test_unsubscribe_any_stops_timer(self):
        """Unsubscribe with any=True also stops the timer."""
        bag = Bag()
        events = []

        bag.subscribe("t1", timer=lambda **kw: events.append(1), interval=0.1)
        await asyncio.sleep(0.25)
        bag.unsubscribe("t1", any=True)
        count_at_stop = len(events)
        await asyncio.sleep(0.25)

        assert len(events) == count_at_stop

    def test_timer_without_interval_raises(self):
        """Timer without interval raises ValueError."""
        bag = Bag()
        with pytest.raises(ValueError, match="interval is required"):
            bag.subscribe("t1", timer=lambda **kw: None)

    def test_any_does_not_activate_timer(self):
        """Subscribe with any= does not activate timer."""
        bag = Bag()
        bag.subscribe("t1", any=lambda **kw: None)

        assert len(bag._tmr_subscribers) == 0

    @pytest.mark.asyncio
    async def test_timer_with_other_events(self):
        """Timer can coexist with other event subscriptions."""
        bag = Bag()
        timer_events = []
        insert_events = []

        bag.subscribe(
            "t1",
            timer=lambda **kw: timer_events.append(kw["evt"]),
            interval=0.1,
            insert=lambda **kw: insert_events.append(kw["evt"]),
        )

        bag["x"] = 1
        await asyncio.sleep(0.25)
        bag.unsubscribe("t1", any=True)

        assert len(insert_events) == 1
        assert len(timer_events) >= 1

    @pytest.mark.asyncio
    async def test_callback_receives_bag(self):
        """Timer callback receives the bag it was subscribed on."""
        bag = Bag()
        received = []

        bag.subscribe(
            "t1",
            timer=lambda **kw: received.append(kw["bag"]),
            interval=0.1,
        )
        await asyncio.sleep(0.15)
        bag.unsubscribe("t1", timer=True)

        assert len(received) >= 1
        assert received[0] is bag

    @pytest.mark.asyncio
    async def test_callback_receives_subscriber_id(self):
        """Timer callback receives subscriber_id."""
        bag = Bag()
        received = []

        bag.subscribe(
            "my_timer",
            timer=lambda **kw: received.append(kw["subscriber_id"]),
            interval=0.1,
        )
        await asyncio.sleep(0.15)
        bag.unsubscribe("my_timer", timer=True)

        assert len(received) >= 1
        assert received[0] == "my_timer"


class TestTimerPropagation:
    """Timer event propagation to parent bags."""

    @pytest.mark.asyncio
    async def test_timer_propagates_to_parent(self):
        """Timer on child bag propagates to parent."""
        root = Bag()
        root["child"] = Bag()
        parent_events = []

        root.subscribe(
            "root_tmr",
            timer=lambda **kw: parent_events.append(kw.get("pathlist")),
            interval=999,
        )
        root["child"].subscribe(
            "child_tmr",
            timer=lambda **kw: None,
            interval=0.1,
        )
        await asyncio.sleep(0.25)
        root["child"].unsubscribe("child_tmr", timer=True)
        root.unsubscribe("root_tmr", timer=True)

        assert len(parent_events) >= 1
        assert parent_events[0] == ["child"]

    @pytest.mark.asyncio
    async def test_stop_propagation_on_timer(self):
        """Timer callback returning False stops propagation."""
        root = Bag()
        root["child"] = Bag()
        parent_events = []

        root.subscribe(
            "root_tmr",
            timer=lambda **kw: parent_events.append(1),
            interval=999,
        )
        root["child"].subscribe(
            "child_tmr",
            timer=lambda **kw: False,
            interval=0.1,
        )
        await asyncio.sleep(0.25)
        root["child"].unsubscribe("child_tmr", timer=True)
        root.unsubscribe("root_tmr", timer=True)

        assert len(parent_events) == 0
