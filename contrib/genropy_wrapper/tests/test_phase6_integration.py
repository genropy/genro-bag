"""Phase 6: Integration test — compatibility matrix and readiness score.

Runs representative tests on all 3 implementations (original, new, wrapper)
across the 9 API areas (A through I from the API comparison), produces a
compatibility matrix, and calculates an overall replacement readiness
percentage: (wrapper_passing / original_passing) * 100.

The matrix is printed to stdout with -s flag, e.g.:
    pytest tests/test_phase6_integration.py -s -k "test_print_matrix"

Areas tested:
    A: Access & Mutation
    B: Iteration
    C: Query & Traversal
    D: Serialization
    E: Events
    F: Hierarchy
    G: Resolvers
    H: BagNode API
    I: Utilities
"""

import copy as copy_module
import datetime
import json
import os
import pickle
import socket

import pytest

import genro_bag
from genro_bag.resolver import BagCbResolver as NewBagCbResolver
from gnr.core.gnrbag import Bag as OriginalBag
from gnr.core.gnrbag import BagCbResolver as OriginalBagCbResolver
from gnr.core.gnrbag import BagNode as OriginalBagNode
from gnr.core.gnrbag import BagResolver as OriginalBagResolver
from replacement.gnrbag import Bag as WrapperBag
from replacement.gnrbag import BagCbResolver as WrapperBagCbResolver
from replacement.gnrbag import BagNode as WrapperBagNode
from replacement.gnrbag import BagResolver as WrapperBagResolver


# ---------------------------------------------------------------------------
# Result collection
# ---------------------------------------------------------------------------

# _results[area][test_name][impl_name] = True/False
_results: dict[str, dict[str, dict[str, bool]]] = {}


def _impl_name(bag_class):
    """Return implementation name for a Bag or BagNode class."""
    mod = bag_class.__module__
    if mod.startswith("gnr."):
        return "original"
    elif mod.startswith("genro_bag"):
        return "new"
    else:
        return "wrapper"


def _record(area, test_name, impl, passed):
    """Record a test result in the global matrix."""
    _results.setdefault(area, {}).setdefault(test_name, {})[impl] = passed


def _run_and_record(area, test_name, bag_class, fn):
    """Run fn(), record result, and assert.

    fn() should raise on failure. We catch AssertionError to record False,
    then re-raise so pytest shows the failure.
    """
    impl = _impl_name(bag_class)
    try:
        fn()
        _record(area, test_name, impl, True)
    except (AssertionError, Exception) as exc:
        _record(area, test_name, impl, False)
        raise


# ---------------------------------------------------------------------------
# Area A: Access & Mutation
# ---------------------------------------------------------------------------

class TestAreaA:
    """Access and mutation operations across all implementations."""

    def test_set_get_scalar(self, bag_class):
        """Set and get a scalar value via __setitem__/__getitem__."""
        def fn():
            b = bag_class()
            b["name"] = "Alice"
            assert b["name"] == "Alice"
        _run_and_record("A", "set_get_scalar", bag_class, fn)

    def test_hierarchical_path(self, bag_class):
        """Set and get nested values via dotted path."""
        def fn():
            b = bag_class()
            b["a.b.c"] = 42
            assert b["a.b.c"] == 42
            assert isinstance(b["a"], bag_class)
        _run_and_record("A", "hierarchical_path", bag_class, fn)

    def test_positional_access(self, bag_class):
        """Access nodes by positional index (#N)."""
        def fn():
            b = bag_class()
            b["x"] = 10
            b["y"] = 20
            b["z"] = 30
            assert b["#0"] == 10
            assert b["#2"] == 30
        _run_and_record("A", "positional_access", bag_class, fn)

    def test_attribute_crud(self, bag_class_camel):
        """Set, get, and delete node attributes."""
        def fn():
            b = bag_class_camel()
            b.setItem("name", "Alice", color="red")
            assert b.getAttr("name", "color") == "red"
            b.setAttr("name", color="blue")
            assert b.getAttr("name", "color") == "blue"
            b.delAttr("name", "color")
            assert b.getAttr("name", "color") is None
        _run_and_record("A", "attribute_crud", bag_class_camel, fn)

    def test_pop_node(self, bag_class):
        """pop() removes a node and returns its value."""
        def fn():
            b = bag_class()
            b["a"] = 1
            b["b"] = 2
            val = b.pop("a")
            assert val == 1
            assert "a" not in b
        _run_and_record("A", "pop_node", bag_class, fn)


# ---------------------------------------------------------------------------
# Area B: Iteration
# ---------------------------------------------------------------------------

class TestAreaB:
    """Iteration and collection operations."""

    def test_keys_values_items(self, bag_class):
        """keys(), values(), items() return correct ordered sequences."""
        def fn():
            b = bag_class()
            b["a"] = 1
            b["b"] = 2
            b["c"] = 3
            assert list(b.keys()) == ["a", "b", "c"]
            assert list(b.values()) == [1, 2, 3]
            assert list(b.items()) == [("a", 1), ("b", 2), ("c", 3)]
        _run_and_record("B", "keys_values_items", bag_class, fn)

    def test_len_contains(self, bag_class):
        """len() and 'in' operator work correctly."""
        def fn():
            b = bag_class()
            b["x"] = 10
            b["y"] = 20
            assert len(b) == 2
            assert "x" in b
            assert "z" not in b
        _run_and_record("B", "len_contains", bag_class, fn)

    def test_iter_protocol(self, bag_class):
        """Bag supports iteration over nodes."""
        def fn():
            b = bag_class()
            b["a"] = 1
            b["b"] = 2
            nodes = list(b)
            assert len(nodes) == 2
        _run_and_record("B", "iter_protocol", bag_class, fn)

    def test_clear(self, bag_class):
        """clear() removes all nodes."""
        def fn():
            b = bag_class()
            b["a"] = 1
            b["b"] = 2
            b.clear()
            assert len(b) == 0
            assert list(b.keys()) == []
        _run_and_record("B", "clear", bag_class, fn)


# ---------------------------------------------------------------------------
# Area C: Query & Traversal
# ---------------------------------------------------------------------------

class TestAreaC:
    """Query, digest, walk, and node lookup."""

    def test_digest_basic(self, bag_class_camel):
        """digest() returns (label, value) tuples for top-level nodes."""
        def fn():
            b = bag_class_camel()
            b.setItem("a", 10)
            b.setItem("b", 20)
            result = b.digest()
            assert result[0][0] == "a"
            assert result[1][1] == 20
        _run_and_record("C", "digest_basic", bag_class_camel, fn)

    def test_digest_with_condition(self, bag_class_camel):
        """digest() with condition filters nodes."""
        def fn():
            b = bag_class_camel()
            b.setItem("a", 10, active=True)
            b.setItem("b", 20, active=False)
            b.setItem("c", 30, active=True)
            result = b.digest(
                "#a.active,#v",
                condition=lambda node: node.getAttr("active") is True,
            )
            assert len(result) == 2
            assert result[0] == (True, 10)
            assert result[1] == (True, 30)
        _run_and_record("C", "digest_with_condition", bag_class_camel, fn)

    def test_walk_callback(self, bag_class):
        """walk() with callback visits all leaf nodes."""
        def fn():
            b = bag_class()
            b["a.x"] = 1
            b["a.y"] = 2
            b["b"] = 3
            visited = []

            def collector(node):
                visited.append(node.label)

            b.walk(collector)
            assert len(visited) >= 3
        _run_and_record("C", "walk_callback", bag_class, fn)

    def test_get_node_by_attr(self, bag_class_camel):
        """Find a node by attribute value."""
        def fn():
            b = bag_class_camel()
            b.setItem("alice", 100, role="admin")
            b.setItem("bob", 200, role="user")
            node = b.getNodeByAttr("role", "admin")
            assert node is not None
            assert node.getValue() == 100
        _run_and_record("C", "get_node_by_attr", bag_class_camel, fn)


# ---------------------------------------------------------------------------
# Area D: Serialization
# ---------------------------------------------------------------------------

class TestAreaD:
    """XML, JSON, and pickle serialization."""

    def test_xml_roundtrip(self, bag_class):
        """to_xml() -> from_xml() produces an equal Bag (typed values)."""
        def fn():
            b = bag_class()
            b["name"] = "Alice"
            b["age"] = 30
            b["birthday"] = datetime.date(1994, 3, 15)

            if hasattr(b, "toXml"):
                xml_str = b.toXml()
                b2 = bag_class(xml_str)
                # toXml preserves types via _T annotations
                assert b2["age"] == 30
                assert b2["birthday"] == datetime.date(1994, 3, 15)
            else:
                # genro_bag.to_xml() omits root element and _T annotations;
                # wrap for from_xml, verify structure (types lost)
                xml_str = b.to_xml()
                xml_str = f"<GenRoBag>{xml_str}</GenRoBag>"
                b2 = bag_class.from_xml(xml_str)

            assert b2["name"] == "Alice"
        _run_and_record("D", "xml_roundtrip", bag_class, fn)

    def test_json_roundtrip(self, bag_class):
        """to_json() -> from_json() preserves structure and values."""
        def fn():
            b = bag_class()
            b["name"] = "Bob"
            b["score"] = 42

            if hasattr(b, "toJson"):
                json_str = b.toJson()
                # Original fromJson has param name shadowing json module;
                # parse manually and pass dict instead
                json_data = json.loads(json_str)
                b2 = bag_class()
                b2.fromJson(json_data)
            else:
                json_str = b.to_json()
                b2 = bag_class.from_json(json_str)

            assert b2["name"] == "Bob"
            assert b2["score"] == 42
        _run_and_record("D", "json_roundtrip", bag_class, fn)

    def test_pickle_roundtrip(self, bag_class):
        """Pickle roundtrip preserves Bag structure and values."""
        def fn():
            b = bag_class()
            b["x"] = 10
            b["nested.y"] = 20
            data = pickle.dumps(b)
            b2 = pickle.loads(data)
            assert b2["x"] == 10
            assert b2["nested.y"] == 20
        _run_and_record("D", "pickle_roundtrip", bag_class, fn)

    def test_xml_typed_attributes(self, bag_class_camel):
        """XML serialization preserves typed attributes (_T annotations)."""
        def fn():
            b = bag_class_camel()
            b.setItem("count", 42)
            b.setItem("active", True)
            b.setItem("ratio", 3.14)
            xml_str = b.toXml()
            # XML must contain _T type annotations for non-string values
            assert "_T=" in xml_str
        _run_and_record("D", "xml_typed_attributes", bag_class_camel, fn)


# ---------------------------------------------------------------------------
# Area E: Events
# ---------------------------------------------------------------------------

class TestAreaE:
    """Event subscription and triggers."""

    def test_subscribe_insert(self, bag_class):
        """Insert event fires when a new node is added."""
        def fn():
            b = bag_class()
            events = []

            def on_insert(**kwargs):
                events.append("insert")

            if hasattr(b, "subscribe") and _impl_name(bag_class) != "new":
                b.subscribe(1, insert=on_insert)
            else:
                b.subscribe(subscriber_id="1", insert=on_insert)

            b["new_key"] = "value"
            assert "insert" in events
        _run_and_record("E", "subscribe_insert", bag_class, fn)

    def test_subscribe_update(self, bag_class):
        """Update event fires when an existing node's value changes."""
        def fn():
            b = bag_class()
            b["existing"] = "old"
            events = []

            def on_update(evt=None, **kwargs):
                if evt == "upd_value":
                    events.append("upd_value")

            if hasattr(b, "subscribe") and _impl_name(bag_class) != "new":
                b.subscribe(1, update=on_update)
            else:
                b.subscribe(subscriber_id="1", update=on_update)

            b["existing"] = "new"
            assert "upd_value" in events
        _run_and_record("E", "subscribe_update", bag_class, fn)

    def test_subscribe_delete(self, bag_class):
        """Delete event fires when a node is removed via pop()."""
        def fn():
            b = bag_class()
            b["to_delete"] = 42
            events = []

            def on_delete(**kwargs):
                events.append("delete")

            if hasattr(b, "subscribe") and _impl_name(bag_class) != "new":
                b.subscribe(1, delete=on_delete)
            else:
                b.subscribe(subscriber_id="1", delete=on_delete)

            b.pop("to_delete")
            assert "delete" in events
        _run_and_record("E", "subscribe_delete", bag_class, fn)


# ---------------------------------------------------------------------------
# Area F: Hierarchy
# ---------------------------------------------------------------------------

class TestAreaF:
    """Copy, backref, and hierarchy operations."""

    def test_deepcopy(self, bag_class):
        """deepcopy creates independent copy with equal values."""
        def fn():
            b = bag_class()
            b["a.b"] = 10
            b["c"] = 20

            if hasattr(b, "deepcopy"):
                b2 = b.deepcopy()
            else:
                b2 = copy_module.deepcopy(b)

            assert b2["a.b"] == 10
            assert b2["c"] == 20
            # Modifying copy doesn't affect original
            b2["a.b"] = 99
            assert b["a.b"] == 10
        _run_and_record("F", "deepcopy", bag_class, fn)

    def test_set_backref_fullpath(self, bag_class):
        """setBackRef enables fullpath tracking on nested Bags."""
        def fn():
            b = bag_class()
            b["a.b.c"] = 42

            if hasattr(b, "setBackRef"):
                b.setBackRef()
            else:
                b.set_backref()

            inner = b["a.b"]
            assert inner.fullpath == "a.b"
        _run_and_record("F", "set_backref_fullpath", bag_class, fn)

    def test_copy_shallow(self, bag_class_camel):
        """copy() returns equal but not identical Bag (wrapper/original only)."""
        def fn():
            b = bag_class_camel()
            b["x"] = 1
            b["y"] = 2
            b2 = b.copy()
            assert b2 == b
            assert b2 is not b
        _run_and_record("F", "copy_shallow", bag_class_camel, fn)

    def test_update(self, bag_class_camel):
        """update() merges another Bag, overwriting existing keys."""
        def fn():
            b1 = bag_class_camel()
            b1.setItem("a", 1)
            b1.setItem("b", 2)
            b2 = bag_class_camel()
            b2.setItem("b", 20)
            b2.setItem("c", 30)
            b1.update(b2)
            assert b1["a"] == 1
            assert b1["b"] == 20
            assert b1["c"] == 30
        _run_and_record("F", "update", bag_class_camel, fn)


# ---------------------------------------------------------------------------
# Area G: Resolvers
# ---------------------------------------------------------------------------

class _OriginalResolver(OriginalBagResolver):
    classKwargs = {"cacheTime": 0, "readOnly": True}
    classArgs = ["hostname"]

    def load(self):
        result = OriginalBag()
        result["hostname"] = socket.gethostname()
        result["pid"] = os.getpid()
        return result


class _WrapperResolver(WrapperBagResolver):
    classKwargs = {"cacheTime": 0, "readOnly": True}
    classArgs = ["hostname"]

    def load(self):
        result = WrapperBag()
        result["hostname"] = socket.gethostname()
        result["pid"] = os.getpid()
        return result


class _NewResolver(genro_bag.BagResolver):
    class_kwargs = {"cache_time": 0, "read_only": True}
    class_args = ["hostname"]

    def load(self):
        result = genro_bag.Bag()
        result["hostname"] = socket.gethostname()
        result["pid"] = os.getpid()
        return result


class TestAreaG:
    """Resolver loading and callback resolvers."""

    def test_custom_resolver(self, bag_class):
        """Custom resolver loads data on access."""
        def fn():
            impl = _impl_name(bag_class)
            b = bag_class()
            if impl == "original":
                b["info"] = _OriginalResolver()
            elif impl == "wrapper":
                b["info"] = _WrapperResolver()
            else:
                b["info"] = _NewResolver()

            assert b["info.hostname"] == socket.gethostname()
            assert b["info.pid"] == os.getpid()
        _run_and_record("G", "custom_resolver", bag_class, fn)

    def test_cb_resolver(self, bag_class):
        """Callback resolver calls a function on access."""
        def fn():
            impl = _impl_name(bag_class)
            b = bag_class()
            counter = {"calls": 0}

            def my_callback(**kwargs):
                counter["calls"] += 1
                result = bag_class()
                result["data"] = "loaded"
                return result

            if impl == "original":
                b["lazy"] = OriginalBagCbResolver(my_callback, cacheTime=0)
            elif impl == "wrapper":
                b["lazy"] = WrapperBagCbResolver(my_callback, cacheTime=0)
            else:
                b["lazy"] = NewBagCbResolver(callback=my_callback, cache_time=0)

            assert b["lazy.data"] == "loaded"
            assert counter["calls"] >= 1
        _run_and_record("G", "cb_resolver", bag_class, fn)


# ---------------------------------------------------------------------------
# Area H: BagNode API
# ---------------------------------------------------------------------------

class TestAreaH:
    """BagNode creation, attribute access, label/tag."""

    def test_node_creation_with_attrs(self, bag_class_camel):
        """Create BagNode with attributes, verify attr dict."""
        def fn():
            b = bag_class_camel()
            b.setItem("item", 42, color="red", size=10)
            node = b.getNode("item")
            assert node.attr.get("color") == "red"
            assert node.attr.get("size") == 10
        _run_and_record("H", "node_creation_with_attrs", bag_class_camel, fn)

    def test_node_label_tag(self, bag_class):
        """BagNode has label and tag properties."""
        def fn():
            b = bag_class()
            b["mykey"] = "val"

            if hasattr(b, "getNode"):
                node = b.getNode("mykey")
            else:
                node = b.get_node("mykey")

            assert node.label == "mykey"
            if hasattr(node, "tag"):
                assert node.tag == "mykey"
        _run_and_record("H", "node_label_tag", bag_class, fn)

    def test_node_value_access(self, bag_class):
        """BagNode.value and getValue() return the stored value."""
        def fn():
            b = bag_class()
            b["item"] = "hello"

            if hasattr(b, "getNode"):
                node = b.getNode("item")
            else:
                node = b.get_node("item")

            assert node.value == "hello"
            if hasattr(node, "getValue"):
                assert node.getValue() == "hello"
        _run_and_record("H", "node_value_access", bag_class, fn)

    def test_node_get_formatted_value(self, bag_class_camel):
        """getFormattedValue returns 'Label: value' string (wrapper/original)."""
        def fn():
            b = bag_class_camel()
            b.setItem("name", "Alice")
            node = b.getNode("name")
            result = node.getFormattedValue()
            assert "Name" in result
            assert "Alice" in result
        _run_and_record("H", "node_get_formatted_value", bag_class_camel, fn)


# ---------------------------------------------------------------------------
# Area I: Utilities
# ---------------------------------------------------------------------------

class TestAreaI:
    """Sort, sum, asDict, normalizeItemPath, toTree."""

    def test_sort_by_key(self, bag_class):
        """sort() orders nodes alphabetically by key."""
        def fn():
            b = bag_class()
            b["c"] = 3
            b["a"] = 1
            b["b"] = 2
            b.sort()
            assert list(b.keys()) == ["a", "b", "c"]
        _run_and_record("I", "sort_by_key", bag_class, fn)

    def test_sort_by_value(self, bag_class):
        """sort('#v:a') orders nodes by value ascending."""
        def fn():
            b = bag_class()
            b["x"] = 30
            b["y"] = 10
            b["z"] = 20
            b.sort("#v:a")
            assert list(b.values()) == [10, 20, 30]
        _run_and_record("I", "sort_by_value", bag_class, fn)

    def test_sum_values(self, bag_class_camel):
        """sum() aggregates node values."""
        def fn():
            b = bag_class_camel()
            b.setItem("a", 10)
            b.setItem("b", 20)
            b.setItem("c", 30)
            assert b.sum() == 60
        _run_and_record("I", "sum_values", bag_class_camel, fn)

    def test_as_dict(self, bag_class):
        """as_dict/asDict converts Bag to flat dict."""
        def fn():
            b = bag_class()
            b["a"] = 1
            b["b"] = 2
            if hasattr(b, "asDict"):
                d = b.asDict()
            elif hasattr(b, "as_dict"):
                d = b.as_dict()
            else:
                pytest.skip(f"{_impl_name(bag_class)} lacks as_dict/asDict")
            assert d == {"a": 1, "b": 2}
        _run_and_record("I", "as_dict", bag_class, fn)

    def test_to_tree(self, bag_class_camel):
        """toTree groups flat Bag into nested hierarchy (wrapper/original)."""
        def fn():
            b = bag_class_camel()
            b["alfa"] = bag_class_camel(dict(number=1, text="g1", title="alfa"))
            b["beta"] = bag_class_camel(dict(number=2, text="g1", title="beta"))
            tree = b.toTree(group_by=("number", "text"), caption="title")
            # Tree should have top-level groups by number
            assert len(tree) == 2
        _run_and_record("I", "to_tree", bag_class_camel, fn)


# ---------------------------------------------------------------------------
# Compatibility Matrix (runs last — Z prefix ensures alphabetical order)
# ---------------------------------------------------------------------------

_AREA_NAMES = {
    "A": "Access & Mutation",
    "B": "Iteration",
    "C": "Query & Traversal",
    "D": "Serialization",
    "E": "Events",
    "F": "Hierarchy",
    "G": "Resolvers",
    "H": "BagNode API",
    "I": "Utilities",
}


class TestZCompatibilityMatrix:
    """Aggregate results from all area tests and print compatibility matrix."""

    def test_print_matrix(self):
        """Print the compatibility matrix to stdout.

        Run with: pytest tests/test_phase6_integration.py -s -k "test_print_matrix"
        """
        if not _results:
            pytest.skip("No results collected (run all area tests first)")

        impls = ["original", "new", "wrapper"]
        header = f"{'Area':<25} {'Original':>10} {'New':>10} {'Wrapper':>10}"
        separator = "-" * len(header)

        print("\n")
        print("=" * len(header))
        print("  COMPATIBILITY MATRIX")
        print("=" * len(header))
        print(header)
        print(separator)

        totals = {impl: {"passed": 0, "total": 0} for impl in impls}

        for area_code in sorted(_AREA_NAMES.keys()):
            area_name = _AREA_NAMES[area_code]
            tests = _results.get(area_code, {})
            counts = {}
            for impl in impls:
                passed = sum(
                    1 for t in tests.values() if t.get(impl, False)
                )
                total = sum(
                    1 for t in tests.values() if impl in t
                )
                counts[impl] = (passed, total)
                totals[impl]["passed"] += passed
                totals[impl]["total"] += total

            cells = []
            for impl in impls:
                p, t = counts[impl]
                cells.append(f"{p}/{t}")

            print(
                f"{area_code}: {area_name:<22} {cells[0]:>10} {cells[1]:>10} {cells[2]:>10}"
            )

        print(separator)
        total_cells = []
        for impl in impls:
            p = totals[impl]["passed"]
            t = totals[impl]["total"]
            total_cells.append(f"{p}/{t}")
        print(
            f"{'TOTAL':<25} {total_cells[0]:>10} {total_cells[1]:>10} {total_cells[2]:>10}"
        )
        print(separator)

        # Readiness score
        orig_passed = totals["original"]["passed"]
        wrap_passed = totals["wrapper"]["passed"]
        if orig_passed > 0:
            readiness = (wrap_passed / orig_passed) * 100
        else:
            readiness = 0.0

        print(f"\nReplacement readiness: {readiness:.1f}%")
        print(f"  (wrapper passing: {wrap_passed}, original passing: {orig_passed})")

        # Behavioral differences summary
        differences = []
        for area_code in sorted(_results.keys()):
            for test_name, impl_results in _results[area_code].items():
                orig = impl_results.get("original")
                wrap = impl_results.get("wrapper")
                if orig is not None and wrap is not None and orig != wrap:
                    differences.append(
                        f"  {area_code}.{test_name}: original={'PASS' if orig else 'FAIL'}, "
                        f"wrapper={'PASS' if wrap else 'FAIL'}"
                    )

        if differences:
            print(f"\nBehavioral differences ({len(differences)}):")
            for d in differences:
                print(d)
        else:
            print("\nNo behavioral differences between original and wrapper.")

        print("=" * len(header))

    def test_readiness_score(self):
        """Assert that replacement readiness meets the minimum threshold.

        The wrapper should pass at least 90% of what the original passes.
        """
        if not _results:
            pytest.skip("No results collected (run all area tests first)")

        orig_passed = 0
        wrap_passed = 0

        for area_tests in _results.values():
            for impl_results in area_tests.values():
                if impl_results.get("original", False):
                    orig_passed += 1
                if impl_results.get("wrapper", False):
                    wrap_passed += 1

        if orig_passed == 0:
            pytest.skip("No original tests passed — cannot compute readiness")

        readiness = (wrap_passed / orig_passed) * 100
        assert readiness >= 90, (
            f"Replacement readiness {readiness:.1f}% is below 90% threshold "
            f"(wrapper: {wrap_passed}, original: {orig_passed})"
        )
