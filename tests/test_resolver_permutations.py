# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Exhaustive permutation tests for resolver traversal.

Tests all combinations of:
- Nesting patterns: sync/async resolvers at various depths
- Operations: get_item, set_item, get_node
- Context: sync and async
- Parameters: static, read_only, cache_time
"""

import asyncio
from datetime import datetime

import pytest
from genro_toolbox import smartawait

from genro_bag import Bag
from genro_bag.bagnode import BagNodeException
from genro_bag.resolver import BagResolver

# =============================================================================
# RESOLVERS
# =============================================================================


class SyncResolver(BagResolver):
    """Sync resolver that returns a Bag or value."""

    class_args = ["content"]
    class_kwargs = {"cache_time": 0, "read_only": False}

    def load(self):
        return self._kw["content"]


class AsyncResolver(BagResolver):
    """Async resolver that returns a Bag or value."""

    class_args = ["content"]
    class_kwargs = {"cache_time": 0, "read_only": False}

    async def async_load(self):
        await asyncio.sleep(0.001)
        return self._kw["content"]


class TimestampSyncResolver(BagResolver):
    """Sync resolver with timestamp for cache testing."""

    class_kwargs = {"cache_time": 0, "read_only": False}

    def load(self):
        return {"type": "sync", "time": datetime.now().isoformat()}


class TimestampAsyncResolver(BagResolver):
    """Async resolver with timestamp for cache testing."""

    class_kwargs = {"cache_time": 0, "read_only": False}

    async def async_load(self):
        await asyncio.sleep(0.001)
        return {"type": "async", "time": datetime.now().isoformat()}


# =============================================================================
# NESTING PATTERNS
# =============================================================================

# Pattern notation:
# P = Placebo (plain Bag, no resolver)
# S = Sync resolver
# A = Async resolver
# . = nesting level separator

NESTING_PATTERNS = [
    # Single level
    "P",
    "S",
    "A",
    # Two levels
    "P.P",
    "P.S",
    "P.A",
    "S.P",
    "S.S",
    "S.A",
    "A.P",
    "A.S",
    "A.A",
    # Three levels - mixed patterns
    "S.A.S",
    "A.S.A",
    "S.S.A",
    "A.A.S",
    "S.A.A",
    "A.S.S",
    "P.S.A",
    "P.A.S",
    "S.P.A",
    "A.P.S",
]

OPERATIONS = ["get_item", "set_item", "get_node"]
STATICS = [True, False]
CACHE_CONFIGS = [
    # (cache_time, read_only, description)
    (0, False, "no_cache"),
    (0, True, "readonly"),
    (5, False, "cached"),  # cache_time > 0 forces read_only=False
]


# =============================================================================
# HELPERS
# =============================================================================


def pattern_has_resolver(pattern: str) -> bool:
    """Check if pattern contains any resolver (S or A)."""
    return "S" in pattern or "A" in pattern


def pattern_set_item_hits_resolver(pattern: str) -> bool:
    """Check if set_item will hit a resolver node (Issue #5).

    set_item uses write_mode=True which traverses statically, creating new Bags
    when needed. Issue #5 (BagNodeException) triggers when the FINAL node
    in the path has a resolver.

    The final node has a resolver when:
    - Pattern ends with S or A
    - AND all preceding levels are reachable statically (all P before the final)

    Examples:
    - "S" → final node is 'a' with resolver → ERROR
    - "A" → final node is 'a' with resolver → ERROR
    - "P.S" → 'a' is Bag, final 'b' has resolver → ERROR
    - "P.A" → 'a' is Bag, final 'b' has resolver → ERROR
    - "S.P" → 'a' has resolver, _htraverse creates new Bag → NO ERROR (writes to new structure)
    - "S.S" → 'a' has resolver, _htraverse creates new Bag → NO ERROR
    - "P.S.A" → 'a' is Bag, 'b' has resolver, _htraverse creates new Bag → NO ERROR
    """
    levels = pattern.split(".")
    last = levels[-1]

    # Final level must be a resolver
    if last not in ("S", "A"):
        return False

    # All preceding levels must be P (reachable statically)
    # If any preceding level is S or A, _htraverse creates new Bags
    for level in levels[:-1]:
        if level in ("S", "A"):
            return False

    return True


# =============================================================================
# BAG BUILDER
# =============================================================================


def build_nested_bag(pattern: str, cache_time: int = 0, read_only: bool = False) -> tuple:
    """Build a Bag with nested resolvers according to pattern.

    Pattern notation:
        P = Placebo (plain value at this level)
        S = Sync resolver at this level
        A = Async resolver at this level

    Examples:
        "P"     → bag["a"] = final_value
        "S"     → bag["a"] = SyncResolver(final_value)
        "P.P"   → bag["a"]["b"] = final_value
        "S.P"   → bag["a"] = SyncResolver(Bag["b"] = final_value)
        "P.S"   → bag["a"]["b"] = SyncResolver(final_value)
        "S.A.P" → bag["a"] = SyncResolver(Bag["b"] = AsyncResolver(Bag["c"] = final_value))

    Args:
        pattern: Nesting pattern like "S.A.P"
        cache_time: Cache time for resolvers
        read_only: Read-only flag for resolvers

    Returns:
        tuple: (bag, path, expected_value)
    """
    levels = pattern.split(".")
    depth = len(levels)

    # Path uses letters: a, b, c, d...
    path_parts = [chr(ord("a") + i) for i in range(depth)]
    full_path = ".".join(path_parts)

    # Final value at the deepest level
    final_value = {"pattern": pattern, "depth": depth}

    # Build from innermost (last level) to outermost (first level)
    # current starts as the final value, then we wrap it according to pattern
    current = final_value

    for i in range(depth - 1, -1, -1):
        level_type = levels[i]

        # Wrap current in resolver if needed
        if level_type == "S":
            current = SyncResolver(current, cache_time=cache_time, read_only=read_only)
        elif level_type == "A":
            current = AsyncResolver(current, cache_time=cache_time, read_only=read_only)
        # P = Placebo, no wrapping

        # If not the outermost level, wrap in a Bag with the key
        if i > 0:
            wrapper = Bag()
            wrapper[path_parts[i]] = current
            current = wrapper

    # Create root bag with first key
    root = Bag()
    root[path_parts[0]] = current

    return root, full_path, final_value


# =============================================================================
# TEST EXECUTION
# =============================================================================


def execute_operation_sync(bag: Bag, path: str, operation: str, static: bool):
    """Execute operation in sync context.

    Note: set_item always uses static=True internally (write_mode=True in _htraverse).
    The static parameter is ignored for set_item.
    """
    if operation == "get_item":
        return bag.get_item(path, static=static)
    elif operation == "set_item":
        new_value = {"set": True, "path": path}
        try:
            # set_item ignores static param - always uses write_mode=True
            bag.set_item(path, new_value)
            return bag.get_item(path, static=True)  # Read back with static=True
        except BagNodeException:
            # Issue #5: set_item on node with resolver raises
            return "RESOLVER_ERROR"
    elif operation == "get_node":
        node = bag.get_node(path, static=static)
        if node is None:
            return None
        # Use get_value to properly handle resolvers
        return node.get_value(static=static)
    raise ValueError(f"Unknown operation: {operation}")


async def execute_operation_async(bag: Bag, path: str, operation: str, static: bool):
    """Execute operation in async context.

    Note: set_item always uses static=True internally (write_mode=True in _htraverse).
    """
    if operation == "get_item":
        return await smartawait(bag.get_item(path, static=static))
    elif operation == "set_item":
        new_value = {"set": True, "path": path}
        try:
            await smartawait(bag.set_item(path, new_value))
            return await smartawait(bag.get_item(path, static=True))
        except BagNodeException:
            return "RESOLVER_ERROR"
    elif operation == "get_node":
        node = await smartawait(bag.get_node(path, static=static))
        if node is None:
            return None
        # Use get_value to properly handle resolvers
        return await smartawait(node.get_value(static=static))
    raise ValueError(f"Unknown operation: {operation}")


# =============================================================================
# ITERATORS
# =============================================================================


def sync_permutation_iterator():
    """Yield all sync test permutations."""
    for pattern in NESTING_PATTERNS:
        for operation in OPERATIONS:
            for static in STATICS:
                for cache_time, read_only, cache_desc in CACHE_CONFIGS:
                    yield pattern, operation, static, cache_time, read_only, cache_desc


def async_permutation_iterator():
    """Yield all async test permutations."""
    for pattern in NESTING_PATTERNS:
        for operation in OPERATIONS:
            for static in STATICS:
                for cache_time, read_only, cache_desc in CACHE_CONFIGS:
                    yield pattern, operation, static, cache_time, read_only, cache_desc


# =============================================================================
# PYTEST TESTS
# =============================================================================


class TestResolverPermutationsSync:
    """Test all resolver permutations in sync context."""

    @pytest.mark.parametrize(
        "pattern,operation,static,cache_time,read_only,cache_desc",
        [
            pytest.param(*args, id=f"{args[0]}-{args[1]}-static={args[2]}-{args[5]}")
            for args in sync_permutation_iterator()
        ],
    )
    def test_sync_permutation(
        self, pattern, operation, static, cache_time, read_only, cache_desc
    ):
        """Test a single permutation in sync context."""
        bag, path, expected = build_nested_bag(pattern, cache_time, read_only)
        has_resolver = pattern_has_resolver(pattern)
        set_item_hits_resolver = pattern_set_item_hits_resolver(pattern)

        result = execute_operation_sync(bag, path, operation, static)

        if operation == "set_item":
            # set_item always uses static=True internally (write_mode)
            # Issue #5: triggers when final node has resolver AND path is statically reachable
            if set_item_hits_resolver:
                assert result == "RESOLVER_ERROR", (
                    f"Expected RESOLVER_ERROR for set_item hitting resolver node, got {result}"
                )
            else:
                # Path doesn't hit resolver node: set_item creates/updates structure
                assert result == {"set": True, "path": path}
        elif static and has_resolver:
            # static=True with resolvers in path: cannot reach value without triggering
            # Result should be None (path unreachable statically)
            assert result is None, f"Expected None for static access through resolver, got {result}"
        else:
            assert isinstance(result, dict), f"Expected dict, got {type(result).__name__}: {result}"
            if operation == "get_item" and not static:
                assert result.get("pattern") == pattern


class TestResolverPermutationsAsync:
    """Test all resolver permutations in async context."""

    @pytest.mark.parametrize(
        "pattern,operation,static,cache_time,read_only,cache_desc",
        [
            pytest.param(*args, id=f"{args[0]}-{args[1]}-static={args[2]}-{args[5]}")
            for args in async_permutation_iterator()
        ],
    )
    @pytest.mark.asyncio
    async def test_async_permutation(
        self, pattern, operation, static, cache_time, read_only, cache_desc
    ):
        """Test a single permutation in async context."""
        bag, path, expected = build_nested_bag(pattern, cache_time, read_only)

        result = await execute_operation_async(bag, path, operation, static)

        if operation == "set_item":
            # set_item uses write_mode=True internally (always static)
            # Issue #5: raises error when final node has resolver and path is reachable
            if pattern_set_item_hits_resolver(pattern):
                assert result == "RESOLVER_ERROR", (
                    f"set_item on pattern '{pattern}' should raise BagNodeException "
                    f"(Issue #5: final node has resolver and path is statically reachable)"
                )
            else:
                # Traversal creates new Bags, so we can set the value
                assert result == {"set": True, "path": path}
        else:
            # For get_item/get_node, behavior depends on static parameter
            # static=True: returns cached _value (may be None if resolver not triggered)
            # static=False: triggers resolver if needed
            if static:
                # static=True never triggers resolver, may return None
                if result is not None:
                    assert isinstance(result, dict)
            else:
                # static=False should trigger resolver and return data
                assert isinstance(result, dict)
                if operation == "get_item":
                    assert result.get("pattern") == pattern


class TestCacheBehavior:
    """Test cache behavior with second access."""

    @pytest.mark.parametrize("pattern", ["S", "A", "S.A", "A.S"])
    @pytest.mark.parametrize("cache_time", [0, 5])
    def test_cache_sync(self, pattern, cache_time):
        """Test caching in sync context."""
        # Use timestamp resolvers for cache testing
        bag = Bag()
        if pattern.startswith("S"):
            bag["test"] = TimestampSyncResolver(cache_time=cache_time)
        else:
            bag["test"] = TimestampAsyncResolver(cache_time=cache_time)

        result1 = bag.get_item("test", static=False)
        result2 = bag.get_item("test", static=False)

        if cache_time > 0:
            # Should be same (cached)
            assert result1["time"] == result2["time"]
        else:
            # Should be different (not cached) - but may be same if fast
            # Just verify both are valid
            assert "time" in result1
            assert "time" in result2

    @pytest.mark.parametrize("pattern", ["S", "A", "S.A", "A.S"])
    @pytest.mark.parametrize("cache_time", [0, 5])
    @pytest.mark.asyncio
    async def test_cache_async(self, pattern, cache_time):
        """Test caching in async context."""
        bag = Bag()
        if pattern.startswith("S"):
            bag["test"] = TimestampSyncResolver(cache_time=cache_time)
        else:
            bag["test"] = TimestampAsyncResolver(cache_time=cache_time)

        result1 = await smartawait(bag.get_item("test", static=False))
        result2 = await smartawait(bag.get_item("test", static=False))

        if cache_time > 0:
            # Should be same (cached)
            assert result1["time"] == result2["time"]
        else:
            # Just verify both are valid
            assert "time" in result1
            assert "time" in result2


class TestAsyncResolverReturnsNonBag:
    """Test traversal when async resolver returns non-Bag value with remaining path."""

    @pytest.mark.asyncio
    async def test_async_resolver_returns_string_with_remaining_path(self):
        """Async resolver returns string, further traversal returns None.

        Covers bag.py line 600: when async resolver returns non-Bag and
        there's still path to traverse, _get_new_curr returns None.
        """
        bag = Bag()
        # AsyncResolver returns "hello" (string, not Bag)
        bag["a"] = AsyncResolver("hello")

        # Try to traverse further into "a.b" - can't traverse into a string
        result = await smartawait(bag.get_item("a.b", static=False))
        assert result is None

    @pytest.mark.asyncio
    async def test_async_resolver_returns_number_with_remaining_path(self):
        """Async resolver returns number, further traversal returns None."""
        bag = Bag()
        bag["x"] = AsyncResolver(42)

        result = await smartawait(bag.get_item("x.y.z", static=False))
        assert result is None

    @pytest.mark.asyncio
    async def test_async_resolver_returns_list_with_remaining_path(self):
        """Async resolver returns list, further traversal returns None."""
        bag = Bag()
        bag["data"] = AsyncResolver([1, 2, 3])

        result = await smartawait(bag.get_item("data.first", static=False))
        assert result is None


# =============================================================================
# STANDALONE RUNNER
# =============================================================================


def run_sync_tests():
    """Run all sync tests and collect results."""
    results = {}
    for pattern, operation, static, cache_time, read_only, cache_desc in sync_permutation_iterator():
        key = (pattern, operation, static, cache_desc)
        try:
            bag, path, expected = build_nested_bag(pattern, cache_time, read_only)
            result = execute_operation_sync(bag, path, operation, static)
            if operation == "set_item":
                ok = result == {"set": True, "path": path}
            else:
                ok = isinstance(result, dict)
            results[key] = "✓" if ok else f"✗ {type(result).__name__}"
        except Exception as e:
            results[key] = f"✗ {e}"
    return results


async def run_async_tests():
    """Run all async tests and collect results."""
    results = {}
    for pattern, operation, static, cache_time, read_only, cache_desc in async_permutation_iterator():
        key = (pattern, operation, static, cache_desc)
        try:
            bag, path, expected = build_nested_bag(pattern, cache_time, read_only)
            result = await execute_operation_async(bag, path, operation, static)
            if operation == "set_item":
                ok = result == {"set": True, "path": path}
            else:
                ok = isinstance(result, dict)
            results[key] = "✓" if ok else f"✗ {type(result).__name__}"
        except Exception as e:
            results[key] = f"✗ {e}"
    return results


def print_results_table(results: dict, title: str):
    """Print results as a formatted table."""
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)
    print()

    # Group by pattern
    patterns = sorted({k[0] for k in results})
    operations = OPERATIONS
    cache_descs = [c[2] for c in CACHE_CONFIGS]

    header = f"{'pattern':<12} | {'operation':<10} | {'static':<6}"
    for cache_desc in cache_descs:
        header += f" | {cache_desc:<10}"
    print(header)
    print("-" * 100)

    for pattern in patterns:
        for operation in operations:
            for static in STATICS:
                static_str = "T" if static else "F"
                row = f"{pattern:<12} | {operation:<10} | {static_str:<6}"
                for cache_desc in cache_descs:
                    key = (pattern, operation, static, cache_desc)
                    result = results.get(key, "?")
                    row += f" | {result:<10}"
                print(row)
        print("-" * 100)


if __name__ == "__main__":
    print("\nRunning resolver permutation tests...\n")

    # Count total permutations
    total_sync = len(list(sync_permutation_iterator()))
    total_async = len(list(async_permutation_iterator()))
    print(f"Total sync permutations: {total_sync}")
    print(f"Total async permutations: {total_async}")
    print(f"Total: {total_sync + total_async}")

    # Run sync tests
    sync_results = run_sync_tests()
    print_results_table(sync_results, "SYNC CONTEXT")

    # Run async tests
    async_results = asyncio.run(run_async_tests())
    print_results_table(async_results, "ASYNC CONTEXT")

    # Summary
    sync_failures = sum(1 for v in sync_results.values() if not v.startswith("✓"))
    async_failures = sum(1 for v in async_results.values() if not v.startswith("✓"))

    print()
    print("=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print(f"Sync:  {total_sync - sync_failures}/{total_sync} passed")
    print(f"Async: {total_async - async_failures}/{total_async} passed")
    print(f"Total: {total_sync + total_async - sync_failures - async_failures}/{total_sync + total_async} passed")
