# Custom Resolvers

Create resolvers for your own data sources by extending `BagResolver`.

## Basic Structure

```python
from genro_bag.resolver import BagResolver

class MyResolver(BagResolver):
    # Positional arguments (required)
    class_args = ['arg1', 'arg2']

    # Keyword arguments with defaults
    class_kwargs = {
        'cache_time': 0,
        'read_only': False,
        'my_option': 'default'
    }

    def load(self):
        """Called when value is accessed. Return the resolved value."""
        arg1 = self.kw['arg1']
        arg2 = self.kw['arg2']
        my_option = self.kw['my_option']

        # Your logic here
        return computed_value
```

## Example: Database Resolver

```python
from genro_bag.resolver import BagResolver
from genro_bag import Bag

class DatabaseResolver(BagResolver):
    """Load data from a database query."""

    class_args = ['query']
    class_kwargs = {
        'cache_time': 60,
        'read_only': False,
        'connection': None
    }

    def load(self):
        query = self.kw['query']
        conn = self.kw['connection']

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

## Example: Redis Resolver

```python
from genro_bag.resolver import BagResolver
import json

class RedisResolver(BagResolver):
    """Load JSON data from Redis."""

    class_args = ['key']
    class_kwargs = {
        'cache_time': 30,
        'read_only': False,
        'redis_client': None
    }

    def load(self):
        key = self.kw['key']
        client = self.kw['redis_client']

        data = client.get(key)
        if data is None:
            return None
        return json.loads(data)

# Usage
bag = Bag()
bag['session'] = RedisResolver('user:123:session', redis_client=redis)
```

## Example: Async Resolver

```python
from genro_bag.resolver import BagResolver
import aiohttp

class AsyncApiResolver(BagResolver):
    """Async HTTP API resolver."""

    class_args = ['url']
    class_kwargs = {
        'cache_time': 300,
        'read_only': False,
        'headers': None
    }

    async def load(self):
        url = self.kw['url']
        headers = self.kw['headers'] or {}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                return await resp.json()

# Usage (in async context)
from genro_toolbox import smartawait

bag = Bag()
bag['data'] = AsyncApiResolver(
    'https://api.example.com/data',
    headers={'Authorization': 'Bearer xxx'}
)

# Access
result = await smartawait(bag.get_item('data'))
```

## Example: File Watcher with mtime Check

> **Note:** For simple file loading (JSON, CSV, text, XML), use the built-in
> [`FileResolver`](builtin.md#fileresolver). The example below shows how to
> extend behavior with a custom mtime-based change detection.

```python
from genro_bag.resolver import BagResolver
from pathlib import Path
import json

class MtimeJsonResolver(BagResolver):
    """Load JSON file, re-read only when file modification time changes."""

    class_args = ['filepath']
    class_kwargs = {
        'cache_time': 0,  # Always check mtime
        'read_only': True
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_mtime = None

    def load(self):
        path = Path(self.kw['filepath'])
        mtime = path.stat().st_mtime

        if self._last_mtime != mtime:
            self._last_mtime = mtime
            with open(path) as f:
                self._cached_data = json.load(f)

        return self._cached_data

# Usage
bag = Bag()
bag['config'] = MtimeJsonResolver('/etc/myapp/config.json')
```

## Returning a Bag

When your resolver returns a Bag, users can navigate into it:

```python
class NestedDataResolver(BagResolver):
    class_args = ['source']
    class_kwargs = {'cache_time': 300}

    def load(self):
        data = fetch_data(self.kw['source'])

        bag = Bag()
        for key, value in data.items():
            bag[key] = value
        return bag

# Usage
bag = Bag()
bag['data'] = NestedDataResolver('my_source')

# Access nested values
bag['data']['nested.key']
```

## Custom Transforms: `on_loading` and `on_loaded`

Subclasses can plug pre/post-processing around `load()` / `async_load()` by
overriding two instance methods:

- **`on_loading(kw) -> kw`**: transform kwargs before the load. Default
  implementation is identity (returns `kw` unchanged).
- **`on_loaded(result) -> result`**: adapt the load result. Default
  implementation is identity. Runs **after** the `as_bag` conversion in
  `_prepare_result`, so if `as_bag=True` the hook receives the converted Bag.

### Reading state: `self.kw` vs `self._kw`

Inside `load()` / `async_load()`, always read parameters from **`self.kw`**
(not `self._kw`). `self.kw` is a property that returns `self.on_loading(self._kw)`,
so any transformation you inject via `on_loading` is visible to the load:

```python
class MultiplyingResolver(BagResolver):
    class_args = ['base']
    class_kwargs = {'multiplier': 1}

    def on_loading(self, kw):
        # Normalize: ensure multiplier is int
        return {**kw, 'multiplier': int(kw['multiplier'])}

    def load(self):
        # Reads transformed kwargs via self.kw
        return self.kw['base'] * self.kw['multiplier']
```

`self._kw` still exists as the raw underlying state (used by `set_attr`,
serialization, child resolver creation). You normally do not touch it.

### Contract: `on_loading` must return a complete dict

Some resolvers iterate over `self.kw.items()` to pick up dynamic kwargs
(e.g. `UrlResolver` collects extra query-string parameters). `on_loading`
must return a dict with **all** the input keys — not a delta — or downstream
code may drop parameters.

```python
def on_loading(self, kw):
    # CORRECT: start from kw, then modify
    return {**kw, 'timeout': kw.get('timeout') or 30}

def on_loading(self, kw):
    # WRONG: loses every key except 'timeout'
    return {'timeout': 30}
```

### Example: adapting the result with `on_loaded`

```python
class JsonApiResolver(BagResolver):
    class_args = ['url']
    class_kwargs = {'as_bag': True}

    async def async_load(self):
        async with httpx.AsyncClient() as client:
            r = await client.get(self.kw['url'])
            return r.json()

    def on_loaded(self, result):
        # as_bag=True has already converted result to Bag before this hook;
        # decorate it with a fetch timestamp
        if isinstance(result, Bag):
            result.set_attr('_fetched_at', datetime.now().isoformat())
        return result
```

### No runtime injection

Hooks are **override-only**. There is no constructor parameter accepting a
callable, no string-based binding. Subclass the resolver and redefine the
hook methods, exactly like the existing `init()` hook.

## Best Practices

### 1. Set Appropriate Cache Times

```python
# Frequently changing data
class_kwargs = {'cache_time': 0}  # No cache

# API data
class_kwargs = {'cache_time': 300}  # 5 minutes

# Static reference data
class_kwargs = {'cache_time': False}  # Infinite

# Active cache — auto-refresh every 60 seconds (async only)
class_kwargs = {'cache_time': -60}
```

### 2. Handle Errors Gracefully

```python
def load(self):
    try:
        return self._fetch_data()
    except ConnectionError:
        return None  # Or raise with context
```

### 3. Document Your Resolver

```python
class MyResolver(BagResolver):
    """Short description of what this resolver does.

    Args:
        source: Where to fetch data from
        cache_time: How long to cache (default: 60)

    Returns:
        Bag with the fetched data structure
    """
```

### 4. Use Type Hints

```python
from genro_bag.resolver import BagResolver
from genro_bag import Bag
from typing import Any

class TypedResolver(BagResolver):
    class_args: list[str] = ['url']
    class_kwargs: dict[str, Any] = {'cache_time': 60}

    def load(self) -> Bag:
        ...
```

## Architecture

```{mermaid}
classDiagram
    BagResolver <|-- YourCustomResolver

    class BagResolver {
        +class_args: list
        +class_kwargs: dict
        -_kw: dict
        -_cache_time
        -_cached_value
        -_cache_timestamp
        +kw: dict
        +load() value
        +on_loading(kw) kw
        +on_loaded(result) result
        +reset()
    }

    class YourCustomResolver {
        +class_args = ['query']
        +class_kwargs = connection: None
        +load() executes query
    }
```
