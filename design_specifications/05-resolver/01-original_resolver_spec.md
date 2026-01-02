# Original BagResolver Specification

## Overview

BagResolver is an abstract class for **lazy loading** values in BagNodes. Instead of storing a static value, a node can have a resolver that computes the value on-demand.

```mermaid
classDiagram
    class BagResolver {
        <<abstract>>
        +classKwargs: dict
        +classArgs: list
        +parentNode: BagNode
        +kwargs: dict
        +cacheTime: int
        +readOnly: bool
        +expired: bool
        +__call__(**kwargs) Any
        +load() Any
        +init()
        +reset()
        +resolverSerialize() dict
    }

    class BagNode {
        +label: str
        +_value: Any
        +_resolver: BagResolver
        +getValue(mode) Any
        +setValue(value)
    }

    BagNode "1" --> "0..1" BagResolver : has resolver
    BagResolver "1" --> "1" BagNode : parentNode
```

## Key Concepts

### 1. Callable Pattern

The resolver is **callable**. To get the resolved value:

```python
value = resolver()  # calls __call__
```

This is the **only entry point** to get the resolved value. All other methods (like `keys()`, `items()`) internally call `self()`.

### 2. Caching Semantics

```mermaid
flowchart TD
    A[resolver called] --> B{cacheTime == 0?}
    B -->|Yes| C[call load]
    B -->|No| D{expired?}
    D -->|Yes| E[call load]
    E --> F[update cache]
    F --> G[return result]
    D -->|No| H[return cached value]
    C --> G
    H --> G
```

**cacheTime values:**

| Value | Behavior |
|-------|----------|
| `0` | NO cache - `load()` called every time |
| `> 0` | Cache for N seconds (TTL) |
| `< 0` | INFINITE cache (until manual `reset()`) |

### 3. readOnly Flag

When `readOnly=True` (default):
- The resolved value is **NOT** stored in `node._value`
- Each access triggers the resolver (subject to caching)
- The node remains "virtual"

When `readOnly=False`:
- The resolved value **IS** stored in `node._value`
- After first resolution, node behaves like a normal node
- Resolver can be "consumed"

## Class-Level Configuration

Subclasses declare their parameters using class variables:

```python
class UrlResolver(BagResolver):
    classKwargs = {'cacheTime': 300, 'readOnly': False, 'timeout': 30}
    classArgs = ['url']  # positional args

    def load(self):
        return fetch(self.url, timeout=self.timeout)
```

```mermaid
flowchart LR
    subgraph "classArgs (positional)"
        A1["args[0]"] --> B1["self.url"]
    end

    subgraph "classKwargs (keyword with defaults)"
        A2["cacheTime=300"] --> B2["self.cacheTime"]
        A3["readOnly=False"] --> B3["self.readOnly"]
        A4["timeout=30"] --> B4["self.timeout"]
    end

    subgraph "extra kwargs"
        A5["other=value"] --> B5["self.kwargs['other']"]
        B5 --> C5["self.other"]
    end
```

### Parameter Resolution in `__init__`

```mermaid
sequenceDiagram
    participant Caller
    participant __init__
    participant Instance

    Caller->>__init__: UrlResolver('http://...', cacheTime=60, custom='x')

    Note over __init__: 1. Save for serialization
    __init__->>Instance: _initArgs = ['http://...']
    __init__->>Instance: _initKwargs = {cacheTime:60, custom:'x'}

    Note over __init__: 2. Process classArgs
    __init__->>Instance: self.url = 'http://...'

    Note over __init__: 3. Process classKwargs
    __init__->>Instance: self.cacheTime = 60 (from kwargs)
    __init__->>Instance: self.readOnly = False (default)
    __init__->>Instance: self.timeout = 30 (default)

    Note over __init__: 4. Process extra kwargs
    __init__->>Instance: self.kwargs = {custom:'x'}
    __init__->>Instance: self.custom = 'x'

    Note over __init__: 5. Call hook
    __init__->>Instance: self.init()
```

## Integration with BagNode

### getValue() Flow

```mermaid
sequenceDiagram
    participant Client
    participant BagNode
    participant Resolver

    Client->>BagNode: node.value (property get)
    BagNode->>BagNode: getValue()

    alt has resolver
        alt mode == 'static'
            BagNode-->>Client: return _value (bypass resolver)
        else normal mode
            alt resolver.readOnly
                BagNode->>Resolver: resolver()
                Resolver-->>BagNode: resolved value
                BagNode-->>Client: return resolved value
                Note over BagNode: _value NOT updated
            else not readOnly
                alt resolver.expired
                    BagNode->>Resolver: resolver()
                    Resolver-->>BagNode: resolved value
                    BagNode->>BagNode: self.value = resolved value
                    Note over BagNode: _value IS updated
                end
                BagNode-->>Client: return _value
            end
        end
    else no resolver
        BagNode-->>Client: return _value
    end
```

### setValue() Flow

```mermaid
sequenceDiagram
    participant Client
    participant BagNode
    participant Resolver

    Client->>BagNode: node.value = new_value
    BagNode->>BagNode: setValue(new_value)

    alt new_value is BagResolver
        BagNode->>BagNode: self.resolver = new_value
        BagNode->>BagNode: value = None
        Note over BagNode: Resolver stored, _value cleared
    else normal value
        BagNode->>BagNode: self._value = new_value
    end
```

## Cache Internals

### State Variables

```python
self._cacheTime        # int: 0, >0, or <0
self._cacheTimeDelta   # timedelta: max duration
self._cache            # Any: cached value
self._cacheLastUpdate  # datetime: when last updated
```

### Cache State Machine

```mermaid
stateDiagram-v2
    [*] --> NoCache: cacheTime=0
    [*] --> Expired: cacheTime≠0, init

    NoCache --> NoCache: every call → load()

    Expired --> Valid: load() called
    Valid --> Expired: time > TTL
    Valid --> Expired: reset() called
    Valid --> Valid: call within TTL

    note right of Expired: _cacheLastUpdate = datetime.min
    note right of Valid: _cache holds value
```

### expired Property Logic

```python
def expired(self):
    if self._cacheTime == 0:          # no cache mode
        return True
    if self._cacheLastUpdate == datetime.min:  # never updated or reset
        return True
    return (datetime.now() - self._cacheLastUpdate) > self._cacheTimeDelta
```

## Proxy Methods

The resolver acts as a **transparent proxy** to the resolved Bag:

```mermaid
flowchart LR
    subgraph "Resolver Proxy"
        A["resolver['foo']"] --> B["self()['foo']"]
        C["resolver.keys()"] --> D["self().keys()"]
        E["resolver.items()"] --> F["self().items()"]
        G["resolver._htraverse(...)"] --> H["self()._htraverse(...)"]
    end

    B --> I["resolved_bag['foo']"]
    D --> J["resolved_bag.keys()"]
    F --> K["resolved_bag.items()"]
    H --> L["resolved_bag._htraverse(...)"]
```

**Important:** `_htraverse` on the resolver does NOT implement traversal logic. It simply:
1. Calls `self()` to resolve the value (get the Bag)
2. Delegates `_htraverse` to the resolved Bag

The actual traversal logic lives in the Bag class.

## Serialization

```python
resolver.resolverSerialize()
# Returns:
{
    'resolverclass': 'UrlResolver',
    'resolvermodule': 'myapp.resolvers',
    'args': ['http://example.com'],
    'kwargs': {'cacheTime': 60, 'custom': 'x'}
}
```

**Note:** The base class has `resolverSerialize()` but NO `deserialize()`. Deserialization is handled elsewhere in Genropy.

## Hooks for Subclasses

### load() - REQUIRED

```python
def load(self):
    """Must be overridden. Returns the resolved value."""
    pass  # Base implementation does nothing
```

### init() - OPTIONAL

```python
def init(self):
    """Called at end of __init__. Override for custom setup."""
    pass
```

This hook allows subclasses to do additional initialization without needing to call `super().__init__()`.

## Dynamic kwargs Update

The `__call__` method accepts kwargs that can update resolver parameters at runtime:

```mermaid
sequenceDiagram
    participant Client
    participant Resolver

    Client->>Resolver: resolver(timeout=60)

    alt kwargs != self.kwargs
        Resolver->>Resolver: self.kwargs.update(kwargs)
        Resolver->>Resolver: self._attachKwargs()
        Resolver->>Resolver: self.reset()
        Note over Resolver: Cache invalidated
    end

    Resolver->>Resolver: proceed with normal resolution
```

This allows changing resolver behavior without creating a new instance.

## Summary

| Aspect | Description |
|--------|-------------|
| **Entry Point** | `resolver()` via `__call__` |
| **Caching** | 0=none, >0=TTL, <0=infinite |
| **readOnly** | True=never store, False=store after resolve |
| **Hooks** | `load()` (required), `init()` (optional) |
| **Proxy** | Transparent delegation to resolved Bag |
| **Serialization** | `resolverSerialize()` only |
