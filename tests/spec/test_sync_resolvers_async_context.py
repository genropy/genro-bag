"""Spec test: CPU-only resolvers (subclass of BagSyncResolver) do not
return coroutines when resolved inside an active event loop.

Regression of the bug documented in issue #59: EnvResolver extended
BagResolver and in async context the base class policy wrapped
load() in asyncio.to_thread, returning a coroutine instead of the value.

Contract:
- EnvResolver, UuidResolver, BagCbResolver (with sync callback) are
  sync-only: the resolved value is always the direct value, never a
  coroutine, even inside an event loop.
- BagAsyncCbResolver is async by design: returns a coroutine to await.
- BagCbResolver rejects async callback at constructor (TypeError).
- BagAsyncCbResolver rejects sync callback at constructor (TypeError).

## Scale

1. EnvResolver in async context                     returns str/value, not coroutine
2. UuidResolver in async context                    returns str, not coroutine
3. BagCbResolver (sync callback) in async context   returns value, not coroutine
4. BagCbResolver with async callback                TypeError at constructor
5. BagAsyncCbResolver with sync callback            TypeError at constructor
6. BagAsyncCbResolver in async context              awaited returns the value
"""

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
        with pytest.raises(TypeError, match="requires an async"):
            BagAsyncCbResolver(lambda: 1)


# =============================================================================
# 6. BagAsyncCbResolver in async context
# =============================================================================


class TestBagAsyncCbResolverInAsyncContext:
    @pytest.mark.asyncio
    async def test_async_callback_awaited_returns_value(self):
        async def async_cb():
            return "async-value"

        bag = Bag()
        bag["v"] = BagAsyncCbResolver(async_cb)
        result = bag["v"]
        # In async context the resolver returns a coroutine to be awaited.
        if asyncio.iscoroutine(result):
            result = await result
        assert result == "async-value"
