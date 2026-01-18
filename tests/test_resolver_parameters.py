# Copyright 2025 Softwell S.r.l. - Genropy Team
# Licensed under the Apache License, Version 2.0

"""Tests for resolver parameter handling - dynamic params from node attrs.

This tests the feature where resolver parameters can come from three sources
with priority (highest to lowest):
    1. call_kwargs: passed directly to resolver()
    2. node.attr: set via bag.set_attr()
    3. resolver._kw: default parameters from construction

Cache is automatically invalidated when effective parameters change.
"""

import pytest

from genro_bag import Bag
from genro_bag.resolvers import BagCbResolver


@pytest.fixture(autouse=True)
def reset_smartasync_cache():
    """Reset smartasync cache before each test."""
    from genro_bag.resolver import BagResolver

    if hasattr(BagCbResolver.load, "_smartasync_reset_cache"):
        BagCbResolver.load._smartasync_reset_cache()
    if hasattr(BagResolver.__call__, "_smartasync_reset_cache"):
        BagResolver.__call__._smartasync_reset_cache()
    yield


class TestResolverDefaultParams:
    """Tests for resolver using default parameters."""

    def test_callback_receives_default_params(self):
        """Callback receives parameters from construction."""

        def somma(a, b):
            return a + b

        resolver = BagCbResolver(somma, a=3, b=5)
        assert resolver() == 8

    def test_internal_params_not_passed_to_callback(self):
        """Internal params (cache_time, etc.) are not passed to callback."""

        def check_kwargs(**kw):
            assert "cache_time" not in kw
            assert "read_only" not in kw
            assert "callback" not in kw
            return kw

        resolver = BagCbResolver(check_kwargs, x=1, y=2, cache_time=60)
        result = resolver()
        assert result == {"x": 1, "y": 2}


class TestResolverNodeParams:
    """Tests for resolver reading parameters from node attributes."""

    def test_resolver_reads_from_node_attrs(self):
        """When attached to node, resolver reads params from node.attr."""

        def somma(a, b):
            return a + b

        bag = Bag()
        bag.set_item("calc", BagCbResolver(somma, a=3, b=5))

        # Default values
        assert bag["calc"] == 8

        # Change via node attribute
        bag.set_attr("calc", a=10)
        assert bag["calc"] == 15

        bag.set_attr("calc", b=20)
        assert bag["calc"] == 30

    def test_node_attrs_override_resolver_defaults(self):
        """Node attributes take priority over resolver defaults."""

        def multiply(x, y):
            return x * y

        bag = Bag()
        resolver = BagCbResolver(multiply, x=2, y=3)  # default: 2*3=6
        bag.set_item("mult", resolver)

        assert bag["mult"] == 6

        # Node attr overrides resolver default
        bag.set_attr("mult", x=10)
        assert bag["mult"] == 30  # 10*3

    def test_params_not_copied_to_node_at_assignment(self):
        """Resolver params are NOT copied to node.attr at assignment."""

        def somma(a, b):
            return a + b

        bag = Bag()
        bag.set_item("calc", BagCbResolver(somma, a=3, b=5))

        node = bag.get_node("calc")
        # Params should NOT be in node attributes
        assert "a" not in node.attr
        assert "b" not in node.attr


class TestResolverCallKwargs:
    """Tests for passing kwargs directly to resolver()."""

    def test_call_kwargs_override_all(self):
        """call_kwargs have highest priority."""

        def somma(a, b):
            return a + b

        bag = Bag()
        bag.set_item("calc", BagCbResolver(somma, a=3, b=5))

        # Default
        assert bag["calc"] == 8

        # Set node attr
        bag.set_attr("calc", a=10)
        assert bag["calc"] == 15

        # Call kwargs override even node attr
        node = bag.get_node("calc")
        assert node.resolver(a=100) == 105  # 100 + 5
        assert node.resolver(a=100, b=200) == 300

    def test_call_kwargs_temporary(self):
        """call_kwargs don't persist - next call uses normal priority."""

        def somma(a, b):
            return a + b

        resolver = BagCbResolver(somma, a=3, b=5)

        assert resolver() == 8
        assert resolver(a=100) == 105
        assert resolver() == 8  # back to default


class TestResolverCacheInvalidation:
    """Tests for automatic cache invalidation on param change."""

    def test_cache_invalidated_on_node_attr_change(self):
        """Changing node attr invalidates resolver cache."""
        call_count = 0

        def counter(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        bag = Bag()
        bag.set_item("data", BagCbResolver(counter, x=5, cache_time=-1))

        # First access loads
        assert bag["data"] == 10
        assert call_count == 1

        # Cached
        assert bag["data"] == 10
        assert call_count == 1

        # Change param via node attr - should invalidate cache
        bag.set_attr("data", x=7)
        assert bag["data"] == 14
        assert call_count == 2

        # New value cached
        assert bag["data"] == 14
        assert call_count == 2

    def test_cache_valid_when_same_params(self):
        """Cache remains valid when params unchanged."""
        call_count = 0

        def counter(x):
            nonlocal call_count
            call_count += 1
            return x

        bag = Bag()
        bag.set_item("data", BagCbResolver(counter, x=5, cache_time=-1))

        assert bag["data"] == 5
        assert call_count == 1

        # Set same value - cache should remain valid
        bag.set_attr("data", x=5)
        assert bag["data"] == 5
        assert call_count == 1  # no reload

    def test_call_kwargs_invalidate_cache(self):
        """Different call_kwargs invalidate cache."""
        call_count = 0

        def counter(x):
            nonlocal call_count
            call_count += 1
            return x

        resolver = BagCbResolver(counter, x=5, cache_time=-1)

        assert resolver() == 5
        assert call_count == 1

        assert resolver() == 5
        assert call_count == 1  # cached

        # Different call_kwargs - reload
        assert resolver(x=10) == 10
        assert call_count == 2

        # Back to original - reload (different params)
        assert resolver() == 5
        assert call_count == 3


class TestResolverParameterPriority:
    """Tests for parameter priority: call_kwargs > node.attr > resolver._kw"""

    def test_full_priority_chain(self):
        """All three sources work with correct priority."""

        def show(a, b, c):
            return f"a={a},b={b},c={c}"

        bag = Bag()
        bag.set_item("test", BagCbResolver(show, a=1, b=2, c=3))

        # All from resolver defaults
        assert bag["test"] == "a=1,b=2,c=3"

        # Set some node attrs
        bag.set_attr("test", a=10, b=20)
        assert bag["test"] == "a=10,b=20,c=3"

        # call_kwargs override
        node = bag.get_node("test")
        assert node.resolver(a=100) == "a=100,b=20,c=3"
        assert node.resolver(b=200) == "a=10,b=200,c=3"
        assert node.resolver(c=300) == "a=10,b=20,c=300"
        assert node.resolver(a=100, b=200, c=300) == "a=100,b=200,c=300"


class TestResolverInternalParams:
    """Tests that internal params are handled correctly."""

    def test_internal_params_in_class(self):
        """Verify internal_params class attribute."""
        assert "cache_time" in BagCbResolver.internal_params
        assert "read_only" in BagCbResolver.internal_params
        assert "callback" in BagCbResolver.internal_params
        assert "retry_policy" in BagCbResolver.internal_params

    def test_internal_params_not_overridden_by_node(self):
        """Internal params in node.attr don't override resolver settings."""
        call_count = 0

        def counter():
            nonlocal call_count
            call_count += 1
            return call_count

        bag = Bag()
        bag.set_item("test", BagCbResolver(counter, cache_time=-1))

        # First call
        assert bag["test"] == 1

        # Try to set cache_time via node attr (should be ignored)
        bag.set_attr("test", cache_time=0)

        # Should still use cached value (cache_time=-1 from resolver)
        assert bag["test"] == 1
        assert call_count == 1


class TestResolverNestedParams:
    """Tests for nested/complex parameter values."""

    def test_nested_dict_params(self):
        """Nested dict parameters work correctly."""

        def process(config):
            return f"host={config['host']},port={config['port']}"

        bag = Bag()
        bag.set_item("srv", BagCbResolver(process, config={"host": "localhost", "port": 8080}))

        assert bag["srv"] == "host=localhost,port=8080"

        # Override with new dict via node attr
        bag.set_attr("srv", config={"host": "remote", "port": 9090})
        assert bag["srv"] == "host=remote,port=9090"

    def test_nested_list_params(self):
        """List parameters work correctly."""

        def join_items(items, sep):
            return sep.join(items)

        bag = Bag()
        bag.set_item("join", BagCbResolver(join_items, items=["a", "b", "c"], sep="-"))

        assert bag["join"] == "a-b-c"

        bag.set_attr("join", items=["x", "y"])
        assert bag["join"] == "x-y"

    def test_nested_params_fingerprint_change(self):
        """Changing nested param content invalidates cache."""
        call_count = 0

        def process(data):
            nonlocal call_count
            call_count += 1
            return sum(data.values())

        bag = Bag()
        bag.set_item("sum", BagCbResolver(process, data={"a": 1, "b": 2}, cache_time=-1))

        assert bag["sum"] == 3
        assert call_count == 1

        # Same structure, different values
        bag.set_attr("sum", data={"a": 10, "b": 20})
        assert bag["sum"] == 30
        assert call_count == 2


class TestResolverReset:
    """Tests for explicit cache reset."""

    def test_reset_forces_reload(self):
        """reset() forces reload even with same params."""
        call_count = 0

        def counter(x):
            nonlocal call_count
            call_count += 1
            return x

        bag = Bag()
        bag.set_item("data", BagCbResolver(counter, x=5, cache_time=-1))

        assert bag["data"] == 5
        assert call_count == 1

        # Cached
        assert bag["data"] == 5
        assert call_count == 1

        # Reset forces reload
        bag.get_node("data").resolver.reset()
        assert bag["data"] == 5
        assert call_count == 2

    def test_reset_clears_fingerprint(self):
        """reset() clears the fingerprint so next call recomputes."""
        resolver = BagCbResolver(lambda x: x, x=1, cache_time=-1)

        resolver()
        assert resolver._last_effective_fingerprint is not None

        resolver.reset()
        assert resolver._last_effective_fingerprint is None


class TestResolverStandaloneVsAttached:
    """Tests for resolver behavior standalone vs attached to node."""

    def test_standalone_uses_only_defaults_and_call_kwargs(self):
        """Standalone resolver uses _kw and call_kwargs only."""

        def show(a, b):
            return f"a={a},b={b}"

        resolver = BagCbResolver(show, a=1, b=2)

        assert resolver() == "a=1,b=2"
        assert resolver(a=10) == "a=10,b=2"
        assert resolver(b=20) == "a=1,b=20"

    def test_attached_uses_node_attrs(self):
        """Attached resolver reads from node attrs."""

        def show(a, b):
            return f"a={a},b={b}"

        resolver = BagCbResolver(show, a=1, b=2)

        # Standalone
        assert resolver() == "a=1,b=2"

        # Attach to node
        bag = Bag()
        bag.set_item("test", resolver)

        # Still uses defaults (no attrs set)
        assert bag["test"] == "a=1,b=2"

        # Now set node attr
        bag.set_attr("test", a=100)
        assert bag["test"] == "a=100,b=2"

    def test_same_resolver_different_nodes(self):
        """Same resolver instance attached to different nodes."""

        def show(x):
            return f"x={x}"

        # Note: this creates two separate resolvers
        bag = Bag()
        bag.set_item("node1", BagCbResolver(show, x=1))
        bag.set_item("node2", BagCbResolver(show, x=2))

        assert bag["node1"] == "x=1"
        assert bag["node2"] == "x=2"

        # Modify only node1
        bag.set_attr("node1", x=100)
        assert bag["node1"] == "x=100"
        assert bag["node2"] == "x=2"  # unchanged


class TestResolverNoneValues:
    """Tests for None parameter values."""

    def test_none_as_default_value(self):
        """None can be a default parameter value."""

        def with_optional(required, optional=None):
            if optional is None:
                return f"required={required}"
            return f"required={required},optional={optional}"

        resolver = BagCbResolver(with_optional, required="a", optional=None)
        assert resolver() == "required=a"

        assert resolver(optional="b") == "required=a,optional=b"

    def test_none_in_node_attr_removed_by_default(self):
        """None in node.attr is removed by default (_remove_null_attributes=True)."""

        def show(x):
            return f"x={x}"

        bag = Bag()
        bag.set_item("test", BagCbResolver(show, x="default"))

        assert bag["test"] == "x=default"

        # Set to None - gets removed from attrs, falls back to resolver default
        bag.set_attr("test", x=None)
        node = bag.get_node("test")
        assert "x" not in node.attr  # None attrs are removed
        assert bag["test"] == "x=default"  # falls back to resolver default

    def test_none_in_node_attr_kept_when_requested(self):
        """None in node.attr kept if _remove_null_attributes=False."""

        def show(x):
            return f"x={x}"

        bag = Bag()
        bag.set_item("test", BagCbResolver(show, x="default"))

        assert bag["test"] == "x=default"

        # Set to None with _remove_null_attributes=False
        bag.set_attr("test", x=None, _remove_null_attributes=False)
        node = bag.get_node("test")
        assert "x" in node.attr
        assert node.attr["x"] is None
        assert bag["test"] == "x=None"  # uses None from node attr


class TestResolverEdgeCases:
    """Edge cases and boundary conditions."""

    def test_no_user_params(self):
        """Resolver with no user params (only internal)."""
        call_count = 0

        def counter():
            nonlocal call_count
            call_count += 1
            return call_count

        bag = Bag()
        bag.set_item("count", BagCbResolver(counter, cache_time=-1))

        assert bag["count"] == 1
        assert bag["count"] == 1  # cached
        assert call_count == 1

    def test_many_params(self):
        """Resolver with many parameters."""

        def many(a, b, c, d, e, f):
            return a + b + c + d + e + f

        bag = Bag()
        bag.set_item("sum", BagCbResolver(many, a=1, b=2, c=3, d=4, e=5, f=6))

        assert bag["sum"] == 21

        bag.set_attr("sum", a=10, c=30, e=50)
        assert bag["sum"] == 10 + 2 + 30 + 4 + 50 + 6  # 102

    def test_static_bypasses_all(self):
        """static=True bypasses parameter resolution entirely."""
        call_count = 0

        def counter(x):
            nonlocal call_count
            call_count += 1
            return x

        bag = Bag()
        bag.set_item("data", BagCbResolver(counter, x=5, cache_time=-1))

        # First call loads
        assert bag["data"] == 5
        assert call_count == 1

        # static returns cached value without checking params
        node = bag.get_node("data")
        assert node.resolver(static=True) == 5
        assert call_count == 1

        # Even with different call_kwargs, static returns cached
        assert node.resolver(static=True, x=999) == 5
        assert call_count == 1


class TestGetItemWithKwargs:
    """Tests for get_item passing kwargs to resolver."""

    def test_get_item_passes_kwargs_to_resolver(self):
        """get_item passes kwargs to resolver, overriding defaults."""

        def somma(a, b):
            return a + b

        bag = Bag()
        bag.set_item("calc", BagCbResolver(somma, a=3, b=5))

        # Default values
        assert bag.get_item("calc") == 8

        # Override with get_item kwargs
        assert bag.get_item("calc", a=10) == 15
        assert bag.get_item("calc", b=20) == 23
        assert bag.get_item("calc", a=100, b=200) == 300

    def test_get_item_kwargs_override_node_attrs(self):
        """get_item kwargs have priority over node attributes."""

        def somma(a, b):
            return a + b

        bag = Bag()
        bag.set_item("calc", BagCbResolver(somma, a=3, b=5))

        # Set node attrs
        bag.set_attr("calc", a=10, b=20)
        assert bag.get_item("calc") == 30

        # get_item kwargs override node attrs
        assert bag.get_item("calc", a=100) == 120  # 100 + 20
        assert bag.get_item("calc", b=200) == 210  # 10 + 200
        assert bag.get_item("calc", a=100, b=200) == 300

    def test_get_item_kwargs_are_temporary(self):
        """get_item kwargs don't persist."""

        def somma(a, b):
            return a + b

        bag = Bag()
        bag.set_item("calc", BagCbResolver(somma, a=3, b=5))

        assert bag.get_item("calc") == 8
        assert bag.get_item("calc", a=100) == 105
        assert bag.get_item("calc") == 8  # back to default

    def test_get_item_with_nested_path_and_kwargs(self):
        """get_item works with nested paths and kwargs."""

        def multiply(x, y):
            return x * y

        bag = Bag()
        inner = Bag()
        inner.set_item("mult", BagCbResolver(multiply, x=2, y=3))
        bag["nested"] = inner

        # Access through nested path
        assert bag.get_item("nested.mult") == 6
        assert bag.get_item("nested.mult", x=10) == 30
        assert bag.get_item("nested.mult", y=10) == 20
        assert bag.get_item("nested.mult", x=10, y=10) == 100

    def test_bag_get_with_kwargs(self):
        """Bag.get (single level) also supports kwargs."""

        def somma(a, b):
            return a + b

        bag = Bag()
        bag.set_item("calc", BagCbResolver(somma, a=3, b=5))

        # Bag.get with static=False triggers resolver
        assert bag.get("calc", static=False) == 8
        assert bag.get("calc", static=False, a=10) == 15
        assert bag.get("calc", static=False, a=10, b=20) == 30

    def test_node_get_value_with_kwargs(self):
        """BagNode.get_value supports kwargs."""

        def somma(a, b):
            return a + b

        bag = Bag()
        bag.set_item("calc", BagCbResolver(somma, a=3, b=5))

        node = bag.get_node("calc")
        assert node.get_value() == 8
        assert node.get_value(a=10) == 15
        assert node.get_value(a=10, b=20) == 30

    def test_get_item_kwargs_with_cache(self):
        """get_item kwargs properly invalidate cache."""
        call_count = 0

        def counter(x):
            nonlocal call_count
            call_count += 1
            return x

        bag = Bag()
        bag.set_item("data", BagCbResolver(counter, x=5, cache_time=-1))

        assert bag.get_item("data") == 5
        assert call_count == 1

        # Same params - cached
        assert bag.get_item("data") == 5
        assert call_count == 1

        # Different params via get_item - reload
        assert bag.get_item("data", x=10) == 10
        assert call_count == 2

        # Back to original - reload (different from last)
        assert bag.get_item("data") == 5
        assert call_count == 3
