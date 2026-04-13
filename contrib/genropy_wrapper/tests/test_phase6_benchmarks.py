"""Phase 6c: Performance benchmarks across all 3 implementations.

Measures elapsed time for common Bag operations using timeit.
Results are collected in a global dict and printed as a formatted table
by the final test (test_print_benchmarks), run with ``pytest -s``.

Categories benchmarked:
    1. Creation   — empty Bag, 100-item Bag, 1000-item Bag
    2. Access     — scalar key, nested path, positional index
    3. Mutation   — set, pop, set_attr
    4. Iteration  — keys(), values(), items(), len(), for-loop
    5. Serialization — to_xml/from_xml, to_json/from_json, pickle
    6. Lookup scaling — key access on bags of size 10, 100, 1000

Each benchmark runs N repetitions via timeit and records the total
elapsed time in milliseconds. No assertions on timing — this is
purely informational.

Usage::

    pytest tests/test_phase6_benchmarks.py -s -k test_print_benchmarks
    pytest tests/test_phase6_benchmarks.py -s   # run all + print table
"""

import json
import pickle
import timeit

import pytest


# ---------------------------------------------------------------------------
# Result collection
# ---------------------------------------------------------------------------

# _benchmarks[category][operation][impl_name] = elapsed_ms
_benchmarks: dict[str, dict[str, dict[str, float]]] = {}

# Number of repetitions per benchmark
_N_FAST = 2000    # fast operations (access, mutation)
_N_MEDIUM = 500   # medium operations (creation, iteration)
_N_SLOW = 100     # slow operations (serialization)


def _impl_name(bag_class) -> str:
    """Return 'original', 'new', 'wrapper', or 'new_wrapper' for a Bag class."""
    mod = bag_class.__module__
    if mod.startswith("gnr."):
        return "original"
    elif mod.startswith("genro_bag"):
        return "new"
    elif "gnrbag_wrapper" in mod:
        return "new_wrapper"
    else:
        return "wrapper"


def _bench(category: str, op_name: str, bag_class, fn, n: int = _N_FAST):
    """Run fn() n times, record elapsed ms in _benchmarks."""
    impl = _impl_name(bag_class)
    elapsed = timeit.timeit(fn, number=n)
    ms = elapsed * 1000
    _benchmarks.setdefault(category, {}).setdefault(op_name, {})[impl] = ms


# ---------------------------------------------------------------------------
# Helpers: build bags of various sizes
# ---------------------------------------------------------------------------

def _make_bag(bag_class, size: int):
    """Create a Bag with `size` items: key_0=0, key_1=1, ..."""
    b = bag_class()
    for i in range(size):
        b[f"key_{i}"] = i
    return b


def _make_nested_bag(bag_class, depth: int = 3):
    """Create a nested Bag: a.b.c = 42 (depth levels)."""
    b = bag_class()
    path = ".".join(chr(ord("a") + i) for i in range(depth))
    b[path] = 42
    return b


# ---------------------------------------------------------------------------
# 1. Creation benchmarks
# ---------------------------------------------------------------------------

class TestCreation:
    """Benchmark Bag creation operations."""

    def test_create_empty(self, bag_class):
        """Create an empty Bag."""
        _bench("1_creation", "empty", bag_class, lambda: bag_class(), n=_N_MEDIUM)

    def test_create_100(self, bag_class):
        """Create a Bag with 100 items."""
        _bench("1_creation", "100_items", bag_class,
               lambda: _make_bag(bag_class, 100), n=_N_MEDIUM)

    def test_create_1000(self, bag_class):
        """Create a Bag with 1000 items."""
        _bench("1_creation", "1000_items", bag_class,
               lambda: _make_bag(bag_class, 1000), n=_N_SLOW)


# ---------------------------------------------------------------------------
# 2. Access benchmarks
# ---------------------------------------------------------------------------

class TestAccess:
    """Benchmark Bag read access operations."""

    def test_scalar_key(self, bag_class):
        """Access a scalar value by key."""
        b = _make_bag(bag_class, 100)

        _bench("2_access", "scalar_key", bag_class,
               lambda: b["key_50"], n=_N_FAST)

    def test_nested_path(self, bag_class):
        """Access a value via dotted path (a.b.c)."""
        b = _make_nested_bag(bag_class, depth=3)

        _bench("2_access", "nested_path", bag_class,
               lambda: b["a.b.c"], n=_N_FAST)

    def test_positional_index(self, bag_class):
        """Access a value by positional index (#N)."""
        b = _make_bag(bag_class, 100)

        _bench("2_access", "positional_#50", bag_class,
               lambda: b["#50"], n=_N_FAST)


# ---------------------------------------------------------------------------
# 3. Mutation benchmarks
# ---------------------------------------------------------------------------

class TestMutation:
    """Benchmark Bag write operations."""

    def test_set_existing(self, bag_class):
        """Overwrite an existing key."""
        b = _make_bag(bag_class, 100)

        _bench("3_mutation", "set_existing", bag_class,
               lambda: b.__setitem__("key_50", 999), n=_N_FAST)

    def test_pop(self, bag_class):
        """Pop and re-insert a key (to keep bag consistent across runs)."""
        b = _make_bag(bag_class, 100)

        def fn():
            b["_bench_tmp"] = "x"
            b.pop("_bench_tmp")

        _bench("3_mutation", "set_and_pop", bag_class, fn, n=_N_FAST)

    def test_set_attr(self, bag_class):
        """Set an attribute on an existing node."""
        b = _make_bag(bag_class, 100)
        # Use snake_case for new, camelCase for original/wrapper
        if hasattr(b, "setAttr"):
            fn = lambda: b.setAttr("key_50", color="red")
        else:
            fn = lambda: b.set_attr("key_50", color="red")

        _bench("3_mutation", "set_attr", bag_class, fn, n=_N_FAST)


# ---------------------------------------------------------------------------
# 4. Iteration benchmarks
# ---------------------------------------------------------------------------

class TestIteration:
    """Benchmark Bag iteration operations."""

    def test_keys(self, bag_class):
        """Iterate over keys()."""
        b = _make_bag(bag_class, 100)

        _bench("4_iteration", "keys", bag_class,
               lambda: list(b.keys()), n=_N_MEDIUM)

    def test_values(self, bag_class):
        """Iterate over values()."""
        b = _make_bag(bag_class, 100)

        _bench("4_iteration", "values", bag_class,
               lambda: list(b.values()), n=_N_MEDIUM)

    def test_items(self, bag_class):
        """Iterate over items()."""
        b = _make_bag(bag_class, 100)

        _bench("4_iteration", "items", bag_class,
               lambda: list(b.items()), n=_N_MEDIUM)

    def test_len(self, bag_class):
        """Call len() on a Bag."""
        b = _make_bag(bag_class, 100)

        _bench("4_iteration", "len", bag_class,
               lambda: len(b), n=_N_FAST)

    def test_for_loop(self, bag_class):
        """Iterate with for-loop (yields BagNode)."""
        b = _make_bag(bag_class, 100)

        def fn():
            for node in b:
                pass

        _bench("4_iteration", "for_loop", bag_class, fn, n=_N_MEDIUM)


# ---------------------------------------------------------------------------
# 5. Serialization benchmarks
# ---------------------------------------------------------------------------

class TestSerialization:
    """Benchmark serialization round-trips."""

    def test_to_xml(self, bag_class):
        """Serialize a 50-item Bag to XML."""
        b = _make_bag(bag_class, 50)
        impl = _impl_name(bag_class)

        if impl == "new":
            fn = lambda: b.to_xml()
        else:
            fn = lambda: b.toXml()

        _bench("5_serialization", "to_xml", bag_class, fn, n=_N_SLOW)

    def test_from_xml(self, bag_class):
        """Deserialize a 50-item Bag from XML."""
        b = _make_bag(bag_class, 50)
        impl = _impl_name(bag_class)

        if impl == "new":
            xml_data = f"<root>{b.to_xml()}</root>"
            fn = lambda: bag_class.from_xml(xml_data)
        else:
            xml_data = b.toXml()
            fn = lambda: bag_class(xml_data)

        _bench("5_serialization", "from_xml", bag_class, fn, n=_N_SLOW)

    def test_to_json(self, bag_class):
        """Serialize a 50-item Bag to JSON."""
        b = _make_bag(bag_class, 50)
        impl = _impl_name(bag_class)

        if impl == "new":
            fn = lambda: b.to_json()
        else:
            fn = lambda: b.toJson()

        _bench("5_serialization", "to_json", bag_class, fn, n=_N_SLOW)

    def test_from_json(self, bag_class):
        """Deserialize a 50-item Bag from JSON."""
        b = _make_bag(bag_class, 50)
        impl = _impl_name(bag_class)

        if impl == "new":
            json_data = b.to_json()
            fn = lambda: bag_class.from_json(json_data)
        else:
            json_data = b.toJson()
            fn = lambda: bag_class().fromJson(json.loads(json_data))

        _bench("5_serialization", "from_json", bag_class, fn, n=_N_SLOW)

    def test_pickle_dumps(self, bag_class):
        """Pickle-serialize a 50-item Bag."""
        b = _make_bag(bag_class, 50)

        _bench("5_serialization", "pickle_dumps", bag_class,
               lambda: pickle.dumps(b), n=_N_SLOW)

    def test_pickle_loads(self, bag_class):
        """Pickle-deserialize a 50-item Bag."""
        b = _make_bag(bag_class, 50)
        data = pickle.dumps(b)

        _bench("5_serialization", "pickle_loads", bag_class,
               lambda: pickle.loads(data), n=_N_SLOW)


# ---------------------------------------------------------------------------
# 6. Lookup scaling benchmarks
# ---------------------------------------------------------------------------

class TestLookupScaling:
    """Benchmark key lookup on bags of increasing size.

    Demonstrates O(1) dict lookup (new/wrapper) vs O(n) list scan (original).
    """

    @pytest.mark.parametrize("size", [10, 100, 1000], ids=["n10", "n100", "n1000"])
    def test_lookup_by_key(self, bag_class, size):
        """Lookup the last key in a bag of given size."""
        b = _make_bag(bag_class, size)
        last_key = f"key_{size - 1}"

        _bench("6_scaling", f"lookup_n{size}", bag_class,
               lambda: b[last_key], n=_N_FAST)

    @pytest.mark.parametrize("size", [10, 100, 1000], ids=["n10", "n100", "n1000"])
    def test_contains(self, bag_class, size):
        """Check 'in' operator on a bag of given size."""
        b = _make_bag(bag_class, size)
        last_key = f"key_{size - 1}"

        _bench("6_scaling", f"contains_n{size}", bag_class,
               lambda: last_key in b, n=_N_FAST)


# ---------------------------------------------------------------------------
# Results printer (run with -s)
# ---------------------------------------------------------------------------

class TestBenchmarkResults:
    """Print the collected benchmark results as a formatted table."""

    def test_print_benchmarks(self):
        """Print benchmark results table to stdout.

        Run with: pytest tests/test_phase6_benchmarks.py -s -k test_print_benchmarks
        """
        if not _benchmarks:
            pytest.skip("No benchmark results collected")

        impls = ["original", "new", "wrapper", "new_wrapper"]

        header = (
            f"{'Category':<18} {'Operation':<22}"
            f" {'Original':>10} {'New':>10} {'Wrapper':>10} {'NewWrap':>10}"
            f" {'New/Orig':>10} {'Wrap/Orig':>10} {'NWrap/Orig':>10}"
        )
        separator = "-" * len(header)

        print("\n")
        print("=" * len(header))
        print("  PERFORMANCE BENCHMARKS (ms)")
        print("=" * len(header))
        print(header)
        print(separator)

        for category in sorted(_benchmarks.keys()):
            ops = _benchmarks[category]
            cat_label = category.split("_", 1)[1] if "_" in category else category

            for op_name in sorted(ops.keys()):
                results = ops[op_name]
                orig_ms = results.get("original")
                new_ms = results.get("new")
                wrap_ms = results.get("wrapper")
                nwrap_ms = results.get("new_wrapper")

                def fmt(v):
                    return f"{v:.2f}" if v is not None else "N/A"

                def ratio(v, base):
                    return f"{v / base:.2f}x" if v and base else "N/A"

                print(
                    f"{cat_label:<18} {op_name:<22}"
                    f" {fmt(orig_ms):>10} {fmt(new_ms):>10} {fmt(wrap_ms):>10} {fmt(nwrap_ms):>10}"
                    f" {ratio(new_ms, orig_ms):>10} {ratio(wrap_ms, orig_ms):>10} {ratio(nwrap_ms, orig_ms):>10}"
                )
                cat_label = ""

            print(separator)

        print("\nLegend: times in milliseconds (lower is better)")
        print("  Ratios vs Original (< 1.0 = faster)")
        print("=" * len(header))
