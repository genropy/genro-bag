"""Null placement follows the shared legacy Python/JS ordering contract."""
import pytest

from genro_bag import Bag


@pytest.mark.parametrize('criterion', ['#v', '#a.score', 'score'])
@pytest.mark.parametrize('mode', ['a', 'A', 'd', 'D'])
def test_nulls_first_ascending_last_descending(criterion, mode):
    bag = Bag()
    for label, value in [('n1', None), ('high', 10), ('n2', None), ('zero', 0)]:
        if criterion == '#v':
            bag.set_item(label, value)
        elif criterion == '#a.score':
            bag.set_item(label, 'row', _attributes={'score': value})
        else:
            bag.set_item(f'{label}.score', value)
    bag.sort(f'{criterion}:{mode}')
    expected = ['n1', 'n2', 'zero', 'high'] if mode.lower() == 'a' else ['high', 'zero', 'n1', 'n2']
    assert bag.keys() == expected
