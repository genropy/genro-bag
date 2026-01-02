# BagNode vs TreeStoreNode - Detailed Comparison

**Status**: 🔴 DA REVISIONARE
**Last Updated**: 2025-01-02

Comparison between Original BagNode (gnrbag.py) and TreeStoreNode (genro-treestore).

---

## 1. Class Definition & Slots

### Original BagNode
```python
class BagNode(object):
    # No __slots__ defined - uses __dict__
    # Attributes set in __init__:
    # - label, locked, _value, resolver, parentbag (via property)
    # - _node_subscribers, _validators, attr
```

### TreeStoreNode
```python
class TreeStoreNode:
    __slots__ = (
        "label",
        "attr",
        "_value",
        "parent",
        "tag",
        "_node_subscribers",
        "_resolver",
        "_invalid_reasons",
    )
```

| Aspect | Original | TreeStore | Decision |
|--------|----------|-----------|----------|
| `__slots__` | No (usa `__dict__`) | Yes | ✅ Use slots |
| Memory | Higher | Lower | TreeStore wins |

---

## 2. Constructor Signature

### Original BagNode
```python
def __init__(self, parentbag, label, value=None, attr=None, resolver=None,
             validators=None, _removeNullAttributes=True, _attributes=None):
```

### TreeStoreNode
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

| Parameter | Original | TreeStore | Notes |
|-----------|----------|-----------|-------|
| Order | parentbag first | label first | TreeStore more logical |
| `label` | Required (2nd) | Required (1st) | Both required |
| `value` | Optional | Optional | Same |
| `attr` | Optional | Optional | Same |
| `parent` | `parentbag` | `parent` | Renamed |
| `resolver` | Optional | Optional | Same |
| `validators` | Optional | **REMOVED** | Not in TreeStore |
| `_removeNullAttributes` | Optional | **REMOVED** | Legacy compat |
| `_attributes` | Fast path | **REMOVED** | Different approach |
| `tag` | **N/A** | Optional | NEW in TreeStore |

---

## 3. Instance Attributes

| Attribute | Original | TreeStore | Notes |
|-----------|----------|-----------|-------|
| `label` | `self.label` | `self.label` | Same |
| `_value` | `self._value` | `self._value` | Same |
| `attr` | `self.attr = {}` (always dict) | `self.attr = attr or {}` (always dict) | Both always dict |
| `parent` | `self._parentbag` (via property) | `self.parent` (direct) | Renamed, property vs direct |
| `resolver` | `self._resolver` (via property) | `self._resolver` (via property) | Same pattern |
| `locked` | `self.locked = False` | **REMOVED** | Never used |
| `_node_subscribers` | `self._node_subscribers = {}` | `self._node_subscribers = {}` | Same |
| `_validators` | `self._validators = None` | **REMOVED** | Removed |
| `tag` | Via `self.attr.get('tag')` property | `self.tag` (dedicated slot) | NEW: dedicated slot |
| `_invalid_reasons` | **N/A** | `self._invalid_reasons = []` | NEW: validation state |

---

## 4. Properties Comparison

### 4.1 `value` Property

**Original:**
```python
def getValue(self, mode=''):
    if not self._resolver == None:
        if 'static' in mode:
            return self._value
        else:
            if self._resolver.readOnly:
                return self._resolver()
            if self._resolver.expired:
                self.value = self._resolver()
            return self._value
    return self._value

value = property(getValue, setValue)
```

**TreeStore:**
```python
@property
def value(self) -> Any:
    if self._resolver is not None:
        return self._resolver._htraverse()
    return self._value

@value.setter
def value(self, new_value: Any) -> None:
    self.set_value(new_value)
```

| Aspect | Original | TreeStore | Notes |
|--------|----------|-----------|-------|
| `mode` param | Yes (`'static'`) | No | Original has mode |
| Resolver call | `_resolver()` | `_resolver._htraverse()` | Different approach |
| Cache logic | In getValue | In Resolver | TreeStore delegates |

### 4.2 `resolver` Property

**Original:**
```python
def _set_resolver(self, resolver):
    if not resolver is None:
        resolver.parentNode = self
    self._resolver = resolver

resolver = property(_get_resolver, _set_resolver)
```

**TreeStore:**
```python
@resolver.setter
def resolver(self, resolver: TreeStoreResolver | None) -> None:
    if resolver is not None:
        resolver.parent_node = self
    self._resolver = resolver
```

| Aspect | Original | TreeStore | Notes |
|--------|----------|-----------|-------|
| Bidirectional link | Yes | Yes | Same pattern |
| Naming | `parentNode` | `parent_node` | snake_case |

### 4.3 `tag` Property

**Original:**

```python
@property
def tag(self):
    return self.attr.get('tag') or self.label
```

Note: `tag` è una property read-only che legge da `attr['tag']` con fallback a `label`.

**TreeStore:**

```python
# Dedicated slot - settato direttamente in __init__
self.tag = tag
```

Note: `tag` è un attributo diretto (slot), non una property.

| Aspect | Original | TreeStore | Notes |
|--------|----------|-----------|-------|
| Storage | Property da `attr` dict | Dedicated slot | TreeStore cleaner |
| Fallback | `label` if no tag | No fallback (`None`) | Different |
| Writeable | No (property getter) | Sì (attributo) | Different |

### 4.4 Properties Only in Original

```python
@property
def position(self):
    """Index in parent's nodes list"""
    if self.parentbag is not None:
        return [id(n) for n in self.parentbag.nodes].index(id(self))

@property
def fullpath(self):
    """Dot-separated path from root"""
    if not self.parentbag is None:
        fullpath = self.parentbag.fullpath
        if not fullpath is None:
            return '%s.%s' % (fullpath, self.label)

@property
def parentNode(self):
    """Parent node (grandparent's node)"""
    if self.parentbag:
        return self.parentbag.parentNode

staticvalue = property(getStaticValue, setStaticValue)  # mode='static'
```

### 4.5 Properties Only in TreeStore

```python
@property
def is_branch(self) -> bool:
    """True if this node contains a TreeStore (has children)."""
    return isinstance(self._value, TreeStore)

@property
def is_leaf(self) -> bool:
    """True if this node contains a scalar value."""
    return not isinstance(self._value, TreeStore)

@property
def _(self) -> TreeStore:
    """Return parent TreeStore for navigation/chaining."""
    if self.parent is None:
        raise ValueError("Node has no parent")
    return self.parent

@property
def is_valid(self) -> bool:
    """True if this node has no validation errors."""
    return len(self._invalid_reasons) == 0
```

---

## 5. Methods Comparison

### 5.1 setValue / set_value

**Original** (complex, ~50 lines):
```python
def setValue(self, value, trigger=True, _attributes=None, _updattr=None,
             _removeNullAttributes=True, _reason=None):
    if self.locked:
        raise BagNodeException("Locked node %s" % self.label)
    if isinstance(value, BagResolver):
        self.resolver = value
        value = None
    elif isinstance(value, BagNode):
        _attributes = _attributes or {}
        _attributes.update(value.attr)
        value = value._value
    if hasattr(value, 'rootattributes'):
        # ... handle rootattributes
    oldvalue = self._value
    if self._validators:
        self._value = self._validators(value, oldvalue)
    else:
        self._value = value
    # ... trigger logic, backref handling
```

**TreeStore** (simple, ~15 lines):
```python
def set_value(
    self,
    value: Any,
    trigger: bool = True,
    reason: str | None = None,
) -> None:
    oldvalue = self._value
    if value == oldvalue:
        return  # No change
    self._value = value
    if trigger:
        for callback in self._node_subscribers.values():
            callback(node=self, info=oldvalue, evt="upd_value")
        if self.parent is not None:
            self.parent._on_node_changed(self, [self.label], "upd_value", oldvalue, reason)
```

| Aspect | Original | TreeStore | Notes |
|--------|----------|-----------|-------|
| `locked` check | Yes | No | Removed |
| Resolver detection | Yes | No | Handled elsewhere? |
| BagNode value | Yes | No | Special case removed |
| `rootattributes` | Yes | No | Legacy removed |
| Validators | Yes | No | Postponed |
| `_attributes` | Yes | No | Simplified |
| `_updattr` | Yes | No | Simplified |
| `_removeNullAttributes` | Yes | No | Legacy removed |
| Complexity | High | Low | TreeStore wins |

### 5.2 getAttr / get_attr

**Original:**
```python
def getAttr(self, label=None, default=None):
    if not label or label == '#':
        return self.attr
    return self.attr.get(label, default)
```

**TreeStore:**
```python
def get_attr(self, attr: str | None = None, default: Any = None) -> Any:
    if attr is None:
        return self.attr
    return self.attr.get(attr, default)
```

| Aspect | Original | TreeStore | Notes |
|--------|----------|-----------|-------|
| `'#'` special | Yes | No | Legacy syntax |
| Naming | `getAttr` | `get_attr` | snake_case |
| Otherwise | Same | Same | - |

### 5.3 setAttr / set_attr

**Original** (~30 lines):
```python
def setAttr(self, attr=None, trigger=True, _updattr=True,
            _removeNullAttributes=True, **kwargs):
    if not _updattr:
        self.attr.clear()
    # ... complex logic with null removal, triggers
```

**TreeStore** (~20 lines):
```python
def set_attr(
    self,
    _attr: dict[str, Any] | None = None,
    trigger: bool = True,
    reason: str | None = None,
    **kwargs: Any,
) -> None:
    # ... simpler logic
```

| Aspect | Original | TreeStore | Notes |
|--------|----------|-----------|-------|
| `_updattr` | Yes | No | Simplified |
| `_removeNullAttributes` | Yes | No | Legacy removed |
| Null removal | Yes | No | Simplified |
| Complexity | High | Medium | TreeStore cleaner |

### 5.4 Methods Only in Original

```python
def getLabel(self)          # Redundant, just return self.label
def setLabel(self, label)   # Redundant, just self.label = label
def getStaticValue(self)    # mode='static' access
def setStaticValue(self, value)
def resetResolver(self)     # Reset resolver and clear value
def diff(self, other)       # Compare with another node
def getInheritedAttributes(self)  # Walk up tree for attrs
def attributeOwnerNode(self, attrname, **kwargs)  # Find attr owner
def hasAttr(self, label, value)  # Check attr exists with value
def delAttr(self, *attrToDelete)  # Remove attributes
def asTuple(self)           # (label, value, attr, resolver)
def toJson(self, typed=True)  # JSON serialization
def getFormattedValue(...)  # Formatted string output

# Validators
def setValidators(self, validators)
def addValidator(self, validator, parameterString)
def removeValidator(self, validator)
def getValidatorData(self, validator, label, dflt)
```

### 5.5 Methods Only in TreeStore

```python
# None unique - TreeStore is simpler
```

### 5.6 Common Methods

```python
# Both have:
subscribe(subscriber_id, callback)
unsubscribe(subscriber_id)
__repr__()
__eq__()  # Original has __ne__ too
```

---

## 6. Summary: What to Keep/Remove/Add

### KEEP from Original
- `label`, `_value`, `attr`, `_resolver` core attributes
- `_node_subscribers` for subscriptions
- `resolver` property with bidirectional link
- `subscribe` / `unsubscribe`
- `__eq__` (with improvements)
- `position` property (useful)
- `fullpath` property (useful for debugging)

### REMOVE from Original
- `locked` - never used
- `validators` - postpone
- `_removeNullAttributes` - legacy
- `getLabel()` / `setLabel()` - redundant
- `rootattributes` handling - legacy
- `mode='static'` - rethink approach

### ADD from TreeStore
- `__slots__` - memory efficiency
- `tag` as dedicated slot
- `is_branch` / `is_leaf` properties
- Type hints throughout
- `_invalid_reasons` - for validation (optional)

### RETHINK
- `_` property for parent navigation - syntax sugar, worth it?
- `_attributes` fast path - needed for deserialization? (Original has it, TreeStore doesn't)
- `staticvalue` property - how to handle resolver bypass?
- `parent` as property vs direct attribute - TreeStore usa diretto, Original usa property

---

## 7. Proposed New BagNode

```python
class BagNode:
    """Node in a Bag hierarchy with value, attributes, and optional resolver."""

    __slots__ = (
        'label',
        '_value',
        '_attr',
        '_parent_bag',
        '_resolver',
        '_node_subscribers',
        'tag',               # For builder support
        '_invalid_reasons',  # For validation state
    )

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

**Note sulla proposta:**
- `_attributes` fast path RIMOSSO (Decision #6) - non serve, usato in un solo punto del framework
- `_attr` sempre dict (mai None) - come in entrambe le implementazioni
- `tag` e `_invalid_reasons` aggiunti da TreeStore
- `parent_bag` come attributo diretto (da decidere se property)
- API semplificata: un solo percorso di inizializzazione

---

## References

- [original_bagnode.py](original_bagnode.py) - Original code
- [treestore_node.py](treestore_node.py) - TreeStore code
- [01-original_bagnode_spec.md](01-original_bagnode_spec.md) - Original analysis
- [02-bagnode_decisions.md](02-bagnode_decisions.md) - Design decisions
