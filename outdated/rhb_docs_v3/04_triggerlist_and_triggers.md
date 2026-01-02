# TriggerList and Triggers — Reactive Engine

The **TriggerList** is the structure that manages triggers for both Bags and BagNodes.
A *trigger* is a callback invoked when something changes in the tree.

## Events

There are three major kinds of events:

1. **insert** — a node is added to a Bag.
2. **delete** — a node is removed from a Bag.
3. **update** — a node’s value and/or attributes change.

## Callback Signatures

### Insert

```text
on_insert(where, position, inserted_node, reason, level)
```

- `where`      — the Bag where insertion occurred (or its path).
- `position`   — index inside the Bag’s ordered children.
- `inserted_node` — the new node.
- `reason`     — an identifier describing why this happened (used to prevent recursion).
- `level`      — 0 for direct Bag, -1, -2… as the event propagates upward.

### Delete

```text
on_delete(where, position, deleted_node, reason, level)
```

### Update

```text
on_update(node, old_value, old_attributes, info, reason, level)
```

where `info` is a structure like:

```text
info = {
    "value_changed": bool,
    "attributes_changed": bool
}
```

`old_value` and `old_attributes` are provided only if the corresponding part actually changed.

## TriggerList Structure

```text
TriggerEntry {
    trigger_id: string
    callback: callable
    event_types: set{"insert","delete","update"}
}

TriggerList {
    entries: list<TriggerEntry>
}
```

### Behaviour

- Triggers are executed **in order of registration**.
- Each trigger has a unique ID and can be removed by ID.
- A TriggerList is attached to:
  - each Bag (structural + subtree updates),
  - each BagNode (local updates only).

## Propagation Order

When a node changes (value/attributes) or is inserted/removed:

1. **Node triggers** fire first (if the event is an update).
2. **Bag triggers** on the containing Bag fire with `level = 0`.
3. The same event propagates up the tree:
   - to the parent Bag’s TriggerList with `level = -1`,
   - then `-2`, etc., until the root Bag is reached.

`reason` can be used by user code to:

- avoid infinite loops (e.g. A changes B, which changes A),
- filter which triggers should react to which type of change.

## Example: Registering a Trigger on a Bag (Python)

```python
def log_update(node, old_value, old_attrs, info, reason, level):
    print(f"[UPDATE][level={level}] node={node.label}, reason={reason}, info={info}")

trigger_id = root.triggers.add(
    callback=log_update,
    event_types={"update"}
)

# Now any update anywhere in the subtree will eventually call log_update.
```

## Example: Node-local Trigger (Python)

```python
def on_config_change(node, old_value, old_attrs, info, reason, level):
    print("Config node changed:", node.value)

config_node = root.getNode("config")
config_node.triggers.add(
    callback=on_config_change,
    event_types={"update"}
)

# Only updates on config_node will call on_config_change.
```

## Mermaid: Event Flow

```mermaid
flowchart TD
    E[Event on node] --> N[Node TriggerList (update only)]
    N --> B0[Bag TriggerList (level 0)]
    B0 --> B1[Parent Bag TriggerList (level -1)]
    B1 --> B2[... up to root]
```
