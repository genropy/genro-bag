# Bag — Hierarchical Container

The **Bag** is the main container in the RHB system. It holds a set of **BagNode** instances,
keyed by unique labels and kept in insertion order.

## Responsibilities

- Store child nodes in a deterministic order.
- Maintain a reference to its parent node (if any).
- Provide high‑level APIs:
  - `getitem(path, default=None)`
  - `getNode(path, default=None)`
  - `setItem(path, value, _attrs=None, **attrs)`
  - `popNode(path)`
- Host a **TriggerList** that reacts to:
  - node insert
  - node delete
  - node update (value and/or attributes)
- Participate in trigger propagation up the tree.

## Core Fields

Conceptually, a Bag contains:

```text
Bag {
    attributes: dict<string, any>
    children: OrderedDict<label, BagNode>
    parent_node: BagNode | None
    triggers: TriggerList
}
```

### Attributes

`attributes` is a dictionary of metadata about the Bag itself.  
It does **not** affect the structure of the tree, but may be used for configuration, tags, etc.

### Children

- `children` is an ordered mapping: `label -> BagNode`.
- **Labels are unique** inside a Bag.
- The order of insertion is preserved and is used by the `#N` path segment.

## Backreferences

- Each Bag (except the root) has `parent_node` pointing to the **BagNode** that contains it.
- Each BagNode has `parent_bag` pointing to the **Bag** that contains it.
- This guarantees:
  - strict tree (no DAG)
  - ability to compute absolute and relative paths
  - trigger propagation from leaf to root.

## TriggerList on Bag

Each Bag owns a `TriggerList` that receives events of type:

- `insert(where, position, inserted_node, reason, level)`
- `delete(where, position, deleted_node, reason, level)`
- `update(node, old_value, old_attrs, info, reason, level)`

When an event occurs inside a Bag (or inside its subtree), the Bag’s `TriggerList` may be invoked
with the appropriate `level` value (0 for direct children, -1, -2… as the event propagates upward).

## Bag API

### `getitem(path, default=None)`

Resolves a path and returns:

- the node value (if the final target is a node and no `?attr` is used),
- the attribute value (if `?attr` is used),
- or `default` if the path cannot be resolved.

**Never raises** — safe read.

### `getNode(path, default=None)`

Similar to `getitem`, but returns the **BagNode** instance itself, or `default` if not found.
If the path ends with `?attr`, it also returns `default`, because the target is not a node.

### `setItem(path, value, _attrs=None, **attrs)`

Creates or updates a node at the given path.

Rules:

- the final segment of `path` **must be a label** (not `#N`, not `/parent`, not `?attr`);
- if the label exists, its node is updated;
- if it does not exist, a new node is created.

Attributes can be provided in three ways:

```python
bag.setItem("aaa.bbb", 10)                       # value only
bag.setItem("aaa.bbb", 10, {"x": 1, "y": 2})     # value + dict attributes
bag.setItem("aaa.bbb", 10, x=1, y=2)             # value + keyword attributes
```

The `_attrs` dict and `**attrs` keyword arguments are merged, with explicit `**attrs` overriding keys from `_attrs`.

### `popNode(path)`

Removes the node at `path` and returns it, or `None` if not found.  
Deletion fires the **delete triggers** on the Bag and its ancestors.

## Example (Python)

```python
from rhb import Bag

root = Bag(attributes={"name": "root"})

# Create a nested structure
root.setItem("users.alice", {"age": 30}, role="admin")
root.setItem("users.bob", {"age": 25}, role="user")

# Read values
age_alice = root["users.alice?age"]          # -> 30
role_bob  = root["users.bob?role"]           # -> "user"

# Safe read (non-existing node)
unknown = root["users.charlie", None]        # -> None

# Pop a node
bob_node = root.popNode("users.bob")
```

## Example (JavaScript)

```javascript
import { Bag } from "./rhb.js";

const root = new Bag({ name: "root" });

root.setItem("users.alice", { age: 30 }, { role: "admin" });
root.setItem("users.bob", { age: 25 }, { role: "user" });

const ageAlice = root.getitem("users.alice?age");   // 30
const roleBob  = root.getitem("users.bob?role");    // "user"

const unknown  = root.getitem("users.charlie", null); // null

const bobNode  = root.popNode("users.bob");
```

This document focuses on Bag itself; see `02_bagnode.md` for BagNode details.
