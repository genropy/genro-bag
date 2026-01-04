# Serialization Implementation Plan

**Version**: 0.2.0
**Last Updated**: 2026-01-04
**Status**: 🟡 APPROVATO PARZIALMENTE - Architettura approvata, dettagli implementativi da revisionare

---

## Piano di Implementazione

### Dipendenza: genro-tytx#31

Prima di implementare `to_tytx()`, è necessario che genro-tytx supporti hook registration:

- **Issue**: [genro-tytx#31 - Add custom type registration hooks](https://github.com/genropy/genro-tytx/issues/31)
- **Stato**: Open

---

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

### Fase 2: Implementare flattener() in Bag

**File**: `src/genro_bag/bag.py`

```python
def flattener(
    self,
    path_registry: dict[int, str] | None = None,
) -> Generator[tuple[str | int | None, str, str | None, Any, dict], None, None]:
    """Generate tuples for serialization in depth-first order.

    Each tuple contains: (parent, label, tag, value, attr)

    Values are Python raw, except:
    - "::X" for Bag (branch nodes)

    TYTX encoding is done later by the serializer, not here.

    Args:
        path_registry: If provided (empty dict), enables compact mode
            with numeric parent codes instead of path strings.

    Yields:
        Tuples of (parent, label, tag, value, attr)
    """
    compact = path_registry is not None
    if compact:
        path_to_code: dict[str, int] = {}
        code_counter = 0

    walk_result = self.walk()
    if walk_result is None:
        return

    for path, node in walk_result:
        parent_path = path.rsplit(".", 1)[0] if "." in path else ""

        # Bag → "::X", otherwise raw value
        if isinstance(node.value, Bag):
            value = "::X"
        else:
            value = node.value

        attr = dict(node.attr) if node.attr else {}

        if compact:
            parent_ref = path_to_code.get(parent_path) if parent_path else None
            yield (parent_ref, node.label, node.tag, value, attr)

            if isinstance(node.value, Bag):
                path_to_code[path] = code_counter
                path_registry[code_counter] = path
                code_counter += 1
        else:
            yield (parent_path, node.label, node.tag, value, attr)
```

---

### Fase 3: Registrare tipo X in genro-tytx

**File**: `src/genro_bag/__init__.py` (o modulo dedicato `tytx_support.py`)

```python
def _register_bag_type():
    """Register Bag type with TYTX for serialization."""
    try:
        from genro_tytx import register_type
    except ImportError:
        return  # genro-tytx not installed

    from genro_bag import Bag
    import json

    def _serialize_bag(bag: Bag) -> str:
        """Serialize Bag to flattened JSON string."""
        return json.dumps(list(bag.flattener()))

    def _deserialize_bag(s: str) -> Bag:
        """Deserialize Bag from flattened JSON string."""
        return Bag.from_flattened(json.loads(s))

    register_type(Bag, "X", _serialize_bag, _deserialize_bag)

# Auto-register on import
_register_bag_type()
```

---

### Fase 4: Implementare from_flattened()

**File**: `src/genro_bag/bag.py`

```python
@classmethod
def from_flattened(
    cls,
    rows: list[tuple],
    builder: Any | None = None,
) -> "Bag":
    """Reconstruct Bag from flattened tuples.

    Args:
        rows: List of (parent, label, tag, value, attr) tuples
        builder: Optional builder instance

    Returns:
        Reconstructed Bag
    """
    try:
        from genro_tytx.utils import raw_decode
    except ImportError:
        raw_decode = None

    bag = cls(builder=builder)
    path_to_bag: dict[str, Bag] = {"": bag}

    for row in rows:
        parent_ref, label, tag, value, attr = row

        # Resolve parent path (handle both string and int refs)
        if isinstance(parent_ref, int):
            # Compact mode - need path_registry (not supported in from_flattened)
            raise ValueError("Compact mode requires path_registry")
        parent_path = parent_ref if parent_ref else ""

        parent_bag = path_to_bag.get(parent_path, bag)
        full_path = f"{parent_path}.{label}" if parent_path else label

        # Decode value
        if value == "::X":
            # Branch node
            child_bag = cls(builder=builder)
            parent_bag.set_item(label, child_bag, _attributes=attr)
            path_to_bag[full_path] = child_bag
        elif value is None:
            # Scalar None
            parent_bag.set_item(label, None, _attributes=attr)
        elif raw_decode and isinstance(value, str):
            # Try TYTX decode
            decoded, result = raw_decode(value)
            parent_bag.set_item(label, result if decoded else value, _attributes=attr)
        else:
            parent_bag.set_item(label, value, _attributes=attr)

    return bag
```

---

### Fase 5: Implementare to_tytx() e from_tytx()

**File**: `src/genro_bag/bag_serialization.py`

```python
def to_tytx(
    bag: "Bag",
    transport: Literal["json", "msgpack"] | None = None,
    compact: bool = False,
) -> str | bytes:
    """Serialize Bag to TYTX format with ::X type.

    Args:
        bag: The Bag to serialize
        transport: Output format (None/'json' or 'msgpack')
        compact: Use numeric parent codes if True

    Returns:
        Serialized data (str for JSON, bytes for msgpack)
    """
    try:
        from genro_tytx import to_tytx as tytx_encode
    except ImportError as e:
        raise ImportError("genro-tytx required for to_tytx()") from e

    if compact:
        paths: dict[int, str] = {}
        rows = list(bag.flattener(path_registry=paths))
        paths_str = {str(k): v for k, v in paths.items()}
        data = {"rows": rows, "paths": paths_str}
    else:
        rows = list(bag.flattener())
        data = rows

    # TYTX will recognize Bag type via registered hook and add ::X suffix
    return tytx_encode(bag, transport=transport)


def from_tytx(
    data: str | bytes,
    transport: Literal["json", "msgpack"] | None = None,
    builder: Any | None = None,
) -> "Bag":
    """Deserialize Bag from TYTX format.

    Args:
        data: Serialized data from to_tytx()
        transport: Input format matching serialization
        builder: Optional builder instance

    Returns:
        Reconstructed Bag
    """
    try:
        from genro_tytx import from_tytx as tytx_decode
    except ImportError as e:
        raise ImportError("genro-tytx required for from_tytx()") from e

    # TYTX will recognize ::X suffix and call registered deserializer
    return tytx_decode(data, transport=transport)
```

---

### Fase 6: Wrapper methods in Bag

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

### Fase 7: Test

**File**: `tests/test_serialization.py`

```python
class TestWalk:
    def test_walk_generator_empty(self):
        bag = Bag()
        assert list(bag.walk()) == []

    def test_walk_generator_flat(self):
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        result = list(bag.walk())
        assert len(result) == 2
        assert result[0][0] == "a"
        assert result[1][0] == "b"

    def test_walk_generator_nested(self):
        bag = Bag()
        child = Bag()
        child['x'] = 10
        bag['parent'] = child
        result = list(bag.walk())
        assert len(result) == 2
        assert result[0][0] == "parent"
        assert result[1][0] == "parent.x"

    def test_walk_callback(self):
        bag = Bag()
        bag['a'] = 1
        bag['b'] = 2
        labels = []
        bag.walk(lambda node: labels.append(node.label))
        assert labels == ["a", "b"]


class TestFlattener:
    def test_flattener_simple(self):
        bag = Bag()
        bag['name'] = 'test'
        rows = list(bag.flattener())
        assert len(rows) == 1
        parent, label, tag, value, attr = rows[0]
        assert parent == ""
        assert label == "name"
        assert value == "test"

    def test_flattener_raw_values(self):
        bag = Bag()
        bag['count'] = 42
        bag['flag'] = True
        rows = list(bag.flattener())
        # Values are raw Python types (TYTX encoding done by serializer)
        assert rows[0][3] == 42
        assert rows[1][3] == True

    def test_flattener_branch(self):
        bag = Bag()
        child = Bag()
        child['x'] = 1
        bag['child'] = child
        rows = list(bag.flattener())
        assert len(rows) == 2
        assert rows[0][3] == "::X"  # Branch marker
        assert rows[1][0] == "child"  # Parent path

    def test_flattener_compact_mode(self):
        bag = Bag()
        child = Bag()
        child['x'] = 1
        bag['parent'] = child

        paths = {}
        rows = list(bag.flattener(path_registry=paths))

        assert rows[0][0] is None  # Root has no parent code
        assert rows[1][0] == 0     # Child references parent code
        assert paths == {0: "parent"}


class TestFromFlattened:
    def test_from_flattened_simple(self):
        rows = [
            ("", "name", None, "test", {}),
            ("", "count", None, "42::L", {}),
        ]
        bag = Bag.from_flattened(rows)
        assert bag['name'] == "test"
        # With genro-tytx: assert bag['count'] == 42

    def test_from_flattened_nested(self):
        rows = [
            ("", "config", None, "::X", {}),
            ("config", "host", None, "localhost", {}),
        ]
        bag = Bag.from_flattened(rows)
        assert isinstance(bag['config'], Bag)
        assert bag['config.host'] == "localhost"


class TestTytxRoundtrip:
    """Tests requiring genro-tytx with hook registration."""

    def test_simple_roundtrip(self):
        pytest.importorskip("genro_tytx")

        bag = Bag()
        bag['name'] = "test"
        bag['count'] = 42

        data = bag.to_tytx()
        restored = Bag.from_tytx(data)

        assert restored['name'] == "test"
        assert restored['count'] == 42

    def test_nested_roundtrip(self):
        pytest.importorskip("genro_tytx")

        bag = Bag()
        child = Bag()
        child['x'] = 1
        bag['child'] = child

        data = bag.to_tytx()
        restored = Bag.from_tytx(data)

        assert isinstance(restored['child'], Bag)
        assert restored['child.x'] == 1

    def test_type_preservation(self):
        pytest.importorskip("genro_tytx")
        from decimal import Decimal
        from datetime import date

        bag = Bag()
        bag['price'] = Decimal("99.99")
        bag['date'] = date(2026, 1, 4)

        data = bag.to_tytx()
        restored = Bag.from_tytx(data)

        assert restored['price'] == Decimal("99.99")
        assert restored['date'] == date(2026, 1, 4)
```

---

## Checklist Implementazione

- [ ] **Blocco**: Attendere genro-tytx#31 (hook registration)
- [ ] Implementare `walk()` in Bag
- [ ] Implementare `flattener()` in Bag
- [ ] Implementare `from_flattened()` in Bag
- [ ] Registrare tipo X in genro-tytx (dopo #31)
- [ ] Implementare `to_tytx()` in bag_serialization.py
- [ ] Implementare `from_tytx()` in bag_serialization.py
- [ ] Aggiungere wrapper methods a Bag
- [ ] Scrivere test per walk
- [ ] Scrivere test per flattener
- [ ] Scrivere test per from_flattened
- [ ] Scrivere test per roundtrip TYTX
- [ ] Aggiornare project_status.md

---

## Ordine di Implementazione

1. **walk()** - Nessuna dipendenza
2. **flattener()** - Dipende da walk(), genro-tytx opzionale
3. **from_flattened()** - Nessuna dipendenza
4. **Registrazione tipo X** - Richiede genro-tytx#31
5. **to_tytx() / from_tytx()** - Richiedono registrazione tipo X

---

## Note Implementative

- `flattener()` emette valori Python raw, l'unico caso speciale è `"::X"` per Bag
- L'encoding TYTX viene fatto dal serializer, non dal flattener
- `from_flattened()` usa `genro_tytx.utils.raw_decode` con graceful fallback
- Il tipo `::X` viene riconosciuto nel deserializer per ricreare le Bag
- Compact mode richiede path_registry per la ricostruzione
