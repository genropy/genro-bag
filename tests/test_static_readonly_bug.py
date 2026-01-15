# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Test for bug: static=True ignored when read_only=True."""

import pytest

from genro_bag import Bag
from genro_bag.resolvers import BagCbResolver


class TestStaticWithReadOnlyBug:
    """Verify that static=True blocks load() even with read_only=True."""

    def test_static_true_should_not_trigger_load_when_readonly(self):
        """BUG: static=True is ignored when read_only=True.

        Scenario:
        - Resolver with read_only=True (each call should invoke load)
        - But with static=True, user explicitly asks for cached value
        - load() should NOT be invoked
        """
        calls = []

        def tracked_io():
            calls.append(1)
            return f"result_{len(calls)}"

        resolver = BagCbResolver(tracked_io, read_only=True, cache_time=0)

        # First normal call - must invoke load()
        result1 = resolver()
        assert len(calls) == 1
        assert result1 == "result_1"

        # Call with static=True - must NOT invoke load()
        result2 = resolver(static=True)

        assert len(calls) == 1, (
            f"BUG: static=True triggered load() with read_only=True. "
            f"Calls to load(): {len(calls)} (expected: 1)"
        )

    def test_static_true_via_bagnode_get_value(self):
        """BUG: static=True via BagNode.get_value() ignored with read_only=True."""
        calls = []

        def tracked_io():
            calls.append(1)
            return f"result_{len(calls)}"

        bag = Bag()
        bag["data"] = BagCbResolver(tracked_io, read_only=True, cache_time=0)

        # First call - must invoke load()
        node = bag.get_node("data")
        _ = node.get_value()
        assert len(calls) == 1

        # Call with static=True - must NOT invoke load()
        _ = node.get_value(static=True)

        assert len(calls) == 1, (
            f"BUG: get_value(static=True) triggered load(). "
            f"Calls: {len(calls)} (expected: 1)"
        )
