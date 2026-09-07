# Architecture

## Where the Layer Sits

`BagEvents` is the lower half: it dispatches an event the moment a write
happens. `DataChangeCollector` is the upper half: it turns that stream into an
accumulated, drainable delta. The consumer sits above both and decides where
the delta goes.

```{mermaid}
flowchart TB
    W["bag['user.name'] = 'Ada'"] --> T[Bag triggers]
    T --> P[plain rail]
    T --> X[transaction list]
    X -->|commit| TR[transaction rail]
    P --> C[DataChangeCollector]
    TR --> C
    C --> L[pending changes]
    L -->|drain| CO[consumer: store / page / socket]
```

## The Two Capture Rails

A write reaches the collector by one of two routes, never both.

**Plain rail** — outside a transaction, the `ins` / `upd` / `del` triggers
dispatch immediately to every subscriber and bubble up to the parent Bags. The
collector subscribes with `update=`, `insert=` and `delete=` separately rather
than `any=`, so the three cases stay readable, and the pathlist it receives is
already absolute with respect to the observed Bag.

**Transaction rail** — inside `Bag.transaction()` the same three triggers
append the mutation to the transaction list and return. There is no dispatch
and no bubble, so a collector on the plain rail alone would lose every
transactional write. The collector therefore also subscribes `transaction=`,
receives the mutations at commit, and walks them in order.

Transaction mutations arrive as positional tuples whose shape depends on the
kind — `("upd", node, pathlist, evt, oldvalue, attrs_diff, reason)` with seven
elements, `("ins", …)` and `("del", …)` with five — so dispatch is on element
zero.

Their `pathlist` is **local to the Bag whose trigger fired**, not absolute:
nothing bubbles inside a transaction, so no parent ever prepends its label.
The collector rebuilds the path by walking the node's backref chain up to the
observed Bag, which yields exactly what the plain rail would have reported for
the same write. The chain survives deletion, so a `del` inside a transaction
reports its full path too.

Both rails end in the same private constructor and the same deposit step:
transaction-born and plain-rail changes are indistinguishable downstream.

## Never Return False

A subscriber that returns `False` stops propagation to every other subscriber
of that Bag. The collector's callbacks therefore never return `False` — if they
did, dict iteration order would decide which other subscribers saw the event.

## Coalescing

Identity is the `key` sub-dict: `path`, `reason`, `fired`. Two changes coalesce
when those three compare equal — plain dict equality, no custom `__eq__`
anywhere.

```{mermaid}
flowchart LR
    A["append(change, replace=True)"] --> B{"pending change<br/>with equal key?"}
    B -->|yes| C[remove it]
    B -->|no| D[keep list as is]
    C --> E["deposit: new change_idx, appended at the tail"]
    D --> E
```

`delete` and `attributes` sit outside the key on purpose: `delete` so a removal
coalesces over a previous set on the same path and only the removal survives;
`attributes` so changes to one path can coalesce even when their metadata
differs. The latest change replaces the previous one in full. Its attributes
represent the complete state, so an attribute absent from the latest change
is not carried over from an earlier one.

The coalesced change gets a **new** `change_idx` and moves to the tail, so
drain order reflects when the last write happened.

## One Collector Per Consumer

The subscriber id is derived from `id(self)`, so any number of collectors
coexist on one Bag, each holding its own pending list and its own
`change_idx` sequence.

```{mermaid}
flowchart TB
    B[Bag] --> C1["collector A<br/>(page 1)"]
    B --> C2["collector B<br/>(page 2)"]
    B --> C3["collector C<br/>(websocket)"]
    C1 --> D1[own pending list]
    C2 --> D2[own pending list]
    C3 --> D3[own pending list]
```

This replaces the legacy design where one shared change list served many
readers and each reader tracked a private offset into it. Draining is
destructive and local: no offsets, no shared cursor, no reader able to consume
another's changes.

## Why the Change Is a Dict

A change must survive `to_tytx` and `to_json` with **no datachange-specific
serialization code**. A dict of scalars nesting one dict already does: the
scalar types are in genro-tytx's registry, and a Bag in `value` travels through
the Bag type registration (suffix `X`). That is infrastructure the layer reuses,
not code it owns.

A class would have required its own wire marker, encoder and decoder, plus a
partial `__eq__` for coalescing. The dict gets both for free.
