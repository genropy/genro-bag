"""Spec test: Bag - query / iteration / aggregation.

Depends on test_basic.py: assumes set_item, get_item, get_attr,
get_node, __len__, __iter__, __contains__ are valid.

## Scale of dependencies in this file

1.  keys()                          simplest primitive
2.  values()
3.  items()
4.  keys/values/items with iter=True (generator)
5.  is_empty()
6.  get_nodes()
7.  get_node_by_attr()
8.  get_node_by_value()
9.  walk() generator mode            uses BagNode.label / .value / dot-separated paths
10. walk() callback mode
11. query()                          variants what/deep/leaf/branch/condition/limit
12. digest()                         query alias + as_columns
13. columns()                        wrapper on digest
14. sum()
15. sort()                           observed via keys()/values() already validated
"""

from __future__ import annotations

import pytest

from genro_bag import Bag, BagNode

# =============================================================================
# 1. keys()
# =============================================================================


class TestKeys:
    def test_empty_bag_returns_empty_list(self):
        """keys() on empty Bag returns empty list."""
        assert Bag().keys() == []

    def test_returns_labels_in_insertion_order(self):
        """keys() returns labels in insertion order."""
        bag = Bag({"a": 1, "b": 2, "c": 3})
        assert bag.keys() == ["a", "b", "c"]

    def test_first_level_only(self):
        """keys() sees only the first level (even with dot-separated paths)."""
        bag = Bag()
        bag["a.b.c"] = 1
        bag["x"] = 2
        assert bag.keys() == ["a", "x"]


# =============================================================================
# 2. values()
# =============================================================================


class TestValues:
    def test_empty_bag_returns_empty_list(self):
        """values() on empty Bag returns empty list."""
        assert Bag().values() == []

    def test_returns_values_in_order(self):
        """values() returns values in insertion order."""
        bag = Bag({"a": 1, "b": 2, "c": 3})
        assert bag.values() == [1, 2, 3]

    def test_nested_bag_value_is_bag_instance(self):
        """If a node has a Bag as value, values() exposes it as such."""
        bag = Bag()
        bag["a.b"] = 1
        vals = bag.values()
        assert len(vals) == 1
        assert isinstance(vals[0], Bag)


# =============================================================================
# 3. items()
# =============================================================================


class TestItems:
    def test_empty_bag_returns_empty_list(self):
        """items() on empty Bag returns empty list."""
        assert Bag().items() == []

    def test_returns_label_value_tuples(self):
        """items() returns (label, value) in order."""
        bag = Bag({"a": 1, "b": 2})
        assert bag.items() == [("a", 1), ("b", 2)]


# =============================================================================
# 4. keys/values/items con iter=True (generator)
# =============================================================================


class TestIterVariants:
    def test_keys_iter_returns_iterator(self):
        """keys(iter=True) returns an iterator, not a list."""
        bag = Bag({"a": 1, "b": 2})
        result = bag.keys(iter=True)
        assert not isinstance(result, list)
        assert list(result) == ["a", "b"]

    def test_values_iter_returns_iterator(self):
        """values(iter=True) returns an iterator."""
        bag = Bag({"a": 1, "b": 2})
        result = bag.values(iter=True)
        assert not isinstance(result, list)
        assert list(result) == [1, 2]

    def test_items_iter_returns_iterator(self):
        """items(iter=True) returns an iterator."""
        bag = Bag({"a": 1, "b": 2})
        result = bag.items(iter=True)
        assert not isinstance(result, list)
        assert list(result) == [("a", 1), ("b", 2)]


# =============================================================================
# 5. is_empty()
# =============================================================================


class TestIsEmpty:
    def test_empty_bag_is_empty(self):
        """A newly created Bag is empty."""
        assert Bag().is_empty() is True

    def test_bag_with_non_none_value_is_not_empty(self):
        """A node with value 1 makes the Bag non-empty."""
        bag = Bag()
        bag["a"] = 1
        assert bag.is_empty() is False

    def test_bag_with_only_none_values_is_empty(self):
        """Nodes with None value count as empty."""
        bag = Bag()
        bag["a"] = None
        bag["b"] = None
        assert bag.is_empty() is True

    def test_zero_is_none_treats_zero_as_empty(self):
        """With zero_is_none=True, 0 also counts as empty."""
        bag = Bag()
        bag["a"] = 0
        assert bag.is_empty(zero_is_none=True) is True
        assert bag.is_empty() is False

    def test_blank_is_none_treats_empty_string_as_empty(self):
        """With blank_is_none=True, empty string also counts as empty."""
        bag = Bag()
        bag["a"] = ""
        assert bag.is_empty(blank_is_none=True) is True
        assert bag.is_empty() is False

    def test_bag_with_resolver_node_is_not_empty(self):
        """A node with a resolver counts as non-empty even without static value.

        Rationale: the resolver represents potential content. is_empty should not
        activate the resolver to discover it, but its mere presence is enough
        to mark the Bag as non-empty.
        """
        from genro_bag.resolvers import BagCbResolver
        bag = Bag()
        bag["data"] = BagCbResolver(lambda: "computed")
        # is_empty must not trigger the resolver, but still returns False
        assert bag.is_empty() is False


# =============================================================================
# 6. get_nodes()
# =============================================================================


class TestGetNodes:
    def test_empty_bag_returns_empty_list(self):
        """get_nodes() on empty Bag returns empty list."""
        assert Bag().get_nodes() == []

    def test_returns_all_first_level_nodes(self):
        """get_nodes() without filter returns all first-level nodes."""
        bag = Bag({"a": 1, "b": 2})
        nodes = bag.get_nodes()
        assert len(nodes) == 2
        assert all(isinstance(n, BagNode) for n in nodes)
        assert [n.label for n in nodes] == ["a", "b"]

    def test_filter_by_condition(self):
        """get_nodes(condition=...) applies a callable filter on nodes."""
        bag = Bag({"a": 1, "b": 2, "c": 3})
        nodes = bag.get_nodes(condition=lambda n: n.value > 1)
        assert [n.label for n in nodes] == ["b", "c"]


# =============================================================================
# 7. get_node_by_attr() - depth-first con priorita' di livello
# =============================================================================


class TestGetNodeByAttr:
    def test_finds_first_level_by_attribute(self):
        """Finds a first-level node by attr=value."""
        bag = Bag()
        bag.set_item("a", 1, _attributes={"id": "target"})
        bag.set_item("b", 2, _attributes={"id": "other"})
        node = bag.get_node_by_attr("id", "target")
        assert isinstance(node, BagNode)
        assert node.label == "a"

    def test_returns_none_if_not_found(self):
        """Returns None if no node matches."""
        bag = Bag()
        bag.set_item("a", 1, _attributes={"id": "x"})
        assert bag.get_node_by_attr("id", "missing") is None

    def test_level_priority_over_depth(self):
        """A match at current level beats a deeper match."""
        bag = Bag()
        bag.set_item("outer.inner", 1, _attributes={"id": "T"})
        # 'top' is a first-level node with id=T -> must win
        bag.set_item("top", 2, _attributes={"id": "T"})
        node = bag.get_node_by_attr("id", "T")
        assert isinstance(node, BagNode)
        assert node.label == "top"

    def test_descends_into_subbags(self):
        """Searches inside sub-Bags if not found at current level."""
        bag = Bag()
        bag.set_item("nest.target", 42, _attributes={"id": "X"})
        node = bag.get_node_by_attr("id", "X")
        assert isinstance(node, BagNode)
        assert node.label == "target"
        assert node.value == 42


# =============================================================================
# 8. get_node_by_value() - primo livello, non ricorsivo
# =============================================================================


class TestGetNodeByValue:
    def test_finds_node_whose_value_contains_key(self):
        """Finds a node whose value (Bag/dict) has key=value."""
        outer = Bag()
        outer["row1.name"] = "alice"
        outer["row2.name"] = "bob"
        node = outer.get_node_by_value("name", "bob")
        assert isinstance(node, BagNode)
        assert node.label == "row2"

    def test_returns_none_if_no_match(self):
        """Returns None if no sub-Bag contains the pair."""
        outer = Bag()
        outer["row1.name"] = "alice"
        assert outer.get_node_by_value("name", "charlie") is None


# =============================================================================
# 9. traverse() - generator mode (path, node)
# =============================================================================


class TestTraverse:
    def test_empty_bag_yields_nothing(self):
        """traverse() on empty Bag yields nothing."""
        assert list(Bag().traverse()) == []

    def test_flat_bag_yields_each_node(self):
        """traverse() on flat Bag yields one tuple per node."""
        bag = Bag({"a": 1, "b": 2})
        result = collect_paths(bag)
        paths = [p for p, _n in result]
        assert paths == ["a", "b"]
        assert all(isinstance(n, BagNode) for _p, n in result)

    def test_deep_tree_yields_depth_first_paths(self):
        """traverse() traverses depth-first with dot-separated paths."""
        bag = Bag()
        bag["a.x"] = 1
        bag["a.y"] = 2
        bag["b"] = 3
        paths = [p for p, _n in collect_paths(bag)]
        # depth-first: 'a', 'a.x', 'a.y', 'b'
        assert paths == ["a", "a.x", "a.y", "b"]


# =============================================================================
# 10. traverse() - legacy callback mode
# =============================================================================


class TestForEach:
    def test_callback_invoked_per_node(self):
        """for_each(callback) calls callback for each visited node."""
        bag = Bag({"a": 1, "b": 2})
        visited = []
        bag.for_each(lambda n: visited.append(n.label), deep=True)
        assert visited == ["a", "b"]

    def test_callback_truthy_return_exits_early(self):
        """If callback returns truthy, walk terminates returning that value."""
        bag = Bag({"a": 1, "b": 2, "c": 3})
        result = bag.for_each(lambda n: n.value if n.value == 2 else None, deep=True)
        assert result == 2

    def test_callback_with_pathlist_tracks_path(self):
        """With _pathlist=[], callback receives current path as list."""
        bag = Bag()
        bag["outer.inner"] = 42
        captured = []

        def cb(node, _pathlist=None, **kw):
            captured.append(list(_pathlist))

        bag.for_each(cb, deep=True, _pathlist=[])
        # first node 'outer' has path ['outer'], second 'inner' has ['outer', 'inner']
        assert captured == [["outer"], ["outer", "inner"]]


# =============================================================================
# 11. query()
# =============================================================================


class TestQuery:
    def test_default_what_returns_tuples_k_v_a(self):
        """query() default = '#k,#v,#a': (label, value, attr)."""
        bag = Bag()
        bag.set_item("a", 1, _attributes={"x": 10})
        bag.set_item("b", 2, _attributes={"x": 20})
        result = bag.query()
        assert result == [("a", 1, {"x": 10}), ("b", 2, {"x": 20})]

    def test_query_labels_only(self):
        """query('#k') returns only labels."""
        bag = Bag({"a": 1, "b": 2})
        assert bag.query("#k") == ["a", "b"]

    def test_query_values_only(self):
        """query('#v') returns only values."""
        bag = Bag({"a": 1, "b": 2})
        assert bag.query("#v") == [1, 2]

    def test_query_attribute_only(self):
        """query('#a.type') returns the 'type' attribute value for each node."""
        bag = Bag()
        bag.set_item("a", 1, _attributes={"type": "int"})
        bag.set_item("b", 2, _attributes={"type": "str"})
        assert bag.query("#a.type") == ["int", "str"]

    def test_query_deep_paths(self):
        """query('#p', deep=True) returns all paths in recursive mode."""
        bag = Bag()
        bag["a.b"] = 1
        bag["a.c"] = 2
        bag["d"] = 3
        result = bag.query("#p", deep=True)
        assert result == ["a", "a.b", "a.c", "d"]

    def test_query_leaves_only(self):
        """query(deep=True, branch=False) excludes branch nodes."""
        bag = Bag()
        bag["a.b"] = 1
        bag["a.c"] = 2
        bag["d"] = 3
        result = bag.query("#p", deep=True, branch=False)
        # 'a' is a branch and is excluded
        assert result == ["a.b", "a.c", "d"]

    def test_query_branches_only(self):
        """query(deep=True, leaf=False) excludes leaf nodes."""
        bag = Bag()
        bag["a.b"] = 1
        bag["c"] = 2
        result = bag.query("#p", deep=True, leaf=False)
        assert result == ["a"]

    def test_query_with_condition(self):
        """query(condition=...) filters nodes."""
        bag = Bag({"a": 1, "b": 2, "c": 3})
        result = bag.query("#k", condition=lambda n: n.value > 1)
        assert result == ["b", "c"]

    def test_query_limit(self):
        """query(limit=N) truncates result to N items."""
        bag = Bag({"a": 1, "b": 2, "c": 3, "d": 4})
        assert bag.query("#k", limit=2) == ["a", "b"]

    def test_query_iter_returns_generator(self):
        """query(iter=True) returns a generator, not a list."""
        bag = Bag({"a": 1, "b": 2})
        result = bag.query("#k", iter=True)
        assert not isinstance(result, list)
        assert list(result) == ["a", "b"]

    def test_query_callable_what(self):
        """query(what=[callable]) applies callable to each node."""
        bag = Bag({"a": 1, "b": 2})
        result = bag.query([lambda n: n.label.upper()])
        assert result == ["A", "B"]

    def test_query_node_node(self):
        """query('#n') returns the BagNode instances themselves."""
        bag = Bag({"a": 1})
        result = bag.query("#n")
        assert len(result) == 1
        assert isinstance(result[0], BagNode)
        assert result[0].label == "a"

    def test_query_static_value(self):
        """query('#__v') returns static_value (never triggers resolver)."""
        bag = Bag({"a": 1})
        assert bag.query("#__v") == [1]

    def test_query_where_colon_what_syntax(self):
        """query('subpath:what') executes query on a sub-Bag.

        Scenario: user wants to query only a subtree without navigating it first.
        """
        bag = Bag()
        bag.set_item("users.alice", "a@x.com")
        bag.set_item("users.bob", "b@x.com")
        bag.set_item("other.skip", "ignore")
        result = bag.query("users:#k,#v")
        assert result == [("alice", "a@x.com"), ("bob", "b@x.com")]

    def test_query_inner_value_path_on_bag_value(self):
        """query('#v.key') extracts specific key from value when dict-like.

        Scenario: collection of records, want only one column.
        """
        bag = Bag()
        bag.set_item("r1", Bag({"name": "alice", "age": 30}))
        bag.set_item("r2", Bag({"name": "bob", "age": 25}))
        assert bag.query("#v.name") == ["alice", "bob"]

    def test_query_custom_key_reads_from_value_dict(self):
        """query('keyname') on __getitem__-able value extracts value[keyname].

        Note: syntax without '#' prefix → direct key on value.
        """
        bag = Bag()
        bag.set_item("r1", {"name": "alice", "city": "Rome"})
        bag.set_item("r2", {"name": "bob", "city": "Milan"})
        assert bag.query("name") == ["alice", "bob"]
        assert bag.query("city") == ["Rome", "Milan"]

    def test_query_deep_limit_stops_across_branches(self):
        """limit truncates result even mid-recursion in deep mode.

        Scenario: bag with many nodes, user wants only first N in pre-order.
        """
        bag = Bag()
        bag["a.b.c"] = 1
        bag["a.b.d"] = 2
        bag["a.e"] = 3
        bag["f"] = 4
        result = bag.query("#p", deep=True, limit=2)
        # pre-order: 'a', 'a.b', ... stopped at 2
        assert len(result) == 2
        assert result == ["a", "a.b"]


# =============================================================================
# 12. digest() - alias retrocompat + as_columns
# =============================================================================


class TestDigest:
    def test_digest_default_matches_query_default(self):
        """digest() without args equals query() non-deep non-iter."""
        bag = Bag({"a": 1, "b": 2})
        assert bag.digest() == bag.query()

    def test_digest_as_columns_transposes(self):
        """digest(as_columns=True) transposes to columns (list of lists)."""
        bag = Bag()
        bag.set_item("a", 1, _attributes={"x": 10})
        bag.set_item("b", 2, _attributes={"x": 20})
        result = bag.digest("#k,#v", as_columns=True)
        assert result == [["a", "b"], [1, 2]]

    def test_digest_as_columns_on_empty_bag(self):
        """digest(as_columns=True) on empty Bag returns empty lists for each col."""
        result = Bag().digest("#k,#v", as_columns=True)
        assert result == [[], []]

    def test_digest_as_columns_single_column(self):
        """digest(what='#k', as_columns=True) returns single list wrapped.

        Scenario: user requests single column with as_columns=True.
        """
        bag = Bag({"a": 1, "b": 2})
        result = bag.digest("#k", as_columns=True)
        # single column: result[0] is the label list
        assert result == [["a", "b"]]


# =============================================================================
# 13. columns() - wrapper su digest
# =============================================================================


class TestColumns:
    def test_columns_from_string(self):
        """columns('a,b') returns columns for fields 'a' and 'b'."""
        bag = Bag()
        bag["row1.name"] = "alice"
        bag["row1.age"] = 30
        bag["row2.name"] = "bob"
        bag["row2.age"] = 25
        result = bag.columns("name,age")
        assert result == [["alice", "bob"], [30, 25]]

    def test_columns_attr_mode(self):
        """columns(cols, attr_mode=True) reads from attributes."""
        bag = Bag()
        bag.set_item("a", 1, _attributes={"price": 10, "qty": 2})
        bag.set_item("b", 2, _attributes={"price": 20, "qty": 3})
        result = bag.columns("price,qty", attr_mode=True)
        assert result == [[10, 20], [2, 3]]


# =============================================================================
# 14. sum()
# =============================================================================


class TestSum:
    def test_sum_values_default(self):
        """sum() without args sums first-level values."""
        bag = Bag({"a": 1, "b": 2, "c": 3})
        assert bag.sum() == 6

    def test_sum_none_values_are_zero(self):
        """None values are treated as 0 by sum."""
        bag = Bag({"a": 1, "b": None, "c": 2})
        assert bag.sum() == 3

    def test_sum_attribute(self):
        """sum('#a.price') sums the 'price' attribute of each node."""
        bag = Bag()
        bag.set_item("a", 1, _attributes={"price": 10})
        bag.set_item("b", 2, _attributes={"price": 20})
        assert bag.sum("#a.price") == 30

    def test_sum_multiple_returns_list(self):
        """sum('#v,#a.qty') returns [sum_values, sum_qty]."""
        bag = Bag()
        bag.set_item("a", 1, _attributes={"qty": 5})
        bag.set_item("b", 2, _attributes={"qty": 7})
        assert bag.sum("#v,#a.qty") == [3, 12]

    def test_sum_with_condition(self):
        """sum with condition filters before summing."""
        bag = Bag({"a": 1, "b": 2, "c": 3})
        total = bag.sum("#v", condition=lambda n: n.value > 1)
        assert total == 5

    def test_sum_stays_at_current_level(self):
        """sum only considers current-level attributes."""
        bag = Bag()
        bag.set_item("outer.a", 0, _attributes={"qty": 10})
        bag.set_item("outer.b", 0, _attributes={"qty": 20})
        bag.set_item("c", 0, _attributes={"qty": 5})
        assert bag.sum("#a.qty") == 5
        with pytest.raises(TypeError):
            bag.sum("#a.qty", deep=True)


# =============================================================================
# 15. sort() - validato tramite keys()/values()
# =============================================================================


class TestSort:
    def test_sort_by_label_ascending_default(self):
        """sort('#k') sorts by label ascending (default)."""
        bag = Bag()
        bag["c"] = 1
        bag["a"] = 2
        bag["b"] = 3
        bag.sort("#k")
        assert bag.keys() == ["a", "b", "c"]

    def test_sort_by_label_descending(self):
        """sort('#k:d') sorts by label descending."""
        bag = Bag()
        bag["a"] = 1
        bag["c"] = 2
        bag["b"] = 3
        bag.sort("#k:d")
        assert bag.keys() == ["c", "b", "a"]

    def test_sort_by_value_ascending(self):
        """sort('#v') sorts by value."""
        bag = Bag()
        bag["a"] = 3
        bag["b"] = 1
        bag["c"] = 2
        bag.sort("#v")
        assert bag.values() == [1, 2, 3]

    def test_sort_by_value_descending(self):
        """sort('#v:d') sorts by value descending."""
        bag = Bag({"a": 1, "b": 3, "c": 2})
        bag.sort("#v:d")
        assert bag.values() == [3, 2, 1]

    def test_sort_by_attribute(self):
        """sort('#a.name') sorts by 'name' attribute."""
        bag = Bag()
        bag.set_item("a", 1, _attributes={"name": "charlie"})
        bag.set_item("b", 2, _attributes={"name": "alice"})
        bag.set_item("c", 3, _attributes={"name": "bob"})
        bag.sort("#a.name")
        assert bag.keys() == ["b", "c", "a"]

    def test_sort_by_callable(self):
        """sort(callable) uses callable as key function."""
        bag = Bag({"a": 3, "b": 1, "c": 2})
        bag.sort(lambda n: n.value)
        assert bag.values() == [1, 2, 3]

    def test_sort_returns_self(self):
        """sort returns self for chaining."""
        bag = Bag({"a": 1})
        assert bag.sort("#k") is bag

    def test_multi_level_sort(self):
        """sort('#a.g:a,#v:d') applies multi-level sort."""
        bag = Bag()
        # same group 'g=A', different values -> must sort by value desc
        bag.set_item("n1", 1, _attributes={"g": "A"})
        bag.set_item("n2", 3, _attributes={"g": "A"})
        bag.set_item("n3", 2, _attributes={"g": "B"})
        bag.sort("#a.g:a,#v:d")
        # within 'A' descending by value -> n2(3), n1(1); then group 'B' -> n3(2)
        assert bag.keys() == ["n2", "n1", "n3"]

    def test_sort_by_field_inside_value_dict(self):
        """sort('fieldname') sorts by value of a key in value dict.

        Scenario: collection of records (value = dict), sort by 'age'.
        """
        bag = Bag()
        bag.set_item("r1", {"age": 30, "name": "alice"})
        bag.set_item("r2", {"age": 25, "name": "bob"})
        bag.set_item("r3", {"age": 40, "name": "carol"})
        bag.sort("age")
        assert bag.keys() == ["r2", "r1", "r3"]


def collect_paths(bag):
    result = []
    bag.for_each(lambda node, _pathlist: result.append((".".join(_pathlist), node)),
                 deep=True, _pathlist=[])
    return result
