# Resolvers Module

The `resolvers` package provides lazy value computation for TreeStore nodes.

## Module Structure

```{mermaid}
graph TB
    subgraph "genro_treestore.resolvers"
        BASE[base.py<br/>TreeStoreResolver]
        CB[callback.py<br/>CallbackResolver]
        DIR[directory.py<br/>DirectoryResolver]
        TXT[txtdoc.py<br/>TxtDocResolver]

        BASE --> CB
        BASE --> DIR
        BASE --> TXT
    end
```

## TreeStoreResolver

```{eval-rst}
.. autoclass:: genro_treestore.TreeStoreResolver
   :members:
   :undoc-members:
   :show-inheritance:
```

## CallbackResolver

```{eval-rst}
.. autoclass:: genro_treestore.CallbackResolver
   :members:
   :undoc-members:
   :show-inheritance:
```

### Example

```python
from genro_treestore import TreeStore, CallbackResolver

store = TreeStore()
store.set_item('config.base', 'https://api.example.com')
store.set_item('config.version', 'v2')

def compute_url(node):
    parent = node.parent
    return f"{parent['base']}/{parent['version']}"

store.set_item('config.full_url')
store.set_resolver('config.full_url', CallbackResolver(compute_url))

print(store['config.full_url'])  # 'https://api.example.com/v2'
```

## DirectoryResolver

```{eval-rst}
.. autoclass:: genro_treestore.DirectoryResolver
   :members:
   :undoc-members:
   :show-inheritance:
```

### Example

```python
from genro_treestore import TreeStore, DirectoryResolver

store = TreeStore()
store.set_item('files')
store.set_resolver('files', DirectoryResolver('/path/to/dir'))

# Directory contents loaded on first access
for name in store['files'].keys():
    print(name)
```

## TxtDocResolver

```{eval-rst}
.. autoclass:: genro_treestore.TxtDocResolver
   :members:
   :undoc-members:
   :show-inheritance:
```

### Example

```python
from genro_treestore import TreeStore, TxtDocResolver

store = TreeStore()
store.set_item('readme')
store.set_resolver('readme', TxtDocResolver('README.md'))

print(store['readme'])  # File contents
```

## Resolver Architecture

```{mermaid}
classDiagram
    class TreeStoreResolver {
        <<abstract>>
        +load(node)*
        +cache_time: int
    }

    class CallbackResolver {
        +callback: Callable
        +cache_time: int
        +load(node)
    }

    class DirectoryResolver {
        +path: Path
        +load(node)
    }

    class TxtDocResolver {
        +path: Path
        +load(node)
    }

    TreeStoreResolver <|-- CallbackResolver
    TreeStoreResolver <|-- DirectoryResolver
    TreeStoreResolver <|-- TxtDocResolver
```

## Resolver Lifecycle

```{mermaid}
stateDiagram-v2
    [*] --> Attached: set_resolver()
    Attached --> Loading: value accessed
    Loading --> Cached: load() returns
    Cached --> Loading: cache expired
    Cached --> [*]: node deleted
```

## Caching

| Resolver | Default Cache | Configurable |
|----------|--------------|--------------|
| `CallbackResolver` | None | Yes (`cache_time`) |
| `DirectoryResolver` | Permanent | No |
| `TxtDocResolver` | Permanent | No |

## Creating Custom Resolvers

```python
from genro_treestore import TreeStoreResolver

class ApiResolver(TreeStoreResolver):
    """Fetch value from REST API."""

    def __init__(self, endpoint: str, cache_time: int = 60):
        self.endpoint = endpoint
        self.cache_time = cache_time

    def load(self, node):
        import requests
        response = requests.get(self.endpoint)
        return response.json()

# Usage
store.set_resolver('api.data', ApiResolver('https://api.example.com/data'))
```

## See Also

- [Resolvers Guide](../guide/resolvers.md) - Detailed usage guide
