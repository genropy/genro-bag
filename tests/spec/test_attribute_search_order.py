"""Attribute lookup has explicit visit order, including the legacy path bridge."""
import pytest

from genro_bag import Bag


@pytest.mark.parametrize('deep_first,expected', [(False, 'sibling'), (True, 'deep')])
@pytest.mark.parametrize('value', ['yes', None])
def test_attribute_search_order(deep_first, expected, value):
    bag = Bag()
    bag.set_item('branch.inner.deep', 1, _attributes={'match': 'yes'})
    bag.set_item('sibling', 2, _attributes={'match': 'yes'})
    assert bag.get_node_by_attr('match', value, deep_first).label == expected
    path = []
    assert bag.getNodeByAttr('match', value, path, deep_first).label == expected
    assert path == (['branch', 'inner', 'deep'] if deep_first else ['sibling'])
    bag.pop_node('sibling')
    assert bag.get_node_by_attr('match', value, deep_first).label == 'deep'
    assert bag.get_node_by_attr('absent', value, deep_first) is None


def test_default_order_is_level_first():
    bag = Bag()
    bag.set_item('branch.deep', 1, _attributes={'match': 'yes'})
    bag.set_item('sibling', 2, _attributes={'match': 'yes'})
    assert bag.get_node_by_attr('match', 'yes').label == 'sibling'
    assert bag.getNodeByAttr('match', 'yes').label == 'sibling'
