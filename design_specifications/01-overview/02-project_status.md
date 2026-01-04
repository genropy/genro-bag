# Project Status

**Last Updated**: 2026-01-04
**Status**: In Development

---

## Implementation Status

### Completed Components

| Component | File | Stmts | Tests | Coverage | Notes |
|-----------|------|-------|-------|----------|-------|
| **BagNodeContainer** | `src/genro_bag/bagnode_container.py` | 111 | - | 79% | Container ordinato con `keys()`, `values()`, `items()` |
| **BagNode** | `src/genro_bag/bag_node.py` | 209 | - | 38% | Node con resolver, backref, subscribers (parziale) |
| **BagResolver** | `src/genro_bag/resolver.py` | 97 | 0 | 0% | Lazy loading con cache TTL, async support |
| **Bag (Core)** | `src/genro_bag/bag.py` | 255 | 50 | 60% | Core methods, `__str__` aggiunto |

### Async/Sync Refactoring (2026-01-03)

Risolto il problema async/sync per `_htraverse`:

**Architettura implementata:**

- `_htraverse_before(path)` - parsing path, gestione `#parent`
- `_htraverse_after(curr, pathlist, write_mode)` - finalizzazione, autocreate in write mode
- `_traverse_until(curr, pathlist)` - loop sync (sempre `static=True`)
- `_async_traverse_until(curr, pathlist, static)` - loop async con `@smartasync`
- `_htraverse(path, write_mode)` - metodo principale sync
- `_async_htraverse(path, write_mode, static)` - metodo principale async

**Decisioni:**

- Setter (`set_item`, `pop`, `pop_node`) sono sempre sync → usano `_htraverse`
- Getter (`get_item`, `get_node`) supportano async → usano `_async_htraverse` con `@smartasync`
- `__getitem__` usa `_htraverse` sync (no resolver trigger)
- Parametro `static`: quando `True`, non triggera i resolver durante il traversal
- Rimosso `SmartLock` dal resolver (l'utente userà contextvars per isolamento)
- Rimosso parametro `mode` da `get` e `get_item` (mai usato nel codebase)

### NodeContainer → BagNodeContainer Refactoring (2026-01-03)

NodeContainer è stato semplificato come "indexed list", poi esteso:

- `__iter__` ritorna nodi (non label)
- `__contains__` solo per label (non indici)
- `__delitem__` supporta cancellazione multipla con virgola
- Usato `smartsplit` per parsing consistente
- Aggiunti `keys()`, `values()`, `items()` che operano sui nodi
- `get()` supporta label, indice numerico e sintassi `#n`

### BagNodeContainer + set_item Refactoring (2026-01-03) - COMPLETATO

**Obiettivo**: Semplificare `Bag.set_item()` eliminando duplicazione di logica.

**Modifiche completate**:
1. ✅ Rinominato `node_container.py` → `bagnode_container.py`
2. ✅ Rinominato classe `NodeContainer` → `BagNodeContainer`
3. ✅ `BagNodeContainer.set()` ora crea `BagNode` internamente (non riceve nodo pronto)
4. ✅ `Bag.set_item()` semplificato: chiama direttamente `obj._nodes.set(...)`
5. ✅ Rimossi `Bag._set()` e `Bag._insert_node()` (logica spostata in `BagNodeContainer.set()`)
6. ✅ Aggiunto parametro `_remove_null_attributes` a `BagNode.__init__`, `set_attr`, `set_value`
7. ✅ `Bag.keys()`, `values()`, `items()` sono wrapper su `_nodes.*`
8. ✅ 50 test passano

**Test coverage attuale** (2026-01-03):

- `bag.py`: 60% (255 stmts, 86 missing) - aggiunto `__str__`
- `bagnode_container.py`: 79% (111 stmts, 20 missing)
- `bag_node.py`: 38% (209 stmts, 111 missing)
- `resolver.py`: 0% (97 stmts, 97 missing)
- **TOTAL**: 49%

### Bag Implementation Details

| Method | Status | Notes |
|--------|--------|-------|
| `__init__` | ✅ Done | Uses BagNodeContainer for _nodes |
| `fill_from` | ⏳ Stub | TODO: implement |
| `parent` / `parent_node` / `backref` | ✅ Done | Properties |
| `_htraverse_before` | ✅ Done | Parse path, handle `#parent` navigation |
| `_htraverse_after` | ✅ Done | Finalize traversal, autocreate in write mode |
| `_traverse_until` | ✅ Done | Sync loop (always `static=True`) |
| `_async_traverse_until` | ✅ Done | Async loop with `@smartasync` |
| `_htraverse` | ✅ Done | Sync version, never triggers resolvers |
| `_async_htraverse` | ✅ Done | Async version with `static` parameter |
| `get` | ✅ Done | Single level access with `?attr` and `#n` syntax |
| `get_item` | ✅ Done | Async with `@smartasync`, `static` parameter |
| `__getitem__` | ✅ Done | Sync, uses `_htraverse` |
| `set_item` | ✅ Done | Semplificato: chiama `_nodes.set()` direttamente |
| `__setitem__` | ✅ Done | Alias for `set_item` |
| `_pop` | ✅ Done | Single level pop with `_reason` |
| `pop` | ✅ Done | Sync, remove and return value |
| `del_item` | ✅ Done | Alias for `pop` |
| `__delitem__` | ✅ Done | Alias for `pop` |
| `pop_node` | ✅ Done | Sync, remove and return node |
| `clear` | ✅ Done | Remove all nodes |
| `keys` | ✅ Done | Wrapper su `_nodes.keys()` |
| `values` | ✅ Done | Wrapper su `_nodes.values()` |
| `items` | ✅ Done | Wrapper su `_nodes.items()` |
| `__str__` | ✅ Done | Formatted output, handles circular refs |
| `__iter__` | ✅ Done | Yields BagNodes |
| `__len__` | ✅ Done | Number of direct children |
| `__call__` | ✅ Done | `bag()` returns keys, `bag(path)` returns value |
| `__contains__` | ✅ Done | Check path or BagNode existence |
| `_get_node` | ✅ Done | Single level get with autocreate |
| `get_node` | ✅ Done | Async with `@smartasync`, `static`, `as_tuple` |
| `set_backref` | ✅ Done | Enable backref mode |
| `del_parent_ref` | ✅ Done | Remove parent reference |
| `clear_backref` | ✅ Done | Clear backref recursively |
| `_on_node_changed` | ✅ Done | Trigger for update events |
| `_on_node_inserted` | ✅ Done | Trigger for insert events |
| `_on_node_deleted` | ✅ Done | Trigger for delete events |
| `_subscribe` | ✅ Done | Internal subscribe helper |
| `subscribe` | ✅ Done | Subscribe to events |
| `unsubscribe` | ✅ Done | Unsubscribe from events |
| `get_nodes` | ✅ Done | Return nodes list with optional filter |
| `nodes` | ✅ Done | Property alias for get_nodes() |
| `digest` | ✅ Done | Extract keys/values/attributes (#k, #v, #a, #__v, #v.path) |
| `columns` | ✅ Done | Shortcut for digest with as_columns=True |

**Metodi rimossi (logica spostata in BagNodeContainer):**
- `_set` → `BagNodeContainer.set()`
- `_insert_node` → `BagNodeContainer.set()`

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
| `smartasync` | `genro_toolbox` | Sync/async dual-mode decorator |
| `smartawait` | `genro_toolbox` | Await coroutines or return values |

---

## Reference Files

| File | Purpose |
|------|---------|
| `design_specifications/04-bag/original_bag.py` | Original Bag class from gnrbag.py (lines 436-2445) |
| `design_specifications/04-bag/original_bag_short.py` | Trimmed version: only methods to implement |
| `design_specifications/04-bag/original_bag_methods.md` | Python method list with priorities |
| `design_specifications/04-bag/js_bag_methods.md` | **JavaScript method list (gnrbag.js)** |
| `design_specifications/04-bag/htraverse.md` | Comparison: Bag vs TreeStore _htraverse |

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
Total tests: 92
- test_bag.py: 92 tests (set_item, get_item, position, iteration, call, index by attr, backref, subscribe, get_nodes, digest, columns, walk)

Coverage: 52% overall
```

---

## Design Specifications

| Directory | Documents | Status |
|-----------|-----------|--------|
| `01-overview/` | Project startup, status, compatibility layer | Current |
| `02-node_container/` | NodeContainer spec | Complete |
| `03-bag_node/` | BagNode spec, decisions, comparison | Complete |
| `04-bag/` | Bag spec, original code reference, htraverse comparison | **In progress** |
| `05-resolver/` | Resolver spec, async problem | **Resolved** |
| `06-builder/` | Builder system (da TreeStore), gnrstructures.py reference | **New** |
| `07-serialization/` | TYTX serialization, walk/flattened | **New** |

---

## Open Questions

### 1. Async/Sync Handling (RESOLVED)

**File**: `design_specifications/05-resolver/bag_async_problem.md`

**Decision taken**: Split approach

- `_htraverse` (sync) per setter - mai triggera resolver
- `_async_htraverse` (async) per getter - può triggerare resolver
- `@smartasync` permette di chiamare metodi async da contesto sync
- Parametro `static` per controllare trigger dei resolver

---

## Next Steps

### Priority 1: Complete Bag Core (CURRENT)

1. ✅ Implement `Bag._htraverse()` for path navigation
2. ✅ Implement `Bag.get_item()` / `Bag.set_item()`
3. ✅ Implement `Bag.__getitem__` / `Bag.__setitem__` / `Bag.__delitem__`
4. ✅ Implement `Bag._set()` / `Bag._pop()` / `Bag._get_node()` / `Bag._insert_node()`
5. ✅ Implement `Bag.get()` with `?attr` syntax
6. ✅ Implement `Bag.get_node()` with `as_tuple`, `autocreate`, `default`, `static`
7. ✅ Refactor _htraverse for sync/async separation
8. ⏳ Write tests for Bag methods
9. ⏳ Implement `Bag.set_backref` / `Bag.clear_backref`
10. ⏳ Implement `Bag.subscribe()` for change notifications

### Priority 2: Resolver Integration

1. Write resolver tests (excluded from this session)
2. Test BagNode + Resolver integration
3. ✅ Async/sync strategy decided and implemented

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
| 15 | Split _htraverse: sync for setters, async for getters | Approved |
| 16 | Remove `mode` parameter from get/get_item | Approved |
| 17 | Remove SmartLock from resolver (use contextvars) | Approved |

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
| `_htraverse` | Single method | Split sync/async | Proper async resolver support |
| `mode` parameter | Present | Removed | Never used in codebase |
| `set_item('', value)` | Merge/update syntax | Removed | Use explicit `update()` method instead |

---

## Adaptation Layer Notes

Sintassi da gestire nel layer di adattamento per retrocompatibilità:

| Sintassi Legacy | Nuova API | Note |
|-----------------|-----------|------|
| `bag.set_item('', other_bag)` | `bag.update(other_bag)` | Merge contenuto di altra Bag |
| `bag.set_item(True, dict)` | `bag.update(dict)` | Merge contenuto di dict |
| `bag[''] = value` | `bag.update(value)` | Equivalente via `__setitem__` |
| `bag.addItem(path, value)` | `bag.set_item(path, value)` | No duplicate labels, sovrascrive |
| `_duplicate=True` | Non supportato | Label duplicate non ammesse |

---

## Git Status

**Branch**: main
**Last commits**:

- `a8c086d` - feat: Add get_nodes, digest and columns methods
- `3cbe865` - refactor: Simplify set_item with BagNodeContainer creating nodes internally
- `ece5957` - docs: Update project status with async/sync refactoring details
- `f07f77d` - refactor: Split _htraverse into sync/async with static parameter
- `ce7732e` - test: Remove obsolete NodeContainer tests for removed methods

---

## How to Resume

1. Read this file for context
2. Check `04-bag/htraverse.md` for sync/async traversal details
3. Check `04-bag/original_bag_short.py` for reference implementation
4. Run `pytest` to verify all tests pass
5. Check coverage report in `htmlcov/index.html`

---

## Processo di Implementazione Metodi Mancanti

Per ogni metodo ancora da implementare (vedi `04-bag/original_bag_methods.md`):

1. **Mostrare il codice originale** dal file `original_bag.py`
2. **Chiedere all'utente** se il metodo va implementato
3. **Se NO**: aggiungere al layer di compatibilità in `03-compatibility_layer.md` con nota "non portato"
4. **Se SI**: mostrare la proposta di implementazione (originale vs nuovo) e procedere dopo approvazione

### Metodi Implementati (2026-01-04)

| Metodo | Status |
|--------|--------|
| `root_attributes` | ✅ Implementato |
| `modified` | ✅ Implementato |
| `setdefault` | ✅ Implementato (fix bug: ritorna sempre il valore) |
| `keys(iter=)` | ✅ Aggiunto parametro `iter` |
| `values(iter=)` | ✅ Aggiunto parametro `iter` |
| `items(iter=)` | ✅ Aggiunto parametro `iter` |
| `get_node_by_attr` | ✅ Implementato (ricerca ricorsiva per attributo) |
| `get_node_by_value` | ✅ Implementato (ricerca per valore, JS compat) |
| `set_attr` | ✅ Implementato (wrapper su BagNode.set_attr) |
| `get_attr` | ✅ Implementato (wrapper su BagNode.get_attr) |
| `del_attr` | ✅ Implementato (wrapper su BagNode.del_attr) |
| `get_inherited_attributes` | ✅ Implementato |
| `sort` | ✅ Implementato (nuovi modes a/A/d/D per case sensitivity) |
| `sum` | ✅ Implementato (aggiunto parametro condition) |
| `__eq__` | ✅ Implementato (Bag, BagNode, BagNodeContainer) |
| `__ne__` | ✅ Implementato |
| `deepcopy` | ✅ Implementato (copia profonda ricorsiva) |
| `update` | ✅ Implementato (merge con `ignore_none` parameter) |
| `static_value` | ✅ Fix bug (era stringa invece di bool) |
| `walk` | ✅ Implementato (dual mode: generator + legacy callback) |

### Metodi Non Portati

| Metodo | Motivo |
|--------|--------|
| `iterkeys()` | Python 2, usa `keys(iter=True)` |
| `itervalues()` | Python 2, usa `values(iter=True)` |
| `iteritems()` | Python 2, usa `items(iter=True)` |
| `has_key()` | Python 2, usa `path in bag` |
| `node` (property) | Deprecato, usa `parent_node` |
| `addItem()` | Label duplicate non ammesse, usa `set_item()` |
| `appendNode()` | Label duplicate non ammesse, usa `set_item()` |
| `getDeepestNode()` | Non usato, funzionalità in `_traverse_until()` |
| `merge()` | Deprecato in originale, usa `update()` |
| `diff()` | Problemi design (ritorno misto), da rivalutare |
| `copy()` | Deprecato, usava shallow copy (bug). Usa `deepcopy()` |
| `filter()` | Nessun uso nel codebase. Usa `get_nodes(condition)` |
| `traverse()` | Nel compatibility layer, wrapper su `walk()` che yielda solo node |
| `getIndex()` | Nel compatibility layer, wrapper su `walk()` - ritorna `[(pathlist, node)]` |
| `getIndexList()` | Nel compatibility layer, wrapper su `walk()` - ritorna lista path |
| `getLeaves()` | Nel compatibility layer, wrapper su `walk()` - solo foglie `[(path, value)]` |
| `isEmpty()` | Non usato nel codebase. Usa `len(bag) == 0` o `not bag` |

### Metodi da Valutare (prossima sessione)

**Serialization** → **Vedi 07-serialization/**:
- `to_tytx` / `from_tytx` - formato primario TYTX (type-preserving)
- `flattened` - generatore per serializzazione
- `to_xml` / `from_xml` - nel compatibility layer
- `to_json` / `from_json` - nel compatibility layer
- `as_dict` / `as_dict_deeply` - nel compatibility layer

**Builder System** → **Vedi 06-builder/**:
- `_builder` - slot per builder instance
- `builder` - property
- `__getattr__` - delegazione al builder
- Ereditarietà builder da parent a child

**Resolver**:
- `get_resolver` / `set_resolver`

---

## Reference Documentation

| Document | Location | Description |
|----------|----------|-------------|
| Builder Overview | `06-builder/01-overview.md` | Pattern builder, gnrstructures.py, ereditarietà |
| Builder Implementation | `06-builder/02-implementation-plan.md` | Piano porting da TreeStore |
| Serialization Overview | `07-serialization/00-overview.md` | Strategia TYTX, compatibility layer |
| Serialization Details | `07-serialization/01-overview.md` | walk/flattened dettagli |
| Serialization Plan | `07-serialization/02-implementation-plan.md` | Piano implementazione |
| Original Bag Methods | `04-bag/original_bag_methods.md` | Lista completa metodi originali |
| Compatibility Layer | `01-overview/03-compatibility_layer.md` | Differenze naming e comportamento |

---

## External References

| Reference | Location | Description |
|-----------|----------|-------------|
| TreeStore Builder | `genro-treestore/builders/` | BuilderBase, decorators, HtmlBuilder |
| TreeStore Serialization | `genro-treestore/store/serialization.py` | to_tytx, from_tytx, XML |
| Original gnrstructures.py | `Genropy/gnrpy/gnr/core/gnrstructures.py` | GnrStructData, GnrStructObj |
| genro-tytx | Package separato | Type-preserving encoding/decoding |
