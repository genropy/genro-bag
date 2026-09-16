"""Strict and predicate are independent, non-recursive sum options."""
import pytest

from genro_bag import Bag


@pytest.mark.parametrize('empty', [None, ''])
def test_sum_strict_and_filter(empty):
    bag = Bag({'a': 3, 'b': empty, 'c': 4})
    assert bag.sum() == 7
    assert bag.sum('#v', True) is None
    assert bag.sum('#v', True, lambda n: n.label != 'b') == 7
    assert bag['b'] == empty


def test_zero_false_empty_selection_and_multiple_sums():
    bag = Bag({'zero': 0, 'false': False, 'true': True})
    assert bag.sum('#v', True) == 1
    assert bag.sum('#v', True, lambda n: False) == 0
    assert Bag().sum('#v', True) == 0
    bag.set_item('other', 3, _attributes={'qty': 4})
    assert bag.sum('#v,#a.qty', True) == [4, None]
    with pytest.raises(TypeError, match='third argument'):
        bag.sum('#v', lambda n: True)


@pytest.mark.parametrize('value', ['9', 'text', ' ', [], {}, Bag()])
def test_non_numeric_values(value):
    bag = Bag()
    bag.set_item('a', 3)
    bag.set_item('invalid', value)
    bag.set_item('b', 4)
    assert bag.sum() == 7
    with pytest.raises(TypeError, match='non-numeric'):
        bag.sum('#v', True)
    assert bag.sum('#v', True, lambda n: n.label != 'invalid') == 7


def test_decimal_values_remain_numeric():
    from decimal import Decimal
    bag = Bag({'a': Decimal('0.1'), 'b': Decimal('0.2')})
    assert bag.sum('#v', True) == Decimal('0.3')


@pytest.mark.parametrize('values', [[None, '9'], ['9', None]])
def test_strict_invalid_type_is_not_hidden_by_null(values):
    bag = Bag(dict(zip(['a', 'b'], values, strict=True)))
    with pytest.raises(TypeError, match='non-numeric'):
        bag.sum('#v', True)
