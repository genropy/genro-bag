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

Navigate OpenAPI specifications:

```python
from genro_bag import Bag
from genro_bag.resolvers import OpenApiResolver

bag = Bag()
bag['api'] = OpenApiResolver('https://petstore.swagger.io/v3/openapi.json')

# Access API structure
bag['api.paths']
bag['api.components.schemas']
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

All resolvers support these parameters:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `cache_time` | 0 | Cache duration in seconds (0=none, <0=infinite) |
| `read_only` | True | If False, resolved value is stored in node |

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

## Async Resolvers

All resolvers support async operations via `smartasync`:

```python
from genro_bag import Bag
from genro_bag.resolvers import BagCbResolver

async def fetch_data():
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get('https://api.example.com/data') as resp:
            return await resp.json()

bag = Bag()
bag['data'] = BagCbResolver(fetch_data)

# Works in both sync and async contexts
data = bag['data']  # Automatically handles async
```

## read_only Mode

Controls how resolved values are stored:

### read_only=True (default)

- Value computed on every access (respecting cache)
- Result NOT stored in node._value
- Good for frequently changing data

### read_only=False

- Value computed and stored in node._value
- Subsequent access returns stored value
- Good for expensive one-time loads

```python
# Store resolved value in node
bag['heavy'] = UrlResolver(
    'https://api.example.com/large-dataset',
    read_only=False,
    cache_time=-1
)

# First access loads and stores
data1 = bag['heavy']  # HTTP request made

# Second access uses stored value
data2 = bag['heavy']  # No HTTP request
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
