"""Spec test: Bag - basic operations (no resolver, no subscribe).

## Design principle: dependency scale

Tests are ordered from simplest to most complex. Each level uses ONLY the
methods validated in previous levels. The file order is the contract.

Scale:
    1.  Bag()                          empty construction (only: doesn't raise)
    2.  Bag(dict) + bag.get(label)     co-validated as duals
    3.  bag.get_item(path)             dotted path + default
    4.  bag[path]                      syntactic sugar for get_item
    5.  bag.set_item + bag.__setitem__ validated with get_item/get_attr
    6.  bag.get_node / bag.node        validated with public node methods
    7.  dunder protocols               __len__, __iter__, __contains__, __call__
    8.  set_item ordering              uses __iter__ to observe order
    9.  pop / __delitem__ / pop_node   use set + get + __contains__
    10. clear                          uses set + __len__
    11. equality __eq__ / __ne__       uses construction + set
    12. root properties                parent, root, fullpath, attributes, backref
    13. set_attr / get_attr / del_attr / setdefault / as_dict
    14. set_item + resolver guard      uses set_callback_item as primitive

## Rule for returned BagNode

When set_item or get_node return a BagNode:
- check the type FIRST (isinstance(..., BagNode))
- then read properties via public node API (label, value, attr,
  get_attr, has_attr, is_branch, position, ...).
- never touch private attributes.
"""

from __future__ import annotations

import pytest

from genro_bag import Bag, BagException, BagNode, BagNodeException

# =============================================================================
# 1. Empty construction
# =============================================================================


class TestBagConstruct:
    def test_empty_bag_does_not_raise(self):
        """Bag() constructs an instance without raising."""
        Bag()

    def test_bag_from_none_does_not_raise(self):
        """Bag(None) is equivalent to Bag() and doesn't raise."""
        Bag(None)


# =============================================================================
# 2. Bag(dict) + get (co-validated)
# =============================================================================


class TestBagFromDictAndGet:
    def test_get_reads_value_initialized_from_dict(self):
        """Bag({'a': 1}).get('a') == 1: construction and dual reading."""
        bag = Bag({"a": 1})
        assert bag.get("a") == 1

    def test_get_missing_returns_none_by_default(self):
        """get('missing') returns None if label doesn't exist."""
        bag = Bag({"a": 1})
        assert bag.get("missing") is None

    def test_get_missing_returns_default(self):
        """get(label, default) returns default if label doesn't exist."""
        bag = Bag({"a": 1})
        assert bag.get("missing", "fallback") == "fallback"

    def test_get_empty_label_returns_self(self):
        """get('') returns the Bag itself (documented convention)."""
        bag = Bag({"a": 1})
        assert bag.get("") is bag

    def test_get_sharp_parent_returns_none_for_root(self):
        """get('#parent') on root returns None."""
        bag = Bag({"a": 1})
        assert bag.get("#parent") is None

    def test_from_empty_dict_does_not_raise(self):
        """Bag({}) is equivalent to Bag() and get on any label returns None."""
        bag = Bag({})
        assert bag.get("anything") is None

    def test_multiple_keys_from_dict_all_readable(self):
        """Bag({'a':1,'b':2}).get(...) reads every initial key."""
        bag = Bag({"a": 1, "b": 2, "c": 3})
        assert bag.get("a") == 1
        assert bag.get("b") == 2
        assert bag.get("c") == 3


# =============================================================================
# 3. get_item (dotted path)
# =============================================================================


class TestGetItem:
    def test_single_level_path_matches_get(self):
        """get_item('a') on Bag({'a': 1}) == bag.get('a')."""
        bag = Bag({"a": 1})
        assert bag.get_item("a") == 1

    def test_missing_path_returns_none(self):
        """get_item on nonexistent path returns None."""
        bag = Bag({"a": 1})
        assert bag.get_item("missing") is None

    def test_missing_path_returns_default(self):
        """get_item(path, default=X) returns X if path doesn't exist."""
        bag = Bag({"a": 1})
        assert bag.get_item("missing", default="fallback") == "fallback"

    def test_empty_path_returns_self(self):
        """get_item('') returns the Bag itself."""
        bag = Bag({"a": 1})
        assert bag.get_item("") is bag


# =============================================================================
# 4. __getitem__ (bracket syntax)
# =============================================================================


class TestBracketGet:
    def test_bracket_equivalent_to_get_item(self):
        """bag['a'] delegates to get_item('a')."""
        bag = Bag({"a": 1})
        assert bag["a"] == bag.get_item("a")


# =============================================================================
# 5. set_item (+ __setitem__) - validated with get_item / get_attr
# =============================================================================


class TestSetItem:
    def test_simple_label(self):
        """bag['a'] = 1; get_item('a') == 1."""
        bag = Bag()
        bag["a"] = 1
        assert bag.get_item("a") == 1

    def test_set_item_method_equivalent_to_bracket(self):
        """set_item('a', 1) is equivalent to bag['a'] = 1."""
        bag = Bag()
        bag.set_item("a", 1)
        assert bag.get_item("a") == 1

    def test_dotted_path(self):
        """set_item('a.b.c', 42); get_item dual on same path."""
        bag = Bag()
        bag.set_item("a.b.c", 42)
        assert bag.get_item("a.b.c") == 42

    def test_overwrite_value(self):
        """Assigning twice updates the value."""
        bag = Bag()
        bag["x"] = 1
        bag["x"] = 2
        assert bag.get_item("x") == 2

    def test_attributes_via_underscore_param(self):
        """_attributes={...} set on node, readable via get_attr."""
        bag = Bag()
        bag.set_item("a.b", "hello", _attributes={"type": "greeting", "lang": "it"})
        assert bag.get_attr("a.b", "type") == "greeting"
        assert bag.get_attr("a.b", "lang") == "it"

    def test_kwargs_merged_into_attributes(self):
        """Extra kwargs become node attributes."""
        bag = Bag()
        bag.set_item("x", 1, type="int", size=4)
        assert bag.get_attr("x", "type") == "int"
        assert bag.get_attr("x", "size") == 4

    def test_kwargs_override_explicit_attributes(self):
        """kwargs override _attributes."""
        bag = Bag()
        bag.set_item("x", 1, _attributes={"type": "old"}, type="new")
        assert bag.get_attr("x", "type") == "new"

    def test_query_syntax_sets_single_attribute(self):
        """set_item('x?attr', v) writes only the attribute, value stays."""
        bag = Bag()
        bag["x"] = 10
        bag.set_item("x?myattr", "attr_value")
        assert bag.get_attr("x", "myattr") == "attr_value"
        assert bag.get_item("x") == 10

    def test_query_syntax_sets_multiple_attributes(self):
        """set_item('x?a&b&c', (1,2,3)) sets multiple attributes."""
        bag = Bag()
        bag["x"] = 0
        bag.set_item("x?a&b&c", (1, 2, 3))
        assert bag.get_attr("x", "a") == 1
        assert bag.get_attr("x", "b") == 2
        assert bag.get_attr("x", "c") == 3

    def test_fired_resets_value_to_none(self):
        """set_item(v, _fired=True): after set, get_item is None."""
        bag = Bag()
        bag.set_item("event", "click", _fired=True)
        assert bag.get_item("event") is None

    def test_returns_bagnode_instance(self):
        """set_item returns a BagNode (type only verified here)."""
        bag = Bag()
        result = bag.set_item("a", 42)
        assert isinstance(result, BagNode)

    def test_returned_node_exposes_label_via_public_api(self):
        """The returned BagNode has label equal to final path segment."""
        bag = Bag()
        node = bag.set_item("a.b.c", 42)
        assert isinstance(node, BagNode)
        assert node.label == "c"

    def test_returned_node_exposes_value_via_public_api(self):
        """The returned BagNode has value equal to assigned value."""
        bag = Bag()
        node = bag.set_item("a", 42)
        assert isinstance(node, BagNode)
        assert node.value == 42

    def test_returned_node_exposes_attr_via_public_api(self):
        """The returned BagNode has attr equal to passed dict."""
        bag = Bag()
        node = bag.set_item("a", 1, _attributes={"k": "v"})
        assert isinstance(node, BagNode)
        assert node.attr == {"k": "v"}

    def test_returned_node_exposes_node_tag_via_public_api(self):
        """node_tag becomes a public property of the node."""
        bag = Bag()
        node = bag.set_item("doc", "hello", node_tag="paragraph")
        assert isinstance(node, BagNode)
        assert node.node_tag == "paragraph"


# =============================================================================
# 6. get_node / node - validated with public BagNode API
# =============================================================================


class TestGetNode:
    def test_get_node_returns_bagnode_instance(self):
        """get_node('a') returns a BagNode if path exists."""
        bag = Bag()
        bag["a"] = 42
        result = bag.get_node("a")
        assert isinstance(result, BagNode)

    def test_get_node_missing_returns_none(self):
        """get_node on nonexistent path returns None."""
        bag = Bag()
        assert bag.get_node("missing") is None

    def test_get_node_exposes_value_attr_label(self):
        """The public properties of returned node are consistent."""
        bag = Bag()
        bag.set_item("a", 42, _attributes={"type": "int"})
        node = bag.get_node("a")
        assert isinstance(node, BagNode)
        assert node.label == "a"
        assert node.value == 42
        assert node.attr == {"type": "int"}

    def test_get_node_autocreate_creates_missing(self):
        """autocreate=True creates the node if missing."""
        bag = Bag()
        node = bag.get_node("new", autocreate=True)
        assert isinstance(node, BagNode)
        assert node.label == "new"
        # readable via get_item
        assert bag.get_item("new") is None

    def test_get_node_none_path_returns_parent_node(self):
        """get_node(None) on root returns None (no parent)."""
        bag = Bag()
        assert bag.get_node(None) is None

    def test_get_node_as_tuple_returns_container_and_node(self):
        """as_tuple=True returns (Bag, BagNode)."""
        bag = Bag()
        bag["a.b"] = 1
        result = bag.get_node("a.b", as_tuple=True)
        assert isinstance(result, tuple)
        container, node = result
        assert isinstance(container, Bag)
        assert isinstance(node, BagNode)
        assert node.label == "b"
        assert node.value == 1

    def test_node_first_level_by_label(self):
        """bag.node('a') quick access to direct child."""
        bag = Bag({"a": 1, "b": 2})
        n = bag.node("a")
        assert isinstance(n, BagNode)
        assert n.label == "a"
        assert n.value == 1

    def test_node_first_level_by_index(self):
        """bag.node(0) access by index."""
        bag = Bag({"a": 1, "b": 2})
        n = bag.node(0)
        assert isinstance(n, BagNode)
        assert n.label == "a"

    def test_set_item_return_matches_get_node(self):
        """set_item('a', v) and get_node('a') return the same node."""
        bag = Bag()
        set_ret = bag.set_item("a", 42)
        got = bag.get_node("a")
        assert set_ret is got


# =============================================================================
# 7. Dunder: __len__, __iter__, __contains__, __call__
# =============================================================================


class TestDunderProtocols:
    def test_len_empty_bag(self):
        """len(Bag()) == 0."""
        assert len(Bag()) == 0

    def test_len_counts_first_level_children(self):
        """len counts only direct children; dotted paths count first level."""
        bag = Bag()
        bag["a"] = 1
        bag["b.c"] = 2
        assert len(bag) == 2

    def test_len_from_dict(self):
        """Bag({...}) has len equal to number of dict keys."""
        assert len(Bag({"a": 1, "b": 2, "c": 3})) == 3

    def test_overwrite_does_not_increase_len(self):
        """Overwriting an existing path doesn't change len."""
        bag = Bag()
        bag["x"] = 1
        bag["x"] = 2
        assert len(bag) == 1

    def test_contains_existing_path(self):
        """'a.b' in bag is True after set_item('a.b')."""
        bag = Bag()
        bag["a.b"] = 1
        assert "a.b" in bag

    def test_contains_missing_path(self):
        """path never set -> not in bag."""
        bag = Bag()
        bag["a.b"] = 1
        assert "a.c" not in bag

    def test_contains_non_string_is_false(self):
        """in with unsupported types returns False."""
        bag = Bag({"a": 1})
        assert (123 in bag) is False  # type: ignore[operator]

    def test_iter_yields_bagnode_instances(self):
        """iter(bag) yields BagNode, not values."""
        bag = Bag({"a": 1, "b": 2})
        items = list(bag)
        assert all(isinstance(n, BagNode) for n in items)

    def test_iter_preserves_insertion_order_from_dict(self):
        """Iteration respects insertion order from initial dict."""
        bag = Bag({"a": 1, "b": 2, "c": 3})
        assert [n.label for n in bag] == ["a", "b", "c"]

    def test_call_no_args_returns_keys_list(self):
        """bag() without arguments returns list of first-level keys."""
        bag = Bag({"a": 1, "b": 2})
        assert bag() == ["a", "b"]

    def test_call_with_path_returns_value(self):
        """bag(path) is equivalent to bag[path]."""
        bag = Bag()
        bag["a.b"] = 42
        assert bag("a.b") == 42


# =============================================================================
# 8. set_item ordering (uses __iter__ validated above)
# =============================================================================


class TestSetItemOrdering:
    def test_sequential_set_appends(self):
        """Sequential set_item appends to end (default)."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag["c"] = 3
        assert [n.label for n in bag] == ["a", "b", "c"]

    def test_node_position_lt_prepends(self):
        """node_position='<' prepends to beginning."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag.set_item("c", 3, node_position="<")
        assert [n.label for n in bag] == ["c", "a", "b"]

    def test_node_position_before_label(self):
        """node_position='<b' inserts before label 'b'."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag.set_item("x", 99, node_position="<b")
        assert [n.label for n in bag] == ["a", "x", "b"]

    def test_node_position_after_label(self):
        """node_position='>a' inserts after label 'a'."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag.set_item("x", 99, node_position=">a")
        assert [n.label for n in bag] == ["a", "x", "b"]


# =============================================================================
# 9. pop / __delitem__ / pop_node
# =============================================================================


class TestPop:
    def test_pop_removes_and_returns_value(self):
        """pop('a.b') removes node and returns its value."""
        bag = Bag()
        bag["a.b"] = 42
        assert bag.pop("a.b") == 42
        assert "a.b" not in bag

    def test_pop_missing_returns_default(self):
        """pop on nonexistent path returns default."""
        bag = Bag()
        assert bag.pop("missing", "gone") == "gone"

    def test_del_item_is_alias_for_pop(self):
        """del bag[path] removes the node."""
        bag = Bag()
        bag["a"] = 1
        del bag["a"]
        assert "a" not in bag

    def test_pop_node_returns_bagnode_instance(self):
        """pop_node returns a BagNode."""
        bag = Bag()
        bag.set_item("a", 42, _attributes={"type": "int"})
        node = bag.pop_node("a")
        assert isinstance(node, BagNode)
        assert node.label == "a"
        assert node.value == 42
        assert node.attr == {"type": "int"}

    def test_pop_node_missing_returns_none(self):
        """pop_node on nonexistent path returns None."""
        bag = Bag()
        assert bag.pop_node("missing") is None


# =============================================================================
# 10. clear (uses set + __len__)
# =============================================================================


class TestClear:
    def test_clear_empties_bag(self):
        """clear() sets len to 0."""
        bag = Bag({"a": 1, "b": 2})
        bag.clear()
        assert len(bag) == 0

    def test_clear_on_empty_is_noop(self):
        """clear() on empty Bag doesn't raise."""
        bag = Bag()
        bag.clear()
        assert len(bag) == 0

    def test_clear_on_nested_bag_notifies_parent_by_default(self):
        """clear() on nested Bag (backref) notifies parent with upd_value.

        Scenario: subscriber on parent receives event with oldvalue = orphan
        Bag containing removed nodes.
        """
        root = Bag()
        root.set_item("inner.a", 1)
        root.set_item("inner.b", 2)
        received = []
        root.subscribe("watch", update=lambda **kw: received.append(kw))
        inner = root.get_item("inner")
        assert isinstance(inner, Bag)
        inner.clear()
        # parent received upd_value for 'inner' node
        assert any(kw.get("evt") == "upd_value" for kw in received)
        # oldvalue is orphan Bag containing removed nodes
        upd = next(kw for kw in received if kw.get("evt") == "upd_value")
        oldvalue = upd.get("oldvalue")
        assert isinstance(oldvalue, Bag)
        assert oldvalue.keys() == ["a", "b"]

    def test_clear_with_trigger_false_skips_notification(self):
        """clear(trigger=False) empties in-place without notifying parent."""
        root = Bag()
        root.set_item("inner.a", 1)
        root.set_item("inner.b", 2)
        received = []
        root.subscribe("watch", update=lambda **kw: received.append(kw))
        inner = root.get_item("inner")
        assert isinstance(inner, Bag)
        inner.clear(trigger=False)
        # parent did NOT receive upd_value
        assert not any(kw.get("evt") == "upd_value" for kw in received)
        # but Bag is still empty
        assert len(inner) == 0


# =============================================================================
# 11. __eq__ / __ne__
# =============================================================================


class TestEquality:
    def test_same_content_equal(self):
        """Two Bag constructed from same dict are equal."""
        assert Bag({"x": 1, "y": 2}) == Bag({"x": 1, "y": 2})

    def test_different_values_not_equal(self):
        """Bag with different values are different."""
        assert Bag({"x": 1}) != Bag({"x": 2})

    def test_different_order_not_equal(self):
        """Node order matters for equality."""
        a = Bag()
        a["x"] = 1
        a["y"] = 2
        b = Bag()
        b["y"] = 2
        b["x"] = 1
        assert a != b

    def test_not_equal_to_non_bag(self):
        """Comparison with non-Bag is always False."""
        assert Bag({"a": 1}) != {"a": 1}
        assert Bag({"a": 1}) != "not a bag"
        assert Bag({"a": 1}) != 42

    def test_bagnode_equal_when_same_resolver_identity(self):
        """Two nodes with same label, same attrs and **same resolver** are
        equal.

        Scenario: same resolver instance is shared between two Bag
        (caching pattern). Nodes return True for ==.
        """
        from genro_bag.resolvers import BagCbResolver
        r = BagCbResolver(lambda: 42)
        bag1 = Bag()
        bag1["x"] = r
        bag2 = Bag()
        bag2["x"] = r
        n1 = bag1.get_node("x")
        n2 = bag2.get_node("x")
        assert n1 == n2


# =============================================================================
# 12. Root Bag properties
# =============================================================================


class TestRootProperties:
    def test_root_bag_has_no_parent(self):
        """A non-nested Bag has parent None."""
        assert Bag().parent is None

    def test_root_bag_has_no_parent_node(self):
        """A non-nested Bag has parent_node None."""
        assert Bag().parent_node is None

    def test_root_is_self_for_root_bag(self):
        """The root of a non-nested Bag is itself."""
        bag = Bag()
        assert bag.root is bag

    def test_fullpath_none_without_backref(self):
        """fullpath is None without backref enabled."""
        bag = Bag()
        bag["a.b"] = 1
        inner = bag.get_item("a")
        assert isinstance(inner, Bag)
        assert inner.fullpath is None

    def test_attributes_empty_for_standalone_bag(self):
        """attributes is empty dict for Bag without parent_node."""
        assert Bag().attributes == {}

    def test_root_attributes_default_none(self):
        """root_attributes default is None."""
        assert Bag().root_attributes is None

    def test_root_attributes_setter_stores_copy(self):
        """root_attributes setter stores the dict."""
        bag = Bag()
        bag.root_attributes = {"owner": "test"}
        assert bag.root_attributes == {"owner": "test"}

    def test_backref_default_false(self):
        """backref default is False."""
        assert Bag().backref is False

    def test_get_inherited_attributes_merges_ancestors(self):
        """get_inherited_attributes on node returns ancestor attributes.

        Scenario: an internal node has attributes, its leaf child inherits them
        in merge with its own. Useful for role/theme/permission propagation.
        """
        root = Bag()
        root.set_item("outer", Bag(), _attributes={"role": "admin", "theme": "dark"})
        inner = root.get_item("outer")
        assert isinstance(inner, Bag)
        inner.set_item("leaf", 42, _attributes={"local": "x"})
        root.set_backref()
        leaf = inner.get_node("leaf")
        inherited = leaf.get_inherited_attributes()
        # attributes propagated from parent are present
        assert inherited.get("role") == "admin"
        assert inherited.get("theme") == "dark"


# =============================================================================
# 13. set_attr / get_attr / del_attr / setdefault / as_dict
# =============================================================================


class TestAttrAccessors:
    def test_set_attr_on_existing_node(self):
        """set_attr adds attributes to an existing node."""
        bag = Bag()
        bag["a"] = 1
        bag.set_attr("a", type="int")
        assert bag.get_attr("a", "type") == "int"

    def test_get_attr_default_for_missing(self):
        """get_attr with default for missing attribute."""
        bag = Bag()
        bag["a"] = 1
        assert bag.get_attr("a", "missing", default="x") == "x"

    def test_del_attr_removes(self):
        """del_attr removes the specific attribute."""
        bag = Bag()
        bag.set_item("a", 1, _attributes={"type": "int", "size": 4})
        bag.del_attr("a", "type")
        assert bag.get_attr("a", "type") is None
        assert bag.get_attr("a", "size") == 4

    def test_setdefault_returns_existing(self):
        """setdefault on existing path doesn't overwrite."""
        bag = Bag()
        bag["a"] = 1
        assert bag.setdefault("a", 99) == 1
        assert bag.get_item("a") == 1

    def test_setdefault_creates_if_missing(self):
        """setdefault creates node if absent."""
        bag = Bag()
        assert bag.setdefault("new", 42) == 42
        assert bag.get_item("new") == 42

    def test_as_dict_first_level(self):
        """as_dict returns dict of first level."""
        bag = Bag({"a": 1, "b": 2})
        assert bag.as_dict() == {"a": 1, "b": 2}

    def test_del_attr_comma_separated_string(self):
        """del_attr accepts string with comma-separated labels.

        Common use: remove multiple attributes at once.
        """
        bag = Bag()
        bag.set_item("x", 1, _attributes={"a": 1, "b": 2, "c": 3, "d": 4})
        node = bag.get_node("x")
        node.del_attr("a,c")
        assert dict(node.attr) == {"b": 2, "d": 4}

    def test_del_attr_multiple_args(self):
        """del_attr accepts multiple separate arguments."""
        bag = Bag()
        bag.set_item("x", 1, _attributes={"a": 1, "b": 2, "c": 3})
        node = bag.get_node("x")
        node.del_attr("a", "c")
        assert dict(node.attr) == {"b": 2}


# =============================================================================
# 13a2. node.get_value(_query_string=...) to read attributes
# =============================================================================


class TestGetValueQueryString:
    """get_value(_query_string='...') allows reading node attributes.

    Syntax:
        - 'attrname' → attribute value
        - 'a&b&c' → tuple with multiple values
    """

    def test_query_string_single_attribute(self):
        """get_value(_query_string='color') returns attribute value."""
        bag = Bag()
        bag.set_item("item", "body", _attributes={"color": "red", "size": 42})
        node = bag.get_node("item")
        assert node.get_value(_query_string="color") == "red"

    def test_query_string_multiple_attributes_returns_tuple(self):
        """get_value(_query_string='a&b&c') returns tuple with values in requested order."""
        bag = Bag()
        bag.set_item(
            "item", "body",
            _attributes={"color": "red", "size": 42, "active": True}
        )
        node = bag.get_node("item")
        result = node.get_value(_query_string="color&size&active")
        assert result == ("red", 42, True)

    def test_query_string_missing_attribute_returns_none(self):
        """Missing attribute returns None (single) / None in tuple."""
        bag = Bag()
        bag.set_item("item", "body", _attributes={"color": "red"})
        node = bag.get_node("item")
        assert node.get_value(_query_string="missing") is None


# =============================================================================
# 13b. Lookup by attribute and value (search scenarios)
# =============================================================================


class TestLookupByAttributeAndValue:
    """bag.get_node_by_attr and bag.get_node_by_value for search scenarios
    on ordered collections (lists of records with logical id, tag, type).
    """

    def test_get_node_by_attr_finds_first_match(self):
        """get_node_by_attr(key, value) returns first node with that attribute."""
        bag = Bag()
        bag.set_item("r1", "alice", _attributes={"id": "x", "role": "admin"})
        bag.set_item("r2", "bob", _attributes={"id": "y", "role": "user"})
        bag.set_item("r3", "carol", _attributes={"id": "z", "role": "user"})
        node = bag.get_node_by_attr("id", "y")
        assert node is not None
        assert node.value == "bob"

    def test_get_node_by_attr_non_id_attribute(self):
        """get_node_by_attr works on any attribute, not just 'id'."""
        bag = Bag()
        bag.set_item("r1", "alice", _attributes={"role": "admin"})
        bag.set_item("r2", "bob", _attributes={"role": "user"})
        node = bag.get_node_by_attr("role", "admin")
        assert node is not None
        assert node.value == "alice"

    def test_get_node_by_attr_returns_none_when_missing(self):
        """get_node_by_attr returns None if no node has that attribute/value."""
        bag = Bag()
        bag.set_item("r1", "alice", _attributes={"id": "x"})
        assert bag.get_node_by_attr("id", "missing") is None

    def test_get_node_by_value_finds_dict_match(self):
        """get_node_by_value searches in dict/Bag values for key=value match."""
        bag = Bag()
        bag.set_item("r1", Bag({"name": "alice", "age": 30}))
        bag.set_item("r2", Bag({"name": "bob", "age": 25}))
        node = bag.get_node_by_value("name", "bob")
        assert node is not None
        assert node.value["name"] == "bob"

    def test_get_node_by_value_returns_none_when_missing(self):
        """get_node_by_value returns None if no dict-node satisfies condition."""
        bag = Bag()
        bag.set_item("r1", Bag({"name": "alice"}))
        assert bag.get_node_by_value("name", "nobody") is None

    def test_get_node_sharp_equal_value_shortcut(self):
        """bag.get_node('#=value') returns first node whose value == value."""
        bag = Bag()
        bag.set_item("r1", "alice")
        bag.set_item("r2", "bob")
        node = bag.get_node("#=alice")
        assert node is not None
        assert node.label == "r1"

    def test_get_node_sharp_equal_value_missing_returns_none(self):
        """bag.get_node('#=missing') returns None if no match."""
        bag = Bag()
        bag.set_item("r1", "alice")
        assert bag.get_node("#=nobody") is None

    def test_get_node_sharp_attr_equal_shortcut(self):
        """bag.get_node('#attr=value') returns node with that attribute."""
        bag = Bag()
        bag.set_item("r1", "alice", _attributes={"id": "X"})
        bag.set_item("r2", "bob", _attributes={"id": "Y"})
        node = bag.get_node("#id=Y")
        assert node is not None
        assert node.label == "r2"


# =============================================================================
# 13c. BagNode as value and objects with rootattributes
# =============================================================================


class TestSetValueWithSpecialObjects:
    """set_item with objects that have special semantics:
    - other BagNode (value extraction + attribute merge)
    - objects with 'rootattributes' dict attribute (attribute merge)
    """

    def test_set_item_with_bagnode_extracts_value_and_attrs(self):
        """Passing a BagNode as value, target inherits value + attributes."""
        bag = Bag()
        bag.set_item("src", "hello", _attributes={"type": "greeting", "lang": "en"})
        src_node = bag.get_node("src")
        assert src_node is not None
        bag.set_item("dst", src_node)
        dst_node = bag.get_node("dst")
        assert dst_node is not None
        assert dst_node.value == "hello"
        # source attributes are copied to target
        assert dst_node.attr.get("type") == "greeting"
        assert dst_node.attr.get("lang") == "en"

    def test_set_item_with_rootattributes_object_merges_attrs(self):
        """An object with 'rootattributes' (dict) attribute merges attrs in node.

        Real scenario: domain object that exposes metadata as rootattributes.
        """
        class DomainObject:
            rootattributes = {"version": "1.0", "author": "alice"}

            def __init__(self, payload):
                self.payload = payload

        bag = Bag()
        obj = DomainObject({"data": 42})
        bag.set_item("config", obj)
        node = bag.get_node("config")
        assert node is not None
        # value is the entire object
        assert node.value is obj
        # attributes from rootattributes were copied
        assert node.attr.get("version") == "1.0"
        assert node.attr.get("author") == "alice"


# =============================================================================
# 14. set_item + resolver guard
# =============================================================================


class TestSetItemResolverGuard:
    def test_raises_when_overwriting_resolver_without_param(self):
        """Overwriting node with resolver without resolver= raises BagNodeException."""
        bag = Bag()
        bag.set_callback_item("data", lambda: "computed")
        with pytest.raises(BagNodeException):
            bag.set_item("data", "new")

    def test_resolver_false_removes_resolver(self):
        """resolver=False removes resolver and writes new value."""
        bag = Bag()
        bag.set_callback_item("data", lambda: "computed")
        bag.set_item("data", "new", resolver=False)
        # node no longer has resolver and new value is read
        assert bag.get_item("data") == "new"

    def test_resolver_replace_with_new_resolver(self):
        """set_item(..., resolver=new_r) replaces existing resolver."""
        from genro_bag.resolvers import BagCbResolver
        bag = Bag()
        bag.set_callback_item("data", lambda: "old")
        assert bag.get_item("data") == "old"
        new_r = BagCbResolver(lambda: "fresh")
        bag.set_item("data", None, resolver=new_r)
        assert bag.get_item("data") == "fresh"


# =============================================================================
# 14b. set_item with ?attr syntax: multiple attributes with tuple
# =============================================================================


class TestSetItemAttrSyntax:
    """The 'path?a&b&c' syntax requires tuple of values with consistent length."""

    def test_single_attr_syntax_sets_attribute(self):
        """set_item('path?attr', value) writes a single attribute."""
        bag = Bag()
        bag.set_item("x", 1)
        bag.set_item("x?color", "red")
        assert bag.get_attr("x", "color") == "red"

    def test_multi_attr_syntax_with_tuple(self):
        """set_item('path?a&b', (v1, v2)) distributes values across attributes."""
        bag = Bag()
        bag.set_item("x", 1)
        bag.set_item("x?a&b", (10, 20))
        assert bag.get_attr("x", "a") == 10
        assert bag.get_attr("x", "b") == 20

    def test_multi_attr_syntax_tuple_length_mismatch_raises(self):
        """set_item('path?a&b', tuple of different length) raises BagNodeException."""
        bag = Bag()
        bag.set_item("x", 1)
        with pytest.raises(BagNodeException):
            bag.set_item("x?a&b", (10, 20, 30))


# =============================================================================
# 14c. set_item with node_tag on existing node
# =============================================================================


class TestSetItemNodeTag:
    """node_tag is the 'semantic type' of the node. set_item can update it
    on an already existing node without recreating it.
    """

    def test_set_item_assigns_node_tag_on_create(self):
        """On creation, set_item(node_tag='X') sets the tag."""
        bag = Bag()
        bag.set_item("x", 42, node_tag="special")
        node = bag.get_node("x")
        assert node is not None
        assert node.node_tag == "special"

    def test_set_item_updates_node_tag_on_existing(self):
        """On existing node, set_item(node_tag='new') updates the tag."""
        bag = Bag()
        bag.set_item("x", 42, node_tag="initial")
        bag.set_item("x", 99, node_tag="updated")
        node = bag.get_node("x")
        assert node is not None
        assert node.node_tag == "updated"
        assert node.value == 99


# =============================================================================
# 14d. get_value(_query_string='k=v') kwargs syntax without resolver
# =============================================================================


class TestGetValueKwargsSyntax:
    """Beyond the 'attr&attr' branch that reads attributes, _query_string with
    dict-like 'k=v' syntax tries to pass kwargs to resolver. Without resolver raises.
    """

    def test_kwargs_syntax_without_resolver_raises(self):
        """node.get_value(_query_string='k=v') on node without resolver raises."""
        bag = Bag()
        bag.set_item("x", "plain")
        node = bag.get_node("x")
        assert node is not None
        with pytest.raises(BagNodeException):
            node.get_value(_query_string="k=v")


# =============================================================================
# 14e. set_value change-detection via _attributes
# =============================================================================


class TestSetValueChangeDetection:
    """set_value triggers subscriber even when value doesn't change
    but attributes do: test here verifies that replay with only attribute
    change still notifies parent.
    """

    def test_same_value_with_new_attrs_still_triggers(self):
        """Replay with identical value but different attrs produces upd event."""
        bag = Bag()
        bag.set_item("x", 42, _attributes={"a": 1})
        received = []
        bag.subscribe("w", update=lambda **kw: received.append(kw.get("evt")))
        # same value, new attr
        bag.set_item("x", 42, _attributes={"a": 2})
        # at least one event of type upd_value* (exact name is up to runtime)
        assert any(evt and evt.startswith("upd") for evt in received)


# =============================================================================
# 15. move - node reordering (drag & drop)
# =============================================================================


class TestMove:
    def test_move_single_node_forward(self):
        """move(0, 2) moves first node to position 2."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag["c"] = 3
        bag.move(0, 2)
        assert bag.keys() == ["b", "c", "a"]

    def test_move_single_node_backward(self):
        """move(2, 0) moves last node to beginning."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag["c"] = 3
        bag.move(2, 0)
        assert bag.keys() == ["c", "a", "b"]

    def test_move_list_of_indices(self):
        """move([0, 2], 1) moves multiple nodes preserving relative order."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag["c"] = 3
        bag["d"] = 4
        bag.move([0, 2], 1)
        # moved nodes ('a' and 'c') are inserted around destination
        # key point: unmoved nodes preserve relative order
        result = bag.keys()
        assert set(result) == {"a", "b", "c", "d"}
        # 'b' and 'd' (unmoved) preserve relative order
        assert result.index("b") < result.index("d")

    def test_move_to_same_position_is_noop(self):
        """move(1, 1) doesn't change order."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag["c"] = 3
        bag.move(1, 1)
        assert bag.keys() == ["a", "b", "c"]

    def test_move_with_negative_position_is_noop(self):
        """move with position < 0 doesn't alter Bag."""
        bag = Bag({"a": 1, "b": 2, "c": 3})
        bag.move(0, -1)
        assert bag.keys() == ["a", "b", "c"]

    def test_move_with_position_out_of_range_is_noop(self):
        """move with position >= len doesn't alter Bag."""
        bag = Bag({"a": 1, "b": 2, "c": 3})
        bag.move(0, 99)
        assert bag.keys() == ["a", "b", "c"]

    def test_move_with_empty_indices_list_is_noop(self):
        """move([], pos) doesn't alter Bag."""
        bag = Bag({"a": 1, "b": 2, "c": 3})
        bag.move([], 0)
        assert bag.keys() == ["a", "b", "c"]

    def test_move_multiple_indices_preserves_relative_order(self):
        """move([0, 1], 3) moves two nodes before destination."""
        bag = Bag({"a": 1, "b": 2, "c": 3, "d": 4, "e": 5})
        bag.move([0, 1], 3)
        # 'a' and 'b' are extracted and re-inserted around destination 'd'
        result = bag.keys()
        assert set(result) == {"a", "b", "c", "d", "e"}
        # 'a' and 'b' maintain relative order
        assert result.index("a") < result.index("b")

    def test_move_single_with_source_out_of_range_is_noop(self):
        """move(99, 0) with source index out of range doesn't alter Bag."""
        bag = Bag({"a": 1, "b": 2, "c": 3})
        bag.move(99, 0)
        assert bag.keys() == ["a", "b", "c"]


# =============================================================================
# 16. as_dict - ascii / lower flags
# =============================================================================


class TestAsDictFlags:
    def test_as_dict_lower(self):
        """as_dict(lower=True) returns keys in lowercase."""
        bag = Bag()
        bag["Name"] = "alice"
        bag["AGE"] = 30
        result = bag.as_dict(lower=True)
        assert result == {"name": "alice", "age": 30}

    def test_as_dict_ascii(self):
        """as_dict(ascii=True) forces keys to str (via str())."""
        bag = Bag()
        bag["a"] = 1
        result = bag.as_dict(ascii=True)
        assert result == {"a": 1}


# =============================================================================
# 17. nodes property
# =============================================================================


class TestNodesProperty:
    def test_nodes_returns_list_of_bagnodes(self):
        """bag.nodes is alias for list of first-level BagNode."""
        bag = Bag({"a": 1, "b": 2})
        nodes = bag.nodes
        assert isinstance(nodes, list)
        assert len(nodes) == 2
        assert all(isinstance(n, BagNode) for n in nodes)
        assert [n.label for n in nodes] == ["a", "b"]


# =============================================================================
# 18. __contains__ with a BagNode
# =============================================================================


class TestContainsNode:
    def test_node_in_bag_after_insertion(self):
        """A BagNode obtained via set_item is contained in Bag."""
        bag = Bag()
        node = bag.set_item("x", 1)
        assert node in bag

    def test_node_not_in_bag_after_pop(self):
        """A BagNode extracted with pop_node is no longer contained."""
        bag = Bag()
        bag.set_item("x", 1)
        node = bag.pop_node("x")
        assert isinstance(node, BagNode)
        assert node not in bag


# =============================================================================
# 19. Path navigation: #parent, ../, backslash escape
# =============================================================================


class TestPathNavigation:
    def test_parent_navigation_with_dotdot(self):
        """A path starting with '../' accesses parent of current Bag.

        Requires nested Bag with backref (#parent resolved via parent chain).
        """
        root = Bag()
        root["outer.inner"] = "target"
        root["outer.sibling"] = "neighbor"
        root.subscribe("w", update=lambda **kw: None)  # enable backref
        inner_bag = root.get_item("outer")
        assert isinstance(inner_bag, Bag)
        # from 'outer' container navigate to ../outer.inner
        assert inner_bag.get_item("../outer.inner") == "target"

    def test_parent_navigation_with_sharp_parent(self):
        """'#parent' is equivalent to '../' (resolves to parent)."""
        root = Bag()
        root["outer.inner"] = "target"
        root.subscribe("w", update=lambda **kw: None)
        inner_bag = root.get_item("outer")
        assert isinstance(inner_bag, Bag)
        # #parent returns parent Bag
        assert inner_bag.get("#parent") is root

    def test_backslash_escape_for_literal_dot_in_label(self):
        """A path with '\\.' treats dot as label part, not separator.

        Scenario: labels containing dot (e.g. email, domains, versions).
        """
        bag = Bag()
        # set_item with path 'user\.name' creates ONE node with label 'user.name',
        # not two nested nodes
        bag.set_item("user\\.name", "alice")
        # reading with same escape retrieves value
        assert bag.get_item("user\\.name") == "alice"
        # naive access (without escape) interprets dot
        # as separator: 'user' followed by 'name' doesn't exist
        assert bag.get_item("user.name") is None

    def test_path_as_list_of_segments(self):
        """set_item/get_item accept path as list of segments.

        Use: build path programmatically without needing '.'.join(...).
        """
        bag = Bag()
        bag.set_item(["a", "b", "c"], 42)
        # same hierarchy created: readable with dotted string or list
        assert bag.get_item("a.b.c") == 42
        assert bag.get_item(["a", "b", "c"]) == 42

    def test_sharp_parent_on_root_returns_none(self):
        """'#parent' on Bag without parent returns None (doesn't raise)."""
        root = Bag()
        root["x"] = 1
        # root has no parent: navigating to parent gives None
        assert root.get("#parent") is None

    def test_dotdot_path_on_root_returns_none(self):
        """'../x' on Bag without parent returns None.

        Same semantics as #parent: navigation to nonexistent parent = None.
        """
        root = Bag()
        root["x"] = 1
        assert root.get_item("../x") is None

    def test_write_sharp_index_in_intermediate_path_raises(self):
        """set_item('#n.x', ...) uses '#n' syntax to reference existing node
        in intermediate path. If index doesn't exist, raises BagException
        (we can't create intermediate node 'at index').
        """
        bag = Bag({"a": 1, "b": 2})
        with pytest.raises(BagException):
            bag.set_item("#5.x", 42)

    def test_get_item_descending_into_scalar_returns_none(self):
        """Navigating into scalar value (non-Bag) returns None.

        If 'a' is an int, 'a.b' and 'a.b.c' are unreachable.
        """
        bag = Bag()
        bag["a"] = 42
        assert bag.get_item("a.b") is None
        assert bag.get_item("a.b.c") is None


# =============================================================================
# 20. node_position advanced: int, '#n', '<#n', '>#n', label, errors
# =============================================================================


class TestNodePositionSharpSyntax:
    def test_position_sharp_n_insert_at_index(self):
        """node_position='#2' inserts at index 2."""
        bag = Bag({"a": 1, "b": 2, "c": 3})
        bag.set_item("new", 99, node_position="#1")
        assert bag.keys() == ["a", "new", "b", "c"]

    def test_position_lt_sharp_n_insert_before_index(self):
        """node_position='<#n' inserts before index n."""
        bag = Bag({"a": 1, "b": 2, "c": 3})
        bag.set_item("new", 99, node_position="<#1")
        assert bag.keys() == ["a", "new", "b", "c"]

    def test_position_gt_sharp_n_insert_after_index(self):
        """node_position='>#n' inserts after index n."""
        bag = Bag({"a": 1, "b": 2, "c": 3})
        bag.set_item("new", 99, node_position=">#1")
        assert bag.keys() == ["a", "b", "new", "c"]

    def test_position_int_positive_out_of_range_clamps_to_len(self):
        """node_position=int beyond len is clamped to len (append)."""
        bag = Bag({"a": 1, "b": 2})
        bag.set_item("new", 99, node_position=999)
        assert bag.keys()[-1] == "new"

    def test_position_int_negative_one_inserts_before_last(self):
        """node_position=-1 inserts before last (Python semantics)."""
        bag = Bag({"a": 1, "b": 2, "c": 3})
        bag.set_item("new", 99, node_position=-1)
        assert bag.keys() == ["a", "b", "new", "c"]

    def test_position_int_negative_two_inserts_before_penultimate(self):
        """node_position=-2 inserts before penultimate."""
        bag = Bag({"a": 1, "b": 2, "c": 3})
        bag.set_item("new", 99, node_position=-2)
        assert bag.keys() == ["a", "new", "b", "c"]

    def test_position_int_negative_len_inserts_at_start(self):
        """node_position=-len(bag) is equivalent to prepend (index 0)."""
        bag = Bag({"a": 1, "b": 2, "c": 3})
        bag.set_item("new", 99, node_position=-3)
        assert bag.keys() == ["new", "a", "b", "c"]

    def test_position_int_negative_out_of_range_clamps_to_zero(self):
        """node_position=-999 beyond negative range is clamped to 0 (prepend)."""
        bag = Bag({"a": 1, "b": 2})
        bag.set_item("new", 99, node_position=-999)
        assert bag.keys()[0] == "new"

    def test_position_int_negative_one_on_empty_bag_clamps_to_zero(self):
        """node_position=-1 on empty Bag is clamped to 0."""
        bag = Bag()
        bag.set_item("new", 99, node_position=-1)
        assert bag.keys() == ["new"]

    def test_position_sharp_negative_raises_value_error(self):
        """node_position='#-1' is malformed syntax: ValueError."""
        bag = Bag({"a": 1, "b": 2})
        with pytest.raises(ValueError):
            bag.set_item("new", 99, node_position="#-1")

    def test_position_lt_sharp_negative_raises(self):
        """node_position='<#-2' is malformed syntax: ValueError."""
        bag = Bag({"a": 1, "b": 2})
        with pytest.raises(ValueError):
            bag.set_item("new", 99, node_position="<#-2")

    def test_position_gt_sharp_negative_raises(self):
        """node_position='>#-3' is malformed syntax: ValueError."""
        bag = Bag({"a": 1, "b": 2})
        with pytest.raises(ValueError):
            bag.set_item("new", 99, node_position=">#-3")

    def test_position_sharp_non_integer_raises(self):
        """node_position='#abc' non-integer: ValueError."""
        bag = Bag({"a": 1, "b": 2})
        with pytest.raises(ValueError):
            bag.set_item("new", 99, node_position="#abc")

    def test_position_lt_missing_label_raises(self):
        """node_position='<missing' with nonexistent label: ValueError (no silent fallback)."""
        bag = Bag({"a": 1, "b": 2})
        with pytest.raises(ValueError):
            bag.set_item("new", 99, node_position="<nonexistent")

    def test_position_gt_missing_label_raises(self):
        """node_position='>missing' with nonexistent label: ValueError."""
        bag = Bag({"a": 1, "b": 2})
        with pytest.raises(ValueError):
            bag.set_item("new", 99, node_position=">nonexistent")

    def test_position_unrecognized_string_raises(self):
        """node_position with unknown syntax: ValueError."""
        bag = Bag({"a": 1, "b": 2})
        with pytest.raises(ValueError):
            bag.set_item("new", 99, node_position="@foo")
