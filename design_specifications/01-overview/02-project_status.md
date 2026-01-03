# Project Status

**Last Updated**: 2026-01-03
**Status**: In Development

---

## Implementation Status

### Completed Components

| Component | File | Lines | Tests | Coverage | Notes |
|-----------|------|-------|-------|----------|-------|
| **NodeContainer** | `src/genro_bag/node_container.py` | ~430 | 63 | 80% | Ordered dict-like container for BagNodes |
| **BagNode** | `src/genro_bag/bag_node.py` | ~555 | 63 | 72% | Node with value, attributes, subscriptions |
| **BagResolver** | `src/genro_bag/resolver.py` | ~340 | 0 | 0% | Lazy loading with cache TTL, async support |

### Pending Components

| Component | File | Status | Notes |
|-----------|------|--------|-------|
| **Bag** | `src/genro_bag/bag.py` | Stub only | Needs `_htraverse`, `get_item`, `set_item`, subscriptions |
| **Resolver Tests** | `tests/test_resolver.py` | Not started | Excluded from current session |
| **Integration Tests** | - | Not started | BagNode + Bag + Resolver together |

---

## Test Summary

```
Total tests: 126
- test_node_container.py: 63 tests
- test_bag_node.py: 63 tests

Coverage: 63% overall
```

---

## Design Specifications

| Directory | Documents | Status |
|-----------|-----------|--------|
| `01-overview/` | Project startup, status | Current |
| `02-node_container/` | NodeContainer spec | Complete |
| `03-bag_node/` | BagNode spec, decisions, comparison | Complete |
| `04-bag/` | Bag spec | Needs review |
| `05-resolver/` | Resolver spec, async problem | **Open question** |

---

## Open Questions

### 1. Async/Sync Handling (DECISION PENDING)

**File**: `design_specifications/05-resolver/bag_async_problem.md`

The resolver supports async `load()` via `@smartasync`. The problem is how to handle async in path traversal:

**Scenario**: `bag['aaa.bbb.ccc']` where `bbb` has an async resolver

**Options discussed**:
- **Option A**: `_htraverse` with `@smartasync` - everything becomes async
- **Option B**: Two methods - `bag['path']` sync, `await bag.get_item('path')` async
- **Option C**: Resolver always returns coroutine, `@smartasync` handles it

**Decision**: NOT YET TAKEN

---

## Next Steps

### Priority 1: Complete Bag Implementation

1. Implement `Bag._htraverse()` for path navigation
2. Implement `Bag.get_item()` / `Bag.set_item()`
3. Implement `Bag.__getitem__` / `Bag.__setitem__` / `Bag.__delitem__`
4. Implement `Bag.backref` and parent-child relationships
5. Implement `Bag.subscribe()` for change notifications

### Priority 2: Resolver Integration

1. Write resolver tests (excluded from this session)
2. Test BagNode + Resolver integration
3. Decide async/sync strategy

### Priority 3: Full Integration

1. Test Bag + BagNode + Resolver together
2. Navigation tests with parent hierarchy
3. Serialization (XML, JSON)

---

## Key Design Decisions Made

| # | Decision | Status |
|---|----------|--------|
| 1 | Remove `locked` from BagNode | Approved |
| 2 | Remove `validators` from BagNode | Approved |
| 3 | Add `tag` attribute to BagNode | Approved |
| 4 | Add `_invalid_reasons` for validation | Approved |
| 5 | Property for resolver (bidirectional link) | Approved |
| 6 | Remove `_attributes` fast path | Approved |
| 7 | `is_branch`/`is_leaf` properties | Postponed |
| 8 | Parent navigation property `_` | Approved |
| 9 | Use snake_case naming | Approved |
| 10 | Use `__slots__` | Approved |

---

## Git Status

**Branch**: main
**Last commits**:
- `036a887` - test: Add comprehensive BagNode tests (63 tests)
- `efee6d8` - docs: Improve docstrings for bag_node, node_container, and resolver
- `eb00032` - feat: Implement BagNode with full API and documentation

**Untracked files**:
- `design_specifications/05-resolver/bag_async_problem.md` (notes, not committed)

---

## How to Resume

1. Read this file for context
2. Check `bag_async_problem.md` if working on resolver/async
3. Check `04-bag/01-bag_spec.md` for Bag implementation details
4. Run `pytest` to verify all tests pass
5. Check coverage report in `htmlcov/index.html`
