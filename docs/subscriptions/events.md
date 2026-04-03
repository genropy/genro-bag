# Subscription Events

Detailed guide to event types and their callback data.

## Insert Events (`ins`)

Triggered when a new node is added to the Bag.

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

### Callback Data

| Key | Description |
|-----|-------------|
| `node` | The new BagNode |
| `evt` | Always `'ins'` |
| `ind` | Index position where inserted |
| `pathlist` | Path from subscription root |

## Update Events (`upd_value`)

Triggered when an existing node's value changes.

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

**Note:** The first assignment triggers `ins`, not `upd_value`.

### Callback Data

| Key | Description |
|-----|-------------|
| `node` | The modified BagNode |
| `evt` | Always `'upd_value'` |
| `pathlist` | Path from subscription root |
| `info` | May contain `oldvalue` |

## Delete Events (`del`)

Triggered when a node is removed.

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

### Callback Data

| Key | Description |
|-----|-------------|
| `node` | The removed BagNode |
| `evt` | Always `'del'` |
| `ind` | Index position before removal |
| `pathlist` | Path from subscription root |

## The `any` Handler

Subscribe to all event types with a single callback:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> events = []

>>> def on_any(**kw):
...     evt = kw['evt']
...     node = kw['node']
...     events.append(f"{evt}: {node.label}")

>>> bag.subscribe('tracker', any=on_any)

>>> bag['x'] = 1      # ins
>>> bag['x'] = 2      # upd_value
>>> del bag['x']      # del

>>> events
['ins: x', 'upd_value: x', 'del: x']
```

## Nested Path Events

Changes to nested paths emit events for each level:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> events = []

>>> def on_any(**kw):
...     events.append(kw['node'].label)

>>> bag.subscribe('w', any=on_any)

>>> bag['config.database.host'] = 'localhost'
>>> events
['config', 'database', 'host']
```

## Pathlist

The `pathlist` shows the path from the subscription point:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> paths = []

>>> def track_path(**kw):
...     path = '.'.join(kw['pathlist'])
...     if path:  # Skip empty root
...         paths.append(path)

>>> bag.subscribe('tracker', any=track_path)

>>> bag['a.b.c'] = 1

>>> paths
['a', 'a.b']
```

Note: Events fire for each intermediate bag created.

## Combining Handlers

You can set different callbacks for different events:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> log = []

>>> bag.subscribe('audit',
...     insert=lambda **kw: log.append(f"ADD: {kw['node'].label}"),
...     update=lambda **kw: log.append(f"MOD: {kw['node'].label}"),
...     delete=lambda **kw: log.append(f"DEL: {kw['node'].label}")
... )

>>> bag['x'] = 1
>>> bag['x'] = 2
>>> del bag['x']

>>> log
['ADD: x', 'MOD: x', 'DEL: x']
```

## Timer Events (`tmr`)

Triggered periodically on a time interval. Unlike other events, timer events
are not caused by data changes — they fire on a schedule.

```python
from genro_bag import Bag

bag = Bag()
events = []

def on_tick(**kw):
    events.append(f"tick on {kw['subscriber_id']}")

bag.subscribe('poller', timer=on_tick, interval=5)

# After 5 seconds: events == ['tick on poller']
# After 10 seconds: events == ['tick on poller', 'tick on poller']

bag.unsubscribe('poller', timer=True)  # Stop the timer
```

### Callback Data

| Key | Description |
|-----|-------------|
| `bag` | The Bag where the timer subscription is registered |
| `evt` | Always `'tmr'` |
| `subscriber_id` | The subscription ID |

### Important Notes

- `any=callback` does **not** include timer events — use `timer=callback` explicitly
- `interval` is required when `timer` is set (raises `ValueError` otherwise)
- `unsubscribe(..., any=True)` cancels timers too
- Timer events propagate to parent bags like other events

## Stop Propagation

Any callback (ins, upd, del, tmr) can return `False` to stop event
propagation to parent bags:

```python
from genro_bag import Bag

root = Bag()
root['child'] = Bag()

root_events = []

def stop_here(**kw):
    # Handle locally, don't propagate
    return False

root.subscribe('root_sub', update=lambda **kw: root_events.append(1))
root['child'].subscribe('child_sub', update=stop_here)

root['child']['x'] = 1
root['child']['x'] = 2  # root_events is still empty
```

Callbacks that return `None` (the default) do **not** stop propagation —
this is fully backwards-compatible.

## Fired Events (`_fired`)

The `_fired` parameter on `set_item` creates event-like signals: set a value
to trigger subscribers, then immediately reset it to `None` without firing
again. Similar to GenroPy's `fireItem`.

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> events = []

>>> bag.subscribe('w', insert=lambda **kw: events.append(kw['node'].value))

>>> bag.set_item('click', 'button_ok', _fired=True)

>>> events
['button_ok']

>>> bag['click'] is None
True
```

The sequence is:

1. `set_item('click', 'button_ok')` — creates the node, fires `ins` event
2. Subscribers see `node.value == 'button_ok'`
3. Value is immediately reset to `None` with `trigger=False` (no second event)

This is useful for signaling events through the subscription system without
leaving stale values in the tree.

## Event Order

Events fire in order of operation:

1. Insert fires immediately when node is created
2. Update fires immediately when value changes
3. Delete fires immediately when node is removed
4. Timer fires periodically on the configured interval

Nested operations fire in depth order (parent first, then children).
