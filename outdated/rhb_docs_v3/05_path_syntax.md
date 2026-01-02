# Path Syntax — Navigation and Selection

The RHB system uses a powerful path syntax to navigate the Bag/BagNode tree.

## Segment Types

1. **Label** — e.g. `aaa`, `users`, `profile`
2. **Index** — `#N` (0-based position in the Bag’s children)
3. **Parent navigation** — `/parent`
4. **Attribute access** — `?attr`

## Full Grammar

```text
path          = segment { "." segment } [ attribute ] ;
segment       = label | index | parent ;
label         = /[A-Za-z0-9_]+/ ;
index         = "#" integer ;
parent        = "/parent" ;
attribute     = "?" label ;
```

Examples:

- `aaa.bbb.ccc`
- `aaa.#2.beta?ccc`
- `root.users.#3.profile`
- `aaa.bbb.ccc/parent`
- `aaa.bbb.ccc/parent/parent?mode`

## Semantics

### Label

Moves down into `children[label]`.

### Index `#N`

Selects the N-th child by insertion order in the Bag:

```text
aaa.#0    # first child of aaa’s Bag
aaa.#2    # third child
```

- `#N` **cannot** be used as a path final segment for insertion (setItem).
- If `#N` is out of range during read → returns default.

### `/parent`

Moves from a node’s Bag back to the parent node.

- Can be chained:
  - `/parent/parent` → grandparent node
- If it goes beyond the root → the path resolves to `None` (or default).

### `?attr`

After resolving the node, selects an attribute:

- `aaa.bbb?color` → attribute `color` of node `bbb`.
- If attribute does not exist → default (`None` unless provided).

## Read Semantics (getitem)

`bag[ path ]` or `bag.getitem(path, default)`:

- returns the node’s value, or the attribute value (if `?attr` is used),
- never raises exceptions,
- returns `default` if:
  - any segment fails,
  - index out of range,
  - parent beyond root,
  - node/attribute not found.

## Write Semantics (setItem)

- final segment of the path **must be a label**;
- intermediate segments can include `#N` and `/parent`;
- `?attr` is not allowed in setItem paths.

Example:

```python
root.setItem("aaa.bbb", 1)
root.setItem("aaa.bbb.ccc", 2)
root.setItem("aaa.#0.ddd", 3)  # valid if #0 resolves to a BagNode with a Bag value
```

Invalid:

```python
root.setItem("aaa.#2", 3)      # cannot insert at index
root.setItem("aaa.bbb?x", 5)   # cannot set by attribute in path
```

## Example Walkthrough

Suppose we have:

```text
root
  users (Bag)
    alice (Node)
    bob   (Node)
```

- `root["users.alice"]` → value of node `alice`.
- `root["users.#0"]` → value of first child in `users` (which is `alice`).
- `root["users.alice/parent"]` → the BagNode that contains the Bag `users` (i.e. the node "users" if present).
- `root["users.alice?age"]` → attribute `age` of node `alice` or `None`.
