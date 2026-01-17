# Resolvers

Resolvers enable **lazy loading**: instead of storing a value directly, a node can compute or fetch its value on demand.

## When Do You Need Resolvers?

You need resolvers when:

- **Values come from external sources**: API calls, database queries, file reads
- **Computation is expensive**: Only compute when actually accessed
- **Data changes over time**: Fetch fresh data on each access (or with caching)
- **You want transparent access**: Code that reads the value doesn't need to know it's dynamic

## The Core Idea

Without resolvers:
```python
# Value is static, set once
bag['data'] = fetch_from_api()  # Called immediately
```

With resolvers:
```python
# Value is computed on access
bag['data'] = UrlResolver('https://api.example.com/data')
# Nothing fetched yet

result = bag['data']  # NOW the API is called
```

## Quick Example

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.resolvers import BagCbResolver
>>> from datetime import datetime

>>> def get_timestamp():
...     return datetime.now().isoformat()

>>> bag = Bag()
>>> bag['timestamp'] = BagCbResolver(get_timestamp)

>>> # Value computed on access
>>> bag['timestamp']  # doctest: +SKIP
'2025-01-07T10:30:45.123456'
```

## Key Features

### Caching

Control how often values are recomputed:

```python
# Compute every time (default)
bag['dynamic'] = BagCbResolver(func, cache_time=0)

# Cache for 5 minutes
bag['cached'] = BagCbResolver(func, cache_time=300)

# Cache forever (until manual reset)
bag['permanent'] = BagCbResolver(func, cache_time=-1)
```

### Async Support

Resolvers work in both sync and async contexts:

```python
# Sync - just works
result = bag['data']

# Async - use smartawait
from genro_toolbox import smartawait
result = await smartawait(bag.get_item('data', static=False))
```

→ [Sync and Async Guide](sync-async.md)

### Serialization

Resolvers survive serialization with TYTX:

```python
tytx = bag.to_tytx()
restored = Bag.from_tytx(tytx)
# Resolver is preserved!
```

## Built-in Resolvers

| Resolver | Purpose |
|----------|---------|
| `BagCbResolver` | Callback function |
| `UrlResolver` | HTTP requests |
| `DirectoryResolver` | Load directory structure |
| `OpenApiResolver` | Navigate OpenAPI specs |
| `TxtDocResolver` | Load file content |
| `SerializedBagResolver` | Load serialized Bag files |

→ [Built-in Resolvers](builtin.md)

## Creating Custom Resolvers

Extend `BagResolver` for your own data sources:

```python
from genro_bag.resolver import BagResolver

class DatabaseResolver(BagResolver):
    class_args = ['query']
    class_kwargs = {'connection': None, 'cache_time': 60}

    def load(self):
        return self._kw['connection'].execute(self._kw['query'])
```

→ [Custom Resolvers](custom.md)

## What's Next?

```{toctree}
:maxdepth: 1

builtin
sync-async
custom
examples
faq
```
