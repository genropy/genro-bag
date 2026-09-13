"""Resolvers always return synchronous values, including inside an event loop."""

from __future__ import annotations

import asyncio
import os

import pytest

from genro_bag import Bag
from genro_bag.resolvers import (
    BagAsyncCbResolver,
    BagCbResolver,
    EnvResolver,
    UuidResolver,
)

# =============================================================================
# 1. EnvResolver in async context
# =============================================================================


class TestEnvResolverInAsyncContext:
    @pytest.mark.asyncio
    async def test_env_resolver_returns_value_not_coroutine(self):
        os.environ["TEST_SYNC_ASYNC_VAR"] = "hello"
        try:
            bag = Bag()
            bag["v"] = EnvResolver("TEST_SYNC_ASYNC_VAR")
            result = bag["v"]
            assert not asyncio.iscoroutine(result)
            assert result == "hello"
        finally:
            os.environ.pop("TEST_SYNC_ASYNC_VAR", None)


# =============================================================================
# 2. UuidResolver in async context
# =============================================================================


class TestUuidResolverInAsyncContext:
    @pytest.mark.asyncio
    async def test_uuid_resolver_returns_string_not_coroutine(self):
        bag = Bag()
        bag["id"] = UuidResolver()
        result = bag["id"]
        assert not asyncio.iscoroutine(result)
        assert isinstance(result, str)
        assert len(result) == 36  # standard UUID string length


# =============================================================================
# 3. BagCbResolver con callback sync in async context
# =============================================================================


class TestBagCbResolverSyncInAsyncContext:
    @pytest.mark.asyncio
    async def test_sync_callback_returns_value_not_coroutine(self):
        bag = Bag()
        bag["calc"] = BagCbResolver(lambda: 42)
        result = bag["calc"]
        assert not asyncio.iscoroutine(result)
        assert result == 42


# =============================================================================
# 4-5. Contratti di rifiuto al costruttore
# =============================================================================


class TestConstructorRejections:
    def test_cb_resolver_rejects_async_callback(self):
        async def async_cb():
            return 1

        with pytest.raises(TypeError, match="requires a sync"):
            BagCbResolver(async_cb)

    def test_async_cb_resolver_rejects_sync_callback(self):
        with pytest.raises(TypeError, match="no longer supported"):
            BagAsyncCbResolver(lambda: 1)


# =============================================================================
# 6. BagAsyncCbResolver in async context
# =============================================================================


class TestBagAsyncCbResolverInAsyncContext:
    @pytest.mark.asyncio
    async def test_async_callback_rejected_in_event_loop(self):
        async def callback():
            return 1
        with pytest.raises(TypeError, match="no longer supported"):
            BagAsyncCbResolver(callback)


@pytest.mark.asyncio
async def test_base_resolver_runs_on_callers_thread():
    import threading

    from genro_bag.resolver import BagResolver

    class Resolver(BagResolver):
        def load(self):
            return threading.get_ident()

    assert Resolver()() == threading.get_ident()


def test_async_only_resolver_rejected_before_coroutine_creation():
    from genro_bag.resolver import BagResolver

    class Resolver(BagResolver):
        async def async_load(self):
            return 1

    with pytest.raises(TypeError, match="synchronous load"):
        Resolver()


def test_awaitable_result_rejected_and_closed():
    import inspect

    async def callback():
        return 1

    value = callback()
    with pytest.raises(TypeError, match="awaitable results"):
        BagCbResolver(lambda: value)()
    assert inspect.getcoroutinestate(value) == inspect.CORO_CLOSED


@pytest.mark.parametrize("method", ["load", "on_loading", "on_loaded"])
def test_async_hooks_fail_without_leaking_coroutines(method):
    import inspect

    from genro_bag.resolver import BagResolver

    created = []

    async def value():
        return 1

    def invalid(*args):
        result = value()
        created.append(result)
        return result

    class Resolver(BagResolver):
        def load(self):
            return self.kw["value"]

    setattr(Resolver, method, invalid)
    resolver = Resolver(value=1, cache_time=False)
    with pytest.raises(TypeError, match="awaitable results"):
        resolver()
    assert resolver.expired
    assert all(inspect.getcoroutinestate(item) == inspect.CORO_CLOSED for item in created)
