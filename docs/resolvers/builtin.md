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

DirectoryResolver defaults to `cache_time=500`.

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

OpenApiResolver defaults to `cache_time=-1` (infinite).

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

## Common Parameters

All resolvers support:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `cache_time` | varies | Cache duration: 0=none, >0=seconds, <0=infinite |
| `read_only` | False | If True, value not stored in node |

**Note:** When `cache_time != 0`, `read_only` is forced to False.

## Resolver Defaults

| Resolver | `cache_time` |
|----------|--------------|
| `BagCbResolver` | 0 |
| `UrlResolver` | 300 |
| `DirectoryResolver` | 500 |
| `OpenApiResolver` | -1 |
| `TxtDocResolver` | 0 |
| `SerializedBagResolver` | 0 |
