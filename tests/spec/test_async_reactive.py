"""Spec test: Bag - uso asincrono e reattivita'.

Dipende da test_basic.py, test_resolvers.py, test_subscriptions.py.

Questo modulo raccoglie i test che richiedono un event loop attivo:

- resolver async (callback coroutine)
- reset(refresh=True) e il suo scheduling al prossimo tick
- reactive=True: refresh automatico sul cambio di attributo
- interval=N: timer di background che ricarica periodicamente
- subscribe(timer=..., interval=...) come osservatore temporale

I test sono marcati @pytest.mark.asyncio. Il loop attivo e' richiesto per:
1. is_async_context() deve essere True per far partire interval/reactive.
2. reset(refresh=True) usa loop.call_soon per coalescenza.
3. async_load() restituisce coroutine che vanno awaited.

## Scala

1.  Resolver async in contesto async           await bag[path]
2.  reset() lazy                                nessun evento, prossimo pull ricarica
3.  reset(refresh=True) emette update event
4.  reset(refresh=True) in sync                 RuntimeError
5.  reset(refresh=True) su read_only            ValueError
6.  reactive=True                               refresh su set_attr
7.  interval in sync                            RuntimeError
8.  interval in async                           timer parte, callback eseguito
9.  subscribe(timer=..., interval=...)          callback temporale
10. coalescing multipli trigger                 un solo refresh per burst
"""

from __future__ import annotations

import asyncio

import pytest

from genro_bag import Bag
from genro_bag.resolvers import BagCbResolver


# =============================================================================
# 1. Resolver async in contesto async
# =============================================================================


class TestAsyncResolverInAsyncContext:
    @pytest.mark.asyncio
    async def test_async_callback_awaited(self):
        """Un callback async fornisce una coroutine che va awaited."""

        async def async_value():
            return "async-result"

        bag = Bag()
        bag["v"] = BagCbResolver(async_value)
        result = bag["v"]
        assert asyncio.iscoroutine(result)
        assert await result == "async-result"

    @pytest.mark.asyncio
    async def test_async_callback_with_kwargs_awaited(self):
        """Il callback async riceve kwargs e ritorna coroutine."""

        async def async_add(x, y):
            return x + y

        bag = Bag()
        bag["s"] = BagCbResolver(async_add, x=7, y=3)
        assert await bag["s"] == 10


# =============================================================================
# 2. reset() lazy - default
# =============================================================================


class TestResetLazy:
    def test_reset_does_not_emit_event(self):
        """reset() default (refresh=False) non emette update events."""
        bag = Bag()
        bag["d"] = BagCbResolver(lambda: 42, cache_time=False)
        events: list = []
        bag.subscribe("w", update=lambda **kw: events.append(kw))

        _ = bag["d"]  # prime cache
        resolver = bag.get_resolver("d")
        resolver.reset()

        assert events == []

    def test_reset_invalidates_cache_for_next_pull(self):
        """Dopo reset(), il prossimo accesso richiama il callback."""
        counter = {"n": 0}

        def cb():
            counter["n"] += 1
            return counter["n"]

        bag = Bag()
        bag["d"] = BagCbResolver(cb, cache_time=False)
        assert bag["d"] == 1
        assert bag["d"] == 1  # cached
        bag.get_resolver("d").reset()
        assert bag["d"] == 2


# =============================================================================
# 3. reset(refresh=True) - eager
# =============================================================================


class TestResetRefreshTrue:
    @pytest.mark.asyncio
    async def test_reset_refresh_true_emits_update_event(self):
        """reset(refresh=True) pianifica un reload che emette update event.

        Nota: NON si fa prime con await in contesto async perche' l'allineamento
        dello stato interno del resolver richiede che il primo load venga
        eseguito dal refresh (documentato in test_reactive_contract).
        """
        counter = {"n": 0}

        def cb():
            counter["n"] += 1
            return counter["n"]

        bag = Bag()
        bag.set_backref()
        bag["d"] = BagCbResolver(cb, cache_time=False)
        _ = bag["d"]  # prime (coroutine lasciata non-awaited di proposito)

        events: list = []
        bag.subscribe("w", update=lambda **kw: events.append(kw["evt"]))

        bag.get_resolver("d").reset(refresh=True)
        for _ in range(4):
            await asyncio.sleep(0)

        assert len(events) >= 1
        # cleanup per stoppare l'eventuale timer
        bag.get_resolver("d").parent_node = None

    @pytest.mark.asyncio
    async def test_reset_refresh_true_writes_new_value_to_node(self):
        """Dopo reset(refresh=True), il static_value del nodo e' il valore nuovo."""
        counter = {"n": 0}

        async def cb():
            counter["n"] += 1
            return counter["n"]

        bag = Bag()
        bag["d"] = BagCbResolver(cb, cache_time=False)
        assert await bag["d"] == 1

        bag.get_resolver("d").reset(refresh=True)
        for _ in range(4):
            await asyncio.sleep(0)

        assert bag.get_item("d", static=True) == 2
        bag.get_resolver("d").parent_node = None


# =============================================================================
# 4. reset(refresh=True) in sync -> RuntimeError
# =============================================================================


class TestResetRefreshSyncRejection:
    def test_refresh_in_sync_raises_runtime_error(self):
        """reset(refresh=True) fuori da un event loop solleva RuntimeError."""
        bag = Bag()
        bag["d"] = BagCbResolver(lambda: 1, cache_time=False)
        with pytest.raises(RuntimeError, match="async context"):
            bag.get_resolver("d").reset(refresh=True)


# =============================================================================
# 5. reset(refresh=True) su read_only -> ValueError
# =============================================================================


class TestResetRefreshReadOnly:
    def test_refresh_on_read_only_raises_value_error(self):
        """reset(refresh=True) su resolver read_only solleva ValueError."""
        resolver = BagCbResolver(lambda: 1, read_only=True)
        with pytest.raises(ValueError, match="read_only"):
            resolver.reset(refresh=True)


# =============================================================================
# 6. reactive=True - refresh automatico su set_attr
# =============================================================================


class TestReactive:
    @pytest.mark.asyncio
    async def test_set_attr_triggers_refresh(self):
        """reactive=True: cambiare un attr schedula un refresh (update event)."""
        counter = {"n": 0}

        def cb(factor):
            counter["n"] += 1
            return counter["n"] * factor

        bag = Bag()
        bag.set_backref()
        bag["d"] = BagCbResolver(cb, factor=2, cache_time=False, reactive=True)
        _ = bag["d"]  # prime coroutine, non-awaited (vedi docstring altro test)

        events: list = []
        bag.subscribe("w", update=lambda **kw: events.append(kw["evt"]))

        bag.set_attr("d", factor=10)

        for _ in range(4):
            await asyncio.sleep(0)

        # almeno un evento update generato dal refresh
        assert len(events) >= 1
        bag.get_resolver("d").parent_node = None


# =============================================================================
# 7. interval in sync -> RuntimeError
# =============================================================================


class TestIntervalSyncRejection:
    def test_interval_in_sync_raises(self):
        """interval=N in contesto sync solleva RuntimeError all'attach."""
        bag = Bag()
        with pytest.raises(RuntimeError, match="async context"):
            bag["d"] = BagCbResolver(lambda: 1, interval=1)


# =============================================================================
# 8. interval in async - timer parte
# =============================================================================


class TestIntervalAsync:
    @pytest.mark.asyncio
    async def test_interval_timer_fires_and_refreshes_value(self):
        """Un resolver con interval=0.01 aggiorna il nodo almeno una volta."""
        counter = {"n": 0}

        def cb():
            counter["n"] += 1
            return counter["n"]

        bag = Bag()
        bag["d"] = BagCbResolver(cb, interval=0.01, cache_time=False)
        # wait per qualche tick
        for _ in range(10):
            await asyncio.sleep(0.01)

        # il callback e' stato chiamato almeno una volta dal timer
        assert counter["n"] >= 1
        # cleanup
        bag.get_resolver("d").interval = None


# =============================================================================
# 9. subscribe(timer=..., interval=...)
# =============================================================================


class TestTimerSubscription:
    @pytest.mark.asyncio
    async def test_timer_callback_fires_at_interval(self):
        """subscribe(timer=cb, interval=0.01) invoca cb dopo il primo tick."""
        hits: list = []
        bag = Bag()
        bag.subscribe("t1", timer=lambda **kw: hits.append(kw["evt"]), interval=0.01)

        for _ in range(10):
            await asyncio.sleep(0.01)

        assert len(hits) >= 1
        assert all(evt == "tmr" for evt in hits)
        # cleanup del timer registrato
        bag.unsubscribe("t1", timer=True)

    @pytest.mark.asyncio
    async def test_unsubscribe_timer_stops_ticks(self):
        """unsubscribe(timer=True) ferma i tick successivi."""
        hits: list = []
        bag = Bag()
        bag.subscribe("t1", timer=lambda **kw: hits.append(1), interval=0.01)

        for _ in range(3):
            await asyncio.sleep(0.01)
        count_before = len(hits)

        bag.unsubscribe("t1", timer=True)

        for _ in range(5):
            await asyncio.sleep(0.01)

        # nessun tick aggiuntivo DOPO la cancellazione
        # (tolleriamo 1 tick in flight gia' schedulato dal loop)
        assert len(hits) - count_before <= 1


# =============================================================================
# 10. Coalescing - multipli trigger in stesso tick
# =============================================================================


class TestCoalescing:
    @pytest.mark.asyncio
    async def test_multiple_resets_in_same_tick_run_one_refresh(self):
        """Tre reset(refresh=True) nello stesso tick eseguono un solo refresh."""
        counter = {"n": 0}

        def cb():
            counter["n"] += 1
            return counter["n"]

        bag = Bag()
        bag.set_backref()
        bag["d"] = BagCbResolver(cb, cache_time=False)
        _ = bag["d"]  # prime (non-awaited, vedi test sopra)

        r = bag.get_resolver("d")
        # tre trigger concentrati nello stesso tick sincrono
        r.reset(refresh=True)
        r.reset(refresh=True)
        r.reset(refresh=True)

        for _ in range(4):
            await asyncio.sleep(0)

        # solo un refresh eseguito in totale (coalescenza)
        assert counter["n"] == 1
        bag.get_resolver("d").parent_node = None
