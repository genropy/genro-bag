# Built-in Resolvers

## BagCbResolver (Callback)

Execute a Python callable on demand.

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.resolvers import BagCbResolver

>>> def compute():
...     return 42 * 2

>>> bag = Bag()
>>> bag['result'] = BagCbResolver(compute)
>>> bag['result']
84
```

### With Arguments

```python
def fetch_user(user_id):
    return database.get_user(user_id)

bag['user'] = BagCbResolver(fetch_user, 'u123')
```

### With Caching

```python
call_count = 0
def expensive():
    global call_count
    call_count += 1
    return {'result': 42, 'calls': call_count}

# Cache for 60 seconds
bag['data'] = BagCbResolver(expensive, cache_time=60)

bag['data']  # {'result': 42, 'calls': 1}
bag['data']  # {'result': 42, 'calls': 1} - cached
```

### Async Callbacks

```python
async def fetch_async():
    async with aiohttp.ClientSession() as session:
        async with session.get('https://api.example.com') as resp:
            return await resp.json()

bag['api'] = BagCbResolver(fetch_async)
```

## UrlResolver

Fetch content from HTTP URLs.

```python
from genro_bag import Bag
from genro_bag.resolvers import UrlResolver

bag = Bag()
bag['api'] = UrlResolver('https://api.example.com/data')

# Access triggers HTTP request
data = bag['api']  # Returns bytes
```

### Parse as Bag

```python
# Auto-parse JSON/XML response
bag['users'] = UrlResolver(
    'https://api.example.com/users',
    as_bag=True,
    cache_time=300
)

users = bag['users']  # Returns Bag
```

### HTTP Methods

```python
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

### Default Cache

UrlResolver defaults to `cache_time=300` (5 minutes).

## DirectoryResolver

Load a directory structure as a Bag hierarchy.

```python
from genro_bag import Bag
from genro_bag.resolvers import DirectoryResolver

bag = Bag()
bag['config'] = DirectoryResolver('/path/to/config/')

# Directory structure becomes Bag:
# /path/to/config/
#   database.xml    -> bag['config.database']
#   logging.json    -> bag['config.logging']
#   subdir/         -> bag['config.subdir'] (recursive)
```

### Supported Files

- `.xml` - Parsed as XML
- `.bag.json` - Parsed as TYTX JSON
- `.bag.mp` - Parsed as TYTX MessagePack

### Default Cache

DirectoryResolver defaults to `cache_time=0` (rescan on each access).

## OpenApiResolver

Navigate OpenAPI specifications.

```python
from genro_bag import Bag
from genro_bag.resolvers import OpenApiResolver

bag = Bag()
bag['api'] = OpenApiResolver('https://petstore3.swagger.io/api/v3/openapi.json')

# Access triggers fetch and parse
api = bag['api']

# Structure organized by tags
api['info']                    # API description
api['api']['pet'].keys()       # ['addPet', 'updatePet', ...]
api['api']['store'].keys()     # ['getInventory', 'placeOrder', ...]

# Access operation details
op = api['api']['pet']['findPetsByStatus']
op['summary']                  # 'Finds Pets by status'
op['method']                   # 'get'
op['path']                     # '/pet/findByStatus'
```

### Default Cache

OpenApiResolver defaults to `cache_time=False` (infinite).

## TxtDocResolver

Load file content as raw bytes.

```python
from genro_bag import Bag
from genro_bag.resolvers import TxtDocResolver

bag = Bag()
bag['readme'] = TxtDocResolver('/path/to/readme.txt')

content = bag['readme']  # Returns bytes
text = content.decode('utf-8')
```

## SerializedBagResolver

Load a serialized Bag file.

```python
from genro_bag import Bag
from genro_bag.resolvers import SerializedBagResolver

bag = Bag()
bag['config'] = SerializedBagResolver('/path/to/config.xml')
bag['data'] = SerializedBagResolver('/path/to/data.bag.json')

# Access triggers file read and parse
config = bag['config']  # Returns Bag
config['database.host']
```

### Supported Formats

- `.xml` - XML format
- `.bag.json` - TYTX JSON
- `.bag.mp` - TYTX MessagePack

## FileResolver

Lazily load a file with automatic format detection by extension.

```python
from genro_bag import Bag
from genro_bag.resolvers import FileResolver

bag = Bag()

# Text files — returned as string
bag['style'] = FileResolver('/path/to/style.css')
bag['readme'] = FileResolver('/path/to/readme.md')

# JSON — returned as dict/list (or Bag with as_bag=True)
bag['config'] = FileResolver('/path/to/config.json')
bag['data'] = FileResolver('/path/to/data.json', as_bag=True)

# CSV — returned as Bag of records
bag['contacts'] = FileResolver('/path/to/contacts.csv')

# Native Bag formats — returned as Bag
bag['settings'] = FileResolver('/path/to/settings.bag.json')
```

### Format Detection

| Extension | Returns | Notes |
| --- | --- | --- |
| `.txt`, `.css`, `.html`, `.md` | `str` | Text content |
| `.json` | `dict`/`list`/scalar | Bag if `as_bag=True` |
| `.csv` | `Bag` | Rows as nodes with column attributes |
| `.bag.json`, `.bag.mp`, `.xml` | `Bag` | Delegates to `fill_from` |
| (other) | `str` | Fallback to text |

### CSV Structure

Each row becomes a Bag node with column values as attributes:

```python
# contacts.csv:
# name,age,city
# Alice,30,NYC
# Bob,25,LA

bag['contacts'] = FileResolver('/path/to/contacts.csv')
contacts = bag['contacts']

node = contacts.get_node('r0')
node.attr['name']   # 'Alice'
node.attr['age']    # '30'
node.attr['city']   # 'NYC'
```

Without headers (`csv_has_header=False`), attributes are named `c0`, `c1`, `c2`, etc.

### Relative Paths

```python
# Resolve relative to a base directory
bag['style'] = FileResolver('static/style.css', base_path='/app')

# Without base_path, resolves relative to cwd
bag['style'] = FileResolver('style.css')
```

### Parameters

| Parameter | Default | Description |
| --- | --- | --- |
| `path` | (required) | File path (absolute or relative) |
| `base_path` | `None` | Base directory for relative paths (default: cwd) |
| `encoding` | `"utf-8"` | Text encoding |
| `csv_delimiter` | `","` | CSV column delimiter |
| `csv_has_header` | `True` | Whether first CSV row is headers |

FileResolver defaults to `cache_time=0` (re-read every time) and `read_only=True`.

## EnvResolver

Read an environment variable on demand, with optional caching.

```python
from genro_bag import Bag
from genro_bag.resolvers import EnvResolver

bag = Bag()
bag['db_host'] = EnvResolver('DATABASE_HOST', default='localhost')
bag['db_port'] = EnvResolver('DATABASE_PORT', default='5432')

bag['db_host']  # reads os.environ['DATABASE_HOST'] or 'localhost'
```

### Live Updates

With `cache_time=0` (default), every access re-reads the variable:

```python
import os

bag['mode'] = EnvResolver('APP_MODE', default='development')
bag['mode']  # 'development'

os.environ['APP_MODE'] = 'production'
bag['mode']  # 'production' — picked up immediately
```

### Caching

With `cache_time=N`, the value is cached for N seconds:

```python
bag['secret'] = EnvResolver('API_KEY', cache_time=60)
bag['secret']  # reads from os.environ
bag['secret']  # cached for 60 seconds
```

EnvResolver defaults to `cache_time=0` (re-read every time).

## UuidResolver

Generate a UUID string on first access, cached forever by default.

```python
from genro_bag import Bag
from genro_bag.resolvers import UuidResolver

bag = Bag()
bag['session_id'] = UuidResolver()
bag['session_id']  # '550e8400-e29b-41d4-a716-446655440000'
bag['session_id']  # same UUID (cached with cache_time=False)
```

### UUID Versions

```python
bag['random_id'] = UuidResolver()          # uuid4 (default, random)
bag['ts_id'] = UuidResolver('uuid1')       # uuid1 (timestamp-based)
```

### Regenerate

```python
node = bag.get_node('session_id')
node.value.reset()       # invalidate cache
bag['session_id']        # new UUID generated
```

UuidResolver defaults to `cache_time=False` (infinite cache).

## Common Parameters

All resolvers support three independent parameters:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `cache_time` | varies | Cache: 0=none, >0=passive TTL (int or float seconds), <0=active refresh (async only), False=infinite |
| `read_only` | False | If True, value is NOT stored in `node._value` |
| `as_bag` | None | If True, convert result to Bag; if None, follows `read_only` |

### Parameter Behavior

The three parameters are **independent**:

- **`cache_time`**: Controls the resolver's internal cache (TTL-based)
- **`read_only`**: Controls whether the value is stored in the Bag node
- **`as_bag`**: Controls automatic conversion to Bag

### Truth Table

| cache_time | read_only | as_bag | Where stored | Converts to Bag |
|------------|-----------|--------|--------------|-----------------|
| 0 | True | [False] | nowhere | No |
| 0 | True | True | nowhere | Yes |
| 0 | True | False | nowhere | No |
| 0 | [False] | [True] | node | Yes |
| 0 | [False] | True | node | Yes |
| 0 | [False] | False | node | No |
| !=0 | True | [False] | cache | No |
| !=0 | True | True | cache | Yes |
| !=0 | True | False | cache | No |
| !=0 | [False] | [True] | node | Yes |
| !=0 | [False] | True | node | Yes |
| !=0 | [False] | False | node | No |

Where `[value]` indicates the computed default: `as_bag` defaults to `not read_only`.

### Practical Implications

- **`read_only=False`** (default): The resolved value becomes part of the Bag and can be navigated with dot notation. Default `as_bag=True` converts the result to Bag automatically.

- **`read_only=True`**: The resolver acts like a "virtual" node - each access triggers resolution, the value is not stored in the Bag tree. Default `as_bag=False` returns raw values.

- **`cache_time != 0`**: The resolver maintains its own internal cache (in `_cached_value`), independent from where the value is stored.

## Resolver Defaults

| Resolver | `cache_time` |
|----------|--------------|
| `BagCbResolver` | 0 |
| `EnvResolver` | 0 |
| `FileResolver` | 0 |
| `UuidResolver` | False |
| `UrlResolver` | 300 |
| `DirectoryResolver` | 0 |
| `OpenApiResolver` | False |
| `TxtDocResolver` | 500 |
| `SerializedBagResolver` | 500 |
