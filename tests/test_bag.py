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
