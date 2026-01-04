# Builder Implementation Plan

**Version**: 0.1.0
**Last Updated**: 2026-01-04
**Status**: 🔴 DA REVISIONARE

---

## Piano di Implementazione

### Fase 1: Creare Directory builders/

**Struttura**:
```
src/genro_bag/builders/
├── __init__.py
├── base.py
└── decorators.py
```

---

### Fase 2: Copiare decorators.py

**Sorgente**: `genro-treestore/src/genro_treestore/builders/decorators.py`
**Destinazione**: `genro-bag/src/genro_bag/builders/decorators.py`

**Modifiche necessarie**: NESSUNA (file completamente generico)

**Contenuto**:
- `_parse_tag_spec()` - parser `tag[n:m]`
- `_parse_tags()` - comma-separated → lista
- `_annotation_to_attr_spec()` - type hint → spec
- `_extract_attrs_from_signature()` - estrae attrs
- `_validate_attrs_from_spec()` - valida kwargs
- `element()` - decorator principale

---

### Fase 3: Adattare base.py

**Sorgente**: `genro-treestore/src/genro_treestore/builders/base.py`
**Destinazione**: `genro-bag/src/genro_bag/builders/base.py`

**Modifiche necessarie**:

#### 3.1 Type Hints (TYPE_CHECKING block)

```python
# Da:
if TYPE_CHECKING:
    from ..store import TreeStore
    from ..store import TreeStoreNode

# A:
if TYPE_CHECKING:
    from ..bag import Bag
    from ..bag_node import BagNode
```

#### 3.2 Metodo child() - UNICO METODO DA ADATTARE

```python
# Da (TreeStore):
def child(
    self,
    target: TreeStore,
    tag: str,
    label: str | None = None,
    value: Any = None,
    _position: str | None = None,
    _builder: BuilderBase | None = None,
    **attr: Any,
) -> TreeStore | TreeStoreNode:
    from ..store import TreeStore
    from ..store import TreeStoreNode

    # ... auto-generate label ...

    if value is not None:
        # Leaf node
        node = TreeStoreNode(label, attr, value, parent=target, tag=tag)
        target._insert_node(node, _position)
        return node
    else:
        # Branch node
        child_store = TreeStore(builder=child_builder)
        node = TreeStoreNode(label, attr, value=child_store, parent=target, tag=tag)
        child_store.parent = node
        target._insert_node(node, _position)
        return child_store
```

```python
# A (Bag):
def child(
    self,
    target: Bag,
    tag: str,
    label: str | None = None,
    value: Any = None,
    _position: str | None = None,
    _builder: BuilderBase | None = None,
    **attr: Any,
) -> Bag | BagNode:
    from ..bag import Bag
    from ..bag_node import BagNode

    # Auto-generate label if not provided
    if label is None:
        n = 0
        while f"{tag}_{n}" in target._nodes:
            n += 1
        label = f"{tag}_{n}"

    # Determine builder for child
    child_builder = _builder if _builder is not None else target._builder

    if value is not None:
        # Leaf node
        target.set_item(label, value, _attributes=attr, _position=_position, tag=tag)
        return target._nodes.get(label)
    else:
        # Branch node
        child_bag = Bag(builder=child_builder)
        target.set_item(label, child_bag, _attributes=attr, _position=_position, tag=tag)
        return child_bag
```

#### 3.3 Metodo check() - Minime modifiche

```python
# check() usa store.nodes() - Bag ha già nodes property
# Nessuna modifica necessaria, solo type hints
def check(self, store: Bag, parent_tag: str | None = None, path: str = "") -> list[str]:
    # ... codice identico ...
    for node in store.nodes:  # Bag.nodes è property
        # ...
```

#### 3.4 Metodi generici - NESSUNA MODIFICA

- `__init_subclass__()` - generico
- `__getattr__()` - generico
- `_validate_attrs()` - generico
- `_resolve_ref()` - generico
- `_parse_children_spec()` - generico
- `_make_schema_handler()` - adattare return type
- `_get_validation_rules()` - generico

---

### Fase 4: Modificare Bag

**File**: `src/genro_bag/bag.py`

#### 4.1 Aggiungere a __slots__

```python
__slots__ = (
    "_nodes",
    "parent",
    "_builder",  # NUOVO
    "_upd_subscribers",
    # ...
)
```

#### 4.2 Modificare __init__

```python
def __init__(
    self,
    source: dict | list | Bag | None = None,
    *,
    builder: Any | None = None,  # NUOVO
) -> None:
    self._nodes = BagNodeContainer()
    self.parent = None
    self._builder = builder  # NUOVO
    # ...
```

#### 4.3 Aggiungere property builder

```python
@property
def builder(self) -> Any:
    """Access the builder instance."""
    return self._builder
```

#### 4.4 Aggiungere __getattr__

```python
def __getattr__(self, name: str) -> Any:
    """Delegate attribute access to builder if present."""
    if name.startswith("_"):
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    if self._builder is not None:
        handler = getattr(self._builder, name)
        if callable(handler):
            return lambda _nodelabel=None, **attr: handler(
                self, tag=name, label=_nodelabel, **attr
            )

    raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
```

#### 4.5 Propagare builder ai child

In `set_item()` quando si crea un child Bag:

```python
# Quando value è Bag e viene inserito
if isinstance(value, Bag) and value._builder is None:
    value._builder = self._builder
```

---

### Fase 5: Aggiornare __init__.py

**File**: `src/genro_bag/__init__.py`

```python
from .bag import Bag
from .bag_node import BagNode, BagNodeException
from .bagnode_container import BagNodeContainer
from .builders import BuilderBase, element

__all__ = [
    "Bag",
    "BagNode",
    "BagNodeException",
    "BagNodeContainer",
    "BuilderBase",
    "element",
]
```

---

### Fase 6: Test

**File**: `tests/test_builders.py`

Test da portare/adattare da TreeStore:
- `TestParseTagSpec` - cardinality syntax
- `TestAnnotationToAttrSpec` - type hint parsing
- `TestBuilderBaseValidateAttrs` - attribute validation
- `TestElementDecorator` - decorator functionality
- `TestBuilderBase` - full integration

Test nuovi specifici per Bag:
- Test creazione nodi con builder
- Test propagazione builder a child
- Test label auto-generation (`tag_0`, `tag_1`, ...)

---

## Checklist Implementazione

- [ ] Creare `src/genro_bag/builders/` directory
- [ ] Copiare `decorators.py` (as-is)
- [ ] Adattare `base.py` (type hints + child())
- [ ] Creare `builders/__init__.py`
- [ ] Aggiungere `_builder` a Bag.__slots__
- [ ] Modificare `Bag.__init__()` con parametro builder
- [ ] Aggiungere `Bag.builder` property
- [ ] Aggiungere `Bag.__getattr__()`
- [ ] Propagare builder in set_item()
- [ ] Aggiornare `__init__.py` exports
- [ ] Scrivere test
- [ ] Aggiornare project_status.md

---

## Stima Effort

| Fase | Linee codice | Complessità |
|------|--------------|-------------|
| decorators.py | ~350 (copia) | Bassa |
| base.py | ~400 (adattare) | Media |
| Bag modifications | ~50 | Bassa |
| Test | ~200 | Media |
| **Totale** | ~1000 | Media |

---

## Dipendenze

Nessuna dipendenza esterna. Il builder system usa solo stdlib Python.
