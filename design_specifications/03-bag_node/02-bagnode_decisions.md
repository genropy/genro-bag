# BagNode Design Decisions

**Status**: 🔴 DA REVISIONARE
**Last Updated**: 2025-01-02

This document tracks design decisions for the new BagNode implementation, comparing the original BagNode with TreeStoreNode.

---

## Reference Files

| File | Description |
|------|-------------|
| [original_bagnode.py](original_bagnode.py) | Original Genropy BagNode |
| [treestore_node.py](treestore_node.py) | TreeStore attempt (more modern) |
| [01-original_bagnode_spec.md](01-original_bagnode_spec.md) | Original BagNode analysis |

---

## Comparison: Original BagNode vs TreeStoreNode

### Constructor Signature

**Original BagNode:**
```python
def __init__(self, parentbag, label, value=None, attr=None, resolver=None,
             validators=None, _removeNullAttributes=True, _attributes=None):
```

**TreeStoreNode:**
```python
def __init__(
    self,
    label: str,
    attr: dict[str, Any] | None = None,
    value: Any = None,
    parent: TreeStore | None = None,
    tag: str | None = None,
    resolver: TreeStoreResolver | None = None,
) -> None:
```

### Slots Comparison

| Original BagNode | TreeStoreNode | Notes |
|------------------|---------------|-------|
| `label` | `label` | Same |
| `_value` | `_value` | Same |
| `parentbag` | `parent` | Renamed (snake_case) |
| `resolver` | `_resolver` | TreeStore uses property |
| `locked` | - | **REMOVED** (never used) |
| `_node_subscribers` | `_node_subscribers` | Same |
| `_validators` | - | Postponed |
| - | `attr` | TreeStore: always dict |
| - | `tag` | **NEW**: for builder validation |
| - | `_invalid_reasons` | **NEW**: validation state |

---

## Design Decisions

### Decision 1: Remove `locked`

**Status**: ✅ APPROVED

**Rationale**:
- `locked` is initialized to `False` in BagNode
- Checked in `setValue` to raise exception if `True`
- **Never set to `True` anywhere in the entire Genropy codebase**
- Dead code / unused feature

**Decision**: Do not include `locked` in new BagNode.

**Future**: If immutability is needed, implement via frozen pattern or context manager.

---

### Decision 2: Remove `validators`

**Status**: ✅ APPROVED

**Rationale**:
- Complex feature with `_validators` callback chain
- Not essential for core functionality
- **Decision**: Remove completely, not just postpone

**Decision**: Do not include `validators`. Feature removed from design.

---

### Decision 3: Add `tag` attribute

**Status**: ✅ APPROVED

**Source**: TreeStoreNode

**Purpose**:
- Used by builder system for validation
- Stores the "type" of node (e.g., `div`, `span` for HTML builder)
- Enables `@valid_children` validation

**Decision**: Include `tag` as dedicated slot in BagNode.

```python
self.tag = tag  # in __slots__ and __init__
```

---

### Decision 4: Add `_invalid_reasons`

**Status**: ✅ APPROVED

**Source**: TreeStoreNode

**Purpose**:
- Tracks validation errors per node
- `is_valid` property checks `len(self._invalid_reasons) == 0`
- Used by builder validation system

**Decision**: Include `_invalid_reasons` for builder validation support.

```python
self._invalid_reasons: list[str] = []

@property
def is_valid(self) -> bool:
    return len(self._invalid_reasons) == 0
```

---

### Decision 5: Property for resolver (bidirectional link)

**Status**: ✅ APPROVED

**Original BagNode**: Property with setter `resolver.parentNode = self`

**TreeStoreNode**: Same pattern with snake_case `resolver.parent_node = self`

**Decision**: Use property pattern with snake_case naming:

```python
@property
def resolver(self) -> Resolver | None:
    return self._resolver

@resolver.setter
def resolver(self, resolver: Resolver | None) -> None:
    if resolver is not None:
        resolver.parent_node = self  # snake_case (Decision #9)
    self._resolver = resolver
```

**Note**: Aligns with resolver.md Decision #10 (Parent Node Ref)

---

### Decision 6: Remove `_attributes` fast path completely

**Status**: ✅ APPROVED

**Original BagNode**: Has `_attributes` parameter for "fast path" deserialization:
```python
def __init__(self, parentbag, label, value=None, attr=None, resolver=None,
             validators=None, _removeNullAttributes=True, _attributes=None):
    ...
    if _attributes:
        self.attr = _attributes
        self._value = value
        return  # Skip all processing
```

**Analysis**:
- Added 7 years ago for fast deserialization
- Used in only one place in the framework
- The performance gain is not needed

**Decision**: Remove `_attributes` parameter entirely. Simple `__init__`:

```python
class BagNode:
    def __init__(
        self,
        label: str,
        value: Any = None,
        attr: dict[str, Any] | None = None,
        parent_bag: Bag | None = None,
        resolver: Resolver | None = None,
        tag: str | None = None,
    ) -> None:
        self.label = label
        self._parent_bag = parent_bag
        self._node_subscribers = {}
        self.tag = tag
        self._invalid_reasons = []
        self._attr = {}
        self._resolver = None

        if attr:
            self.set_attr(attr, trigger=False)

        if resolver is not None:
            self.resolver = resolver  # Property setter for bidirectional link

        if value is not None:
            self.set_value(value, trigger=False)
```

**Benefits**:
- Simpler API - one path only
- No confusing dual parameters
- Less code to maintain

---

### Decision 7: `is_branch` / `is_leaf` properties

**Status**: 🟠 POSTPONED

**Source**: TreeStoreNode

```python
@property
def is_branch(self) -> bool:
    """True if this node contains a TreeStore (has children)."""
    return isinstance(self._value, TreeStore)

@property
def is_leaf(self) -> bool:
    """True if this node contains a scalar value."""
    return not isinstance(self._value, TreeStore)
```

**Original BagNode**: No equivalent (checks done inline)

**Proposal**: Include - cleaner API, self-documenting

---

### Decision 8: Parent navigation property `_`

**Status**: ✅ APPROVED

**Source**: TreeStoreNode

**Decision**: Include `_` property for parent navigation:

```python
@property
def _(self) -> Bag:
    """Return parent Bag for navigation/chaining."""
    if self._parent_bag is None:
        raise ValueError("Node has no parent")
    return self._parent_bag
```

**Usage**: `node._.set_item('sibling', 'value')`

**Benefits**:
- Enables fluent chaining: `node._.set_item(...)`
- Concise syntax for parent access
- Follows TreeStore pattern

---

### Decision 9: Naming convention

**Status**: ✅ APPROVED (from Resolver decisions)

Use snake_case:
- `parent_bag` (not `parentbag`)
- `get_value()` / `set_value()`
- `get_attr()` / `set_attr()`

---

### Decision 10: `__slots__` usage

**Status**: ✅ APPROVED

Both Original and TreeStore use `__slots__`. Continue this pattern for memory efficiency.

---

## Proposed New BagNode Signature

```python
class BagNode:
    __slots__ = (
        '_label',
        '_value',
        '_attr',
        '_parent_bag',
        '_resolver',
        '_node_subscribers',
        # Optional (to discuss):
        # 'tag',
        # '_invalid_reasons',
    )

    def __init__(
        self,
        label: str,
        value: Any = None,
        attr: dict[str, Any] | None = None,
        parent_bag: Bag | None = None,
        resolver: Resolver | None = None,
        *,
        _attributes: dict[str, Any] | None = None,  # Fast path
    ) -> None:
```

**Changes from Original**:
- Removed: `validators`, `locked`, `_removeNullAttributes`
- Renamed: `parentbag` → `parent_bag`
- Reordered: `label` first (always required)
- Added: `_attributes` as keyword-only for fast path

---

## Open Questions

1. **tag**: Include for builder support?
2. **_invalid_reasons**: Include for validation tracking?
3. **`_` property**: Include parent navigation shortcut?
4. **Subscribers**: Keep full subscription system or simplify?

---

## Next Steps

1. Finalize decisions on open questions
2. Create `bagnode.md` specification (like resolver.md)
3. Implement BagNode with tests
