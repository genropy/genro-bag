import pytest

from genro_bag import Bag


@pytest.mark.parametrize('method', ['set_item', 'setItem'])
def test_empty_path_merge_replaces_subtree_and_copies_attributes(method):
    bag = Bag()
    bag.set_item('a', 1)
    bag.set_item('child.old', 10)
    incoming = Bag()
    incoming.set_item('child.new', 20)
    incoming.set_item('b', 3, _attributes={'caption': 'B'})
    assert getattr(bag, method)('', incoming) is bag
    assert bag.keys() == ['a', 'child', 'b']
    assert bag['a'] == 1
    assert bag['child'].keys() == ['new']
    assert bag.get_node('b').attr == {'caption': 'B'}
    assert bag.get_node('b') is not incoming.get_node('b')


def test_mapping_empty_input_and_self_merge():
    bag = Bag({'a': 1})
    bag.set_item('', {'a': 2, 'b': None})
    assert bag.as_dict() == {'a': 2, 'b': None}
    bag.set_item('', Bag())
    bag.set_item('', {})
    bag.set_item('', bag)
    assert bag.as_dict() == {'a': 2, 'b': None}
    assert bag.get_node('') is None
