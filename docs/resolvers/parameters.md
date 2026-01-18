# Resolver Parameters

How to pass parameters to resolvers at call time.

## Two Ways to Pass Parameters

### 1. Via `get_item()` kwargs

```python
bag.get_item('calc', multiplier=5)
```

### 2. Via Path Syntax (Query String)

```python
bag['calc?multiplier=5::L']
```

Both methods pass parameters to the resolver with the same effect.

## Path Syntax Reference

| Pattern | Result | Description |
|---------|--------|-------------|
| `node?factor=5` | `resolver(factor='5')` | String value |
| `node?factor=5::L` | `resolver(factor=5)` | Integer (Long) |
| `node?price=34.5::F` | `resolver(price=34.5)` | Float |
| `node?date=2025-01-18::D` | `resolver(date=date(2025,1,18))` | Date |
| `node?x=5::L&y=10::L` | `resolver(x=5, y=10)` | Multiple params |
| `node?_body={"a":1}::JS` | `resolver(_body={'a':1})` | JSON object |

### Type Suffixes

Values use [TYTX type suffixes](../../tytx.md):

| Suffix | Type | Example |
|--------|------|---------|
| `::L` | int (long) | `5::L` → `5` |
| `::F` | float | `3.14::F` → `3.14` |
| `::D` | date | `2025-01-18::D` → `date(2025,1,18)` |
| `::B` | bool | `true::B` → `True` |
| `::JS` | JSON | `{"a":1}::JS` → `{'a':1}` |

## Complete Example

```python
from genro_bag import Bag
from genro_bag.resolver import BagCbResolver

def multiply(base, factor=1):
    return base * factor

bag = Bag()
bag['calc'] = BagCbResolver(multiply, base=10)

# Default: factor=1
bag['calc']  # 10

# Via get_item kwargs
bag.get_item('calc', factor=5)  # 50

# Via path syntax (equivalent)
bag['calc?factor=5::L']  # 50

# Multiple parameters
bag['calc?base=20::L&factor=3::L']  # 60
```

## Complex Parameters with JSON

For complex values, use `::JS`:

```python
bag['api?_body={"name":"test","value":100}::JS']
```

Can be combined with other parameters:

```python
bag['api?method=POST&_body={"data":[1,2,3]}::JS&timeout=30::L']
```

## Parameter Priority

When multiple sources provide the same parameter:

1. **Path syntax / call kwargs** (highest priority)
2. **Node attributes** (`bag.set_attr('node', param=value)`)
3. **Resolver defaults** (lowest priority)

```python
bag['calc'] = BagCbResolver(multiply, base=10, factor=2)  # defaults

bag.set_attr('calc', factor=3)  # node attribute

bag['calc']                  # 30 (uses node attr factor=3)
bag['calc?factor=5::L']      # 50 (path syntax overrides)
bag.get_item('calc', factor=7)  # 70 (kwargs override)
```

## Navigating Resolved Values

When a resolver returns a Bag or JSON (with `as_bag=True`), the result is cached in the node and can be navigated with standard path syntax:

```python
from genro_bag import Bag
from genro_bag.resolvers import UrlResolver

bag = Bag()
bag['api'] = UrlResolver(
    'https://api.example.com/users',
    as_bag=True,
    cache_time=300
)

# First access triggers HTTP request, result cached as Bag
bag['api']  # Returns Bag with user data

# Navigate into cached result
bag['api.users.0.name']      # 'Alice'
bag['api.users.0.email']     # 'alice@example.com'

# Pass parameters and navigate result
bag['api?status=active::L.users.0.name']
```

The resolved Bag becomes the node's value, so subsequent path navigation doesn't re-trigger the resolver (until cache expires).

## Error Handling

Using `?key=value` syntax on a node without resolver raises an error:

```python
bag['static_node'] = 42
bag['static_node?x=5']  # Raises BagNodeException
```

This syntax is only valid for nodes with resolvers.
