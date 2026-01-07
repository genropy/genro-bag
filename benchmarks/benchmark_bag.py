#!/usr/bin/env python3
# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Benchmarks for genro-bag operations.

Run with: python benchmarks/benchmark_bag.py
"""

import statistics
import time
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
    data = {f'key{i}': i for i in range(100)}
    start = time.perf_counter()
    for _ in range(1000):
        Bag(data)
    elapsed = time.perf_counter() - start
    print(f"Bag from 100-key dict (1k): {elapsed*1000:.2f}ms ({elapsed/1000*1000:.2f}ms/op)")

    # Nested dict
    nested = {'level1': {'level2': {'level3': {'value': 42}}}}
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
        bag[f'item{i}'] = i

    # Direct access
    start = time.perf_counter()
    for i in range(1000):
        _ = bag[f'item{i}']
    elapsed = time.perf_counter() - start
    print(f"Direct access (1k keys): {elapsed*1000:.2f}ms ({elapsed/1000*1e6:.2f}µs/op)")

    # Nested access
    bag2 = Bag()
    bag2['a.b.c.d.e'] = 'deep'
    start = time.perf_counter()
    for _ in range(10000):
        _ = bag2['a.b.c.d.e']
    elapsed = time.perf_counter() - start
    print(f"Nested access 5 levels (10k): {elapsed*1000:.2f}ms ({elapsed/10000*1e6:.2f}µs/op)")

    # Index access
    start = time.perf_counter()
    for _ in range(10000):
        _ = bag['#0']
    elapsed = time.perf_counter() - start
    print(f"Index access #0 (10k): {elapsed*1000:.2f}ms ({elapsed/10000*1e6:.2f}µs/op)")

    # Attribute access
    bag3 = Bag()
    bag3.set_item('node', 'value', attr1='a', attr2='b', attr3='c')
    start = time.perf_counter()
    for _ in range(10000):
        _ = bag3['node?attr1']
    elapsed = time.perf_counter() - start
    print(f"Attribute access (10k): {elapsed*1000:.2f}ms ({elapsed/10000*1e6:.2f}µs/op)")


def benchmark_modification():
    """Benchmark modification operations."""
    print("\n=== Modification Benchmarks ===")

    # Simple assignment
    bag = Bag()
    start = time.perf_counter()
    for i in range(10000):
        bag[f'key{i}'] = i
    elapsed = time.perf_counter() - start
    print(f"Simple assignment (10k): {elapsed*1000:.2f}ms ({elapsed/10000*1e6:.2f}µs/op)")

    # Nested assignment (creates intermediate nodes)
    bag2 = Bag()
    start = time.perf_counter()
    for i in range(1000):
        bag2[f'level1.level2.item{i}'] = i
    elapsed = time.perf_counter() - start
    print(f"Nested assignment (1k): {elapsed*1000:.2f}ms ({elapsed/1000*1000:.2f}ms/op)")

    # set_item with attributes
    bag3 = Bag()
    start = time.perf_counter()
    for i in range(10000):
        bag3.set_item(f'item{i}', i, price=i*10, name=f'Item {i}')
    elapsed = time.perf_counter() - start
    print(f"set_item with attrs (10k): {elapsed*1000:.2f}ms ({elapsed/10000*1e6:.2f}µs/op)")

    # Update value
    bag4 = Bag()
    bag4['key'] = 0
    start = time.perf_counter()
    for i in range(10000):
        bag4['key'] = i
    elapsed = time.perf_counter() - start
    print(f"Update existing key (10k): {elapsed*1000:.2f}ms ({elapsed/10000*1e6:.2f}µs/op)")


def benchmark_iteration():
    """Benchmark iteration patterns."""
    print("\n=== Iteration Benchmarks ===")

    # Prepare bag
    bag = Bag()
    for i in range(1000):
        bag.set_item(f'item{i}', i, attr=f'value{i}')

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
    items = bag['items'] = Bag()
    for i in range(100):
        items.set_item(f'item{i}', f'value{i}', num=i, flag=i % 2 == 0)

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

    # to_tytx
    start = time.perf_counter()
    for _ in range(100):
        tytx = bag.to_tytx()
    elapsed = time.perf_counter() - start
    print(f"to_tytx (100x100 nodes): {elapsed*1000:.2f}ms ({elapsed/100*1000:.2f}ms/op)")
    print(f"  TYTX size: {len(tytx)} bytes")

    # from_tytx
    start = time.perf_counter()
    for _ in range(100):
        Bag.from_tytx(tytx)
    elapsed = time.perf_counter() - start
    print(f"from_tytx (100x): {elapsed*1000:.2f}ms ({elapsed/100*1000:.2f}ms/op)")


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
    bag['counter'] = BagCbResolver(simple_callback, cache_time=0)
    start = time.perf_counter()
    for _ in range(1000):
        _ = bag['counter']
    elapsed = time.perf_counter() - start
    print(f"Resolver access no cache (1k): {elapsed*1000:.2f}ms ({elapsed/1000*1e6:.2f}µs/op)")
    print(f"  Callback invocations: {call_count}")

    # Resolver access (with cache)
    bag2 = Bag()
    call_count = 0
    bag2['cached'] = BagCbResolver(simple_callback, cache_time=60)
    start = time.perf_counter()
    for _ in range(10000):
        _ = bag2['cached']
    elapsed = time.perf_counter() - start
    print(f"Resolver access cached (10k): {elapsed*1000:.2f}ms ({elapsed/10000*1e6:.2f}µs/op)")
    print(f"  Callback invocations: {call_count}")


def benchmark_subscriptions():
    """Benchmark subscription operations."""
    print("\n=== Subscription Benchmarks ===")

    events = []
    def on_change(**kw):
        events.append(kw['evt'])

    # Subscription setup
    bag = Bag()
    start = time.perf_counter()
    bag.subscribe('watcher', any=on_change)
    elapsed = time.perf_counter() - start
    print(f"Subscribe: {elapsed*1e6:.2f}µs")

    # Modifications with subscription
    start = time.perf_counter()
    for i in range(1000):
        bag[f'key{i}'] = i
    elapsed = time.perf_counter() - start
    print(f"1k inserts with subscription: {elapsed*1000:.2f}ms ({elapsed/1000*1e6:.2f}µs/op)")
    print(f"  Events fired: {len(events)}")

    # Updates with subscription
    events.clear()
    start = time.perf_counter()
    for i in range(1000):
        bag['key0'] = i
    elapsed = time.perf_counter() - start
    print(f"1k updates with subscription: {elapsed*1000:.2f}ms ({elapsed/1000*1e6:.2f}µs/op)")
    print(f"  Events fired: {len(events)}")

    # Without subscription (for comparison)
    bag2 = Bag()
    start = time.perf_counter()
    for i in range(1000):
        bag2[f'key{i}'] = i
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
        head.title(value='Test')
        body = html.body()
        for i in range(10):
            div = body.div(class_=f'item-{i}')
            div.p(value=f'Paragraph {i}')
    elapsed = time.perf_counter() - start
    print(f"Build HTML structure (100x): {elapsed*1000:.2f}ms ({elapsed/100*1000:.2f}ms/op)")


def benchmark_large_bag():
    """Benchmark operations on large bags."""
    print("\n=== Large Bag Benchmarks ===")

    # Create large bag
    print("Creating 100k node bag...")
    start = time.perf_counter()
    bag = Bag()
    for i in range(100000):
        bag[f'item{i}'] = i
    elapsed = time.perf_counter() - start
    print(f"Create 100k nodes: {elapsed*1000:.2f}ms ({elapsed/100000*1e6:.2f}µs/op)")

    # Random access
    import random
    keys = [f'item{random.randint(0, 99999)}' for _ in range(1000)]
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


def benchmark_comparison_dict():
    """Compare with plain dict for baseline."""
    print("\n=== Comparison with dict ===")

    # Dict creation
    start = time.perf_counter()
    for _ in range(10000):
        {}
    elapsed = time.perf_counter() - start
    print(f"Empty dict creation (10k): {elapsed*1000:.2f}ms ({elapsed/10000*1e6:.2f}µs/op)")

    # Dict from dict
    data = {f'key{i}': i for i in range(100)}
    start = time.perf_counter()
    for _ in range(1000):
        dict(data)
    elapsed = time.perf_counter() - start
    print(f"dict() from 100-key dict (1k): {elapsed*1000:.2f}ms ({elapsed/1000*1000:.2f}ms/op)")

    # Dict assignment
    d = {}
    start = time.perf_counter()
    for i in range(10000):
        d[f'key{i}'] = i
    elapsed = time.perf_counter() - start
    print(f"Dict assignment (10k): {elapsed*1000:.2f}ms ({elapsed/10000*1e6:.2f}µs/op)")

    # Dict access
    start = time.perf_counter()
    for i in range(10000):
        _ = d[f'key{i}']
    elapsed = time.perf_counter() - start
    print(f"Dict access (10k): {elapsed*1000:.2f}ms ({elapsed/10000*1e6:.2f}µs/op)")


def main():
    print("=" * 60)
    print("genro-bag Benchmarks")
    print("=" * 60)

    benchmark_comparison_dict()
    benchmark_creation()
    benchmark_access()
    benchmark_modification()
    benchmark_iteration()
    benchmark_serialization()
    benchmark_resolvers()
    benchmark_subscriptions()
    benchmark_builders()
    benchmark_large_bag()

    print("\n" + "=" * 60)
    print("Benchmarks completed")
    print("=" * 60)


if __name__ == '__main__':
    main()
