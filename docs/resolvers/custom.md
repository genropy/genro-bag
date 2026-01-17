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
        arg1 = self._kw['arg1']
        arg2 = self._kw['arg2']
        my_option = self._kw['my_option']

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
        query = self._kw['query']
        conn = self._kw['connection']

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
        key = self._kw['key']
        client = self._kw['redis_client']

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
        url = self._kw['url']
        headers = self._kw['headers'] or {}

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
result = await smartawait(bag.get_item('data', static=False))
```

## Example: File Watcher

```python
from genro_bag.resolver import BagResolver
from pathlib import Path
import json

class JsonFileResolver(BagResolver):
    """Load JSON file, re-read when file changes."""

    class_args = ['filepath']
    class_kwargs = {
        'cache_time': 0,  # Always check
        'read_only': True
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_mtime = None

    def load(self):
        path = Path(self._kw['filepath'])
        mtime = path.stat().st_mtime

        if self._last_mtime != mtime:
            self._last_mtime = mtime
            with open(path) as f:
                self._cached_data = json.load(f)

        return self._cached_data

# Usage
bag = Bag()
bag['config'] = JsonFileResolver('/etc/myapp/config.json')
```

## Returning a Bag

When your resolver returns a Bag, users can navigate into it:

```python
class NestedDataResolver(BagResolver):
    class_args = ['source']
    class_kwargs = {'cache_time': 300}

    def load(self):
        data = fetch_data(self._kw['source'])

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

## Best Practices

### 1. Set Appropriate Cache Times

```python
# Frequently changing data
class_kwargs = {'cache_time': 0}  # No cache

# API data
class_kwargs = {'cache_time': 300}  # 5 minutes

# Static reference data
class_kwargs = {'cache_time': -1}  # Infinite
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
        +load() value
        +reset()
    }

    class YourCustomResolver {
        +class_args = ['query']
        +class_kwargs = connection: None
        +load() executes query
    }
```
