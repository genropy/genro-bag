
# 01 — RHB Structure (Complete)

## 1. Overview
A Reactive Hierarchical Bag (RHB) is a hierarchical, reactive data tree composed of:
- **Bag** objects (containers of nodes)
- **Node** objects (label + attributes + value)
- Automatic **backreferences** to maintain tree integrity
- Fully reactive behavior (trigger propagation)
- Resolver-based dynamic values (sync and async)

## 2. Node Specification

### 2.1 Fields
- `label: string` — name of this node  
- `attributes: dict<string, any>` — metadata  
- `value: any | Bag` — raw value or child Bag  
- `parent_bag: Bag | null` — backref  
- `triggers: list<Trigger>` — local triggers (update only)  
- `resolver: optional Resolver` — optional dynamic value provider  
- `resolver_cache: {value, expires_at}` — cached value if applicable  

### 2.2 Behavior
- A node belongs to **exactly one** Bag.
- If `value` is a Bag, the Bag’s `parent_node` is this node.
- Value changes propagate triggers.
- Attribute changes propagate triggers.

## 3. Bag Specification

### 3.1 Fields
- `attributes: dict<string, any>`
- `children: OrderedDict<label, Node>`
- `parent_node: Node | null`
- `triggers: list<Trigger>`

### 3.2 Behavior
- A Bag contains **unique** labels.
- Insertion/removal changes fire triggers.
- Bags form a strict tree (not DAG).

