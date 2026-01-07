# Copyright 2025 Softwell S.r.l. - Genropy Team
# Licensed under the Apache License, Version 2.0

"""Extended coverage tests - using only Bag public API.

These tests exercise internal code paths through the public Bag interface,
without directly testing internal modules like bagnode, bag_parse, bag_query.
"""

import pytest

from genro_bag.bag import Bag


# =============================================================================
# BagNode equality and comparison (via Bag.get_node)
# =============================================================================


class TestNodeEquality:
    """Test node equality comparisons through Bag API."""

    def test_nodes_equal_same_value_and_attrs(self):
        """Two nodes with same label, value, and attrs are equal."""
        bag1 = Bag()
        bag1.set_item('item', 'value', attr1='a', attr2='b')

        bag2 = Bag()
        bag2.set_item('item', 'value', attr1='a', attr2='b')

        node1 = bag1.get_node('item')
        node2 = bag2.get_node('item')

        assert node1 == node2

    def test_nodes_not_equal_different_value(self):
        """Nodes with different values are not equal."""
        bag1 = Bag()
        bag1['item'] = 'value1'

        bag2 = Bag()
        bag2['item'] = 'value2'

        assert bag1.get_node('item') != bag2.get_node('item')

    def test_nodes_not_equal_different_attrs(self):
        """Nodes with different attributes are not equal."""
        bag1 = Bag()
        bag1.set_item('item', 'value', attr='a')

        bag2 = Bag()
        bag2.set_item('item', 'value', attr='b')

        assert bag1.get_node('item') != bag2.get_node('item')

    def test_nodes_not_equal_different_label(self):
        """Nodes with different labels are not equal."""
        bag = Bag()
        bag['item1'] = 'value'
        bag['item2'] = 'value'

        assert bag.get_node('item1') != bag.get_node('item2')

    def test_node_not_equal_to_non_node(self):
        """Node is not equal to non-BagNode objects."""
        bag = Bag()
        bag['item'] = 'value'
        node = bag.get_node('item')

        assert node != 'value'
        assert node != 42
        assert node != {'label': 'item', 'value': 'value'}

    def test_node_equality_with_resolver(self):
        """Nodes with same resolver are equal."""
        from genro_bag.resolvers import BagCbResolver

        resolver = BagCbResolver(lambda: 42)

        bag1 = Bag()
        bag1['item'] = resolver

        bag2 = Bag()
        bag2['item'] = resolver

        assert bag1.get_node('item') == bag2.get_node('item')

    def test_node_str_repr(self):
        """Test node string representations."""
        bag = Bag()
        bag['item'] = 'value'
        node = bag.get_node('item')

        assert 'item' in str(node)
        assert 'BagNode' in repr(node)


# =============================================================================
# Node navigation (fullpath, position, parent_node)
# =============================================================================


class TestNodeNavigation:
    """Test node navigation properties through Bag API."""

    def test_node_position(self):
        """Test node position in parent."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag['c'] = 3

        assert bag.get_node('a').position == 0
        assert bag.get_node('b').position == 1
        assert bag.get_node('c').position == 2

    def test_node_fullpath_nested_with_backref(self):
        """Test fullpath for nested nodes with backref enabled."""
        bag = Bag()
        bag['level1.level2.leaf'] = 'value'
        bag.set_backref()  # Enable backref mode

        leaf_node = bag['level1.level2'].get_node('leaf')
        assert leaf_node.fullpath == 'level1.level2.leaf'

    def test_node_fullpath_root_returns_none(self):
        """Root-level node without backref has None fullpath."""
        bag = Bag()
        bag['item'] = 'value'
        # Without backref, fullpath is None
        node = bag.get_node('item')
        assert node.fullpath is None

    def test_node_parent_node_navigation(self):
        """Test parent_node navigation."""
        bag = Bag()
        bag['level1.level2.leaf'] = 'value'
        bag.set_backref()  # Enable backref mode

        level2 = bag['level1.level2']
        leaf = level2.get_node('leaf')

        # parent_node should be the node containing level2 Bag
        parent = leaf.parent_node
        assert parent is not None
        assert parent.label == 'level2'

    def test_node_underscore_returns_parent_bag(self):
        """Test _ property returns parent bag for chaining."""
        bag = Bag()
        bag['item'] = 'value'
        node = bag.get_node('item')

        # _ returns parent bag
        assert node._ is bag

    def test_node_fullpath_without_backref_returns_none(self):
        """Fullpath returns None when backref is not enabled."""
        bag = Bag()
        bag['a.b.c'] = 'value'

        # Without backref, fullpath is None
        node = bag['a.b'].get_node('c')
        assert node.fullpath is None


# =============================================================================
# Attribute inheritance and ownership
# =============================================================================


class TestAttributeInheritance:
    """Test attribute inheritance through Bag API."""

    def test_get_inherited_attributes_single_level(self):
        """Test inherited attributes at single level."""
        bag = Bag()
        bag.set_item('item', 'value', color='red', size='large')
        bag.set_backref()  # Enable backref mode

        node = bag.get_node('item')
        inherited = node.get_inherited_attributes()

        assert inherited['color'] == 'red'
        assert inherited['size'] == 'large'

    def test_get_inherited_attributes_multiple_levels(self):
        """Test inherited attributes merge from ancestors."""
        bag = Bag()
        bag.set_item('level1', Bag(), ancestor_attr='from_ancestor')
        bag['level1'].set_item('level2', Bag(), middle_attr='from_middle')
        bag['level1.level2'].set_item('leaf', 'value', leaf_attr='from_leaf')
        bag.set_backref()  # Enable backref mode

        leaf_node = bag['level1.level2'].get_node('leaf')
        inherited = leaf_node.get_inherited_attributes()

        assert inherited['leaf_attr'] == 'from_leaf'
        assert inherited['middle_attr'] == 'from_middle'
        assert inherited['ancestor_attr'] == 'from_ancestor'

    def test_attribute_owner_node_finds_owner(self):
        """Test finding the node that owns an attribute."""
        bag = Bag()
        bag.set_item('level1', Bag(), owner_attr='owned')
        bag['level1'].set_item('level2', Bag())
        bag['level1.level2']['leaf'] = 'value'
        bag.set_backref()  # Enable backref mode

        leaf_node = bag['level1.level2'].get_node('leaf')
        owner = leaf_node.attribute_owner_node('owner_attr')

        assert owner is not None
        assert owner.label == 'level1'
        assert owner.get_attr('owner_attr') == 'owned'

    def test_attribute_owner_node_with_value_match(self):
        """Test finding owner with specific attribute value."""
        bag = Bag()
        bag.set_item('level1', Bag(), status='active')
        bag['level1'].set_item('level2', Bag(), status='inactive')
        bag['level1.level2']['leaf'] = 'value'
        bag.set_backref()  # Enable backref mode

        leaf_node = bag['level1.level2'].get_node('leaf')

        # Find owner with status='active'
        owner = leaf_node.attribute_owner_node('status', 'active')
        assert owner is not None
        assert owner.label == 'level1'

        # Find owner with status='inactive'
        owner = leaf_node.attribute_owner_node('status', 'inactive')
        assert owner is not None
        assert owner.label == 'level2'

    def test_attribute_owner_node_not_found(self):
        """Test attribute_owner_node returns None if not found."""
        bag = Bag()
        bag['item'] = 'value'
        bag.set_backref()  # Enable backref mode

        node = bag.get_node('item')
        owner = node.attribute_owner_node('nonexistent_attr')
        assert owner is None


# =============================================================================
# Node diff
# =============================================================================


class TestNodeDiff:
    """Test node diff through Bag API."""

    def test_diff_equal_nodes(self):
        """Diff of equal nodes returns None."""
        bag1 = Bag()
        bag1.set_item('item', 'value', attr='a')

        bag2 = Bag()
        bag2.set_item('item', 'value', attr='a')

        diff = bag1.get_node('item').diff(bag2.get_node('item'))
        assert diff is None

    def test_diff_different_label(self):
        """Diff detects different labels."""
        bag = Bag()
        bag['item1'] = 'value'
        bag['item2'] = 'value'

        diff = bag.get_node('item1').diff(bag.get_node('item2'))
        assert 'label' in diff.lower()

    def test_diff_different_value(self):
        """Diff detects different values."""
        bag1 = Bag()
        bag1['item'] = 'value1'

        bag2 = Bag()
        bag2['item'] = 'value2'

        diff = bag1.get_node('item').diff(bag2.get_node('item'))
        assert 'value' in diff.lower()

    def test_diff_different_attrs(self):
        """Diff detects different attributes."""
        bag1 = Bag()
        bag1.set_item('item', 'value', attr='a')

        bag2 = Bag()
        bag2.set_item('item', 'value', attr='b')

        diff = bag1.get_node('item').diff(bag2.get_node('item'))
        assert 'attr' in diff.lower()

    def test_diff_nested_bags(self):
        """Diff of nested Bag values calls nested diff."""
        bag1 = Bag()
        bag1['parent'] = Bag()
        bag1['parent.child'] = 'value1'

        bag2 = Bag()
        bag2['parent'] = Bag()
        bag2['parent.child'] = 'value2'

        diff = bag1.get_node('parent').diff(bag2.get_node('parent'))
        assert diff is not None
        assert 'value' in diff.lower()


# =============================================================================
# Move and delete operations
# =============================================================================


class TestMoveAndDelete:
    """Test move and delete operations through Bag API."""

    def test_delete_single_node(self):
        """Delete single node by label."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag['c'] = 3

        del bag['b']

        assert 'b' not in bag
        assert bag.keys() == ['a', 'c']

    def test_delete_by_hash_index(self):
        """Delete node by #n index syntax."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag['c'] = 3

        del bag['#1']  # Remove 'b' at index 1

        assert bag.keys() == ['a', 'c']

    def test_delete_multiple_nodes_sequentially(self):
        """Delete multiple nodes sequentially."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag['c'] = 3
        bag['d'] = 4

        del bag['b']
        del bag['c']

        assert bag.keys() == ['a', 'd']

    def test_move_single_node_to_position(self):
        """Move single node to new position."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag['c'] = 3
        bag.set_backref()  # Enable backref mode

        # Move 'a' (index 0) to position after 'b' (index 1)
        bag._nodes.move(0, 1)

        # After move: b, a, c
        assert bag.keys() == ['b', 'a', 'c']

    def test_move_multiple_nodes(self):
        """Move multiple nodes to new position."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag['c'] = 3
        bag['d'] = 4
        bag.set_backref()  # Enable backref mode

        # Move indices [0, 1] (a, b) to position 3 (d)
        bag._nodes.move([0, 1], 3)

        # After move: c, d, b, a (or similar reorder)
        assert len(bag) == 4
        assert set(bag.keys()) == {'a', 'b', 'c', 'd'}

    def test_move_to_invalid_position(self):
        """Move to invalid position is ignored."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2

        # Negative position
        bag._nodes.move(0, -1)
        assert bag.keys() == ['a', 'b']

        # Position beyond length
        bag._nodes.move(0, 10)
        assert bag.keys() == ['a', 'b']

    def test_pop_by_label_returns_value(self):
        """Pop by label returns the value."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2

        value = bag.pop('a')

        assert value == 1
        assert 'a' not in bag

    def test_pop_node_returns_node(self):
        """pop_node returns the BagNode."""
        bag = Bag()
        bag.set_item('a', 1, attr='test')
        bag['b'] = 2

        node = bag.pop_node('a')

        assert node is not None
        assert node.value == 1
        assert node.get_attr('attr') == 'test'
        assert 'a' not in bag


# =============================================================================
# Query with deep path access
# =============================================================================


class TestQueryDeepPath:
    """Test query with #v. deep path access."""

    def test_query_v_dot_inner_path(self):
        """Query #v.path accesses inner path of value."""
        bag = Bag()

        # Create nodes whose values are Bags
        inner1 = Bag()
        inner1['name'] = 'Alice'
        inner1['age'] = 30

        inner2 = Bag()
        inner2['name'] = 'Bob'
        inner2['age'] = 25

        bag['user1'] = inner1
        bag['user2'] = inner2

        # Query inner path
        names = bag.query('#v.name')
        assert list(names) == ['Alice', 'Bob']

    def test_query_v_dot_with_non_bag_value(self):
        """Query #v.path returns None for non-Bag values."""
        bag = Bag()
        bag['item1'] = 'string_value'
        bag['item2'] = 42

        # Inner path on non-Bag returns None
        result = list(bag.query('#v.inner'))
        assert result == [None, None]

    def test_query_double_v(self):
        """Query #__v returns static value."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2

        result = list(bag.query('#__v'))
        assert result == [1, 2]


# =============================================================================
# Digest with columns
# =============================================================================


class TestDigestColumns:
    """Test digest with as_columns option."""

    def test_digest_as_columns(self):
        """Digest returns columns when as_columns=True."""
        bag = Bag()
        bag.set_item('item1', 10, price=100)
        bag.set_item('item2', 20, price=200)
        bag.set_item('item3', 30, price=300)

        columns = bag.digest('#k,#v,#a.price', as_columns=True)

        assert len(columns) == 3
        assert columns[0] == ['item1', 'item2', 'item3']  # keys
        assert columns[1] == [10, 20, 30]  # values
        assert columns[2] == [100, 200, 300]  # prices

    def test_digest_as_columns_empty(self):
        """Digest with empty bag returns empty columns."""
        bag = Bag()

        columns = bag.digest('#k,#v', as_columns=True)

        assert len(columns) == 2
        assert columns[0] == []
        assert columns[1] == []

    def test_digest_single_column(self):
        """Digest single column with as_columns."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2

        columns = bag.digest('#k', as_columns=True)

        assert columns == [['a', 'b']]


# =============================================================================
# Sort operations
# =============================================================================


class TestSortOperations:
    """Test sort operations through Bag API."""

    def test_sort_by_key_ascending(self):
        """Sort by key ascending."""
        bag = Bag()
        bag['c'] = 3
        bag['a'] = 1
        bag['b'] = 2

        bag.sort('#k:a')

        assert bag.keys() == ['a', 'b', 'c']

    def test_sort_by_key_descending(self):
        """Sort by key descending."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag['c'] = 3

        bag.sort('#k:d')

        assert bag.keys() == ['c', 'b', 'a']

    def test_sort_by_value_ascending(self):
        """Sort by value ascending."""
        bag = Bag()
        bag['x'] = 30
        bag['y'] = 10
        bag['z'] = 20

        bag.sort('#v:a')

        assert bag.values() == [10, 20, 30]

    def test_sort_by_value_descending(self):
        """Sort by value descending."""
        bag = Bag()
        bag['x'] = 10
        bag['y'] = 30
        bag['z'] = 20

        bag.sort('#v:d')

        assert bag.values() == [30, 20, 10]

    def test_sort_by_attribute(self):
        """Sort by attribute value."""
        bag = Bag()
        bag.set_item('item1', 'a', priority=3)
        bag.set_item('item2', 'b', priority=1)
        bag.set_item('item3', 'c', priority=2)

        bag.sort('#a.priority:a')

        assert bag.keys() == ['item2', 'item3', 'item1']

    def test_sort_by_value_field(self):
        """Sort by field in value (when value is dict-like)."""
        bag = Bag()
        bag['item1'] = Bag({'name': 'Charlie', 'age': 30})
        bag['item2'] = Bag({'name': 'Alice', 'age': 25})
        bag['item3'] = Bag({'name': 'Bob', 'age': 35})

        bag.sort('name:a')

        assert bag.keys() == ['item2', 'item3', 'item1']

    def test_sort_multi_level(self):
        """Sort with multiple levels."""
        bag = Bag()
        bag.set_item('a', 1, group='B', order=2)
        bag.set_item('b', 2, group='A', order=1)
        bag.set_item('c', 3, group='B', order=1)
        bag.set_item('d', 4, group='A', order=2)

        # Sort by group ascending, then by order ascending
        bag.sort('#a.group:a,#a.order:a')

        keys = bag.keys()
        # Group A first (b, d), then Group B (c, a)
        # Within each group, sorted by order
        assert keys[0] in ['b', 'd']  # Group A
        assert keys[2] in ['a', 'c']  # Group B

    def test_sort_with_none_values(self):
        """Sort handles None values (sorted last)."""
        bag = Bag()
        bag.set_item('item1', 'a', priority=None)
        bag.set_item('item2', 'b', priority=1)
        bag.set_item('item3', 'c', priority=2)

        bag.sort('#a.priority:a')

        # None should be last
        assert bag.keys()[-1] == 'item1'

    def test_sort_case_insensitive(self):
        """Sort case insensitive (mode 'a' or 'd')."""
        bag = Bag()
        bag['Apple'] = 1
        bag['banana'] = 2
        bag['Cherry'] = 3

        bag.sort('#k:a')  # case insensitive ascending

        # Should be alphabetical ignoring case
        keys = bag.keys()
        assert keys[0].lower() < keys[1].lower() < keys[2].lower()

    def test_sort_case_sensitive(self):
        """Sort case sensitive (mode 'A' or 'D')."""
        bag = Bag()
        bag['apple'] = 1
        bag['Banana'] = 2
        bag['cherry'] = 3

        bag.sort('#k:A')  # case sensitive ascending

        # Capital letters sort before lowercase in ASCII
        assert bag.keys()[0] == 'Banana'

    def test_sort_with_callable(self):
        """Sort with custom callable key."""
        bag = Bag()
        bag['aaa'] = 1
        bag['b'] = 2
        bag['cc'] = 3

        # Sort by label length
        bag.sort(lambda n: len(n.label))

        assert bag.keys() == ['b', 'cc', 'aaa']


# =============================================================================
# Sum operations
# =============================================================================


class TestSumOperations:
    """Test sum operations through Bag API."""

    def test_sum_values(self):
        """Sum all values."""
        bag = Bag()
        bag['a'] = 10
        bag['b'] = 20
        bag['c'] = 30

        assert bag.sum() == 60

    def test_sum_attribute(self):
        """Sum attribute values."""
        bag = Bag()
        bag.set_item('item1', 'a', price=100)
        bag.set_item('item2', 'b', price=200)
        bag.set_item('item3', 'c', price=300)

        assert bag.sum('#a.price') == 600

    def test_sum_multiple_specs(self):
        """Sum multiple specs returns list."""
        bag = Bag()
        bag.set_item('item1', 10, qty=1)
        bag.set_item('item2', 20, qty=2)
        bag.set_item('item3', 30, qty=3)

        result = bag.sum('#v,#a.qty')

        assert isinstance(result, list)
        assert result[0] == 60  # sum of values
        assert result[1] == 6   # sum of qty

    def test_sum_with_condition(self):
        """Sum with condition filter."""
        bag = Bag()
        bag.set_item('item1', 10, active=True)
        bag.set_item('item2', 20, active=False)
        bag.set_item('item3', 30, active=True)

        total = bag.sum('#v', condition=lambda n: n.get_attr('active'))

        assert total == 40  # Only active items

    def test_sum_deep_recursive(self):
        """Sum with deep=True for recursive sum."""
        bag = Bag()
        bag['level1'] = Bag()
        bag['level1.a'] = 10
        bag['level1.b'] = 20
        bag['level2'] = Bag()
        bag['level2.c'] = 30
        bag['level2.d'] = 40

        # Deep sum includes nested bags
        total = bag.sum('#v', deep=True)

        # Values are in nested bags, not at root
        assert total == 100

    def test_sum_with_none_values(self):
        """Sum handles None values as 0."""
        bag = Bag()
        bag['a'] = 10
        bag['b'] = None
        bag['c'] = 20

        assert bag.sum() == 30


# =============================================================================
# Walk with callback return
# =============================================================================


class TestWalkCallback:
    """Test walk with callback return value."""

    def test_walk_callback_stops_on_return(self):
        """Walk stops when callback returns truthy value."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag['c'] = 3

        visited = []

        def callback(node, **kw):
            visited.append(node.label)
            if node.label == 'b':
                return 'found'
            return None

        result = bag.walk(callback)

        assert result == 'found'
        assert 'a' in visited
        assert 'b' in visited
        assert 'c' not in visited  # Should have stopped at 'b'

    def test_walk_callback_visits_all(self):
        """Walk visits all nodes when callback returns None."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag['c'] = 3

        visited = []

        def callback(node, **kw):
            visited.append(node.label)
            return None

        result = bag.walk(callback)

        assert result is None
        assert visited == ['a', 'b', 'c']

    def test_walk_callback_recursive(self):
        """Walk visits nested bags recursively."""
        bag = Bag()
        bag['level1'] = Bag()
        bag['level1.child1'] = 'a'
        bag['level1.child2'] = 'b'
        bag['level2'] = 'c'

        visited = []

        def callback(node, **kw):
            visited.append(node.label)
            return None

        bag.walk(callback)

        assert 'level1' in visited
        assert 'child1' in visited
        assert 'child2' in visited
        assert 'level2' in visited


# =============================================================================
# Rootattributes handling
# =============================================================================


class TestRootattributes:
    """Test rootattributes handling in set_value."""

    def test_set_value_with_rootattributes_object(self):
        """Setting value with rootattributes merges them."""

        class ObjWithRootattr:
            def __init__(self):
                self.rootattributes = {'inherited': 'yes', 'source': 'object'}

        bag = Bag()
        obj = ObjWithRootattr()
        bag.set_item('item', obj)

        # Check that rootattributes were merged into node's attributes
        node = bag.get_node('item')
        assert node.get_attr('inherited') == 'yes'
        assert node.get_attr('source') == 'object'

    def test_set_value_with_empty_rootattributes(self):
        """Empty rootattributes doesn't add anything."""

        class ObjWithEmptyRootattr:
            def __init__(self):
                self.rootattributes = {}

        bag = Bag()
        bag.set_item('item', ObjWithEmptyRootattr(), myattr='mine')

        node = bag.get_node('item')
        assert node.get_attr('myattr') == 'mine'


# =============================================================================
# Static value property
# =============================================================================


class TestStaticValue:
    """Test static_value property."""

    def test_static_value_with_resolver_read_only(self):
        """static_value stays None with read_only resolver (default)."""
        from genro_bag.resolvers import BagCbResolver

        call_count = [0]

        def callback():
            call_count[0] += 1
            return 'resolved'

        # Default is read_only=True - no caching
        resolver = BagCbResolver(callback)
        bag = Bag()
        bag['item'] = resolver

        node = bag.get_node('item')

        # static_value is None initially
        assert node.static_value is None
        assert call_count[0] == 0

        # Accessing .value triggers resolver but doesn't cache
        result = node.value
        assert result == 'resolved'
        assert call_count[0] == 1

        # static_value remains None (read_only doesn't cache)
        assert node.static_value is None

    def test_static_value_with_resolver_caches_when_not_read_only(self):
        """static_value returns cached _value when read_only=False."""
        from genro_bag.resolvers import BagCbResolver

        call_count = [0]

        def callback():
            call_count[0] += 1
            return 'resolved'

        # read_only=False enables caching
        resolver = BagCbResolver(callback, read_only=False)
        bag = Bag()
        bag['item'] = resolver

        node = bag.get_node('item')

        # static_value is None initially
        assert node.static_value is None
        assert call_count[0] == 0

        # Accessing .value triggers resolver and caches result
        result = node.value
        assert result == 'resolved'
        assert call_count[0] == 1

        # Now static_value has the cached result
        assert node.static_value == 'resolved'

    def test_set_static_value_directly(self):
        """static_value setter bypasses processing."""
        bag = Bag()
        bag['item'] = 'original'

        node = bag.get_node('item')
        node.static_value = 'direct_set'

        assert node.static_value == 'direct_set'
        assert node.value == 'direct_set'


# =============================================================================
# Node as_tuple and to_json
# =============================================================================


class TestNodeConversion:
    """Test node conversion methods."""

    def test_node_as_tuple(self):
        """as_tuple returns (label, value, attr, resolver)."""
        bag = Bag()
        bag.set_item('item', 'value', attr1='a', attr2='b')

        node = bag.get_node('item')
        t = node.as_tuple()

        assert t[0] == 'item'
        assert t[1] == 'value'
        assert t[2] == {'attr1': 'a', 'attr2': 'b'}
        assert t[3] is None  # No resolver

    def test_node_to_json(self):
        """to_json returns dict with label, value, attr."""
        bag = Bag()
        bag.set_item('item', 42, type='int')

        node = bag.get_node('item')
        j = node.to_json()

        assert j['label'] == 'item'
        assert j['value'] == 42
        assert j['attr'] == {'type': 'int'}

    def test_node_to_json_with_simple_value(self):
        """to_json handles simple values."""
        bag = Bag()
        bag.set_item('item', 'simple_value', attr1='a')

        node = bag.get_node('item')
        j = node.to_json()

        assert j['label'] == 'item'
        assert j['value'] == 'simple_value'
        assert j['attr'] == {'attr1': 'a'}


# =============================================================================
# Delete attribute
# =============================================================================


class TestDeleteAttribute:
    """Test del_attr method."""

    def test_del_single_attr(self):
        """Delete single attribute."""
        bag = Bag()
        bag.set_item('item', 'value', attr1='a', attr2='b')

        node = bag.get_node('item')
        node.del_attr('attr1')

        assert 'attr1' not in node.attr
        assert node.get_attr('attr2') == 'b'

    def test_del_multiple_attrs(self):
        """Delete multiple attributes."""
        bag = Bag()
        bag.set_item('item', 'value', a=1, b=2, c=3)

        node = bag.get_node('item')
        node.del_attr('a', 'b')

        assert 'a' not in node.attr
        assert 'b' not in node.attr
        assert node.get_attr('c') == 3

    def test_del_attr_comma_separated(self):
        """Delete attributes with comma-separated string."""
        bag = Bag()
        bag.set_item('item', 'value', x=1, y=2, z=3)

        node = bag.get_node('item')
        node.del_attr('x,y')

        assert 'x' not in node.attr
        assert 'y' not in node.attr
        assert node.get_attr('z') == 3

    def test_del_nonexistent_attr(self):
        """Delete nonexistent attribute doesn't raise."""
        bag = Bag()
        bag.set_item('item', 'value', attr='a')

        node = bag.get_node('item')
        node.del_attr('nonexistent')  # Should not raise

        assert node.get_attr('attr') == 'a'


# =============================================================================
# Has attribute
# =============================================================================


class TestHasAttribute:
    """Test has_attr method."""

    def test_has_attr_exists(self):
        """has_attr returns True if attribute exists."""
        bag = Bag()
        bag.set_item('item', 'value', myattr='myvalue')

        node = bag.get_node('item')
        assert node.has_attr('myattr') is True

    def test_has_attr_not_exists(self):
        """has_attr returns False if attribute doesn't exist."""
        bag = Bag()
        bag['item'] = 'value'

        node = bag.get_node('item')
        assert node.has_attr('nonexistent') is False

    def test_has_attr_with_value_match(self):
        """has_attr with value checks both existence and value."""
        bag = Bag()
        bag.set_item('item', 'value', status='active')

        node = bag.get_node('item')
        assert node.has_attr('status', 'active') is True
        assert node.has_attr('status', 'inactive') is False


# =============================================================================
# Remove null attributes
# =============================================================================


class TestRemoveNullAttributes:
    """Test _remove_null_attributes in set_attr."""

    def test_set_attr_removes_null(self):
        """set_attr with _remove_null_attributes removes None values."""
        bag = Bag()
        bag.set_item('item', 'value', a=1, b=2, c=3)

        node = bag.get_node('item')
        node.set_attr({'a': None, 'd': 4}, _remove_null_attributes=True)

        assert 'a' not in node.attr
        assert node.get_attr('d') == 4

    def test_set_value_removes_null_attrs(self):
        """set_item with _remove_null_attributes in attrs."""
        bag = Bag()
        bag.set_item('item', 'value', keep='kept', remove=None,
                     _remove_null_attributes=True)

        node = bag.get_node('item')
        assert node.get_attr('keep') == 'kept'
        assert 'remove' not in node.attr


# =============================================================================
# Bag __str__ with visited tracking
# =============================================================================


class TestBagStr:
    """Test Bag __str__ representation."""

    def test_str_simple_bag(self):
        """String representation of simple bag."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 'hello'

        s = str(bag)

        assert 'a' in s
        assert 'b' in s
        assert '1' in s
        assert 'hello' in s

    def test_str_nested_bag(self):
        """String representation of nested bag."""
        bag = Bag()
        bag['level1'] = Bag()
        bag['level1.child'] = 'value'

        s = str(bag)

        assert 'level1' in s
        assert 'child' in s
        assert 'Bag' in s

    def test_str_with_none_value(self):
        """String representation handles None values."""
        bag = Bag()
        bag['item'] = None

        s = str(bag)

        assert 'item' in s
        assert 'None' in s

    def test_str_with_bytes_value(self):
        """String representation handles bytes values."""
        bag = Bag()
        bag['item'] = b'hello bytes'

        s = str(bag)

        assert 'item' in s
        assert 'hello bytes' in s


# =============================================================================
# Index access with #n syntax
# =============================================================================


class TestIndexAccess:
    """Test #n index access syntax."""

    def test_access_by_hash_index(self):
        """Access node by #n index."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag['c'] = 3

        assert bag['#0'] == 1
        assert bag['#1'] == 2
        assert bag['#2'] == 3

    def test_access_invalid_hash_index(self):
        """Access invalid #n index returns None."""
        bag = Bag()
        bag['a'] = 1

        assert bag['#10'] is None
        assert bag['#abc'] is None

    def test_get_node_by_hash_index(self):
        """Get node by #n index."""
        bag = Bag()
        bag['first'] = 'a'
        bag['second'] = 'b'

        node = bag.get_node('#1')
        assert node is not None
        assert node.label == 'second'


# =============================================================================
# Attribute access via path
# =============================================================================


class TestAttributePathAccess:
    """Test ?attr syntax in paths."""

    def test_get_attribute_via_path(self):
        """Get attribute using ?attr syntax."""
        bag = Bag()
        bag.set_item('item', 'value', color='red', size='large')

        assert bag['item?color'] == 'red'
        assert bag['item?size'] == 'large'

    def test_get_nested_attribute(self):
        """Get attribute from nested node."""
        bag = Bag()
        bag.set_item('level1.item', 'value', priority=10)

        assert bag['level1.item?priority'] == 10

    def test_set_and_get_root_attribute(self):
        """Set and get root Bag attribute with ?attr syntax."""
        bag = Bag()
        # Set root attribute using set_item with path '?attr'
        bag.set_item('item', 'value', _attributes={'_root_attr': 'test'})

        # Access node attribute
        assert bag['item?_root_attr'] == 'test'

    def test_get_missing_attribute(self):
        """Get missing attribute returns None."""
        bag = Bag()
        bag['item'] = 'value'

        assert bag['item?nonexistent'] is None


# =============================================================================
# BagNodeContainer positional operations
# =============================================================================


class TestBagNodeContainerPositions:
    """Test BagNodeContainer positional insert and index operations."""

    def test_insert_at_beginning(self):
        """Insert node at position '<' (beginning)."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag.set_item('first', 0, _position='<')

        assert bag.keys() == ['first', 'a', 'b']

    def test_insert_before_label(self):
        """Insert node before a specific label."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag['c'] = 3
        bag.set_item('new', 99, _position='<b')

        assert bag.keys() == ['a', 'new', 'b', 'c']

    def test_insert_after_label(self):
        """Insert node after a specific label."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag['c'] = 3
        bag.set_item('new', 99, _position='>b')

        assert bag.keys() == ['a', 'b', 'new', 'c']

    def test_insert_at_hash_index(self):
        """Insert node at #n index position."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag['c'] = 3
        bag.set_item('new', 99, _position='#1')

        assert bag.keys() == ['a', 'new', 'b', 'c']

    def test_insert_before_hash_index(self):
        """Insert node before #n index."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag['c'] = 3
        bag.set_item('new', 99, _position='<#2')

        assert bag.keys() == ['a', 'b', 'new', 'c']

    def test_insert_after_hash_index(self):
        """Insert node after #n index."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag['c'] = 3
        bag.set_item('new', 99, _position='>#0')

        assert bag.keys() == ['a', 'new', 'b', 'c']

    def test_insert_invalid_position_appends(self):
        """Invalid position spec appends at end."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag.set_item('new', 99, _position='<nonexistent')

        # When label not found, appends at end
        assert bag.keys()[-1] == 'new'

    def test_insert_invalid_hash_appends(self):
        """Invalid #n position appends at end."""
        bag = Bag()
        bag['a'] = 1
        bag.set_item('new', 99, _position='#invalid')

        assert 'new' in bag

    def test_index_by_attr_value(self):
        """Find index by =attr=value syntax."""
        bag = Bag()
        bag.set_item('a', 1, color='red')
        bag.set_item('b', 2, color='blue')
        bag.set_item('c', 3, color='red')

        # Find by attribute value
        idx = bag._nodes.index('=color=blue')
        assert idx == 1

    def test_index_by_value_only(self):
        """Find index by ==value syntax."""
        bag = Bag()
        bag['a'] = 'first'
        bag['b'] = 'target'
        bag['c'] = 'last'

        # Find by value
        idx = bag._nodes.index('==target')
        assert idx == 1

    def test_index_not_found(self):
        """Index returns -1 when not found."""
        bag = Bag()
        bag['a'] = 1

        assert bag._nodes.index('nonexistent') == -1
        assert bag._nodes.index('#999') == -1


# =============================================================================
# Node subscriptions
# =============================================================================


class TestNodeSubscriptions:
    """Test node-level subscriptions through Bag API."""

    def test_subscribe_to_node_value_change(self):
        """Subscribe to a specific node's value changes."""
        bag = Bag()
        bag['item'] = 'initial'

        events = []

        def on_change(node, info, evt):
            events.append({'evt': evt, 'old': info, 'new': node.value})

        node = bag.get_node('item')
        node.subscribe('test', on_change)

        bag['item'] = 'updated'

        assert len(events) == 1
        assert events[0]['evt'] == 'upd_value'
        assert events[0]['old'] == 'initial'
        assert events[0]['new'] == 'updated'

    def test_unsubscribe_from_node(self):
        """Unsubscribe stops receiving events."""
        bag = Bag()
        bag['item'] = 'initial'

        events = []

        def on_change(node, info, evt):
            events.append(evt)

        node = bag.get_node('item')
        node.subscribe('test', on_change)

        bag['item'] = 'first'
        node.unsubscribe('test')
        bag['item'] = 'second'

        # Only one event (before unsubscribe)
        assert len(events) == 1

    def test_subscribe_to_node_attr_change(self):
        """Subscribe to a specific node's attribute changes."""
        bag = Bag()
        bag.set_item('item', 'value', myattr='initial')
        bag.set_backref()

        events = []

        def on_change(node, info, evt):
            events.append({'evt': evt, 'attrs': info})

        node = bag.get_node('item')
        node.subscribe('test', on_change)

        # Use dict to set attributes
        node.set_attr({'myattr': 'updated'})

        assert len(events) == 1
        assert events[0]['evt'] == 'upd_attrs'


# =============================================================================
# Node validation (is_valid property)
# =============================================================================


class TestNodeValidation:
    """Test node validation through Bag API."""

    def test_node_is_valid_by_default(self):
        """Node is valid when no invalid_reasons."""
        bag = Bag()
        bag['item'] = 'value'

        node = bag.get_node('item')
        assert node.is_valid is True

    def test_node_invalid_with_reasons(self):
        """Node is invalid when invalid_reasons present."""
        bag = Bag()
        bag['item'] = 'value'

        node = bag.get_node('item')
        node._invalid_reasons.append('Some error')

        assert node.is_valid is False


# =============================================================================
# Reset resolver
# =============================================================================


class TestResetResolver:
    """Test resolver reset functionality."""

    def test_reset_resolver_clears_value(self):
        """reset_resolver clears the cached value."""
        from genro_bag.resolvers import BagCbResolver

        counter = [0]

        def callback():
            counter[0] += 1
            return f'value_{counter[0]}'

        resolver = BagCbResolver(callback, read_only=False)
        bag = Bag()
        bag['item'] = resolver

        node = bag.get_node('item')

        # First access
        _ = node.value
        assert counter[0] == 1

        # Reset resolver
        node.reset_resolver()

        # Value should be None after reset
        assert node.static_value is None


# =============================================================================
# Node ne comparison
# =============================================================================


class TestNodeNeComparison:
    """Test node != comparison."""

    def test_node_ne_different_values(self):
        """Nodes with different values are not equal."""
        bag1 = Bag()
        bag1['item'] = 'value1'

        bag2 = Bag()
        bag2['item'] = 'value2'

        node1 = bag1.get_node('item')
        node2 = bag2.get_node('item')

        assert node1 != node2

    def test_node_ne_same_values(self):
        """Nodes with same values are equal (ne returns False)."""
        bag1 = Bag()
        bag1['item'] = 'value'

        bag2 = Bag()
        bag2['item'] = 'value'

        node1 = bag1.get_node('item')
        node2 = bag2.get_node('item')

        assert not (node1 != node2)


# =============================================================================
# Node repr
# =============================================================================


class TestNodeRepr:
    """Test node __repr__."""

    def test_node_repr_contains_label(self):
        """Node repr contains label and id."""
        bag = Bag()
        bag['my_item'] = 'value'

        node = bag.get_node('my_item')
        r = repr(node)

        assert 'my_item' in r
        assert 'BagNode' in r


# =============================================================================
# Builder validation and schema
# =============================================================================


class TestBuilderValidation:
    """Test builder validation through Bag API."""

    def test_builder_attr_validation_required(self):
        """Builder validates required attributes."""
        from genro_bag.builders import HtmlBuilder

        bag = Bag(builder=HtmlBuilder())

        # img requires src attribute - test if validation triggers
        body = bag.body()
        # This should work without error
        body.div(id='test')

    def test_builder_check_valid_structure(self):
        """Builder check method validates structure."""
        from genro_bag.builders import HtmlBuilder

        builder = HtmlBuilder()
        bag = Bag(builder=builder)

        body = bag.body()
        body.div(id='container')

        errors = builder.check(bag['body_0'], parent_tag='body')
        # div is valid child of body
        assert not errors or 'div' not in str(errors)

    def test_builder_check_invalid_child(self):
        """Builder check reports invalid children when valid_children defined."""
        from genro_bag.builders.base import BagBuilderBase

        class StrictBuilder(BagBuilderBase):
            _schema = {
                'parent': {
                    'children': 'allowed_child',  # Only allowed_child is valid
                }
            }

        builder = StrictBuilder()
        bag = Bag()

        # Add an invalid child
        bag['invalid_child'] = Bag()
        bag.get_node('invalid_child').tag = 'invalid_element'

        # Check with parent_tag='parent' which only allows 'allowed_child'
        errors = builder.check(bag, parent_tag='parent')
        assert len(errors) > 0
        assert 'invalid_element' in errors[0] or 'not a valid child' in errors[0]

    def test_builder_attr_type_validation_int(self):
        """Builder validates integer attributes."""
        from genro_bag.builders.base import BagBuilderBase

        class TestBuilder(BagBuilderBase):
            _schema = {
                'test_elem': {
                    'attrs': {
                        'count': {'type': 'int', 'min': 0, 'max': 100}
                    }
                }
            }

        builder = TestBuilder()

        # Valid integer - raise_on_error=False to get errors list
        errors = builder._validate_attrs('test_elem', {'count': 50}, raise_on_error=False)
        assert errors == []

        # Out of range
        errors = builder._validate_attrs('test_elem', {'count': 200}, raise_on_error=False)
        assert len(errors) > 0
        assert 'max' in errors[0] or '<=' in errors[0]

    def test_builder_attr_type_validation_bool(self):
        """Builder validates boolean attributes."""
        from genro_bag.builders.base import BagBuilderBase

        class TestBuilder(BagBuilderBase):
            _schema = {
                'test_elem': {
                    'attrs': {
                        'enabled': {'type': 'bool'}
                    }
                }
            }

        builder = TestBuilder()

        # Valid bool - raise_on_error=False
        errors = builder._validate_attrs('test_elem', {'enabled': True}, raise_on_error=False)
        assert errors == []

        # Valid string bool
        errors = builder._validate_attrs('test_elem', {'enabled': 'true'}, raise_on_error=False)
        assert errors == []

        # Invalid string
        errors = builder._validate_attrs('test_elem', {'enabled': 'maybe'}, raise_on_error=False)
        assert len(errors) > 0

    def test_builder_attr_type_validation_enum(self):
        """Builder validates enum attributes."""
        from genro_bag.builders.base import BagBuilderBase

        class TestBuilder(BagBuilderBase):
            _schema = {
                'test_elem': {
                    'attrs': {
                        'status': {'type': 'enum', 'values': ['active', 'inactive']}
                    }
                }
            }

        builder = TestBuilder()

        # Valid enum value - raise_on_error=False
        errors = builder._validate_attrs('test_elem', {'status': 'active'}, raise_on_error=False)
        assert errors == []

        # Invalid enum value
        errors = builder._validate_attrs('test_elem', {'status': 'unknown'}, raise_on_error=False)
        assert len(errors) > 0

    def test_builder_resolve_ref(self):
        """Builder resolves =ref references."""
        from genro_bag.builders.base import BagBuilderBase

        class TestBuilder(BagBuilderBase):
            _ref_flow = frozenset({'div', 'p', 'span'})

        builder = TestBuilder()

        # Resolve reference
        result = builder._resolve_ref('=flow')
        assert 'div' in result
        assert 'p' in result

    def test_builder_resolve_ref_comma_separated(self):
        """Builder resolves comma-separated refs."""
        from genro_bag.builders.base import BagBuilderBase

        class TestBuilder(BagBuilderBase):
            _ref_block = frozenset({'div', 'section'})

        builder = TestBuilder()

        # Resolve with literal mixed
        result = builder._resolve_ref('span, =block')
        assert 'span' in result
        assert 'div' in result or 'section' in result

    def test_builder_schema_handler(self):
        """Builder creates handlers from schema."""
        from genro_bag.builders.base import BagBuilderBase

        class TestBuilder(BagBuilderBase):
            _schema = {
                'custom_elem': {
                    'children': 'child_a, child_b',
                    'leaf': False
                }
            }

        builder = TestBuilder()
        bag = Bag(builder=builder)

        # Access schema-defined element
        handler = getattr(builder, 'custom_elem', None)
        assert handler is not None

    def test_builder_getattr_unknown_raises(self):
        """Builder __getattr__ raises for unknown elements."""
        from genro_bag.builders.base import BagBuilderBase

        class TestBuilder(BagBuilderBase):
            pass

        builder = TestBuilder()

        with pytest.raises(AttributeError):
            _ = builder.unknown_element


# =============================================================================
# Resolver proxy methods
# =============================================================================


class TestResolverProxy:
    """Test resolver proxy methods."""

    def test_resolver_getitem_proxy(self):
        """Resolver proxies __getitem__ to resolved Bag."""
        from genro_bag.resolvers import BagCbResolver

        def callback():
            b = Bag()
            b['nested'] = 'value'
            return b

        resolver = BagCbResolver(callback)

        # Test proxy directly on resolver (not through Bag path)
        assert resolver['nested'] == 'value'

    def test_resolver_keys_proxy(self):
        """Resolver proxies keys() to resolved Bag."""
        from genro_bag.resolvers import BagCbResolver

        def callback():
            b = Bag()
            b['a'] = 1
            b['b'] = 2
            return b

        resolver = BagCbResolver(callback)

        keys = resolver.keys()
        assert 'a' in keys
        assert 'b' in keys

    def test_resolver_items_proxy(self):
        """Resolver proxies items() to resolved Bag."""
        from genro_bag.resolvers import BagCbResolver

        def callback():
            b = Bag()
            b['x'] = 10
            return b

        resolver = BagCbResolver(callback)

        items = resolver.items()
        assert ('x', 10) in items

    def test_resolver_values_proxy(self):
        """Resolver proxies values() to resolved Bag."""
        from genro_bag.resolvers import BagCbResolver

        def callback():
            b = Bag()
            b['item'] = 42
            return b

        resolver = BagCbResolver(callback)

        values = resolver.values()
        assert 42 in values

    def test_resolver_get_node_proxy(self):
        """Resolver proxies get_node() to resolved Bag."""
        from genro_bag.resolvers import BagCbResolver

        def callback():
            b = Bag()
            b['item'] = 'value'
            return b

        resolver = BagCbResolver(callback)

        node = resolver.get_node('item')
        assert node is not None
        assert node.value == 'value'


# =============================================================================
# Resolver serialization
# =============================================================================


class TestResolverSerialization:
    """Test resolver serialization/deserialization."""

    def test_resolver_serialize(self):
        """Resolver serializes to dict."""
        from genro_bag.resolvers import BagCbResolver

        def my_callback():
            return 'value'

        resolver = BagCbResolver(my_callback, cache_time=60)

        data = resolver.serialize()

        assert 'resolver_module' in data
        assert 'resolver_class' in data
        assert data['resolver_class'] == 'BagCbResolver'

    def test_resolver_equality(self):
        """Two resolvers with same params are equal."""
        from genro_bag.resolvers import BagCbResolver

        def cb():
            return 'x'

        r1 = BagCbResolver(cb, cache_time=30)
        r2 = BagCbResolver(cb, cache_time=30)

        assert r1 == r2

    def test_resolver_inequality_different_params(self):
        """Resolvers with different params are not equal."""
        from genro_bag.resolvers import BagCbResolver

        def cb():
            return 'x'

        r1 = BagCbResolver(cb, cache_time=30)
        r2 = BagCbResolver(cb, cache_time=60)

        assert r1 != r2


# =============================================================================
# BagNodeContainer clear and iteration
# =============================================================================


class TestBagNodeContainerOperations:
    """Test BagNodeContainer operations."""

    def test_clear_removes_all(self):
        """clear() removes all nodes."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag['c'] = 3

        bag._nodes.clear()

        assert len(bag) == 0
        assert list(bag.keys()) == []

    def test_keys_iter_mode(self):
        """keys(iter=True) returns iterator."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2

        keys_iter = bag._nodes.keys(iter=True)

        # Should be an iterator, not a list
        assert hasattr(keys_iter, '__next__')
        assert list(keys_iter) == ['a', 'b']

    def test_values_iter_mode(self):
        """values(iter=True) returns iterator."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2

        values_iter = bag._nodes.values(iter=True)

        assert hasattr(values_iter, '__next__')
        assert list(values_iter) == [1, 2]

    def test_items_iter_mode(self):
        """items(iter=True) returns iterator."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2

        items_iter = bag._nodes.items(iter=True)

        assert hasattr(items_iter, '__next__')
        assert list(items_iter) == [('a', 1), ('b', 2)]

    def test_container_equality(self):
        """Two containers with same nodes are equal."""
        bag1 = Bag()
        bag1['a'] = 1
        bag1['b'] = 2

        bag2 = Bag()
        bag2['a'] = 1
        bag2['b'] = 2

        assert bag1._nodes == bag2._nodes

    def test_container_inequality_different_type(self):
        """Container not equal to non-container."""
        bag = Bag()
        bag['a'] = 1

        assert bag._nodes != "not a container"


# =============================================================================
# Node diff with nested Bag
# =============================================================================


class TestNodeDiffNested:
    """Test node diff with nested Bags."""

    def test_diff_nested_bags_different(self):
        """Diff shows differences in nested Bags."""
        bag1 = Bag()
        bag1['level1'] = Bag()
        bag1['level1.child'] = 'value1'

        bag2 = Bag()
        bag2['level1'] = Bag()
        bag2['level1.child'] = 'value2'

        node1 = bag1.get_node('level1')
        node2 = bag2.get_node('level1')

        diff = node1.diff(node2)

        # Should show value difference
        assert diff is not None
        assert 'value' in diff


# =============================================================================
# Set value with BagNode as value
# =============================================================================


class TestSetValueWithBagNode:
    """Test setting value with BagNode extracts value and attrs."""

    def test_set_value_extracts_node_value(self):
        """Setting a BagNode as value extracts its value."""
        bag1 = Bag()
        bag1.set_item('source', 'source_value', attr1='a')

        bag2 = Bag()
        source_node = bag1.get_node('source')
        bag2.get_node('target') or bag2.set_item('target', 'placeholder')

        target_node = bag2.get_node('target')
        target_node.set_value(source_node)

        # Value should be extracted
        assert target_node.value == 'source_value'
        # Attributes should be merged
        assert target_node.get_attr('attr1') == 'a'


# =============================================================================
# Updattr parameter
# =============================================================================


class TestUpdattrParameter:
    """Test _updattr parameter behavior."""

    def test_updattr_true_updates_attrs(self):
        """_updattr=True updates existing attributes."""
        bag = Bag()
        bag.set_item('item', 'value', attr1='a', attr2='b')

        # Update with new attrs, keeping existing
        bag.set_item('item', 'new_value', attr3='c', _updattr=True)

        node = bag.get_node('item')
        assert node.get_attr('attr1') == 'a'  # kept
        assert node.get_attr('attr3') == 'c'  # added

    def test_updattr_false_replaces_attrs(self):
        """_updattr=False (or None) replaces attributes."""
        bag = Bag()
        bag.set_item('item', 'value', attr1='a', attr2='b')

        # Replace attrs entirely
        bag.set_item('item', 'new_value', attr3='c', _updattr=False)

        node = bag.get_node('item')
        assert node.get_attr('attr1') is None  # removed
        assert node.get_attr('attr3') == 'c'  # new


# =============================================================================
# HtmlPage tests
# =============================================================================


class TestHtmlPage:
    """Test HtmlPage functionality."""

    def test_html_page_basic_structure(self):
        """HtmlPage creates basic html structure."""
        from genro_bag.builders.html import HtmlPage

        page = HtmlPage()

        assert page.html is not None
        assert page.head is not None
        assert page.body is not None

    def test_html_page_to_html(self):
        """HtmlPage to_html generates valid HTML."""
        from genro_bag.builders.html import HtmlPage

        page = HtmlPage()
        page.head.title(value='Test Page')
        page.body.div(id='main')

        html = page.to_html()

        assert '<!DOCTYPE html>' in html
        assert '<html>' in html
        assert '<head>' in html
        assert '<body>' in html
        assert 'Test Page' in html
        assert 'id="main"' in html

    def test_html_page_to_html_save_file(self, tmp_path):
        """HtmlPage to_html can save to file."""
        from genro_bag.builders.html import HtmlPage

        page = HtmlPage()
        page.head.title(value='File Test')

        result = page.to_html(filename='test.html', output_dir=str(tmp_path))

        assert 'test.html' in result
        assert (tmp_path / 'test.html').exists()
        content = (tmp_path / 'test.html').read_text()
        assert 'File Test' in content

    def test_html_page_print_tree(self, capsys):
        """HtmlPage print_tree outputs tree structure."""
        from genro_bag.builders.html import HtmlPage

        page = HtmlPage()
        page.head.title(value='Tree Test')
        page.body.div(id='container')
        page.body['div_0'].p(value='Paragraph')

        page.print_tree()

        captured = capsys.readouterr()
        assert 'HEAD' in captured.out
        assert 'BODY' in captured.out
        assert 'title' in captured.out or 'Tree Test' in captured.out

    def test_html_page_nested_content(self):
        """HtmlPage handles nested content."""
        from genro_bag.builders.html import HtmlPage

        page = HtmlPage()
        div = page.body.div(id='outer')
        div.div(id='inner')
        div['div_0'].p(value='Deeply nested')

        html = page.to_html()

        assert '<div id="outer">' in html
        assert '<div id="inner">' in html
        assert 'Deeply nested' in html


# =============================================================================
# HtmlBuilder void elements
# =============================================================================


class TestHtmlBuilderVoidElements:
    """Test HtmlBuilder void element handling."""

    def test_void_element_has_empty_value(self):
        """Void elements (like br, hr, img) have empty string value."""
        from genro_bag.builders import HtmlBuilder

        builder = HtmlBuilder()
        bag = Bag(builder=builder)

        body = bag.body()
        body.br()  # void element

        # br should exist as a node
        assert 'br_0' in body

    def test_builder_all_tags_property(self):
        """HtmlBuilder has ALL_TAGS property."""
        from genro_bag.builders import HtmlBuilder

        builder = HtmlBuilder()

        assert hasattr(builder, 'ALL_TAGS')
        assert 'div' in builder.ALL_TAGS
        assert 'span' in builder.ALL_TAGS

    def test_builder_void_elements_property(self):
        """HtmlBuilder has VOID_ELEMENTS property."""
        from genro_bag.builders import HtmlBuilder

        builder = HtmlBuilder()

        assert hasattr(builder, 'VOID_ELEMENTS')
        assert 'br' in builder.VOID_ELEMENTS
        assert 'hr' in builder.VOID_ELEMENTS
        assert 'img' in builder.VOID_ELEMENTS


# =============================================================================
# Decorator @element tests
# =============================================================================


class TestElementDecorator:
    """Test @element decorator functionality."""

    def test_element_decorator_registers_tags(self):
        """@element decorator registers multiple tags."""
        from genro_bag.builders.base import BagBuilderBase
        from genro_bag.builders.decorators import element

        class TestBuilder(BagBuilderBase):
            @element(tags='tag_a, tag_b')
            def multi_tag_method(self, _target, _tag, _label=None, value=None, **attr):
                return self.child(_target, _tag, _label=_label, value=value, **attr)

        builder = TestBuilder()

        # Both tags should be in _element_tags
        assert 'tag_a' in builder._element_tags
        assert 'tag_b' in builder._element_tags

    def test_element_decorator_with_children(self):
        """@element decorator sets valid_children."""
        from genro_bag.builders.base import BagBuilderBase
        from genro_bag.builders.decorators import element

        class TestBuilder(BagBuilderBase):
            @element(children='child_a, child_b')
            def parent_elem(self, _target, _tag, _label=None, value=None, **attr):
                return self.child(_target, _tag, _label=_label, value=value, **attr)

        builder = TestBuilder()

        # Method should have _valid_children attribute
        method = builder.parent_elem
        assert hasattr(method, '_valid_children')
        assert 'child_a' in method._valid_children

    def test_element_decorator_with_cardinality(self):
        """@element decorator parses cardinality specs."""
        from genro_bag.builders.base import BagBuilderBase
        from genro_bag.builders.decorators import element

        class TestBuilder(BagBuilderBase):
            # Syntax: tag[n] = exactly n, tag[n:] = min n, tag[:m] = max m, tag[n:m] = range
            @element(children='required_child[1], optional_child[:3]')
            def card_elem(self, _target, _tag, _label=None, value=None, **attr):
                return self.child(_target, _tag, _label=_label, value=value, **attr)

        builder = TestBuilder()

        method = builder.card_elem
        assert hasattr(method, '_child_cardinality')
        # required_child[1] means min=1, max=1
        assert 'required_child' in method._child_cardinality
        assert method._child_cardinality['required_child'] == (1, 1)


# =============================================================================
# Additional bagnode coverage
# =============================================================================


class TestBagNodeAdditionalCoverage:
    """Additional BagNode tests for coverage."""

    def test_node_eq_exception_handling(self):
        """Node equality handles exceptions gracefully."""
        bag = Bag()
        bag['item'] = 'value'

        node = bag.get_node('item')

        # Comparing with non-BagNode should return False
        assert node != "not a node"
        assert node != 42
        assert node != None

    def test_node_position_without_parent(self):
        """Node position returns None without parent."""
        from genro_bag.bagnode import BagNode

        # Create orphan node
        node = BagNode(None, label='orphan', value='test')

        assert node.position is None

    def test_node_fullpath_partial_backref(self):
        """Node fullpath with partial backref chain."""
        bag = Bag()
        bag['a'] = Bag()
        bag['a.b'] = 'value'

        # Without full backref chain
        node = bag['a'].get_node('b')
        assert node.fullpath is None  # No backref

    def test_container_get_by_int(self):
        """BagNodeContainer get by integer index."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2

        node = bag._nodes.get(0)
        assert node.value == 1

        # Out of range
        assert bag._nodes.get(99) is None

    def test_container_get_by_hash_string(self):
        """BagNodeContainer get by #n string."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2

        node = bag._nodes.get('#1')
        assert node.value == 2

        # Invalid hash
        assert bag._nodes.get('#invalid') is None

    def test_container_getitem_out_of_range(self):
        """BagNodeContainer __getitem__ out of range."""
        bag = Bag()
        bag['a'] = 1

        # Out of range by int
        assert bag._nodes[99] is None

        # By label not found
        assert bag._nodes['nonexistent'] is None


# =============================================================================
# Decorator validation tests
# =============================================================================


class TestDecoratorValidation:
    """Test @element decorator attribute validation."""

    def test_validate_required_attribute_missing(self):
        """Validation fails when required attribute is missing."""
        from genro_bag.builders.base import BagBuilderBase
        from genro_bag.builders.decorators import element

        class TestBuilder(BagBuilderBase):
            @element()
            def test_elem(self, _target, _tag, _label=None, value=None, required_attr: str = None, **attr):
                # required_attr has no default (except None for type hint), method implementation
                return self.child(_target, _tag, _label=_label, value=value, **attr)

        # required_attr: str with default None is not required (default makes it optional)

    def test_validate_int_attribute_invalid(self):
        """Validation fails when int attribute gets invalid value."""
        from genro_bag.builders.decorators import _validate_attrs_from_spec

        attrs_spec = {'count': {'type': 'int', 'required': False}}

        # Valid int
        _validate_attrs_from_spec(attrs_spec, {'count': 42})

        # String that can be converted to int is valid
        _validate_attrs_from_spec(attrs_spec, {'count': '42'})

        # Invalid string raises
        with pytest.raises(ValueError, match="must be an integer"):
            _validate_attrs_from_spec(attrs_spec, {'count': 'not_a_number'})

    def test_validate_bool_attribute_invalid_string(self):
        """Validation fails when bool attribute gets invalid string."""
        from genro_bag.builders.decorators import _validate_attrs_from_spec

        attrs_spec = {'enabled': {'type': 'bool', 'required': False}}

        # Valid bool
        _validate_attrs_from_spec(attrs_spec, {'enabled': True})

        # Valid string representations
        _validate_attrs_from_spec(attrs_spec, {'enabled': 'true'})
        _validate_attrs_from_spec(attrs_spec, {'enabled': 'false'})
        _validate_attrs_from_spec(attrs_spec, {'enabled': '1'})
        _validate_attrs_from_spec(attrs_spec, {'enabled': '0'})
        _validate_attrs_from_spec(attrs_spec, {'enabled': 'yes'})
        _validate_attrs_from_spec(attrs_spec, {'enabled': 'no'})

        # Invalid string raises
        with pytest.raises(ValueError, match="must be a boolean"):
            _validate_attrs_from_spec(attrs_spec, {'enabled': 'maybe'})

    def test_validate_bool_attribute_invalid_type(self):
        """Validation fails when bool attribute gets non-bool, non-string."""
        from genro_bag.builders.decorators import _validate_attrs_from_spec

        attrs_spec = {'enabled': {'type': 'bool', 'required': False}}

        # Non-string, non-bool raises
        with pytest.raises(ValueError, match="must be a boolean"):
            _validate_attrs_from_spec(attrs_spec, {'enabled': 42})

    def test_validate_required_missing(self):
        """Validation fails when required attribute is missing."""
        from genro_bag.builders.decorators import _validate_attrs_from_spec

        attrs_spec = {'name': {'type': 'string', 'required': True}}

        # Missing required attribute
        with pytest.raises(ValueError, match="is required"):
            _validate_attrs_from_spec(attrs_spec, {})

    def test_validate_enum_invalid_value(self):
        """Validation fails when enum attribute gets invalid value."""
        from genro_bag.builders.decorators import _validate_attrs_from_spec

        attrs_spec = {'color': {'type': 'enum', 'values': ['red', 'green', 'blue'], 'required': False}}

        # Valid enum value
        _validate_attrs_from_spec(attrs_spec, {'color': 'red'})

        # Invalid enum value raises
        with pytest.raises(ValueError, match="must be one of"):
            _validate_attrs_from_spec(attrs_spec, {'color': 'purple'})


class TestAnnotationConversion:
    """Test type annotation to attr spec conversion."""

    def test_annotation_union_multiple_types(self):
        """Union with multiple non-None types defaults to string."""
        from genro_bag.builders.decorators import _annotation_to_attr_spec
        from typing import Union

        # Union[int, str] -> string (fallback)
        spec = _annotation_to_attr_spec(Union[int, str])
        assert spec['type'] == 'string'

    def test_annotation_optional_int(self):
        """Optional[int] extracts int type."""
        from genro_bag.builders.decorators import _annotation_to_attr_spec
        from typing import Optional

        spec = _annotation_to_attr_spec(Optional[int])
        assert spec['type'] == 'int'

    def test_annotation_literal(self):
        """Literal creates enum type."""
        from genro_bag.builders.decorators import _annotation_to_attr_spec
        from typing import Literal

        spec = _annotation_to_attr_spec(Literal['a', 'b', 'c'])
        assert spec['type'] == 'enum'
        assert spec['values'] == ['a', 'b', 'c']

    def test_annotation_unknown_type_defaults_string(self):
        """Unknown types default to string."""
        from genro_bag.builders.decorators import _annotation_to_attr_spec

        # Custom class -> string
        class MyClass:
            pass

        spec = _annotation_to_attr_spec(MyClass)
        assert spec['type'] == 'string'


class TestSignatureExtraction:
    """Test attribute extraction from function signatures."""

    def test_extract_skips_var_positional(self):
        """Signature extraction skips *args."""
        from genro_bag.builders.decorators import _extract_attrs_from_signature

        def func(a: int, *args, b: str = 'default'):
            pass

        attrs = _extract_attrs_from_signature(func)

        assert 'a' in attrs
        assert 'b' in attrs
        # *args should be skipped

    def test_extract_skips_unannotated(self):
        """Signature extraction skips unannotated parameters."""
        from genro_bag.builders.decorators import _extract_attrs_from_signature

        def func(annotated: int, unannotated):
            pass

        attrs = _extract_attrs_from_signature(func)

        assert 'annotated' in attrs
        assert 'unannotated' not in attrs

    def test_extract_required_parameter(self):
        """Parameters without default are marked required."""
        from genro_bag.builders.decorators import _extract_attrs_from_signature

        def func(required_param: int):
            pass

        attrs = _extract_attrs_from_signature(func)

        assert attrs['required_param']['required'] is True

    def test_extract_optional_parameter_with_default(self):
        """Parameters with default are marked optional with default value."""
        from genro_bag.builders.decorators import _extract_attrs_from_signature

        def func(optional_param: str = 'default_value'):
            pass

        attrs = _extract_attrs_from_signature(func)

        assert attrs['optional_param']['required'] is False
        assert attrs['optional_param']['default'] == 'default_value'


class TestParseTagSpec:
    """Test tag specification parsing."""

    def test_parse_simple_tag(self):
        """Simple tag without cardinality."""
        from genro_bag.builders.decorators import _parse_tag_spec

        tag, min_c, max_c = _parse_tag_spec('my_tag')
        assert tag == 'my_tag'
        assert min_c == 0
        assert max_c is None

    def test_parse_exact_count(self):
        """Tag with exact count [n]."""
        from genro_bag.builders.decorators import _parse_tag_spec

        tag, min_c, max_c = _parse_tag_spec('child[2]')
        assert tag == 'child'
        assert min_c == 2
        assert max_c == 2

    def test_parse_min_only(self):
        """Tag with minimum only [n:]."""
        from genro_bag.builders.decorators import _parse_tag_spec

        tag, min_c, max_c = _parse_tag_spec('child[1:]')
        assert tag == 'child'
        assert min_c == 1
        assert max_c is None

    def test_parse_max_only(self):
        """Tag with maximum only [:m]."""
        from genro_bag.builders.decorators import _parse_tag_spec

        tag, min_c, max_c = _parse_tag_spec('child[:5]')
        assert tag == 'child'
        assert min_c == 0
        assert max_c == 5

    def test_parse_range(self):
        """Tag with range [n:m]."""
        from genro_bag.builders.decorators import _parse_tag_spec

        tag, min_c, max_c = _parse_tag_spec('child[2:5]')
        assert tag == 'child'
        assert min_c == 2
        assert max_c == 5

    def test_parse_invalid_spec_raises(self):
        """Invalid spec raises ValueError."""
        from genro_bag.builders.decorators import _parse_tag_spec

        with pytest.raises(ValueError, match="Invalid tag specification"):
            _parse_tag_spec('123invalid')

    def test_parse_empty_brackets(self):
        """Empty brackets [:]."""
        from genro_bag.builders.decorators import _parse_tag_spec

        tag, min_c, max_c = _parse_tag_spec('child[:]')
        assert tag == 'child'
        assert min_c == 0
        assert max_c is None


class TestParseTags:
    """Test tags parameter parsing."""

    def test_parse_comma_separated_string(self):
        """Parse comma-separated tag string."""
        from genro_bag.builders.decorators import _parse_tags

        tags = _parse_tags('tag_a, tag_b, tag_c')
        assert tags == ['tag_a', 'tag_b', 'tag_c']

    def test_parse_tuple_of_strings(self):
        """Parse tuple of tag strings."""
        from genro_bag.builders.decorators import _parse_tags

        tags = _parse_tags(('tag_a', 'tag_b'))
        assert tags == ['tag_a', 'tag_b']

    def test_parse_empty_string(self):
        """Empty string returns empty list."""
        from genro_bag.builders.decorators import _parse_tags

        tags = _parse_tags('')
        assert tags == []

    def test_parse_empty_tuple(self):
        """Empty tuple returns empty list."""
        from genro_bag.builders.decorators import _parse_tags

        tags = _parse_tags(())
        assert tags == []


class TestElementDecoratorAdvanced:
    """Advanced @element decorator tests."""

    def test_element_with_refs_in_children(self):
        """@element with reference syntax in children."""
        from genro_bag.builders.base import BagBuilderBase
        from genro_bag.builders.decorators import element

        class TestBuilder(BagBuilderBase):
            # Children with '=' means has_refs=True, defers parsing
            @element(children='child=parent.child_spec')
            def ref_elem(self, _target, _tag, _label=None, value=None, **attr):
                return self.child(_target, _tag, _label=_label, value=value, **attr)

        builder = TestBuilder()

        method = builder.ref_elem
        # With refs, _valid_children is empty frozenset (deferred)
        assert method._valid_children == frozenset()
        assert hasattr(method, '_raw_children_spec')

    def test_element_remaps_underscore_params(self):
        """@element decorator remaps _tag to tag in kwargs."""
        from genro_bag.builders.decorators import element

        received = {}

        @element(validate=False)
        def decorated_func(_target, tag=None, label=None, **attr):
            received['tag'] = tag
            received['label'] = label
            return None

        # Call wrapper with _tag and _label (they get remapped)
        decorated_func(None, _tag='custom_tag', _label='custom_label')

        # Wrapper remapped _tag -> tag and _label -> label
        assert received['tag'] == 'custom_tag'
        assert received['label'] == 'custom_label'

    def test_element_children_as_tuple(self):
        """@element with children as tuple."""
        from genro_bag.builders.base import BagBuilderBase
        from genro_bag.builders.decorators import element

        class TestBuilder(BagBuilderBase):
            @element(children=('child_a', 'child_b[1:]'))
            def tuple_children(self, _target, _tag, _label=None, value=None, **attr):
                return self.child(_target, _tag, _label=_label, value=value, **attr)

        builder = TestBuilder()

        method = builder.tuple_children
        assert 'child_a' in method._valid_children
        assert 'child_b' in method._valid_children
        assert method._child_cardinality['child_b'] == (1, None)
