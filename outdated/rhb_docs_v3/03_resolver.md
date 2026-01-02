# Resolver — Dynamic Value Computation

A **Resolver** is an object attached to a BagNode that is responsible for computing its value.
It supports both **synchronous** and **asynchronous** computation and optional caching.

## Resolver Fields

Conceptually, a Resolver can be defined as:

```text
Resolver {
    fn: callable          # sync or async implementation
    cachetime: int        # 0, -1 or seconds
    last_value: any       # cached value if available
    expires_at: float|None  # timestamp (e.g. epoch seconds) or None
}
```

## Caching Semantics

- `cachetime = 0` → **no cache**
  - resolver is called every time the node is read;
  - in this mode the resolver must be **synchronous**.
- `cachetime = -1` → **infinite cache**
  - first computation populates the cache;
  - value is reused until explicit invalidation.
- `cachetime = N` (N > 0) → cache valid for N seconds
  - value is recomputed when expired or invalidated.

## Return Types

The resolver function `fn` can return:

- just a `value`
- or `(value, attributes)` as a tuple

In both cases:

- `value` becomes the new node value,
- `attributes` (if provided) are merged into the node’s attributes,
- appropriate triggers are fired.

## Sync vs Async

### Synchronous Resolver

A sync resolver is called directly during a read if there is no valid cache.

**Python example:**

```python
import time

def time_resolver(node):
    # returns current time as value
    return time.time()

node.resolver = Resolver(fn=time_resolver, cachetime=0)
```

### Asynchronous Resolver

An async resolver does *not* return the value to the caller immediately.  
Instead, it writes the result into a Bag path upon completion.

Conceptually:

```python
async def fetch_data(node, target_path):
    data = await http_get("https://example.com/data")
    # target_path may be this node or some other node
    node.parent_bag.setItem(target_path, data)
```

The key idea is:

- the caller may trigger the async resolver,
- when the result eventually arrives, `setItem` / `setValue` is used,
- this automatically fires all relevant triggers.

## Cache Invalidation

A node’s resolver cache can be invalidated externally, e.g.:

```python
node.invalidate_cache()
```

After invalidation:

- the next read will recompute the value (sync),
- or re‑launch the async process as defined by the system.

## Trigger Integration

Whether sync or async, when the resolver produces a new value:

1. the node’s value (and possibly attributes) are updated;
2. local node triggers fire;
3. the Bag trigger chain fires (update events);
4. propagation continues up to the root Bag.

## Example: Sync Resolver in Python

```python
class Resolver:
    def __init__(self, fn, cachetime=0):
        self.fn = fn
        self.cachetime = cachetime
        self.last_value = None
        self.expires_at = None

    def resolve(self, node):
        import time
        now = time.time()
        if self.cachetime != 0 and self.expires_at is not None and now < self.expires_at:
            return self.last_value

        result = self.fn(node)
        if isinstance(result, tuple):
            value, attrs = result
        else:
            value, attrs = result, None

        if self.cachetime != 0:
            self.last_value = (value, attrs)
            self.expires_at = None if self.cachetime == -1 else now + self.cachetime

        return value, attrs
```

For triggers and propagation, see `04_triggerlist_and_triggers.md`.
