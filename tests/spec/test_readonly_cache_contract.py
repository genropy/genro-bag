"""Read-only storage is independent of cache duration and parameter spelling."""
from datetime import datetime, timedelta

import pytest

import genro_bag.resolver as resolver_module
from genro_bag import Bag, BagResolver


@pytest.mark.parametrize('duration', [0, -1, 10])
@pytest.mark.parametrize('declaration', ['native', 'legacy', 'explicit'])
def test_readonly_cache_storage_and_expiry(monkeypatch, duration, declaration):
    class Clock(datetime):
        current = datetime(2026, 1, 1)

        @classmethod
        def now(cls):
            return cls.current

    monkeypatch.setattr(resolver_module, 'datetime', Clock)
    attributes = {'class_kwargs': {'read_only': True, 'cache_time': duration}}
    if declaration == 'legacy':
        attributes = {'classKwargs': {'readOnly': True, 'cacheTime': duration}}
    elif declaration == 'explicit':
        attributes = {}
    calls = []

    def load(self):
        calls.append(1)
        return Bag({'count': len(calls)})

    Resolver = type('Getter', (BagResolver,), {**attributes, 'load': load})
    # Verify inherited defaults as well as directly declared ones.
    class Inherited(Resolver):
        pass

    options = {'cache_time': duration, 'read_only': True} if declaration == 'explicit' else {}
    resolver = Inherited(**options)
    bag = Bag()
    node = bag.set_item('result', resolver)
    node.static_value = 'unchanged'
    assert resolver.read_only is True
    first = node.value
    second = node.value
    assert len(calls) == (2 if duration == 0 else 1)
    assert (first is second) == (duration != 0)
    assert node.static_value == 'unchanged'
    if duration != 0:
        assert resolver.cached_value is first
    Clock.current += timedelta(seconds=11)
    _ = node.value
    assert len(calls) == (1 if duration == -1 else 3 if duration == 0 else 2)
    assert node.static_value == 'unchanged'
    before = len(calls)
    resolver.reset()
    _ = node.value
    assert len(calls) == before + 1
    assert node.static_value == 'unchanged'


@pytest.mark.parametrize('duration', [0, -1, 10])
@pytest.mark.parametrize('default,override', [(True, False), (False, True)])
def test_constructor_overrides_class_storage_policy(duration, default, override):
    class Resolver(BagResolver):
        class_kwargs = {'read_only': default, 'cache_time': duration, 'as_bag': False}

        def load(self):
            return 42

    resolver = Resolver(read_only=override)
    bag = Bag()
    node = bag.set_item('result', resolver)
    assert node.value == 42
    assert resolver.read_only is override
    assert node.static_value == (None if override else 42)


def test_class_writable_default_is_respected_without_cache():
    class Resolver(BagResolver):
        class_kwargs = {'read_only': False, 'cache_time': 0, 'as_bag': False}

        def load(self):
            return 42

    resolver = Resolver()
    node = Bag().set_item('result', resolver)
    assert node.value == 42
    assert node.static_value == 42
