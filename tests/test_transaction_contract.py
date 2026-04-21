# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""Contract tests for Bag.transaction() context manager (issue #47)."""

import pytest

from genro_bag import Bag


class TestTransactionContract:
    """Contract tests for Bag.transaction()."""

    def test_granular_silent_inside_with(self):
        """Granular (any=) subscriber receives 0 events inside ``with``, normal events outside."""
        bag = Bag()
        events = []
        bag.subscribe("sub", any=lambda **kw: events.append(kw["evt"]))

        with bag.transaction():
            bag["a"] = 1
            bag["b"] = 2
        assert events == []

        bag["c"] = 3
        assert events == ["ins"]

    def test_transaction_event_on_exit(self):
        """Transaction subscriber receives one call on exit with mutations in insertion order."""
        bag = Bag()
        received = []
        bag.subscribe("tx", transaction=lambda **kw: received.append(kw["mutations"]))

        with bag.transaction():
            bag["a"] = 1
            bag["b"] = 2

        assert len(received) == 1
        mutations = received[0]
        assert len(mutations) == 2
        assert mutations[0][0] == "ins"
        assert mutations[1][0] == "ins"
        assert mutations[0][1].label == "a"
        assert mutations[1][1].label == "b"

    def test_nested_each_emits(self):
        """Nested ``with`` blocks emit distinct events (no merge into outer)."""
        bag = Bag()
        received = []
        bag.subscribe("tx", transaction=lambda **kw: received.append(list(kw["mutations"])))

        with bag.transaction():
            bag["a"] = 1
            with bag.transaction():
                bag["b"] = 2
            bag["c"] = 3

        assert len(received) == 2
        inner_mutations = received[0]
        outer_mutations = received[1]
        assert len(inner_mutations) == 1
        assert inner_mutations[0][1].label == "b"
        assert len(outer_mutations) == 2
        assert [m[1].label for m in outer_mutations] == ["a", "c"]

    def test_exception_no_event(self):
        """Exception inside ``with`` suppresses the event; applied mutations persist."""
        bag = Bag()
        received = []
        bag.subscribe("tx", transaction=lambda **kw: received.append(kw["mutations"]))

        with pytest.raises(RuntimeError, match="boom"), bag.transaction():
            bag["a"] = 1
            raise RuntimeError("boom")

        assert received == []
        assert bag["a"] == 1

    def test_sub_bag_mutations_included(self):
        """Mutations on a nested sub-bag appear once in the root transaction list (no bubble duplication)."""
        root = Bag()
        root["child"] = Bag()
        received = []
        root.subscribe("tx", transaction=lambda **kw: received.append(kw["mutations"]))

        with root.transaction():
            root["child"]["x"] = 42

        assert len(received) == 1
        mutations = received[0]
        assert len(mutations) == 1
        assert mutations[0][0] == "ins"
        assert mutations[0][1].label == "x"

    def test_transaction_only_subscriber(self):
        """Subscriber with only transaction= receives nothing from any=, events only on exit."""
        bag = Bag()
        tx_events = []
        any_events = []
        bag.subscribe("tx_only", transaction=lambda **kw: tx_events.append(kw["mutations"]))
        bag.subscribe("any_sub", any=lambda **kw: any_events.append(kw["evt"]))

        with bag.transaction():
            bag["a"] = 1
            assert tx_events == []
            assert any_events == []

        assert len(tx_events) == 1
        assert any_events == []
