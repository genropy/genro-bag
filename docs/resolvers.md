# Resolvers

Resolvers enable **lazy loading** of values in Bag nodes. Instead of storing a static value, a node can have a resolver that computes or fetches the value on demand.

## Key Concepts

- **Lazy loading**: Value is computed only when accessed
- **Caching**: Results can be cached with configurable TTL
- **Transparent access**: Access looks the same as static values
- **Async support**: All resolvers support async operations

## Built-in Resolvers

### BagCbResolver (Callback)

Compute values using a Python callable:

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.resolvers import BagCbResolver

>>> def get_timestamp():
...     from datetime import datetime
...     return datetime.now().isoformat()

>>> bag = Bag()
>>> bag['timestamp'] = BagCbResolver(get_timestamp)

>>> # Value is computed on access
>>> bag['timestamp']  # doctest: +SKIP
'2025-01-07T10:30:45.123456'
```

### With Caching

```python
from genro_bag import Bag
from genro_bag.resolvers import BagCbResolver

call_count = 0
def expensive_computation():
    global call_count
    call_count += 1
    return {'result': 42, 'calls': call_count}

bag = Bag()
# Cache for 60 seconds
bag['data'] = BagCbResolver(expensive_computation, cache_time=60)

bag['data']  # First call - computes: {'result': 42, 'calls': 1}
bag['data']  # Second call - uses cache: {'result': 42, 'calls': 1}
```

Cache time values:
- `0`: No caching, compute every time (default)
- `> 0`: Cache for N seconds
- `< 0`: Cache indefinitely (until manual reset)

### UrlResolver

Fetch content from HTTP URLs:

```python
from genro_bag import Bag
from genro_bag.resolvers import UrlResolver

bag = Bag()
bag['api'] = UrlResolver('https://api.example.com/data')

# Access triggers HTTP request
data = bag['api']  # Returns bytes
```

### With Auto-Parsing

```python
from genro_bag import Bag
from genro_bag.resolvers import UrlResolver

bag = Bag()
# Parse response as Bag based on content-type
bag['users'] = UrlResolver(
    'https://api.example.com/users',
    as_bag=True,
    cache_time=300
)

# Returns Bag parsed from JSON/XML response
users = bag['users']
```

### HTTP Methods

```python
from genro_bag import Bag
from genro_bag.resolvers import UrlResolver

# GET with query parameters
bag['search'] = UrlResolver(
    'https://api.example.com/search',
    qs={'query': 'test', 'limit': 10}
)

# POST with body
body = Bag({'name': 'Alice', 'email': 'alice@example.com'})
bag['create'] = UrlResolver(
    'https://api.example.com/users',
    method='post',
    body=body,
    as_bag=True
)
```

### DirectoryResolver

Load Bag from a directory structure:

```python
from genro_bag import Bag
from genro_bag.resolvers import DirectoryResolver

bag = Bag()
bag['config'] = DirectoryResolver('/path/to/config/')

# Directory contents become Bag structure:
# /path/to/config/
#   database.xml    -> bag['config.database']
#   logging.json    -> bag['config.logging']
#   subdir/         -> bag['config.subdir'] (recursive)
```

Supported file formats:
- `.xml` - Parsed as XML
- `.bag.json` - Parsed as TYTX JSON
- `.bag.mp` - Parsed as TYTX MessagePack

### OpenApiResolver

Navigate OpenAPI specifications. The resolver organizes endpoints by tags for easy navigation:

```python
from genro_bag import Bag
from genro_bag.resolvers import OpenApiResolver

bag = Bag()
bag['api'] = OpenApiResolver('https://petstore3.swagger.io/api/v3/openapi.json')

# Access triggers fetch and parse
api = bag['api']

# Structure organized by tags
api['info']                    # API description (value), title/version (attrs)
api['api']['pet'].keys()       # ['addPet', 'updatePet', 'findPetsByStatus', ...]
api['api']['store'].keys()     # ['getInventory', 'placeOrder', ...]

# Access operation details
op = api['api']['pet']['findPetsByStatus']
op['summary']                  # 'Finds Pets by status'
op['method']                   # 'get'
op['path']                     # '/pet/findByStatus'
op['qs']['status'] = 'available'  # Set query param
# op['value'] is a UrlResolver ready to call the endpoint
```

### TxtDocResolver

Load file content as raw bytes:

```python
from genro_bag import Bag
from genro_bag.resolvers import TxtDocResolver

bag = Bag()
bag['readme'] = TxtDocResolver('/path/to/readme.txt')

# Access triggers file read
content = bag['readme']  # Returns bytes
text = content.decode('utf-8')  # Decode to string
```

### SerializedBagResolver

Load a serialized Bag file (XML, TYTX JSON, TYTX MessagePack):

```python
from genro_bag import Bag
from genro_bag.resolvers import SerializedBagResolver

bag = Bag()
bag['config'] = SerializedBagResolver('/path/to/config.xml')
bag['data'] = SerializedBagResolver('/path/to/data.bag.json')

# Access triggers file read and parse
config = bag['config']  # Returns Bag parsed from XML
config['database.host']
```

## Creating Custom Resolvers

Extend `BagResolver` to create custom resolvers:

```python
from genro_bag.resolver import BagResolver
from genro_bag import Bag

class DatabaseResolver(BagResolver):
    """Load data from database query."""

    class_args = ['query']
    class_kwargs = {
        'cache_time': 60,
        'read_only': True,
        'connection': None
    }

    def load(self):
        query = self._kw['query']
        conn = self._kw['connection']

        # Execute query and return as Bag
        results = conn.execute(query).fetchall()
        bag = Bag()
        for i, row in enumerate(results):
            bag[f'row_{i}'] = Bag(dict(row))
        return bag

# Usage
bag = Bag()
bag['users'] = DatabaseResolver(
    'SELECT * FROM users',
    connection=db_conn,
    cache_time=300
)
```

## Resolver Parameters

All resolvers support these base parameters (defaults may vary by resolver):

| Parameter    | Base Default | Description                                               |
|--------------|--------------|-----------------------------------------------------------|
| `cache_time` | 0            | Cache duration in seconds (0=none, <0=infinite)           |
| `read_only`  | False        | If True, value is not stored in node (computed each time) |

**Important**: When `cache_time != 0`, `read_only` is forced to `False` because caching
requires storing the value. Set `cache_time=0` if you need true `read_only=True` behavior.

Some resolvers override base defaults:

- `UrlResolver`: `cache_time=300` (so effectively `read_only=False`)
- `DirectoryResolver`: `cache_time=500` (so effectively `read_only=False`)
- `OpenApiResolver`: `cache_time=-1` (infinite cache, so effectively `read_only=False`)
- `BagCbResolver`: `cache_time=0`, `read_only=False`

## Caching Behavior

### No Cache (default)

```python
resolver = BagCbResolver(func, cache_time=0)
# load() called on EVERY access
```

### Timed Cache

```python
resolver = BagCbResolver(func, cache_time=300)
# load() called once, result cached for 5 minutes
```

### Infinite Cache

```python
resolver = BagCbResolver(func, cache_time=-1)
# load() called once, result cached forever
# Use resolver.reset() to clear cache
```

### Manual Reset

```python
resolver = bag.get_node('data').resolver
resolver.reset()  # Clear cache, next access will reload
```

## Sync and Async Support

Resolvers work in both **synchronous** and **asynchronous** contexts, but the behavior differs based on the `static` parameter.

### The `static` Parameter Contract

When accessing values with resolvers, the `static` parameter controls the return type:

| `static` | Return Type | Behavior |
|----------|-------------|----------|
| `True` | Always direct data | No resolver trigger, returns cached/stored value |
| `False` | Data OR coroutine | May trigger resolver; returns coroutine if in async context and cache expired |

### Sync Context

In synchronous code, resolvers work transparently - **no special handling required**. Even async resolvers are automatically awaited via `@smartasync`:

```python
from genro_bag import Bag
from genro_bag.resolvers import UrlResolver

bag = Bag()
bag['api'] = UrlResolver('https://api.example.com/data')

# In a regular function - works directly, even with async resolvers
def get_data():
    return bag.get_item('api', static=False)  # Always returns data
```

### Async Context

In async code with `static=False`, the result may be a coroutine when the resolver needs to load fresh data. Use `smartawait` to handle both cases:

```python
from genro_bag import Bag
from genro_bag.resolvers import UrlResolver
from genro_toolbox import smartawait

bag = Bag()
bag['api'] = UrlResolver('https://api.example.com/data', cache_time=300)

# RECOMMENDED: Use smartawait to handle both data and coroutine
async def get_data():
    result = await smartawait(bag.get_item('api', static=False))
    return result
```

Or explicitly check for coroutine:

```python
import inspect

async def get_data():
    result = bag.get_item('api', static=False)
    if inspect.iscoroutine(result):
        result = await result
    return result
```

### When Does It Return a Coroutine?

In async context with `static=False`:

- **Returns data directly** if:
  - Value is cached and not expired
  - No resolver attached (static value)

- **Returns coroutine** if:
  - Resolver present AND cache expired (needs fresh load)

### Safe Pattern for Async Code

```python
from genro_toolbox import smartawait

async def safe_get(bag, path):
    """Always-safe getter for async code."""
    return await smartawait(bag.get_item(path, static=False))
```

### Async Callbacks

You can also use async functions as callbacks:

```python
from genro_bag import Bag
from genro_bag.resolvers import BagCbResolver
from genro_toolbox import smartawait

async def fetch_data():
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get('https://api.example.com/data') as resp:
            return await resp.json()

bag = Bag()
bag['data'] = BagCbResolver(fetch_data)

# In async context, use smartawait
async def get_data():
    return await smartawait(bag.get_item('data', static=False))
```

## read_only Mode

Controls how resolved values are stored:

### read_only=False (base default)

- Value computed and stored in node._value
- Subsequent access returns stored value
- Good for expensive one-time loads

### read_only=True

- Value computed on every access (respecting cache)
- Result NOT stored in node._value
- Good for frequently changing data

**Note**: `read_only=True` is forced to `False` when `cache_time != 0`. This is because
caching inherently requires storing the value. If you need true read-only behavior
(recompute on every access), set `cache_time=0`.

```python
# Cached resolver - read_only is effectively False
bag['cached'] = UrlResolver(
    'https://api.example.com/data',
    cache_time=300  # read_only forced to False
)

# True read-only - recompute every time
bag['dynamic'] = BagCbResolver(
    get_current_time,
    cache_time=0,
    read_only=True
)
```

## Modifying Nodes with Resolvers

When a node has a resolver attached, you cannot simply overwrite its value with `set_item`. This protects against accidental data loss - the resolver represents a data source that should be explicitly handled.

### Default Behavior: Raise Error

```python
from genro_bag import Bag
from genro_bag.resolvers import BagCbResolver

bag = Bag()
bag['data'] = BagCbResolver(lambda: 'computed')

# This raises BagNodeException!
bag.set_item('data', 'new_value')
# Error: Cannot set value on node 'data' with resolver.
# Use resolver=False to remove resolver, or resolver=NewResolver to replace it.
```

### Remove Resolver and Set Value

Use `resolver=False` to explicitly remove the resolver:

```python
bag.set_item('data', 'plain_value', resolver=False)

node = bag.get_node('data')
node.resolver  # None - resolver removed
node.value     # 'plain_value'
```

### Replace Resolver

Provide a new resolver to replace the existing one:

```python
new_resolver = BagCbResolver(lambda: 'new_computed')
bag.set_item('data', None, resolver=new_resolver)

node = bag.get_node('data')
node.resolver  # new_resolver
```

### Bracket Notation with Resolvers

The bracket notation `bag['path'] = value` checks if the value is a resolver:

```python
# This works - assigning a resolver
bag['data'] = BagCbResolver(lambda: 'computed')

# This raises error - trying to overwrite resolver with plain value
bag['data'] = 'plain_value'  # BagNodeException!

# To replace, use set_item explicitly
bag.set_item('data', 'plain_value', resolver=False)
```

## Serialization

Resolvers are serializable with TYTX:

```python
from genro_bag import Bag
from genro_bag.resolvers import UrlResolver

bag = Bag()
bag['api'] = UrlResolver('https://api.example.com')

# Resolver is preserved
tytx = bag.to_tytx()
restored = Bag.from_tytx(tytx)

# Restored bag has the same resolver
restored['api']  # Triggers HTTP request
```

## Next Steps

- Learn about [Subscriptions](subscriptions.md) for reactivity
- Explore [Builders](builders/index.md) for domain-specific structures
- Return to [Basic Usage](basic-usage.md)
