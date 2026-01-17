# Architecture

## Subscription Flow

```{mermaid}
flowchart TB
    A["bag['key'] = value"] --> B[Bag]
    B --> C[_subs registry]
    C --> D["'logger' → callbacks"]
    C --> E["'validator' → callbacks"]
    C --> F["'sync' → callbacks"]

    B --> G["Operation (ins/upd/del)"]
    G --> H[Emit Event]
    H --> I["callback(node, evt, pathlist, ind)"]
```

## Event Propagation

When setting a nested path, events are emitted for each level:

```{mermaid}
flowchart TB
    A["bag['a.b.c'] = 1"] --> B[Creates hierarchy]

    subgraph Hierarchy
        direction TB
        R[bag] --> N1["'a' Bag"]
        N1 --> N2["'b' Bag"]
        N2 --> N3["'c' = 1"]
    end

    N1 -.->|ins event| E1["pathlist: ['a']"]
    N2 -.->|ins event| E2["pathlist: ['a', 'b']"]
    N3 -.->|ins event| E3["pathlist: ['a', 'b', 'c']"]
```
