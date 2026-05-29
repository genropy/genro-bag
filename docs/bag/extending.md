# Extending Bag and BagNode

`Bag` and `BagNode` are designed to be extended. You can subclass them, mix in additional behavior, and the core machinery will preserve your custom types automatically — intermediate nodes, copies, and deserialized bags all stay in your subclass.

This page explains **why** you would extend them, **how** the extension mechanism works, and the trade-offs of mixin ordering.

## Why extend?

Extending `Bag` / `BagNode` is useful when you want to:

- **Add domain methods directly on the bag.** A `ConfigBag` can expose `validate()`, `apply_defaults()`, etc. instead of forcing callers to use external helpers.
- **Add per-instance state that travels with the bag.** Caches, source metadata, lifecycle hooks.
- **Customize the node type.** A `TaggedBagNode` can carry extra fields, custom `__repr__`, computed properties.
- **Keep the whole tree consistent.** If the root is a `ConfigBag`, intermediate sub-bags created on path assignment are also `ConfigBag`, and their nodes are `TaggedBagNode`. No manual reconstruction needed.
- **Share behavior via mixins.** The same mixin can be combined with different base subclasses without rewriting it.

## How extension works

The core never instantiates `Bag()` or `BagNode()` directly when replicating structure. It uses polymorphic patterns:

- Instance methods that need a new bag use `self.__class__()` (e.g. when `bag['a.b.c'] = v` creates intermediate nodes, or during `deepcopy`).
- `@classmethod` deserializers (`from_xml`, `from_json`, `from_tytx`) use `cls()`.
- Nodes are instantiated via `parent_bag._node_class(...)`, where `_node_class` is a class attribute on `Bag` (default: `BagNode`). The leading underscore marks it as internal infrastructure: subclasses set it explicitly to inject a custom node factory, but user code never reads or writes it.

This means subclassing alone is enough to make your custom type propagate everywhere. You just need to respect two constraints:

1. **Constructors must be callable with zero arguments.** `self.__class__()` passes nothing, so all init parameters must have defaults.
2. **`BagNode.__init__` signature must be preserved.** A custom node is instantiated with `(parent_bag, label, value, attr, resolver, node_tag, xml_tag, _remove_null_attributes)`. Add new state, but don't change this signature.

## Extending with mixins — the basics

A mixin is a plain class that contributes methods or attributes. It is not meant to be instantiated alone.

```python
from genro_bag import Bag
from genro_bag.bagnode import BagNode


class _ConfigMixin:
    """Add new methods only; do not override Bag internals."""
    def apply_defaults(self, defaults: dict) -> None:
        for key, value in defaults.items():
            self.setdefault(key, value)


class _TaggedNodeMixin:
    """Add new methods only; do not override BagNode internals."""
    def is_tagged(self, tag: str) -> bool:
        return self.node_tag == tag


class TaggedBagNode(BagNode, _TaggedNodeMixin):
    pass


class ConfigBag(Bag, _ConfigMixin):
    _node_class = TaggedBagNode
```

Use it normally:

```python
cfg = ConfigBag()
cfg['db.host'] = 'localhost'

assert isinstance(cfg, ConfigBag)
assert isinstance(cfg['db'], ConfigBag)            # intermediate sub-bag
assert type(cfg.get_node('db')) is TaggedBagNode    # node uses class attribute
cfg.apply_defaults({'db.port': 5432})              # mixin method available
```

## Mixin order: left vs right

In Python, classes listed earlier in the parent list come first in the MRO and win when resolving attribute/method names. This matters when an attribute could come from multiple places.

### Mixin on the right — the safe default

```python
class ConfigBag(Bag, _ConfigMixin):    # Bag first, mixin second
    ...
```

- The mixin **cannot** override anything that exists in `Bag`. If `_ConfigMixin` accidentally defined a method named `clear` or `setdefault`, `Bag`'s version would still win.
- The mixin only adds new names (`apply_defaults`, `validate`, …).
- Recommended for the common case: you just want extra functionality, not to change how `Bag` already works.

### Mixin on the left — only when override is intentional

```python
class ConfigBag(_ConfigMixin, Bag):    # mixin first, Bag second
    ...
```

- The mixin **can** override methods and attributes of `Bag`.
- Use this only when the override is a deliberate design choice — for example, a reusable mixin that carries a default `_node_class` you want to apply across multiple subclasses.
- Risk: any name clash, even unintentional, will silently shadow `Bag` behavior.

### Quick comparison

| Concern | Mixin on the right | Mixin on the left |
|---|---|---|
| Can override `Bag` methods | No | Yes |
| Safe against accidental name clashes | Yes | No |
| Right choice for "add helpers" | ✓ | ✗ |
| Right choice for "the mixin owns a default like `_node_class`" | ✗ | ✓ |

## When you only need a custom node factory

If the only thing you want to change is the node type — no extra methods on the bag, no mixins — declare `_node_class` directly on the subclass:

```python
class TaggedBag(Bag):
    _node_class = TaggedBagNode
```

That's it. No mixins, no MRO concerns. `TaggedBag._node_class` resolves to `TaggedBagNode` because the subclass itself is always before `Bag` in the MRO, regardless of any other parents.

The same applies when you combine a "right-side" mixin with a node override:

```python
class ConfigBag(Bag, _ConfigMixin):
    _node_class = TaggedBagNode      # explicit, single line
```

The override is visible at a glance when reading `ConfigBag`, and the mixin stays harmless because it cannot reach the `_node_class` slot ahead of the subclass itself.

## Mixins with `__init__`

If a mixin needs initialization, it must cooperate via `super()`:

```python
class _CachingMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cache: dict = {}


class CachedBag(Bag, _CachingMixin):
    pass
```

`super().__init__(*args, **kwargs)` keeps the constructor chain intact. Remember the zero-argument rule: `CachedBag()` must remain callable with no arguments, so any new parameter introduced by the mixin needs a default.

## Decision guide

| What you want | What to do |
|---|---|
| Only add helper methods to the bag | Mixin on the right, no `_node_class` override |
| Only change the node type | `_node_class = MyNode` directly on the subclass |
| Add helpers **and** custom nodes | Mixin on the right + `_node_class` override on the subclass |
| Mixin must impose a shared default (e.g. its own `_node_class`) | Mixin on the left, deliberately |
| Per-instance state | Mixin with `__init__` calling `super().__init__(*args, **kwargs)` |

## Full verification example

```python
import copy
from genro_bag import Bag
from genro_bag.bagnode import BagNode


class _ConfigMixin:
    def apply_defaults(self, defaults: dict) -> None:
        for key, value in defaults.items():
            self.setdefault(key, value)


class _TaggedNodeMixin:
    def is_tagged(self, tag: str) -> bool:
        return self.node_tag == tag


class TaggedBagNode(BagNode, _TaggedNodeMixin):
    pass


class ConfigBag(Bag, _ConfigMixin):
    _node_class = TaggedBagNode


cfg = ConfigBag()
cfg['db.host'] = 'localhost'
cfg['db.port'] = 5432

# Custom bag class propagates to intermediate sub-bags
assert isinstance(cfg['db'], ConfigBag)

# Custom node class is used for every node
assert type(cfg.get_node('db')) is TaggedBagNode
assert type(cfg['db'].get_node('host')) is TaggedBagNode

# Mixin methods are available on bag and node
cfg.apply_defaults({'db.timeout': 30})
assert cfg.get_node('db').is_tagged('config') is False

# Deepcopy preserves the custom types
cfg2 = copy.deepcopy(cfg)
assert isinstance(cfg2, ConfigBag)
assert type(cfg2.get_node('db')) is TaggedBagNode
```
