"""Spec test: i resolver CPU-only (subclass di BagSyncResolver) non
restituiscono coroutine quando risolti dentro un event loop attivo.

Regressione del bug documentato in issue #59: EnvResolver estendeva
BagResolver e in contesto async la policy della base class wrappava
load() in asyncio.to_thread, ritornando una coroutine invece del valore.

Contratto:
- EnvResolver, UuidResolver, BagCbResolver (con callback sync) sono
  sync-only: il valore risolto e' sempre il valore diretto, mai una
  coroutine, anche dentro un event loop.
- BagAsyncCbResolver e' async by design: torna una coroutine da awaitare.
- BagCbResolver rifiuta callback async al costruttore (TypeError).
- BagAsyncCbResolver rifiuta callback sync al costruttore (TypeError).

## Scala

1. EnvResolver in async context                     ritorna str/valore, non coroutine
2. UuidResolver in async context                    ritorna str, non coroutine
3. BagCbResolver (sync callback) in async context   ritorna valore, non coroutine
4. BagCbResolver con callback async                 TypeError al costruttore
5. BagAsyncCbResolver con callback sync             TypeError al costruttore
6. BagAsyncCbResolver in async context              awaited restituisce il valore
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
