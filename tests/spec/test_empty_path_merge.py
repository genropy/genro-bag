import pytest

from genro_bag import Bag


@pytest.mark.parametrize('method', ['setItem'])
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
    bag.setItem('', {'a': 2, 'b': None})
    assert bag.as_dict() == {'a': 2, 'b': None}
    bag.setItem('', Bag())
    bag.setItem('', {})
    bag.setItem('', bag)
    assert bag.as_dict() == {'a': 2, 'b': None}
    assert bag.get_node('') is None


@pytest.mark.parametrize("value", [None, 0, "text", {}, {"a": 2}, Bag()])
def test_native_empty_path_rejected_without_mutation(value):
    bag = Bag({"existing": 1})
    with pytest.raises(ValueError, match="non-empty"):
        bag.set_item("", value)
    assert bag.as_dict() == {"existing": 1}
    assert bag.set_item("valid", value) is bag.get_node("valid")


def test_legacy_empty_path_scalar_is_noop():
    bag = Bag({"existing": 1})
    assert bag.setItem("", 42) is bag
    assert bag.as_dict() == {"existing": 1}
