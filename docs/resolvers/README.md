# Resolvers

Values that compute themselves: lazy loading, API calls, file watches, computed properties.

## When Do You Need Resolvers?

- Values come from **external sources** (APIs, databases, files)
- Computation is **expensive** (only compute when accessed)
- Data **changes over time** (fetch fresh or use cache)
- You want **transparent access** (code doesn't know it's dynamic)

## Quick Start

```python
from genro_bag import Bag
from genro_bag.resolvers import BagCbResolver, UrlResolver

bag = Bag()

# Computed on each access
bag['now'] = BagCbResolver(lambda: datetime.now().isoformat())

# Fetched from network, cached 5 minutes
bag['api'] = UrlResolver('https://api.example.com/data', cache_time=300)

# Access looks the same as static values
bag['now']  # '2025-01-15T10:30:45.123456'
bag['api']  # Fetches and returns data
```

## The Key Insight

Without resolvers:
```python
bag['data'] = fetch_from_api()  # Called immediately
```

With resolvers:
```python
bag['data'] = UrlResolver('https://...')  # Nothing happens yet
result = bag['data']  # NOW the API is called
```

## Built-in Resolvers

| Resolver | Purpose |
|----------|---------|
| `BagCbResolver` | Python callback function |
| `UrlResolver` | HTTP requests (GET, POST, etc.) |
| `DirectoryResolver` | Load directory as Bag hierarchy |
| `OpenApiResolver` | Navigate OpenAPI specifications |
| `TxtDocResolver` | Load file content |
| `SerializedBagResolver` | Load serialized Bag files |
| `EnvResolver` | Read environment variables |
| `UuidResolver` | Generate UUID strings |

## Caching

```python
# No cache - compute every time
bag['dynamic'] = BagCbResolver(func, cache_time=0)

# Cache 5 minutes
bag['cached'] = BagCbResolver(func, cache_time=300)

# Cache forever (until manual reset)
bag['permanent'] = BagCbResolver(func, cache_time=False)

# Active cache — background refresh every 30 seconds (async only)
bag['live'] = BagCbResolver(func, cache_time=-30)

# Reset cache manually
bag.get_node('cached').resolver.reset()
```

## Async Support

```python
# In sync code - just works
result = bag['data']

# In async code - use smartawait
from genro_toolbox import smartawait
result = await smartawait(bag.get_item('data'))
```

## Custom Resolvers

```python
from genro_bag.resolver import BagResolver

class DatabaseResolver(BagResolver):
    class_args = ['query']
    class_kwargs = {'connection': None, 'cache_time': 60}

    def load(self):
        return self.kw['connection'].execute(self.kw['query'])

# Usage
bag['users'] = DatabaseResolver('SELECT * FROM users', connection=db)
```

## Documentation

- [Built-in Resolvers](builtin.md) — All resolver types
- [Custom Resolvers](custom.md) — Create your own
- [Examples](examples.md) — Practical patterns
- [FAQ](faq.md) — Common questions

## Related

- **Need to react to changes?** → [Subscriptions](../subscriptions/)
