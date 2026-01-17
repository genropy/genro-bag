# Subscriptions FAQ

## Basic Questions

### When do callbacks fire?

Immediately when the operation occurs:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> fired = []
>>> bag.subscribe('w', any=lambda **kw: fired.append(kw['evt']))

>>> bag['x'] = 1
>>> fired  # Already fired
['ins']
```

### Can I have multiple subscribers?

Yes, each with a unique ID:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag.subscribe('logger', any=lambda **kw: None)
>>> bag.subscribe('validator', any=lambda **kw: None)
>>> bag.subscribe('sync', any=lambda **kw: None)
```

### What if a callback raises an exception?

The exception propagates and may prevent other subscribers from running:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()

>>> def failing(**kw):
...     raise ValueError("Failed!")

>>> bag.subscribe('failing', any=failing)

>>> try:
...     bag['x'] = 1
... except ValueError:
...     pass  # Exception propagated
```

**Best practice**: Catch exceptions in your callbacks if you want resilience.

### How do I stop receiving events?

Unsubscribe:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> events = []
>>> bag.subscribe('w', any=lambda **kw: events.append(1))

>>> bag['a'] = 1
>>> len(events)
1

>>> bag.unsubscribe('w', any=True)

>>> bag['b'] = 2
>>> len(events)  # No new events
1
```

## Event Behavior

### Why doesn't first assignment trigger `upd_value`?

First assignment creates the node (`ins`). Only subsequent assignments trigger `upd_value`:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> events = []
>>> bag.subscribe('w', any=lambda **kw: events.append(kw['evt']))

>>> bag['x'] = 1  # ins (creation)
>>> bag['x'] = 2  # upd_value (modification)

>>> events
['ins', 'upd_value']
```

### Why do I get multiple events for nested paths?

Each intermediate Bag is created:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> events = []
>>> bag.subscribe('w', any=lambda **kw: events.append(kw['node'].label))

>>> bag['a.b.c'] = 1
>>> events
['a', 'b', 'c']
```

### Can I prevent event firing temporarily?

No built-in mechanism. Workarounds:

1. Unsubscribe/resubscribe
2. Use a flag in your callback
3. Batch changes and subscribe after

## Performance

### Are subscriptions slow?

Each subscription adds overhead. For high-frequency updates:
- Keep callbacks fast
- Consider batching
- Use selective event types (not `any`)

### How many subscribers is too many?

Depends on callback complexity. Hundreds of simple callbacks are fine. Avoid heavy computation in callbacks.

### Can I batch changes?

No built-in batching. Pattern:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()

>>> # Unsubscribe for bulk load
>>> # ... do bulk operations ...
>>> # Resubscribe
```

## Backref Mode

### What is backref mode?

When subscriptions are active, nodes maintain parent references:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag.subscribe('w', any=lambda **kw: None)

>>> bag.backref
True

>>> bag['a.b'] = 1
>>> node = bag.get_node('a.b')
>>> node.parent_bag is bag['a']
True
```

### Why does subscribing enable backref?

To support `pathlist` in callbacks and allow traversing up the tree.

### Can I disable backref?

Unsubscribe all subscribers:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag.subscribe('w', any=lambda **kw: None)
>>> bag.backref
True

>>> bag.unsubscribe('w', any=True)
>>> # backref may still be True until explicitly disabled
```

## Common Mistakes

### Modifying the Bag in a callback

This can cause recursive events:

```python
# CAREFUL - this may loop!
def on_change(**kw):
    bag['counter'] = bag['counter'] + 1  # Triggers another event!

bag.subscribe('counter', update=on_change)
```

**Solution**: Check the node label or use guards:

```python
def on_change(**kw):
    if kw['node'].label != 'counter':
        bag['counter'] = bag['counter'] + 1
```

### Forgetting to unsubscribe

Can cause memory leaks and unexpected behavior:

```python
# Object deleted but callback still holds reference
del my_object
# Callback may still fire and fail
```

**Solution**: Always unsubscribe when done.

### Using mutable state in callbacks

```python
# WRONG - shared mutable state
results = []
bag.subscribe('w', any=lambda **kw: results.append(kw))
# results keeps growing forever
```
