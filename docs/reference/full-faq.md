# Frequently Asked Questions

## General

### What is a Bag?

A Bag is a hierarchical dictionary — a tree of named nodes where each node can have a value, attributes, and children. Think of it as a nested dictionary that preserves order, supports path-based access, and can be serialized to XML, JSON, or MessagePack.

### How is Bag different from a regular dict?

| Feature | dict | Bag |
|---------|------|-----|
| Nested access | `d['a']['b']['c']` | `bag['a.b.c']` |
| Node attributes | Not supported | `bag['user?role']` |
| Ordered children | Yes (Python 3.7+) | Yes |
| Lazy values | No | Yes (resolvers) |
| Reactivity | No | Yes (subscriptions) |
| XML serialization | No | Native |
| Type preservation | Limited | Full (via TYTX) |

### When should I use Bag instead of dataclasses or Pydantic?

Use Bag when:
- Structure is dynamic or not known at compile time
- You need path-based navigation
- XML serialization is required
- You want lazy loading via resolvers
- You need reactive updates via subscriptions
- Structure comes from external sources (APIs, configs, user input)

Use dataclasses/Pydantic when:
- Structure is fixed and known
- You need strict type validation
- IDE autocomplete is essential
- Performance is critical for simple data

### Is Bag thread-safe?

Bag is not thread-safe by default. If you need concurrent access:
- Use locks around modifications
- Create separate Bag instances per thread
- Use immutable patterns (create new Bags instead of modifying)

## Path Syntax

### How do I access nested values?

Use dot notation:

```python
bag['config.database.host']      # Value at path
bag['config.database']           # Returns child Bag
```

### How do I access node attributes?

Use the `?` syntax:

```python
bag['user?role']                 # Get 'role' attribute
bag['user?']                     # Get all attributes as dict
```

### How do I access by index?

Use the `#` syntax:

```python
bag['#0']                        # First child
bag['#-1']                       # Last child
bag['items.#2']                  # Third child of 'items'
```

### Can I use variables in paths?

Yes, use f-strings or string formatting:

```python
key = 'database'
bag[f'config.{key}.host']

index = 3
bag[f'items.#{index}']
```

### How do I iterate over children?

```python
# Iterate over nodes
for node in bag:
    print(node.label, node.value)

# Dict-like iteration
for key in bag.keys():
    print(key)

for value in bag.values():
    print(value)

for key, value in bag.items():
    print(key, value)
```

## Nodes and Attributes

### What's the difference between value and attributes?

- **Value**: The main content of a node (any Python object)
- **Attributes**: Metadata about the node (dict of key-value pairs)

```python
bag.set_item('product', 'Laptop', price=999, in_stock=True)
bag['product']           # 'Laptop' (value)
bag['product?price']     # 999 (attribute)
```

In XML terms: value is element content, attributes are XML attributes.

### Can a node have both value and children?

Yes, but it's uncommon. A node can have:
- Only a value (leaf node)
- Only children (container node)
- Both value and children (mixed content)

```python
bag['section'] = 'Introduction'           # Value
bag['section.paragraph'] = 'First para'   # Child
# Now 'section' has both value and children
```

### How do I get the BagNode object?

```python
node = bag.get_node('path.to.node')
node.label      # Node name
node.value      # Node value
node.attr       # Attributes dict
node.resolver   # Resolver if any
```

### How do I check if a path exists?

```python
if 'config.database' in bag:
    # Path exists
    pass

# Or use get with default
value = bag.get('config.missing', default='fallback')
```

## Resolvers

### What is a resolver?

A resolver is a lazy value provider. Instead of storing a static value, the node computes or fetches the value on demand.

```python
bag['timestamp'] = BagCbResolver(lambda: datetime.now().isoformat())
# Value computed fresh each time
bag['timestamp']  # '2025-01-07T10:30:00'
bag['timestamp']  # '2025-01-07T10:30:05'
```

### How does caching work?

```python
# No cache (default) - compute every time
BagCbResolver(func, cache_time=0)

# Cache for 60 seconds
BagCbResolver(func, cache_time=60)

# Cache forever (until manual reset)
BagCbResolver(func, cache_time=-1)
```

### Can I use async functions with resolvers?

Yes. Resolvers detect the execution context automatically:

```python
async def fetch_data():
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.json()

bag['data'] = BagCbResolver(fetch_data)

# Works in sync context
data = bag['data']

# Works in async context
async def main():
    data = bag['data']
```

### How do I reset a resolver's cache?

```python
node = bag.get_node('data')
node.resolver.reset()
# Next access will reload
```

### What's the difference between read_only=True and False?

- `read_only=False` (base default): Value is computed once and stored in node permanently
- `read_only=True` (default for UrlResolver, DirectoryResolver): Value is computed each time (respecting cache), never stored in node

```python
# read_only=True (UrlResolver default): always fresh (with cache)
bag['live'] = UrlResolver(url, cache_time=60)

# read_only=False: load once, store forever
bag['static'] = UrlResolver(url, read_only=False)
```

## Subscriptions

### How do subscriptions work?

Register callbacks that fire when the Bag changes. Callbacks receive all arguments as keyword arguments:

```python
def on_change(**kw):
    node = kw['node']
    evt = kw['evt']
    print(f"{evt}: {node.label}")

bag.subscribe('my_watcher', any=on_change)

bag['x'] = 1     # Prints: ins: x
bag['x'] = 2     # Prints: upd_value: x
del bag['x']     # Prints: del: x
```

### What events are available?

- `ins` - Node inserted
- `upd_value` - Node value changed
- `del` - Node deleted

Subscribe to specific events or all:

```python
bag.subscribe('id', insert=on_insert)
bag.subscribe('id', update=on_update)
bag.subscribe('id', delete=on_delete)
bag.subscribe('id', any=on_any)  # All events
```

### Do subscriptions work with nested changes?

Yes. Changes propagate up the hierarchy:

```python
bag.subscribe('watcher', any=on_change)
bag['a.b.c'] = 1
# Fires for: a (ins), b (ins), c (ins)
```

### How do I unsubscribe?

```python
bag.unsubscribe('my_watcher', any=True)      # Remove all
bag.unsubscribe('my_watcher', update=True)   # Remove only update
```

### Can I use subscriptions for validation?

Yes:

```python
def validate_email(node, evt, **kw):
    if node.label == 'email' and '@' not in str(node.value):
        raise ValueError('Invalid email')

bag.subscribe('validator', update=validate_email)
bag['email'] = 'invalid'  # Raises ValueError
```

## Builders

### What is a builder?

A builder provides a fluent API for constructing validated Bag structures:

```python
bag = Bag(builder=HtmlBuilder)
div = bag.div(id='main')
div.h1('Title')
div.p('Content')
```

### How do builders validate structure?

The `@element` decorator defines allowed children via `sub_tags`:

```python
@element(sub_tags='item')
def menu(self): ...

# menu can only contain 'item' elements
menu.item('OK')      # Works
menu.div('Error')    # Raises BuilderChildError
```

### Can I create custom builders?

Yes, extend `BagBuilderBase`:

```python
from genro_bag.builders import BagBuilderBase, element

class MyBuilder(BagBuilderBase):
    @element(sub_tags='child')
    def parent(self): ...

    @element()
    def child(self): ...
```

### Why do node labels have `_0` suffix?

Builders auto-number elements to ensure unique labels:

```python
bag.div()  # label: div_0
bag.div()  # label: div_1
```

Access by generated label or iterate:

```python
bag['div_0']
for div in bag:
    print(div.value)
```

## Serialization

### What serialization formats are supported?

- **XML**: Native, human-readable, schema-compatible
- **JSON**: Via TYTX format, type-preserving
- **MessagePack**: Via TYTX format, binary, fast

### What is TYTX?

TYTX (Typed Text) is a serialization format that preserves Python types:

```python
bag = Bag({'count': 42, 'active': True, 'rate': 3.14})
tytx = bag.to_tytx()
restored = Bag.from_tytx(tytx)
# Types preserved: int, bool, float
```

### How do I serialize to XML?

```python
xml = bag.to_xml()
bag = Bag.from_xml(xml)
```

### Are resolvers serialized?

Yes, with TYTX:

```python
bag['api'] = UrlResolver('https://api.example.com')
tytx = bag.to_tytx()

restored = Bag.from_tytx(tytx)
restored['api']  # Resolver still works
```

### How do I handle large files?

Use streaming or file operations:

```python
# To file
bag.to_xml_file('data.xml')
bag.to_tytx_file('data.tytx')

# From file
bag = Bag.from_xml_file('data.xml')
bag = Bag.from_tytx_file('data.tytx')
```

## Performance

### Is Bag fast enough for large datasets?

Bag is optimized for flexibility, not raw speed. For large datasets:
- Use resolvers for lazy loading
- Access specific paths instead of iterating
- Consider caching frequently accessed values
- For millions of records, use specialized data structures

### How can I improve performance?

1. **Use caching** for expensive resolvers
2. **Avoid deep nesting** when possible
3. **Access directly** instead of iterating
4. **Disable backref** if you don't need subscriptions
5. **Use TYTX MessagePack** for faster serialization

### Does backref mode affect performance?

Yes, slightly. Backref maintains parent references for subscriptions:

```python
bag = Bag()
bag.backref  # False by default

bag.subscribe('x', any=callback)
bag.backref  # True (auto-enabled)
```

If you don't need subscriptions, backref stays disabled.

## Common Patterns

### How do I merge two Bags?

```python
# Update with another Bag
bag1.update(bag2)

# Or copy nodes
for node in bag2:
    bag1[node.label] = node.value
```

### How do I deep copy a Bag?

```python
import copy
new_bag = copy.deepcopy(bag)

# Or via serialization
new_bag = Bag.from_tytx(bag.to_tytx())
```

### How do I convert Bag to regular dict?

```python
# Simple conversion (values only)
d = dict(bag.items())

# With nested conversion
def to_dict(bag):
    result = {}
    for node in bag:
        if isinstance(node.value, Bag):
            result[node.label] = to_dict(node.value)
        else:
            result[node.label] = node.value
    return result
```

### How do I find nodes by value?

```python
node = bag.get_node_by_value('name', 'Alice')
if node:
    print(node.label, node.attr)
```

### How do I get all paths in a Bag?

```python
def get_all_paths(bag, prefix=''):
    paths = []
    for node in bag:
        path = f"{prefix}.{node.label}" if prefix else node.label
        paths.append(path)
        if isinstance(node.value, Bag):
            paths.extend(get_all_paths(node.value, path))
    return paths
```

## Troubleshooting

### KeyError when accessing path

The path doesn't exist. Check with `in` or use `get`:

```python
if 'config.database' in bag:
    value = bag['config.database']

# Or with default
value = bag.get('config.database', default=None)
```

### BuilderChildError

You're trying to add an element that's not allowed as a child:

```python
# If menu only allows 'item' children
menu.div()  # BuilderChildError

# Fix: add allowed element
menu.item()
```

### Resolver not updating

Check cache settings:

```python
resolver = bag.get_node('data').resolver
resolver.reset()  # Clear cache

# Or use cache_time=0 for no caching
bag['data'] = BagCbResolver(func, cache_time=0)
```

### Subscription callback not firing

Ensure you subscribed before the change:

```python
bag.subscribe('watcher', any=callback)  # Subscribe first
bag['x'] = 1                            # Then modify
```

Check that backref is enabled:

```python
bag.backref  # Should be True after subscribing
```

### XML parsing fails

Check for:
- Malformed XML
- Encoding issues (use UTF-8)
- Special characters not escaped

```python
# Specify encoding
bag = Bag.from_xml(xml_string.encode('utf-8'))
```

## Migration

### How do I migrate from nested dicts?

```python
# From nested dict
data = {'config': {'database': {'host': 'localhost'}}}

# To Bag
bag = Bag(data)
# or
bag = Bag()
bag['config.database.host'] = 'localhost'
```

### How do I migrate from XML processing?

```python
# Instead of ElementTree
import xml.etree.ElementTree as ET
tree = ET.parse('data.xml')
root = tree.getroot()

# Use Bag
bag = Bag.from_xml_file('data.xml')
bag['root.child.value']
```

## Next Steps

- Read the [Examples](examples.md) for real-world usage
- Explore [Builders](builders/index.md) for domain-specific structures
- Learn about [Resolvers](resolvers.md) for lazy loading
- Understand [Subscriptions](subscriptions.md) for reactivity
