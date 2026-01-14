#!/usr/bin/env python3
# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Benchmarks for genro-bag operations.

Run with: python benchmarks/benchmark_bag.py
"""

import statistics
import sys
import time
import tracemalloc
from contextlib import contextmanager

from genro_bag import Bag
from genro_bag.resolvers import BagCbResolver


@contextmanager
def timer(name: str, iterations: int = 1):
    """Context manager to measure execution time."""
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        yield
        times.append(time.perf_counter() - start)

    avg = statistics.mean(times)
    if iterations > 1:
        std = statistics.stdev(times) if len(times) > 1 else 0
        print(f"{name}: {avg*1000:.3f}ms (±{std*1000:.3f}ms)")
    else:
        print(f"{name}: {avg*1000:.3f}ms")


def benchmark_creation():
    """Benchmark Bag creation."""
    print("\n=== Creation Benchmarks ===")

    # Empty bag
    start = time.perf_counter()
    for _ in range(10000):
        Bag()
    elapsed = time.perf_counter() - start
    print(f"Empty Bag creation (10k): {elapsed*1000:.2f}ms ({elapsed/10000*1e6:.2f}µs/op)")

    # Bag from dict
    data = {f"key{i}": i for i in range(100)}
    start = time.perf_counter()
    for _ in range(1000):
        Bag(data)
    elapsed = time.perf_counter() - start
    print(f"Bag from 100-key dict (1k): {elapsed*1000:.2f}ms ({elapsed/1000*1000:.2f}ms/op)")

    # Nested dict
    nested = {"level1": {"level2": {"level3": {"value": 42}}}}
    start = time.perf_counter()
    for _ in range(1000):
        Bag(nested)
    elapsed = time.perf_counter() - start
    print(f"Bag from nested dict (1k): {elapsed*1000:.2f}ms ({elapsed/1000*1000:.2f}ms/op)")


def benchmark_access():
    """Benchmark value access patterns."""
    print("\n=== Access Benchmarks ===")

    # Prepare bag
    bag = Bag()
    for i in range(1000):
        bag[f"item{i}"] = i

    # Direct access
    start = time.perf_counter()
    for i in range(1000):
        _ = bag[f"item{i}"]
    elapsed = time.perf_counter() - start
    print(f"Direct access (1k keys): {elapsed*1000:.2f}ms ({elapsed/1000*1e6:.2f}µs/op)")

    # Nested access
    bag2 = Bag()
    bag2["a.b.c.d.e"] = "deep"
    start = time.perf_counter()
    for _ in range(10000):
        _ = bag2["a.b.c.d.e"]
    elapsed = time.perf_counter() - start
    print(f"Nested access 5 levels (10k): {elapsed*1000:.2f}ms ({elapsed/10000*1e6:.2f}µs/op)")

    # Index access
    start = time.perf_counter()
    for _ in range(10000):
        _ = bag["#0"]
    elapsed = time.perf_counter() - start
    print(f"Index access #0 (10k): {elapsed*1000:.2f}ms ({elapsed/10000*1e6:.2f}µs/op)")

    # Attribute access
    bag3 = Bag()
    bag3.set_item("node", "value", attr1="a", attr2="b", attr3="c")
    start = time.perf_counter()
    for _ in range(10000):
        _ = bag3["node?attr1"]
    elapsed = time.perf_counter() - start
    print(f"Attribute access (10k): {elapsed*1000:.2f}ms ({elapsed/10000*1e6:.2f}µs/op)")


def benchmark_modification():
    """Benchmark modification operations."""
    print("\n=== Modification Benchmarks ===")

    # Simple assignment
    bag = Bag()
    start = time.perf_counter()
    for i in range(10000):
        bag[f"key{i}"] = i
    elapsed = time.perf_counter() - start
    print(f"Simple assignment (10k): {elapsed*1000:.2f}ms ({elapsed/10000*1e6:.2f}µs/op)")

    # Nested assignment (creates intermediate nodes)
    bag2 = Bag()
    start = time.perf_counter()
    for i in range(1000):
        bag2[f"level1.level2.item{i}"] = i
    elapsed = time.perf_counter() - start
    print(f"Nested assignment (1k): {elapsed*1000:.2f}ms ({elapsed/1000*1000:.2f}ms/op)")

    # set_item with attributes
    bag3 = Bag()
    start = time.perf_counter()
    for i in range(10000):
        bag3.set_item(f"item{i}", i, price=i * 10, name=f"Item {i}")
    elapsed = time.perf_counter() - start
    print(f"set_item with attrs (10k): {elapsed*1000:.2f}ms ({elapsed/10000*1e6:.2f}µs/op)")

    # Update value
    bag4 = Bag()
    bag4["key"] = 0
    start = time.perf_counter()
    for i in range(10000):
        bag4["key"] = i
    elapsed = time.perf_counter() - start
    print(f"Update existing key (10k): {elapsed*1000:.2f}ms ({elapsed/10000*1e6:.2f}µs/op)")


def benchmark_iteration():
    """Benchmark iteration patterns."""
    print("\n=== Iteration Benchmarks ===")

    # Prepare bag
    bag = Bag()
    for i in range(1000):
        bag.set_item(f"item{i}", i, attr=f"value{i}")

    # Iterate nodes
    start = time.perf_counter()
    for _ in range(100):
        for node in bag:
            _ = node.value
    elapsed = time.perf_counter() - start
    print(f"Node iteration (100x1k): {elapsed*1000:.2f}ms ({elapsed/100*1000:.2f}ms/iter)")

    # keys()
    start = time.perf_counter()
    for _ in range(100):
        list(bag.keys())
    elapsed = time.perf_counter() - start
    print(f"keys() (100x1k): {elapsed*1000:.2f}ms ({elapsed/100*1000:.2f}ms/iter)")

    # values()
    start = time.perf_counter()
    for _ in range(100):
        list(bag.values())
    elapsed = time.perf_counter() - start
    print(f"values() (100x1k): {elapsed*1000:.2f}ms ({elapsed/100*1000:.2f}ms/iter)")

    # items()
    start = time.perf_counter()
    for _ in range(100):
        list(bag.items())
    elapsed = time.perf_counter() - start
    print(f"items() (100x1k): {elapsed*1000:.2f}ms ({elapsed/100*1000:.2f}ms/iter)")


def benchmark_serialization():
    """Benchmark serialization operations."""
    print("\n=== Serialization Benchmarks ===")

    # Prepare bag with root wrapper for valid XML
    bag = Bag()
    items = bag["items"] = Bag()
    for i in range(100):
        items.set_item(f"item{i}", f"value{i}", num=i, flag=i % 2 == 0)

    # to_xml
    start = time.perf_counter()
    for _ in range(100):
        xml = bag.to_xml()
    elapsed = time.perf_counter() - start
    print(f"to_xml (100x100 nodes): {elapsed*1000:.2f}ms ({elapsed/100*1000:.2f}ms/op)")
    print(f"  XML size: {len(xml)} bytes")

    # from_xml
    start = time.perf_counter()
    for _ in range(100):
        Bag.from_xml(xml)
    elapsed = time.perf_counter() - start
    print(f"from_xml (100x): {elapsed*1000:.2f}ms ({elapsed/100*1000:.2f}ms/op)")

    # to_tytx (JSON - default)
    start = time.perf_counter()
    for _ in range(100):
        tytx_json = bag.to_tytx(transport="json")
    elapsed = time.perf_counter() - start
    print(f"to_tytx JSON (100x100 nodes): {elapsed*1000:.2f}ms ({elapsed/100*1000:.2f}ms/op)")
    print(f"  TYTX JSON size: {len(tytx_json)} bytes")

    # from_tytx (JSON)
    start = time.perf_counter()
    for _ in range(100):
        Bag.from_tytx(tytx_json)
    elapsed = time.perf_counter() - start
    print(f"from_tytx JSON (100x): {elapsed*1000:.2f}ms ({elapsed/100*1000:.2f}ms/op)")

    # to_tytx (MessagePack)
    try:
        start = time.perf_counter()
        for _ in range(100):
            tytx_mp = bag.to_tytx(transport="msgpack")
        elapsed = time.perf_counter() - start
        print(
            f"to_tytx MsgPack (100x100 nodes): {elapsed*1000:.2f}ms ({elapsed/100*1000:.2f}ms/op)"
        )
        print(f"  TYTX MsgPack size: {len(tytx_mp)} bytes")

        # from_tytx (MessagePack)
        start = time.perf_counter()
        for _ in range(100):
            Bag.from_tytx(tytx_mp, transport="msgpack")
        elapsed = time.perf_counter() - start
        print(f"from_tytx MsgPack (100x): {elapsed*1000:.2f}ms ({elapsed/100*1000:.2f}ms/op)")
    except ImportError:
        print("  (MessagePack not available - install msgpack)")


def benchmark_resolvers():
    """Benchmark resolver operations."""
    print("\n=== Resolver Benchmarks ===")

    call_count = 0

    def simple_callback():
        nonlocal call_count
        call_count += 1
        return call_count

    # Resolver creation
    start = time.perf_counter()
    for _ in range(10000):
        BagCbResolver(simple_callback)
    elapsed = time.perf_counter() - start
    print(f"BagCbResolver creation (10k): {elapsed*1000:.2f}ms ({elapsed/10000*1e6:.2f}µs/op)")

    # Resolver access (no cache)
    bag = Bag()
    call_count = 0
    bag["counter"] = BagCbResolver(simple_callback, cache_time=0)
    start = time.perf_counter()
    for _ in range(1000):
        _ = bag["counter"]
    elapsed = time.perf_counter() - start
    print(f"Resolver access no cache (1k): {elapsed*1000:.2f}ms ({elapsed/1000*1e6:.2f}µs/op)")
    print(f"  Callback invocations: {call_count}")

    # Resolver access (with cache)
    bag2 = Bag()
    call_count = 0
    bag2["cached"] = BagCbResolver(simple_callback, cache_time=60)
    start = time.perf_counter()
    for _ in range(10000):
        _ = bag2["cached"]
    elapsed = time.perf_counter() - start
    print(f"Resolver access cached (10k): {elapsed*1000:.2f}ms ({elapsed/10000*1e6:.2f}µs/op)")
    print(f"  Callback invocations: {call_count}")


def benchmark_subscriptions():
    """Benchmark subscription operations."""
    print("\n=== Subscription Benchmarks ===")

    events = []

    def on_change(**kw):
        events.append(kw["evt"])

    # Subscription setup
    bag = Bag()
    start = time.perf_counter()
    bag.subscribe("watcher", any=on_change)
    elapsed = time.perf_counter() - start
    print(f"Subscribe: {elapsed*1e6:.2f}µs")

    # Modifications with subscription
    start = time.perf_counter()
    for i in range(1000):
        bag[f"key{i}"] = i
    elapsed = time.perf_counter() - start
    print(f"1k inserts with subscription: {elapsed*1000:.2f}ms ({elapsed/1000*1e6:.2f}µs/op)")
    print(f"  Events fired: {len(events)}")

    # Updates with subscription
    events.clear()
    start = time.perf_counter()
    for i in range(1000):
        bag["key0"] = i
    elapsed = time.perf_counter() - start
    print(f"1k updates with subscription: {elapsed*1000:.2f}ms ({elapsed/1000*1e6:.2f}µs/op)")
    print(f"  Events fired: {len(events)}")

    # Without subscription (for comparison)
    bag2 = Bag()
    start = time.perf_counter()
    for i in range(1000):
        bag2[f"key{i}"] = i
    elapsed = time.perf_counter() - start
    print(f"1k inserts without subscription: {elapsed*1000:.2f}ms ({elapsed/1000*1e6:.2f}µs/op)")


def benchmark_builders():
    """Benchmark builder operations."""
    print("\n=== Builder Benchmarks ===")

    from genro_bag.builders import HtmlBuilder

    # Builder creation
    start = time.perf_counter()
    for _ in range(1000):
        Bag(builder=HtmlBuilder())
    elapsed = time.perf_counter() - start
    print(f"Bag with HtmlBuilder (1k): {elapsed*1000:.2f}ms ({elapsed/1000*1000:.2f}ms/op)")

    # Building structure
    start = time.perf_counter()
    for _ in range(100):
        bag = Bag(builder=HtmlBuilder())
        html = bag.html()
        head = html.head()
        head.title(value="Test")
        body = html.body()
        for i in range(10):
            div = body.div(class_=f"item-{i}")
            div.p(value=f"Paragraph {i}")
    elapsed = time.perf_counter() - start
    print(f"Build HTML structure (100x): {elapsed*1000:.2f}ms ({elapsed/100*1000:.2f}ms/op)")


def benchmark_large_bag():
    """Benchmark operations on large bags."""
    print("\n=== Large Bag Benchmarks (100k nodes) ===")

    # Create large bag
    print("Creating 100k node bag...")
    start = time.perf_counter()
    bag = Bag()
    for i in range(100000):
        bag[f"item{i}"] = i
    elapsed = time.perf_counter() - start
    print(f"Create 100k nodes: {elapsed*1000:.2f}ms ({elapsed/100000*1e6:.2f}µs/op)")

    # Random access
    import random

    keys = [f"item{random.randint(0, 99999)}" for _ in range(1000)]
    start = time.perf_counter()
    for key in keys:
        _ = bag[key]
    elapsed = time.perf_counter() - start
    print(f"Random access (1k on 100k): {elapsed*1000:.2f}ms ({elapsed/1000*1e6:.2f}µs/op)")

    # Iteration
    start = time.perf_counter()
    count = sum(1 for _ in bag)
    elapsed = time.perf_counter() - start
    print(f"Full iteration (100k nodes): {elapsed*1000:.2f}ms")

    # len()
    start = time.perf_counter()
    for _ in range(1000):
        _ = len(bag)
    elapsed = time.perf_counter() - start
    print(f"len() on 100k bag (1k): {elapsed*1000:.2f}ms ({elapsed/1000*1e6:.2f}µs/op)")


def benchmark_very_large_flat_bag():
    """Benchmark operations on very large flat bag (1M nodes)."""
    print("\n=== Very Large Flat Bag Benchmarks (1M nodes) ===")

    import random

    # Create 1M node bag
    print("Creating 1M node flat bag...")
    start = time.perf_counter()
    bag = Bag()
    for i in range(1000000):
        bag[f"item{i}"] = i
    elapsed = time.perf_counter() - start
    print(f"Create 1M nodes: {elapsed:.2f}s ({elapsed/1000000*1e6:.2f}µs/op)")

    # Sequential access (first 10k)
    start = time.perf_counter()
    for i in range(10000):
        _ = bag[f"item{i}"]
    elapsed = time.perf_counter() - start
    print(f"Sequential access (10k on 1M): {elapsed*1000:.2f}ms ({elapsed/10000*1e6:.2f}µs/op)")

    # Random access
    keys = [f"item{random.randint(0, 999999)}" for _ in range(10000)]
    start = time.perf_counter()
    for key in keys:
        _ = bag[key]
    elapsed = time.perf_counter() - start
    print(f"Random access (10k on 1M): {elapsed*1000:.2f}ms ({elapsed/10000*1e6:.2f}µs/op)")

    # Update existing keys
    start = time.perf_counter()
    for i in range(10000):
        bag[f"item{i}"] = i * 2
    elapsed = time.perf_counter() - start
    print(f"Update existing (10k on 1M): {elapsed*1000:.2f}ms ({elapsed/10000*1e6:.2f}µs/op)")

    # len()
    start = time.perf_counter()
    for _ in range(100):
        _ = len(bag)
    elapsed = time.perf_counter() - start
    print(f"len() on 1M bag (100x): {elapsed*1000:.2f}ms ({elapsed/100*1000:.2f}ms/op)")

    # Iteration (partial - first 100k)
    start = time.perf_counter()
    count = 0
    for node in bag:
        count += 1
        if count >= 100000:
            break
    elapsed = time.perf_counter() - start
    print(f"Partial iteration (100k of 1M): {elapsed*1000:.2f}ms")

    # Full iteration
    start = time.perf_counter()
    count = sum(1 for _ in bag)
    elapsed = time.perf_counter() - start
    print(f"Full iteration (1M nodes): {elapsed:.2f}s")


def format_bytes(size):
    """Format bytes to human readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"


def benchmark_memory():
    """Benchmark memory consumption."""
    print("\n=== Memory Benchmarks ===")

    # Empty structures
    empty_dict = {}
    empty_bag = Bag()
    print(f"Empty dict: {sys.getsizeof(empty_dict)} bytes")
    print(f"Empty Bag: {sys.getsizeof(empty_bag)} bytes (shallow)")

    # Small structures (100 items)
    tracemalloc.start()
    d = {f"key{i}": i for i in range(100)}
    dict_snapshot = tracemalloc.take_snapshot()
    dict_mem = sum(stat.size for stat in dict_snapshot.statistics("lineno"))
    tracemalloc.stop()

    tracemalloc.start()
    bag = Bag()
    for i in range(100):
        bag[f"key{i}"] = i
    bag_snapshot = tracemalloc.take_snapshot()
    bag_mem = sum(stat.size for stat in bag_snapshot.statistics("lineno"))
    tracemalloc.stop()

    print("\n100 items:")
    print(f"  dict: {format_bytes(dict_mem)}")
    print(f"  Bag: {format_bytes(bag_mem)}")
    print(f"  Ratio: {bag_mem/dict_mem:.1f}x")

    # Medium structures (10k items)
    tracemalloc.start()
    d = {f"key{i}": i for i in range(10000)}
    dict_snapshot = tracemalloc.take_snapshot()
    dict_mem = sum(stat.size for stat in dict_snapshot.statistics("lineno"))
    tracemalloc.stop()

    tracemalloc.start()
    bag = Bag()
    for i in range(10000):
        bag[f"key{i}"] = i
    bag_snapshot = tracemalloc.take_snapshot()
    bag_mem = sum(stat.size for stat in bag_snapshot.statistics("lineno"))
    tracemalloc.stop()

    print("\n10,000 items:")
    print(f"  dict: {format_bytes(dict_mem)}")
    print(f"  Bag: {format_bytes(bag_mem)}")
    print(f"  Ratio: {bag_mem/dict_mem:.1f}x")
    print(f"  Per-item overhead: {(bag_mem - dict_mem) / 10000:.0f} bytes/item")

    # Large structures (100k items)
    tracemalloc.start()
    d = {f"key{i}": i for i in range(100000)}
    dict_snapshot = tracemalloc.take_snapshot()
    dict_mem = sum(stat.size for stat in dict_snapshot.statistics("lineno"))
    tracemalloc.stop()

    tracemalloc.start()
    bag = Bag()
    for i in range(100000):
        bag[f"key{i}"] = i
    bag_snapshot = tracemalloc.take_snapshot()
    bag_mem = sum(stat.size for stat in bag_snapshot.statistics("lineno"))
    tracemalloc.stop()

    print("\n100,000 items:")
    print(f"  dict: {format_bytes(dict_mem)}")
    print(f"  Bag: {format_bytes(bag_mem)}")
    print(f"  Ratio: {bag_mem/dict_mem:.1f}x")
    print(f"  Per-item overhead: {(bag_mem - dict_mem) / 100000:.0f} bytes/item")

    # With attributes
    tracemalloc.start()
    bag = Bag()
    for i in range(10000):
        bag.set_item(f"item{i}", i, price=i * 10, name=f"Item {i}", active=True)
    bag_snapshot = tracemalloc.take_snapshot()
    bag_with_attrs_mem = sum(stat.size for stat in bag_snapshot.statistics("lineno"))
    tracemalloc.stop()

    print("\n10,000 items with 3 attributes each:")
    print(f"  Bag: {format_bytes(bag_with_attrs_mem)}")
    print(f"  Per-item (with attrs): {bag_with_attrs_mem / 10000:.0f} bytes/item")

    # Nested structure
    tracemalloc.start()
    bag = Bag()
    for i in range(1000):
        bag[f"level1.level2.level3.item{i}"] = i
    bag_snapshot = tracemalloc.take_snapshot()
    nested_mem = sum(stat.size for stat in bag_snapshot.statistics("lineno"))
    tracemalloc.stop()

    print("\n1,000 items nested 3 levels deep:")
    print(f"  Bag: {format_bytes(nested_mem)}")
    print(f"  Per-item: {nested_mem / 1000:.0f} bytes/item")

    # Builder overhead
    from genro_bag.builders import HtmlBuilder

    # Bag without builder
    tracemalloc.start()
    bag_no_builder = Bag()
    for i in range(100):
        bag_no_builder[f"div_{i}"] = f"content{i}"
    no_builder_snapshot = tracemalloc.take_snapshot()
    no_builder_mem = sum(stat.size for stat in no_builder_snapshot.statistics("lineno"))
    tracemalloc.stop()

    # Bag with HtmlBuilder
    tracemalloc.start()
    bag_with_builder = Bag(builder=HtmlBuilder())
    for i in range(100):
        bag_with_builder.div(value=f"content{i}")
    builder_snapshot = tracemalloc.take_snapshot()
    builder_mem = sum(stat.size for stat in builder_snapshot.statistics("lineno"))
    tracemalloc.stop()

    print("\n100 items - Builder overhead:")
    print(f"  Bag without builder: {format_bytes(no_builder_mem)}")
    print(f"  Bag with HtmlBuilder: {format_bytes(builder_mem)}")
    print(f"  Builder overhead: {format_bytes(builder_mem - no_builder_mem)}")
    print(f"  Ratio: {builder_mem/no_builder_mem:.2f}x")

    # Timing comparison
    start = time.perf_counter()
    for _ in range(1000):
        bag = Bag()
        for i in range(10):
            bag[f"item{i}"] = i
    elapsed_no_builder = time.perf_counter() - start

    start = time.perf_counter()
    for _ in range(1000):
        bag = Bag(builder=HtmlBuilder())
        for i in range(10):
            bag.div(value=i)
    elapsed_with_builder = time.perf_counter() - start

    print("\n1000x create Bag with 10 items - Time:")
    print(f"  Without builder: {elapsed_no_builder*1000:.2f}ms")
    print(f"  With HtmlBuilder: {elapsed_with_builder*1000:.2f}ms")
    print(f"  Builder slowdown: {elapsed_with_builder/elapsed_no_builder:.2f}x")


def benchmark_comparison_dict():
    """Compare with plain dict for baseline."""
    print("\n=== Comparison with flat dict ===")

    # Dict creation
    start = time.perf_counter()
    for _ in range(10000):
        {}
    elapsed = time.perf_counter() - start
    print(f"Empty dict creation (10k): {elapsed*1000:.2f}ms ({elapsed/10000*1e6:.2f}µs/op)")

    # Dict from dict
    data = {f"key{i}": i for i in range(100)}
    start = time.perf_counter()
    for _ in range(1000):
        dict(data)
    elapsed = time.perf_counter() - start
    print(f"dict() from 100-key dict (1k): {elapsed*1000:.2f}ms ({elapsed/1000*1000:.2f}ms/op)")

    # Dict assignment
    d = {}
    start = time.perf_counter()
    for i in range(10000):
        d[f"key{i}"] = i
    elapsed = time.perf_counter() - start
    print(f"Dict assignment (10k): {elapsed*1000:.2f}ms ({elapsed/10000*1e6:.2f}µs/op)")

    # Dict access
    start = time.perf_counter()
    for i in range(10000):
        _ = d[f"key{i}"]
    elapsed = time.perf_counter() - start
    print(f"Dict access (10k): {elapsed*1000:.2f}ms ({elapsed/10000*1e6:.2f}µs/op)")


def benchmark_comparison_hierarchical():
    """Compare with other hierarchical structures."""
    import xml.etree.ElementTree as ET

    print("\n=== Comparison with hierarchical structures ===")

    # --- NESTED DICT ---
    print("\n-- Nested dict --")

    # Creation: nested dict 3 levels, 1000 items
    start = time.perf_counter()
    for _ in range(100):
        d = {}
        for i in range(1000):
            if "level1" not in d:
                d["level1"] = {}
            if "level2" not in d["level1"]:
                d["level1"]["level2"] = {}
            d["level1"]["level2"][f"item{i}"] = i
    elapsed = time.perf_counter() - start
    print(
        f"Nested dict creation (100x1k items, 3 levels): {elapsed*1000:.2f}ms ({elapsed/100*1000:.2f}ms/op)"
    )

    # Access: nested dict
    d = {"level1": {"level2": {f"item{i}": i for i in range(1000)}}}
    start = time.perf_counter()
    for _ in range(10000):
        _ = d["level1"]["level2"]["item500"]
    elapsed = time.perf_counter() - start
    print(f"Nested dict access (10k): {elapsed*1000:.2f}ms ({elapsed/10000*1e6:.2f}µs/op)")

    # Bag equivalent
    start = time.perf_counter()
    for _ in range(100):
        bag = Bag()
        for i in range(1000):
            bag[f"level1.level2.item{i}"] = i
    elapsed = time.perf_counter() - start
    print(
        f"Bag creation (100x1k items, 3 levels): {elapsed*1000:.2f}ms ({elapsed/100*1000:.2f}ms/op)"
    )

    bag = Bag()
    for i in range(1000):
        bag[f"level1.level2.item{i}"] = i
    start = time.perf_counter()
    for _ in range(10000):
        _ = bag["level1.level2.item500"]
    elapsed = time.perf_counter() - start
    print(f"Bag access (10k): {elapsed*1000:.2f}ms ({elapsed/10000*1e6:.2f}µs/op)")

    # --- ELEMENTTREE ---
    print("\n-- xml.etree.ElementTree --")

    # Creation: ElementTree with 1000 elements
    start = time.perf_counter()
    for _ in range(100):
        root = ET.Element("root")
        level1 = ET.SubElement(root, "level1")
        level2 = ET.SubElement(level1, "level2")
        for i in range(1000):
            item = ET.SubElement(level2, f"item{i}")
            item.text = str(i)
    elapsed = time.perf_counter() - start
    print(
        f"ElementTree creation (100x1k items): {elapsed*1000:.2f}ms ({elapsed/100*1000:.2f}ms/op)"
    )

    # Access by find (XPath-like)
    root = ET.Element("root")
    level1 = ET.SubElement(root, "level1")
    level2 = ET.SubElement(level1, "level2")
    for i in range(1000):
        item = ET.SubElement(level2, f"item{i}")
        item.text = str(i)
        item.set("num", str(i))

    start = time.perf_counter()
    for _ in range(10000):
        _ = root.find(".//item500")
    elapsed = time.perf_counter() - start
    print(f"ElementTree find (10k): {elapsed*1000:.2f}ms ({elapsed/10000*1e6:.2f}µs/op)")

    # Access by direct traversal
    start = time.perf_counter()
    for _ in range(10000):
        _ = root[0][0][500].text
    elapsed = time.perf_counter() - start
    print(f"ElementTree index access (10k): {elapsed*1000:.2f}ms ({elapsed/10000*1e6:.2f}µs/op)")

    # Attribute access
    start = time.perf_counter()
    for _ in range(10000):
        _ = root[0][0][500].get("num")
    elapsed = time.perf_counter() - start
    print(f"ElementTree attrib access (10k): {elapsed*1000:.2f}ms ({elapsed/10000*1e6:.2f}µs/op)")

    # Bag equivalent with attributes
    bag = Bag()
    for i in range(1000):
        bag.set_item(f"level1.level2.item{i}", str(i), num=str(i))

    start = time.perf_counter()
    for _ in range(10000):
        _ = bag["level1.level2.item500"]
    elapsed = time.perf_counter() - start
    print(f"Bag path access (10k): {elapsed*1000:.2f}ms ({elapsed/10000*1e6:.2f}µs/op)")

    start = time.perf_counter()
    for _ in range(10000):
        _ = bag["level1.level2.item500?num"]
    elapsed = time.perf_counter() - start
    print(f"Bag attribute access (10k): {elapsed*1000:.2f}ms ({elapsed/10000*1e6:.2f}µs/op)")

    # --- SERIALIZATION COMPARISON ---
    print("\n-- Serialization comparison --")

    # ElementTree to string
    root = ET.Element("items")
    for i in range(100):
        item = ET.SubElement(root, f"item{i}")
        item.text = f"value{i}"
        item.set("num", str(i))
        item.set("flag", str(i % 2 == 0))

    start = time.perf_counter()
    for _ in range(100):
        xml_str = ET.tostring(root, encoding="unicode")
    elapsed = time.perf_counter() - start
    print(
        f"ElementTree tostring (100x100 items): {elapsed*1000:.2f}ms ({elapsed/100*1000:.2f}ms/op)"
    )
    print(f"  Size: {len(xml_str)} bytes")

    start = time.perf_counter()
    for _ in range(100):
        ET.fromstring(xml_str)
    elapsed = time.perf_counter() - start
    print(f"ElementTree fromstring (100x): {elapsed*1000:.2f}ms ({elapsed/100*1000:.2f}ms/op)")

    # Bag equivalent
    bag = Bag()
    items = bag["items"] = Bag()
    for i in range(100):
        items.set_item(f"item{i}", f"value{i}", num=i, flag=i % 2 == 0)

    start = time.perf_counter()
    for _ in range(100):
        bag_xml = bag.to_xml()
    elapsed = time.perf_counter() - start
    print(f"Bag to_xml (100x100 items): {elapsed*1000:.2f}ms ({elapsed/100*1000:.2f}ms/op)")
    print(f"  Size: {len(bag_xml)} bytes")

    start = time.perf_counter()
    for _ in range(100):
        Bag.from_xml(bag_xml)
    elapsed = time.perf_counter() - start
    print(f"Bag from_xml (100x): {elapsed*1000:.2f}ms ({elapsed/100*1000:.2f}ms/op)")

    # --- MEMORY COMPARISON ---
    print("\n-- Memory comparison (1000 items, 3 levels) --")

    # Nested dict
    tracemalloc.start()
    d = {"level1": {"level2": {f"item{i}": i for i in range(1000)}}}
    snapshot = tracemalloc.take_snapshot()
    nested_dict_mem = sum(stat.size for stat in snapshot.statistics("lineno"))
    tracemalloc.stop()
    print(f"Nested dict: {format_bytes(nested_dict_mem)}")

    # ElementTree
    tracemalloc.start()
    root = ET.Element("root")
    level1 = ET.SubElement(root, "level1")
    level2 = ET.SubElement(level1, "level2")
    for i in range(1000):
        item = ET.SubElement(level2, f"item{i}")
        item.text = str(i)
    snapshot = tracemalloc.take_snapshot()
    et_mem = sum(stat.size for stat in snapshot.statistics("lineno"))
    tracemalloc.stop()
    print(f"ElementTree: {format_bytes(et_mem)}")

    # Bag
    tracemalloc.start()
    bag = Bag()
    for i in range(1000):
        bag[f"level1.level2.item{i}"] = i
    snapshot = tracemalloc.take_snapshot()
    bag_mem = sum(stat.size for stat in snapshot.statistics("lineno"))
    tracemalloc.stop()
    print(f"Bag: {format_bytes(bag_mem)}")

    print("\nRatios (vs nested dict):")
    print(f"  ElementTree: {et_mem/nested_dict_mem:.1f}x")
    print(f"  Bag: {bag_mem/nested_dict_mem:.1f}x")


def main():
    print("=" * 60)
    print("genro-bag Benchmarks")
    print("=" * 60)

    benchmark_comparison_dict()
    benchmark_comparison_hierarchical()
    benchmark_memory()
    benchmark_creation()
    benchmark_access()
    benchmark_modification()
    benchmark_iteration()
    benchmark_serialization()
    benchmark_resolvers()
    benchmark_subscriptions()
    benchmark_builders()
    benchmark_large_bag()
    benchmark_very_large_flat_bag()

    print("\n" + "=" * 60)
    print("Benchmarks completed")
    print("=" * 60)


if __name__ == "__main__":
    main()
