# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for BagNode class.

These tests cover the BagNode API without resolver integration.
Resolver-related tests are in a separate module.
"""

from __future__ import annotations

import pytest

from genro_bag.bagnode import BagNode

# =============================================================================
# INITIALIZATION AND BASIC PROPERTIES
# =============================================================================


class TestBagNodeInit:
    """Tests for BagNode initialization."""

    def test_init_minimal(self):
        """BagNode can be created with just parent_bag and label."""
        node = BagNode(parent_bag=None, label="test")

        assert node.label == "test"
        assert node.value is None
        assert node.attr == {}
        assert node.tag is None
        assert node.parent_bag is None

    def test_init_with_value(self):
        """BagNode can be created with an initial value."""
        node = BagNode(parent_bag=None, label="test", value="hello")

        assert node.value == "hello"

    def test_init_with_attr(self):
        """BagNode can be created with initial attributes."""
        node = BagNode(parent_bag=None, label="test", attr={"color": "red", "size": 10})

        assert node.attr == {"color": "red", "size": 10}

    def test_init_with_tag(self):
        """BagNode can be created with a tag."""
        node = BagNode(parent_bag=None, label="test", tag="div")

        assert node.tag == "div"

    def test_init_value_types(self):
        """BagNode accepts various value types."""
        # String
        node = BagNode(parent_bag=None, label="s", value="text")
        assert node.value == "text"

        # Integer
        node = BagNode(parent_bag=None, label="i", value=42)
        assert node.value == 42

        # Float
        node = BagNode(parent_bag=None, label="f", value=3.14)
        assert node.value == 3.14

        # List
        node = BagNode(parent_bag=None, label="l", value=[1, 2, 3])
        assert node.value == [1, 2, 3]

        # Dict
        node = BagNode(parent_bag=None, label="d", value={"a": 1})
        assert node.value == {"a": 1}

        # None
        node = BagNode(parent_bag=None, label="n", value=None)
        assert node.value is None


class TestBagNodeStr:
    """Tests for BagNode string representations."""

    def test_str(self):
        """__str__ returns readable representation."""
        node = BagNode(parent_bag=None, label="mynode")

        assert str(node) == "BagNode : mynode"

    def test_repr(self):
        """__repr__ includes id for debugging."""
        node = BagNode(parent_bag=None, label="mynode")

        result = repr(node)
        assert "BagNode : mynode at" in result
        assert str(id(node)) in result


# =============================================================================
# VALUE PROPERTY AND METHODS
# =============================================================================


class TestBagNodeValue:
    """Tests for value property and get_value/set_value methods."""

    def test_value_property_get(self):
        """value property returns the node's value."""
        node = BagNode(parent_bag=None, label="test", value="initial")

        assert node.value == "initial"

    def test_value_property_set(self):
        """value property can set the node's value."""
        node = BagNode(parent_bag=None, label="test", value="initial")
        node.value = "updated"

        assert node.value == "updated"

    def test_get_value_default(self):
        """get_value() returns the value."""
        node = BagNode(parent_bag=None, label="test", value="hello")

        assert node.get_value() == "hello"

    def test_get_value_static_mode(self):
        """get_value('static') bypasses resolver (returns raw _value)."""
        node = BagNode(parent_bag=None, label="test", value="hello")

        # Without resolver, both should return same value
        assert node.get_value() == "hello"
        assert node.get_value("static") == "hello"

    def test_set_value_basic(self):
        """set_value() updates the node's value."""
        node = BagNode(parent_bag=None, label="test")
        node.set_value("new_value")

        assert node.value == "new_value"

    def test_set_value_with_attributes(self):
        """set_value() can set attributes along with value."""
        node = BagNode(parent_bag=None, label="test")
        node.set_value("val", _attributes={"a": 1, "b": 2})

        assert node.value == "val"
        assert node.attr == {"a": 1, "b": 2}

    def test_set_value_updattr_true(self):
        """set_value with _updattr=True merges attributes."""
        node = BagNode(parent_bag=None, label="test", attr={"existing": "keep"})
        node.set_value("val", _attributes={"new": "added"}, _updattr=True)

        assert node.attr == {"existing": "keep", "new": "added"}

    def test_set_value_updattr_false(self):
        """set_value with _updattr=False replaces all attributes."""
        node = BagNode(parent_bag=None, label="test", attr={"existing": "remove"})
        node.set_value("val", _attributes={"new": "only"}, _updattr=False)

        assert node.attr == {"new": "only"}
        assert "existing" not in node.attr

    def test_set_value_bagnode_extracts_value_and_attr(self):
        """When setting a BagNode as value, extracts its value and merges attrs."""
        source = BagNode(
            parent_bag=None, label="source", value="extracted", attr={"from_source": True}
        )
        target = BagNode(parent_bag=None, label="target")

        target.set_value(source)

        assert target.value == "extracted"
        assert target.attr["from_source"] is True

    def test_static_value_property_get(self):
        """static_value property returns raw _value."""
        node = BagNode(parent_bag=None, label="test", value="hello")

        assert node.static_value == "hello"

    def test_static_value_property_set(self):
        """static_value setter bypasses set_value processing."""
        node = BagNode(parent_bag=None, label="test")
        node.static_value = "direct"

        assert node.value == "direct"


# =============================================================================
# ATTRIBUTES
# =============================================================================


class TestBagNodeAttributes:
    """Tests for attribute methods."""

    def test_attr_property(self):
        """attr property returns the attributes dict."""
        node = BagNode(parent_bag=None, label="test", attr={"x": 1, "y": 2})

        assert node.attr == {"x": 1, "y": 2}

    def test_get_attr_single(self):
        """get_attr(label) returns single attribute value."""
        node = BagNode(parent_bag=None, label="test", attr={"color": "blue"})

        assert node.get_attr("color") == "blue"

    def test_get_attr_with_default(self):
        """get_attr returns default if attribute not found."""
        node = BagNode(parent_bag=None, label="test", attr={"a": 1})

        assert node.get_attr("missing", "default") == "default"

    def test_get_attr_none_returns_all(self):
        """get_attr(None) returns all attributes."""
        node = BagNode(parent_bag=None, label="test", attr={"a": 1, "b": 2})

        assert node.get_attr(None) == {"a": 1, "b": 2}

    def test_get_attr_hash_returns_all(self):
        """get_attr('#') returns all attributes."""
        node = BagNode(parent_bag=None, label="test", attr={"a": 1, "b": 2})

        assert node.get_attr("#") == {"a": 1, "b": 2}

    def test_set_attr_dict(self):
        """set_attr can set attributes from a dict."""
        node = BagNode(parent_bag=None, label="test")
        node.set_attr({"x": 10, "y": 20})

        assert node.attr == {"x": 10, "y": 20}

    def test_set_attr_kwargs(self):
        """set_attr can set attributes from kwargs."""
        node = BagNode(parent_bag=None, label="test")
        node.set_attr(x=10, y=20)

        assert node.attr == {"x": 10, "y": 20}

    def test_set_attr_merge(self):
        """set_attr merges with existing attributes by default."""
        node = BagNode(parent_bag=None, label="test", attr={"a": 1})
        node.set_attr({"b": 2})

        assert node.attr == {"a": 1, "b": 2}

    def test_set_attr_updattr_false_replaces(self):
        """set_attr with _updattr=False replaces all attributes."""
        node = BagNode(parent_bag=None, label="test", attr={"old": "remove"})
        node.set_attr({"new": "only"}, _updattr=False)

        assert node.attr == {"new": "only"}

    def test_del_attr_single(self):
        """del_attr removes a single attribute."""
        node = BagNode(parent_bag=None, label="test", attr={"a": 1, "b": 2, "c": 3})
        node.del_attr("b")

        assert node.attr == {"a": 1, "c": 3}

    def test_del_attr_multiple(self):
        """del_attr removes multiple attributes."""
        node = BagNode(parent_bag=None, label="test", attr={"a": 1, "b": 2, "c": 3})
        node.del_attr("a", "c")

        assert node.attr == {"b": 2}

    def test_del_attr_comma_separated(self):
        """del_attr accepts comma-separated string."""
        node = BagNode(parent_bag=None, label="test", attr={"a": 1, "b": 2, "c": 3})
        node.del_attr("a, c")

        assert node.attr == {"b": 2}

    def test_del_attr_nonexistent_silent(self):
        """del_attr silently ignores non-existent attributes."""
        node = BagNode(parent_bag=None, label="test", attr={"a": 1})
        node.del_attr("nonexistent")  # Should not raise

        assert node.attr == {"a": 1}

    def test_has_attr_exists(self):
        """has_attr returns True if attribute exists."""
        node = BagNode(parent_bag=None, label="test", attr={"color": "red"})

        assert node.has_attr("color") is True

    def test_has_attr_not_exists(self):
        """has_attr returns False if attribute doesn't exist."""
        node = BagNode(parent_bag=None, label="test", attr={"color": "red"})

        assert node.has_attr("size") is False

    def test_has_attr_with_value_match(self):
        """has_attr with value returns True if attribute has that value."""
        node = BagNode(parent_bag=None, label="test", attr={"color": "red"})

        assert node.has_attr("color", "red") is True

    def test_has_attr_with_value_no_match(self):
        """has_attr with value returns False if attribute has different value."""
        node = BagNode(parent_bag=None, label="test", attr={"color": "red"})

        assert node.has_attr("color", "blue") is False


# =============================================================================
# SUBSCRIPTIONS
# =============================================================================


class TestBagNodeSubscriptions:
    """Tests for subscription methods."""

    def test_subscribe_and_trigger_on_value_change(self):
        """Subscribers are notified when value changes."""
        node = BagNode(parent_bag=None, label="test", value="initial")
        events = []

        def callback(node, info, evt):
            events.append({"node": node, "info": info, "evt": evt})

        node.subscribe("sub1", callback)
        node.set_value("updated")

        assert len(events) == 1
        assert events[0]["evt"] == "upd_value"
        assert events[0]["info"] == "initial"  # oldvalue

    def test_subscribe_no_trigger_if_same_value(self):
        """Subscribers are NOT notified if value doesn't change."""
        node = BagNode(parent_bag=None, label="test", value="same")
        events = []

        def callback(node, info, evt):
            events.append(evt)

        node.subscribe("sub1", callback)
        node.set_value("same")  # Same value

        assert len(events) == 0

    def test_subscribe_trigger_false(self):
        """Subscribers are NOT notified when trigger=False."""
        node = BagNode(parent_bag=None, label="test", value="initial")
        events = []

        def callback(node, info, evt):
            events.append(evt)

        node.subscribe("sub1", callback)
        node.set_value("updated", trigger=False)

        assert len(events) == 0

    def test_subscribe_on_attr_change(self):
        """Subscribers are notified when attributes change."""
        node = BagNode(parent_bag=None, label="test")
        events = []

        def callback(node, info, evt):
            events.append({"evt": evt, "info": info})

        node.subscribe("sub1", callback)
        node.set_attr({"new_attr": "value"})

        assert len(events) == 1
        assert events[0]["evt"] == "upd_attrs"
        assert "new_attr" in events[0]["info"]

    def test_unsubscribe(self):
        """Unsubscribed callbacks are no longer called."""
        node = BagNode(parent_bag=None, label="test", value="initial")
        events = []

        def callback(node, info, evt):
            events.append(evt)

        node.subscribe("sub1", callback)
        node.unsubscribe("sub1")
        node.set_value("updated")

        assert len(events) == 0

    def test_unsubscribe_nonexistent_silent(self):
        """Unsubscribing non-existent subscriber doesn't raise."""
        node = BagNode(parent_bag=None, label="test")
        node.unsubscribe("nonexistent")  # Should not raise

    def test_multiple_subscribers(self):
        """Multiple subscribers all receive notifications."""
        node = BagNode(parent_bag=None, label="test", value="initial")
        events1, events2 = [], []

        node.subscribe("sub1", lambda node, info, evt: events1.append(evt))
        node.subscribe("sub2", lambda node, info, evt: events2.append(evt))
        node.set_value("updated")

        assert len(events1) == 1
        assert len(events2) == 1


# =============================================================================
# EQUALITY AND COMPARISON
# =============================================================================


class TestBagNodeEquality:
    """Tests for equality comparison."""

    def test_equal_same_value_same_attr(self):
        """Nodes with same value and attr are equal."""
        node1 = BagNode(parent_bag=None, label="a", value="hello", attr={"x": 1})
        node2 = BagNode(parent_bag=None, label="b", value="hello", attr={"x": 1})

        assert node1 == node2

    def test_not_equal_different_value(self):
        """Nodes with different values are not equal."""
        node1 = BagNode(parent_bag=None, label="a", value="hello")
        node2 = BagNode(parent_bag=None, label="a", value="world")

        assert node1 != node2

    def test_not_equal_different_attr(self):
        """Nodes with different attributes are not equal."""
        node1 = BagNode(parent_bag=None, label="a", value="hello", attr={"x": 1})
        node2 = BagNode(parent_bag=None, label="a", value="hello", attr={"x": 2})

        assert node1 != node2

    def test_equal_ignores_label(self):
        """Equality does NOT consider label (by design)."""
        node1 = BagNode(parent_bag=None, label="different1", value="same", attr={"a": 1})
        node2 = BagNode(parent_bag=None, label="different2", value="same", attr={"a": 1})

        assert node1 == node2

    def test_not_equal_to_non_bagnode(self):
        """BagNode is not equal to non-BagNode objects."""
        node = BagNode(parent_bag=None, label="test", value="hello")

        assert node != "hello"
        assert node != {"value": "hello"}
        assert node != None


# =============================================================================
# UTILITY METHODS
# =============================================================================


class TestBagNodeUtility:
    """Tests for utility methods."""

    def test_as_tuple(self):
        """as_tuple returns (label, value, attr, resolver)."""
        node = BagNode(parent_bag=None, label="test", value="val", attr={"a": 1})

        result = node.as_tuple()

        assert result[0] == "test"
        assert result[1] == "val"
        assert result[2] == {"a": 1}
        assert result[3] is None  # No resolver

    def test_to_json(self):
        """to_json returns JSON-serializable dict."""
        node = BagNode(parent_bag=None, label="test", value="val", attr={"a": 1})

        result = node.to_json()

        assert result == {"label": "test", "value": "val", "attr": {"a": 1}}

    def test_diff_equal_nodes(self):
        """diff returns None for equal nodes."""
        node1 = BagNode(parent_bag=None, label="a", value="same", attr={"x": 1})
        node2 = BagNode(parent_bag=None, label="a", value="same", attr={"x": 1})

        assert node1.diff(node2) is None

    def test_diff_different_label(self):
        """diff reports different label."""
        node1 = BagNode(parent_bag=None, label="a", value="same")
        node2 = BagNode(parent_bag=None, label="b", value="same")

        result = node1.diff(node2)

        assert "Other label: b" in result

    def test_diff_different_attr(self):
        """diff reports different attributes."""
        node1 = BagNode(parent_bag=None, label="a", attr={"x": 1})
        node2 = BagNode(parent_bag=None, label="a", attr={"x": 2})

        result = node1.diff(node2)

        assert "attributes" in result

    def test_diff_different_value(self):
        """diff reports different value."""
        node1 = BagNode(parent_bag=None, label="a", value="hello")
        node2 = BagNode(parent_bag=None, label="a", value="world")

        result = node1.diff(node2)

        assert "value" in result

    def test_is_valid_default(self):
        """New node is valid by default."""
        node = BagNode(parent_bag=None, label="test")

        assert node.is_valid is True


# =============================================================================
# NAVIGATION (without parent - limited tests)
# =============================================================================


class TestBagNodeNavigationNoParent:
    """Tests for navigation properties when node has no parent."""

    def test_parent_bag_none(self):
        """parent_bag is None when no parent set."""
        node = BagNode(parent_bag=None, label="test")

        assert node.parent_bag is None

    def test_position_none_without_parent(self):
        """position is None when no parent."""
        node = BagNode(parent_bag=None, label="test")

        assert node.position is None

    def test_fullpath_none_without_parent(self):
        """fullpath is None when no parent."""
        node = BagNode(parent_bag=None, label="test")

        assert node.fullpath is None

    def test_parent_node_none_without_parent(self):
        """parent_node is None when no parent."""
        node = BagNode(parent_bag=None, label="test")

        assert node.parent_node is None

    def test_underscore_property_raises_without_parent(self):
        """_ property raises ValueError when no parent."""
        node = BagNode(parent_bag=None, label="test")

        with pytest.raises(ValueError, match="Node has no parent"):
            _ = node._

    def test_get_inherited_attributes_no_parent(self):
        """get_inherited_attributes returns own attrs when no parent."""
        node = BagNode(parent_bag=None, label="test", attr={"own": "attr"})

        assert node.get_inherited_attributes() == {"own": "attr"}

    def test_attribute_owner_node_self(self):
        """attribute_owner_node returns self if attribute is on self."""
        node = BagNode(parent_bag=None, label="test", attr={"myattr": "value"})

        assert node.attribute_owner_node("myattr") is node

    def test_attribute_owner_node_not_found(self):
        """attribute_owner_node returns None if attribute not found."""
        node = BagNode(parent_bag=None, label="test", attr={"other": "value"})

        assert node.attribute_owner_node("missing") is None

    def test_attribute_owner_node_with_value(self):
        """attribute_owner_node with attrvalue matches value."""
        node = BagNode(parent_bag=None, label="test", attr={"color": "red"})

        assert node.attribute_owner_node("color", attrvalue="red") is node
        assert node.attribute_owner_node("color", attrvalue="blue") is None
