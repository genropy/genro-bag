#!/usr/bin/env python3
# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Profile individual steps of get_item to identify bottlenecks.

Run with: python benchmarks/profile_get_item.py
"""

import inspect
import time

from genro_bag import Bag
from genro_bag.bagnode import BagNodeContainer
from genro_toolbox import smartcontinuation, smartsplit

N = 500_000

_baseline_ns = None


def bench(label, fn, n=N, baseline=False):
    """Run fn() n times and print timing with % vs baseline."""
    global _baseline_ns
    # warmup
    for _ in range(1000):
        fn()
    start = time.perf_counter()
    for _ in range(n):
        fn()
    elapsed = time.perf_counter() - start
    ns_op = elapsed / n * 1e9
    if baseline:
        _baseline_ns = ns_op
    if _baseline_ns and not baseline and _baseline_ns > 0:
        ratio = ns_op / _baseline_ns
        print(f"  {label:50s} {ns_op:8.1f} ns/op  ({ratio:5.1f}x baseline)")
    else:
        print(f"  {label:50s} {ns_op:8.1f} ns/op")
    return ns_op


def main():
    # Setup: bag with 'pippo' present
    bag = Bag()
    bag["pippo"] = 42
    bag["a.b.c"] = 99
    node = bag._nodes._dict["pippo"]

    print("=" * 72)
    print(f"Profiling get_item steps  ({N:,} iterations each)")
    print("=" * 72)

    # ---------------------------------------------------------------
    print("\n--- Full operations (end-to-end) ---")
    # ---------------------------------------------------------------

    bench("bag.get_item('pippo')",
          lambda: bag.get_item("pippo"))

    bench("bag.get_item('pippo', static=True)",
          lambda: bag.get_item("pippo", static=True))

    bench("bag.get_item('a.b.c')",
          lambda: bag.get_item("a.b.c"))

    bench("bag['pippo']  (__getitem__)",
          lambda: bag["pippo"])

    bench("dict.__getitem__ (=== BASELINE ===)",
          lambda: bag._nodes._dict["pippo"], baseline=True)

    # ---------------------------------------------------------------
    print("\n--- Step-by-step breakdown for get_item('pippo') ---")
    # ---------------------------------------------------------------

    path = "pippo"

    # Step 1: bool check on path
    bench("1. if not path",
          lambda: not path)

    # Step 2: _htraverse call
    bench("2. _htraverse('pippo', static=False)  [full]",
          lambda: bag._htraverse(path, static=False))

    # Step 2a: _htraverse_before
    bench("2a. _htraverse_before('pippo')",
          lambda: bag._htraverse_before(path))

    # Step 2a-i: str.replace inside _htraverse_before
    bench("    2a-i.   path.replace('../', '#parent.')",
          lambda: path.replace("../", "#parent."))

    # Step 2a-ii: smartsplit
    bench("    2a-ii.  smartsplit('pippo', '.')",
          lambda: smartsplit(path, "."))

    # Step 2a-iii: smartsplit internals - escape check
    escape = "\\."
    bench("    2a-iii. escape in path  (smartsplit guard)",
          lambda: escape in path)

    # Step 2a-iv: str.split + strip + list comprehension
    bench("    2a-iv.  [x.strip() for x in path.split('.')]",
          lambda: [x.strip() for x in path.split(".")])

    # Step 2a-v: just path.split
    bench("    2a-v.   path.split('.')  (raw)",
          lambda: path.split("."))

    # Step 2b: _traverse_inner (single segment, exits immediately)
    pathlist_example = ["pippo"]
    bench("2b. _traverse_inner(bag, ['pippo'], False, False)",
          lambda: bag._traverse_inner(bag, ["pippo"], False, False))

    # Step 2b-i: the while guard check
    bench("    2b-i.  len(['pippo']) > 1",
          lambda: len(pathlist_example) > 1)

    # Step 2c: smartcontinuation (with a tuple, not coroutine)
    sync_tuple = (bag, ["pippo"])
    identity = lambda x: x
    bench("2c. smartcontinuation(tuple, fn)",
          lambda: smartcontinuation(sync_tuple, identity))

    # Step 2c-i: inspect.isawaitable (the guard inside)
    bench("    2c-i.  inspect.isawaitable(tuple)",
          lambda: inspect.isawaitable(sync_tuple))

    # Step 2d: finalize closure inside _htraverse
    def htraverse_finalize(result):
        curr, pathlist = result
        if len(pathlist) > 1:
            return None, None
        return curr, pathlist[0]
    bench("2d. finalize (htraverse closure)",
          lambda: htraverse_finalize((bag, ["pippo"])))

    # Step 3: smartcontinuation #2 (in get_item)
    bench("3. smartcontinuation #2",
          lambda: smartcontinuation((bag, "pippo"), identity))

    # Step 4: finalize closure inside get_item → calls bag.get()
    bench("4. bag.get('pippo', static=False)  [single-level]",
          lambda: bag.get("pippo", static=False))

    # Step 4a: BagNodeContainer.get('pippo')
    bench("4a. _nodes.get('pippo')  [BagNodeContainer]",
          lambda: bag._nodes.get("pippo"))

    # Step 4a-i: just the dict lookup
    bench("    4a-i.  _nodes._dict.get('pippo')  [raw dict]",
          lambda: bag._nodes._dict.get("pippo"))

    # Step 4a-ii: str.startswith('#') check
    bench("    4a-ii. 'pippo'.startswith('#')",
          lambda: path.startswith("#"))

    # Step 4b: node.get_value()
    bench("4b. node.get_value(static=False)",
          lambda: node.get_value(static=False))

    # ---------------------------------------------------------------
    print("\n--- Allocation costs ---")
    # ---------------------------------------------------------------

    bench("closure allocation (def f(): pass inside fn)",
          lambda: (lambda: None))

    bench("list creation ['pippo']",
          lambda: ["pippo"])

    bench("tuple creation (bag, 'pippo')",
          lambda: (bag, "pippo"))

    # ---------------------------------------------------------------
    print("\n--- Dotted path: get_item('a.b.c') ---")
    # ---------------------------------------------------------------

    dpath = "a.b.c"

    bench("_htraverse('a.b.c', static=False)  [full]",
          lambda: bag._htraverse(dpath, static=False))

    bench("_htraverse_before('a.b.c')",
          lambda: bag._htraverse_before(dpath))

    bench("smartsplit('a.b.c', '.')",
          lambda: smartsplit(dpath, "."))

    bench("'a.b.c'.split('.')",
          lambda: dpath.split("."))

    # ---------------------------------------------------------------
    print("\n--- Potential fast path (what we'd save) ---")
    # ---------------------------------------------------------------

    def fast_get_item_plain_key():
        """What get_item would do with plain key pre-filter."""
        n = bag._nodes._dict.get("pippo")
        return n.get_value(static=False) if n else None

    bench("fast path: dict.get + get_value  (plain key)",
          fast_get_item_plain_key)

    bench("full path: bag.get_item('pippo')",
          lambda: bag.get_item("pippo"))

    # Summary
    print("\n" + "=" * 72)
    print("Key: lower ns/op = faster. Compare 'full path' vs 'fast path'.")
    print("=" * 72)


if __name__ == "__main__":
    main()
