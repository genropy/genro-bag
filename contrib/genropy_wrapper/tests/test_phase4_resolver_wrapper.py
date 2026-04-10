"""Phase 4 tests: BagResolver wrapper + event edge cases.

Tests cover:
- BagResolver wrapper class: __init_subclass__ translation, camelCase property aliases,
  instanceKwargs, resolverSerialize
- BagCbResolver wrapper: 'method' positional arg compatibility
- Event edge cases: propagation with backref, multiple subscriptions, callback kwargs
- Cross-implementation resolver comparison
"""

import pytest
import genro_bag
from gnr.core.gnrbag import Bag as OriginalBag
from gnr.core.gnrbag import BagCbResolver as OrigBagCbResolver
from genro_bag.resolver import BagCbResolver as NewBagCbResolver
from replacement.gnrbag import (
    Bag as WrapperBag,
    BagCbResolver as WrapperBagCbResolver,
    BagResolver as WrapperBagResolver,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _impl_name(cls):
    """Derive implementation name from a Bag class."""
    module = cls.__module__
    if module == "gnr.core.gnrbag":
        return "original"
    elif module.startswith("genro_bag"):
        return "new"
    return "wrapper"


# ===========================================================================
# SECTION A: BagResolver wrapper — __init_subclass__ and camelCase aliases
# ===========================================================================


class TestResolverInitSubclass:
    """Test that __init_subclass__ translates classKwargs/classArgs to snake_case."""

    def test_class_kwargs_translated(self):
        """Subclass with classKwargs should get translated class_kwargs."""
        class MyResolver(WrapperBagResolver):
            classKwargs = {"cacheTime": 300, "readOnly": True, "myParam": "default"}

            def load(self):
                return 42

        assert MyResolver.class_kwargs == {
            "cache_time": 300,
            "read_only": True,
            "myParam": "default",
        }

    def test_class_args_translated(self):
        """Subclass with classArgs should get translated class_args."""
        class MyResolver(WrapperBagResolver):
            classArgs = ["url", "format"]

            def load(self):
                return None

        assert MyResolver.class_args == ["url", "format"]

    def test_subclass_instantiation(self):
        """Subclass with classKwargs/classArgs should instantiate correctly."""
        class CalcResolver(WrapperBagResolver):
            classKwargs = {"cacheTime": 0, "readOnly": False, "multiplier": 2}
            classArgs = ["base"]

            def load(self):
                return self._kw["base"] * self._kw["multiplier"]

        r = CalcResolver(10, multiplier=3)
        assert r() == 30

    def test_subclass_with_camel_case_kwargs_in_init(self):
        """Passing cacheTime= in __init__ should be translated to cache_time."""
        class MyResolver(WrapperBagResolver):
            classKwargs = {"cacheTime": 0, "readOnly": False}

            def load(self):
                return "result"

        r = MyResolver(cacheTime=600)
        assert r._kw["cache_time"] == 600


class TestResolverCamelCaseProperties:
    """Test camelCase property aliases on BagResolver wrapper."""

    def test_cache_time_property(self):
        """cacheTime property should read/write cache_time."""
        class MyResolver(WrapperBagResolver):
            classKwargs = {"cacheTime": 0, "readOnly": False}

            def load(self):
                return "val"

        r = MyResolver()
        assert r.cacheTime == 0
        r.cacheTime = 120
        assert r.cacheTime == 120
        assert r._kw["cache_time"] == 120

    def test_read_only_property(self):
        """readOnly property should read/write read_only."""
        class MyResolver(WrapperBagResolver):
            classKwargs = {"cacheTime": 0, "readOnly": True}

            def load(self):
                return "val"

        r = MyResolver()
        assert r.readOnly is True
        r.readOnly = False
        assert r.readOnly is False

    def test_parent_node_property(self):
        """parentNode property should alias parent_node."""
        b = WrapperBag()
        resolver = WrapperBagCbResolver(lambda: 42)
        b.set_item("x", resolver)
        node = b.get_node("x")
        assert resolver.parentNode is node

    def test_instance_kwargs(self):
        """instanceKwargs should return dict of current parameter values."""
        class MyResolver(WrapperBagResolver):
            classKwargs = {"cacheTime": 300, "readOnly": True, "format": "json"}
            classArgs = ["url"]

            def load(self):
                return None

        r = MyResolver("http://example.com", format="xml")
        ik = r.instanceKwargs
        assert ik["url"] == "http://example.com"
        assert ik["cacheTime"] == 300
        assert ik["readOnly"] is True
        assert ik["format"] == "xml"


class TestResolverSerialize:
    """Test resolverSerialize() compatibility method."""

    def test_serialize_format(self):
        """resolverSerialize should return dict with original format keys."""
        class MyResolver(WrapperBagResolver):
            classKwargs = {"cacheTime": 60, "readOnly": False}
            classArgs = ["path"]

            def load(self):
                return None

        r = MyResolver("/data/file.txt")
        data = r.resolverSerialize()

        assert "resolverclass" in data
        assert "resolvermodule" in data
        assert "args" in data
        assert "kwargs" in data
        assert data["resolverclass"] == "MyResolver"
        assert data["args"] == ["/data/file.txt"]
        assert data["kwargs"]["cacheTime"] == 60

    def test_serialize_cb_resolver(self):
        """BagCbResolver wrapper should serialize correctly."""
        r = WrapperBagCbResolver(lambda: "hello")
        data = r.resolverSerialize()
        assert data["resolverclass"] == "BagCbResolver"


# ===========================================================================
# SECTION B: BagCbResolver wrapper — 'method' parameter compatibility
# ===========================================================================


class TestBagCbResolverWrapper:
    """Test BagCbResolver wrapper with 'method' positional arg."""

    def test_method_positional_arg(self):
        """First positional arg should be stored and callable."""
        r = WrapperBagCbResolver(lambda: "hello")
        assert r() == "hello"

    def test_method_with_kwargs(self):
        """Extra kwargs should be passed to callback on load."""
        def compute(x=1, y=2):
            return x + y

        r = WrapperBagCbResolver(compute, x=10, y=20)
        assert r() == 30

    def test_resolver_on_wrapper_bag(self):
        """BagCbResolver wrapper should work when set on a Bag."""
        b = WrapperBag()
        b.setCallBackItem("calc", lambda x=5: x * 2)
        assert b["calc"] == 10

    def test_set_callback_item_with_kwargs(self):
        """setCallBackItem with extra kwargs should pass them to callback."""
        b = WrapperBag()
        b.setCallBackItem("greeting", lambda name="world": f"hello {name}",
                          name="test")
        assert b["greeting"] == "hello test"


# ===========================================================================
# SECTION C: Event edge cases
# ===========================================================================


class TestEventPropagationBackref:
    """Test event propagation through backref hierarchy."""

    def test_parent_sees_child_insert(self, bag_class_camel):
        """With backref, parent should see insert events from child Bag."""
        parent = bag_class_camel()
        parent["child"] = bag_class_camel()
        parent.setBackRef()
        events = []
        parent.subscribe(subscriberId="parent_sub",
                         insert=lambda **kw: events.append(("ins", kw.get("pathlist"))))
        parent["child"]["new_item"] = 42
        assert len(events) >= 1
        # The pathlist should include the child path
        pathlist = events[0][1]
        if pathlist is not None:
            assert "child" in pathlist or "new_item" in pathlist

    def test_parent_sees_child_update(self, bag_class_camel):
        """With backref, parent should see update events from child Bag."""
        parent = bag_class_camel()
        parent["child"] = bag_class_camel()
        parent["child"]["x"] = 1
        parent.setBackRef()
        events = []
        parent.subscribe(subscriberId="parent_sub",
                         update=lambda **kw: events.append("upd"))
        parent["child"]["x"] = 99
        assert len(events) >= 1


class TestMultipleSubscriptions:
    """Test multiple subscriptions on the same Bag."""

    def test_two_subscribers_both_fire(self, bag_class_camel):
        """Two different subscriber IDs should both receive events."""
        b = bag_class_camel()
        events_a = []
        events_b = []
        b.subscribe(subscriberId="sub_a", insert=lambda **kw: events_a.append(1))
        b.subscribe(subscriberId="sub_b", insert=lambda **kw: events_b.append(1))
        b["x"] = 1
        assert len(events_a) == 1
        assert len(events_b) == 1

    def test_unsubscribe_one_keeps_other(self, bag_class_camel):
        """Unsubscribing one subscriber should not affect the other."""
        b = bag_class_camel()
        events_a = []
        events_b = []
        b.subscribe(subscriberId="sub_a", insert=lambda **kw: events_a.append(1))
        b.subscribe(subscriberId="sub_b", insert=lambda **kw: events_b.append(1))
        b.unsubscribe(subscriberId="sub_a", insert=True)
        b["x"] = 1
        assert len(events_a) == 0
        assert len(events_b) == 1


class TestEventCallbackKwargs:
    """Test that event callbacks receive correct kwargs."""

    def test_insert_callback_has_evt(self, bag_class_camel):
        """Insert callback should receive evt='ins'."""
        b = bag_class_camel()
        events = []
        b.subscribe(subscriberId="test", insert=lambda **kw: events.append(kw))
        b["x"] = 1
        assert events[0]["evt"] == "ins"

    def test_update_callback_has_oldvalue(self, bag_class_camel):
        """Update callback should receive oldvalue with previous value."""
        b = bag_class_camel()
        b["x"] = 1
        events = []
        b.subscribe(subscriberId="test", update=lambda **kw: events.append(kw))
        b["x"] = 99
        assert len(events) >= 1
        assert "oldvalue" in events[0]
        assert events[0]["oldvalue"] == 1

    def test_delete_callback_has_node(self, bag_class_camel):
        """Delete callback should receive the deleted node."""
        b = bag_class_camel()
        b["x"] = 42
        events = []
        b.subscribe(subscriberId="test", delete=lambda **kw: events.append(kw))
        b.pop("x")
        assert len(events) == 1
        assert "node" in events[0]


# ===========================================================================
# SECTION D: Cross-implementation resolver comparison
# ===========================================================================


class TestResolverCrossImpl:
    """Compare resolver behavior across implementations."""

    def test_cb_resolver_same_result_all_3(self, bag_class):
        """BagCbResolver should produce the same result on all implementations."""
        b = bag_class()
        impl = _impl_name(bag_class)
        if impl == "original":
            resolver = OrigBagCbResolver(lambda x=10: x * 2)
        elif impl == "new":
            resolver = NewBagCbResolver(lambda x=10: x * 2)
        else:
            resolver = WrapperBagCbResolver(lambda x=10: x * 2)
        b.set_item("calc", resolver) if impl != "original" else b.setItem("calc", None, resolver=resolver)
        # Original sets resolver differently but result should be same
        if impl == "original":
            # Original setItem with resolver= doesn't attach properly
            # Use setCallBackItem instead
            b2 = bag_class()
            b2.setCallBackItem("calc", lambda x=10: x * 2)
            result = b2["calc"]
        else:
            result = b["calc"]
        assert result == 20

    def test_set_callback_item_camel(self, bag_class_camel):
        """setCallBackItem should work on original and wrapper."""
        b = bag_class_camel()
        b.setCallBackItem("val", lambda: "computed")
        assert b["val"] == "computed"

    def test_get_resolver_returns_resolver(self):
        """getResolver should return the resolver on wrapper.

        Only tested on wrapper — original's BagNode lacks getResolver().
        """
        b = WrapperBag()
        b.setCallBackItem("calc", lambda: 42)
        r = b.getResolver("calc")
        assert r is not None
