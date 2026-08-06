# Data Change Examples

Practical patterns for capturing and consuming changes.

## The Attach / Drain Loop

The basic shape: a producer writes, a consumer drains whenever it is ready.

```{doctest}
>>> from genro_bag import Bag, DataChangeCollector

>>> store = Bag()
>>> collector = DataChangeCollector(store)

>>> # ... the producer writes, over time ...
>>> store['order.total'] = 100
>>> store['order.status'] = 'draft'

>>> # ... the consumer wakes up ...
>>> for change in collector.drain():
...     print(change['key']['path'], '->', type(change['value']).__name__)
order -> Bag
order.total -> int
order.status -> str

>>> # nothing new since
>>> collector.drain()
[]
```

Replace the `print` with "apply to a replica" and you have a synchronizer.

## Peeking Without Consuming

`drain(reset=False)` reads the pending list without emptying it — useful to
decide whether it is worth sending anything at all.

```{doctest}
>>> from genro_bag import Bag, DataChangeCollector

>>> bag = Bag()
>>> collector = DataChangeCollector(bag)
>>> bag['a'] = 1

>>> len(collector.drain(reset=False))
1
>>> collector.pending
1
```

## Delete Propagation

A delete is a change with `delete=True`. It says *the node is gone* — a
consumer applying it to a replica must remove the node, not set it to None.

```{doctest}
>>> from genro_bag import Bag, DataChangeCollector

>>> bag = Bag()
>>> bag['user.name'] = 'Ada'
>>> collector = DataChangeCollector(bag)

>>> del bag['user.name']
>>> change = collector.drain()[0]
>>> change['key']['path'], change['delete']
('user.name', True)
```

Applying it to a replica reads naturally:

```python
for change in collector.drain():
    if change['delete']:
        del replica[change['key']['path']]
    else:
        replica.set_item(change['key']['path'], change['value'],
                         **(change['attributes'] or {}))
```

## Writes Inside a Transaction

`Bag.transaction()` batches mutations and dispatches them at commit. The
collector captures them anyway, in order — a write never escapes capture
because it happened inside a transaction.

```{doctest}
>>> from genro_bag import Bag, DataChangeCollector

>>> bag = Bag()
>>> collector = DataChangeCollector(bag)

>>> with bag.transaction():
...     bag['a'] = 1
...     bag['b'] = 2
...     bag['c'] = 3

>>> [c['key']['path'] for c in collector.drain()]
['a', 'b', 'c']
```

## Forwarding a Change

`append()` deposits a change that was not born from a local write — one
received from another collector, or a fire event a consumer is relaying.

```{doctest}
>>> from genro_bag import Bag, DataChangeCollector

>>> source, target = Bag(), Bag()
>>> upstream = DataChangeCollector(source)
>>> downstream = DataChangeCollector(target)

>>> source['a'] = 1
>>> for change in upstream.drain():
...     downstream.append(change)
>>> [c['key']['path'] for c in downstream.drain()]
['a']
```

## Coalescing Repeated Writes

With `replace=True`, a change replaces the pending one carrying an equal `key`,
so a path written ten times ships once — with the last value, at the tail of
the drain order.

```{doctest}
>>> from genro_bag import Bag, DataChangeCollector

>>> bag = Bag()
>>> collector = DataChangeCollector(bag)
>>> bag['x'] = 0
>>> collector.reset()

>>> for i in range(10):
...     bag['x'] = i
...     for change in collector.drain():
...         pass
...     collector.append(change, replace=True)

>>> changes = collector.drain()
>>> len(changes), changes[0]['value']
(1, 9)
```

## Restricting and Discarding by Prefix

`drop(prefix)` throws away the pending changes under one subtree — for a
consumer that no longer cares about that branch.

```{doctest}
>>> from genro_bag import Bag, DataChangeCollector

>>> bag = Bag()
>>> collector = DataChangeCollector(bag)
>>> bag['a.x'] = 1
>>> bag['b.y'] = 2

>>> collector.drop('a')
>>> [c['key']['path'] for c in collector.drain()]
['b', 'b.y']
```

## Detaching

`detach()` unsubscribes the collector from both rails; anything already pending
stays readable.

```{doctest}
>>> from genro_bag import Bag, DataChangeCollector

>>> bag = Bag()
>>> collector = DataChangeCollector(bag)
>>> bag['a'] = 1
>>> collector.detach()

>>> bag['b'] = 2          # no longer captured
>>> [c['key']['path'] for c in collector.drain()]
['a']
```
