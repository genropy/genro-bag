# Sync and Async

Resolvers work seamlessly in both synchronous and asynchronous contexts. This guide explains how.

## The Four Cases

When you access a resolver value, the system handles four possible combinations:

| Resolver Type | Execution Context | What Happens |
|--------------|-------------------|--------------|
| Sync (`load()`) | Sync | Direct call to `load()` |
| Sync (`load()`) | Async | `load()` wrapped with `@smartasync` |
| Async (`async_load()`) | Sync | `async_load()` run synchronously via `smartasync` |
| Async (`async_load()`) | Async | `await async_load()` |

**Key point:** You don't need to worry about this. The resolver handles it automatically.

## Writing Resolvers

### Sync Resolver

Override `load()` for synchronous operations:

```python
from genro_bag.resolver import BagResolver

class FileResolver(BagResolver):
    class_args = ['path']

    def load(self):
        with open(self._kw['path']) as f:
            return f.read()
```

### Async Resolver

Override `async_load()` for asynchronous operations:

```python
from genro_bag.resolver import BagResolver
import httpx

class ApiResolver(BagResolver):
    class_args = ['url']
    class_kwargs = {'cache_time': 300}

    async def async_load(self):
        async with httpx.AsyncClient() as client:
            response = await client.get(self._kw['url'])
            return response.json()
```

## Accessing Values

### In Sync Code

```python
from genro_bag import Bag
from genro_bag.resolvers import UrlResolver

bag = Bag()
bag['api'] = UrlResolver('https://api.example.com/data')

# Just access the value - works with both sync and async resolvers
data = bag['api']
```

### In Async Code

Use `get_item()` with `static=False` and `smartawait`:

```python
from genro_bag import Bag
from genro_bag.resolvers import UrlResolver
from genro_toolbox import smartawait

bag = Bag()
bag['api'] = UrlResolver('https://api.example.com/data')

async def fetch_data():
    # Use get_item + smartawait for async access
    data = await smartawait(bag.get_item('api', static=False))
    return data
```

## Why `smartawait`?

In async context, `bag.get_item('api', static=False)` may return:
- The value directly (if cached)
- A coroutine (if resolver needs to load)

`smartawait` handles both cases:

```python
from genro_toolbox import smartawait

# Always safe - works whether result is value or coroutine
result = await smartawait(bag.get_item('api', static=False))
```

## The `static` Parameter

| `static` | Behavior |
|----------|----------|
| `True` | Return cached value only, never trigger resolver |
| `False` | Trigger resolver if needed (default for `get_item`) |

```python
# Check if value is cached without triggering load
cached = bag.get_item('api', static=True)
if cached is None:
    print("Not loaded yet")

# Trigger load if needed
data = bag.get_item('api', static=False)
```

## Complete Example

```python
from genro_bag import Bag
from genro_bag.resolver import BagResolver
from genro_toolbox import smartawait
import httpx

# Define an async resolver
class WeatherResolver(BagResolver):
    class_args = ['city']
    class_kwargs = {'cache_time': 600}  # Cache for 10 minutes

    async def async_load(self):
        url = f'https://api.weather.com/{self._kw["city"]}'
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            return response.json()

# Setup
bag = Bag()
bag['weather'] = WeatherResolver('rome')

# === SYNC CONTEXT ===
# Works! Resolver runs synchronously via smartasync
weather = bag['weather']
print(weather['temperature'])

# === ASYNC CONTEXT ===
async def main():
    # Use get_item + smartawait
    weather = await smartawait(bag.get_item('weather', static=False))
    print(weather['temperature'])

import asyncio
asyncio.run(main())
```

## How It Works Internally

The resolver's `_dispatch_load()` method detects the context:

```
is_async?        in_async_context?        Action
─────────────────────────────────────────────────────
False            False                    → load()
False            True                     → @smartasync load()
True             False                    → smartasync(async_load)()
True             True                     → await async_load()
```

- `is_async`: True if resolver overrides `async_load()`
- `in_async_context`: True if running inside an event loop

## Best Practices

### 1. Choose the Right Type

```python
# Use sync (load) for:
# - File system operations
# - CPU-bound computations
# - Libraries without async support

# Use async (async_load) for:
# - HTTP requests
# - Database queries with async drivers
# - Any I/O that benefits from concurrency
```

### 2. In Async Code, Always Use smartawait

```python
# ❌ WRONG - might get a coroutine
data = bag['api']

# ✅ CORRECT
data = await smartawait(bag.get_item('api', static=False))
```

### 3. Use static=True to Check Cache

```python
# Check without triggering load
if bag.get_item('api', static=True) is None:
    print("Will need to fetch")
```

### 4. Leverage Caching

```python
# First access triggers load
data1 = bag['api']  # HTTP request happens

# Second access returns cached value
data2 = bag['api']  # No request, instant return
```

## Summary

| Context | How to Access |
|---------|--------------|
| Sync code | `bag['key']` or `bag.get_item('key')` |
| Async code | `await smartawait(bag.get_item('key', static=False))` |

The resolver system automatically bridges sync/async boundaries, so you can:
- Use async resolvers in sync code (they run synchronously)
- Use sync resolvers in async code (they're wrapped appropriately)
