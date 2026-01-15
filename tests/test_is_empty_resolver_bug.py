# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Test per bug: is_empty() triggera resolver e non considera la sua presenza."""

from genro_bag import Bag
from genro_bag.resolvers import BagCbResolver


class TestIsEmptyResolverBug:
    """Verifica che is_empty() gestisca correttamente i resolver."""

    def test_is_empty_should_not_trigger_resolver(self):
        """is_empty() non deve triggerare il resolver."""
        calls = []

        def tracked_io():
            calls.append(1)
            return "loaded_value"

        bag = Bag()
        bag["data"] = BagCbResolver(tracked_io)

        # is_empty() non deve triggerare I/O
        _ = bag.is_empty()

        assert len(calls) == 0, (
            f"is_empty() ha triggerato il resolver. "
            f"Chiamate a load(): {len(calls)} (atteso: 0)"
        )

    def test_node_with_resolver_is_not_empty(self):
        """Un nodo con resolver (anche senza valore statico) non e' vuoto."""
        bag = Bag()
        bag["data"] = BagCbResolver(lambda: "value")

        # Il nodo ha un resolver, quindi non e' vuoto
        assert bag.is_empty() is False, (
            "Un nodo con resolver dovrebbe essere considerato non vuoto"
        )

    def test_node_without_resolver_and_none_value_is_empty(self):
        """Un nodo senza resolver e con valore None e' vuoto."""
        bag = Bag()
        bag["data"] = None

        assert bag.is_empty() is True

    def test_empty_bag_is_empty(self):
        """Un Bag senza nodi e' vuoto."""
        bag = Bag()
        assert bag.is_empty() is True
