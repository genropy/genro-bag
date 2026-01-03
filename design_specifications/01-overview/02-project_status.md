# Project Status

**Last Updated**: 2026-01-03
**Status**: In Development

---

## Implementation Status

### Completed Components

| Component | File | Lines | Tests | Coverage | Notes |
|-----------|------|-------|-------|----------|-------|
| **NodeContainer** | `src/genro_bag/node_container.py` | ~300 | TBD | TBD | Indexed list for BagNodes (refactored) |
| **BagNode** | `src/genro_bag/bag_node.py` | ~555 | 63 | 72% | Node with value, attributes, subscriptions |
| **BagResolver** | `src/genro_bag/resolver.py` | ~340 | 0 | 0% | Lazy loading with cache TTL, async support |
| **Bag (Core)** | `src/genro_bag/bag.py` | ~936 | 0 | 0% | Core methods implemented, tests pending |

### NodeContainer Refactoring (2026-01-03)

NodeContainer è stato semplificato come "indexed list":

- Rimossi metodi dict-like non usati: `get()`, `keys()`, `values()`, `items()`, `update()`
- `__iter__` ora ritorna nodi (non label)
- `__contains__` solo per label (non indici)
- `__delitem__` supporta cancellazione multipla con virgola
- Rinominato `_parse_what` → `_get_nodes`
- Usato `smartsplit` per parsing consistente

### Bag Implementation Details

| Method | Status | Notes |
|--------|--------|-------|
| `__init__` | ✅ Done | Uses NodeContainer for _nodes |
| `fill_from` | ⏳ Stub | TODO: implement |
| `parent` / `parent_node` / `backref` | ✅ Done | Properties |
| `_htraverse` | ✅ Done | Core path navigation with `smartsplit` |
| `get` | ✅ Done | Single level access with `mode` and `?attr` syntax |
| `get_item` / `__getitem__` | ✅ Done | Hierarchical path access with `mode` |
| `_set` | ✅ Done | Single level set with resolver support |
| `_insert_node` | ✅ Done | Position-based node insertion |
| `set_item` / `__setitem__` | ✅ Done | With autocreate, `**kwargs` as attributes |
| `_pop` | ✅ Done | Single level pop with `_reason` |
| `pop` / `del_item` / `__delitem__` | ✅ Done | Remove and return value with `_reason` |
| `pop_node` | ✅ Done | Remove and return node with `_reason` |
| `clear` | ✅ Done | Remove all nodes |
| `keys` / `values` / `items` | ✅ Done | Dict-like access |
| `__iter__` / `__len__` / `__contains__` | ✅ Done | Iteration and membership (str + BagNode) |
| `__call__` | ✅ Done | `bag()` returns keys, `bag(path)` returns value |
| `_get_node` | ✅ Done | Single level get with autocreate |
| `get_node` | ✅ Done | Get BagNode at path with `as_tuple`, `autocreate`, `default` |
| `_on_node_inserted` | ⏳ Stub | Event trigger |
| `_on_node_deleted` | ⏳ Stub | Event trigger |
| `subscribe` / `unsubscribe` | ❌ Not started | Event subscription system |
| `set_backref` / `clear_backref` | ❌ Not started | Backref mode management |

### Pending Components

| Component | File | Status | Notes |
|-----------|------|--------|-------|
| **Bag Tests** | `tests/test_bag.py` | Not started | Need tests for new methods |
| **Resolver Tests** | `tests/test_resolver.py` | Not started | Excluded from current session |
| **Integration Tests** | - | Not started | BagNode + Bag + Resolver together |

---

## External Dependencies

| Dependency | Location | Purpose |
|------------|----------|---------|
| `smartsplit` | `genro_toolbox.string_utils` | Path splitting with escaped separators |

---

## Reference Files

| File | Purpose |
|------|---------|
| `design_specifications/04-bag/original_bag.py` | Original Bag class from gnrbag.py (lines 436-2445) |
| `design_specifications/04-bag/original_bag_short.py` | Trimmed version: only methods to implement |
| `design_specifications/04-bag/original_bag_methods.md` | Python method list with priorities |
| `design_specifications/04-bag/js_bag_methods.md` | **JavaScript method list (gnrbag.js)** |

### JavaScript Reference (IMPORTANT)

The JavaScript implementation (`gnrbag.js`) must be kept in sync with Python.
The file `js_bag_methods.md` documents all JS methods for `GnrBagNode`, `GnrBag`, and `GnrBagResolver`.

**Key differences to harmonize**:

| Aspect | Python (current) | JavaScript | Decision |
|--------|------------------|------------|----------|
| Parent reference | `#parent` | `#parent` | ✅ Aligned |
| Path alias | `../` → `#parent.` | `../` → `#parent.` | ✅ Aligned |
| Query syntax | `?attr` implemented | `?attr`, `~path`, `#keys`, etc. | Partial |
| `fireItem` | Not present | Set + immediate null | TBD |
| `lazySet` | Not present | Skip if value unchanged | TBD |

**Goal**: Final Python implementation must support the same functionality as JavaScript to ensure client-server compatibility.

---

## Test Summary

```
Total tests: 126
- test_node_container.py: 63 tests
- test_bag_node.py: 63 tests
- test_bag.py: 0 tests (pending)

Coverage: 63% overall
```

---

## Design Specifications

| Directory | Documents | Status |
|-----------|-----------|--------|
| `01-overview/` | Project startup, status | Current |
| `02-node_container/` | NodeContainer spec | Complete |
| `03-bag_node/` | BagNode spec, decisions, comparison | Complete |
| `04-bag/` | Bag spec, original code reference | **In progress** |
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

### Priority 1: Complete Bag Core (CURRENT)

1. ✅ Implement `Bag._htraverse()` for path navigation
2. ✅ Implement `Bag.get_item()` / `Bag.set_item()`
3. ✅ Implement `Bag.__getitem__` / `Bag.__setitem__` / `Bag.__delitem__`
4. ✅ Implement `Bag._set()` / `Bag._pop()` / `Bag._get_node()` / `Bag._insert_node()`
5. ✅ Implement `Bag.get()` with `mode` and `?attr` syntax
6. ✅ Implement `Bag.get_node()` with `as_tuple`, `autocreate`, `default`
7. ⏳ Write tests for Bag methods
8. ⏳ Implement `Bag.set_backref` / `Bag.clear_backref`
9. ⏳ Implement `Bag.subscribe()` for change notifications

### Priority 2: Resolver Integration

1. Write resolver tests (excluded from this session)
2. Test BagNode + Resolver integration
3. Decide async/sync strategy

### Priority 3: Full Integration

1. Test Bag + BagNode + Resolver together
2. Navigation tests with parent hierarchy
3. Serialization (XML, JSON) - deferred

---

## Key Design Decisions Made

| # | Decision | Status |
|---|----------|--------|
| 1 | Remove `locked` from BagNode | Approved |
| 2 | Remove `validators` from BagNode and Bag | Approved |
| 3 | Add `tag` attribute to BagNode | Approved |
| 4 | Add `_invalid_reasons` for validation | Approved |
| 5 | Property for resolver (bidirectional link) | Approved |
| 6 | Remove `_attributes` fast path | Approved |
| 7 | `is_branch`/`is_leaf` properties | Postponed |
| 8 | Parent navigation property `_` | Approved |
| 9 | Use snake_case naming | Approved |
| 10 | Use `__slots__` | Approved |
| 11 | No duplicate labels in Bag | Approved |
| 12 | Serialization methods removed from first implementation | Approved |
| 13 | Use `#parent` instead of `#^` for parent reference | Approved |
| 14 | `smartsplit` moved to `genro_toolbox.string_utils` | Approved |

---

## Differences from Original (intentional)

| Aspect | Original | New | Reason |
|--------|----------|-----|--------|
| `index('#-1')` | Accepts (bug) | Rejects | Fix: negative index in `#n` syntax invalid |
| `_validators` | Present | Removed | Design decision: validation handled differently |
| Parent reference | `#^` | `#parent` | JS compatibility, readability |
| Storage | `list` | `NodeContainer` | No duplicate labels, ordered dict semantics |
| `_index` in Bag | Present | Removed | Moved to `NodeContainer.index()` |
| `_get_label`, `_resolve_key`, `_resolve_index` | Present | Removed | Consolidated into `NodeContainer.index()` |

---

## Git Status

**Branch**: main
**Last commits**:

- `abcd9b5` - refactor: Simplify NodeContainer index methods
- `07a7402` - docs: Add project status document for session continuity
- `036a887` - test: Add comprehensive BagNode tests (63 tests)
- `efee6d8` - docs: Improve docstrings for bag_node, node_container, and resolver
- `eb00032` - feat: Implement BagNode with full API and documentation

**Untracked files**:

- `design_specifications/05-resolver/bag_async_problem.md` (notes, not committed)
- `design_specifications/04-bag/` (reference files)

---

## How to Resume

1. Read this file for context
2. Check `bag_async_problem.md` if working on resolver/async
3. Check `04-bag/original_bag_short.py` for reference implementation
4. Run `pytest` to verify all tests pass
5. Check coverage report in `htmlcov/index.html`
