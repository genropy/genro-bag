# Architecture

## Builder Creation

```{mermaid}
flowchart TB
    A["Bag(builder=HtmlBuilder)"] --> B[Bag with .builder]
    B --> C[HtmlBuilder]
    C --> D[Schema: 112 HTML tags]
    C --> E["Methods: div(), p(), ..."]
    C --> F[Validation rules]
```

## Method Call Flow

```{mermaid}
flowchart TB
    A["bag.div()"] --> B{"'div' valid at this position?"}
    B -->|Yes| C["Create BagNode with tag='div'"]
    C --> D{Has children?}
    D -->|Yes| E[Return Bag]
    D -->|No| F[Return BagNode]
```

## Element Types

| Decorator | Returns | Description |
|-----------|---------|-------------|
| `@element(sub_tags='child[]')` | Bag | Container, children allowed |
| `@element(sub_tags='')` | BagNode | Leaf, no children |
| `@element()` | BagNode | Leaf, no children |

## compile() Flow

```{mermaid}
flowchart TB
    A["doc.builder.compile()"] --> B[Walk Bag]
    B --> C[For each node]
    C --> D[Get compile_template from schema]
    D --> E[Render node to output format]
    E --> C
    B --> F["Return compiled output (str, bytes)"]
```
