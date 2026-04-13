#!/usr/bin/env python3
# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Comparative benchmarks: legacy vs core vs old wrapper vs new wrapper.

Run with:
    PYTHONPATH=contrib/genropy_wrapper python contrib/genropy_wrapper/benchmarks/benchmark_wrapper_comparison.py
"""

import time

from gnr.core.gnrbag import Bag as LegacyBag
from genro_bag import Bag as CoreBag
from replacement.gnrbag import Bag as OldWrapperBag
from replacement.gnrbag_wrapper import Bag as NewWrapperBag


N_OPS = 10000
N_REPS = 3

IMPLEMENTATIONS = [
    ("legacy", LegacyBag),
    ("core", CoreBag),
    ("old_wrapper", OldWrapperBag),
    ("new_wrapper", NewWrapperBag),
]


def bench(fn, n=N_OPS):
    """Run fn() n times, return best of N_REPS in microseconds per op."""
    best = float("inf")
    for _ in range(N_REPS):
        start = time.perf_counter()
        for _ in range(n):
            fn()
        elapsed = time.perf_counter() - start
        us_per_op = elapsed / n * 1e6
        if us_per_op < best:
            best = us_per_op
    return best


def print_row(label, results):
    """Print a row of results."""
    parts = [f"{label:40s}"]
    for name, us in results:
        parts.append(f"{name}: {us:7.2f} us")
    print("  ".join(parts))


def print_header():
    parts = [f"{'Operation':40s}"]
    for name, _ in IMPLEMENTATIONS:
        parts.append(f"{name:>16s}")
    print("  ".join(parts))
    print("-" * (40 + 18 * len(IMPLEMENTATIONS)))


def run_benchmark(label, fn_factory, n=N_OPS):
    """Run a benchmark across all implementations."""
    results = []
    for name, cls in IMPLEMENTATIONS:
        fn = fn_factory(cls)
        if fn is None:
            results.append((name, float("nan")))
        else:
            us = bench(fn, n)
            results.append((name, us))
    print_row(label, results)


def main():
    print("=" * 80)
    print("Wrapper Comparison Benchmarks")
    print(f"  {N_OPS} ops/measurement, best of {N_REPS} reps")
    print("=" * 80)

    # ------------------------------------------------------------------
    print("\n=== Creation ===")
    # ------------------------------------------------------------------

    run_benchmark(
        "Empty Bag()",
        lambda cls: lambda: cls(),
    )

    run_benchmark(
        "Bag from dict (10 keys)",
        lambda cls: lambda: cls({"k0": 0, "k1": 1, "k2": 2, "k3": 3, "k4": 4,
                                  "k5": 5, "k6": 6, "k7": 7, "k8": 8, "k9": 9}),
        n=5000,
    )

    # ------------------------------------------------------------------
    print("\n=== snake_case Access (set_item / get_item / [] ) ===")
    # ------------------------------------------------------------------

    def make_set_item_bench(cls):
        if not hasattr(cls, "set_item"):
            return None
        b = cls()
        return lambda: b.set_item("key", 42)

    run_benchmark("set_item('key', 42)", make_set_item_bench)

    def make_get_item_bench(cls):
        if not hasattr(cls, "get_item"):
            return None
        b = cls()
        b["key"] = 42
        return lambda: b.get_item("key")

    run_benchmark("get_item('key')", make_get_item_bench)

    def make_bracket_bench(cls):
        b = cls()
        b["key"] = 42
        return lambda: b["key"]

    run_benchmark("bag['key']", make_bracket_bench)

    def make_nested_bench(cls):
        b = cls()
        b["a.b.c"] = 99
        return lambda: b["a.b.c"]

    run_benchmark("bag['a.b.c'] (nested)", make_nested_bench)

    # ------------------------------------------------------------------
    print("\n=== camelCase Access (setItem / getItem) ===")
    # ------------------------------------------------------------------

    def make_setItem_bench(cls):
        b = cls()
        if hasattr(b, "setItem"):
            return lambda: b.setItem("key", 42)
        return None

    run_benchmark("setItem('key', 42)", make_setItem_bench)

    def make_getItem_bench(cls):
        b = cls()
        b["key"] = 42
        if hasattr(b, "getItem"):
            return lambda: b.getItem("key")
        return None

    run_benchmark("getItem('key')", make_getItem_bench)

    # ------------------------------------------------------------------
    print("\n=== Node Operations ===")
    # ------------------------------------------------------------------

    def make_get_node_bench(cls):
        b = cls()
        b["x"] = 1
        if hasattr(b, "get_node"):
            return lambda: b.get_node("x")
        return None

    run_benchmark("get_node('x')", make_get_node_bench)

    def make_getNode_bench(cls):
        b = cls()
        b["x"] = 1
        if hasattr(b, "getNode"):
            return lambda: b.getNode("x")
        return None

    run_benchmark("getNode('x') [camelCase]", make_getNode_bench)

    # ------------------------------------------------------------------
    print("\n=== Iteration ===")
    # ------------------------------------------------------------------

    def make_keys_bench(cls):
        b = cls()
        for i in range(100):
            b[f"k{i}"] = i
        return lambda: list(b.keys())

    run_benchmark("keys() (100 items)", make_keys_bench, n=2000)

    def make_walk_bench(cls):
        b = cls()
        for i in range(50):
            b[f"k{i}"] = i
        if not hasattr(b, "walk"):
            return None
        # Legacy walk requires callback; new/wrapper support generator mode
        try:
            list(b.walk())
            return lambda: list(b.walk())
        except TypeError:
            collected = []
            return lambda: (collected.clear(), b.walk(lambda n: collected.append(n)))

    run_benchmark("walk() (50 items)", make_walk_bench, n=2000)

    # ------------------------------------------------------------------
    print("\n=== Attribute Operations ===")
    # ------------------------------------------------------------------

    def make_set_attr_bench(cls):
        b = cls()
        b["x"] = 1
        if hasattr(b, "set_attr"):
            return lambda: b.set_attr("x", color="red")
        return None

    run_benchmark("set_attr('x', color='red')", make_set_attr_bench)

    def make_setAttr_bench(cls):
        b = cls()
        b["x"] = 1
        if hasattr(b, "setAttr"):
            return lambda: b.setAttr("x", color="red")
        return None

    run_benchmark("setAttr('x', color='red') [camelCase]", make_setAttr_bench)

    def make_get_attr_bench(cls):
        b = cls()
        b.set_item("x", 1, color="red") if hasattr(b, "set_item") else None
        if hasattr(b, "get_attr"):
            return lambda: b.get_attr("x", "color")
        return None

    run_benchmark("get_attr('x', 'color')", make_get_attr_bench)

    # ------------------------------------------------------------------
    print("\n=== Pop / Delete ===")
    # ------------------------------------------------------------------

    def make_pop_bench(cls):
        def fn():
            b = cls()
            b["x"] = 1
            b.pop("x")
        return fn

    run_benchmark("set + pop('x')", make_pop_bench, n=5000)

    # ------------------------------------------------------------------
    print("\n=== Digest / Query ===")
    # ------------------------------------------------------------------

    def make_digest_bench(cls):
        b = cls()
        for i in range(50):
            b[f"k{i}"] = i
        if hasattr(b, "digest"):
            return lambda: b.digest("#k,#v")
        return None

    run_benchmark("digest('#k,#v') (50 items)", make_digest_bench, n=2000)

    # ------------------------------------------------------------------
    print("\n=== Serialization ===")
    # ------------------------------------------------------------------

    def make_to_xml_bench(cls):
        b = cls()
        for i in range(20):
            b[f"item{i}"] = f"val{i}"
        if hasattr(b, "to_xml"):
            return lambda: b.to_xml()
        elif hasattr(b, "toXml"):
            return lambda: b.toXml()
        return None

    run_benchmark("to_xml (20 items)", make_to_xml_bench, n=1000)

    def make_to_json_bench(cls):
        b = cls()
        for i in range(20):
            b[f"item{i}"] = f"val{i}"
        if hasattr(b, "to_json"):
            return lambda: b.to_json()
        elif hasattr(b, "toJson"):
            return lambda: b.toJson()
        return None

    run_benchmark("to_json (20 items)", make_to_json_bench, n=1000)

    # ------------------------------------------------------------------
    print("\n=== Overhead: __getattr__ resolution ===")
    # ------------------------------------------------------------------

    print("\n  Measures the cost of camelCase → snake_case resolution")
    print("  (only applicable to new_wrapper)\n")

    # Direct snake_case vs camelCase via __getattr__
    for impl_name, cls in IMPLEMENTATIONS:
        b = cls()
        b["x"] = 42

        if hasattr(cls, "get_item") and impl_name == "new_wrapper":
            direct = bench(lambda: b.get_item("x"))
            # getItem goes through __getattr__
            import warnings
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            via_getattr = bench(lambda: b.getItem("x"))
            warnings.resetwarnings()
            overhead = via_getattr - direct
            print(f"  {impl_name}: get_item={direct:.2f}us  getItem(via __getattr__)={via_getattr:.2f}us  overhead={overhead:.2f}us")

    print("\n" + "=" * 80)
    print("Benchmarks completed")
    print("=" * 80)


if __name__ == "__main__":
    main()
