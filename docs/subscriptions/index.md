# Subscriptions (Reactivity)

React to changes in Bag data. When values are modified, your callbacks are automatically invoked.

## When Do You Need Subscriptions?

You need subscriptions when:

- **Validation**: Check constraints when data changes
- **Logging**: Audit trail of modifications
- **Computed properties**: Update dependent values automatically
- **UI synchronization**: React to model changes
- **Side effects**: Trigger actions on data changes

## The Core Idea

Without subscriptions:
```python
bag['count'] = 1
# ... somewhere else in code
# How do you know 'count' changed?
```

With subscriptions:
```python
def on_change(**kw):
    print(f"Changed: {kw['node'].label}")

bag.subscribe('watcher', any=on_change)
bag['count'] = 1  # Prints: "Changed: count"
```

## Quick Example

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> events = []

>>> def on_change(**kw):
...     node = kw['node']
...     evt = kw['evt']
...     events.append(f"{evt}: {node.label}")

>>> bag.subscribe('watcher', any=on_change)

>>> bag['name'] = 'Alice'
>>> bag['name'] = 'Bob'

>>> events
['ins: name', 'upd_value: name']
```

## Event Types

| Event | Triggered When |
|-------|----------------|
| `ins` | New node added |
| `upd_value` | Node value changed |
| `del` | Node removed |

## Subscribing

```python
bag.subscribe(
    'my_subscriber',     # Unique ID
    insert=callback,     # Called on new nodes
    update=callback,     # Called on value changes
    delete=callback,     # Called on removal
    any=callback         # Called on all events
)
```

## Callback Signature

```python
def callback(**kw):
    node = kw['node']       # The affected BagNode
    evt = kw['evt']         # Event type: 'ins', 'upd_value', 'del'
    pathlist = kw['pathlist']  # Path from subscription root
    ind = kw.get('ind')     # Index position
```

## Unsubscribing

```python
# Remove specific subscription type
bag.unsubscribe('my_subscriber', update=True)

# Remove all subscriptions for this ID
bag.unsubscribe('my_subscriber', any=True)
```

## Key Features

### Nested Paths

Subscriptions work with hierarchical changes:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> events = []
>>> bag.subscribe('w', any=lambda **kw: events.append(kw['node'].label))

>>> bag['config.database.host'] = 'localhost'
>>> events
['config', 'database', 'host']
```

### Multiple Subscribers

```python
bag.subscribe('logger', any=log_changes)
bag.subscribe('validator', update=validate)
bag.subscribe('sync', any=sync_to_server)
```

### Backref Mode

Subscriptions automatically enable parent references:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag.subscribe('w', any=lambda **kw: None)
>>> bag.backref
True
```

## What's Next?

```{toctree}
:maxdepth: 1

events
examples
faq
```
