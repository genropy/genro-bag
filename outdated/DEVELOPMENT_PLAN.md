# genro-bag Development Plan

**Version**: 0.1.0
**Last Updated**: 2025-12-07
**Status**: Planning

## Objective

Rewrite GnrBag with clean, modern API for Python and JavaScript, then unify in Rust.

## Development Phases

### FASE 1: Python Minimale

- Bag + BagNode core
- Path traversal (`a.b.c`, `#0`, `#parent`)
- Attributi sui nodi
- Serializzazione: XML, MessagePack, JSON (con TYTX)
- Test completi

### FASE 2: JS Minimale

- Stessa API di Python
- Stesso comportamento
- Serializzazione: XML, MessagePack, JSON (con TYTX)
- Test interoperabilità Python ↔ JS

### FASE 3: Rust Core

- Implementazione unica
- Binding PyO3 (Python)
- Binding wasm-bindgen (JS)
- Stessi test → drop-in replacement

### FASE 4: Wrapper Compatibilità Legacy

- Resolver, Trigger, Subscribe (nel wrapper, non nel core)
- Metodi deprecati con warning
- API legacy → nuova API

## API Classification

### CORE (Fase 1 - Minimale)

#### Bag

**Dunder methods:**
- `__getitem__`, `__setitem__`, `__delitem__`
- `__iter__`, `__len__`, `__contains__`
- `__str__`, `__eq__`

**Accesso/Modifica:**
- `get(path, default=None)`
- `getItem(path, default=None)`
- `setItem(path, value, **attrs)`
- `addItem(path, value, **attrs)`
- `pop(path, default=None)`
- `clear()`

**Chiavi/Valori:**
- `keys()`
- `values()`
- `items()`

**Nodi:**
- `getNode(path)`
- `getNodes()`

**Attributi:**
- `getAttr(path, attr)`
- `setAttr(path, **attrs)`

**Serializzazione:**
- `toXml()` / `fromXml()`
- `toJson()` / `fromJson()`
- `toMsgpack()` / `fromMsgpack()`

#### BagNode

- `label` (property)
- `getValue()` / `setValue(value)`
- `getAttr(name)` / `setAttr(**attrs)`
- `getStaticValue()` / `setStaticValue(value)`

### FASE 2 (Dopo il core)

- `sort()`, `sum()`, `digest()`
- `filter()`, `walk()`, `traverse()`
- `copy()`, `deepcopy()`, `update()`
- `asDict()`, `asDictDeeply()`

### LEGACY/DEPRECARE

- `merge()` - già deprecato
- `pickle()` / `unpickle()` - usare JSON/MessagePack
- `formula()`, `defineFormula()`, `defineSymbol()` - wrapper separato
- `rowchild()`, `child()` - builder pattern, wrapper separato

### WRAPPER COMPATIBILITÀ (non nel core Rust)

- Resolver
- Trigger / Subscribe
- Validators

## Path Syntax

| Syntax | Meaning |
|--------|---------|
| `a.b.c` | Nested path by label |
| `#0` | Access by index |
| `#-1` | Last element |
| `#parent` | Parent bag |
| `a.#0.b` | Mixed path |

## Serialization

| Format | Python | JS | Notes |
|--------|--------|-----|-------|
| **MessagePack** | `toMsgpack()` / `fromMsgpack()` | `toMsgpack()` / `fromMsgpack()` | Primary, TYTX for types |
| **JSON** | `toJson()` / `fromJson()` | `toJson()` / `fromJson()` | With TYTX (`123::L`) |
| **XML** | `toXml()` / `fromXml()` | `toXml()` / `fromXml()` | Legacy, typed attributes |

## Notes

- TYTX encoding/decoding stays in Python/JS (Rust booster was too slow)
- Resolver/Trigger logic stays in wrapper layer
- Core should be pure data structure with serialization
- Tests must be portable between Python and JS

## References

- Legacy Python: `gnrpy/gnr/core/gnrbag.py`
- Legacy JS: `gnrjs/gnr_d11/js/gnrbag.js`
- Rust architecture: `genro-bag-rust/` (documentation only for now)
- TYTX spec: `genro-tytx/`
