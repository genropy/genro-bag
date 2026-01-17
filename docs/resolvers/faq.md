# Resolvers FAQ

## Basic Questions

### When is the resolver called?

When you access the value for the first time (or when cache expires):

```python
bag['data'] = UrlResolver('https://...')  # Nothing happens yet
result = bag['data']  # NOW the HTTP request is made
```

### How do I force a refresh?

Reset the resolver's cache:

```python
node = bag.get_node('data')
node.resolver.reset()

# Next access will reload
fresh_data = bag['data']
```

### Can I check if a value is resolved without triggering resolution?

Yes, use `static=True`:

```python
# This won't trigger the resolver
cached = bag.get_item('data', static=True)

if cached is None:
    # Not yet resolved or no cached value
    pass
```

### What happens if the resolver fails?

The exception propagates to the caller:

```python
bag['api'] = UrlResolver('https://invalid-url')

try:
    data = bag['api']
except Exception as e:
    print(f"Failed to resolve: {e}")
```

## Caching

### How does caching work?

| `cache_time` | Behavior |
|--------------|----------|
| `0` | No caching, compute every time |
| `> 0` | Cache for N seconds |
| `< 0` | Cache forever (until reset) |

### Why is my value not updating?

Check your cache_time:

```python
# This caches forever
bag['data'] = UrlResolver('...', cache_time=-1)

# Force refresh
bag.get_node('data').resolver.reset()
```

### Can I have different cache times for different values?

Yes, each resolver has its own cache:

```python
bag['static'] = UrlResolver('...', cache_time=-1)   # Forever
bag['dynamic'] = UrlResolver('...', cache_time=30)  # 30 seconds
bag['realtime'] = UrlResolver('...', cache_time=0)  # Never cache
```

## Async

### How do I use resolvers in async code?

Use `smartawait`:

```python
from genro_toolbox import smartawait

async def get_data():
    return await smartawait(bag.get_item('api', static=False))
```

### Why do I get a coroutine instead of the value?

In async context with `static=False`, you may get a coroutine:

```python
# This might return a coroutine
result = bag.get_item('api', static=False)

# Always safe:
result = await smartawait(bag.get_item('api', static=False))
```

### Can I use sync resolvers in async code?

Yes, they work automatically. The `@smartasync` decorator handles it.

## Serialization

### Are resolvers preserved when serializing?

With TYTX, yes:

```python
tytx = bag.to_tytx()
restored = Bag.from_tytx(tytx)
# Resolver is preserved!
```

With XML/JSON, no — only the cached value is preserved.

### Can I serialize a Bag with unresolved resolvers?

Yes, but the resolver definition is stored, not the value:

```python
bag['api'] = UrlResolver('https://...')
# Never accessed, so no cached value

tytx = bag.to_tytx()
restored = Bag.from_tytx(tytx)

# The resolver is there, will fetch when accessed
data = restored['api']  # HTTP request happens now
```

## Modifying Nodes with Resolvers

### Why can't I overwrite a resolver node?

To prevent accidental data loss:

```python
bag['data'] = UrlResolver('...')
bag['data'] = 'new_value'  # ERROR!
```

### How do I replace a resolver with a value?

Use `resolver=False`:

```python
bag.set_item('data', 'new_value', resolver=False)
```

### How do I replace one resolver with another?

```python
new_resolver = UrlResolver('https://new-url')
bag.set_item('data', None, resolver=new_resolver)
```

## Performance

### Are resolvers thread-safe?

Basic thread safety is provided, but for high-concurrency use cases, consider external synchronization.

### How do I avoid thundering herd with cached resolvers?

Use appropriate cache times and consider staggering:

```python
# Don't: All caches expire at the same time
for i in range(100):
    bag[f'item_{i}'] = UrlResolver('...', cache_time=300)

# Better: Stagger cache times
import random
for i in range(100):
    jitter = random.randint(0, 60)
    bag[f'item_{i}'] = UrlResolver('...', cache_time=300 + jitter)
```

## Common Mistakes

### Using `bag['key']` inside the resolver for the same key

This causes infinite recursion:

```python
# WRONG - infinite loop!
def bad_resolver():
    current = bag['data']  # Calls this resolver again!
    return current + 1

bag['data'] = BagCbResolver(bad_resolver)
```

### Forgetting async context

```python
# WRONG in async code
result = bag['api']  # Might be a coroutine!

# RIGHT
result = await smartawait(bag.get_item('api', static=False))
```
