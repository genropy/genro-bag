# Serialization Implementation Plan

**Version**: 0.1.0
**Last Updated**: 2026-01-04
**Status**: 🔴 DA REVISIONARE

---

## Piano di Implementazione

### Fase 1: Implementare walk() in Bag

**File**: `src/genro_bag/bag.py`

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

### Fase 2: Implementare flattened() in Bag

**File**: `src/genro_bag/bag.py`

```python
def flattened(
    self,
    path_registry: dict[int, str] | None = None,
) -> Generator[tuple[str | int | None, str, str | None, Any, dict], None, None]:
    """Generate tuples for serialization in depth-first order.

    Each node becomes a tuple containing all information needed
    to reconstruct the tree hierarchy.

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
        - value: None for branch nodes, actual value for leaf nodes
        - attr: Dict of node attributes (copy)

    Example:
        >>> # Normal mode
        >>> list(bag.flattened())
        [('', 'config_0', 'config', None, {}),
         ('config_0', 'host_0', 'setting', 'localhost', {})]

        >>> # Compact mode
        >>> paths = {}
        >>> list(bag.flattened(path_registry=paths))
        [(None, 'config_0', 'config', None, {}),
         (0, 'host_0', 'setting', 'localhost', {})]
        >>> paths
        {0: 'config_0'}
    """
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

        # Determine if branch
        is_branch = isinstance(node.value, Bag)
        value = None if is_branch else node.value

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
            if is_branch:
                path_to_code[path] = code_counter
                path_registry[code_counter] = path
                code_counter += 1
        else:
            # Normal mode: use path strings
            yield (parent_path, node.label, node.tag, value, attr)
```

---

### Fase 3: Implementare to_tytx()

**File**: `src/genro_bag/bag_serialization.py`

```python
def to_tytx(
    bag: Bag,
    transport: Literal["json", "msgpack"] | None = None,
    compact: bool = False,
) -> str | bytes:
    """Serialize a Bag to TYTX format.

    TYTX preserves Python types (Decimal, date, datetime, time)
    across serialization.

    Args:
        bag: The Bag to serialize.
        transport: Output format:
            - None or 'json': JSON string (default)
            - 'msgpack': Binary MessagePack bytes
        compact: Serialization mode:
            - False (default): Parent paths as full strings
            - True: Parent paths as numeric codes

    Returns:
        str if transport is None or 'json', bytes if 'msgpack'.

    Raises:
        ImportError: If genro-tytx package is not installed.
    """
    try:
        from genro_tytx import to_tytx as tytx_encode
    except ImportError as e:
        raise ImportError("genro-tytx package required for serialization") from e

    if compact:
        paths: dict[int, str] = {}
        rows = list(bag.flattened(path_registry=paths))
        paths_str = {str(k): v for k, v in paths.items()}
        return tytx_encode({"rows": rows, "paths": paths_str}, transport=transport)
    else:
        rows = list(bag.flattened())
        return tytx_encode({"rows": rows}, transport=transport)
```

---

### Fase 4: Implementare from_tytx()

**File**: `src/genro_bag/bag_serialization.py`

```python
def from_tytx(
    data: str | bytes,
    transport: Literal["json", "msgpack"] | None = None,
    builder: Any | None = None,
) -> Bag:
    """Deserialize Bag from TYTX format.

    Reconstructs a complete Bag hierarchy from TYTX-encoded data.
    Automatically detects normal vs compact format.

    Args:
        data: Serialized data from to_tytx().
        transport: Input format matching serialization.
        builder: Optional builder instance for the reconstructed bag.

    Returns:
        Bag: Fully reconstructed tree with types preserved.

    Raises:
        ImportError: If genro-tytx package is not installed.
    """
    try:
        from genro_tytx import from_tytx as tytx_decode
    except ImportError as e:
        raise ImportError("genro-tytx package required for deserialization") from e

    from .bag import Bag

    parsed = tytx_decode(data, transport=transport)
    rows = parsed["rows"]
    paths_raw = parsed.get("paths")
    code_to_path: dict[int, str] | None = (
        {int(k): v for k, v in paths_raw.items()} if paths_raw else None
    )

    bag = Bag(builder=builder)
    path_to_bag: dict[str, Bag] = {"": bag}

    for row in rows:
        parent_ref, label, tag, value, attr = row

        # Resolve parent path
        if code_to_path is not None:
            parent_path = code_to_path.get(parent_ref, "") if parent_ref is not None else ""
        else:
            parent_path = parent_ref

        # Get parent bag
        parent_bag = path_to_bag.get(parent_path, bag)
        full_path = f"{parent_path}.{label}" if parent_path else label

        if value is None:
            # Branch node - create child bag
            child_bag = Bag(builder=builder)
            parent_bag.set_item(label, child_bag, _attributes=attr, tag=tag)
            path_to_bag[full_path] = child_bag
        else:
            # Leaf node
            parent_bag.set_item(label, value, _attributes=attr, tag=tag)

    return bag
```

---

### Fase 5: Aggiungere metodi wrapper a Bag

**File**: `src/genro_bag/bag.py`

```python
def to_tytx(
    self,
    transport: Literal["json", "msgpack"] | None = None,
    compact: bool = False,
) -> str | bytes:
    """Serialize to TYTX format. See bag_serialization.to_tytx()."""
    from .bag_serialization import to_tytx
    return to_tytx(self, transport=transport, compact=compact)

@classmethod
def from_tytx(
    cls,
    data: str | bytes,
    transport: Literal["json", "msgpack"] | None = None,
    builder: Any | None = None,
) -> "Bag":
    """Deserialize from TYTX format. See bag_serialization.from_tytx()."""
    from .bag_serialization import from_tytx
    return from_tytx(data, transport=transport, builder=builder)
```

---

### Fase 6: Test

**File**: `tests/test_serialization.py`

```python
class TestWalk:
    def test_walk_generator_empty(self):
        bag = Bag()
        assert list(bag.walk()) == []

    def test_walk_generator_flat(self):
        bag = Bag()
        bag.set_item("a", 1)
        bag.set_item("b", 2)
        result = list(bag.walk())
        assert len(result) == 2
        assert result[0][0] == "a"
        assert result[1][0] == "b"

    def test_walk_generator_nested(self):
        bag = Bag()
        child = Bag()
        child.set_item("x", 10)
        bag.set_item("parent", child)
        result = list(bag.walk())
        assert len(result) == 2
        assert result[0][0] == "parent"
        assert result[1][0] == "parent.x"

    def test_walk_callback(self):
        bag = Bag()
        bag.set_item("a", 1)
        bag.set_item("b", 2)
        labels = []
        bag.walk(lambda node: labels.append(node.label))
        assert labels == ["a", "b"]


class TestFlattened:
    def test_flattened_normal_mode(self):
        bag = Bag()
        bag.set_item("a", 1)
        rows = list(bag.flattened())
        assert len(rows) == 1
        parent, label, tag, value, attr = rows[0]
        assert parent == ""
        assert label == "a"
        assert value == 1

    def test_flattened_compact_mode(self):
        bag = Bag()
        child = Bag()
        child.set_item("x", 10)
        bag.set_item("parent", child)

        paths = {}
        rows = list(bag.flattened(path_registry=paths))

        assert len(rows) == 2
        assert rows[0][0] is None  # root has no parent code
        assert rows[1][0] == 0     # child references parent code
        assert paths == {0: "parent"}


class TestTytxRoundtrip:
    def test_simple_roundtrip(self):
        bag = Bag()
        bag.set_item("name", "test")
        bag.set_item("count", 42)

        data = bag.to_tytx()
        restored = Bag.from_tytx(data)

        assert restored["name"] == "test"
        assert restored["count"] == 42

    def test_nested_roundtrip(self):
        bag = Bag()
        child = Bag()
        child.set_item("x", 1)
        bag.set_item("child", child)

        data = bag.to_tytx()
        restored = Bag.from_tytx(data)

        assert restored["child.x"] == 1

    def test_type_preservation(self):
        from decimal import Decimal
        from datetime import date

        bag = Bag()
        bag.set_item("price", Decimal("99.99"))
        bag.set_item("date", date(2026, 1, 4))

        data = bag.to_tytx()
        restored = Bag.from_tytx(data)

        assert restored["price"] == Decimal("99.99")
        assert restored["date"] == date(2026, 1, 4)
```

---

## Checklist Implementazione

- [ ] Implementare `walk()` in Bag
- [ ] Implementare `flattened()` in Bag
- [ ] Implementare `to_tytx()` in bag_serialization.py
- [ ] Implementare `from_tytx()` in bag_serialization.py
- [ ] Aggiungere metodi wrapper `to_tytx()`, `from_tytx()` a Bag
- [ ] Scrivere test per walk
- [ ] Scrivere test per flattened
- [ ] Scrivere test per roundtrip TYTX
- [ ] Aggiornare project_status.md

---

## Stima Effort

| Fase | Linee codice | Complessità |
|------|--------------|-------------|
| walk() | ~30 | Bassa |
| flattened() | ~50 | Media |
| to_tytx() | ~25 | Bassa |
| from_tytx() | ~50 | Media |
| Test | ~150 | Media |
| **Totale** | ~305 | Media |

---

## Dipendenze

- **genro-tytx** - Opzionale, ImportError graceful se mancante

---

## Note

- `set_item()` in Bag dovrà supportare parametro `tag` per from_tytx()
- Verificare che `_attributes` sia passato correttamente in set_item()
- Il builder viene propagato ai child Bag durante deserializzazione
