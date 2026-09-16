import warnings

import pytest

from genro_bag import Bag
from genro_bag._camel_names import BagResolverNamesMixin
from genro_bag.resolver import BagResolver


class Rows(BagResolver):
    def load(self):
        return Bag({'a': 1, 'b': 2})


def test_container_helpers_live_only_in_compatibility_mixin():
    for name in ('__getitem__', '__iter__', '_htraverse', 'get_node', 'getNode',
                 'keys', 'items', 'values', 'digest'):
        assert name not in BagResolver.__dict__
        assert name in BagResolverNamesMixin.__dict__


@pytest.mark.parametrize('operation, expected', [
    (lambda r: r['a'], 1),
    (lambda r: [n.label for n in r], ['a', 'b']),
    (lambda r: r.keys(), ['a', 'b']),
    (lambda r: r.items(), [('a', 1), ('b', 2)]),
    (lambda r: r.values(), [1, 2]),
    (lambda r: r.get_node('a').label, 'a'),
    (lambda r: r.getNode('b').label, 'b'),
    (lambda r: r.digest('#v'), [1, 2]),
])
def test_existing_delegations_warn_and_preserve_results(operation, expected):
    with pytest.warns(DeprecationWarning, match='resolve explicitly') as notices:
        assert operation(Rows()) == expected
    assert len(notices) == 1


def test_explicit_resolution_does_not_warn():
    with warnings.catch_warnings(record=True) as notices:
        warnings.simplefilter('always')
        assert Rows()().keys() == ['a', 'b']
    assert not notices
