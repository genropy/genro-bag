# Resolver Parameters Demo

Shows how parameters flow through the resolver system with three priority levels.

## Parameter Priority

When a resolver is called, parameters come from three sources (highest priority first):

1. **call_kwargs**: Passed to `get_item()` or `get_value()` at call time
2. **node.attr**: Attributes set on the parent BagNode
3. **resolver._kw**: Default parameters set at resolver construction

## Basic Example with BagCbResolver

```python
>>> from genro_bag import Bag
>>> from genro_bag.resolver import BagCbResolver
>>>
>>> def multiply(base, multiplier):
...     return base * multiplier
>>>
>>> bag = Bag()
>>> bag['calc'] = BagCbResolver(multiply, base=10, multiplier=2)
>>>
>>> # Level 3: Uses resolver defaults (base=10, multiplier=2)
>>> bag['calc']
20
>>>
>>> # Level 2: Override via node attributes
>>> bag.set_attr('calc', multiplier=5)
>>> bag['calc']
50
>>>
>>> # Level 1: Override via call_kwargs (highest priority)
>>> bag.get_item('calc', multiplier=10)
100
>>>
>>> # Node attr is still there, used when no call_kwargs
>>> bag['calc']
50
```

## Cache Invalidation

Cache is automatically invalidated when effective parameters change:

```python
>>> from genro_bag import Bag
>>> from genro_bag.resolver import BagCbResolver
>>>
>>> call_count = 0
>>> def counter(x):
...     global call_count
...     call_count += 1
...     return x * 2
>>>
>>> bag = Bag()
>>> bag['data'] = BagCbResolver(counter, x=5, cache_time=-1)  # infinite cache
>>>
>>> bag['data']  # First call
10
>>> call_count
1
>>>
>>> bag['data']  # From cache (same params)
10
>>> call_count
1
>>>
>>> bag.set_attr('data', x=7)  # Change param -> invalidates cache
>>> bag['data']  # Recomputed
14
>>> call_count
2
>>>
>>> bag.get_item('data', x=10)  # Different call_kwargs -> recomputed
20
>>> call_count
3
```

## Internal vs User Parameters

Internal parameters (`cache_time`, `read_only`, `retry_policy`) are NOT read from node attributes:

```python
>>> from genro_bag import Bag
>>> from genro_bag.resolver import BagCbResolver
>>>
>>> bag = Bag()
>>> bag['calc'] = BagCbResolver(lambda x: x * 2, x=5, cache_time=60)
>>>
>>> # Setting cache_time on node has NO effect (it's internal)
>>> bag.set_attr('calc', cache_time=0)
>>> bag.get_node('calc').resolver.cache_time
60
>>>
>>> # But user params (x) ARE read from node
>>> bag.set_attr('calc', x=10)
>>> bag['calc']
20
```

## With UrlResolver

UrlResolver supports dynamic parameters for query strings and path substitution:

```python
>>> from genro_bag import Bag
>>> from genro_bag.resolvers import UrlResolver
>>>
>>> bag = Bag()
>>> bag['api'] = UrlResolver(
...     'https://api.example.com/users/{id}',
...     as_bag=True,
...     cache_time=60
... )
>>>
>>> # Pass path parameter via call_kwargs
>>> user = bag.get_item('api', arg_0=123)  # -> /users/123
>>>
>>> # Pass query string params
>>> users = bag.get_item('api', page=1, limit=10)  # -> ?page=1&limit=10
```

## Parameter Flow Diagram

```
bag.get_item('path', **call_kwargs)
    |
    v
node.get_value(**call_kwargs)
    |
    v
resolver(static=False, **call_kwargs)
    |
    v
+------------------------------------------+
| effective_kw = {}                         |
| effective_kw.update(resolver._kw)     # 3 |
| effective_kw.update(node.attr)        # 2 |
| effective_kw.update(call_kwargs)      # 1 |
+------------------------------------------+
    |
    v
resolver.load()  # uses self._kw = effective_kw
    |
    v
result (cached if cache_time != 0)
```
