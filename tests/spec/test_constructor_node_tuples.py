"""Named tuple construction without changing positional list semantics."""

from types import MappingProxyType

import pytest

from genro_bag import Bag
from genro_bag.resolver import BagCbResolver


def test_single_node_triple_and_attribute_copy():
    attributes = {'name': 'demo'}
    bag = Bag(('project', None, attributes))
    assert bag.keys() == ['project']
    assert bag.get_node('project').attr == attributes
    attributes['name'] = 'changed'
    assert bag.get_node('project').attr['name'] == 'demo'


@pytest.mark.parametrize('sequence', [list, tuple])
def test_named_pairs_and_triples_in_order(sequence):
    bag = Bag(sequence([('first', 10), ('second', 20, {'caption': 'Second'})]))
    assert bag.keys() == ['first', 'second']
    assert bag['first'] == 10
    assert bag.get_node('second').attr == {'caption': 'Second'}


def test_regular_lists_remain_positional():
    assert Bag(['label', 10]).keys() == ['0', '1']
    bag = Bag([['label', 10], {'name': 'demo'}, (1, 2)])
    assert bag.keys() == ['0', '1', '2']
    assert bag['0'] == ['label', 10]
    assert bag['1.name'] == 'demo'
    assert bag['2'] == (1, 2)


def test_tuple_resolver_stays_lazy_and_subclass_is_preserved():
    class CustomBag(Bag):
        pass
    calls = []
    bag = CustomBag(('lazy', BagCbResolver(lambda: calls.append(1) or 42)))
    assert type(bag) is CustomBag
    assert calls == []
    assert bag['lazy'] == 42
    assert calls == [1]


def test_fill_from_tuple_validation_is_atomic():
    bag = Bag({'existing': 1})
    with pytest.raises(TypeError, match='attributes'):
        bag.fill_from([('ok', 2), ('bad', 3, 99)])
    assert bag.keys() == ['existing']
    assert bag['existing'] == 1
    bag.fill_from(('next', 2, MappingProxyType({'caption': 'Next'})))
    assert bag.keys() == ['next']
    assert bag.get_node('next').attr == {'caption': 'Next'}
