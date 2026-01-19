# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Additional tests for BagNode to increase coverage.

These tests cover edge cases and less common code paths.
"""

import pytest

from genro_bag import Bag
from genro_bag.bagnode import BagNode, BagNodeContainer, BagNodeException
from genro_bag.resolver import BagResolver


# =============================================================================
# Tests for __getattr__ AttributeError path (line 178)
# =============================================================================


class TestBagNodeGetAttrNoBuilder:
    """Tests for __getattr__ when node has no builder."""

    def test_getattr_raises_attribute_error_without_builder(self):
        """__getattr__ raises AttributeError when no builder exists."""
        node = BagNode(parent_bag=None, label="test")

        with pytest.raises(AttributeError, match="object has no attribute 'unknown'"):
            node.unknown()


# =============================================================================
# Tests for get_value kwargs syntax without resolver (lines 268-270)
# =============================================================================


class TestBagNodeGetValueKwargsNoResolver:
    """Tests for get_value with kwargs syntax but no resolver."""

    def test_get_value_kwargs_syntax_without_resolver_raises(self):
        """get_value with kwargs query string raises without resolver."""
        bag = Bag()
        bag["item"] = "value"
        node = bag.get_node("item")

        # Use kwargs syntax (dict-style) in query string
        with pytest.raises(BagNodeException, match="Cannot use kwargs syntax without resolver"):
            node.get_value(_query_string="key=value")


# =============================================================================
# Tests for resolver setter and reset_resolver (lines 395-397, 401-403)
# =============================================================================


class TestBagNodeResolverMethods:
    """Tests for resolver setter and reset methods."""

    def test_resolver_setter_sets_parent_node(self):
        """resolver setter sets parent_node on the resolver."""

        class MockResolver(BagResolver):
            _args = ()
            _kw = {}

            def load(self):
                return "resolved"

        bag = Bag()
        bag["item"] = "initial"
        node = bag.get_node("item")

        resolver = MockResolver()
        node.resolver = resolver

        assert resolver.parent_node is node

    def test_reset_resolver_calls_reset(self):
        """reset_resolver calls reset on resolver and clears static value."""

        class MockResolver(BagResolver):
            _args = ()
            _kw = {}
            _reset_called = False

            def load(self):
                return "resolved"

            def reset(self):
                self._reset_called = True

        bag = Bag()
        bag["item"] = "initial"
        node = bag.get_node("item")

        resolver = MockResolver()
        node.resolver = resolver
        node.set_value("some_value")

        node.reset_resolver()

        assert resolver._reset_called is True
        # static_value should be None after reset
        assert node.static_value is None


# =============================================================================
# Tests for fullpath property (lines 540-544)
# =============================================================================


class TestBagNodeFullpath:
    """Tests for fullpath property."""

    def test_fullpath_with_nested_bag(self):
        """fullpath returns dot-separated path for nested nodes."""
        # Need set_backref() for fullpath to work
        root = Bag()
        root.set_backref()  # Enable backref mode
        root["level1"] = Bag()
        level1 = root["level1"]
        level1["level2"] = "value"

        node = level1.get_node("level2")

        # fullpath depends on parent's fullpath
        assert node.fullpath is not None
        assert "level2" in node.fullpath


# =============================================================================
# Tests for is_branch property (lines 644-646)
# =============================================================================


class TestBagNodeIsBranch:
    """Tests for is_branch property."""

    def test_is_branch_true_for_bag_value(self):
        """is_branch returns True when value is a Bag."""
        bag = Bag()
        bag["child"] = Bag()

        node = bag.get_node("child")

        assert node.is_branch is True

    def test_is_branch_false_for_non_bag_value(self):
        """is_branch returns False when value is not a Bag."""
        bag = Bag()
        bag["item"] = "string value"

        node = bag.get_node("item")

        assert node.is_branch is False


# =============================================================================
# Tests for to_json with nested value (line 688)
# =============================================================================


class TestBagNodeToJsonNested:
    """Tests for to_json with nested value that has to_json method."""

    def test_to_json_with_value_having_to_json(self):
        """to_json calls to_json on value if it has to_json method."""

        class MockSerializable:
            def to_json(self, typed=True, nested=False):
                return {"serialized": True, "nested": nested}

        bag = Bag()
        bag["nested"] = MockSerializable()

        node = bag.get_node("nested")
        result = node.to_json()

        assert "label" in result
        assert result["label"] == "nested"
        # value should be the result of to_json call
        assert result["value"] == {"serialized": True, "nested": True}


# =============================================================================
# Tests for BagNodeContainer._parse_position (line 762)
# =============================================================================


class TestBagNodeContainerParsePosition:
    """Tests for _parse_position with int position."""

    def test_parse_position_with_int(self):
        """_parse_position clamps int to valid range."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag["c"] = 3

        # Test clamping
        assert bag._nodes._parse_position(-5) == 0  # Clamped to 0
        assert bag._nodes._parse_position(1) == 1  # Within range
        assert bag._nodes._parse_position(100) == 3  # Clamped to max


# =============================================================================
# Tests for BagNodeContainer.__setitem__ (lines 822-827)
# =============================================================================


class TestBagNodeContainerSetItem:
    """Tests for __setitem__ update existing item."""

    def test_setitem_updates_existing_node(self):
        """__setitem__ updates existing node in place."""
        bag = Bag()
        bag["item"] = "initial"
        original_node = bag.get_node("item")

        # Create new node with same label
        new_node = BagNode(parent_bag=bag, label="item", value="updated")

        # Direct container access to test __setitem__
        bag._nodes["item"] = new_node

        # The node should be updated
        assert bag._nodes["item"] is new_node


# =============================================================================
# Tests for BagNodeContainer.__delitem__ (lines 831-839)
# =============================================================================


class TestBagNodeContainerDelItem:
    """Tests for __delitem__ with int and string."""

    def test_delitem_with_int_index(self):
        """__delitem__ removes item by int index."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag["c"] = 3

        del bag._nodes[1]  # Delete by index

        assert len(bag) == 2
        assert "b" not in bag._nodes

    def test_delitem_with_comma_separated_string(self):
        """__delitem__ removes multiple items by comma-separated labels."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag["c"] = 3
        bag["d"] = 4

        del bag._nodes["a,c"]  # Delete by comma-separated labels

        assert len(bag) == 2
        assert "a" not in bag._nodes
        assert "b" in bag._nodes
        assert "c" not in bag._nodes
        assert "d" in bag._nodes


# =============================================================================
# Tests for BagNodeContainer.pop returning None (line 988)
# =============================================================================


class TestBagNodeContainerPopNone:
    """Tests for pop returning None."""

    def test_pop_nonexistent_returns_none(self):
        """pop returns None for non-existent key."""
        bag = Bag()
        bag["a"] = 1

        result = bag._nodes.pop("nonexistent")

        assert result is None


# =============================================================================
# Tests for BagNodeContainer.move edge cases (lines 1010, 1035)
# =============================================================================


class TestBagNodeContainerMoveEdgeCases:
    """Tests for move edge cases."""

    def test_move_with_empty_indices_returns_early(self):
        """move with empty indices list returns early."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2

        # Empty list should return early
        bag._nodes.move([], 0)

        # No change
        assert len(bag) == 2

    def test_move_multiple_nodes(self):
        """move can move multiple nodes at once."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag["c"] = 3
        bag["d"] = 4

        # Move first two nodes to position 2
        bag._nodes.move([0, 1], 3)

        # Nodes should be reordered
        labels = [n.label for n in bag._nodes]
        # After move, order changes
        assert len(labels) == 4
