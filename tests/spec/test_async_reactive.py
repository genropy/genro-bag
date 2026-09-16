"""Synchronous Bag contract, including callers running inside an event loop."""

import inspect
import threading

import pytest

from genro_bag import Bag
from genro_bag.resolvers import BagAsyncCbResolver, BagCbResolver, DirectoryResolver


@pytest.mark.asyncio
async def test_nested_callback_resolution_stays_on_calling_thread():
    caller = threading.get_ident()
    calls = []

    def leaf():
        calls.append(threading.get_ident())
        return 42

    def branch():
        calls.append(threading.get_ident())
        return Bag({"leaf": BagCbResolver(leaf)})

    bag = Bag({"branch": BagCbResolver(branch)})
    result = bag["branch.leaf"]
    assert result == 42
    assert not inspect.isawaitable(result)
    assert calls == [caller, caller]
    assert bag.getItem("branch.leaf") == 42
    assert bag.getNode("branch.leaf").value == 42


@pytest.mark.asyncio
async def test_directory_xml_configuration_is_immediately_traversable(tmp_path):
    (tmp_path / "environment.xml").write_text(
        '<GenRoBag><resources><common path="/resources"/></resources></GenRoBag>'
    )
    bag = Bag({"gnr": DirectoryResolver(str(tmp_path))})
    environment = bag.getItem("gnr.environment_xml")
    assert isinstance(environment, Bag)
    assert "resources" in environment
    assert bag["gnr.environment_xml.resources.common?path"] == "/resources"
    assert bag.getItem("gnr.environment_xml.resources.common?path") == "/resources"


def test_reset_invalidates_cache_without_loading():
    calls = []
    bag = Bag({"value": BagCbResolver(lambda: calls.append(1) or len(calls), cache_time=-1)})
    assert bag["value"] == 1
    events = []
    bag.subscribe("watch", update=lambda **kw: events.append(kw))
    bag.get_resolver("value").reset()
    assert calls == [1]
    assert events == []
    assert bag["value"] == 2


@pytest.mark.asyncio
async def test_eager_refresh_is_inline_and_does_not_coalesce():
    calls = []
    bag = Bag({"value": BagCbResolver(lambda: calls.append(1) or len(calls), cache_time=-1)})
    assert bag["value"] == 1
    events = []
    bag.subscribe("watch", update=lambda **kw: events.append(kw))
    resolver = bag.get_resolver("value")
    for expected in (2, 3, 4):
        resolver.reset(refresh=True)
        assert bag.get_item("value", static=True) == expected
        assert len(calls) == expected
    assert len(events) == 3


def test_eager_refresh_also_works_without_event_loop():
    bag = Bag({"value": BagCbResolver(lambda: 42, read_only=False)})
    bag.get_resolver("value").reset(refresh=True)
    assert bag.get_item("value", static=True) == 42


@pytest.mark.asyncio
async def test_reactive_attribute_change_refreshes_before_return():
    bag = Bag({"value": BagCbResolver(lambda factor: factor * 2, factor=3,
                                      reactive=True, cache_time=-1)})
    assert bag["value"] == 6
    bag.set_attr("value", factor=5)
    assert bag.get_item("value", static=True) == 10


@pytest.mark.asyncio
async def test_async_callback_is_rejected_even_with_running_loop():
    async def callback():
        return 1

    with pytest.raises(TypeError):
        BagAsyncCbResolver(callback)
    with pytest.raises(TypeError):
        BagCbResolver(callback)


@pytest.mark.asyncio
async def test_interval_and_timer_subscription_are_rejected_in_running_loop():
    with pytest.raises(ValueError):
        BagCbResolver(lambda: 1, interval=1)
    bag = Bag()
    with pytest.raises(ValueError):
        bag.subscribe("timer", timer=lambda **kw: None, interval=1)
