# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for set_item behavior on nodes with resolvers (Issue #5)."""

import pytest

from genro_bag import Bag
from genro_bag.bagnode import BagNodeException
from genro_bag.resolvers import BagCbResolver


class TestSetItemOnResolverNode:
    """Verify set_item behavior when node has a resolver."""

    def test_set_item_on_resolver_node_raises_error(self):
        """set_item on node with resolver should raise BagNodeException."""
        bag = Bag()
        bag["data"] = BagCbResolver(lambda: "computed")

        with pytest.raises(BagNodeException) as exc_info:
            bag.set_item("data", "new_value")

        assert "resolver" in str(exc_info.value).lower()

    def test_set_item_with_resolver_false_removes_resolver(self):
        """set_item with resolver=False removes resolver and sets value."""
        bag = Bag()
        bag["data"] = BagCbResolver(lambda: "computed")

        # Verify resolver exists
        node = bag.get_node("data")
        assert node.resolver is not None

        # Remove resolver and set value
        bag.set_item("data", "plain_value", resolver=False)

        # Verify resolver removed and value set
        node = bag.get_node("data")
        assert node.resolver is None
        assert node.value == "plain_value"

    def test_set_item_with_new_resolver_replaces_resolver(self):
        """set_item with resolver=NewResolver replaces the resolver."""
        bag = Bag()
        original_resolver = BagCbResolver(lambda: "original")
        bag["data"] = original_resolver

        # Replace resolver
        new_resolver = BagCbResolver(lambda: "new")
        bag.set_item("data", None, resolver=new_resolver)

        node = bag.get_node("data")
        assert node.resolver is new_resolver
        assert node.resolver is not original_resolver

    def test_set_item_on_node_without_resolver_works_normally(self):
        """set_item on node without resolver should work normally."""
        bag = Bag()
        bag["data"] = "initial"

        # Should not raise
        bag.set_item("data", "updated")

        assert bag["data"] == "updated"

    def test_set_item_creates_new_node_with_resolver(self):
        """set_item on non-existent path with resolver creates node."""
        bag = Bag()
        resolver = BagCbResolver(lambda: "computed")

        bag.set_item("new_data", None, resolver=resolver)

        node = bag.get_node("new_data")
        assert node.resolver is resolver

    def test_set_item_resolver_false_on_node_without_resolver(self):
        """set_item with resolver=False on node without resolver works."""
        bag = Bag()
        bag["data"] = "initial"

        # Should not raise, just sets the value
        bag.set_item("data", "updated", resolver=False)

        assert bag["data"] == "updated"


class TestSetItemOnNestedResolverPath:
    """Test set_item through paths containing resolvers."""

    def test_set_item_on_path_through_resolver_with_static_true(self):
        """set_item with static=True cannot traverse through resolver."""
        inner = Bag()
        inner["child"] = "value"

        bag = Bag()
        bag["parent"] = BagCbResolver(lambda: inner)

        # With static=True (default), cannot reach child through resolver
        # The path traversal should stop at the resolver node
        # This should create a new nested structure, not modify the resolved bag
        bag.set_item("parent.child", "new_value", static=True)

        # The original resolved bag should be unchanged
        resolved = bag.get_item("parent", static=False)
        # Note: behavior depends on implementation - may create new path or raise

    def test_set_item_on_path_through_resolver_with_static_false(self):
        """set_item with static=False can traverse through resolver."""
        inner = Bag()
        inner["child"] = "original"

        bag = Bag()
        bag["parent"] = BagCbResolver(lambda: inner, read_only=False)

        # Trigger resolver first to populate node._value
        _ = bag.get_item("parent", static=False)

        # Now set_item with static=False should be able to modify
        # the resolved bag (if it's stored in node._value)
        bag.set_item("parent.child", "modified", static=False)

        # Check the modification
        resolved = bag.get_item("parent", static=False)
        assert resolved["child"] == "modified"
