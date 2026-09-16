from datetime import datetime, timedelta

import genro_bag.resolver as resolver_module
from genro_bag import Bag
from genro_bag.resolver import BagCbResolver


class _Clock(datetime):
    current = datetime(2026, 1, 1, 12, 0, 0)

    @classmethod
    def now(cls, tz=None):
        return cls.current


def _counter_resolver(*, cache_time, read_only=True):
    calls = []
    resolver = BagCbResolver(
        lambda **kw: calls.append(kw) or len(calls),
        cache_time=cache_time,
        read_only=read_only,
    )
    return resolver, calls


def test_read_only_positive_ttl_uses_internal_cache_without_touching_node(monkeypatch):
    monkeypatch.setattr(resolver_module, "datetime", _Clock)
    resolver, calls = _counter_resolver(cache_time=10)
    bag = Bag()
    bag.set_item("value", "static", resolver=resolver)

    assert bag["value"] == 1
    assert bag["value"] == 1
    assert resolver.cached_value == 1
    assert bag.get_item("value", static=True) == "static"

    node = bag.get_node("value")
    node.resolver = None
    assert resolver() == 1
    node.resolver = resolver
    assert bag.get_item("value", static=True) == "static"

    _Clock.current += timedelta(seconds=11)
    assert bag["value"] == 2
    assert len(calls) == 2
    assert bag.get_item("value", static=True) == "static"


def test_read_only_zero_does_not_cache_and_negative_duration_is_infinite():
    uncached, uncached_calls = _counter_resolver(cache_time=0)
    assert (uncached(), uncached()) == (1, 2)
    assert uncached.cached_value is None
    assert len(uncached_calls) == 2

    infinite, infinite_calls = _counter_resolver(cache_time=-0.5)
    assert (infinite(), infinite()) == (1, 1)
    assert infinite.cached_value == 1
    assert len(infinite_calls) == 1


def test_read_only_cached_none_is_a_valid_cached_result():
    calls = []
    resolver = BagCbResolver(
        lambda: calls.append(1) or None,
        cache_time=-1,
        read_only=True,
    )

    assert resolver() is None
    assert resolver() is None
    assert len(calls) == 1
    assert resolver.expired is False


def test_read_only_reset_and_parameter_change_invalidate_attached_cache():
    calls = []
    resolver = BagCbResolver(
        lambda factor: calls.append(factor) or factor * 2,
        factor=2,
        cache_time=-1,
        read_only=True,
    )
    bag = Bag({"value": resolver})

    assert bag["value"] == 4
    resolver.reset()
    assert bag["value"] == 4
    bag.set_attr("value", factor=3)
    assert bag["value"] == 6
    assert calls == [2, 2, 3]


def test_writable_cache_uses_current_storage_after_attach_and_detach():
    resolver, calls = _counter_resolver(cache_time=-1, read_only=False)
    assert resolver() == 1

    bag = Bag()
    bag.set_item("value", "old", resolver=resolver)
    assert bag.get_item("value", static=True) == "old"
    assert bag["value"] == 2
    assert bag.get_item("value", static=True) == 2

    node = bag.get_node("value")
    node.resolver = None
    assert resolver() == 3
    assert resolver.cached_value == 3
    assert len(calls) == 3


def test_changing_read_only_invalidates_cache_and_switches_storage():
    resolver, calls = _counter_resolver(cache_time=-1, read_only=True)
    bag = Bag()
    bag.set_item("value", "static", resolver=resolver)
    assert bag["value"] == 1

    resolver.readOnly = False
    assert bag["value"] == 2
    assert bag.get_item("value", static=True) == 2
    assert calls == [{}, {}]
