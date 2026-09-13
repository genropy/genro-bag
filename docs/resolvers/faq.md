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
| `> 0` | Passive cache for N seconds (reload on next access after expiry) |
| `< 0` | Legacy cache convention; no background refresh |
| `False` | Cache forever (until manual reset) |

### Why is my value not updating?

Check your cache_time:

```python
# This caches forever
bag['data'] = UrlResolver('...', cache_time=False)

# Force refresh
bag.get_node('data').resolver.reset()
```

### Can I have different cache times for different values?

Yes, each resolver has its own cache:

```python
bag['static'] = UrlResolver('...', cache_time=False)  # Forever
bag['dynamic'] = UrlResolver('...', cache_time=30)  # 30 seconds
bag['realtime'] = UrlResolver('...', cache_time=0)  # Never cache
```

## Execution context

Resolvers always execute synchronously and return the final value, including
inside an event loop. Async callbacks and loaders are rejected.

## Serialization

### Are resolvers preserved when serializing?

Yes, in XML, JSON and TYTX alike, whether the resolver is the node's value
or sits in an attribute:

```python
bag['api'] = UrlResolver('https://...')
bag.set_item('doc', 'text', author=EnvResolver('USER'))

restored = Bag.from_json(bag.to_json())
restored.get_resolver('api')   # UrlResolver, rebuilt
restored['doc?author']         # resolves as before
```

The resolver travels as a `::RSLV:` marked string carrying its class and
parameters. You get back an equivalent resolver, not the same object.

### Can I serialize a Bag with unresolved resolvers?

Yes — that is the normal case. Serializing stores the definition and never
runs the resolver, so no HTTP request, no file read, nothing:

```python
bag['api'] = UrlResolver('https://...')   # never accessed

restored = Bag.from_json(bag.to_json())   # still nothing happens
data = restored['api']                    # the request happens here
```

Reading back is inert too: the resolver is rebuilt but not called. The
effect only happens when your code reads the value.

### What if a resolver cannot be serialized?

You get a `BagSerializationError` naming the node and the attribute.
Callback-based resolvers are the usual case — a function cannot travel:

```python
bag['cb'] = BagCbResolver(lambda: compute())
bag.to_json()   # BagSerializationError: node 'cb' holds a BagCbResolver...
```

### Do I need to sign anything?

Whenever the Bag leaves the process and may come back — handed to a
browser, stored in a URL, put on a queue. A resolver's arguments say what
it will act on, so an unsigned payload lets whoever holds it rewrite a path
or a URL before returning it.

```python
# server, on the way out
payload = bag.to_json(sign_key=SECRET, expires_in=300)

# server, on the way in
bag = Bag.from_json(payload, sign_key=SECRET)   # SignatureError if altered
```

The key stays server-side: you sign and verify, the client only carries.
Reading with `sign_key` demands a valid signature, so an unsigned payload
is refused too. `SignatureExpired` (a subclass of `SignatureError`) tells
an expired token from a forged one.

For Bags that never leave your control the key is unnecessary.

### Does signing keep the parameters secret?

No. A signature proves the payload was not altered; it does not hide it.
The encoding is base64, not encryption, so whoever receives the payload
reads every parameter — including a server path or an API key.

Keep secrets out of the parameters. Where a resolver needs a credential,
compute it at request time in a hook instead of storing it:

```python
class ApiResolver(UrlResolver):
    def prepare_headers(self):
        return {'Authorization': f'Bearer {os.environ["API_TOKEN"]}'}
```

`prepare_headers()` is never serialized, so the token stays on the server.
Passing it as a parameter — `UrlResolver(url, headers={'Authorization': ...})`
— puts it on the wire.

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

### Execution context

Use `result = bag["api"]` in every context. No await is needed.
