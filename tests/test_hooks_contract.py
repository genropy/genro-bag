# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""Tests for on_loading / on_loaded hooks and self.kw property (issue #49).

Covers:
    - default identity hooks: behaviour identical to pre-change
    - self.kw property: returns on_loading(self._kw) on each access
    - subclass override of on_loading: visible inside load() via self.kw
    - subclass override of on_loaded: applied after _prepare_result
    - combination as_bag=True + custom on_loaded: hook sees converted Bag
    - sync and async paths
    - reactive regression: param change still compares against self._kw
"""

import pytest

from genro_bag import Bag
from genro_bag.resolver import BagCbResolver, BagResolver, BagSyncResolver


class TestDefaultIdentity:
    """Default on_loading / on_loaded are identity — zero behaviour change."""

    def test_kw_returns_underlying_kw_by_default(self):
        """self.kw returns self._kw unchanged when on_loading is identity."""
        resolver = BagCbResolver(lambda x: x, x=42)
        assert resolver.kw["x"] == 42
        assert resolver.kw == resolver._kw

    def test_kw_accesses_dont_mutate_state(self):
        """Reading self.kw does not mutate self._kw."""
        resolver = BagCbResolver(lambda x: x, x=42)
        snapshot = dict(resolver._kw)
        _ = resolver.kw
        _ = resolver.kw
        assert resolver._kw == snapshot

    def test_on_loaded_identity_by_default(self):
        """on_loaded returns result unchanged by default."""
        resolver = BagCbResolver(lambda: "hello")
        assert resolver() == "hello"


class TestOnLoadingOverride:
    """Subclass overrides on_loading — load() sees transformed kwargs."""

    def test_on_loading_transforms_visible_in_load(self):
        """A subclass that doubles a param in on_loading sees it in load()."""

        class DoublingResolver(BagSyncResolver):
            class_kwargs = {"base": 0, "as_bag": False}

            def on_loading(self, kw):
                return {**kw, "base": kw["base"] * 2}

            def load(self):
                return self.kw["base"]

        resolver = DoublingResolver(base=10)
        assert resolver() == 20

    def test_on_loading_must_return_complete_dict(self):
        """Consumer contract: on_loading must return a complete dict.

        url_resolver and BagCbResolver iterate over self.kw.items(); a
        partial delta would drop keys.
        """

        class PartialResolver(BagSyncResolver):
            class_kwargs = {"a": None, "b": None, "as_bag": False}

            def on_loading(self, kw):
                # INTENTIONAL BAD: only returns "a", loses "b"
                return {"a": kw["a"]}

            def load(self):
                # Access "b" — will raise KeyError because on_loading dropped it
                return self.kw["b"]

        resolver = PartialResolver(a=1, b=2)
        with pytest.raises(KeyError):
            resolver()

    def test_underlying_state_not_touched_by_on_loading(self):
        """on_loading returns a transformed dict, but self._kw stays raw."""

        class XFormResolver(BagSyncResolver):
            class_kwargs = {"v": 0, "as_bag": False}

            def on_loading(self, kw):
                return {**kw, "v": 999}

            def load(self):
                return self.kw["v"]

        resolver = XFormResolver(v=5)
        _ = resolver()
        assert resolver._kw["v"] == 5  # raw state untouched


class TestOnLoadedOverride:
    """Subclass overrides on_loaded — transforms the produced result."""

    def test_on_loaded_wraps_result(self):
        """on_loaded override wraps the load result."""

        class WrappingResolver(BagSyncResolver):
            class_kwargs = {"as_bag": False}

            def on_loaded(self, result):
                return {"wrapped": result}

            def load(self):
                return "payload"

        resolver = WrappingResolver()
        assert resolver() == {"wrapped": "payload"}

    def test_on_loaded_runs_after_as_bag_conversion(self):
        """When as_bag=True, on_loaded receives the converted Bag."""

        class InspectingResolver(BagSyncResolver):
            class_kwargs = {"as_bag": True}

            received_type = None

            def on_loaded(self, result):
                InspectingResolver.received_type = type(result)
                return result

            def load(self):
                return {"a": 1, "b": 2}

        bag = Bag()
        bag.set_item("data", InspectingResolver())
        _ = bag["data"]
        assert InspectingResolver.received_type is Bag


class TestAsyncPath:
    """Hooks work in async resolvers too."""

    @pytest.mark.asyncio
    async def test_on_loading_visible_in_async_load(self):
        """on_loading transformations reach async_load via self.kw."""

        class AsyncDoubler(BagResolver):
            class_kwargs = {"base": 0, "as_bag": False}

            def on_loading(self, kw):
                return {**kw, "base": kw["base"] * 2}

            async def async_load(self):
                return self.kw["base"]

        resolver = AsyncDoubler(base=7)
        result = await resolver()
        assert result == 14

    @pytest.mark.asyncio
    async def test_on_loaded_in_async(self):
        """on_loaded runs in async path too."""

        class AsyncWrapper(BagResolver):
            class_kwargs = {"as_bag": False}

            def on_loaded(self, result):
                return f"wrapped:{result}"

            async def async_load(self):
                return "payload"

        resolver = AsyncWrapper()
        assert (await resolver()) == "wrapped:payload"


class TestReactiveRegression:
    """Reactive trigger works coherently with on_loading transformations."""

    @pytest.mark.asyncio
    async def test_reactive_refresh_applies_on_loading(self):
        """After a reactive refresh, load() sees on_loading applied to current state.

        on_loading is an execution-time transformation. It does not affect the
        reactive detection logic (which compares raw attrs), but each refresh
        passes the current raw state through on_loading before load().
        """
        import asyncio as _asyncio

        class TransformingResolver(BagSyncResolver):
            class_kwargs = {"base": 0, "as_bag": False, "reactive": True}

            def on_loading(self, kw):
                return {**kw, "base": kw["base"] + 1000}

            def load(self):
                return self.kw["base"]

        bag = Bag()
        bag.set_backref()
        bag.set_item("data", TransformingResolver(base=0))
        node = bag.get_node("data")

        # Initial load: on_loading(base=0) → 1000
        assert bag["data"] == 1000

        # Change via set_attr: triggers reactive refresh
        node.set_attr(base=5)
        await _asyncio.sleep(0)  # let coalesced refresh run

        # New effective value is 5; on_loading(5) = 1005
        assert bag["data"] == 1005
