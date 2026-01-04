# Serialization Technical Details

**Version**: 0.2.0
**Last Updated**: 2026-01-04
**Status**: 🟡 APPROVATO PARZIALMENTE - Architettura approvata, dettagli implementativi da revisionare

---

## Obiettivo

Implementare la serializzazione per Bag con:

- **flattener()** - Generator di tuple per pipeline composabile
- **TYTX** - Type-preserving format con tipo `::X` per Bag
- **XML/JSON puri** - Per interoperabilità esterna (no magia Genropy)

---

## Prerequisiti

Prima della serializzazione, serve implementare:

1. **`walk()`** - Traversal depth-first dell'albero
2. **`flattener()`** - Generatore di tuple per serializzazione

---

## Metodo walk()

```python
def walk(
    self,
    callback: Callable[[BagNode], None] | None = None,
) -> Generator[tuple[str, BagNode], None, None] | None:
    """Walk the tree depth-first.

    Args:
        callback: If provided, call callback(node) for each node
                  and return None.
                  If None, return generator of (path, node) tuples.

    Returns:
        Generator of (path, node) if callback is None, else None.

    Example:
        >>> # Callback mode
        >>> bag.walk(lambda node: print(node.label))

        >>> # Generator mode
        >>> for path, node in bag.walk():
        ...     print(f"{path}: {node.value}")
    """
    if callback is not None:
        for node in self.nodes:
            callback(node)
            if isinstance(node.value, Bag):
                node.value.walk(callback)
        return None

    def _walk_gen(bag: Bag, prefix: str) -> Generator[tuple[str, BagNode], None, None]:
        for node in bag.nodes:
            path = f"{prefix}.{node.label}" if prefix else node.label
            yield path, node
            if isinstance(node.value, Bag):
                yield from _walk_gen(node.value, path)

    return _walk_gen(self, "")
```

---

## Metodo flattener()

**Nome**: `flattener()` (non `flattened()` come in TreeStore)

### Signature

```python
def flattener(
    self,
    path_registry: dict[int, str] | None = None,
) -> Generator[tuple[str | int | None, str, str | None, str | None, dict], None, None]:
    """Generate tuples for serialization in depth-first order.

    Args:
        path_registry: If provided (empty dict), enables compact mode.
            - Parent references become numeric codes (0, 1, 2...)
            - Dict is populated with {code: path} for branch nodes
            If None, parent references are full path strings.

    Yields:
        Tuples of (parent, label, tag, value, attr) where:
        - parent: Path string (normal) or int code (compact), None/'' for root
        - label: Node's key within parent (e.g., 'setting_0')
        - tag: Node type from builder (e.g., 'setting') or None
        - value: TYTX-encoded value:
            - "::X" for branch nodes (Bag)
            - None for scalar None
            - "value::SUFFIX" for typed values
            - "string" for plain strings
        - attr: Dict of node attributes (copy)
    """
```

### Implementazione

```python
def flattener(
    self,
    path_registry: dict[int, str] | None = None,
) -> Generator[tuple[str | int | None, str, str | None, Any, dict], None, None]:

    compact = path_registry is not None
    if compact:
        path_to_code: dict[str, int] = {}
        code_counter = 0

    walk_result = self.walk()
    if walk_result is None:
        return

    for path, node in walk_result:
        # Extract parent path
        parent_path = path.rsplit(".", 1)[0] if "." in path else ""

        # Determine value: Bag → "::X", otherwise raw value
        if isinstance(node.value, Bag):
            value = "::X"  # Branch marker
        else:
            value = node.value  # Raw value (encoding done later by serializer)

        # Copy attributes
        attr = dict(node.attr) if node.attr else {}

        if compact:
            # Compact mode: use numeric codes
            if parent_path:
                parent_ref = path_to_code.get(parent_path)
            else:
                parent_ref = None

            yield (parent_ref, node.label, node.tag, value, attr)

            # Register branch nodes
            if isinstance(node.value, Bag):
                path_to_code[path] = code_counter
                path_registry[code_counter] = path
                code_counter += 1
        else:
            # Normal mode: use path strings
            yield (parent_path, node.label, node.tag, value, attr)
```

**Nota**: Il flattener emette valori Python raw. L'encoding TYTX (suffissi `::L`, `::D`, etc.) viene fatto successivamente dal serializer.

### Output Examples

**Normal Mode** (path strings):

```python
bag = Bag()
bag['name'] = 'Giovanni'
bag['age'] = 42
config = Bag()
config['debug'] = True
bag['config'] = config

list(bag.flattener())
# [
#     ('', 'name', None, 'Giovanni', {}),
#     ('', 'age', None, 42, {}),           # raw int
#     ('', 'config', None, '::X', {}),     # branch marker
#     ('config', 'debug', None, True, {}), # raw bool
# ]
```

**Compact Mode** (numeric codes):

```python
paths = {}
list(bag.flattener(path_registry=paths))
# [
#     (None, 'name', None, 'Giovanni', {}),
#     (None, 'age', None, 42, {}),
#     (None, 'config', None, '::X', {}),
#     (0, 'debug', None, True, {}),
# ]
# paths = {0: 'config'}
```

---

## Valori nel Flattener

Il flattener emette valori Python raw, eccetto per le Bag:

| Tipo Python | Valore emesso | Note |
|-------------|---------------|------|
| `Bag` | `"::X"` | Unico caso speciale - branch marker |
| `None` | `None` | Raw |
| `int` | `42` | Raw |
| `float` | `3.14` | Raw |
| `bool` | `True` | Raw |
| `Decimal` | `Decimal("99.99")` | Raw |
| `date` | `date(2026, 1, 4)` | Raw |
| `datetime` | `datetime(...)` | Raw |
| `time` | `time(10, 30)` | Raw |
| `str` | `"hello"` | Raw |

L'encoding TYTX (`::L`, `::D`, etc.) viene applicato dal serializer, non dal flattener.

---

## Pipeline con Localizer

Il flattener produce un generator che può essere processato da iteratori composabili:

```python
def localizer(flattened_iter, translate_cb):
    """Iteratore che traduce le stringhe localizzabili."""
    for parent, label, tag, value, attr in flattened_iter:
        # Traduci il valore se è stringa
        if isinstance(value, str) and not value.endswith(('::X', '::L', '::R', '::B', '::N', '::D', '::DHZ', '::H')):
            value = translate_cb(value)

        # Traduci attributi stringa
        translated_attr = {}
        for k, v in attr.items():
            if isinstance(v, str):
                translated_attr[k] = translate_cb(v)
            else:
                translated_attr[k] = v

        yield (parent, label, tag, value, translated_attr)
```

**Uso**:

```python
# Pipeline: flattener → localizer → serializer
localized = localizer(bag.flattener(), my_translate_cb)
rows = list(localized)
```

---

## Formato Wire TYTX

### Struttura con ::X

```python
# Bag serializzata
'[["", "name", null, "Giovanni", {}], ["", "config", null, "::X", {}], ["config", "debug", null, "true::B", {}]]::X'
```

Il suffix `::X` finale indica "questa è una Bag serializzata".

### Compact Mode

```python
{
    "rows": [
        [null, "name", null, "Giovanni", {}],
        [null, "config", null, "::X", {}],
        [0, "debug", null, "true::B", {}]
    ],
    "paths": {"0": "config"}
}
```

---

## Differenze da TreeStore

| Aspetto | TreeStore | Bag |
|---------|-----------|-----|
| Nome metodo | `flattened()` | `flattener()` |
| Branch detection | `value is None` | `value == "::X"` |
| Tipo branch | Implicito | Esplicito `::X` |
| Valori tipizzati | Post-processing | Nel flattener |

---

## Dipendenze

- **genro-tytx** - Per encoding valori (opzionale, graceful fallback)
- **genro-tytx#31** - Hook registration per tipo `::X`

---

## Riferimenti

- [00-overview.md](00-overview.md) - Architettura generale
- [02-implementation-plan.md](02-implementation-plan.md) - Piano implementazione
- [GitHub Issue #31](https://github.com/genropy/genro-tytx/issues/31) - Hook registration
- TreeStore `flattened()`: `genro-treestore/src/genro_treestore/store/core.py`
