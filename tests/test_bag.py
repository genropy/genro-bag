# Copyright 2025 Softwell S.r.l. - Genropy Team
# Licensed under the Apache License, Version 2.0

"""Tests for Bag - using only public API."""

from genro_bag.bag import Bag


class TestBagSetItem:
    """Test set_item and __setitem__."""

    def test_set_simple_value(self):
        """Set a simple value at root level."""
        bag = Bag()
        bag['foo'] = 42
        assert bag['foo'] == 42

    def test_set_nested_path(self):
        """Set value at nested path creates intermediate bags."""
        bag = Bag()
        bag['a.b.c'] = 'hello'
        assert bag['a.b.c'] == 'hello'

    def test_set_overwrites_existing(self):
        """Setting same path overwrites value."""
        bag = Bag()
        bag['x'] = 1
        bag['x'] = 2
        assert bag['x'] == 2

    def test_set_multiple_keys(self):
        """Set multiple keys at same level."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag['c'] = 3
        assert bag['a'] == 1
        assert bag['b'] == 2
        assert bag['c'] == 3


class TestBagGetItem:
    """Test get_item and __getitem__."""

    def test_get_existing_value(self):
        """Get existing value."""
        bag = Bag()
        bag['foo'] = 'bar'
        assert bag['foo'] == 'bar'

    def test_get_missing_returns_none(self):
        """Get missing key returns None."""
        bag = Bag()
        assert bag['missing'] is None

    def test_get_nested_path(self):
        """Get value at nested path."""
        bag = Bag()
        bag['a.b.c'] = 100
        assert bag['a.b.c'] == 100

    def test_get_partial_path_returns_bag(self):
        """Get intermediate path returns nested Bag."""
        bag = Bag()
        bag['a.b.c'] = 'leaf'
        result = bag['a.b']
        assert isinstance(result, Bag)
        assert result['c'] == 'leaf'


class TestBagPosition:
    """Test set_item with _position parameter."""

    def test_position_append_default(self):
        """Default position appends at end."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag['c'] = 3
        assert bag.keys() == ['a', 'b', 'c']

    def test_position_append_explicit(self):
        """Position '>' appends at end."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag.set_item('last', 'X', _position='>')
        assert bag.keys() == ['a', 'b', 'last']

    def test_position_prepend(self):
        """Position '<' inserts at beginning."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag.set_item('first', 'X', _position='<')
        assert bag.keys() == ['first', 'a', 'b']

    def test_position_index(self):
        """Position '#n' inserts at index n."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag['c'] = 3
        bag.set_item('mid', 'X', _position='#1')
        assert bag.keys() == ['a', 'mid', 'b', 'c']

    def test_position_index_invalid(self):
        """Position '#invalid' appends at end (fallback)."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag.set_item('new', 'X', _position='#invalid')
        assert bag.keys() == ['a', 'b', 'new']

    def test_position_after_label(self):
        """Position '>label' inserts after label."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag['c'] = 3
        bag.set_item('after_a', 'X', _position='>a')
        assert bag.keys() == ['a', 'after_a', 'b', 'c']

    def test_position_after_missing_label(self):
        """Position '>missing' appends at end (fallback)."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag.set_item('new', 'X', _position='>missing')
        assert bag.keys() == ['a', 'b', 'new']

    def test_position_before_label(self):
        """Position '<label' inserts before label."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag['c'] = 3
        bag.set_item('before_c', 'X', _position='<c')
        assert bag.keys() == ['a', 'b', 'before_c', 'c']

    def test_position_before_missing_label(self):
        """Position '<missing' appends at end (fallback)."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag.set_item('new', 'X', _position='<missing')
        assert bag.keys() == ['a', 'b', 'new']

    def test_position_before_index(self):
        """Position '<#n' inserts before index n."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag['c'] = 3
        bag.set_item('new', 'X', _position='<#2')
        assert bag.keys() == ['a', 'b', 'new', 'c']

    def test_position_before_index_invalid(self):
        """Position '<#invalid' appends at end (fallback)."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag.set_item('new', 'X', _position='<#invalid')
        assert bag.keys() == ['a', 'b', 'new']

    def test_position_after_index(self):
        """Position '>#n' inserts after index n."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag['c'] = 3
        bag.set_item('new', 'X', _position='>#0')
        assert bag.keys() == ['a', 'new', 'b', 'c']

    def test_position_after_index_invalid(self):
        """Position '>#invalid' appends at end (fallback)."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag.set_item('new', 'X', _position='>#invalid')
        assert bag.keys() == ['a', 'b', 'new']

    def test_position_unknown_syntax(self):
        """Unknown position syntax appends at end (fallback)."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag.set_item('new', 'X', _position='unknown')
        assert bag.keys() == ['a', 'b', 'new']


class TestBagAttributes:
    """Test node attributes with ?attr syntax."""

    def test_set_and_get_attribute(self):
        """Set attribute and get it with ?attr syntax."""
        bag = Bag()
        bag.set_item('x', 42, _attributes={'type': 'int'})
        assert bag['x'] == 42
        assert bag.get('x?type') == 'int'

    def test_get_missing_attribute(self):
        """Get missing attribute returns None."""
        bag = Bag()
        bag['x'] = 42
        assert bag.get('x?missing') is None

    def test_set_multiple_attributes(self):
        """Set multiple attributes."""
        bag = Bag()
        bag.set_item('data', 'hello', _attributes={'type': 'str', 'size': 5})
        assert bag.get('data?type') == 'str'
        assert bag.get('data?size') == 5

    def test_set_attributes_via_kwargs(self):
        """Set attributes via kwargs."""
        bag = Bag()
        bag.set_item('item', 100, dtype='number', readonly=True)
        assert bag.get('item?dtype') == 'number'
        assert bag.get('item?readonly') is True


class TestBagIndexAccess:
    """Test access with #n index syntax."""

    def test_get_by_index(self):
        """Get value by #n index."""
        bag = Bag()
        bag['a'] = 10
        bag['b'] = 20
        bag['c'] = 30
        assert bag.get('#0') == 10
        assert bag.get('#1') == 20
        assert bag.get('#2') == 30

    def test_get_by_invalid_index(self):
        """Get by out of range index returns default."""
        bag = Bag()
        bag['a'] = 1
        assert bag.get('#99') is None

    def test_position_before_index(self):
        """Position '<#n' inserts before index n."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag['c'] = 3
        bag.set_item('new', 'X', _position='<#2')
        assert bag.keys() == ['a', 'b', 'new', 'c']

    def test_position_after_index(self):
        """Position '>#n' inserts after index n."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag['c'] = 3
        bag.set_item('new', 'X', _position='>#0')
        assert bag.keys() == ['a', 'new', 'b', 'c']


class TestBagPopAndDelete:
    """Test pop and delete operations."""

    def test_pop_existing(self):
        """Pop existing key returns value."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        result = bag.pop('a')
        assert result == 1
        assert bag.keys() == ['b']

    def test_pop_missing_returns_default(self):
        """Pop missing key returns default."""
        bag = Bag()
        bag['a'] = 1
        result = bag.pop('missing', 'default')
        assert result == 'default'

    def test_pop_nested_path(self):
        """Pop from nested path."""
        bag = Bag()
        bag['a.b.c'] = 'value'
        result = bag.pop('a.b.c')
        assert result == 'value'
        assert bag['a.b.c'] is None

    def test_del_item(self):
        """Delete item with del."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        del bag['a']
        assert bag.keys() == ['b']


class TestBagClear:
    """Test clear operation."""

    def test_clear_removes_all(self):
        """Clear removes all nodes."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag['c'] = 3
        bag.clear()
        assert len(bag) == 0
        assert bag.keys() == []


class TestBagContains:
    """Test __contains__ (in operator)."""

    def test_contains_existing(self):
        """Existing key returns True."""
        bag = Bag()
        bag['a'] = 1
        assert 'a' in bag

    def test_contains_missing(self):
        """Missing key returns False."""
        bag = Bag()
        bag['a'] = 1
        assert 'missing' not in bag

    def test_contains_nested_path(self):
        """Nested path works with in."""
        bag = Bag()
        bag['a.b.c'] = 1
        assert 'a.b.c' in bag
        assert 'a.b.x' not in bag


class TestBagIteration:
    """Test iteration and len."""

    def test_len(self):
        """Len returns number of direct children."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag['c.d'] = 3
        assert len(bag) == 3  # a, b, c

    def test_iter_yields_nodes(self):
        """Iteration yields BagNodes."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        labels = [node.label for node in bag]
        assert labels == ['a', 'b']

    def test_values(self):
        """Values returns list of values."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        assert bag.values() == [1, 2]

    def test_items(self):
        """Items returns list of (label, value) tuples."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        assert bag.items() == [('a', 1), ('b', 2)]


class TestBagCall:
    """Test __call__ syntax."""

    def test_call_no_arg_returns_keys(self):
        """Calling bag() returns keys."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        assert bag() == ['a', 'b']

    def test_call_with_path_returns_value(self):
        """Calling bag(path) returns value."""
        bag = Bag()
        bag['a.b'] = 42
        assert bag('a.b') == 42


class TestBagIndexByAttribute:
    """Test index lookup by attribute value (?attr=value) and by value (?=value)."""

    def test_index_by_attribute_value(self):
        """Find node index by attribute value with ?attr=value syntax."""
        bag = Bag()
        bag.set_item('a', 10, color='red')
        bag.set_item('b', 20, color='blue')
        bag.set_item('c', 30, color='green')
        # Use position syntax to find by attribute
        bag.set_item('new', 'X', _position='<?color=blue')
        assert bag.keys() == ['a', 'new', 'b', 'c']

    def test_index_by_attribute_value_after(self):
        """Insert after node found by attribute value."""
        bag = Bag()
        bag.set_item('a', 10, color='red')
        bag.set_item('b', 20, color='blue')
        bag.set_item('c', 30, color='green')
        bag.set_item('new', 'X', _position='>?color=blue')
        assert bag.keys() == ['a', 'b', 'new', 'c']

    def test_index_by_value(self):
        """Find node index by value with ?=value syntax."""
        bag = Bag()
        bag['a'] = 'apple'
        bag['b'] = 'banana'
        bag['c'] = 'cherry'
        bag.set_item('new', 'X', _position='<?=banana')
        assert bag.keys() == ['a', 'new', 'b', 'c']

    def test_index_by_value_after(self):
        """Insert after node found by value."""
        bag = Bag()
        bag['a'] = 'apple'
        bag['b'] = 'banana'
        bag['c'] = 'cherry'
        bag.set_item('new', 'X', _position='>?=banana')
        assert bag.keys() == ['a', 'b', 'new', 'c']

    def test_index_by_attribute_not_found(self):
        """Attribute value not found appends at end."""
        bag = Bag()
        bag.set_item('a', 10, color='red')
        bag.set_item('b', 20, color='blue')
        bag.set_item('new', 'X', _position='<?color=yellow')
        assert bag.keys() == ['a', 'b', 'new']

    def test_index_by_value_not_found(self):
        """Value not found appends at end."""
        bag = Bag()
        bag['a'] = 'apple'
        bag['b'] = 'banana'
        bag.set_item('new', 'X', _position='<?=orange')
        assert bag.keys() == ['a', 'b', 'new']


class TestBagBackref:
    """Test backref mode: set_backref, del_parent_ref, clear_backref."""

    def test_set_backref_enables_backref_mode(self):
        """set_backref enables backref mode."""
        bag = Bag()
        bag['a'] = 1
        assert bag.backref is False
        bag.set_backref()
        assert bag.backref is True

    def test_set_backref_sets_parent_bag_on_nodes(self):
        """set_backref sets parent_bag reference on all existing nodes."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
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
        bag['a.b.c'] = 'deep'
        bag.set_backref()
        assert bag.backref is True
        inner = bag['a']
        assert inner.backref is True
        bag.clear_backref()
        assert bag.backref is False
        assert inner.backref is False

    def test_clear_backref_clears_parent_bag_on_nodes(self):
        """clear_backref sets parent_bag to None on all nodes."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag.set_backref()
        bag.clear_backref()
        for node in bag:
            assert node.parent_bag is None


class TestBagSubscribe:
    """Test subscribe and unsubscribe for events."""

    def test_subscribe_enables_backref(self):
        """subscribe automatically enables backref mode."""
        bag = Bag()
        bag['a'] = 1
        assert bag.backref is False
        bag.subscribe('test', any=lambda **kw: None)
        assert bag.backref is True

    def test_subscribe_update_callback(self):
        """subscribe to update events receives callback on value change."""
        bag = Bag()
        bag['a'] = 1
        events = []
        bag.subscribe('test', update=lambda **kw: events.append(('upd', kw)))
        bag['a'] = 2
        assert len(events) == 1
        assert events[0][0] == 'upd'
        assert events[0][1]['evt'] == 'upd_value'

    def test_subscribe_insert_callback(self):
        """subscribe to insert events receives callback on new node."""
        bag = Bag()
        events = []
        bag.subscribe('test', insert=lambda **kw: events.append(('ins', kw)))
        bag['new'] = 'value'
        assert len(events) == 1
        assert events[0][0] == 'ins'
        assert events[0][1]['evt'] == 'ins'

    def test_subscribe_delete_callback(self):
        """subscribe to delete events receives callback on node removal."""
        bag = Bag()
        bag['a'] = 1
        events = []
        bag.subscribe('test', delete=lambda **kw: events.append(('del', kw)))
        del bag['a']
        assert len(events) == 1
        assert events[0][0] == 'del'
        assert events[0][1]['evt'] == 'del'

    def test_subscribe_any_callback(self):
        """subscribe with any=callback subscribes to all events."""
        bag = Bag()
        events = []
        bag.subscribe('test', any=lambda **kw: events.append(kw['evt']))
        bag['a'] = 1  # insert
        bag['a'] = 2  # update
        del bag['a']  # delete
        assert events == ['ins', 'upd_value', 'del']

    def test_unsubscribe_update(self):
        """unsubscribe removes update callback."""
        bag = Bag()
        bag['a'] = 1
        events = []
        bag.subscribe('test', update=lambda **kw: events.append('upd'))
        bag['a'] = 2
        assert len(events) == 1
        bag.unsubscribe('test', update=True)
        bag['a'] = 3
        assert len(events) == 1  # no new event

    def test_unsubscribe_any(self):
        """unsubscribe with any=True removes all callbacks."""
        bag = Bag()
        events = []
        bag.subscribe('test', any=lambda **kw: events.append(kw['evt']))
        bag['a'] = 1
        assert len(events) == 1
        bag.unsubscribe('test', any=True)
        bag['a'] = 2
        del bag['a']
        assert len(events) == 1  # no new events

    def test_multiple_subscribers(self):
        """Multiple subscribers receive events independently."""
        bag = Bag()
        events1 = []
        events2 = []
        bag.subscribe('sub1', insert=lambda **kw: events1.append('ins'))
        bag.subscribe('sub2', insert=lambda **kw: events2.append('ins'))
        bag['a'] = 1
        assert events1 == ['ins']
        assert events2 == ['ins']


class TestBagEventPropagation:
    """Test event propagation up the hierarchy."""

    def test_insert_propagates_to_parent(self):
        """Insert event propagates up to parent bag."""
        root = Bag()
        root['child'] = Bag()
        root.set_backref()
        events = []
        root.subscribe('test', insert=lambda **kw: events.append(kw['pathlist']))
        root['child']['new'] = 'value'
        assert len(events) == 1
        assert events[0] == ['child']

    def test_update_propagates_to_parent(self):
        """Update event propagates up to parent bag."""
        root = Bag()
        root['child.item'] = 1
        root.set_backref()
        events = []
        root.subscribe('test', update=lambda **kw: events.append(kw['pathlist']))
        root['child.item'] = 2
        assert len(events) == 1
        # pathlist contains the full path from subscribed bag to changed node
        assert events[0] == ['child', 'item']

    def test_delete_propagates_to_parent(self):
        """Delete event propagates up to parent bag."""
        root = Bag()
        root['child.item'] = 1
        root.set_backref()
        events = []
        root.subscribe('test', delete=lambda **kw: events.append(kw['pathlist']))
        del root['child.item']
        assert len(events) == 1
        # pathlist for delete indicates "where" (parent), not "what" (node)
        assert events[0] == ['child']


class TestBagGetNodes:
    """Test get_nodes method and nodes property."""

    def test_get_nodes_returns_all_nodes(self):
        """get_nodes without condition returns all nodes."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag['c'] = 3
        nodes = bag.get_nodes()
        assert len(nodes) == 3
        assert [n.label for n in nodes] == ['a', 'b', 'c']

    def test_get_nodes_with_condition(self):
        """get_nodes with condition filters nodes."""
        bag = Bag()
        bag.set_item('a', 1, even=False)
        bag.set_item('b', 2, even=True)
        bag.set_item('c', 3, even=False)
        bag.set_item('d', 4, even=True)
        nodes = bag.get_nodes(condition=lambda n: n.get_attr('even'))
        assert len(nodes) == 2
        assert [n.label for n in nodes] == ['b', 'd']

    def test_nodes_property(self):
        """nodes property returns same as get_nodes()."""
        bag = Bag()
        bag['x'] = 10
        bag['y'] = 20
        assert bag.nodes == bag.get_nodes()


class TestBagDigest:
    """Test digest method."""

    def test_digest_default(self):
        """digest without args returns #k,#v,#a."""
        bag = Bag()
        bag.set_item('a', 1, x=10)
        bag.set_item('b', 2, y=20)
        result = bag.digest()
        assert len(result) == 2
        assert result[0] == ('a', 1, {'x': 10})
        assert result[1] == ('b', 2, {'y': 20})

    def test_digest_keys_only(self):
        """digest #k returns list of labels."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        result = bag.digest('#k')
        assert result == ['a', 'b']

    def test_digest_values_only(self):
        """digest #v returns list of values."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        result = bag.digest('#v')
        assert result == [1, 2]

    def test_digest_keys_and_values(self):
        """digest #k,#v returns tuples."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        result = bag.digest('#k,#v')
        assert result == [('a', 1), ('b', 2)]

    def test_digest_attribute(self):
        """digest #a.attrname returns specific attribute."""
        bag = Bag()
        bag.set_item('x', 'file0', created_by='Jack')
        bag.set_item('y', 'file1', created_by='Mark')
        result = bag.digest('#k,#a.created_by')
        assert result == [('x', 'Jack'), ('y', 'Mark')]

    def test_digest_all_attributes(self):
        """digest #a returns all attributes dict."""
        bag = Bag()
        bag.set_item('a', 1, x=10, y=20)
        result = bag.digest('#a')
        assert result == [{'x': 10, 'y': 20}]

    def test_digest_with_condition(self):
        """digest with condition filters nodes."""
        bag = Bag()
        bag.set_item('a', 1, active=True)
        bag.set_item('b', 2, active=False)
        bag.set_item('c', 3, active=True)
        result = bag.digest('#k', condition=lambda n: n.get_attr('active'))
        assert result == ['a', 'c']

    def test_digest_with_path(self):
        """digest with path:what syntax."""
        bag = Bag()
        bag['letters.a'] = 'alpha'
        bag['letters.b'] = 'beta'
        result = bag.digest('letters:#k,#v')
        assert result == [('a', 'alpha'), ('b', 'beta')]

    def test_digest_as_columns(self):
        """digest with as_columns=True returns list of lists."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        result = bag.digest('#k,#v', as_columns=True)
        assert result == [['a', 'b'], [1, 2]]

    def test_digest_callable(self):
        """digest with callable applies function to each node."""
        bag = Bag()
        bag['a'] = 10
        bag['b'] = 20
        result = bag.digest([lambda n: n.value * 2])
        assert result == [20, 40]

    def test_query_iter(self):
        """query with iter=True returns generator."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag['c'] = 3
        result = bag.query('#k', iter=True)
        # Should be a generator, not a list
        assert hasattr(result, '__next__')
        assert list(result) == ['a', 'b', 'c']

    def test_query_deep(self):
        """query with deep=True traverses recursively."""
        bag = Bag()
        bag['a'] = 1
        bag['b.c'] = 2
        bag['b.d'] = 3
        result = bag.query('#p', deep=True)
        assert 'a' in result
        assert 'b' in result
        assert 'b.c' in result
        assert 'b.d' in result

    def test_query_deep_with_values(self):
        """query deep with path and value."""
        bag = Bag()
        bag['a'] = 1
        bag['b.c'] = 2
        result = bag.query('#p,#v', deep=True)
        # Should have tuples of (path, value)
        result_dict = dict(result)
        assert result_dict['a'] == 1
        assert result_dict['b.c'] == 2
        # 'b' is a Bag, not a leaf value
        assert 'b' in result_dict

    def test_query_deep_with_condition(self):
        """query deep with condition filters nodes."""
        bag = Bag()
        bag['a'] = 1
        bag['b.c'] = 2
        bag['b.d'] = 3
        # Only leaf nodes (not Bag values)
        result = bag.query('#p,#v', deep=True,
                          condition=lambda n: not isinstance(n.value, Bag))
        result_dict = dict(result)
        assert 'a' in result_dict
        assert 'b.c' in result_dict
        assert 'b.d' in result_dict
        assert 'b' not in result_dict  # 'b' is a Bag, filtered out

    def test_query_deep_iter(self):
        """query deep with iter returns generator."""
        bag = Bag()
        bag['a'] = 1
        bag['b.c'] = 2
        result = bag.query('#p', deep=True, iter=True)
        assert hasattr(result, '__next__')
        paths = list(result)
        assert 'a' in paths
        assert 'b.c' in paths

    def test_query_path_specifier(self):
        """query with #p returns path."""
        bag = Bag()
        bag['x'] = 1
        bag['y'] = 2
        result = bag.query('#p')
        assert result == ['x', 'y']

    def test_query_node_specifier(self):
        """query with #n returns the node itself."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        result = bag.query('#n')
        assert len(result) == 2
        assert result[0].label == 'a'
        assert result[1].label == 'b'


class TestBagColumns:
    """Test columns method."""

    def test_columns_from_values(self):
        """columns extracts values as columns."""
        bag = Bag()
        bag['row1'] = Bag({'name': 'Alice', 'age': 30})
        bag['row2'] = Bag({'name': 'Bob', 'age': 25})
        result = bag.columns('name,age')
        # columns uses digest on values, so it extracts from each row's value
        assert len(result) == 2

    def test_columns_attr_mode(self):
        """columns with attr_mode extracts attributes."""
        bag = Bag()
        bag.set_item('a', 1, x=10, y=20)
        bag.set_item('b', 2, x=30, y=40)
        result = bag.columns('x,y', attr_mode=True)
        assert result == [[10, 30], [20, 40]]


class TestBagWalk:
    """Test walk method."""

    def test_walk_generator_flat(self):
        """walk() without callback returns generator of (path, node)."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag['c'] = 3
        result = list(bag.walk())
        assert len(result) == 3
        assert result[0] == ('a', bag.get_node('a'))
        assert result[1] == ('b', bag.get_node('b'))
        assert result[2] == ('c', bag.get_node('c'))

    def test_walk_generator_nested(self):
        """walk() traverses nested Bags depth-first."""
        bag = Bag()
        bag['a'] = 1
        bag['b.x'] = 10
        bag['b.y'] = 20
        bag['c'] = 3
        result = [(path, node.value) for path, node in bag.walk()]
        # Should be: a, b (Bag), b.x, b.y, c
        assert len(result) == 5
        assert result[0] == ('a', 1)
        assert result[1][0] == 'b'  # b is a Bag
        assert result[2] == ('b.x', 10)
        assert result[3] == ('b.y', 20)
        assert result[4] == ('c', 3)

    def test_walk_generator_deeply_nested(self):
        """walk() handles deeply nested structures."""
        bag = Bag()
        bag['a.b.c.d'] = 'deep'
        result = [(path, node.value) for path, node in bag.walk()]
        # a (Bag), a.b (Bag), a.b.c (Bag), a.b.c.d
        assert len(result) == 4
        paths = [path for path, _ in result]
        assert paths == ['a', 'a.b', 'a.b.c', 'a.b.c.d']
        assert result[-1] == ('a.b.c.d', 'deep')

    def test_walk_generator_early_exit(self):
        """walk() generator supports early exit via break."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag['c'] = 3
        bag['d'] = 4
        found = None
        for path, node in bag.walk():
            if node.value == 2:
                found = path
                break
        assert found == 'b'

    def test_walk_callback_basic(self):
        """walk() with callback calls it for each node."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        visited = []
        bag.walk(lambda n: visited.append(n.label))
        assert visited == ['a', 'b']

    def test_walk_callback_nested(self):
        """walk() with callback traverses nested Bags."""
        bag = Bag()
        bag['a'] = 1
        bag['b.x'] = 10
        bag['b.y'] = 20
        visited = []
        bag.walk(lambda n: visited.append(n.label))
        assert visited == ['a', 'b', 'x', 'y']

    def test_walk_callback_early_exit(self):
        """walk() with callback supports early exit."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag['c'] = 3

        def find_b(node):
            if node.value == 2:
                return node  # truthy return stops walk
        result = bag.walk(find_b)
        assert result.value == 2
        assert result.label == 'b'

    def test_walk_callback_pathlist(self):
        """walk() with _pathlist tracks path."""
        bag = Bag()
        bag['a.b.c'] = 'deep'
        paths = []

        def collect_paths(node, _pathlist=None):
            paths.append(_pathlist)
        bag.walk(collect_paths, _pathlist=[])
        assert paths == [['a'], ['a', 'b'], ['a', 'b', 'c']]

    def test_walk_callback_indexlist(self):
        """walk() with _indexlist tracks indices."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag['c'] = 3
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
                return 'resolved_value'

        bag = Bag()
        resolver = SimpleResolver()
        bag.set_resolver('data', resolver)

        assert 'data' in bag
        node = bag.get_node('data')
        assert node.resolver is resolver

    def test_get_resolver_returns_resolver(self):
        """get_resolver returns the resolver from a node."""
        from genro_bag import BagResolver

        class SimpleResolver(BagResolver):
            def load(self):
                return 'resolved_value'

        bag = Bag()
        resolver = SimpleResolver()
        bag.set_resolver('data', resolver)

        result = bag.get_resolver('data')
        assert result is resolver

    def test_get_resolver_nonexistent_path_returns_none(self):
        """get_resolver returns None for nonexistent path."""
        bag = Bag()
        result = bag.get_resolver('nonexistent')
        assert result is None

    def test_get_resolver_no_resolver_returns_none(self):
        """get_resolver returns None if node has no resolver."""
        bag = Bag()
        bag['data'] = 'value'
        result = bag.get_resolver('data')
        assert result is None

    def test_set_resolver_nested_path(self):
        """set_resolver works with nested paths."""
        from genro_bag import BagResolver

        class SimpleResolver(BagResolver):
            def load(self):
                return 'nested_resolved'

        bag = Bag()
        resolver = SimpleResolver()
        bag.set_resolver('a.b.c', resolver)

        assert bag.get_resolver('a.b.c') is resolver
        assert bag.get_resolver('a') is None
        assert bag.get_resolver('a.b') is None

    def test_set_resolver_replaces_existing(self):
        """set_resolver replaces existing resolver."""
        from genro_bag import BagResolver

        class Resolver1(BagResolver):
            def load(self):
                return 'first'

        class Resolver2(BagResolver):
            def load(self):
                return 'second'

        bag = Bag()
        resolver1 = Resolver1()
        resolver2 = Resolver2()

        bag.set_resolver('data', resolver1)
        assert bag.get_resolver('data') is resolver1

        bag.set_resolver('data', resolver2)
        assert bag.get_resolver('data') is resolver2


class TestBagFillFrom:
    """Tests for fill_from method."""

    def test_fill_from_dict_simple(self):
        """fill_from with dict populates bag."""
        bag = Bag()
        bag.fill_from({'a': 1, 'b': 2})
        assert bag['a'] == 1
        assert bag['b'] == 2

    def test_fill_from_dict_nested(self):
        """fill_from with nested dict creates nested bags."""
        bag = Bag()
        bag.fill_from({'x': {'y': {'z': 'deep'}}})
        assert bag['x.y.z'] == 'deep'
        assert isinstance(bag['x'], Bag)

    def test_fill_from_dict_clears_existing(self):
        """fill_from clears existing content."""
        bag = Bag()
        bag['old'] = 'data'
        bag.fill_from({'new': 'value'})
        assert 'old' not in bag
        assert bag['new'] == 'value'

    def test_fill_from_bag(self):
        """fill_from with another Bag copies nodes."""
        source = Bag()
        source.set_item('a', 1, attr1='x')
        source.set_item('b', 2, attr2='y')

        target = Bag()
        target.fill_from(source)

        assert target['a'] == 1
        assert target['b'] == 2
        node_a = target.get_node('a')
        assert node_a.get_attr('attr1') == 'x'

    def test_fill_from_bag_deep_copy(self):
        """fill_from does deep copy of nested bags."""
        source = Bag()
        source['nested.value'] = 'original'

        target = Bag()
        target.fill_from(source)

        # Modify source, target should be unchanged
        source['nested.value'] = 'modified'
        assert target['nested.value'] == 'original'

    def test_fill_from_file_tytx_json(self, tmp_path):
        """fill_from loads .bag.json file."""
        # Create source bag and save
        source = Bag()
        source['name'] = 'test'
        source['count'] = 42
        filepath = tmp_path / 'data.bag.json'
        source.to_tytx(filename=str(filepath))

        # Load into new bag
        target = Bag()
        target.fill_from(str(filepath))

        assert target['name'] == 'test'
        assert target['count'] == 42

    def test_fill_from_file_tytx_msgpack(self, tmp_path):
        """fill_from loads .bag.mp file."""
        # Create source bag and save
        source = Bag()
        source['name'] = 'binary'
        source['value'] = 123
        filepath = tmp_path / 'data.bag.mp'
        source.to_tytx(transport='msgpack', filename=str(filepath))

        # Load into new bag
        target = Bag()
        target.fill_from(str(filepath))

        assert target['name'] == 'binary'
        assert target['value'] == 123

    def test_fill_from_file_xml(self, tmp_path):
        """fill_from loads .xml file."""
        # Create source bag and save
        source = Bag()
        source['item'] = 'xml_value'
        xml_content = source.to_xml()
        filepath = tmp_path / 'data.xml'
        filepath.write_text(xml_content)

        # Load into new bag
        target = Bag()
        target.fill_from(str(filepath))

        assert target['item'] == 'xml_value'

    def test_fill_from_file_not_found(self):
        """fill_from raises FileNotFoundError for missing file."""
        import pytest

        bag = Bag()
        with pytest.raises(FileNotFoundError):
            bag.fill_from('/nonexistent/path/file.bag.json')

    def test_fill_from_file_unknown_extension(self, tmp_path):
        """fill_from raises ValueError for unknown extension."""
        import pytest

        filepath = tmp_path / 'data.unknown'
        filepath.write_text('content')

        bag = Bag()
        with pytest.raises(ValueError, match='Unrecognized file extension'):
            bag.fill_from(str(filepath))

    def test_bag_constructor_with_dict(self):
        """Bag constructor accepts dict source."""
        bag = Bag({'a': 1, 'b': {'c': 2}})
        assert bag['a'] == 1
        assert bag['b.c'] == 2

    def test_bag_constructor_with_file(self, tmp_path):
        """Bag constructor accepts file path."""
        source = Bag()
        source['key'] = 'from_file'
        filepath = tmp_path / 'init.bag.json'
        source.to_tytx(filename=str(filepath))

        bag = Bag(str(filepath))
        assert bag['key'] == 'from_file'


class TestBagSubscriberLog:
    """Test subscriber logging all operations on a Bag."""

    def test_subscriber_logs_all_operations(self):
        """Subscriber logs insert, update, delete operations."""
        bag = Bag()
        log = []

        def logger(**kw):
            log.append({
                'evt': kw.get('evt'),
                'pathlist': kw.get('pathlist'),
                'node_label': kw.get('node').label if kw.get('node') else None,
                'oldvalue': kw.get('oldvalue'),
            })

        bag.subscribe('logger', any=logger)

        # Insert operations
        bag['name'] = 'Alice'
        bag['age'] = 30
        bag['address.city'] = 'Rome'  # Creates 'address' Bag + 'city' inside

        # Update operations
        bag['name'] = 'Bob'
        bag['age'] = 31

        # Delete operations
        del bag['age']

        # Verify we have the expected event types
        insert_events = [e for e in log if e['evt'] == 'ins']
        update_events = [e for e in log if e['evt'] == 'upd_value']
        delete_events = [e for e in log if e['evt'] == 'del']

        # 4 inserts: name, age, address (Bag), city - no duplicates
        assert len(insert_events) == 4

        # 2 updates: name Alice->Bob, age 30->31
        assert len(update_events) == 2

        # 1 delete: age
        assert len(delete_events) == 1

        # Check inserts in order
        assert insert_events[0]['node_label'] == 'name'
        assert insert_events[1]['node_label'] == 'age'
        assert insert_events[2]['node_label'] == 'address'
        assert insert_events[3]['node_label'] == 'city'

        # Check updates have oldvalue
        name_update = [e for e in update_events if e['node_label'] == 'name'][0]
        assert name_update['oldvalue'] == 'Alice'

        age_update = [e for e in update_events if e['node_label'] == 'age'][0]
        assert age_update['oldvalue'] == 30

        # Check delete is for 'age'
        assert delete_events[0]['node_label'] == 'age'

    def test_subscriber_logs_nested_operations(self):
        """Subscriber logs operations on nested bags."""
        root = Bag()
        log = []

        def logger(**kw):
            log.append({
                'evt': kw.get('evt'),
                'pathlist': kw.get('pathlist'),
            })

        root.subscribe('logger', any=logger)

        # Create nested structure
        root['level1.level2.level3'] = 'deep_value'

        # Modify nested value
        root['level1.level2.level3'] = 'updated_value'

        # Delete nested
        del root['level1.level2.level3']

        # Find the update event
        update_events = [e for e in log if e['evt'] == 'upd_value']
        assert len(update_events) == 1
        assert update_events[0]['pathlist'] == ['level1', 'level2', 'level3']

        # Find delete event
        delete_events = [e for e in log if e['evt'] == 'del']
        assert len(delete_events) == 1
        assert delete_events[0]['pathlist'] == ['level1', 'level2']

    def test_subscriber_logs_attribute_changes(self):
        """Subscriber logs attribute updates."""
        bag = Bag()
        log = []

        def logger(**kw):
            log.append({
                'evt': kw.get('evt'),
                'node_label': kw.get('node').label if kw.get('node') else None,
            })

        bag.subscribe('logger', any=logger)

        # Insert with attributes
        bag.set_item('item', 'value', color='red', size=10)

        # Update attributes only
        node = bag.get_node('item')
        node.set_attr(color='blue')

        # Check we got insert and attr update
        assert log[0]['evt'] == 'ins'
        assert log[0]['node_label'] == 'item'

        assert log[1]['evt'] == 'upd_attrs'
        assert log[1]['node_label'] == 'item'

    def test_subscriber_multiple_subscribers_independent(self):
        """Multiple subscribers receive events independently."""
        bag = Bag()
        log_inserts = []
        log_updates = []
        log_all = []

        bag.subscribe('ins_logger', insert=lambda **kw: log_inserts.append(kw['evt']))
        bag.subscribe('upd_logger', update=lambda **kw: log_updates.append(kw['evt']))
        bag.subscribe('all_logger', any=lambda **kw: log_all.append(kw['evt']))

        bag['x'] = 1  # insert
        bag['x'] = 2  # update
        bag['y'] = 3  # insert

        assert log_inserts == ['ins', 'ins']
        assert log_updates == ['upd_value']
        assert log_all == ['ins', 'upd_value', 'ins']

    def test_unsubscribe_stops_logging(self):
        """After unsubscribe, no more events are logged."""
        bag = Bag()
        log = []

        bag.subscribe('logger', any=lambda **kw: log.append(kw['evt']))

        bag['a'] = 1
        assert len(log) == 1

        bag.unsubscribe('logger', any=True)

        bag['b'] = 2
        bag['a'] = 10
        del bag['a']

        # No new events after unsubscribe
        assert len(log) == 1


class TestBagMove:
    """Test move method - reordering nodes."""

    def test_move_single_node_forward(self):
        """Move single node forward."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag['c'] = 3
        bag['d'] = 4

        # Move 'a' (index 0) to position 2
        bag.move(0, 2)

        assert list(bag.keys()) == ['b', 'c', 'a', 'd']

    def test_move_single_node_backward(self):
        """Move single node backward."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag['c'] = 3
        bag['d'] = 4

        # Move 'd' (index 3) to position 1
        bag.move(3, 1)

        assert list(bag.keys()) == ['a', 'd', 'b', 'c']

    def test_move_same_position_noop(self):
        """Moving to same position does nothing."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag['c'] = 3

        bag.move(1, 1)

        assert list(bag.keys()) == ['a', 'b', 'c']

    def test_move_negative_position_noop(self):
        """Negative position does nothing."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2

        bag.move(0, -1)

        assert list(bag.keys()) == ['a', 'b']

    def test_move_invalid_index_noop(self):
        """Invalid from index does nothing."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2

        bag.move(10, 0)

        assert list(bag.keys()) == ['a', 'b']

    def test_move_out_of_bounds_position_noop(self):
        """Out of bounds target position does nothing."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2

        bag.move(0, 10)

        assert list(bag.keys()) == ['a', 'b']

    def test_move_multiple_nodes_forward(self):
        """Move multiple non-consecutive nodes forward."""
        bag = Bag()
        bag['a'] = 1  # 0
        bag['b'] = 2  # 1
        bag['c'] = 3  # 2
        bag['d'] = 4  # 3
        bag['e'] = 5  # 4

        # Move indices 0, 2 (a, c) to position 3 (d)
        # JS behavior: pop in reverse order (c then a), insert in pop order
        bag.move([0, 2], 3)

        # After pop: [b, d, e] - c popped first, then a
        # popped = [c, a] (reverse order of sorted indices)
        # dest_label = 'd', delta = 1 (indices[0]=0 < position=3)
        # new_pos = index('d') + 1 = 1 + 1 = 2
        # Insert c at 2: [b, d, c, e]
        # Insert a at 2: [b, d, a, c, e]
        assert list(bag.keys()) == ['b', 'd', 'a', 'c', 'e']

    def test_move_multiple_nodes_backward(self):
        """Move multiple non-consecutive nodes backward."""
        bag = Bag()
        bag['a'] = 1  # 0
        bag['b'] = 2  # 1
        bag['c'] = 3  # 2
        bag['d'] = 4  # 3
        bag['e'] = 5  # 4

        # Move indices 3, 4 (d, e) to position 1 (b)
        # JS behavior: pop in reverse order (e then d), insert in pop order
        bag.move([3, 4], 1)

        # After pop: [a, b, c] - e popped first, then d
        # popped = [e, d] (reverse order of sorted indices)
        # dest_label = 'b', delta = 0 (indices[0]=3 >= position=1)
        # new_pos = index('b') + 0 = 1
        # Insert e at 1: [a, e, b, c]
        # Insert d at 1: [a, d, e, b, c]
        assert list(bag.keys()) == ['a', 'd', 'e', 'b', 'c']

    def test_move_with_trigger_fires_events(self):
        """Move fires del and ins events when trigger=True."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag['c'] = 3

        events = []
        bag.subscribe('logger', any=lambda **kw: events.append(kw['evt']))

        bag.move(0, 2, trigger=True)

        # Should have del and ins events
        assert 'del' in events
        assert 'ins' in events

    def test_move_without_trigger_no_events(self):
        """Move with trigger=False fires no events."""
        bag = Bag()

        events = []
        bag.subscribe('logger', any=lambda **kw: events.append(kw['evt']))

        # Subscribe BEFORE inserting to capture insert events
        bag['a'] = 1
        bag['b'] = 2
        bag['c'] = 3

        # Clear events from inserts
        events.clear()

        bag.move(0, 2, trigger=False)

        # No events should be fired for move
        assert events == []

    def test_move_preserves_values_and_attributes(self):
        """Move preserves node values and attributes."""
        bag = Bag()
        bag.set_item('a', 1, color='red')
        bag.set_item('b', 2, color='blue')
        bag.set_item('c', 3, color='green')

        bag.move(0, 2)

        # Check 'a' is now at position 2 with preserved value and attr
        node = bag.get_node('#2')
        assert node.label == 'a'
        assert node.value == 1
        assert node.attr['color'] == 'red'

    def test_move_single_element_list(self):
        """Single-element list behaves like single int."""
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        bag['c'] = 3

        bag.move([0], 2)

        assert list(bag.keys()) == ['b', 'c', 'a']


class TestBagRoot:
    """Test root property for navigating to root Bag."""

    def test_root_on_standalone_bag(self):
        """Root of a standalone bag is itself."""
        bag = Bag()
        bag['a'] = 1
        assert bag.root is bag

    def test_root_without_backref(self):
        """Without backref, root is always self (no parent chain)."""
        bag = Bag()
        bag['a.b.c'] = 'deep'
        inner = bag['a.b']
        # Without backref, inner.parent is None
        assert inner.root is inner

    def test_root_with_backref(self):
        """With backref, root traverses to the top."""
        bag = Bag()
        bag['a.b.c'] = 'deep'
        bag.set_backref()

        inner_b = bag['a.b']
        inner_a = bag['a']

        # All should resolve to the root bag
        assert inner_b.root is bag
        assert inner_a.root is bag
        assert bag.root is bag

    def test_root_deeply_nested(self):
        """Root works for deeply nested bags."""
        bag = Bag()
        bag['level1.level2.level3.level4.leaf'] = 'value'
        bag.set_backref()

        level4 = bag['level1.level2.level3.level4']
        level3 = bag['level1.level2.level3']
        level2 = bag['level1.level2']
        level1 = bag['level1']

        assert level4.root is bag
        assert level3.root is bag
        assert level2.root is bag
        assert level1.root is bag


class TestBagFired:
    """Test _fired parameter for event-like signals."""

    def test_fired_sets_then_resets_to_none(self):
        """_fired=True sets value then immediately resets to None."""
        bag = Bag()
        bag.set_item('event', 'click', _fired=True)
        assert bag['event'] is None

    def test_fired_creates_node_if_not_exists(self):
        """_fired creates node even if it didn't exist."""
        bag = Bag()
        bag.set_item('new_event', 'trigger', _fired=True)
        assert 'new_event' in bag
        assert bag['new_event'] is None

    def test_fired_triggers_single_event(self):
        """_fired triggers only one event (the set), reset to None is silent."""
        bag = Bag()
        events = []
        bag.subscribe('test', any=lambda **kw: events.append(
            (kw['evt'], kw['node'].label, kw['node'].value)
        ))

        bag.set_item('signal', 'data', _fired=True)

        # Should have only: ins (with value 'data')
        # The reset to None is silent (do_trigger=False)
        assert len(events) == 1
        assert events[0][0] == 'ins'
        assert events[0][1] == 'signal'
        assert events[0][2] == 'data'  # Value at event time
        # But after the call, value is None
        assert bag['signal'] is None

    def test_fired_on_existing_node(self):
        """_fired works on existing nodes too."""
        bag = Bag()
        bag['existing'] = 'old_value'

        events = []
        bag.subscribe('test', any=lambda **kw: events.append(kw['evt']))

        bag.set_item('existing', 'fired_value', _fired=True)

        assert bag['existing'] is None
        # Only one update: for 'fired_value' (reset to None is silent)
        assert events.count('upd_value') == 1

    def test_fired_preserves_attributes(self):
        """_fired preserves node attributes."""
        bag = Bag()
        bag.set_item('event', 'click', _fired=True, _attributes={'type': 'mouse'})

        node = bag.get_node('event')
        assert node.value is None
        assert node.attr['type'] == 'mouse'


class TestBagSetItemAttrSyntax:
    """Test ?attr syntax in set_item for setting node attributes."""

    def test_set_attr_on_existing_node(self):
        """?attr sets attribute on existing node."""
        bag = Bag()
        bag['node'] = 'value'
        bag.set_item('node?myattr', 'attr_value')

        node = bag.get_node('node')
        assert node.value == 'value'  # Value unchanged
        assert node.attr['myattr'] == 'attr_value'

    def test_set_attr_nested_path(self):
        """?attr works with nested paths."""
        bag = Bag()
        bag['a.b.c'] = 42
        bag.set_item('a.b.c?type', 'integer')

        assert bag['a.b.c'] == 42
        assert bag['a.b.c?type'] == 'integer'

    def test_set_attr_using_bracket_syntax(self):
        """?attr works via __setitem__ (bag[path] = value)."""
        bag = Bag()
        bag['x'] = 100
        bag['x?unit'] = 'meters'

        assert bag['x'] == 100
        node = bag.get_node('x')
        assert node.attr['unit'] == 'meters'

    def test_set_attr_creates_node_if_missing(self):
        """?attr creates node with None value if it doesn't exist."""
        bag = Bag()
        bag.set_item('missing?attr', 'value')
        # Node is created with None value and the attribute set
        assert 'missing' in bag
        assert bag['missing'] is None
        assert bag['missing?attr'] == 'value'

    def test_set_attr_overwrites_existing_attr(self):
        """?attr overwrites existing attribute."""
        bag = Bag()
        bag.set_item('node', 'val', _attributes={'myattr': 'old'})
        bag.set_item('node?myattr', 'new')

        assert bag.get_node('node').attr['myattr'] == 'new'

    def test_set_attr_triggers_event(self):
        """?attr triggers update event when do_trigger=True."""
        bag = Bag()
        bag['node'] = 'value'

        events = []
        bag.subscribe('test', any=lambda **kw: events.append(kw['evt']))

        bag.set_item('node?myattr', 'attr_value')

        assert 'upd_attrs' in events

    def test_set_attr_no_trigger(self):
        """?attr respects do_trigger=False."""
        bag = Bag()
        bag['node'] = 'value'

        events = []
        bag.subscribe('test', any=lambda **kw: events.append(kw['evt']))

        bag.set_item('node?myattr', 'attr_value', do_trigger=False)

        assert len(events) == 0

    def test_set_attr_replaces_non_bag_with_bag(self):
        """?attr on nested path replaces non-Bag values with Bags."""
        bag = Bag()
        bag['a'] = 'string_value'  # a is a string, not a Bag
        bag.set_item('a.b.c?color', 'red')

        # a was replaced with a Bag
        assert isinstance(bag['a'], Bag)
        # nested structure was created
        assert bag['a.b.c'] is None
        assert bag['a.b.c?color'] == 'red'
