# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Test per bug: static=True ignorato quando read_only=True."""

import pytest

from genro_bag import Bag
from genro_bag.resolvers import BagCbResolver


class TestStaticWithReadOnlyBug:
    """Verifica che static=True blocchi load() anche con read_only=True."""

    def test_static_true_should_not_trigger_load_when_readonly(self):
        """BUG: static=True viene ignorato quando read_only=True.

        Scenario:
        - Resolver con read_only=True (ogni chiamata dovrebbe invocare load)
        - Ma con static=True, l'utente chiede esplicitamente il valore cached
        - Il load() NON dovrebbe essere invocato
        """
        calls = []

        def tracked_io():
            calls.append(1)
            return f"result_{len(calls)}"

        # read_only=True significa "non salvare in cache"
        # MA static=True dovrebbe comunque restituire cached_value senza load()
        resolver = BagCbResolver(tracked_io, read_only=True, cache_time=0)

        # Prima chiamata normale - deve invocare load()
        result1 = resolver()
        assert len(calls) == 1
        assert result1 == "result_1"

        # Chiamata con static=True - NON deve invocare load()
        # Deve restituire il valore cached (anche se None per read_only)
        result2 = resolver(static=True)

        # BUG: Attualmente len(calls) == 2 perché static viene ignorato
        # ATTESO: len(calls) == 1 (load non invocato)
        assert len(calls) == 1, (
            f"BUG: static=True ha scatenato load() con read_only=True. "
            f"Chiamate a load(): {len(calls)} (atteso: 1)"
        )

    def test_static_true_via_bagnode_get_value(self):
        """BUG: static=True via BagNode.get_value() ignorato con read_only=True."""
        calls = []

        def tracked_io():
            calls.append(1)
            return f"result_{len(calls)}"

        bag = Bag()
        bag["data"] = BagCbResolver(tracked_io, read_only=True, cache_time=0)

        # Prima chiamata - deve invocare load()
        node = bag.get_node("data")
        _ = node.get_value()
        assert len(calls) == 1

        # Chiamata con static=True - NON deve invocare load()
        _ = node.get_value(static=True)

        # BUG: len(calls) == 2
        assert len(calls) == 1, (
            f"BUG: get_value(static=True) ha scatenato load(). "
            f"Chiamate: {len(calls)} (atteso: 1)"
        )
