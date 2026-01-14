# Subscriptions (Reactivity)

Bag provides a subscription system for reacting to changes. When data is modified, registered callbacks are automatically invoked.

## Overview

Three types of events can be subscribed to:

- **update**: When a node's value changes
- **insert**: When a new node is added
- **delete**: When a node is removed

## Basic Usage

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> events = []

>>> def on_change(**kw):
...     node = kw['node']
...     evt = kw['evt']
...     events.append(f"{evt}: {node.label} = {node.value}")

>>> bag.subscribe('watcher', any=on_change)

>>> bag['name'] = 'Alice'
>>> bag['age'] = 30
>>> bag['name'] = 'Bob'  # Update

>>> events
['ins: name = Alice', 'ins: age = 30', 'upd_value: name = Bob']
```

## Subscribe Method

```python
bag.subscribe(
    subscriber_id,      # Unique identifier for this subscription
    update=callback,    # Called on value changes
    insert=callback,    # Called on new nodes
    delete=callback,    # Called on node removal
    any=callback        # Called on all events
)
```

### Callback Signature

Callbacks receive all arguments as keyword arguments (`**kw`):

```python
def callback(**kw):
    node = kw['node']       # The affected BagNode
    pathlist = kw['pathlist']  # List of labels from subscription root
    evt = kw['evt']         # Event type: 'upd_value', 'ins', or 'del'
    ind = kw.get('ind')     # Index position (for insert/delete)
    reason = kw.get('reason')  # Optional reason string
    # For update events, oldvalue is passed via 'info' key
```

## Event Types

### Update Events

Triggered when a node's value changes:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> updates = []

>>> def on_update(**kw):
...     node = kw['node']
...     pathlist = kw['pathlist']
...     path = '.'.join(pathlist)
...     updates.append(f"{path}: {node.value}")

>>> bag.subscribe('tracker', update=on_update)

>>> bag['count'] = 0
>>> bag['count'] = 1
>>> bag['count'] = 2

>>> updates
['count: 1', 'count: 2']
```

### Insert Events

Triggered when new nodes are added:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> inserts = []

>>> def on_insert(**kw):
...     node = kw['node']
...     ind = kw['ind']
...     inserts.append(f"[{ind}] {node.label} = {node.value}")

>>> bag.subscribe('tracker', insert=on_insert)

>>> bag['a'] = 1
>>> bag['b'] = 2

>>> inserts
['[0] a = 1', '[1] b = 2']
```

### Delete Events

Triggered when nodes are removed:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag({'x': 1, 'y': 2, 'z': 3})
>>> deletes = []

>>> def on_delete(**kw):
...     node = kw['node']
...     ind = kw['ind']
...     deletes.append(f"deleted [{ind}]: {node.label}")

>>> bag.subscribe('tracker', delete=on_delete)

>>> del bag['y']

>>> deletes
['deleted [1]: y']
```

## Nested Paths

Subscriptions work with nested structures:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> events = []

>>> def on_any(**kw):
...     node = kw['node']
...     evt = kw['evt']
...     events.append(f"{evt}: {node.label}")

>>> bag.subscribe('watcher', any=on_any)

>>> bag['config.database.host'] = 'localhost'
>>> bag['config.database.port'] = 5432

>>> events
['ins: config', 'ins: database', 'ins: host', 'ins: port']
```

## Multiple Subscribers

Multiple callbacks can subscribe to the same bag:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> log1, log2 = [], []

>>> bag.subscribe('logger1', any=lambda **kw: log1.append(kw['evt']))
>>> bag.subscribe('logger2', any=lambda **kw: log2.append(kw['evt']))

>>> bag['x'] = 1

>>> log1, log2
(['ins'], ['ins'])
```

## Unsubscribing

Remove subscriptions when no longer needed:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> events = []

>>> bag.subscribe('watcher', any=lambda **kw: events.append(kw['evt']))

>>> bag['a'] = 1
>>> events
['ins']

>>> bag.unsubscribe('watcher', any=True)

>>> bag['b'] = 2
>>> events  # No new events
['ins']
```

### Selective Unsubscribe

```python
# Remove only update subscription
bag.unsubscribe('watcher', update=True)

# Remove only insert subscription
bag.unsubscribe('watcher', insert=True)

# Remove only delete subscription
bag.unsubscribe('watcher', delete=True)

# Remove all subscriptions for this ID
bag.unsubscribe('watcher', any=True)
```

## Backref Mode

Subscriptions automatically enable **backref mode**, which:

- Maintains parent references for tree traversal
- Propagates events up the hierarchy
- Enables `node.fullpath` access

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag.subscribe('watcher', any=lambda **kw: None)

>>> # Backref is automatically enabled
>>> bag.backref
True
```

## Practical Examples

### Validation

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()

>>> def validate(**kw):
...     node = kw['node']
...     evt = kw['evt']
...     if evt == 'upd_value' and node.label == 'email':
...         if '@' not in str(node.value):
...             raise ValueError('Invalid email')

>>> bag.subscribe('validator', update=validate)

>>> bag['email'] = 'test@example.com'  # OK

>>> try:
...     bag['email'] = 'invalid'
... except ValueError as e:
...     print(e)
Invalid email
```

### Change Logging

```python
import logging

def log_changes(**kw):
    node = kw['node']
    pathlist = kw['pathlist']
    evt = kw['evt']
    path = '.'.join(pathlist)
    if evt == 'upd_value':
        logging.info(f"Updated {path}: {node.value}")
    elif evt == 'ins':
        logging.info(f"Added {path} = {node.value}")
    elif evt == 'del':
        logging.info(f"Deleted {path}")

bag.subscribe('logger', any=log_changes)
```

### Computed Properties

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag['price'] = 100
>>> bag['quantity'] = 5
>>> bag['total'] = 500

>>> def update_total(**kw):
...     node = kw['node']
...     if node.label in ('price', 'quantity'):
...         parent = node.parent_bag
...         parent['total'] = parent['price'] * parent['quantity']

>>> bag.subscribe('calculator', update=update_total)

>>> bag['price'] = 150
>>> bag['total']
750

>>> bag['quantity'] = 3
>>> bag['total']
450
```

## Best Practices

1. **Use descriptive subscriber IDs**: Makes debugging easier
2. **Unsubscribe when done**: Prevents memory leaks
3. **Keep callbacks fast**: Heavy work should be async
4. **Handle exceptions**: Callback errors can disrupt other subscribers

## Next Steps

- Return to [Basic Usage](basic-usage.md)
- Explore [Query Syntax](query-syntax.md)
- Learn about [Builders](builders/index.md)
