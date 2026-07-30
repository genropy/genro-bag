"""Spec test: Bag - async usage and reactivity.

Depends on test_basic.py, test_resolvers.py, test_subscriptions.py.

This module collects tests that require an active event loop:

- async resolver (coroutine callback)
- reset(refresh=True) and its scheduling at the next tick
- reactive=True: automatic refresh on attribute change
- interval=N: background timer that periodically reloads
- subscribe(timer=..., interval=...) as a temporal observer

Tests are marked @pytest.mark.asyncio. The active loop is required for:
1. is_async_context() must be True to start interval/reactive.
2. reset(refresh=True) uses loop.call_soon for coalescing.
3. async_load() returns coroutines that must be awaited.

## Scale

1.  Async resolver in async context            await bag[path]
2.  reset() lazy                                no event, next pull reloads
3.  reset(refresh=True) emits update event
4.  reset(refresh=True) in sync                 RuntimeError
5.  reset(refresh=True) on read_only            ValueError
6.  reactive=True                               refresh on set_attr
7.  interval in sync                            RuntimeError
8.  interval in async                           timer starts, callback executed
9.  subscribe(timer=..., interval=...)          temporal callback
10. coalescing multiple triggers                one refresh per burst
"""

from __future__ import annotations

import asyncio

import pytest

from genro_bag import Bag
from genro_bag.resolvers import BagAsyncCbResolver, BagCbResolver

# =============================================================================
# 1. Resolver async in contesto async
# =============================================================================


class TestAsyncResolverInAsyncContext:
    @pytest.mark.asyncio
    async def test_async_callback_awaited(self):
        """An async callback provides a coroutine to await."""

        async def async_value():
            return "async-result"

        bag = Bag()
        bag["v"] = BagAsyncCbResolver(async_value)
        result = bag["v"]
        assert asyncio.iscoroutine(result)
        assert await result == "async-result"

    @pytest.mark.asyncio
    async def test_async_callback_with_kwargs_awaited(self):
        """The async callback receives kwargs and returns a coroutine."""

        async def async_add(x, y):
            return x + y

        bag = Bag()
        bag["s"] = BagAsyncCbResolver(async_add, x=7, y=3)
        assert await bag["s"] == 10


# =============================================================================
# 2. reset() lazy - default
# =============================================================================


class TestResetLazy:
    def test_reset_does_not_emit_event(self):
        """reset() default (refresh=False) does not emit update events."""
        bag = Bag()
        bag["d"] = BagCbResolver(lambda: 42, cache_time=False)
        events: list = []
        bag.subscribe("w", update=lambda **kw: events.append(kw))

        _ = bag["d"]  # prime cache
        resolver = bag.get_resolver("d")
        resolver.reset()

        assert events == []

    def test_reset_invalidates_cache_for_next_pull(self):
        """After reset(), the next access calls the callback."""
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
        """reset(refresh=True) schedules a reload that emits an update event.

        Note: we do NOT prime with await in async context because the alignment
        of the resolver's internal state requires that the first load be
        executed by the refresh (documented in test_reactive_contract).
        """
        counter = {"n": 0}

        def cb():
            counter["n"] += 1
            return counter["n"]

        bag = Bag()
        bag.set_backref()
        bag["d"] = BagCbResolver(cb, cache_time=False)
        _ = bag["d"]  # prime (coroutine left unawaited on purpose)

        events: list = []
        bag.subscribe("w", update=lambda **kw: events.append(kw["evt"]))

        bag.get_resolver("d").reset(refresh=True)
        for _ in range(4):
            await asyncio.sleep(0)

        assert len(events) >= 1
        # cleanup to stop any timer
        bag.get_resolver("d").parent_node = None

    @pytest.mark.asyncio
    async def test_reset_refresh_true_writes_new_value_to_node(self):
        """After reset(refresh=True), the node's static_value is the new value."""
        counter = {"n": 0}

        async def cb():
            counter["n"] += 1
            return counter["n"]

        bag = Bag()
        bag["d"] = BagAsyncCbResolver(cb, cache_time=False)
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
        """reset(refresh=True) outside an event loop raises RuntimeError."""
        bag = Bag()
        bag["d"] = BagCbResolver(lambda: 1, cache_time=False)
        with pytest.raises(RuntimeError, match="async context"):
            bag.get_resolver("d").reset(refresh=True)


# =============================================================================
# 5. reset(refresh=True) su read_only -> ValueError
# =============================================================================


class TestResetRefreshReadOnly:
    def test_refresh_on_read_only_raises_value_error(self):
        """reset(refresh=True) on read_only resolver raises ValueError."""
        resolver = BagCbResolver(lambda: 1, read_only=True)
        with pytest.raises(ValueError, match="read_only"):
            resolver.reset(refresh=True)


# =============================================================================
# 6. reactive=True - refresh automatico su set_attr
# =============================================================================


class TestReactive:
    @pytest.mark.asyncio
    async def test_set_attr_triggers_refresh(self):
        """reactive=True: changing an attr schedules a refresh (update event)."""
        counter = {"n": 0}

        def cb(factor):
            counter["n"] += 1
            return counter["n"] * factor

        bag = Bag()
        bag.set_backref()
        bag["d"] = BagCbResolver(cb, factor=2, cache_time=False, reactive=True)
        _ = bag["d"]  # prime coroutine, unawaited (see docstring in other test)

        events: list = []
        bag.subscribe("w", update=lambda **kw: events.append(kw["evt"]))

        bag.set_attr("d", factor=10)

        for _ in range(4):
            await asyncio.sleep(0)

        # at least one update event generated by the refresh
        assert len(events) >= 1
        bag.get_resolver("d").parent_node = None


# =============================================================================
# 7. interval in sync -> RuntimeError
# =============================================================================


class TestIntervalSyncRejection:
    def test_interval_in_sync_raises(self):
        """interval=N in sync context raises RuntimeError on attach."""
        bag = Bag()
        with pytest.raises(RuntimeError, match="async context"):
            bag["d"] = BagCbResolver(lambda: 1, interval=1)


# =============================================================================
# 8. interval in async - timer parte
# =============================================================================


class TestIntervalAsync:
    @pytest.mark.asyncio
    async def test_interval_timer_fires_and_refreshes_value(self):
        """A resolver with interval=0.01 updates the node at least once."""
        counter = {"n": 0}

        def cb():
            counter["n"] += 1
            return counter["n"]

        bag = Bag()
        bag["d"] = BagCbResolver(cb, interval=0.01, cache_time=False)
        # wait for a few ticks
        for _ in range(10):
            await asyncio.sleep(0.01)

        # the callback was called at least once by the timer
        assert counter["n"] >= 1
        # cleanup
        bag.get_resolver("d").interval = None


# =============================================================================
# 9. subscribe(timer=..., interval=...)
# =============================================================================


class TestTimerSubscription:
    @pytest.mark.asyncio
    async def test_timer_callback_fires_at_interval(self):
        """subscribe(timer=cb, interval=0.01) invokes cb after the first tick."""
        hits: list = []
        bag = Bag()
        bag.subscribe("t1", timer=lambda **kw: hits.append(kw["evt"]), interval=0.01)

        for _ in range(10):
            await asyncio.sleep(0.01)

        assert len(hits) >= 1
        assert all(evt == "tmr" for evt in hits)
        # cleanup of the registered timer
        bag.unsubscribe("t1", timer=True)

    @pytest.mark.asyncio
    async def test_unsubscribe_timer_stops_ticks(self):
        """unsubscribe(timer=True) stops subsequent ticks."""
        hits: list = []
        bag = Bag()
        bag.subscribe("t1", timer=lambda **kw: hits.append(1), interval=0.01)

        for _ in range(3):
            await asyncio.sleep(0.01)
        count_before = len(hits)

        bag.unsubscribe("t1", timer=True)

        for _ in range(5):
            await asyncio.sleep(0.01)

        # no additional ticks AFTER cancellation
        # (we tolerate 1 tick already scheduled by the loop)
        assert len(hits) - count_before <= 1


# =============================================================================
# 10. Coalescing - multipli trigger in stesso tick
# =============================================================================


class TestCoalescing:
    @pytest.mark.asyncio
    async def test_multiple_resets_in_same_tick_run_one_refresh(self):
        """Three reset(refresh=True) in the same tick execute one refresh.

        The first access to bag["d"] executes the sync callback (counter=1),
        then the three resets coalesce into a single refresh (counter=2). The
        test verifies the final count = 2, and that the three resets combined
        produced only one delta compared to the prime.
        """
        counter = {"n": 0}

        def cb():
            counter["n"] += 1
            return counter["n"]

        bag = Bag()
        bag.set_backref()
        bag["d"] = BagCbResolver(cb, cache_time=False)
        _ = bag["d"]  # prime: executes the sync callback once
        assert counter["n"] == 1

        r = bag.get_resolver("d")
        # three triggers concentrated in the same synchronous tick
        r.reset(refresh=True)
        r.reset(refresh=True)
        r.reset(refresh=True)

        for _ in range(4):
            await asyncio.sleep(0)

        # prime (1) + one coalesced refresh (1) = 2 total executions
        assert counter["n"] == 2
        bag.get_resolver("d").parent_node = None


# =============================================================================
# 11. Path traversal with resolver: 2x2 sync/async matrix
# =============================================================================
#
# The Bag must behave observably in all combinations of:
#   - execution context: sync (no loop) or async (loop running)
#   - resolver: sync or async callback
#
# Furthermore, the resolver can be:
#   - only on the leaf
#   - only in an intermediate position (returns a sub-Bag)
#   - in multiple positions along the path (chain of resolvers)
#
# Observable contract rule:
#   - In sync ctx: bag[path] always returns the final value (the Bag
#     resolves coroutines internally when needed).
#   - In async ctx: bag[path] on a path with a resolver can return a
#     coroutine that the user must await. The user can always close
#     with `while iscoroutine(v): v = await v`.
# =============================================================================


def _sub_bag_sync():
    """Sync callback that returns a sub-Bag."""
    sub = Bag()
    sub["leaf"] = "deep_value"
    return sub


async def _sub_bag_async():
    """Async callback that returns a sub-Bag."""
    await asyncio.sleep(0)
    sub = Bag()
    sub["leaf"] = "deep_value"
    return sub


def _scalar_sync():
    """Sync callback that returns a scalar (leaf case)."""
    return "leaf_sync"


async def _scalar_async():
    """Async callback that returns a scalar (leaf case)."""
    await asyncio.sleep(0)
    return "leaf_async"


async def _drain(value):
    """Utility: repeated await until the result is no longer a coroutine."""
    while asyncio.iscoroutine(value):
        value = await value
    return value


class TestPathTraversalIntermediateResolver:
    """Resolver in intermediate position: path 'middle.leaf' where 'middle' has
    a resolver that returns a sub-Bag with 'leaf' inside.
    """

    def test_ctx_sync_resolver_sync_returns_value(self):
        """sync ctx + intermediate sync resolver → final value directly."""
        root = Bag()
        root["middle"] = BagCbResolver(_sub_bag_sync)
        assert root["middle.leaf"] == "deep_value"

    def test_ctx_sync_resolver_async_returns_value(self):
        """sync ctx + intermediate async resolver → the Bag resolves internally."""
        root = Bag()
        root["middle"] = BagAsyncCbResolver(_sub_bag_async)
        # In sync context, the internal coroutine is resolved transparently
        assert root["middle.leaf"] == "deep_value"

    @pytest.mark.asyncio
    async def test_ctx_async_resolver_sync_returns_value_after_await(self):
        """async ctx + intermediate sync resolver → bag[path] is awaitable."""
        root = Bag()
        root["middle"] = BagCbResolver(_sub_bag_sync)
        v = await _drain(root["middle.leaf"])
        assert v == "deep_value"

    @pytest.mark.asyncio
    async def test_ctx_async_resolver_async_returns_value_after_await(self):
        """async ctx + intermediate async resolver → bag[path] is awaitable."""
        root = Bag()
        root["middle"] = BagAsyncCbResolver(_sub_bag_async)
        v = await _drain(root["middle.leaf"])
        assert v == "deep_value"


class TestPathTraversalLeafResolver:
    """Resolver in final position (leaf): direct path to a node with resolver.

    This is the case already covered by the suite, replicated here for the
    complete matrix.
    """

    def test_ctx_sync_leaf_sync(self):
        """sync ctx + leaf sync resolver."""
        root = Bag()
        root["leaf"] = BagCbResolver(_scalar_sync)
        assert root["leaf"] == "leaf_sync"

    def test_ctx_sync_leaf_async(self):
        """sync ctx + leaf async resolver → resolves internally."""
        root = Bag()
        root["leaf"] = BagAsyncCbResolver(_scalar_async)
        assert root["leaf"] == "leaf_async"

    @pytest.mark.asyncio
    async def test_ctx_async_leaf_sync(self):
        """async ctx + leaf sync resolver → direct value (not awaitable)."""
        root = Bag()
        root["leaf"] = BagCbResolver(_scalar_sync)
        v = await _drain(root["leaf"])
        assert v == "leaf_sync"

    @pytest.mark.asyncio
    async def test_ctx_async_leaf_async(self):
        """async ctx + leaf async resolver → awaitable."""
        root = Bag()
        root["leaf"] = BagAsyncCbResolver(_scalar_async)
        v = await _drain(root["leaf"])
        assert v == "leaf_async"


class TestPathTraversalChainedResolvers:
    """Multiple resolvers in chain along the path. Each intermediate resolver
    returns a Bag that contains the next resolver.
    """

    def test_two_resolvers_sync_then_sync_on_leaf(self):
        """path 'mid.leaf': intermediate sync resolver + leaf sync resolver."""
        def intermediate():
            inner = Bag()
            inner["leaf"] = BagCbResolver(_scalar_sync)
            return inner

        root = Bag()
        root["mid"] = BagCbResolver(intermediate)
        assert root["mid.leaf"] == "leaf_sync"

    def test_two_resolvers_async_then_sync_on_leaf_sync_ctx(self):
        """path 'mid.leaf': intermediate async resolver + leaf sync resolver, sync ctx."""
        async def intermediate():
            await asyncio.sleep(0)
            inner = Bag()
            inner["leaf"] = BagCbResolver(_scalar_sync)
            return inner

        root = Bag()
        root["mid"] = BagAsyncCbResolver(intermediate)
        assert root["mid.leaf"] == "leaf_sync"

    @pytest.mark.asyncio
    async def test_two_resolvers_mixed_async_ctx(self):
        """async ctx + two mixed resolvers (async intermediate + async leaf)."""
        async def intermediate():
            await asyncio.sleep(0)
            inner = Bag()
            inner["leaf"] = BagAsyncCbResolver(_scalar_async)
            return inner

        root = Bag()
        root["mid"] = BagAsyncCbResolver(intermediate)
        v = await _drain(root["mid.leaf"])
        assert v == "leaf_async"

    def test_three_resolvers_chain_all_sync_ctx(self):
        """path 'a.b.c' with 3 resolvers in chain (mixed types), sync ctx."""
        def leaf_cb():
            return "FINAL"

        def second_cb():
            b = Bag()
            b["c"] = BagCbResolver(leaf_cb)
            return b

        async def first_cb():
            await asyncio.sleep(0)
            b = Bag()
            b["b"] = BagCbResolver(second_cb)
            return b

        root = Bag()
        root["a"] = BagAsyncCbResolver(first_cb)
        # path: a (async) -> b (sync, returns Bag) -> c (sync leaf)
        assert root["a.b.c"] == "FINAL"

    @pytest.mark.asyncio
    async def test_three_resolvers_chain_all_async_ctx(self):
        """path 'a.b.c' with 3 resolvers in chain (mixed types), async ctx."""
        async def leaf_cb():
            await asyncio.sleep(0)
            return "FINAL_ASYNC"

        async def second_cb():
            await asyncio.sleep(0)
            b = Bag()
            b["c"] = BagAsyncCbResolver(leaf_cb)
            return b

        def first_cb():
            b = Bag()
            b["b"] = BagAsyncCbResolver(second_cb)
            return b

        root = Bag()
        root["a"] = BagCbResolver(first_cb)
        v = await _drain(root["a.b.c"])
        assert v == "FINAL_ASYNC"
