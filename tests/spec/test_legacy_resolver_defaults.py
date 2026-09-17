"""Legacy declaration adaptation must not change native resolver defaults."""
import pytest

from genro_bag import Bag, BagResolver


class LegacyReadonly(BagResolver):
    classKwargs = {'cacheTime': -1, 'readOnly': True, 'mode': 'bag'}
    classArgs = ['target']

    def load(self):
        return Bag({'value': 1})


class InheritedReadonly(LegacyReadonly):
    pass


@pytest.mark.parametrize('cls', [LegacyReadonly, InheritedReadonly])
def test_readonly_class_default_survives_infinite_cache(cls):
    resolver = cls('table')
    bag = Bag()
    node = bag.set_item('result', resolver)
    assert resolver.read_only is True
    first = node.value
    assert node.value is first
    assert resolver.cached_value is first
    assert node.static_value is None
    assert cls('table', readOnly=False).read_only is False
    assert cls('table', read_only=False).read_only is False


def test_legacy_extra_keywords_are_live_and_exclude_declared_parameters():
    resolver = LegacyReadonly('table', branch_customer='C1')
    extras = resolver.kwargs
    assert dict(extras) == {'branch_customer': 'C1'}
    extras['branch_customer'] = 'C2'
    assert resolver.kwargs['branch_customer'] == 'C2'
    resolver._kw = {**resolver._kw, 'branch_region': 'EU'}
    assert extras.copy() == {'branch_customer': 'C2', 'branch_region': 'EU'}
    assert extras.pop('branch_region') == 'EU'
    assert dict(extras) == {'branch_customer': 'C2'}


def test_native_automatic_readonly_policy_is_unchanged():
    assert BagResolver(cache_time=0).read_only is True
    assert BagResolver(cache_time=-1).read_only is False
    assert BagResolver(cache_time=-1, read_only=True).read_only is True
