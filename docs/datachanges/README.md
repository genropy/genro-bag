# Data Changes

Know what changed in a Bag since it was last drained.

Subscriptions tell you about a change *at the moment it happens*. A data change
collector accumulates those changes, so a consumer can pick them up later, in
its own rhythm — and get exactly the writes it missed, no more.

## When Do You Need a Collector?

- **A global store** that hands each reader the deltas it has not seen yet
- **A page store** kept in sync with a server-side Bag
- **A push rail** (websocket, SSE) that ships changes to a remote replica

All three need the same thing: *what changed, in order, once*. That is the
collector's whole job. Where the changes go — which page, which socket, which
peer — is the consumer's decision: genro-bag knows what changed, never whom to
tell.

## Quick Start

```{doctest}
>>> from genro_bag import Bag, DataChangeCollector

>>> bag = Bag()
>>> collector = DataChangeCollector(bag)

>>> bag['user.name'] = 'Ada'
>>> bag['user.role'] = 'admin'
>>> collector.pending
3

>>> changes = collector.drain()
>>> [c['key']['path'] for c in changes]
['user', 'user.name', 'user.role']
>>> collector.pending
0
```

`drain()` empties the pending list: the next call returns only what happened
since. Setting `user.name` created the intermediate `user` node too, and that
insertion is a change like any other.

## A Change Is a Plain Dict

```python
{
    "key": {"path": str, "reason": str | None, "fired": bool},
    "value": Any,
    "attributes": dict | None,
    "delete": bool,
    "change_ts": datetime,
    "change_idx": int,
}
```

No class, no custom `__eq__`. A dict of scalars nesting one dict travels
through `to_tytx` and `to_json` with **no datachange-specific serialization
code** — a Bag in `value` included. That is why it is a dict.

`key` holds exactly the three fields that decide identity: two changes coalesce
when their `key` dicts compare equal.

## Restricting to Paths

A collector with no `paths` captures every write. Pass prefixes to narrow it:

```{doctest}
>>> from genro_bag import Bag, DataChangeCollector

>>> bag = Bag()
>>> collector = DataChangeCollector(bag, paths={'user'})

>>> bag['user.name'] = 'Ada'
>>> bag['system.load'] = 0.4
>>> [c['key']['path'] for c in collector.drain()]
['user', 'user.name']
```

Prefixes match on segment boundaries: `user` captures `user.name`, never
`username`. `subscribe_path()` and `unsubscribe_path()` widen and narrow the
set at runtime.

## Many Collectors, One Bag

Each collector owns its pending list, so one Bag can serve several consumers
without any of them stepping on another's changes — draining one leaves the
others untouched. Attach one collector per consumer and forget about offsets.

## Next Steps

| Page | Content |
|------|---------|
| [Examples](examples.md) | Attach/drain loops, forwarding, delete propagation |
| [FAQ](faq.md) | Routing, deletes, transactions |
| [Architecture](architecture.md) | The two capture rails, coalescing |
