# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""Tests for stop propagation in subscription events."""

from genro_bag import Bag


class TestStopPropagationUpdate:
    """Stop propagation for update events."""

    def test_return_none_propagates(self):
        """Callback returning None does not stop propagation."""
        root = Bag()
        root["child"] = Bag()
        root["child"]["x"] = 1

        root_events = []
        child_events = []

        root.subscribe("root_sub", update=lambda **kw: root_events.append(kw["evt"]))
        root["child"].subscribe("child_sub", update=lambda **kw: child_events.append(kw["evt"]))

        root["child"]["x"] = 2

        assert len(child_events) == 1
        assert len(root_events) == 1

    def test_return_false_stops_propagation(self):
        """Callback returning False stops propagation to parent."""
        root = Bag()
        root["child"] = Bag()
        root["child"]["x"] = 1

        root_events = []

        def stop_propagation(**kw):
            return False

        root.subscribe("root_sub", update=lambda **kw: root_events.append(kw["evt"]))
        root["child"].subscribe("child_sub", update=stop_propagation)

        root["child"]["x"] = 2

        assert len(root_events) == 0

    def test_first_subscriber_false_stops_all(self):
        """First subscriber returning False stops subsequent subscribers and propagation."""
        root = Bag()
        root["child"] = Bag()
        root["child"]["x"] = 1

        root_events = []
        second_events = []

        def stop_propagation(**kw):
            return False

        root.subscribe("root_sub", update=lambda **kw: root_events.append(kw["evt"]))
        root["child"].subscribe("first", update=stop_propagation)
        root["child"].subscribe("second", update=lambda **kw: second_events.append(kw["evt"]))

        root["child"]["x"] = 2

        assert len(second_events) == 0
        assert len(root_events) == 0


class TestStopPropagationInsert:
    """Stop propagation for insert events."""

    def test_return_none_propagates(self):
        """Callback returning None does not stop propagation."""
        root = Bag()
        root["child"] = Bag()

        root_events = []
        child_events = []

        root.subscribe("root_sub", insert=lambda **kw: root_events.append(kw["evt"]))
        root["child"].subscribe("child_sub", insert=lambda **kw: child_events.append(kw["evt"]))

        root["child"]["new"] = "value"

        assert len(child_events) == 1
        assert len(root_events) == 1

    def test_return_false_stops_propagation(self):
        """Callback returning False stops propagation to parent."""
        root = Bag()
        root["child"] = Bag()

        root_events = []

        def stop_propagation(**kw):
            return False

        root.subscribe("root_sub", insert=lambda **kw: root_events.append(kw["evt"]))
        root["child"].subscribe("child_sub", insert=stop_propagation)

        root["child"]["new"] = "value"

        assert len(root_events) == 0


class TestStopPropagationDelete:
    """Stop propagation for delete events."""

    def test_return_none_propagates(self):
        """Callback returning None does not stop propagation."""
        root = Bag()
        root["child"] = Bag()
        root["child"]["x"] = 1

        root_events = []
        child_events = []

        root.subscribe("root_sub", delete=lambda **kw: root_events.append(kw["evt"]))
        root["child"].subscribe("child_sub", delete=lambda **kw: child_events.append(kw["evt"]))

        del root["child"]["x"]

        assert len(child_events) == 1
        assert len(root_events) == 1

    def test_return_false_stops_propagation(self):
        """Callback returning False stops propagation to parent."""
        root = Bag()
        root["child"] = Bag()
        root["child"]["x"] = 1

        root_events = []

        def stop_propagation(**kw):
            return False

        root.subscribe("root_sub", delete=lambda **kw: root_events.append(kw["evt"]))
        root["child"].subscribe("child_sub", delete=stop_propagation)

        del root["child"]["x"]

        assert len(root_events) == 0


class TestStopPropagationRetrocompat:
    """Verify retrocompatibility — existing callbacks without return continue to work."""

    def test_all_events_propagate_by_default(self):
        """All events propagate when callbacks return None (default)."""
        root = Bag()
        root["child"] = Bag()

        root_events = []

        root.subscribe("root_sub", any=lambda **kw: root_events.append(kw["evt"]))

        root["child"]["a"] = 1  # insert
        root["child"]["a"] = 2  # update
        del root["child"]["a"]  # delete

        assert "ins" in root_events
        assert "upd_value" in root_events
        assert "del" in root_events
