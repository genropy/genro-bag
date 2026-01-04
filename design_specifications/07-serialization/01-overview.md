# Serialization Overview

**Version**: 0.1.0
**Last Updated**: 2026-01-04
**Status**: 🔴 DA REVISIONARE

---

## Obiettivo

Implementare la serializzazione per Bag supportando:
- **TYTX** - Type-preserving format (Decimal, date, datetime, time)
- **XML** - Standard XML import/export
- **JSON** - Standard JSON (già stub presenti)

---

## Prerequisiti

Prima della serializzazione, serve implementare:
1. **`walk()`** - Traversal depth-first dell'albero
2. **`flattened()`** - Generatore di tuple per serializzazione

---

## Modello di Riferimento: TreeStore

### Metodo walk() in TreeStore

```python
def walk(self, callback=None):
    """Walk the tree depth-first.

    Args:
        callback: If provided, call callback(node) for each node.
                  If None, return generator of (path, node) tuples.
    """
    if callback is not None:
        for node in self.nodes():
            callback(node)
            if node.is_branch:
                node.value.walk(callback)
        return None

    def _walk_gen(store, prefix):
        for node in store.nodes():
            path = f"{prefix}.{node.label}" if prefix else node.label
            yield path, node
            if node.is_branch:
                yield from _walk_gen(node.value, path)

    return _walk_gen(self, "")
```

### Metodo flattened() in TreeStore

```python
def flattened(self, path_registry=None):
    """Generate tuples for serialization.

    Args:
        path_registry: If provided (dict), use compact mode with numeric codes.
                       If None, use normal mode with path strings.

    Yields:
        (parent, label, tag, value, attr) tuples where:
        - parent: Path string (normal) or int code (compact)
        - label: Node's key within parent
        - tag: Node type from builder (or None)
        - value: None for branch, actual value for leaf
        - attr: Dict of node attributes
    """
```

**Output Normal Mode**:
```python
[
    ("", "config_0", "config", None, {"name": "app"}),
    ("config_0", "db_0", "section", None, {"name": "database"}),
    ("config_0.db_0", "host_0", "setting", "localhost", {"key": "host"}),
]
```

**Output Compact Mode**:
```python
[
    (None, "config_0", "config", None, {"name": "app"}),
    (0, "db_0", "section", None, {"name": "database"}),
    (1, "host_0", "setting", "localhost", {"key": "host"}),
]
# path_registry = {0: "config_0", 1: "config_0.db_0"}
```

---

## Formato Wire TYTX

### Struttura

```python
{
    "rows": [
        (parent, label, tag, value, attr),
        ...
    ],
    "paths": {  # Solo in compact mode
        "0": "config_0",
        "1": "config_0.db_0",
        ...
    }
}
```

### Caratteristiche TYTX

- **Type-preserving**: Decimal, date, datetime, time preservati
- **Transport**: JSON (str) o MessagePack (bytes)
- **Compact mode**: ~30% più piccolo senza compressione
- **Normal mode**: Comprime meglio con gzip

---

## Serializzazione in TreeStore

### to_tytx()

```python
def to_tytx(store, transport=None, compact=False):
    from genro_tytx import to_tytx as tytx_encode

    if compact:
        paths = {}
        rows = list(store.flattened(path_registry=paths))
        paths_str = {str(k): v for k, v in paths.items()}
        return tytx_encode({"rows": rows, "paths": paths_str}, transport=transport)
    else:
        rows = list(store.flattened())
        return tytx_encode({"rows": rows}, transport=transport)
```

### from_tytx()

```python
def from_tytx(data, transport=None, builder=None):
    from genro_tytx import from_tytx as tytx_decode

    parsed = tytx_decode(data, transport=transport)
    rows = parsed["rows"]
    paths_raw = parsed.get("paths")
    code_to_path = {int(k): v for k, v in paths_raw.items()} if paths_raw else None

    store = TreeStore(builder=builder)
    path_to_store = {"": store}

    for row in rows:
        parent_ref, label, tag, value, attr = row

        # Resolve parent
        if code_to_path is not None:
            parent_path = code_to_path.get(parent_ref, "") if parent_ref is not None else ""
        else:
            parent_path = parent_ref

        parent_store = path_to_store.get(parent_path, store)
        full_path = f"{parent_path}.{label}" if parent_path else label

        # Create node
        node = TreeStoreNode(label, attr, value=value, tag=tag)

        if value is None:
            # Branch - create child store
            child_store = TreeStore(builder=builder)
            node._value = child_store
            child_store.parent = node
            path_to_store[full_path] = child_store

        node.parent = parent_store
        parent_store._insert_node(node, trigger=False)

    return store
```

---

## Stato Attuale in genro-bag

### File bag_serialization.py

Contiene solo stub:

```python
def to_xml(bag, root_tag=None) -> str:
    raise NotImplementedError("to_xml not yet implemented")

def from_xml(data, builder=None) -> "Bag":
    raise NotImplementedError("from_xml not yet implemented")

def to_json(bag, indent=None) -> str:
    raise NotImplementedError("to_json not yet implemented")

def from_json(data, builder=None) -> "Bag":
    raise NotImplementedError("from_json not yet implemented")

def as_dict(bag) -> dict:
    raise NotImplementedError("as_dict not yet implemented")

def as_dict_deeply(bag) -> dict:
    raise NotImplementedError("as_dict_deeply not yet implemented")

def as_string(bag) -> str:
    raise NotImplementedError("as_string not yet implemented")
```

### Da Implementare

| Funzione | Priorità | Note |
|----------|----------|------|
| `walk()` | Alta | Prerequisito per tutto |
| `flattened()` | Alta | Prerequisito per TYTX |
| `to_tytx()` | Alta | Serializzazione type-preserving |
| `from_tytx()` | Alta | Deserializzazione type-preserving |
| `to_xml()` | Media | Legacy Genropy |
| `from_xml()` | Media | Legacy Genropy |
| `to_json()` | Bassa | Può usare TYTX con transport='json' |
| `as_dict()` | Bassa | Utility |

---

## Differenze Bag vs TreeStore

| Aspetto | TreeStore | Bag |
|---------|-----------|-----|
| Branch detection | `isinstance(value, TreeStore)` | `isinstance(value, Bag)` |
| Nodes iterator | `store.nodes()` | `bag.nodes` (property) |
| Insert node | `store._insert_node(node)` | `bag.set_item(label, value, ...)` |
| Tag attribute | `node.tag` | `node.tag` ✅ |

---

## Dipendenze

- **genro-tytx** - Per serializzazione TYTX (opzionale, ImportError se mancante)

---

## Riferimenti

- TreeStore serialization: `genro-treestore/src/genro_treestore/store/serialization.py`
- Bag stub: `genro-bag/src/genro_bag/bag_serialization.py`
- TYTX docs: genro-tytx package
