import pytest

from genro_bag import Bag


def test_formulas_are_not_exposed_by_native_or_names_mixin():
    bag = Bag()
    for name in ('defineSymbol', 'defineFormula', 'formula', 'define_symbol', 'define_formula'):
        assert not hasattr(bag, name)


@pytest.mark.parametrize('method', ['setItem', 'addItem'])
@pytest.mark.parametrize('validators', [{}, {'required': True}])
def test_removed_validation_is_rejected_before_mutating(method, validators):
    bag = Bag({'existing': 1})
    with pytest.raises(TypeError, match='no longer supported'):
        getattr(bag, method)('new', 2, _validators=validators)
    assert bag.keys() == ['existing']
