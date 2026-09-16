import pytest

from genro_bag import Bag
from genro_bag.resolver import BagCbResolver


@pytest.mark.parametrize('duration', [-1, -10, -0.5])
def test_negative_cache_is_infinite_until_reset(duration):
    calls = []
    resolver = BagCbResolver(lambda: calls.append(1) or len(calls), cache_time=duration)
    bag = Bag({'value': resolver})
    assert resolver.expired
    assert bag['value'] == 1
    assert bag['value'] == 1
    assert not resolver.expired
    assert resolver.serialize()['kwargs']['cache_time'] == duration
    resolver.reset()
    assert resolver.expired
    assert bag['value'] == 2


@pytest.mark.parametrize('duration', [-1, -10, -0.5])
def test_legacy_names_preserve_negative_duration(duration):
    resolver = BagCbResolver(lambda: 1, cacheTime=duration)
    assert resolver.cache_time == duration
    assert resolver.cacheTime == duration
    resolver.cacheTime = duration * 2
    assert resolver.cache_time == duration * 2
    with pytest.raises(TypeError):
        resolver.cacheTime = False
