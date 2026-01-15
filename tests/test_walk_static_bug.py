# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Test for bug: walk() generator mode triggers resolvers despite being static."""

import pytest

from genro_bag import Bag
from genro_bag.resolvers import BagCbResolver


class TestWalkGeneratorStaticBug:
    """Verify that walk() generator mode does not trigger resolvers."""

    def test_walk_generator_should_not_trigger_resolver(self):
        """BUG: walk() generator mode uses node.value which triggers resolvers.

        The docstring says:
        > Generator mode (no callback): [...] Always uses static mode (no resolver triggering).

        But the code uses node.value instead of node.get_value(static=True).
        """
        calls = []

        def tracked_io():
            calls.append(1)
            return Bag({"nested": "value"})

        bag = Bag()
        bag["plain"] = "hello"
        bag["lazy"] = BagCbResolver(tracked_io)

        # walk() in generator mode should NOT trigger resolver
        paths = [path for path, node in bag.walk()]

        assert len(calls) == 0, (
            f"BUG: walk() generator mode triggered resolver. "
            f"Calls to load(): {len(calls)} (expected: 0)"
        )
        assert paths == ["plain", "lazy"]

    def test_walk_generator_with_nested_bag_should_not_trigger_resolver(self):
        """BUG: walk() recurses into resolved Bags, triggering resolver."""
        calls = []

        def tracked_io():
            calls.append(1)
            return Bag({"child": "data"})

        bag = Bag()
        bag["level1"] = Bag()
        bag["level1"]["plain"] = "value"
        bag["level1"]["lazy"] = BagCbResolver(tracked_io)

        # walk() should traverse nested Bags without triggering resolvers
        paths = [path for path, node in bag.walk()]

        assert len(calls) == 0, (
            f"BUG: walk() triggered resolver during traversal. "
            f"Calls: {len(calls)} (expected: 0)"
        )
        # Should see level1, level1.plain, level1.lazy (but NOT children of lazy)
        assert "level1" in paths
        assert "level1.plain" in paths
        assert "level1.lazy" in paths


class TestSerializeStaticBug:
    """Verify that serialization does not trigger resolvers."""

    def test_to_tytx_should_not_trigger_resolver(self):
        """BUG: to_tytx uses _node_flattener which may trigger resolvers."""
        calls = []

        def tracked_io():
            calls.append(1)
            return {"computed": "data"}

        bag = Bag()
        bag["plain"] = "hello"
        bag["lazy"] = BagCbResolver(tracked_io)

        # Serialization should NOT trigger resolver
        # to_tytx calls _node_flattener internally
        _ = bag.to_tytx()

        assert len(calls) == 0, (
            f"BUG: to_tytx() triggered resolver. "
            f"Calls: {len(calls)} (expected: 0)"
        )

    def test_to_json_should_not_trigger_resolver(self):
        """BUG: _node_to_json_dict uses node.value which triggers resolvers."""
        calls = []

        def tracked_io():
            calls.append(1)
            return {"computed": "data"}

        bag = Bag()
        bag["plain"] = "hello"
        bag["lazy"] = BagCbResolver(tracked_io)

        # to_json should NOT trigger resolver
        json_str = bag.to_json()

        assert len(calls) == 0, (
            f"BUG: to_json() triggered resolver. "
            f"Calls: {len(calls)} (expected: 0)"
        )
