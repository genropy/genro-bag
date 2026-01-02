# Resolvers

Resolvers enable lazy evaluation of node values in TreeStore. Instead of storing a static value, a node can have a resolver that computes the value on demand.

## How Resolvers Work

```{mermaid}
sequenceDiagram
    participant C as Client
    participant S as TreeStore
    participant N as Node
    participant R as Resolver

    C->>S: store['config.computed']
    S->>N: get value
    N->>N: check if resolver exists
    N->>R: load()
    R-->>R: compute value
    R->>N: return + cache
    N-->>S: value
    S-->>C: value

    Note over R: Cached until TTL expires

    C->>S: store['config.computed'] (again)
    S->>N: get value
    N->>N: check cache
    N-->>S: cached value
    S-->>C: value (from cache)
```

## Resolver Types

```{mermaid}
graph TB
    subgraph "Resolver Hierarchy"
        BASE[TreeStoreResolver<br/>Abstract base class]
        CB[CallbackResolver<br/>Function-based]
        DIR[DirectoryResolver<br/>Filesystem]
        TXT[TxtDocResolver<br/>Text files]

        BASE --> CB
        BASE --> DIR
        BASE --> TXT
    end
```

| Resolver | Purpose | Caching |
|----------|---------|---------|
| `CallbackResolver` | Compute value via callback function | Optional TTL |
| `DirectoryResolver` | Lazy-load directory contents | On demand |
| `TxtDocResolver` | Load text file content | On demand |

## CallbackResolver

The most flexible resolver - computes values using a callback function.

### Basic Usage

```python
from genro_treestore import TreeStore, CallbackResolver

store = TreeStore()
store.set_item('config.base_url', 'https://api.example.com')
store.set_item('config.version', 'v2')

# Define callback that computes value
def get_full_url(node):
    parent = node.parent  # TreeStore containing this node
    base = parent.get_item('base_url')
    version = parent.get_item('version')
    return f"{base}/{version}"

# Create node and attach resolver
store.set_item('config.full_url')
store.set_resolver('config.full_url', CallbackResolver(get_full_url))

# Value is computed on access
print(store['config.full_url'])  # 'https://api.example.com/v2'
```

### With Caching

```python
import time

def expensive_computation(node):
    time.sleep(1)  # Simulate expensive operation
    return "computed_value"

# Cache for 60 seconds
resolver = CallbackResolver(expensive_computation, cache_time=60)
store.set_resolver('expensive.value', resolver)

# First access: computes value (slow)
value1 = store['expensive.value']

# Second access within 60s: returns cached value (fast)
value2 = store['expensive.value']

# After 60s: recomputes
```

### Callback Signature

The callback receives the `TreeStoreNode` as its argument:

```python
def my_callback(node: TreeStoreNode) -> Any:
    # node.label - the node's label
    # node.attr - the node's attributes dict
    # node.parent - the parent TreeStore
    # node.store - the root TreeStore
    return computed_value
```

## DirectoryResolver

Lazily loads directory contents into the tree structure.

```python
from genro_treestore import TreeStore, DirectoryResolver

store = TreeStore()

# Attach resolver to a node
store.set_item('filesystem')
store.set_resolver('filesystem', DirectoryResolver('/path/to/directory'))

# Directory contents are loaded on first access
for name, node in store['filesystem'].items():
    print(f"{name}: {node}")
```

## TxtDocResolver

Loads text file content on demand.

```python
from genro_treestore import TreeStore, TxtDocResolver

store = TreeStore()

# Attach resolver
store.set_item('readme')
store.set_resolver('readme', TxtDocResolver('/path/to/README.md'))

# Content is loaded on access
print(store['readme'])  # File contents
```

## Creating Custom Resolvers

Extend `TreeStoreResolver` to create custom resolvers:

```python
from genro_treestore import TreeStoreResolver

class DatabaseResolver(TreeStoreResolver):
    """Load value from database on demand."""

    def __init__(self, query: str, connection):
        self.query = query
        self.connection = connection

    def load(self, node):
        """Called when node value is accessed."""
        cursor = self.connection.execute(self.query)
        return cursor.fetchone()

# Usage
store.set_item('user.current')
store.set_resolver('user.current', DatabaseResolver(
    "SELECT * FROM users WHERE id = 1",
    db_connection
))
```

## Resolver Lifecycle

```{mermaid}
stateDiagram-v2
    [*] --> Attached: set_resolver()
    Attached --> Loading: value accessed
    Loading --> Cached: load() returns
    Cached --> Loading: cache expired
    Cached --> [*]: node deleted

    note right of Cached
        Value stored in node
        until TTL expires
    end note
```

## Best Practices

1. **Use caching wisely**: Set appropriate `cache_time` for expensive computations
2. **Keep callbacks simple**: Complex logic should be in separate functions
3. **Handle errors**: Callbacks should handle exceptions gracefully
4. **Avoid circular dependencies**: Don't create resolvers that depend on each other cyclically

## See Also

- {class}`~genro_treestore.TreeStoreResolver` - Base resolver class
- {class}`~genro_treestore.CallbackResolver` - Function-based resolver
- {class}`~genro_treestore.DirectoryResolver` - Filesystem resolver
- {class}`~genro_treestore.TxtDocResolver` - Text file resolver
