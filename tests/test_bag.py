# Copyright 2025 Softwell S.r.l. - Genropy Team
# Licensed under the Apache License, Version 2.0

"""Tests for Bag - using only public API."""

import pytest

from genro_bag.bag import Bag


class TestBagSetItem:
    """Test set_item and __setitem__."""

    def test_set_simple_value(self):
        """Set a simple value at root level."""
        bag = Bag()
        bag["foo"] = 42
        assert bag["foo"] == 42

    def test_set_nested_path(self):
        """Set value at nested path creates intermediate bags."""
        bag = Bag()
        bag["a.b.c"] = "hello"
        assert bag["a.b.c"] == "hello"

    def test_set_overwrites_existing(self):
        """Setting same path overwrites value."""
        bag = Bag()
        bag["x"] = 1
        bag["x"] = 2
        assert bag["x"] == 2

    def test_set_multiple_keys(self):
        """Set multiple keys at same level."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag["c"] = 3
        assert bag["a"] == 1
        assert bag["b"] == 2
        assert bag["c"] == 3


class TestBagGetItem:
    """Test get_item and __getitem__."""

    def test_get_existing_value(self):
        """Get existing value."""
        bag = Bag()
        bag["foo"] = "bar"
        assert bag["foo"] == "bar"

    def test_get_missing_returns_none(self):
        """Get missing key returns None."""
        bag = Bag()
        assert bag["missing"] is None

    def test_get_nested_path(self):
        """Get value at nested path."""
        bag = Bag()
        bag["a.b.c"] = 100
        assert bag["a.b.c"] == 100

    def test_get_partial_path_returns_bag(self):
        """Get intermediate path returns nested Bag."""
        bag = Bag()
        bag["a.b.c"] = "leaf"
        result = bag["a.b"]
        assert isinstance(result, Bag)
        assert result["c"] == "leaf"


class TestBagPosition:
    """Test set_item with _position parameter."""

    def test_position_append_default(self):
        """Default position appends at end."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag["c"] = 3
        assert bag.keys() == ["a", "b", "c"]

    def test_position_append_explicit(self):
        """Position '>' appends at end."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag.set_item("last", "X", node_position=">")
        assert bag.keys() == ["a", "b", "last"]

    def test_position_prepend(self):
        """Position '<' inserts at beginning."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag.set_item("first", "X", node_position="<")
        assert bag.keys() == ["first", "a", "b"]

    def test_position_index(self):
        """Position '#n' inserts at index n."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag["c"] = 3
        bag.set_item("mid", "X", node_position="#1")
        assert bag.keys() == ["a", "mid", "b", "c"]

    def test_position_index_invalid(self):
        """Position '#invalid' appends at end (fallback)."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag.set_item("new", "X", node_position="#invalid")
        assert bag.keys() == ["a", "b", "new"]

    def test_position_after_label(self):
        """Position '>label' inserts after label."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag["c"] = 3
        bag.set_item("after_a", "X", node_position=">a")
        assert bag.keys() == ["a", "after_a", "b", "c"]

    def test_position_after_missing_label(self):
        """Position '>missing' appends at end (fallback)."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag.set_item("new", "X", node_position=">missing")
        assert bag.keys() == ["a", "b", "new"]

    def test_position_before_label(self):
        """Position '<label' inserts before label."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag["c"] = 3
        bag.set_item("before_c", "X", node_position="<c")
        assert bag.keys() == ["a", "b", "before_c", "c"]

    def test_position_before_missing_label(self):
        """Position '<missing' appends at end (fallback)."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag.set_item("new", "X", node_position="<missing")
        assert bag.keys() == ["a", "b", "new"]

    def test_position_before_index(self):
        """Position '<#n' inserts before index n."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag["c"] = 3
        bag.set_item("new", "X", node_position="<#2")
        assert bag.keys() == ["a", "b", "new", "c"]

    def test_position_before_index_invalid(self):
        """Position '<#invalid' appends at end (fallback)."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag.set_item("new", "X", node_position="<#invalid")
        assert bag.keys() == ["a", "b", "new"]

    def test_position_after_index(self):
        """Position '>#n' inserts after index n."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag["c"] = 3
        bag.set_item("new", "X", node_position=">#0")
        assert bag.keys() == ["a", "new", "b", "c"]

    def test_position_after_index_invalid(self):
        """Position '>#invalid' appends at end (fallback)."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag.set_item("new", "X", node_position=">#invalid")
        assert bag.keys() == ["a", "b", "new"]

    def test_position_unknown_syntax(self):
        """Unknown position syntax appends at end (fallback)."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag.set_item("new", "X", node_position="unknown")
        assert bag.keys() == ["a", "b", "new"]


class TestBagAttributes:
    """Test node attributes with ?attr syntax."""

    def test_set_and_get_attribute(self):
        """Set attribute and get it with ?attr syntax."""
        bag = Bag()
        bag.set_item("x", 42, _attributes={"type": "int"})
        assert bag["x"] == 42
        assert bag.get("x?type") == "int"

    def test_get_missing_attribute(self):
        """Get missing attribute returns None."""
        bag = Bag()
        bag["x"] = 42
        assert bag.get("x?missing") is None

    def test_set_multiple_attributes(self):
        """Set multiple attributes."""
        bag = Bag()
        bag.set_item("data", "hello", _attributes={"type": "str", "size": 5})
        assert bag.get("data?type") == "str"
        assert bag.get("data?size") == 5

    def test_set_attributes_via_kwargs(self):
        """Set attributes via kwargs."""
        bag = Bag()
        bag.set_item("item", 100, dtype="number", readonly=True)
        assert bag.get("item?dtype") == "number"
        assert bag.get("item?readonly") is True


class TestBagIndexAccess:
    """Test access with #n index syntax."""

    def test_get_by_index(self):
        """Get value by #n index."""
        bag = Bag()
        bag["a"] = 10
        bag["b"] = 20
        bag["c"] = 30
        assert bag.get("#0") == 10
        assert bag.get("#1") == 20
        assert bag.get("#2") == 30

    def test_get_by_invalid_index(self):
        """Get by out of range index returns default."""
        bag = Bag()
        bag["a"] = 1
        assert bag.get("#99") is None

    def test_position_before_index(self):
        """Position '<#n' inserts before index n."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag["c"] = 3
        bag.set_item("new", "X", node_position="<#2")
        assert bag.keys() == ["a", "b", "new", "c"]

    def test_position_after_index(self):
        """Position '>#n' inserts after index n."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag["c"] = 3
        bag.set_item("new", "X", node_position=">#0")
        assert bag.keys() == ["a", "new", "b", "c"]


class TestBagPopAndDelete:
    """Test pop and delete operations."""

    def test_pop_existing(self):
        """Pop existing key returns value."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        result = bag.pop("a")
        assert result == 1
        assert bag.keys() == ["b"]

    def test_pop_missing_returns_default(self):
        """Pop missing key returns default."""
        bag = Bag()
        bag["a"] = 1
        result = bag.pop("missing", "default")
        assert result == "default"

    def test_pop_nested_path(self):
        """Pop from nested path."""
        bag = Bag()
        bag["a.b.c"] = "value"
        result = bag.pop("a.b.c")
        assert result == "value"
        assert bag["a.b.c"] is None

    def test_del_item(self):
        """Delete item with del."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        del bag["a"]
        assert bag.keys() == ["b"]


class TestBagClear:
    """Test clear operation."""

    def test_clear_removes_all(self):
        """Clear removes all nodes."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag["c"] = 3
        bag.clear()
        assert len(bag) == 0
        assert bag.keys() == []


class TestBagContains:
    """Test __contains__ (in operator)."""

    def test_contains_existing(self):
        """Existing key returns True."""
        bag = Bag()
        bag["a"] = 1
        assert "a" in bag

    def test_contains_missing(self):
        """Missing key returns False."""
        bag = Bag()
        bag["a"] = 1
        assert "missing" not in bag

    def test_contains_nested_path(self):
        """Nested path works with in."""
        bag = Bag()
        bag["a.b.c"] = 1
        assert "a.b.c" in bag
        assert "a.b.x" not in bag


class TestBagIteration:
    """Test iteration and len."""

    def test_len(self):
        """Len returns number of direct children."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag["c.d"] = 3
        assert len(bag) == 3  # a, b, c

    def test_iter_yields_nodes(self):
        """Iteration yields BagNodes."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        labels = [node.label for node in bag]
        assert labels == ["a", "b"]

    def test_values(self):
        """Values returns list of values."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        assert bag.values() == [1, 2]

    def test_items(self):
        """Items returns list of (label, value) tuples."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        assert bag.items() == [("a", 1), ("b", 2)]


class TestBagCall:
    """Test __call__ syntax."""

    def test_call_no_arg_returns_keys(self):
        """Calling bag() returns keys."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        assert bag() == ["a", "b"]

    def test_call_with_path_returns_value(self):
        """Calling bag(path) returns value."""
        bag = Bag()
        bag["a.b"] = 42
        assert bag("a.b") == 42


class TestBagBackref:
    """Test backref mode: set_backref, del_parent_ref, clear_backref."""

    def test_set_backref_enables_backref_mode(self):
        """set_backref enables backref mode."""
        bag = Bag()
        bag["a"] = 1
        assert bag.backref is False
        bag.set_backref()
        assert bag.backref is True

    def test_set_backref_sets_parent_bag_on_nodes(self):
        """set_backref sets parent_bag reference on all existing nodes."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag.set_backref()
        for node in bag:
            assert node.parent_bag is bag

    def test_del_parent_ref_clears_backref(self):
        """del_parent_ref sets backref to False and clears parent."""
        bag = Bag()
        bag.set_backref()
        assert bag.backref is True
        bag.del_parent_ref()
        assert bag.backref is False

    def test_clear_backref_recursive(self):
        """clear_backref clears backref recursively on nested bags."""
        bag = Bag()
        bag["a.b.c"] = "deep"
        bag.set_backref()
        assert bag.backref is True
        inner = bag["a"]
        assert inner.backref is True
        bag.clear_backref()
        assert bag.backref is False
        assert inner.backref is False

    def test_clear_backref_clears_parent_bag_on_nodes(self):
        """clear_backref sets parent_bag to None on all nodes."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag.set_backref()
        bag.clear_backref()
        for node in bag:
            assert node.parent_bag is None

    def test_nested_bag_gets_parent_node_with_backref(self):
        """When setting a Bag as value with backref, the Bag gets parent_node."""
        bag = Bag()
        bag.set_backref()
        # First set to None, then to Bag - tests the overwrite case
        bag["alfa"] = None
        bag["alfa"] = Bag()
        alfa_node = bag.node("alfa")
        inner_bag = alfa_node.value
        assert isinstance(inner_bag, Bag)
        assert inner_bag.parent_node is not None
        assert inner_bag.parent_node.label == "alfa"


class TestBagSubscribe:
    """Test subscribe and unsubscribe for events."""

    def test_subscribe_enables_backref(self):
        """subscribe automatically enables backref mode."""
        bag = Bag()
        bag["a"] = 1
        assert bag.backref is False
        bag.subscribe("test", any=lambda **kw: None)
        assert bag.backref is True

    def test_subscribe_update_callback(self):
        """subscribe to update events receives callback on value change."""
        bag = Bag()
        bag["a"] = 1
        events = []
        bag.subscribe("test", update=lambda **kw: events.append(("upd", kw)))
        bag["a"] = 2
        assert len(events) == 1
        assert events[0][0] == "upd"
        assert events[0][1]["evt"] == "upd_value"

    def test_subscribe_insert_callback(self):
        """subscribe to insert events receives callback on new node."""
        bag = Bag()
        events = []
        bag.subscribe("test", insert=lambda **kw: events.append(("ins", kw)))
        bag["new"] = "value"
        assert len(events) == 1
        assert events[0][0] == "ins"
        assert events[0][1]["evt"] == "ins"

    def test_subscribe_delete_callback(self):
        """subscribe to delete events receives callback on node removal."""
        bag = Bag()
        bag["a"] = 1
        events = []
        bag.subscribe("test", delete=lambda **kw: events.append(("del", kw)))
        del bag["a"]
        assert len(events) == 1
        assert events[0][0] == "del"
        assert events[0][1]["evt"] == "del"

    def test_subscribe_any_callback(self):
        """subscribe with any=callback subscribes to all events."""
        bag = Bag()
        events = []
        bag.subscribe("test", any=lambda **kw: events.append(kw["evt"]))
        bag["a"] = 1  # insert
        bag["a"] = 2  # update
        del bag["a"]  # delete
        assert events == ["ins", "upd_value", "del"]

    def test_unsubscribe_update(self):
        """unsubscribe removes update callback."""
        bag = Bag()
        bag["a"] = 1
        events = []
        bag.subscribe("test", update=lambda **kw: events.append("upd"))
        bag["a"] = 2
        assert len(events) == 1
        bag.unsubscribe("test", update=True)
        bag["a"] = 3
        assert len(events) == 1  # no new event

    def test_unsubscribe_any(self):
        """unsubscribe with any=True removes all callbacks."""
        bag = Bag()
        events = []
        bag.subscribe("test", any=lambda **kw: events.append(kw["evt"]))
        bag["a"] = 1
        assert len(events) == 1
        bag.unsubscribe("test", any=True)
        bag["a"] = 2
        del bag["a"]
        assert len(events) == 1  # no new events

    def test_multiple_subscribers(self):
        """Multiple subscribers receive events independently."""
        bag = Bag()
        events1 = []
        events2 = []
        bag.subscribe("sub1", insert=lambda **kw: events1.append("ins"))
        bag.subscribe("sub2", insert=lambda **kw: events2.append("ins"))
        bag["a"] = 1
        assert events1 == ["ins"]
        assert events2 == ["ins"]


class TestBagEventPropagation:
    """Test event propagation up the hierarchy."""

    def test_insert_propagates_to_parent(self):
        """Insert event propagates up to parent bag."""
        root = Bag()
        root["child"] = Bag()
        root.set_backref()
        events = []
        root.subscribe("test", insert=lambda **kw: events.append(kw["pathlist"]))
        root["child"]["new"] = "value"
        assert len(events) == 1
        assert events[0] == ["child"]

    def test_update_propagates_to_parent(self):
        """Update event propagates up to parent bag."""
        root = Bag()
        root["child.item"] = 1
        root.set_backref()
        events = []
        root.subscribe("test", update=lambda **kw: events.append(kw["pathlist"]))
        root["child.item"] = 2
        assert len(events) == 1
        # pathlist contains the full path from subscribed bag to changed node
        assert events[0] == ["child", "item"]

    def test_delete_propagates_to_parent(self):
        """Delete event propagates up to parent bag."""
        root = Bag()
        root["child.item"] = 1
        root.set_backref()
        events = []
        root.subscribe("test", delete=lambda **kw: events.append(kw["pathlist"]))
        del root["child.item"]
        assert len(events) == 1
        # pathlist for delete indicates "where" (parent), not "what" (node)
        assert events[0] == ["child"]


class TestBagGetNodes:
    """Test get_nodes method and nodes property."""

    def test_get_nodes_returns_all_nodes(self):
        """get_nodes without condition returns all nodes."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag["c"] = 3
        nodes = bag.get_nodes()
        assert len(nodes) == 3
        assert [n.label for n in nodes] == ["a", "b", "c"]

    def test_get_nodes_with_condition(self):
        """get_nodes with condition filters nodes."""
        bag = Bag()
        bag.set_item("a", 1, even=False)
        bag.set_item("b", 2, even=True)
        bag.set_item("c", 3, even=False)
        bag.set_item("d", 4, even=True)
        nodes = bag.get_nodes(condition=lambda n: n.get_attr("even"))
        assert len(nodes) == 2
        assert [n.label for n in nodes] == ["b", "d"]

    def test_nodes_property(self):
        """nodes property returns same as get_nodes()."""
        bag = Bag()
        bag["x"] = 10
        bag["y"] = 20
        assert bag.nodes == bag.get_nodes()


class TestBagDigest:
    """Test digest method."""

    def test_digest_default(self):
        """digest without args returns #k,#v,#a."""
        bag = Bag()
        bag.set_item("a", 1, x=10)
        bag.set_item("b", 2, y=20)
        result = bag.digest()
        assert len(result) == 2
        assert result[0] == ("a", 1, {"x": 10})
        assert result[1] == ("b", 2, {"y": 20})

    def test_digest_keys_only(self):
        """digest #k returns list of labels."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        result = bag.digest("#k")
        assert result == ["a", "b"]

    def test_digest_values_only(self):
        """digest #v returns list of values."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        result = bag.digest("#v")
        assert result == [1, 2]

    def test_digest_keys_and_values(self):
        """digest #k,#v returns tuples."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        result = bag.digest("#k,#v")
        assert result == [("a", 1), ("b", 2)]

    def test_digest_attribute(self):
        """digest #a.attrname returns specific attribute."""
        bag = Bag()
        bag.set_item("x", "file0", created_by="Jack")
        bag.set_item("y", "file1", created_by="Mark")
        result = bag.digest("#k,#a.created_by")
        assert result == [("x", "Jack"), ("y", "Mark")]

    def test_digest_all_attributes(self):
        """digest #a returns all attributes dict."""
        bag = Bag()
        bag.set_item("a", 1, x=10, y=20)
        result = bag.digest("#a")
        assert result == [{"x": 10, "y": 20}]

    def test_digest_with_condition(self):
        """digest with condition filters nodes."""
        bag = Bag()
        bag.set_item("a", 1, active=True)
        bag.set_item("b", 2, active=False)
        bag.set_item("c", 3, active=True)
        result = bag.digest("#k", condition=lambda n: n.get_attr("active"))
        assert result == ["a", "c"]

    def test_digest_with_path(self):
        """digest with path:what syntax."""
        bag = Bag()
        bag["letters.a"] = "alpha"
        bag["letters.b"] = "beta"
        result = bag.digest("letters:#k,#v")
        assert result == [("a", "alpha"), ("b", "beta")]

    def test_digest_as_columns(self):
        """digest with as_columns=True returns list of lists."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        result = bag.digest("#k,#v", as_columns=True)
        assert result == [["a", "b"], [1, 2]]

    def test_digest_callable(self):
        """digest with callable applies function to each node."""
        bag = Bag()
        bag["a"] = 10
        bag["b"] = 20
        result = bag.digest([lambda n: n.value * 2])
        assert result == [20, 40]

    def test_query_iter(self):
        """query with iter=True returns generator."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag["c"] = 3
        result = bag.query("#k", iter=True)
        # Should be a generator, not a list
        assert hasattr(result, "__next__")
        assert list(result) == ["a", "b", "c"]

    def test_query_deep(self):
        """query with deep=True traverses recursively."""
        bag = Bag()
        bag["a"] = 1
        bag["b.c"] = 2
        bag["b.d"] = 3
        result = bag.query("#p", deep=True)
        assert "a" in result
        assert "b" in result
        assert "b.c" in result
        assert "b.d" in result

    def test_query_deep_with_values(self):
        """query deep with path and value."""
        bag = Bag()
        bag["a"] = 1
        bag["b.c"] = 2
        result = bag.query("#p,#v", deep=True)
        # Should have tuples of (path, value)
        result_dict = dict(result)
        assert result_dict["a"] == 1
        assert result_dict["b.c"] == 2
        # 'b' is a Bag, not a leaf value
        assert "b" in result_dict

    def test_query_deep_with_condition(self):
        """query deep with condition filters nodes."""
        bag = Bag()
        bag["a"] = 1
        bag["b.c"] = 2
        bag["b.d"] = 3
        # Only leaf nodes (not Bag values)
        result = bag.query("#p,#v", deep=True, condition=lambda n: not isinstance(n.value, Bag))
        result_dict = dict(result)
        assert "a" in result_dict
        assert "b.c" in result_dict
        assert "b.d" in result_dict
        assert "b" not in result_dict  # 'b' is a Bag, filtered out

    def test_query_deep_iter(self):
        """query deep with iter returns generator."""
        bag = Bag()
        bag["a"] = 1
        bag["b.c"] = 2
        result = bag.query("#p", deep=True, iter=True)
        assert hasattr(result, "__next__")
        paths = list(result)
        assert "a" in paths
        assert "b.c" in paths

    def test_query_path_specifier(self):
        """query with #p returns path."""
        bag = Bag()
        bag["x"] = 1
        bag["y"] = 2
        result = bag.query("#p")
        assert result == ["x", "y"]

    def test_query_node_specifier(self):
        """query with #n returns the node itself."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        result = bag.query("#n")
        assert len(result) == 2
        assert result[0].label == "a"
        assert result[1].label == "b"


class TestBagColumns:
    """Test columns method."""

    def test_columns_from_values(self):
        """columns extracts values as columns."""
        bag = Bag()
        bag["row1"] = Bag({"name": "Alice", "age": 30})
        bag["row2"] = Bag({"name": "Bob", "age": 25})
        result = bag.columns("name,age")
        # columns uses digest on values, so it extracts from each row's value
        assert len(result) == 2

    def test_columns_attr_mode(self):
        """columns with attr_mode extracts attributes."""
        bag = Bag()
        bag.set_item("a", 1, x=10, y=20)
        bag.set_item("b", 2, x=30, y=40)
        result = bag.columns("x,y", attr_mode=True)
        assert result == [[10, 30], [20, 40]]


class TestBagWalk:
    """Test walk method."""

    def test_walk_generator_flat(self):
        """walk() without callback returns generator of (path, node)."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag["c"] = 3
        result = list(bag.walk())
        assert len(result) == 3
        assert result[0] == ("a", bag.get_node("a"))
        assert result[1] == ("b", bag.get_node("b"))
        assert result[2] == ("c", bag.get_node("c"))

    def test_walk_generator_nested(self):
        """walk() traverses nested Bags depth-first."""
        bag = Bag()
        bag["a"] = 1
        bag["b.x"] = 10
        bag["b.y"] = 20
        bag["c"] = 3
        result = [(path, node.value) for path, node in bag.walk()]
        # Should be: a, b (Bag), b.x, b.y, c
        assert len(result) == 5
        assert result[0] == ("a", 1)
        assert result[1][0] == "b"  # b is a Bag
        assert result[2] == ("b.x", 10)
        assert result[3] == ("b.y", 20)
        assert result[4] == ("c", 3)

    def test_walk_generator_deeply_nested(self):
        """walk() handles deeply nested structures."""
        bag = Bag()
        bag["a.b.c.d"] = "deep"
        result = [(path, node.value) for path, node in bag.walk()]
        # a (Bag), a.b (Bag), a.b.c (Bag), a.b.c.d
        assert len(result) == 4
        paths = [path for path, _ in result]
        assert paths == ["a", "a.b", "a.b.c", "a.b.c.d"]
        assert result[-1] == ("a.b.c.d", "deep")

    def test_walk_generator_early_exit(self):
        """walk() generator supports early exit via break."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag["c"] = 3
        bag["d"] = 4
        found = None
        for path, node in bag.walk():
            if node.value == 2:
                found = path
                break
        assert found == "b"

    def test_walk_callback_basic(self):
        """walk() with callback calls it for each node."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        visited = []
        bag.walk(lambda n: visited.append(n.label))
        assert visited == ["a", "b"]

    def test_walk_callback_nested(self):
        """walk() with callback traverses nested Bags."""
        bag = Bag()
        bag["a"] = 1
        bag["b.x"] = 10
        bag["b.y"] = 20
        visited = []
        bag.walk(lambda n: visited.append(n.label))
        assert visited == ["a", "b", "x", "y"]

    def test_walk_callback_early_exit(self):
        """walk() with callback supports early exit."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag["c"] = 3

        def find_b(node):
            if node.value == 2:
                return node  # truthy return stops walk

        result = bag.walk(find_b)
        assert result.value == 2
        assert result.label == "b"

    def test_walk_callback_pathlist(self):
        """walk() with _pathlist tracks path."""
        bag = Bag()
        bag["a.b.c"] = "deep"
        paths = []

        def collect_paths(node, _pathlist=None):
            paths.append(_pathlist)

        bag.walk(collect_paths, _pathlist=[])
        assert paths == [["a"], ["a", "b"], ["a", "b", "c"]]

    def test_walk_callback_indexlist(self):
        """walk() with _indexlist tracks indices."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag["c"] = 3
        indices = []

        def collect_indices(node, _indexlist=None):
            indices.append(_indexlist)

        bag.walk(collect_indices, _indexlist=[])
        assert indices == [[0], [1], [2]]

    def test_walk_empty_bag(self):
        """walk() on empty bag returns empty generator."""
        bag = Bag()
        result = list(bag.walk())
        assert result == []

    def test_walk_callback_empty_bag(self):
        """walk() with callback on empty bag does nothing."""
        bag = Bag()
        visited = []
        bag.walk(lambda n: visited.append(n.label))
        assert visited == []


class TestBagResolver:
    """Tests for get_resolver and set_resolver methods."""

    def test_set_resolver_creates_node(self):
        """set_resolver creates node with resolver."""
        from genro_bag import BagResolver

        class SimpleResolver(BagResolver):
            def load(self):
                return "resolved_value"

        bag = Bag()
        resolver = SimpleResolver()
        bag.set_resolver("data", resolver)

        assert "data" in bag
        node = bag.get_node("data")
        assert node.resolver is resolver

    def test_get_resolver_returns_resolver(self):
        """get_resolver returns the resolver from a node."""
        from genro_bag import BagResolver

        class SimpleResolver(BagResolver):
            def load(self):
                return "resolved_value"

        bag = Bag()
        resolver = SimpleResolver()
        bag.set_resolver("data", resolver)

        result = bag.get_resolver("data")
        assert result is resolver

    def test_get_resolver_nonexistent_path_returns_none(self):
        """get_resolver returns None for nonexistent path."""
        bag = Bag()
        result = bag.get_resolver("nonexistent")
        assert result is None

    def test_get_resolver_no_resolver_returns_none(self):
        """get_resolver returns None if node has no resolver."""
        bag = Bag()
        bag["data"] = "value"
        result = bag.get_resolver("data")
        assert result is None

    def test_set_resolver_nested_path(self):
        """set_resolver works with nested paths."""
        from genro_bag import BagResolver

        class SimpleResolver(BagResolver):
            def load(self):
                return "nested_resolved"

        bag = Bag()
        resolver = SimpleResolver()
        bag.set_resolver("a.b.c", resolver)

        assert bag.get_resolver("a.b.c") is resolver
        assert bag.get_resolver("a") is None
        assert bag.get_resolver("a.b") is None

    def test_set_resolver_replaces_existing(self):
        """set_resolver replaces existing resolver."""
        from genro_bag import BagResolver

        class Resolver1(BagResolver):
            def load(self):
                return "first"

        class Resolver2(BagResolver):
            def load(self):
                return "second"

        bag = Bag()
        resolver1 = Resolver1()
        resolver2 = Resolver2()

        bag.set_resolver("data", resolver1)
        assert bag.get_resolver("data") is resolver1

        bag.set_resolver("data", resolver2)
        assert bag.get_resolver("data") is resolver2


class TestBagFillFrom:
    """Tests for fill_from method."""

    def test_fill_from_dict_simple(self):
        """fill_from with dict populates bag."""
        bag = Bag()
        bag.fill_from({"a": 1, "b": 2})
        assert bag["a"] == 1
        assert bag["b"] == 2

    def test_fill_from_dict_nested(self):
        """fill_from with nested dict creates nested bags."""
        bag = Bag()
        bag.fill_from({"x": {"y": {"z": "deep"}}})
        assert bag["x.y.z"] == "deep"
        assert isinstance(bag["x"], Bag)

    def test_fill_from_dict_clears_existing(self):
        """fill_from clears existing content."""
        bag = Bag()
        bag["old"] = "data"
        bag.fill_from({"new": "value"})
        assert "old" not in bag
        assert bag["new"] == "value"

    def test_fill_from_bag(self):
        """fill_from with another Bag copies nodes."""
        source = Bag()
        source.set_item("a", 1, attr1="x")
        source.set_item("b", 2, attr2="y")

        target = Bag()
        target.fill_from(source)

        assert target["a"] == 1
        assert target["b"] == 2
        node_a = target.get_node("a")
        assert node_a.get_attr("attr1") == "x"

    def test_fill_from_bag_deep_copy(self):
        """fill_from does deep copy of nested bags."""
        source = Bag()
        source["nested.value"] = "original"

        target = Bag()
        target.fill_from(source)

        # Modify source, target should be unchanged
        source["nested.value"] = "modified"
        assert target["nested.value"] == "original"

    def test_fill_from_file_tytx_json(self, tmp_path):
        """fill_from loads .bag.json file."""
        # Create source bag and save
        source = Bag()
        source["name"] = "test"
        source["count"] = 42
        filepath = tmp_path / "data.bag.json"
        source.to_tytx(filename=str(filepath))

        # Load into new bag
        target = Bag()
        target.fill_from(str(filepath))

        assert target["name"] == "test"
        assert target["count"] == 42

    def test_fill_from_file_tytx_msgpack(self, tmp_path):
        """fill_from loads .bag.mp file."""
        # Create source bag and save
        source = Bag()
        source["name"] = "binary"
        source["value"] = 123
        filepath = tmp_path / "data.bag.mp"
        source.to_tytx(transport="msgpack", filename=str(filepath))

        # Load into new bag
        target = Bag()
        target.fill_from(str(filepath))

        assert target["name"] == "binary"
        assert target["value"] == 123

    def test_fill_from_file_xml(self, tmp_path):
        """fill_from loads .xml file."""
        # Create source bag and save
        source = Bag()
        source["item"] = "xml_value"
        xml_content = source.to_xml()
        filepath = tmp_path / "data.xml"
        filepath.write_text(xml_content)

        # Load into new bag
        target = Bag()
        target.fill_from(str(filepath))

        assert target["item"] == "xml_value"

    def test_fill_from_file_not_found(self):
        """fill_from raises FileNotFoundError for missing file."""
        import pytest

        bag = Bag()
        with pytest.raises(FileNotFoundError):
            bag.fill_from("/nonexistent/path/file.bag.json")

    def test_fill_from_file_unknown_extension(self, tmp_path):
        """fill_from raises ValueError for unknown extension."""
        import pytest

        filepath = tmp_path / "data.unknown"
        filepath.write_text("content")

        bag = Bag()
        with pytest.raises(ValueError, match="Unrecognized file extension"):
            bag.fill_from(str(filepath))

    def test_bag_constructor_with_dict(self):
        """Bag constructor accepts dict source."""
        bag = Bag({"a": 1, "b": {"c": 2}})
        assert bag["a"] == 1
        assert bag["b.c"] == 2

    def test_bag_constructor_with_file(self, tmp_path):
        """Bag constructor accepts file path."""
        source = Bag()
        source["key"] = "from_file"
        filepath = tmp_path / "init.bag.json"
        source.to_tytx(filename=str(filepath))

        bag = Bag(str(filepath))
        assert bag["key"] == "from_file"


class TestBagSubscriberLog:
    """Test subscriber logging all operations on a Bag."""

    def test_subscriber_logs_all_operations(self):
        """Subscriber logs insert, update, delete operations."""
        bag = Bag()
        log = []

        def logger(**kw):
            log.append(
                {
                    "evt": kw.get("evt"),
                    "pathlist": kw.get("pathlist"),
                    "node_label": kw.get("node").label if kw.get("node") else None,
                    "oldvalue": kw.get("oldvalue"),
                }
            )

        bag.subscribe("logger", any=logger)

        # Insert operations
        bag["name"] = "Alice"
        bag["age"] = 30
        bag["address.city"] = "Rome"  # Creates 'address' Bag + 'city' inside

        # Update operations
        bag["name"] = "Bob"
        bag["age"] = 31

        # Delete operations
        del bag["age"]

        # Verify we have the expected event types
        insert_events = [e for e in log if e["evt"] == "ins"]
        update_events = [e for e in log if e["evt"] == "upd_value"]
        delete_events = [e for e in log if e["evt"] == "del"]

        # 4 inserts: name, age, address (Bag), city - no duplicates
        assert len(insert_events) == 4

        # 2 updates: name Alice->Bob, age 30->31
        assert len(update_events) == 2

        # 1 delete: age
        assert len(delete_events) == 1

        # Check inserts in order
        assert insert_events[0]["node_label"] == "name"
        assert insert_events[1]["node_label"] == "age"
        assert insert_events[2]["node_label"] == "address"
        assert insert_events[3]["node_label"] == "city"

        # Check updates have oldvalue
        name_update = [e for e in update_events if e["node_label"] == "name"][0]
        assert name_update["oldvalue"] == "Alice"

        age_update = [e for e in update_events if e["node_label"] == "age"][0]
        assert age_update["oldvalue"] == 30

        # Check delete is for 'age'
        assert delete_events[0]["node_label"] == "age"

    def test_subscriber_logs_nested_operations(self):
        """Subscriber logs operations on nested bags."""
        root = Bag()
        log = []

        def logger(**kw):
            log.append(
                {
                    "evt": kw.get("evt"),
                    "pathlist": kw.get("pathlist"),
                }
            )

        root.subscribe("logger", any=logger)

        # Create nested structure
        root["level1.level2.level3"] = "deep_value"

        # Modify nested value
        root["level1.level2.level3"] = "updated_value"

        # Delete nested
        del root["level1.level2.level3"]

        # Find the update event
        update_events = [e for e in log if e["evt"] == "upd_value"]
        assert len(update_events) == 1
        assert update_events[0]["pathlist"] == ["level1", "level2", "level3"]

        # Find delete event
        delete_events = [e for e in log if e["evt"] == "del"]
        assert len(delete_events) == 1
        assert delete_events[0]["pathlist"] == ["level1", "level2"]

    def test_subscriber_logs_attribute_changes(self):
        """Subscriber logs attribute updates."""
        bag = Bag()
        log = []

        def logger(**kw):
            log.append(
                {
                    "evt": kw.get("evt"),
                    "node_label": kw.get("node").label if kw.get("node") else None,
                }
            )

        bag.subscribe("logger", any=logger)

        # Insert with attributes
        bag.set_item("item", "value", color="red", size=10)

        # Update attributes only
        node = bag.get_node("item")
        node.set_attr(color="blue")

        # Check we got insert and attr update
        assert log[0]["evt"] == "ins"
        assert log[0]["node_label"] == "item"

        assert log[1]["evt"] == "upd_attrs"
        assert log[1]["node_label"] == "item"

    def test_subscriber_multiple_subscribers_independent(self):
        """Multiple subscribers receive events independently."""
        bag = Bag()
        log_inserts = []
        log_updates = []
        log_all = []

        bag.subscribe("ins_logger", insert=lambda **kw: log_inserts.append(kw["evt"]))
        bag.subscribe("upd_logger", update=lambda **kw: log_updates.append(kw["evt"]))
        bag.subscribe("all_logger", any=lambda **kw: log_all.append(kw["evt"]))

        bag["x"] = 1  # insert
        bag["x"] = 2  # update
        bag["y"] = 3  # insert

        assert log_inserts == ["ins", "ins"]
        assert log_updates == ["upd_value"]
        assert log_all == ["ins", "upd_value", "ins"]

    def test_unsubscribe_stops_logging(self):
        """After unsubscribe, no more events are logged."""
        bag = Bag()
        log = []

        bag.subscribe("logger", any=lambda **kw: log.append(kw["evt"]))

        bag["a"] = 1
        assert len(log) == 1

        bag.unsubscribe("logger", any=True)

        bag["b"] = 2
        bag["a"] = 10
        del bag["a"]

        # No new events after unsubscribe
        assert len(log) == 1


class TestBagMove:
    """Test move method - reordering nodes."""

    def test_move_single_node_forward(self):
        """Move single node forward."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag["c"] = 3
        bag["d"] = 4

        # Move 'a' (index 0) to position 2
        bag.move(0, 2)

        assert list(bag.keys()) == ["b", "c", "a", "d"]

    def test_move_single_node_backward(self):
        """Move single node backward."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag["c"] = 3
        bag["d"] = 4

        # Move 'd' (index 3) to position 1
        bag.move(3, 1)

        assert list(bag.keys()) == ["a", "d", "b", "c"]

    def test_move_same_position_noop(self):
        """Moving to same position does nothing."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag["c"] = 3

        bag.move(1, 1)

        assert list(bag.keys()) == ["a", "b", "c"]

    def test_move_negative_position_noop(self):
        """Negative position does nothing."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2

        bag.move(0, -1)

        assert list(bag.keys()) == ["a", "b"]

    def test_move_invalid_index_noop(self):
        """Invalid from index does nothing."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2

        bag.move(10, 0)

        assert list(bag.keys()) == ["a", "b"]

    def test_move_out_of_bounds_position_noop(self):
        """Out of bounds target position does nothing."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2

        bag.move(0, 10)

        assert list(bag.keys()) == ["a", "b"]

    def test_move_multiple_nodes_forward(self):
        """Move multiple non-consecutive nodes forward."""
        bag = Bag()
        bag["a"] = 1  # 0
        bag["b"] = 2  # 1
        bag["c"] = 3  # 2
        bag["d"] = 4  # 3
        bag["e"] = 5  # 4

        # Move indices 0, 2 (a, c) to position 3 (d)
        # JS behavior: pop in reverse order (c then a), insert in pop order
        bag.move([0, 2], 3)

        # After pop: [b, d, e] - c popped first, then a
        # popped = [c, a] (reverse order of sorted indices)
        # dest_label = 'd', delta = 1 (indices[0]=0 < position=3)
        # new_pos = index('d') + 1 = 1 + 1 = 2
        # Insert c at 2: [b, d, c, e]
        # Insert a at 2: [b, d, a, c, e]
        assert list(bag.keys()) == ["b", "d", "a", "c", "e"]

    def test_move_multiple_nodes_backward(self):
        """Move multiple non-consecutive nodes backward."""
        bag = Bag()
        bag["a"] = 1  # 0
        bag["b"] = 2  # 1
        bag["c"] = 3  # 2
        bag["d"] = 4  # 3
        bag["e"] = 5  # 4

        # Move indices 3, 4 (d, e) to position 1 (b)
        # JS behavior: pop in reverse order (e then d), insert in pop order
        bag.move([3, 4], 1)

        # After pop: [a, b, c] - e popped first, then d
        # popped = [e, d] (reverse order of sorted indices)
        # dest_label = 'b', delta = 0 (indices[0]=3 >= position=1)
        # new_pos = index('b') + 0 = 1
        # Insert e at 1: [a, e, b, c]
        # Insert d at 1: [a, d, e, b, c]
        assert list(bag.keys()) == ["a", "d", "e", "b", "c"]

    def test_move_with_trigger_fires_events(self):
        """Move fires del and ins events when trigger=True."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag["c"] = 3

        events = []
        bag.subscribe("logger", any=lambda **kw: events.append(kw["evt"]))

        bag.move(0, 2, trigger=True)

        # Should have del and ins events
        assert "del" in events
        assert "ins" in events

    def test_move_without_trigger_no_events(self):
        """Move with trigger=False fires no events."""
        bag = Bag()

        events = []
        bag.subscribe("logger", any=lambda **kw: events.append(kw["evt"]))

        # Subscribe BEFORE inserting to capture insert events
        bag["a"] = 1
        bag["b"] = 2
        bag["c"] = 3

        # Clear events from inserts
        events.clear()

        bag.move(0, 2, trigger=False)

        # No events should be fired for move
        assert events == []

    def test_move_preserves_values_and_attributes(self):
        """Move preserves node values and attributes."""
        bag = Bag()
        bag.set_item("a", 1, color="red")
        bag.set_item("b", 2, color="blue")
        bag.set_item("c", 3, color="green")

        bag.move(0, 2)

        # Check 'a' is now at position 2 with preserved value and attr
        node = bag.get_node("#2")
        assert node.label == "a"
        assert node.value == 1
        assert node.attr["color"] == "red"

    def test_move_single_element_list(self):
        """Single-element list behaves like single int."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag["c"] = 3

        bag.move([0], 2)

        assert list(bag.keys()) == ["b", "c", "a"]


class TestBagRoot:
    """Test root property for navigating to root Bag."""

    def test_root_on_standalone_bag(self):
        """Root of a standalone bag is itself."""
        bag = Bag()
        bag["a"] = 1
        assert bag.root is bag

    def test_root_without_backref(self):
        """Without backref, root is always self (no parent chain)."""
        bag = Bag()
        bag["a.b.c"] = "deep"
        inner = bag["a.b"]
        # Without backref, inner.parent is None
        assert inner.root is inner

    def test_root_with_backref(self):
        """With backref, root traverses to the top."""
        bag = Bag()
        bag["a.b.c"] = "deep"
        bag.set_backref()

        inner_b = bag["a.b"]
        inner_a = bag["a"]

        # All should resolve to the root bag
        assert inner_b.root is bag
        assert inner_a.root is bag
        assert bag.root is bag

    def test_root_deeply_nested(self):
        """Root works for deeply nested bags."""
        bag = Bag()
        bag["level1.level2.level3.level4.leaf"] = "value"
        bag.set_backref()

        level4 = bag["level1.level2.level3.level4"]
        level3 = bag["level1.level2.level3"]
        level2 = bag["level1.level2"]
        level1 = bag["level1"]

        assert level4.root is bag
        assert level3.root is bag
        assert level2.root is bag
        assert level1.root is bag


class TestBagFired:
    """Test _fired parameter for event-like signals."""

    def test_fired_sets_then_resets_to_none(self):
        """_fired=True sets value then immediately resets to None."""
        bag = Bag()
        bag.set_item("event", "click", _fired=True)
        assert bag["event"] is None

    def test_fired_creates_node_if_not_exists(self):
        """_fired creates node even if it didn't exist."""
        bag = Bag()
        bag.set_item("new_event", "trigger", _fired=True)
        assert "new_event" in bag
        assert bag["new_event"] is None

    def test_fired_triggers_single_event(self):
        """_fired triggers only one event (the set), reset to None is silent."""
        bag = Bag()
        events = []
        bag.subscribe(
            "test", any=lambda **kw: events.append((kw["evt"], kw["node"].label, kw["node"].value))
        )

        bag.set_item("signal", "data", _fired=True)

        # Should have only: ins (with value 'data')
        # The reset to None is silent (do_trigger=False)
        assert len(events) == 1
        assert events[0][0] == "ins"
        assert events[0][1] == "signal"
        assert events[0][2] == "data"  # Value at event time
        # But after the call, value is None
        assert bag["signal"] is None

    def test_fired_on_existing_node(self):
        """_fired works on existing nodes too."""
        bag = Bag()
        bag["existing"] = "old_value"

        events = []
        bag.subscribe("test", any=lambda **kw: events.append(kw["evt"]))

        bag.set_item("existing", "fired_value", _fired=True)

        assert bag["existing"] is None
        # Only one update: for 'fired_value' (reset to None is silent)
        assert events.count("upd_value") == 1

    def test_fired_preserves_attributes(self):
        """_fired preserves node attributes."""
        bag = Bag()
        bag.set_item("event", "click", _fired=True, _attributes={"type": "mouse"})

        node = bag.get_node("event")
        assert node.value is None
        assert node.attr["type"] == "mouse"


class TestBagSetItemAttrSyntax:
    """Test ?attr syntax in set_item for setting node attributes."""

    def test_set_attr_on_existing_node(self):
        """?attr sets attribute on existing node."""
        bag = Bag()
        bag["node"] = "value"
        bag.set_item("node?myattr", "attr_value")

        node = bag.get_node("node")
        assert node.value == "value"  # Value unchanged
        assert node.attr["myattr"] == "attr_value"

    def test_set_attr_nested_path(self):
        """?attr works with nested paths."""
        bag = Bag()
        bag["a.b.c"] = 42
        bag.set_item("a.b.c?type", "integer")

        assert bag["a.b.c"] == 42
        assert bag["a.b.c?type"] == "integer"

    def test_set_attr_using_bracket_syntax(self):
        """?attr works via __setitem__ (bag[path] = value)."""
        bag = Bag()
        bag["x"] = 100
        bag["x?unit"] = "meters"

        assert bag["x"] == 100
        node = bag.get_node("x")
        assert node.attr["unit"] == "meters"

    def test_set_attr_creates_node_if_missing(self):
        """?attr creates node with None value if it doesn't exist."""
        bag = Bag()
        bag.set_item("missing?attr", "value")
        # Node is created with None value and the attribute set
        assert "missing" in bag
        assert bag["missing"] is None
        assert bag["missing?attr"] == "value"

    def test_set_attr_overwrites_existing_attr(self):
        """?attr overwrites existing attribute."""
        bag = Bag()
        bag.set_item("node", "val", _attributes={"myattr": "old"})
        bag.set_item("node?myattr", "new")

        assert bag.get_node("node").attr["myattr"] == "new"

    def test_set_attr_triggers_event(self):
        """?attr triggers update event when do_trigger=True."""
        bag = Bag()
        bag["node"] = "value"

        events = []
        bag.subscribe("test", any=lambda **kw: events.append(kw["evt"]))

        bag.set_item("node?myattr", "attr_value")

        assert "upd_attrs" in events

    def test_set_attr_no_trigger(self):
        """?attr respects do_trigger=False."""
        bag = Bag()
        bag["node"] = "value"

        events = []
        bag.subscribe("test", any=lambda **kw: events.append(kw["evt"]))

        bag.set_item("node?myattr", "attr_value", do_trigger=False)

        assert len(events) == 0

    def test_set_attr_replaces_non_bag_with_bag(self):
        """?attr on nested path replaces non-Bag values with Bags."""
        bag = Bag()
        bag["a"] = "string_value"  # a is a string, not a Bag
        bag.set_item("a.b.c?color", "red")

        # a was replaced with a Bag
        assert isinstance(bag["a"], Bag)
        # nested structure was created
        assert bag["a.b.c"] is None
        assert bag["a.b.c?color"] == "red"


class TestBagAsDict:
    """Test as_dict method."""

    def test_as_dict_simple(self):
        """Convert simple Bag to dict."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        result = bag.as_dict()
        assert result == {"a": 1, "b": 2}

    def test_as_dict_with_ascii(self):
        """as_dict with ascii=True converts keys to str."""
        bag = Bag()
        bag["name"] = "test"
        bag["count"] = 42
        result = bag.as_dict(ascii=True)
        assert result == {"name": "test", "count": 42}
        assert all(isinstance(k, str) for k in result.keys())

    def test_as_dict_with_lower(self):
        """as_dict with lower=True converts keys to lowercase."""
        bag = Bag()
        bag["Name"] = "test"
        bag["COUNT"] = 42
        result = bag.as_dict(lower=True)
        assert result == {"name": "test", "count": 42}

    def test_as_dict_with_ascii_and_lower(self):
        """as_dict with both ascii and lower."""
        bag = Bag()
        bag["MyKey"] = "value"
        result = bag.as_dict(ascii=True, lower=True)
        assert result == {"mykey": "value"}

    def test_as_dict_nested_returns_bag(self):
        """as_dict only converts first level, nested Bags remain."""
        bag = Bag()
        bag["a.b"] = "nested"
        result = bag.as_dict()
        assert isinstance(result["a"], Bag)


class TestBagSetdefault:
    """Test setdefault method."""

    def test_setdefault_new_key(self):
        """setdefault creates key if not present."""
        bag = Bag()
        result = bag.setdefault("missing", "default_value")
        assert result == "default_value"
        assert bag["missing"] == "default_value"

    def test_setdefault_existing_key(self):
        """setdefault returns existing value without changing it."""
        bag = Bag()
        bag["existing"] = "original"
        result = bag.setdefault("existing", "new_value")
        assert result == "original"
        assert bag["existing"] == "original"

    def test_setdefault_none_default(self):
        """setdefault with default None."""
        bag = Bag()
        result = bag.setdefault("key")
        assert result is None
        assert bag["key"] is None


class TestBagUpdate:
    """Test update method."""

    def test_update_from_dict(self):
        """Update Bag from dict."""
        bag = Bag()
        bag["a"] = 1
        bag.update({"a": 10, "b": 2})
        assert bag["a"] == 10
        assert bag["b"] == 2

    def test_update_from_bag(self):
        """Update Bag from another Bag."""
        bag = Bag()
        bag["a"] = 1
        source = Bag()
        source["a"] = 10
        source["b"] = 2
        bag.update(source)
        assert bag["a"] == 10
        assert bag["b"] == 2

    def test_update_ignore_none(self):
        """Update with ignore_none=True doesn't overwrite with None."""
        bag = Bag()
        bag["a"] = "keep_me"
        bag.update({"a": None, "b": "new"}, ignore_none=True)
        assert bag["a"] == "keep_me"
        assert bag["b"] == "new"

    def test_update_ignore_none_false(self):
        """Update with ignore_none=False overwrites with None."""
        bag = Bag()
        bag["a"] = "replace_me"
        bag.update({"a": None}, ignore_none=False)
        assert bag["a"] is None

    def test_update_nested_bags_from_dict(self):
        """Update nested Bags from dict (non-recursive)."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag.update({"a": 10, "c": 3})
        assert bag["a"] == 10
        assert bag["b"] == 2
        assert bag["c"] == 3

    def test_update_with_attributes(self):
        """Update preserves and merges attributes."""
        bag = Bag()
        bag.set_item("a", 1, attr1="old")
        source = Bag()
        source.set_item("a", 2, attr2="new")
        bag.update(source)
        assert bag["a"] == 2
        node = bag.get_node("a")
        assert node.attr.get("attr1") == "old"
        assert node.attr.get("attr2") == "new"


class TestBagDeepcopy:
    """Test deepcopy method."""

    def test_deepcopy_simple(self):
        """Deepcopy creates independent copy."""
        bag = Bag()
        bag["a"] = 1
        copy = bag.deepcopy()
        copy["a"] = 2
        assert bag["a"] == 1
        assert copy["a"] == 2

    def test_deepcopy_nested(self):
        """Deepcopy recursively copies nested Bags."""
        bag = Bag()
        bag["a.b"] = "original"
        copy = bag.deepcopy()
        copy["a.b"] = "modified"
        assert bag["a.b"] == "original"
        assert copy["a.b"] == "modified"

    def test_deepcopy_preserves_attributes(self):
        """Deepcopy preserves node attributes."""
        bag = Bag()
        bag.set_item("x", 42, color="red", size=10)
        copy = bag.deepcopy()
        node = copy.get_node("x")
        assert node.attr["color"] == "red"
        assert node.attr["size"] == 10


class TestBagPickle:
    """Test pickle support."""

    def test_pickle_simple(self):
        """Pickle and unpickle simple Bag."""
        import pickle

        bag = Bag()
        bag["a"] = 1
        bag["b"] = "text"
        data = pickle.dumps(bag)
        restored = pickle.loads(data)
        assert restored["a"] == 1
        assert restored["b"] == "text"

    def test_pickle_nested(self):
        """Pickle and unpickle nested Bag."""
        import pickle

        bag = Bag()
        bag["x.y.z"] = "deep"
        data = pickle.dumps(bag)
        restored = pickle.loads(data)
        assert restored["x.y.z"] == "deep"

    def test_pickle_with_backref(self):
        """Pickle Bag with backref enabled."""
        import pickle

        bag = Bag()
        bag.set_backref()
        bag["a.b"] = "value"
        data = pickle.dumps(bag)
        restored = pickle.loads(data)
        assert restored["a.b"] == "value"
        # After unpickling, backref is restored
        assert restored.backref is True


class TestBagGetNode:
    """Test get_node method with various parameters."""

    def test_get_node_basic(self):
        """Get node at path."""
        bag = Bag()
        bag.set_item("x", 42, color="blue")
        node = bag.get_node("x")
        assert node is not None
        assert node.value == 42
        assert node.attr["color"] == "blue"

    def test_get_node_missing(self):
        """Get missing node returns None."""
        bag = Bag()
        node = bag.get_node("missing")
        assert node is None

    def test_get_node_as_tuple(self):
        """Get node with as_tuple returns (bag, node)."""
        bag = Bag()
        bag["a.b"] = "value"
        result = bag.get_node("a.b", as_tuple=True)
        assert isinstance(result, tuple)
        assert isinstance(result[0], Bag)
        assert result[1].value == "value"

    def test_get_node_autocreate(self):
        """Get node with autocreate creates if missing."""
        bag = Bag()
        node = bag.get_node("new_key", autocreate=True, default="created")
        assert node is not None
        assert node.value == "created"

    def test_get_node_by_index(self):
        """Get node by integer index."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag["c"] = 3
        node = bag.get_node(1)
        assert node.value == 2
        assert node.label == "b"

    def test_get_node_empty_path(self):
        """Get node with empty path returns parent_node."""
        bag = Bag()
        bag.set_backref()
        bag["child.item"] = "x"
        child_bag = bag["child"]
        # The parent_node of child_bag is the node 'child' in bag
        assert child_bag.get_node(None) is not None


class TestBagStr:
    """Test __str__ representation."""

    def test_str_simple(self):
        """String representation of simple Bag."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = "text"
        s = str(bag)
        assert "a" in s
        assert "b" in s
        assert "1" in s
        assert "text" in s

    def test_str_nested(self):
        """String representation of nested Bag."""
        bag = Bag()
        bag["x.y"] = "deep"
        s = str(bag)
        assert "x" in s
        assert "y" in s

    def test_str_with_attributes(self):
        """String representation shows attributes."""
        bag = Bag()
        bag.set_item("item", "val", dtype="str")
        s = str(bag)
        assert "dtype" in s

    def test_str_with_none(self):
        """String representation handles None values."""
        bag = Bag()
        bag["empty"] = None
        s = str(bag)
        assert "None" in s

    def test_str_with_bytes(self):
        """String representation handles bytes."""
        bag = Bag()
        bag["data"] = b"hello"
        s = str(bag)
        assert "hello" in s

    def test_str_circular_reference(self):
        """String representation handles circular references.

        Covers bag.py line 1173: visited node detection.
        """
        bag = Bag()
        bag["name"] = "parent"
        bag["self_ref"] = bag  # circular reference
        s = str(bag)
        assert "name" in s
        assert "self_ref" in s
        assert "visited at" in s  # should detect the circular reference

    def test_str_type_with_dot_in_name(self):
        """String representation handles types with dots in name.

        Covers bag.py line 1184: type name with module prefix.
        """
        # Create a class with a dotted __name__ (simulating module.ClassName)
        class DottedType:
            pass

        DottedType.__name__ = "mymodule.CustomClass"

        bag = Bag()
        bag["custom"] = DottedType()
        s = str(bag)
        assert "custom" in s
        assert "CustomClass" in s  # should extract just the class name


class TestBagEquality:
    """Test __eq__ and __ne__."""

    def test_equal_simple(self):
        """Equal Bags with same content."""
        bag1 = Bag()
        bag1["a"] = 1
        bag2 = Bag()
        bag2["a"] = 1
        assert bag1 == bag2

    def test_not_equal_different_values(self):
        """Bags with different values are not equal."""
        bag1 = Bag()
        bag1["a"] = 1
        bag2 = Bag()
        bag2["a"] = 2
        assert bag1 != bag2

    def test_not_equal_different_keys(self):
        """Bags with different keys are not equal."""
        bag1 = Bag()
        bag1["a"] = 1
        bag2 = Bag()
        bag2["b"] = 1
        assert bag1 != bag2

    def test_equal_nested(self):
        """Equal nested Bags."""
        bag1 = Bag()
        bag1["x.y"] = "val"
        bag2 = Bag()
        bag2["x.y"] = "val"
        assert bag1 == bag2

    def test_not_equal_to_non_bag(self):
        """Bag is not equal to non-Bag."""
        bag = Bag()
        bag["a"] = 1
        assert bag != {"a": 1}


class TestBagProperties:
    """Test various properties."""

    def test_fullpath_root(self):
        """Fullpath of root Bag is None."""
        bag = Bag()
        assert bag.fullpath is None

    def test_fullpath_nested(self):
        """Fullpath of nested Bag with backref."""
        bag = Bag()
        bag.set_backref()
        bag["a.b.c"] = "x"
        nested = bag["a.b"]
        assert nested.fullpath == "a.b"

    def test_root_attributes_get_set(self):
        """Get and set root_attributes."""
        bag = Bag()
        bag.root_attributes = {"version": "1.0"}
        assert bag.root_attributes == {"version": "1.0"}


class TestBagDelAttr:
    """Test del_attr method."""

    def test_del_attr_single(self):
        """Delete single attribute."""
        bag = Bag()
        bag.set_item("x", 1, color="red", size=10)
        bag.del_attr("x", "color")
        node = bag.get_node("x")
        assert "color" not in node.attr
        assert "size" in node.attr

    def test_del_attr_multiple(self):
        """Delete multiple attributes."""
        bag = Bag()
        bag.set_item("x", 1, a=1, b=2, c=3)
        bag.del_attr("x", "a", "b")
        node = bag.get_node("x")
        assert "a" not in node.attr
        assert "b" not in node.attr
        assert "c" in node.attr


class TestBagGetInheritedAttributes:
    """Test get_inherited_attributes method."""

    def test_inherited_attributes_from_parent(self):
        """Get attributes inherited from parent chain."""
        bag = Bag()
        bag.set_backref()
        bag.set_item("parent", Bag(), color="blue")
        parent_bag = bag["parent"]
        parent_bag.set_item("child", "value")
        child_node = parent_bag.get_node("child")
        # The child should be able to see parent's inherited attributes
        inherited = parent_bag.get_inherited_attributes()
        assert isinstance(inherited, dict)


class TestBagSort:
    """Test sort method."""

    def test_sort_by_key_ascending(self):
        """Sort by key ascending."""
        bag = Bag()
        bag["c"] = 3
        bag["a"] = 1
        bag["b"] = 2
        bag.sort("#k:a")
        assert bag.keys() == ["a", "b", "c"]

    def test_sort_by_key_descending(self):
        """Sort by key descending."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag["c"] = 3
        bag.sort("#k:d")
        assert bag.keys() == ["c", "b", "a"]

    def test_sort_by_value_ascending(self):
        """Sort by value ascending."""
        bag = Bag()
        bag["x"] = 30
        bag["y"] = 10
        bag["z"] = 20
        bag.sort("#v:a")
        assert bag.keys() == ["y", "z", "x"]

    def test_sort_by_value_descending(self):
        """Sort by value descending."""
        bag = Bag()
        bag["x"] = 10
        bag["y"] = 30
        bag["z"] = 20
        bag.sort("#v:d")
        assert bag.keys() == ["y", "z", "x"]

    def test_sort_by_attribute(self):
        """Sort by attribute value using #a.attr syntax."""
        bag = Bag()
        bag.set_item("a", 1, order=3)
        bag.set_item("b", 2, order=1)
        bag.set_item("c", 3, order=2)
        bag.sort("#a.order:a")
        assert bag.keys() == ["b", "c", "a"]

    def test_sort_with_callable(self):
        """Sort with custom callable."""
        bag = Bag()
        bag["abc"] = 1
        bag["a"] = 2
        bag["ab"] = 3
        bag.sort(key=lambda n: len(n.label))
        assert bag.keys() == ["a", "ab", "abc"]


class TestBagSum:
    """Test sum method."""

    def test_sum_values(self):
        """Sum all values."""
        bag = Bag()
        bag["a"] = 10
        bag["b"] = 20
        bag["c"] = 30
        assert bag.sum("#v") == 60

    def test_sum_with_condition(self):
        """Sum values matching condition."""
        bag = Bag()
        bag["a"] = 10
        bag["b"] = 20
        bag["c"] = 30
        result = bag.sum("#v", condition=lambda n: n.value > 15)
        assert result == 50

    def test_sum_attribute(self):
        """Sum attribute values using #a.attr syntax."""
        bag = Bag()
        bag.set_item("a", "x", score=10)
        bag.set_item("b", "y", score=20)
        bag.set_item("c", "z", score=30)
        assert bag.sum("#a.score") == 60


class TestBagIsEmpty:
    """Test is_empty method."""

    def test_is_empty_true(self):
        """Empty Bag is empty."""
        bag = Bag()
        assert bag.is_empty() is True

    def test_is_empty_false(self):
        """Bag with items is not empty."""
        bag = Bag()
        bag["a"] = 1
        assert bag.is_empty() is False

    def test_is_empty_zero_is_none(self):
        """is_empty with zero_is_none treats 0 as empty."""
        bag = Bag()
        bag["a"] = 0
        assert bag.is_empty(zero_is_none=True) is True

    def test_is_empty_blank_is_none(self):
        """is_empty with blank_is_none treats '' as empty."""
        bag = Bag()
        bag["a"] = ""
        assert bag.is_empty(blank_is_none=True) is True

    def test_is_empty_with_none_value(self):
        """Bag with only None value is considered empty."""
        bag = Bag()
        bag["a"] = None
        assert bag.is_empty() is True


class TestBagGetNodeByAttr:
    """Test get_node_by_attr method."""

    def test_get_node_by_attr_found(self):
        """Find node by attribute value."""
        bag = Bag()
        bag.set_item("a", 1, id="first")
        bag.set_item("b", 2, id="second")
        bag.set_item("c", 3, id="third")
        node = bag.get_node_by_attr("id", "second")
        assert node is not None
        assert node.label == "b"

    def test_get_node_by_attr_not_found(self):
        """Return None if no node with attribute."""
        bag = Bag()
        bag.set_item("a", 1, id="first")
        node = bag.get_node_by_attr("id", "missing")
        assert node is None


class TestBagGetNodeByValue:
    """Test get_node_by_value method."""

    def test_get_node_by_value_found(self):
        """Find node by nested value."""
        bag = Bag()
        bag["a.name"] = "alice"
        bag["b.name"] = "bob"
        bag["c.name"] = "charlie"
        node = bag.get_node_by_value("name", "bob")
        assert node is not None
        assert node.label == "b"

    def test_get_node_by_value_not_found(self):
        """Return None if no node with value."""
        bag = Bag()
        bag["a.name"] = "alice"
        node = bag.get_node_by_value("name", "missing")
        assert node is None


class TestBagQueryIterVariants:
    """Test query/digest methods with iter parameter."""

    def test_keys_iter(self):
        """keys with iter=True returns iterator."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        result = bag.keys(iter=True)
        assert hasattr(result, "__iter__")
        assert list(result) == ["a", "b"]

    def test_values_iter(self):
        """values with iter=True returns iterator."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        result = bag.values(iter=True)
        assert hasattr(result, "__iter__")
        assert list(result) == [1, 2]

    def test_items_iter(self):
        """items with iter=True returns iterator."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        result = bag.items(iter=True)
        assert hasattr(result, "__iter__")
        assert list(result) == [("a", 1), ("b", 2)]


class TestBagPopNode:
    """Test pop_node method."""

    def test_pop_node_existing(self):
        """Pop existing node returns the node."""
        bag = Bag()
        bag.set_item("x", 42, color="red")
        node = bag.pop_node("x")
        assert node is not None
        assert node.value == 42
        assert node.attr["color"] == "red"
        assert "x" not in bag

    def test_pop_node_missing(self):
        """Pop missing node returns None."""
        bag = Bag()
        node = bag.pop_node("missing")
        assert node is None

    def test_pop_node_nested(self):
        """Pop nested node."""
        bag = Bag()
        bag["a.b.c"] = "deep"
        node = bag.pop_node("a.b.c")
        assert node is not None
        assert node.value == "deep"
        assert bag["a.b.c"] is None


class TestBagGetAttr:
    """Test get_attr method based on docstring.

    Args documented:
        path: Path to the node. If None, uses parent_node.
        attr: Attribute name to get.
        default: Default value if node or attribute not found.
    """

    def test_get_attr_with_path_and_attr(self):
        """Get specific attribute from node at path."""
        bag = Bag()
        bag.set_item("x", 42, color="red", size=10)
        assert bag.get_attr("x", "color") == "red"
        assert bag.get_attr("x", "size") == 10

    def test_get_attr_missing_attr_returns_default(self):
        """Get missing attribute returns default."""
        bag = Bag()
        bag.set_item("x", 42, color="red")
        assert bag.get_attr("x", "missing") is None
        assert bag.get_attr("x", "missing", default="fallback") == "fallback"

    def test_get_attr_missing_path_returns_default(self):
        """Get attribute from missing path returns default."""
        bag = Bag()
        assert bag.get_attr("missing", "attr") is None
        assert bag.get_attr("missing", "attr", default="fallback") == "fallback"

    def test_get_attr_path_none_uses_parent_node(self):
        """Get attribute with path=None uses parent_node."""
        bag = Bag()
        bag.set_backref()
        bag.set_item("child", Bag(), color="blue")
        child_bag = bag["child"]
        # child_bag.parent_node is the 'child' node which has color='blue'
        # get_attr(None) should get from parent_node
        # But the docstring says "uses parent_node" - need to check what this means
        result = child_bag.get_attr(None, "color")
        assert result == "blue"


class TestBagAttributesProperty:
    """Test attributes property based on docstring.

    Documented behavior:
        Returns the attributes dict of the BagNode that contains this Bag.
        Returns an empty dict if this is a standalone Bag with no parent node.
    """

    def test_attributes_standalone_bag_returns_empty(self):
        """Standalone Bag returns empty dict."""
        bag = Bag()
        assert bag.attributes == {}

    def test_attributes_nested_bag_returns_parent_node_attrs(self):
        """Nested Bag returns attributes of containing node."""
        bag = Bag()
        bag.set_backref()
        bag.set_item("child", Bag(), color="red", size=10)
        child_bag = bag["child"]
        attrs = child_bag.attributes
        assert attrs.get("color") == "red"
        assert attrs.get("size") == 10


class TestBagSetCallbackItem:
    """Test set_callback_item method based on docstring.

    Documented args:
        path: Path to the node.
        callback: Callable that returns the value. Can be sync or async.
        **kwargs: Arguments passed to BagCbResolver (cache_time, read_only).
    """

    def test_set_callback_item_basic(self):
        """Set callback item with basic sync callback."""
        bag = Bag()
        counter = [0]

        def get_value():
            counter[0] += 1
            return f"value_{counter[0]}"

        bag.set_callback_item("dynamic", get_value)

        # Access via resolver directly (sync way)
        node = bag.get_node("dynamic")
        assert node.resolver is not None
        result1 = node.resolver()
        result2 = node.resolver()
        assert result1 == "value_1"
        assert result2 == "value_2"  # called again, no cache

    def test_set_callback_item_with_cache(self):
        """Set callback item with cache_time."""
        bag = Bag()
        counter = [0]

        def get_value():
            counter[0] += 1
            return counter[0]

        # cache_time=-1 means infinite cache, read_only=False required for caching
        bag.set_callback_item("cached", get_value, cache_time=-1, read_only=False)

        # Access via resolver directly
        node = bag.get_node("cached")
        node.resolver()
        node.resolver()
        node.resolver()
        # Only first call actually loads
        assert counter[0] == 1

    def test_set_callback_item_async(self):
        """Set callback item with async callback."""
        bag = Bag()
        counter = [0]

        async def async_get_value():
            counter[0] += 1
            return f"async_value_{counter[0]}"

        bag.set_callback_item("async_dynamic", async_get_value)

        # Access via resolver - @smartasync handles sync/async automatically
        node = bag.get_node("async_dynamic")
        assert node.resolver is not None

        # Call resolver in sync context - @smartasync uses asyncio.run internally
        result = node.resolver()
        assert result == "async_value_1"

    def test_set_callback_item_returns_dict(self):
        """Set callback item that returns a dict/JSON structure."""
        bag = Bag()

        def get_data():
            return {"name": "John", "age": 30, "address": {"city": "Rome", "zip": "00100"}}

        bag.set_callback_item("user", get_data)

        # Access via resolver
        node = bag.get_node("user")
        result = node.resolver()

        assert isinstance(result, dict)
        assert result["name"] == "John"
        assert result["age"] == 30
        assert result["address"]["city"] == "Rome"

    def test_set_callback_item_returns_list(self):
        """Set callback item that returns a list."""
        bag = Bag()

        def get_items():
            return [
                {"id": 1, "name": "Item 1"},
                {"id": 2, "name": "Item 2"},
                {"id": 3, "name": "Item 3"},
            ]

        bag.set_callback_item("items", get_items)

        node = bag.get_node("items")
        result = node.resolver()

        assert isinstance(result, list)
        assert len(result) == 3
        assert result[0]["id"] == 1


class TestBagFromUrl:
    """Test from_url class method based on docstring.

    Documented:
        url: URL to fetch content from.
        timeout: Request timeout in seconds.

    Uses UrlResolver internally, which detects format from content-type header.
    """

    @pytest.mark.network
    def test_from_url_xml(self):
        """Load Bag from XML URL."""
        # Use a public XML endpoint (content-type: text/xml or application/xml)
        url = "https://www.w3schools.com/xml/note.xml"
        bag = Bag.from_url(url)

        assert isinstance(bag, Bag)
        assert len(bag) > 0

    @pytest.mark.network
    def test_from_url_json(self):
        """Load Bag from JSON URL."""
        # Use a public JSON endpoint (content-type: application/json)
        url = "https://jsonplaceholder.typicode.com/todos/1"
        bag = Bag.from_url(url)

        assert isinstance(bag, Bag)
        # JSON response has userId, id, title, completed fields
        assert "userId" in bag.keys() or "id" in bag.keys()


class TestBagQueryAdvanced:
    """Test query method advanced parameters based on docstring.

    Documented args not yet tested:
        leaf: If True (default), include leaf nodes.
        branch: If True (default), include branch nodes.
        limit: Maximum number of results to return.
    """

    def test_query_branch_false_only_leaves(self):
        """query with branch=False returns only leaf nodes."""
        bag = Bag()
        bag["a"] = 1
        bag["b.c"] = 2
        bag["b.d"] = 3
        result = bag.query("#k", deep=True, branch=False)
        # Should not include 'b' (it's a branch), only leaves
        assert "a" in result
        assert "c" in result
        assert "d" in result
        assert "b" not in result

    def test_query_leaf_false_only_branches(self):
        """query with leaf=False returns only branch nodes."""
        bag = Bag()
        bag["a"] = 1
        bag["b.c"] = 2
        result = bag.query("#k", deep=True, leaf=False)
        # Should only include 'b' (branch), not 'a' or 'c' (leaves)
        assert "b" in result
        assert "a" not in result
        assert "c" not in result

    def test_query_limit(self):
        """query with limit returns at most N results."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag["c"] = 3
        bag["d"] = 4
        result = bag.query("#k", limit=2)
        assert len(result) == 2
        assert result == ["a", "b"]

    def test_query_static_value(self):
        """query with #__v returns static value (bypassing resolver)."""
        bag = Bag()
        bag["normal"] = "static_value"
        result = bag.query("#k,#__v")
        assert result == [("normal", "static_value")]


class TestBagCoverageMissing:
    """Tests to cover missing lines in bag.py using only public API."""

    # Line 139: fill_from with unsupported type
    def test_fill_from_invalid_type(self):
        """fill_from raises TypeError for unsupported types."""
        bag = Bag()
        with pytest.raises(TypeError, match="fill_from expects"):
            bag.fill_from(12345)

    # Line 356: path as list (not string)
    def test_get_item_path_as_list(self):
        """get_item works with path as list."""
        bag = Bag()
        bag["a.b.c"] = "value"
        assert bag[["a", "b", "c"]] == "value"

    # Lines 360-361: #parent navigation in path
    def test_parent_navigation_in_path(self):
        """Path with #parent navigates up."""
        bag = Bag()
        bag.set_backref()
        bag["a.b"] = Bag()
        bag["a.b.c"] = "value"
        bag["a.x"] = "sibling"
        # Navigate from b to parent (a) then to x
        child = bag["a.b"]
        assert child["#parent.x"] == "sibling"

    # Line 386, 492, 518: empty path returns self
    def test_get_item_empty_path(self):
        """get_item with empty path returns self."""
        bag = Bag({"a": 1})
        assert bag.get_item("") is bag

    # Line 391: read mode path with non-existent intermediate
    def test_get_nonexistent_deep_path(self):
        """Getting non-existent deep path returns None."""
        bag = Bag()
        bag["a"] = 1
        assert bag["a.b.c.d"] is None

    # Line 399: write mode with #n for non-existent index in path
    def test_set_item_hash_n_nonexistent(self):
        """set_item with #n in intermediate path raises when index doesn't exist."""
        from genro_bag.bag import BagException

        bag = Bag()
        bag["a"] = Bag()  # create intermediate Bag
        # Path #5.x requires creating intermediate #5 which doesn't exist
        with pytest.raises(BagException, match="Not existing index"):
            bag["a.#5.x"] = "value"  # #5 index doesn't exist, can't create intermediate

    # Line 436: _traverse_until when intermediate is not Bag
    def test_traverse_non_bag_intermediate(self):
        """Traversing through non-Bag intermediate returns None."""
        bag = Bag()
        bag["a"] = "string_value"  # not a Bag
        assert bag["a.b"] is None

    # Lines 550, 552: get() with empty label or #parent
    def test_get_empty_label(self):
        """get() with empty label returns self."""
        bag = Bag({"a": 1})
        assert bag.get("") is bag

    def test_get_parent_label(self):
        """get() with #parent returns parent."""
        bag = Bag()
        bag.set_backref()
        bag["child"] = Bag()
        child = bag["child"]
        assert child.get("#parent") is bag

    # Lines 687-688: resolver with attributes
    def test_set_item_resolver_with_attributes(self):
        """set_item with resolver that has attributes merges them."""
        from genro_bag.resolver import BagResolver

        class AttrResolver(BagResolver):
            attributes = {"from_resolver": True}

            def load(self):
                return "resolved"

        bag = Bag()
        bag.set_item("x", None, resolver=AttrResolver(), color="blue")
        node = bag.get_node("x")
        assert node.attr.get("color") == "blue"
        assert node.attr.get("from_resolver") is True

    # Line 694: set_item with #n syntax raises
    def test_set_item_hash_n_syntax(self):
        """set_item with #n for new node raises."""
        from genro_bag.bag import BagException

        bag = Bag()
        bag["a"] = Bag()
        with pytest.raises(BagException, match="Cannot create new node"):
            bag["a.#99"] = "value"

    # Lines 768->772: pop when path doesn't exist
    def test_pop_nonexistent_path(self):
        """pop on non-existent path returns default."""
        bag = Bag()
        bag["a"] = 1
        result = bag.pop("x.y.z", default="missing")
        assert result == "missing"

    # Lines 804->806: pop_node when path doesn't exist
    def test_pop_node_nonexistent(self):
        """pop_node on non-existent path returns None."""
        bag = Bag()
        bag["a"] = 1
        result = bag.pop_node("x.y.z")
        assert result is None

    # Line 829: clear with backref
    def test_clear_with_backref(self):
        """clear() with backref fires delete events."""
        bag = Bag()
        bag.set_backref()
        bag["a"] = 1
        bag["b"] = 2
        deleted = []
        # node is a list of all deleted nodes when clear() is called
        bag.subscribe("test", delete=lambda **kw: deleted.extend([n.label for n in kw["node"]]))
        bag.clear()
        assert len(bag) == 0
        assert "a" in deleted and "b" in deleted

    # Line 897: set_attr uses get_node with autocreate
    def test_set_attr_on_existing_node(self):
        """set_attr sets attribute on existing node."""
        bag = Bag()
        bag["x"] = "value"
        bag.set_attr("x", color="red")
        node = bag.get_node("x")
        assert node.attr.get("color") == "red"

    # Line 926->exit: del_attr when node doesn't exist
    def test_del_attr_nonexistent_node(self):
        """del_attr on non-existent node does nothing."""
        bag = Bag()
        bag["a"] = 1
        # Should not raise
        bag.del_attr("nonexistent", "color")

    # Line 937: get_inherited_attributes without parent
    def test_get_inherited_attributes_no_parent(self):
        """get_inherited_attributes without parent returns empty dict."""
        bag = Bag()
        bag["a"] = 1
        assert bag.get_inherited_attributes() == {}

    # Line 1030: type_name with dot (not reachable - Python types don't have dots)
    # Skipped - standard Python types don't produce dotted names

    # Lines 1113-1116: __contains__ with BagNode or other type
    def test_contains_bagnode(self):
        """__contains__ with BagNode checks node membership."""
        bag = Bag()
        bag["a"] = 1
        node = bag.get_node("a")
        assert node in bag

    def test_contains_other_type(self):
        """__contains__ with non-string/non-BagNode returns False."""
        bag = Bag()
        bag["a"] = 1
        assert 12345 not in bag
        assert ["a"] not in bag

    # Line 1232: update with nested Bag merge
    def test_update_nested_bag_merge(self):
        """update merges nested Bags recursively."""
        bag1 = Bag()
        bag1["config.host"] = "localhost"
        bag1["config.port"] = 8080

        bag2 = Bag()
        bag2["config.port"] = 9090
        bag2["config.timeout"] = 30

        bag1.update(bag2)
        assert bag1["config.host"] == "localhost"
        assert bag1["config.port"] == 9090
        assert bag1["config.timeout"] == 30

    # Bug report: update() passes attr= instead of _attributes= to set_item
    def test_update_preserves_attributes(self):
        """Bug: update() passes attr= to set_item which expects _attributes=.

        This causes attributes to be stored as a kwarg named 'attr' instead
        of being set as node attributes.
        """
        source = Bag()
        source.set_item("key", "value", _attributes={"color": "red", "size": 10})

        target = Bag()
        target.update(source)

        # Attributes should be preserved on the node
        node = target.get_node("key")
        assert node is not None
        assert node.attr.get("color") == "red", "Attribute 'color' not preserved"
        assert node.attr.get("size") == 10, "Attribute 'size' not preserved"
        # Should NOT have an 'attr' attribute (that would be the bug)
        assert "attr" not in node.attr, "Bug: 'attr' stored as attribute instead of _attributes"

    # Line 1262: get_node with autocreate and backref fires insert event
    def test_get_node_autocreate_with_backref(self):
        """get_node with autocreate and backref fires insert event."""
        bag = Bag()
        bag.set_backref()
        inserted = []
        bag.subscribe("test", insert=lambda **kw: inserted.append(kw["node"].label))
        node = bag.get_node("new_node", autocreate=True)
        assert node is not None
        assert "new_node" in bag.keys()
        assert "new_node" in inserted

    # Bug report: autocreate returns ghost node not in container
    def test_get_node_autocreate_returns_registered_node(self):
        """Bug: _get_node autocreate returns unregistered 'ghost' node.

        The node returned by _get_node(autocreate=True) must be the SAME
        node that is registered in the container, not a different instance.
        This ensures backref/events work correctly.
        """
        bag = Bag()
        bag.set_backref()

        # Get node with autocreate
        returned_node = bag.get_node("test_key", autocreate=True, default="value")

        # Get the node that's actually in the container
        container_node = bag._nodes.get("test_key")

        # They MUST be the same object
        assert returned_node is container_node, (
            f"Returned node {id(returned_node)} differs from "
            f"container node {id(container_node)} - ghost node bug!"
        )

    # Line 1313: get_node returns None for non-existent
    def test_get_node_nonexistent(self):
        """get_node returns None for non-existent path."""
        bag = Bag()
        bag["a"] = 1
        assert bag.get_node("x.y.z") is None

    # Line 1343->exit: clear_backref when not in backref mode
    def test_clear_backref_not_in_backref_mode(self):
        """clear_backref does nothing when not in backref mode."""
        bag = Bag()
        bag["a"] = 1
        # Should not raise, just does nothing
        bag.clear_backref()
        assert bag["a"] == 1

    # Lines 1429->1431: unsubscribe with update or any
    def test_unsubscribe_update(self):
        """unsubscribe with update=True removes update subscriber."""
        bag = Bag()
        bag.subscribe("test", update=lambda *a: None)
        assert "test" in bag._upd_subscribers
        bag.unsubscribe("test", update=True)
        assert "test" not in bag._upd_subscribers

    def test_unsubscribe_any(self):
        """unsubscribe with any=True removes all subscriptions."""
        bag = Bag()
        bag.subscribe("test", update=lambda *a: None, insert=lambda *a: None)
        bag.unsubscribe("test", any=True)
        assert "test" not in bag._upd_subscribers
        assert "test" not in bag._ins_subscribers

    def test_unsubscribe_insert_only(self):
        """unsubscribe with insert=True only removes insert subscriber."""
        bag = Bag()
        bag.subscribe("test", update=lambda *a: None, insert=lambda *a: None)
        bag.unsubscribe("test", insert=True)
        # update still there, insert removed
        assert "test" in bag._upd_subscribers
        assert "test" not in bag._ins_subscribers


class TestBagSerializationRoundtrip:
    """Tests for serialization via roundtrip - format is opaque."""

    # ==================== TYTX Roundtrip ====================

    def test_tytx_roundtrip_simple_values(self):
        """TYTX roundtrip preserves simple values."""
        original = Bag()
        original["string"] = "hello"
        original["integer"] = 42
        original["float"] = 3.14
        original["boolean"] = True

        restored = Bag.from_tytx(original.to_tytx())

        assert restored["string"] == "hello"
        assert restored["integer"] == 42
        assert restored["float"] == 3.14
        assert restored["boolean"] is True

    def test_tytx_roundtrip_nested_bags(self):
        """TYTX roundtrip preserves nested Bag structures."""
        original = Bag()
        original["a.b.c"] = 1
        original["a.b.d"] = 2
        original["a.e"] = 3

        restored = Bag.from_tytx(original.to_tytx())

        assert restored["a.b.c"] == 1
        assert restored["a.b.d"] == 2
        assert restored["a.e"] == 3
        assert isinstance(restored["a"], Bag)
        assert isinstance(restored["a.b"], Bag)

    def test_tytx_roundtrip_with_attributes(self):
        """TYTX roundtrip preserves node attributes."""
        original = Bag()
        original.set_item("item", "value", _attributes={"id": 123, "active": True})

        restored = Bag.from_tytx(original.to_tytx())

        node = restored.get_node("item")
        assert node.attr.get("id") == 123
        assert node.attr.get("active") is True

    def test_tytx_roundtrip_with_none(self):
        """TYTX roundtrip preserves None values."""
        original = Bag()
        original.set_item("null_value", None)
        original["normal"] = "text"

        restored = Bag.from_tytx(original.to_tytx())

        assert restored["null_value"] is None
        assert restored["normal"] == "text"

    def test_tytx_roundtrip_with_tags(self):
        """TYTX roundtrip preserves node tags."""
        original = Bag()
        original["item"] = "value"
        original.get_node("item").tag = "custom_tag"

        restored = Bag.from_tytx(original.to_tytx())

        assert restored.get_node("item").tag == "custom_tag"

    def test_tytx_roundtrip_compact_mode(self):
        """TYTX roundtrip works with compact=True."""
        original = Bag()
        original["a.b.c"] = 1
        original["a.b.d"] = 2

        restored = Bag.from_tytx(original.to_tytx(compact=True))

        assert restored["a.b.c"] == 1
        assert restored["a.b.d"] == 2

    def test_tytx_roundtrip_datetime(self):
        """TYTX roundtrip preserves datetime types (datetime becomes UTC-aware)."""
        import datetime

        original = Bag()
        original["date"] = datetime.date(2025, 1, 15)
        original["time"] = datetime.time(14, 30, 0)
        # TYTX normalizes datetime to UTC - use aware datetime for equality
        original["datetime"] = datetime.datetime(
            2025, 1, 15, 14, 30, 0, tzinfo=datetime.timezone.utc
        )

        restored = Bag.from_tytx(original.to_tytx())

        assert restored["date"] == datetime.date(2025, 1, 15)
        assert restored["time"] == datetime.time(14, 30, 0)
        assert restored["datetime"] == datetime.datetime(
            2025, 1, 15, 14, 30, 0, tzinfo=datetime.timezone.utc
        )

    def test_tytx_roundtrip_decimal(self):
        """TYTX roundtrip preserves Decimal type."""
        from decimal import Decimal

        original = Bag()
        original["price"] = Decimal("19.99")

        restored = Bag.from_tytx(original.to_tytx())

        assert restored["price"] == Decimal("19.99")
        assert isinstance(restored["price"], Decimal)

    def test_tytx_file_roundtrip(self, tmp_path):
        """TYTX roundtrip via file."""
        original = Bag()
        original["test"] = "data"
        original["nested.value"] = 42

        filepath = tmp_path / "output"
        original.to_tytx(filename=str(filepath))

        # File gets .bag.json extension
        assert (tmp_path / "output.bag.json").exists()
        content = (tmp_path / "output.bag.json").read_text()
        restored = Bag.from_tytx(content)

        assert restored["test"] == "data"
        assert restored["nested.value"] == 42

    # ==================== JSON Roundtrip ====================

    def test_json_roundtrip_simple(self):
        """JSON roundtrip via from_json(to_json())."""
        original = Bag()
        original["name"] = "test"
        original["count"] = 42

        restored = Bag.from_json(original.to_json())

        assert restored["name"] == "test"
        assert restored["count"] == 42

    def test_json_roundtrip_nested(self):
        """JSON roundtrip preserves nested structure."""
        original = Bag()
        child = Bag()
        child["x"] = 1
        original["parent"] = child

        restored = Bag.from_json(original.to_json())

        assert isinstance(restored["parent"], Bag)
        assert restored["parent.x"] == 1

    def test_json_roundtrip_with_attributes(self):
        """JSON roundtrip preserves attributes."""
        original = Bag()
        original.set_item("item", "value", _attributes={"id": 123})

        restored = Bag.from_json(original.to_json())

        assert restored.get_node("item").attr.get("id") == 123

    def test_json_typed_false(self):
        """to_json with typed=False produces valid JSON."""
        bag = Bag()
        bag["value"] = 123

        json_str = bag.to_json(typed=False)
        restored = Bag.from_json(json_str)

        assert restored["value"] == 123

    # ==================== XML Features (format-specific) ====================

    def test_xml_with_doc_header(self):
        """to_xml with doc_header adds XML declaration."""
        bag = Bag()
        bag["item"] = "value"

        xml = bag.to_xml(doc_header=True)
        assert xml.startswith("<?xml version='1.0'")

    def test_xml_with_custom_header(self):
        """to_xml with doc_header string uses custom header."""
        bag = Bag()
        bag["item"] = "value"

        xml = bag.to_xml(doc_header="<?xml custom?>")
        assert xml.startswith("<?xml custom?>")

    def test_xml_with_pretty(self):
        """to_xml with pretty=True adds formatting."""
        bag = Bag()
        bag["parent.child"] = "value"

        xml = bag.to_xml(pretty=True)
        assert "\n" in xml

    def test_xml_self_closed_tags(self):
        """to_xml self_closed_tags parameter controls empty element format."""
        bag = Bag()
        bag["empty"] = Bag()

        # Default: self-closing
        xml_default = bag.to_xml()
        assert "<empty/>" in xml_default

        # Explicit empty list: open/close
        xml_no_self_close = bag.to_xml(self_closed_tags=[])
        assert "<empty></empty>" in xml_no_self_close

    def test_xml_file_output(self, tmp_path):
        """to_xml writes to file."""
        bag = Bag()
        bag["test"] = "data"

        filepath = tmp_path / "output.xml"
        result = bag.to_xml(filename=str(filepath))

        assert result is None
        assert filepath.exists()

    def test_xml_special_chars_roundtrip(self):
        """XML roundtrip preserves special characters."""
        original = Bag()
        original["text"] = "<script>&test</script>"

        xml = original.to_xml()
        # from_xml wraps in root, so we check the restored value
        restored = Bag.from_xml(f"<root>{xml}</root>")

        assert restored["root.text"] == "<script>&test</script>"

    def test_xml_sanitizes_invalid_tag_names(self):
        """to_xml sanitizes invalid XML tag names."""
        bag = Bag()
        bag["tag with spaces"] = "value"
        bag["123numeric"] = "value2"

        xml = bag.to_xml()
        # Invalid chars replaced, original stored in _tag attribute
        assert "tag_with_spaces" in xml
        assert "_123numeric" in xml


class TestBagParsingCoverage:
    """Tests for parsing various input formats."""

    # ==================== XML Parsing ====================

    def test_from_xml_basic(self):
        """from_xml parses basic XML."""
        xml = "<root><name>test</name></root>"
        bag = Bag.from_xml(xml)
        assert bag["root.name"] == "test"

    def test_from_xml_bytes(self):
        """from_xml accepts bytes input."""
        xml = b"<root><value>text</value></root>"
        bag = Bag.from_xml(xml)
        assert bag["root.value"] == "text"

    def test_from_xml_legacy_genrobag_wrapper(self):
        """from_xml unwraps GenRoBag root element."""
        xml = "<GenRoBag><item>value</item></GenRoBag>"
        bag = Bag.from_xml(xml)
        assert bag["item"] == "value"

    def test_from_xml_legacy_type_long(self):
        """from_xml decodes _T="L" as integer."""
        xml = '<GenRoBag><count _T="L">42</count></GenRoBag>'
        bag = Bag.from_xml(xml)
        assert bag["count"] == 42
        assert isinstance(bag["count"], int)

    def test_from_xml_legacy_type_float(self):
        """from_xml decodes _T="R" as float."""
        xml = '<GenRoBag><value _T="R">3.14</value></GenRoBag>'
        bag = Bag.from_xml(xml)
        assert bag["value"] == 3.14

    def test_from_xml_legacy_type_bag(self):
        """from_xml with nested bag structure."""
        xml = "<GenRoBag><parent><child>value</child></parent></GenRoBag>"
        bag = Bag.from_xml(xml)
        assert isinstance(bag["parent"], Bag)
        assert bag["parent.child"] == "value"

    def test_from_xml_duplicate_tags(self):
        """from_xml handles duplicate tags with suffixes."""
        xml = "<root><item>a</item><item>b</item><item>c</item></root>"
        bag = Bag.from_xml(xml)
        assert bag["root.item"] == "a"
        assert bag["root.item_1"] == "b"
        assert bag["root.item_2"] == "c"

    def test_from_xml_with_attributes(self):
        """from_xml preserves and decodes attributes."""
        xml = '<root><item id="123::L">value</item></root>'
        bag = Bag.from_xml(xml)
        node = bag.get_node("root.item")
        # TYTX decodes 123::L to int
        assert node.attr.get("id") == 123

    def test_from_xml_empty_with_factory(self):
        """from_xml uses empty factory for empty elements."""
        xml = "<root><empty></empty></root>"
        bag = Bag.from_xml(xml, empty=lambda: "DEFAULT")
        assert bag["root.empty"] == "DEFAULT"

    def test_from_xml_mixed_content(self):
        """from_xml handles mixed content (text + children)."""
        xml = "<root>text before<child>child value</child></root>"
        bag = Bag.from_xml(xml)
        assert bag["root._"] == "text before"
        assert bag["root.child"] == "child value"

    def test_from_xml_whitespace_preserved(self):
        """from_xml preserves inner whitespace in content."""
        xml = "<root><item>  value  </item></root>"
        bag = Bag.from_xml(xml)
        assert bag["root.item"] == "  value  "

    def test_from_xml_special_chars_unescaped(self):
        """from_xml unescapes XML entities."""
        xml = "<root><text>&lt;script&gt;&amp;test&lt;/script&gt;</text></root>"
        bag = Bag.from_xml(xml)
        assert bag["root.text"] == "<script>&test</script>"

    def test_from_xml_with_tag_attribute(self):
        """from_xml uses _tag attribute as label."""
        xml = '<root><_item _tag="real-name">value</_item></root>'
        bag = Bag.from_xml(xml)
        assert bag["root.real-name"] == "value"

    # ==================== JSON Parsing ====================

    def test_from_json_string(self):
        """from_json parses JSON string."""
        json_str = '{"name": "test", "count": 42}'
        bag = Bag.from_json(json_str)
        assert bag["name"] == "test"
        assert bag["count"] == 42

    def test_from_json_dict(self):
        """from_json accepts dict directly."""
        data = {"name": "test", "value": 123}
        bag = Bag.from_json(data)
        assert bag["name"] == "test"
        assert bag["value"] == 123

    def test_from_json_list_with_labels(self):
        """from_json accepts list with label/value format."""
        data = [{"label": "a", "value": 1}, {"label": "b", "value": 2}]
        bag = Bag.from_json(data)
        assert bag["a"] == 1
        assert bag["b"] == 2

    def test_from_json_nested(self):
        """from_json with nested dict."""
        data = {"parent": {"child": "value"}}
        bag = Bag.from_json(data)
        assert isinstance(bag["parent"], Bag)
        assert bag["parent.child"] == "value"

    def test_from_json_list_joiner(self):
        """from_json with list_joiner joins string lists."""
        data = {"tags": ["a", "b", "c"]}
        bag = Bag.from_json(data, list_joiner=",")
        assert bag["tags"] == "a,b,c"

    def test_from_json_generic_list(self):
        """from_json converts generic list to Bag with prefix."""
        data = {"items": [1, 2, 3]}
        bag = Bag.from_json(data)
        assert bag["items.items_0"] == 1
        assert bag["items.items_1"] == 2
        assert bag["items.items_2"] == 3

    def test_from_json_empty_dict(self):
        """from_json with empty dict returns empty Bag."""
        bag = Bag.from_json({})
        assert len(bag) == 0

    def test_from_json_empty_list(self):
        """from_json with empty list returns empty Bag."""
        bag = Bag.from_json([])
        assert len(bag) == 0

    def test_from_json_scalar_wrapped(self):
        """from_json wraps scalar in dict."""
        bag = Bag.from_json('"simple string"')
        assert bag["value"] == "simple string"

    def test_from_json_with_attr(self):
        """from_json with node format including attr."""
        data = [{"label": "item", "value": "test", "attr": {"id": 123}}]
        bag = Bag.from_json(data)
        assert bag.get_node("item").attr.get("id") == 123


class TestSerializationEdgeCases:
    """Tests for edge cases in serialization/parsing to achieve full coverage."""

    # ==================== bag_parse.py edge cases ====================

    def test_from_xml_with_gnr_env_var(self, monkeypatch):
        """from_xml substitutes GNR_* environment variables."""
        monkeypatch.setenv("GNR_TEST_VALUE", "replaced")
        xml = "<root><item>{GNR_TEST_VALUE}</item></root>"
        bag = Bag.from_xml(xml)
        assert bag["root.item"] == "replaced"

    def test_from_xml_empty_result_returns_empty_bag(self):
        """from_xml with content that produces None returns empty Bag."""
        # XML con solo whitespace nel contenuto
        xml = "<root></root>"
        bag = Bag.from_xml(xml)
        assert isinstance(bag["root"], Bag) or bag["root"] == ""

    def test_from_xml_trailing_newline_stripped(self):
        """from_xml strips trailing newlines from content."""
        xml = "<root><item>value\n</item></root>"
        bag = Bag.from_xml(xml)
        assert bag["root.item"] == "value"

    def test_from_xml_legacy_invalid_value_for_int_type(self):
        """from_xml with valid int type but invalid value produces error marker."""
        # _T="L" is long/int type, "not-a-number" is invalid for int
        xml = '<GenRoBag><item _T="L">not-a-number</item></GenRoBag>'
        bag = Bag.from_xml(xml)
        # Invalid value for valid type produces error marker
        assert "**INVALID" in str(bag["item"])

    def test_from_xml_legacy_invalid_value_for_date_type(self):
        """from_xml with valid date type but invalid value produces error marker."""
        # _T="D" is date type, "not-a-date" is invalid for date
        xml = '<GenRoBag><item _T="D">not-a-date</item></GenRoBag>'
        bag = Bag.from_xml(xml)
        # Invalid value for valid type produces error marker
        assert "**INVALID" in str(bag["item"])

    def test_from_xml_element_with_children_and_text(self):
        """from_xml element with both text content and child elements."""
        xml = "<root><parent>text content<child>child value</child></parent></root>"
        bag = Bag.from_xml(xml)
        # Text goes to '_' key, child to its own key
        assert bag["root.parent._"] == "text content"
        assert bag["root.parent.child"] == "child value"

    def test_from_xml_value_is_zero(self):
        """from_xml preserves zero as value (not treated as empty)."""
        xml = '<GenRoBag><count _T="L">0</count></GenRoBag>'
        bag = Bag.from_xml(xml)
        assert bag["count"] == 0

    def test_from_tytx_none_value_roundtrip(self):
        """from_tytx correctly handles ::NN marker for None."""
        original = Bag()
        original.set_item("null_item", None)

        tytx = original.to_tytx()
        restored = Bag.from_tytx(tytx)

        assert restored["null_item"] is None

    # ==================== bag_serialize.py edge cases ====================

    def test_to_xml_pretty_multiple_roots(self):
        """to_xml pretty print with multiple root elements."""
        bag = Bag()
        bag["first"] = "a"
        bag["second"] = "b"

        xml = bag.to_xml(pretty=True)
        # Should work despite multiple roots (uses wrapper internally)
        assert "first" in xml
        assert "second" in xml
        assert "\n" in xml

    def test_to_xml_attribute_with_none_value(self):
        """to_xml skips attributes with None value."""
        bag = Bag()
        bag.set_item("item", "value", _attributes={"keep": "yes", "skip": None})

        xml = bag.to_xml()
        assert 'keep="yes"' in xml
        assert "skip" not in xml

    def test_to_xml_empty_tag_name(self):
        """to_xml handles empty string as tag name."""
        bag = Bag()
        bag[""] = "value"

        xml = bag.to_xml()
        # Empty tag becomes _none_
        assert "_none_" in xml

    def test_to_xml_tag_with_colon_unknown_namespace(self):
        """to_xml with colon in tag but unknown namespace."""
        bag = Bag()
        bag["unknown:tag"] = "value"

        xml = bag.to_xml()
        # Unknown namespace prefix gets sanitized
        assert "unknown_tag" in xml

    def test_to_xml_tag_with_colon_known_namespace(self):
        """to_xml preserves tag with known namespace prefix."""
        bag = Bag()
        bag.set_item("root", Bag(), _attributes={"xmlns:ns": "http://example.com"})
        bag["root"]["ns:item"] = "value"

        xml = bag.to_xml()
        assert "<ns:item>" in xml

    def test_to_xml_empty_string_value(self):
        """to_xml with empty string value."""
        bag = Bag()
        bag.set_item("empty", "")

        xml = bag.to_xml()
        assert "<empty/>" in xml

    def test_to_xml_empty_string_no_self_close(self):
        """to_xml with empty string and self_closed_tags=[]."""
        bag = Bag()
        bag.set_item("empty", "")

        xml = bag.to_xml(self_closed_tags=[])
        assert "<empty></empty>" in xml

    def test_to_xml_none_in_specific_self_closed_list(self):
        """to_xml with None and tag in self_closed_tags list."""
        bag = Bag()
        bag.set_item("br", None)
        bag.set_item("div", None)

        xml = bag.to_xml(self_closed_tags=["br"])
        assert "<br/>" in xml
        assert "<div></div>" in xml

    def test_to_xml_nested_empty_bag_in_self_closed_list(self):
        """to_xml with empty nested Bag and tag in self_closed_tags."""
        bag = Bag()
        bag["meta"] = Bag()
        bag["section"] = Bag()

        xml = bag.to_xml(self_closed_tags=["meta"])
        assert "<meta/>" in xml
        assert "<section></section>" in xml

    def test_to_tytx_file_removes_js_suffix(self, tmp_path):
        """to_tytx removes ::JS suffix when writing to file."""
        bag = Bag()
        bag["test"] = "data"

        filepath = tmp_path / "output"
        bag.to_tytx(filename=str(filepath))

        content = (tmp_path / "output.bag.json").read_text()
        # File content should not end with ::JS
        assert not content.endswith("::JS")

    def test_to_xml_extract_namespaces_empty_attrs(self):
        """to_xml with node without attributes (namespace extraction)."""
        bag = Bag()
        bag["item"] = "value"  # No attributes

        xml = bag.to_xml()
        assert "<item>value</item>" in xml

    def test_to_xml_file_with_encoding(self, tmp_path):
        """to_xml writes file with specified encoding."""
        bag = Bag()
        bag["text"] = "àèìòù"  # Non-ASCII chars

        filepath = tmp_path / "output.xml"
        bag.to_xml(filename=str(filepath), encoding="UTF-8")

        content = filepath.read_bytes()
        assert "àèìòù".encode() in content

    def test_from_xml_legacy_invalid_value_raises_with_flag(self):
        """from_xml raises exception with raise_on_error=True for invalid values."""
        xml = '<GenRoBag><item _T="L">not-a-number</item></GenRoBag>'
        with pytest.raises(ValueError):
            Bag.from_xml(xml, raise_on_error=True)

    def test_from_xml_legacy_empty_invalid_value_raises_with_flag(self):
        """from_xml raises for empty element with valid type that fails decoding."""
        # Empty value with date type - tytx_decode('::D') should fail
        xml = '<GenRoBag><item _T="D"></item></GenRoBag>'
        with pytest.raises(Exception):
            Bag.from_xml(xml, raise_on_error=True)

    def test_from_tytx_msgpack_transport(self):
        """from_tytx with msgpack transport."""
        pytest.importorskip("msgpack")
        original = Bag()
        original["test"] = "value"
        original["number"] = 42

        msgpack_data = original.to_tytx(transport="msgpack")
        restored = Bag.from_tytx(msgpack_data, transport="msgpack")

        assert restored["test"] == "value"
        assert restored["number"] == 42

    def test_from_tytx_with_tag_roundtrip(self):
        """from_tytx correctly restores node tags."""
        original = Bag()
        original["item"] = "value"
        original.get_node("item").tag = "custom_tag"

        restored = Bag.from_tytx(original.to_tytx())
        assert restored.get_node("item").tag == "custom_tag"


class TestBagCoverageEdgeCases:
    """Tests for edge cases to improve coverage."""

    def test_fill_from_xml_file(self, tmp_path):
        """fill_from with format='xml' loads XML file."""
        xml_content = "<root><item>value</item><number>42</number></root>"
        xml_file = tmp_path / "data.xml"
        xml_file.write_text(xml_content)

        bag = Bag()
        bag.fill_from(str(xml_file), format="xml")

        assert bag["root.item"] == "value"
        assert bag["root.number"] == "42"

    def test_pop_node_nonexistent_path(self):
        """pop_node on nonexistent path returns None."""
        bag = Bag()
        bag["existing"] = "value"

        result = bag.pop_node("nonexistent.path")

        assert result is None

    def test_pop_node_partial_path(self):
        """pop_node on partial path (parent exists, child doesn't) returns None."""
        bag = Bag()
        bag["parent.child"] = "value"

        result = bag.pop_node("parent.nonexistent")

        assert result is None

    def test_htraverse_parent_beyond_root(self):
        """Traversing #parent beyond root returns None."""
        bag = Bag()
        bag.set_backref()
        bag["child"] = "value"

        # Try to go up when there's no parent (bag is root)
        result = bag.get_item("#parent.something", static=True)

        assert result is None

    def test_htraverse_empty_path_after_parent(self):
        """Empty path after #parent navigation returns the parent bag."""
        parent = Bag()
        parent.set_backref()
        parent["child"] = Bag()
        child = parent["child"]
        child["data"] = "value"

        # get_item("#parent") navigates to parent with empty remaining path
        # This covers line 520: if not pathlist: return curr, ""
        result = child.get_item("#parent", static=True)

        assert result is parent

    def test_node_compiled_property(self):
        """node.compiled returns a dict for storing compilation data."""
        bag = Bag()
        bag["item"] = "value"
        node = bag.get_node("item")

        # First access creates empty dict
        compiled = node.compiled
        assert compiled == {}
        assert isinstance(compiled, dict)

        # Can store data
        node.compiled["obj"] = "some_widget"
        node.compiled["class"] = "MyClass"

        # Data persists
        assert node.compiled["obj"] == "some_widget"
        assert node.compiled["class"] == "MyClass"

        # Same dict instance returned
        assert node.compiled is compiled
