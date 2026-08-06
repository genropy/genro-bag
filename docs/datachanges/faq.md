# Data Changes FAQ

## Scope

### Why doesn't the collector send changes anywhere?

Because routing is not genro-bag's business. The collector answers one
question — *what changed in this Bag since you last asked* — and stops there.
Who receives it, over which transport, with which fan-out, is the consumer's
decision, and every consumer answers it differently: a global store hands out
deltas per reader, a page store applies them to a replica, a websocket rail
ships them to a peer.

Keeping the boundary there is what lets all three share one foundation instead
of carrying a private reduction each.

### Why a plain dict and not a `DataChange` class?

So a change travels on the wire with no code of its own. A dict of scalars
nesting one dict is already carriable: `str`, `bool`, `int` and `datetime` are
in genro-tytx's type registry, and a Bag in `value` travels through the Bag
type registration. A custom class would have needed a datachange-specific
encoder, a wire marker, and a decoder on the other side.

It also removes the need for a partial `__eq__`: coalescing compares
`new['key'] == old['key']` — the dict's own equality, nothing overridden.

One boundary comes with the registry ride: signing cannot reach a Bag
inside a plain value. With `sign_key`, a change whose `value` is a Bag
carrying a resolver is refused by `to_tytx`/`to_json`
(`BagSerializationError`) rather than sent unsigned — see
[serialization](../bag/serialization.md) → *Bags nested in plain values*.
Changes without resolvers in their `value` are unaffected.

### How do I subscribe to a change, instead of polling?

You do not: that is what [subscriptions](../subscriptions/README.md) are for.
The collector exists precisely for the consumers that cannot react at write
time and need to pick up the accumulated delta later.

## Semantics

### Why is a delete not just a change to None?

Because they are different states. A node set to None exists and holds None; a
deleted node is gone. A consumer applying the change to a replica must be able
to tell them apart, so a delete carries `delete=True` and the replica removes
the node.

### Why is `delete` outside `key`?

So a delete coalesces over a previous set on the same path. If `delete`
discriminated, "set x, then delete x" would ship as two changes and a consumer
would have to reason about their order. With `delete` outside, the removal is
the only survivor — which is what actually happened.

### Why are `attributes` outside `key` too?

Merging fuses them. If `attributes` discriminated, two writes to the same path
carrying different attributes would never coalesce, and there would be nothing
left to fuse.

### What is `fired`?

It marks a one-shot event change rather than a state change. The plain capture
rail never produces one: `set_item(..., _fired=True)` resets the node value
with `trigger=False` after the write, so the callback only ever sees an
ordinary set. Locally captured changes therefore always carry `fired=False`; a
consumer forwarding a fire event supplies `fired=True` on the change it
appends.

### Does capture trigger my resolvers?

No. `value` is the node's **static** value, so a collector attached to a Bag
full of resolvers never causes a fetch. `attributes` is the node's full
attribute dict at capture time — not the diff — so a change is directly
applicable to a replica.

## Transactions

### Are writes inside `Bag.transaction()` captured?

Yes. They have to be handled separately, though: inside a transaction the
three triggers append the mutation to the transaction list and return, with no
dispatch to plain subscribers and no parent bubble. A collector listening only
on the plain rail would silently lose every transactional write.

So the collector subscribes **both** rails and deposits transaction mutations
through the same constructor the plain rail uses — transaction-born and
plain-rail changes are indistinguishable downstream.

### Do transaction events bubble to a parent Bag?

No, and this is visible: a collector attached to a child Bag sees nothing from
a transaction opened on the root. Only a collector on the transaction's own Bag
captures them. Plain writes bubble normally.

## Operations

### Two consumers on one Bag — do they interfere?

No. Each collector has its own subscriber id and its own pending list, so
draining one leaves the other's pending untouched, and detaching one does not
stop the other. Attach one collector per consumer.

### Is it thread-safe?

No — the collector inherits the Bag's threading model and takes no locks of its
own. genro-bag is not thread-safe by design.

### What does `change_idx` mean?

A per-collector monotonic counter, assigned on every deposit. `drain()` returns
the changes ordered by it. A coalesced change gets a **new** index and goes to
the tail, so drain order reflects when the last write happened.

### How do prefixes match?

On segment boundaries, both in capture (`paths=`) and in `drop(prefix)`. The
prefix `a.b` captures `a.b` and `a.b.c`, never `a.bc`.
