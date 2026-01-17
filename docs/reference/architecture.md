# Architecture

This document explains how Bag works internally, removing the "magic" and showing the underlying mechanisms.

## Core Data Model

A Bag is a container of `BagNode` objects. Each node has a label, a value, and optional attributes.

```mermaid
classDiagram
    class Bag {
        -List~BagNode~ _nodes
        -Dict _node_index
        -BagNode _parent_node
        -Builder _builder
        +__getitem__(path)
        +__setitem__(path, value)
        +set_item(path, value, **attrs)
        +subscribe(name, callback)
    }

    class BagNode {
        -str _label
        -Any _value
        -Dict _attr
        -Bag _parent
        +label: str
        +value: Any
        +attr: Dict
        +parent: Bag
    }

    Bag "1" *-- "*" BagNode : contains
    BagNode "1" --> "0..1" Bag : value can be
```

## Node Structure

Each `BagNode` holds:
- **label**: The node's name (key)
- **value**: Any Python object, including another Bag for nesting
- **attr**: Dictionary of metadata attributes

```mermaid
graph LR
    subgraph BagNode
        L[label: 'user']
        V[value: 'Alice']
        A[attr: role='admin', active=True]
    end
```

## Path Resolution

When you access `bag['a.b.c']`, the path is parsed and resolved step by step.

```mermaid
flowchart LR
    A["bag['a.b.c']"] --> B[Split path: a, b, c]
    B --> C[Get node 'a']
    C --> D{a.value is Bag?}
    D -->|Yes| E[Get node 'b' from a.value]
    D -->|No| F[Return None]
    E --> G{b.value is Bag?}
    G -->|Yes| H[Get node 'c' from b.value]
    G -->|No| I[Return None]
    H --> J[Return c.value]
```

### Path Syntax

| Syntax | Meaning | Example |
|--------|---------|---------|
| `a.b.c` | Nested path | `bag['config.db.host']` |
| `#0` | Index access | `bag['#0']` (first node) |
| `key?attr` | Attribute access | `bag['user?role']` |
| `?attr` | Root attribute | `bag['?version']` |

## Attribute Access

Attributes are accessed using the `?` syntax in paths.

```mermaid
flowchart TB
    A["bag['user?role']"] --> B[Parse: key='user', attr='role']
    B --> C[Get node 'user']
    C --> D[Return node.attr['role']]

    E["bag.set_item('user', 'Alice', role='admin')"] --> F[Create/update node]
    F --> G[Set node.value = 'Alice']
    F --> H[Set node.attr['role'] = 'admin']
```

## Resolvers

Resolvers provide lazy loading. When a node's value is a Resolver, accessing it triggers resolution.

```mermaid
sequenceDiagram
    participant User
    participant Bag
    participant Node
    participant Resolver
    participant External as External Source

    User->>Bag: bag['data']
    Bag->>Node: get value
    Node->>Node: value is Resolver?
    Note over Node: Yes, it's a Resolver
    Node->>Resolver: resolve()
    Resolver->>External: fetch data
    External-->>Resolver: return data
    Resolver-->>Node: resolved value
    Node-->>Bag: return value
    Bag-->>User: data
```

### Resolver Types

```mermaid
classDiagram
    class BagResolver {
        <<abstract>>
        +load() Any
        +async_load() Any
        +cache_time: int
    }

    class BagCbResolver {
        -Callable _callback
        +load() Any
    }

    class UrlResolver {
        -str _url
        +load() Any
    }

    class DirectoryResolver {
        -Path _path
        +load() Bag
    }

    BagResolver <|-- BagCbResolver
    BagResolver <|-- UrlResolver
    BagResolver <|-- DirectoryResolver
```

### Caching

Resolvers support caching to avoid repeated expensive operations.

```mermaid
flowchart TB
    A[Access resolver] --> B{Cache valid?}
    B -->|Yes| C[Return cached value]
    B -->|No| D[Call load/async_load]
    D --> E[Store in cache with timestamp]
    E --> F[Return value]
```

## Subscriptions

Subscriptions enable reactive programming by notifying callbacks when nodes change.

```mermaid
sequenceDiagram
    participant User
    participant Bag
    participant Subscription
    participant Callback

    User->>Bag: subscribe('watcher', update=on_change)
    Bag->>Subscription: create subscription

    User->>Bag: bag['name'] = 'Alice'
    Bag->>Bag: create/update node
    Bag->>Subscription: notify(node, 'ins')
    Subscription->>Callback: on_change(node, 'ins')
```

### Event Types

| Event | Trigger |
|-------|---------|
| `ins` | New node inserted |
| `upd_value` | Node value changed |
| `upd_attr` | Node attribute changed |
| `del` | Node deleted |

```mermaid
flowchart LR
    subgraph Events
        INS[ins: insert]
        UPD_V[upd_value: value change]
        UPD_A[upd_attr: attr change]
        DEL[del: delete]
    end

    subgraph Subscription
        ANY[any: all events]
        UPDATE[update: ins + upd_*]
        DELETE[delete: del only]
    end

    INS --> ANY
    INS --> UPDATE
    UPD_V --> ANY
    UPD_V --> UPDATE
    UPD_A --> ANY
    UPD_A --> UPDATE
    DEL --> ANY
    DEL --> DELETE
```

## Builders

Builders provide a fluent API for constructing Bags with structural validation.

```mermaid
flowchart TB
    A[bag.div] --> B["__getattr__('div')"]
    B --> C[Builder.create_child]
    C --> D{Tag allowed?}
    D -->|Yes| E[Create BagNode]
    D -->|No| F[Raise ValidationError]
    E --> G[Set attributes]
    G --> H[Return node for chaining]
```

### Builder Hierarchy

```mermaid
classDiagram
    class Builder {
        <<abstract>>
        +create_child(tag, value, attrs)
        +validate_tag(parent, tag)
    }

    class HtmlBuilder {
        +ALLOWED_CHILDREN: Dict
        +validate_tag()
    }

    class XmlBuilder {
        +schema: XmlSchema
        +validate_tag()
    }

    Builder <|-- HtmlBuilder
    Builder <|-- XmlBuilder
```

## Serialization

Bag supports multiple serialization formats.

```mermaid
flowchart LR
    subgraph Bag
        B[Bag object]
    end

    subgraph Formats
        XML[XML]
        JSON[TYTX JSON]
        MSGPACK[TYTX MsgPack]
    end

    B -->|to_xml| XML
    XML -->|from_xml| B

    B -->|to_tytx json| JSON
    JSON -->|from_tytx json| B

    B -->|to_tytx msgpack| MSGPACK
    MSGPACK -->|from_tytx msgpack| B
```

### TYTX Format

TYTX (Type-preserving Transfer) maintains Python types across serialization.

```mermaid
flowchart TB
    subgraph "Python Object"
        PY[value: 42, type: int]
    end

    subgraph "TYTX Encoding"
        TX["{'_t': 'I', '_v': 42}"]
    end

    subgraph "After Deserialization"
        PY2[value: 42, type: int]
    end

    PY -->|encode| TX
    TX -->|decode| PY2
```

## Memory Layout

Understanding memory usage helps optimize for large Bags.

```mermaid
graph TB
    subgraph "Bag (48 bytes shallow)"
        BL[_nodes: List]
        BI[_node_index: Dict]
        BP[_parent_node: ref]
        BB[_builder: ref]
    end

    subgraph "BagNode (~290 bytes each)"
        NL[_label: str]
        NV[_value: Any]
        NA[_attr: Dict]
        NP[_parent: ref]
    end

    BL --> NL
```

### Memory Scaling

| Items | Dict | Bag | Per-item |
|-------|------|-----|----------|
| 100 | 7.7 KB | 36 KB | ~290 bytes |
| 10,000 | 975 KB | 3.7 MB | ~289 bytes |
| 100,000 | 11.4 MB | 38.8 MB | ~288 bytes |

## Thread Safety

Bag is **not thread-safe** by default. For concurrent access:

```mermaid
flowchart TB
    subgraph "Thread-Safe Pattern"
        L[Lock]
        B[Bag]
        T1[Thread 1]
        T2[Thread 2]
    end

    T1 -->|acquire| L
    L -->|protected| B
    T2 -->|wait| L
```

Recommended approach:
- Use a threading.Lock for write operations
- Or use separate Bag instances per thread
- Or use async with proper await patterns

## Complete Data Flow

```mermaid
flowchart TB
    subgraph Input
        I1[Direct assignment]
        I2[From dict]
        I3[From XML]
        I4[Builder API]
    end

    subgraph "Bag Core"
        B[Bag]
        N[BagNodes]
        S[Subscriptions]
    end

    subgraph Processing
        R[Resolvers]
        V[Validation]
    end

    subgraph Output
        O1[Path access]
        O2[To XML]
        O3[To TYTX]
        O4[Iteration]
    end

    I1 --> B
    I2 --> B
    I3 --> B
    I4 --> V
    V --> B

    B --> N
    N --> S
    N --> R

    B --> O1
    B --> O2
    B --> O3
    B --> O4
```

## Performance Characteristics

| Operation | Time Complexity | Notes |
|-----------|-----------------|-------|
| Direct access `bag['key']` | O(1) | Hash lookup |
| Path access `bag['a.b.c']` | O(n) | n = path depth |
| Index access `bag['#0']` | O(1) | List index |
| Insert | O(1) amortized | Creates BagNode |
| Delete | O(n) | n = number of nodes |
| Iteration | O(n) | n = number of nodes |
| Subscribe | O(1) | Register callback |
| Event dispatch | O(s) | s = number of subscribers |
