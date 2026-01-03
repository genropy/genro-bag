# Copyright 2025 Softwell S.r.l. - Genropy Team
# Licensed under the Apache License, Version 2.0

"""Tests for NodeContainer specification."""

import pytest

from genro_bag import NodeContainer


class TestNodeContainerBasic:
    """Test basic NodeContainer creation and access."""

    def test_create_empty(self):
        """Create an empty NodeContainer."""
        d = NodeContainer()
        assert len(d) == 0

    def test_create_from_dict(self):
        """Create NodeContainer from a dict."""
        d = NodeContainer({'a': 1, 'b': 2})
        assert d['a'] == 1
        assert d['b'] == 2


class TestAccessSyntax:
    """Test the three access syntaxes: label, numeric index, '#n' string."""

    def test_access_by_label(self):
        """Access by label string."""
        d = NodeContainer()
        d['foo'] = 1
        d['bar'] = 2
        d['baz'] = 3

        assert d['foo'] == 1
        assert d['bar'] == 2
        assert d['baz'] == 3

    def test_access_by_numeric_index(self):
        """Access by numeric index."""
        d = NodeContainer()
        d['foo'] = 1
        d['bar'] = 2
        d['baz'] = 3

        assert d[0] == 1
        assert d[1] == 2
        assert d[2] == 3

    def test_access_by_hash_index(self):
        """Access by '#n' string index."""
        d = NodeContainer()
        d['foo'] = 1
        d['bar'] = 2
        d['baz'] = 3

        assert d['#0'] == 1
        assert d['#1'] == 2
        assert d['#2'] == 3

    def test_all_syntaxes_equivalent(self):
        """All three syntaxes return the same value."""
        d = NodeContainer()
        d['foo'] = 1
        d['bar'] = 2
        d['baz'] = 3

        # Access second element with all syntaxes
        assert d['bar'] == d[1] == d['#1'] == 2


class TestMissingKeys:
    """Test behavior for missing keys/indices - never raises, returns None."""

    def test_missing_label_returns_none(self):
        """Missing label returns None."""
        d = NodeContainer()
        d['foo'] = 1

        assert d['missing'] is None

    def test_out_of_range_index_returns_none(self):
        """Out of range numeric index returns None."""
        d = NodeContainer()
        d['foo'] = 1

        assert d[99] is None

    def test_out_of_range_hash_index_returns_none(self):
        """Out of range '#n' index returns None."""
        d = NodeContainer()
        d['foo'] = 1

        assert d['#99'] is None

class TestContains:
    """Test __contains__ for checking existence."""

    def test_contains_existing_label(self):
        """Label exists."""
        d = NodeContainer()
        d['foo'] = 1

        assert 'foo' in d

    def test_contains_missing_label(self):
        """Label does not exist."""
        d = NodeContainer()
        d['foo'] = 1

        assert 'missing' not in d


class TestPositionInsert:
    """Test insertion with _position parameter."""

    def test_default_append(self):
        """Default position appends to end."""
        d = NodeContainer()
        d.set('a', 1)
        d.set('b', 2)
        d.set('c', 3)

        assert d.keys() == ['a', 'b', 'c']

    def test_position_append_explicit(self):
        """Position '>' appends to end."""
        d = NodeContainer()
        d.set('a', 1)
        d.set('b', 2, _position='>')

        assert d.keys() == ['a', 'b']

    def test_position_prepend(self):
        """Position '<' prepends to beginning."""
        d = NodeContainer()
        d.set('a', 1)
        d.set('b', 2)
        d.set('c', 3, _position='<')

        assert d.keys() == ['c', 'a', 'b']

    def test_position_at_index(self):
        """Position '#n' inserts at index n."""
        d = NodeContainer()
        d.set('a', 1)
        d.set('b', 2)
        d.set('c', 3, _position='#1')

        assert d.keys() == ['a', 'c', 'b']

    def test_position_before_label(self):
        """Position '<label' inserts before label."""
        d = NodeContainer()
        d.set('a', 1)
        d.set('b', 2)
        d.set('c', 3, _position='<b')

        assert d.keys() == ['a', 'c', 'b']

    def test_position_after_label(self):
        """Position '>label' inserts after label."""
        d = NodeContainer()
        d.set('a', 1)
        d.set('b', 2)
        d.set('c', 3)
        d.set('d', 4, _position='>a')

        assert d.keys() == ['a', 'd', 'b', 'c']

    def test_position_before_hash_index(self):
        """Position '<#n' inserts before index n."""
        d = NodeContainer()
        d.set('a', 1)
        d.set('b', 2)
        d.set('c', 3)
        d.set('d', 4, _position='<#2')

        assert d.keys() == ['a', 'b', 'd', 'c']

    def test_position_after_hash_index(self):
        """Position '>#n' inserts after index n."""
        d = NodeContainer()
        d.set('a', 1)
        d.set('b', 2)
        d.set('c', 3)
        d.set('d', 4, _position='>#0')

        assert d.keys() == ['a', 'd', 'b', 'c']

    def test_position_numeric_int(self):
        """Position as int inserts at that index."""
        d = NodeContainer()
        d.set('a', 1)
        d.set('b', 2)
        d.set('c', 3, _position=1)

        assert d.keys() == ['a', 'c', 'b']

    def test_complex_positioning(self):
        """Complex sequence of positional inserts from spec."""
        d = NodeContainer()
        d.set('a', 1)                      # [a]
        d.set('b', 2)                      # [a, b]
        d.set('c', 3, _position='<')       # [c, a, b]
        d.set('d', 4, _position='<b')      # [c, a, d, b]
        d.set('e', 5, _position='>#1')     # [c, a, e, d, b]
        d.set('f', 6, _position='#0')      # [f, c, a, e, d, b]

        assert d.keys() == ['f', 'c', 'a', 'e', 'd', 'b']


class TestOverwrite:
    """Test overwriting existing keys preserves position."""

    def test_overwrite_preserves_position(self):
        """Overwriting a key preserves its position."""
        d = NodeContainer()
        d['x'] = 1
        d['y'] = 2
        d['z'] = 3

        d['y'] = 99

        assert d.keys() == ['x', 'y', 'z']
        assert d['y'] == 99


class TestMove:
    """Test move() method for repositioning elements."""

    def test_move_single_to_beginning(self):
        """Move single element to beginning."""
        d = NodeContainer()
        d['a'] = 1
        d['b'] = 2
        d['c'] = 3
        d['foo'] = 4

        d.move('foo', '<')

        assert d.keys() == ['foo', 'a', 'b', 'c']

    def test_move_single_to_end(self):
        """Move single element to end."""
        d = NodeContainer()
        d['a'] = 1
        d['b'] = 2
        d['c'] = 3

        d.move('a', '>')

        assert d.keys() == ['b', 'c', 'a']

    def test_move_by_numeric_index(self):
        """Move element by numeric index."""
        d = NodeContainer()
        d['a'] = 1
        d['b'] = 2
        d['c'] = 3

        d.move(0, '>')

        assert d.keys() == ['b', 'c', 'a']

    def test_move_by_hash_index(self):
        """Move element by '#n' index."""
        d = NodeContainer()
        d['a'] = 1
        d['b'] = 2
        d['c'] = 3

        d.move('#0', '>')

        assert d.keys() == ['b', 'c', 'a']

    def test_move_after_label(self):
        """Move element after another label."""
        d = NodeContainer()
        d['a'] = 1
        d['b'] = 2
        d['c'] = 3
        d['d'] = 4

        d.move('a', '>c')

        assert d.keys() == ['b', 'c', 'a', 'd']

    def test_move_multiple_with_string(self):
        """Move multiple elements with comma-separated string."""
        d = NodeContainer()
        d['a'] = 1
        d['b'] = 2
        d['c'] = 3
        d['foo'] = 4
        d['bar'] = 5
        d['egg'] = 6

        d.move('foo,bar', '>egg')

        assert d.keys() == ['a', 'b', 'c', 'egg', 'foo', 'bar']

    def test_move_multiple_with_list(self):
        """Move multiple elements with list."""
        d = NodeContainer()
        d['a'] = 1
        d['b'] = 2
        d['c'] = 3
        d['d'] = 4

        d.move(['a', 'c'], '>')

        assert d.keys() == ['b', 'd', 'a', 'c']

    def test_move_multiple_mixed_references(self):
        """Move multiple elements with mixed reference types."""
        d = NodeContainer()
        d['a'] = 1
        d['b'] = 2
        d['c'] = 3
        d['d'] = 4
        d['e'] = 5

        d.move([0, 'c', '#4'], '<')

        # a, c, e moved to beginning, preserving relative order
        assert d.keys()[:3] == ['a', 'c', 'e']

    def test_move_preserves_relative_order(self):
        """Moving multiple elements preserves their relative order."""
        d = NodeContainer()
        d['a'] = 1
        d['b'] = 2
        d['c'] = 3
        d['foo'] = 4
        d['bar'] = 5
        d['egg'] = 6

        d.move('foo,bar', '>egg')

        # foo and bar should maintain their relative order
        keys = d.keys()
        assert keys.index('foo') < keys.index('bar')


class TestIteration:
    """Test keys(), values(), items() methods."""

    def test_keys_returns_list_by_default(self):
        """keys() returns a list by default."""
        d = NodeContainer()
        d.set('c', 3)
        d.set('a', 1)
        d.set('b', 2)

        result = d.keys()

        assert isinstance(result, list)
        assert result == ['c', 'a', 'b']

    def test_keys_with_iter_true(self):
        """keys(iter=True) returns an iterator."""
        d = NodeContainer()
        d.set('c', 3)
        d.set('a', 1)
        d.set('b', 2)

        result = d.keys(iter=True)

        assert hasattr(result, '__iter__')
        assert hasattr(result, '__next__')
        assert list(result) == ['c', 'a', 'b']

    def test_values_returns_list_by_default(self):
        """values() returns a list by default."""
        d = NodeContainer()
        d.set('c', 3)
        d.set('a', 1)
        d.set('b', 2)

        result = d.values()

        assert isinstance(result, list)
        assert result == [3, 1, 2]

    def test_values_with_iter_true(self):
        """values(iter=True) returns an iterator."""
        d = NodeContainer()
        d.set('c', 3)
        d.set('a', 1)
        d.set('b', 2)

        result = d.values(iter=True)

        assert hasattr(result, '__iter__')
        assert hasattr(result, '__next__')
        assert list(result) == [3, 1, 2]

    def test_items_returns_list_by_default(self):
        """items() returns a list by default."""
        d = NodeContainer()
        d.set('c', 3)
        d.set('a', 1)
        d.set('b', 2)

        result = d.items()

        assert isinstance(result, list)
        assert result == [('c', 3), ('a', 1), ('b', 2)]

    def test_items_with_iter_true(self):
        """items(iter=True) returns an iterator."""
        d = NodeContainer()
        d.set('c', 3)
        d.set('a', 1)
        d.set('b', 2)

        result = d.items(iter=True)

        assert hasattr(result, '__iter__')
        assert hasattr(result, '__next__')
        assert list(result) == [('c', 3), ('a', 1), ('b', 2)]

    def test_iter_over_dict(self):
        """Iterating over NodeContainer yields keys in order."""
        d = NodeContainer()
        d.set('c', 3)
        d.set('a', 1)
        d.set('b', 2)

        assert list(d) == ['c', 'a', 'b']


class TestSlicing:
    """Test slicing on keys(), values(), items()."""

    def test_keys_slicing(self):
        """Slicing on keys()."""
        d = NodeContainer()
        d['a'] = 1
        d['b'] = 2
        d['c'] = 3
        d['d'] = 4
        d['e'] = 5

        assert d.keys()[1:3] == ['b', 'c']

    def test_values_slicing(self):
        """Slicing on values()."""
        d = NodeContainer()
        d['a'] = 1
        d['b'] = 2
        d['c'] = 3
        d['d'] = 4
        d['e'] = 5

        assert d.values()[1:3] == [2, 3]

    def test_items_slicing(self):
        """Slicing on items()."""
        d = NodeContainer()
        d['a'] = 1
        d['b'] = 2
        d['c'] = 3
        d['d'] = 4
        d['e'] = 5

        assert d.items()[1:3] == [('b', 2), ('c', 3)]


class TestUpdate:
    """Test update() method."""

    def test_update_overwrites_existing(self):
        """Update overwrites existing keys, preserving position."""
        d = NodeContainer()
        d['a'] = 1
        d['b'] = 2
        d['c'] = 3

        d.update({'b': 99})

        assert d['b'] == 99
        assert d.keys() == ['a', 'b', 'c']

    def test_update_appends_new(self):
        """Update appends new keys at the end."""
        d = NodeContainer()
        d['a'] = 1
        d['b'] = 2
        d['c'] = 3

        d.update({'x': 10, 'y': 20})

        assert d.keys()[-2:] == ['x', 'y']

    def test_update_mixed(self):
        """Update with both existing and new keys."""
        d = NodeContainer()
        d['a'] = 1
        d['b'] = 2
        d['c'] = 3

        d.update({'b': 99, 'x': 10, 'y': 20})

        assert d.keys() == ['a', 'b', 'c', 'x', 'y']
        assert d['b'] == 99
        assert d['x'] == 10
        assert d['y'] == 20


class TestClone:
    """Test clone() method."""

    def test_clone_all(self):
        """Clone without selector clones everything."""
        d = NodeContainer()
        d['a'] = 1
        d['b'] = 2
        d['c'] = 3

        clone = d.clone()

        assert clone.keys() == ['a', 'b', 'c']
        assert clone['a'] == 1
        assert clone['b'] == 2
        assert clone['c'] == 3

    def test_clone_is_independent(self):
        """Cloned NodeContainer is independent from original."""
        d = NodeContainer()
        d['a'] = 1

        clone = d.clone()
        clone['a'] = 99

        assert d['a'] == 1
        assert clone['a'] == 99

    def test_clone_with_string_selector(self):
        """Clone with comma-separated string selector."""
        d = NodeContainer()
        d['a'] = 1
        d['b'] = 2
        d['c'] = 3
        d['d'] = 4
        d['e'] = 5

        clone = d.clone('b,c,#4')

        assert clone.keys() == ['b', 'c', 'e']

    def test_clone_with_list_selector(self):
        """Clone with list selector."""
        d = NodeContainer()
        d['a'] = 1
        d['b'] = 2
        d['c'] = 3
        d['d'] = 4
        d['e'] = 5

        clone = d.clone([1, 'c', '#4'])

        assert clone.keys() == ['b', 'c', 'e']

    def test_clone_with_callable_selector(self):
        """Clone with callable selector."""
        d = NodeContainer()
        d['a'] = 1
        d['b'] = 2
        d['c'] = 3
        d['d'] = 4
        d['e'] = 5

        clone = d.clone(lambda k, v: v > 2)

        assert clone.keys() == ['c', 'd', 'e']

    def test_clone_preserves_order(self):
        """Clone preserves original order."""
        d = NodeContainer()
        d['c'] = 3
        d['a'] = 1
        d['b'] = 2

        clone = d.clone()

        assert clone.keys() == ['c', 'a', 'b']


class TestDelete:
    """Test deletion via __delitem__ and pop."""

    def test_delitem_by_label(self):
        """Delete by label."""
        d = NodeContainer()
        d['a'] = 1
        d['b'] = 2
        d['c'] = 3

        del d['b']

        assert d.keys() == ['a', 'c']
        assert 'b' not in d

    def test_delitem_by_index(self):
        """Delete by numeric index."""
        d = NodeContainer()
        d['a'] = 1
        d['b'] = 2
        d['c'] = 3

        del d[1]

        assert d.keys() == ['a', 'c']

    def test_delitem_by_hash_index(self):
        """Delete by '#n' index."""
        d = NodeContainer()
        d['a'] = 1
        d['b'] = 2
        d['c'] = 3

        del d['#1']

        assert d.keys() == ['a', 'c']

    def test_pop_by_label(self):
        """Pop by label returns value."""
        d = NodeContainer()
        d['a'] = 1
        d['b'] = 2
        d['c'] = 3

        value = d.pop('b')

        assert value == 2
        assert d.keys() == ['a', 'c']

    def test_pop_by_index(self):
        """Pop by numeric index returns value."""
        d = NodeContainer()
        d['a'] = 1
        d['b'] = 2
        d['c'] = 3

        value = d.pop(1)

        assert value == 2
        assert d.keys() == ['a', 'c']

    def test_pop_with_default(self):
        """Pop missing key with default returns default."""
        d = NodeContainer()
        d['a'] = 1

        value = d.pop('missing', 'default')

        assert value == 'default'


class TestClear:
    """Test clear() method."""

    def test_clear(self):
        """Clear removes all elements."""
        d = NodeContainer()
        d['a'] = 1
        d['b'] = 2
        d['c'] = 3

        d.clear()

        assert len(d) == 0
        assert d.keys() == []


class TestLen:
    """Test __len__ method."""

    def test_len_empty(self):
        """Length of empty NodeContainer is 0."""
        d = NodeContainer()
        assert len(d) == 0

    def test_len_with_elements(self):
        """Length reflects number of elements."""
        d = NodeContainer()
        d['a'] = 1
        d['b'] = 2
        d['c'] = 3

        assert len(d) == 3
