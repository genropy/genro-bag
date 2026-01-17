# Architecture

```{mermaid}
graph TB
    subgraph Bag
        direction TB
        N1[BagNode<br/>label, value, attr]
        N2[BagNode<br/>label, value, attr]
        N3[BagNode<br/>label, value=Bag, attr]
    end

    subgraph NestedBag[Nested Bag]
        direction TB
        N4[BagNode]
        N5[BagNode]
        N6[BagNode]
    end

    N3 --> NestedBag
```

## Access Patterns

```{mermaid}
flowchart LR
    A["bag['a.b.c']"] --> B[Bag]
    B --> C[BagNode 'a']
    C --> D[Bag]
    D --> E[BagNode 'b']
    E --> F[Bag]
    F --> G[BagNode 'c']
    G --> H[value]
```

```{mermaid}
flowchart LR
    A["bag['a?x']"] --> B[Bag]
    B --> C[BagNode 'a']
    C --> D["attr['x']"]
```

## Core Components

- **Bag**: Ordered container of BagNodes
- **BagNode**: Single node with label, value, and attributes
- **Path**: Dot-separated string for hierarchical access
- **Attribute**: Key-value metadata attached to nodes
