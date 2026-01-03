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
