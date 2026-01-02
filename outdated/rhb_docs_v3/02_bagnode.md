# BagNode — Tree Node

A **BagNode** is an element of the RHB tree. It has:

- a **label** (string),
- a set of **attributes** (dictionary),
- a **value** (any type, including another Bag),
- a **parent_bag** backreference,
- optional **Resolver**,
- its own **TriggerList** for local updates.

## Structure

```text
BagNode {
    label: string
    attributes: dict<string, any>
    value: any | Bag
    parent_bag: Bag | None
    resolver: Resolver | None
    triggers: TriggerList   # local to this node
}
```

## Responsibilities

- Represent the leaf or branch in the data tree.
- Host a resolver to compute or refresh its value.
- Emit **local triggers** when:
  - its value changes,
  - its attributes change.
- Allow direct mutation via:
  - `setValue(value, reason=None)`
  - `setAttr(name, value, reason=None)`

## Local Triggers vs Bag Triggers

- **Node triggers** are attached directly to a specific node and fire **only** when that node’s
  value or attributes change.
- **Bag triggers** are attached to a Bag and can fire when:
  - a node is inserted or removed from the Bag,
  - a node inside the Bag (or in its subtree) is updated.

The usual order of execution on an update is:

1. Node’s local triggers.
2. Bag triggers of the containing Bag (level 0).
3. Bag triggers of ancestor Bags (level -1, -2, …).

## `setValue(value, reason=None)`

Changes the node’s value. Typical behaviour:

- If the value did not actually change → no triggers.
- If the value changed:
  - local node triggers fire,
  - Bag trigger chain fires (update event with `value_changed = True`).

If the new value is a Bag, its `parent_node` must be set to this node.

## `setAttr(name, value, reason=None)`

Modifies a single attribute on the node.

- If the attribute did not change → no triggers.
- If the attribute is added/changed/removed:
  - local node triggers fire,
  - Bag trigger chain fires (update event with `attributes_changed = True`).

A convention can be used such that `value = None` means “remove the attribute”, if desired.

## Example (Python)

```python
from rhb import Bag, BagNode

root = Bag()
root.setItem("config", None, mode="development")

config_node = root.getNode("config")

# Change an attribute
config_node.setAttr("mode", "production", reason="switch-env")

# Change the value
config_node.setValue({"debug": False}, reason="apply-config")
```

## Example (JavaScript)

```javascript
import { Bag } from "./rhb.js";

const root = new Bag();
root.setItem("config", null, { mode: "development" });

const configNode = root.getNode("config");

configNode.setAttr("mode", "production", "switch-env");
configNode.setValue({ debug: false }, "apply-config");
```

For resolver details attached to a BagNode, see `03_resolver.md`.
