# genro-bag

[![PyPI version](https://badge.fury.io/py/genro-bag.svg)](https://badge.fury.io/py/genro-bag)
[![Tests](https://github.com/genropy/genro-bag/actions/workflows/tests.yml/badge.svg)](https://github.com/genropy/genro-bag/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/genropy/genro-bag/branch/main/graph/badge.svg)](https://codecov.io/gh/genropy/genro-bag)
[![Documentation](https://readthedocs.org/projects/genro-bag/badge/?version=latest)](https://genro-bag.readthedocs.io/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

**Hierarchical data container for Python.**

## Install

```bash
pip install genro-bag
```

## What is a Bag?

A Bag is a **dict-like container** that organizes data hierarchically. Unlike a standard dict, a Bag is designed to represent tree structures where each element can contain other elements.

### Dict-Like Container

At the simplest level, a Bag behaves like a dictionary:

```python
from genro_bag import Bag

bag = Bag()
bag['name'] = 'Alice'
bag['age'] = 30

print(bag['name'])  # 'Alice'
print(len(bag))     # 2

for key in bag.keys():
    print(key)      # 'name', 'age'
```

### Hierarchical Structure

But unlike a dict, a Bag supports **hierarchical paths** with dot notation. Intermediate levels are created automatically:

```python
bag = Bag()
bag['config.database.host'] = 'localhost'
bag['config.database.port'] = 5432
bag['config.cache.enabled'] = True

# Direct access to any level
print(bag['config.database.host'])  # 'localhost'

# Navigate the subtree
db_config = bag['config.database']
print(db_config['host'])  # 'localhost'
```

This eliminates the defensive pattern typical of nested dicts:

```python
# With standard dict - fragile and verbose
email = data.get('user', {}).get('profile', {}).get('settings', {}).get('email')

# With Bag - one path, clear intent
email = bag['user.profile.settings.email']
```

### Nodes

Each element in a Bag is not a simple value, but a **BagNode**. The node is the fundamental unit: it contains the value, plus additional metadata.

```python
bag = Bag()
bag['user'] = 'Alice'

# Value access (common way)
print(bag['user'])  # 'Alice'

# Access to the underlying node
node = bag.get_node('user')
print(node.label)   # 'user'
print(node.value)   # 'Alice'
```

### Attributes and Values

Each node has two distinct things:
- **value**: the node's value (string, number, another Bag, any object)
- **attr**: a dictionary of attributes (metadata)

Attributes allow associating additional information without modifying the value:

```python
bag = Bag()
bag.set_item('api_key', 'sk-xxx', env='production', expires=2025)

# Value and attributes are separate
print(bag['api_key'])           # 'sk-xxx' (the value)
print(bag['api_key?env'])       # 'production' (an attribute)
print(bag['api_key?expires'])   # 2025 (another attribute)

# Access via node
node = bag.get_node('api_key')
print(node.value)               # 'sk-xxx'
print(node.attr)                # {'env': 'production', 'expires': 2025}
```

This is particularly useful for XML where attributes are native:

```python
bag = Bag()
bag.set_item('user', 'Alice', role='admin', active=True)
print(bag.to_xml())
# <user role="admin" active="True">Alice</user>
```

### Lazy Values (Resolvers)

Not everything can be stored statically. Some values must be *obtained*: from APIs, databases, files. **Resolvers** let you define how to get a value - resolution happens transparently on access:

```python
from genro_bag import Bag
from genro_bag.resolvers import BagCbResolver, UrlResolver

bag = Bag()

# Callback resolver - computes value on-demand
def get_timestamp():
    from datetime import datetime
    return datetime.now().isoformat()

bag['now'] = BagCbResolver(get_timestamp)
print(bag['now'])  # '2025-01-07T10:30:45.123456' - computed now

# URL resolver - HTTP fetch on-demand
bag['weather'] = UrlResolver('https://api.weather.com/today')
print(bag['weather'])  # GET request executed here

# With caching - value is stored for N seconds
bag['data'] = BagCbResolver(expensive_function, cache_time=60)
```

Access is always the same (`bag['key']`), but the value can come from any source.

### Reactivity (Subscriptions)

A Bag can notify when its contents change. You can subscribe to insert, update, and delete events:

```python
bag = Bag()

def on_change(node, evt, **kw):
    print(f'{evt}: {node.label} = {node.value}')

bag.subscribe('logger', any=on_change)

bag['name'] = 'Alice'    # Prints: ins: name = Alice
bag['name'] = 'Bob'      # Prints: upd_value: name = Bob
del bag['name']          # Prints: del: name = Bob
```

This allows building reactive systems where components automatically react to data changes.

### Validated Fluent Construction (Builders)

**Builders** provide a fluent API to construct domain-specific structures. Instead of building the Bag manually, you use methods that guide and validate the construction:

```python
from genro_bag import Bag
from genro_bag.builders import HtmlBuilder

bag = Bag(builder=HtmlBuilder())

# Fluent API - each method returns the created node
div = bag.div(id='main', class_='container')
div.h1(value='Welcome')
div.p(value='Hello, World!')

print(bag.to_xml())
# <div id="main" class="container">
#   <h1>Welcome</h1>
#   <p>Hello, World!</p>
# </div>
```

Builders can also validate the structure:

```python
from genro_bag.builders import BagBuilderBase, element

class MenuBuilder(BagBuilderBase):
    @element(children='item')  # menu can only contain item
    def menu(self, target, tag, **attr):
        return self.child(target, tag, **attr)

    @element()
    def item(self, target, tag, value=None, **attr):
        return self.child(target, tag, value=value, **attr)

bag = Bag(builder=MenuBuilder())
menu = bag.menu(id='nav')
menu.item(value='Home')
menu.item(value='About')
# menu.div()  # Error! 'div' not allowed inside 'menu'
```

## Query and Aggregation

Bag provides methods to extract and aggregate data:

```python
bag = Bag()
bag.set_item('alice', 100, role='admin')
bag.set_item('bob', 50, role='user')
bag.set_item('carol', 75, role='admin')

# Extract labels and values
bag.digest('#k,#v')
# [('alice', 100), ('bob', 50), ('carol', 75)]

# Filter by condition
bag.digest('#k', condition=lambda n: n.value > 60)
# ['alice', 'carol']

# Sum values
bag.sum()  # 225
```

## Serialization

Bag supports multiple serialization formats:

```python
bag = Bag()
bag['count'] = 42
bag.set_item('user', 'Alice', role='admin')

# XML - human readable, native attributes
xml = bag.to_xml()
restored = Bag.from_xml(f'<root>{xml}</root>')

# JSON
json_str = bag.to_json()
restored = Bag.from_json(json_str)

# TYTX - preserves Python types exactly
tytx = bag.to_tytx()
restored = Bag.from_tytx(tytx)
```

**TYTX** (Typed Text eXchange) is the recommended format when you need round-trip without losing types (int, Decimal, datetime, etc.).

## Use Cases

The same hierarchical model applies to different domains:

- **Configurations** - hierarchical paths, attributes for metadata
- **HTML/XML documents** - builders for fluent construction
- **API responses** - resolvers for lazy loading
- **UI state** - subscriptions for reactivity
- **Structured data** - queries for extraction

The structure stays the same. Only the vocabulary changes.

## Documentation

Full documentation: [genro-bag.readthedocs.io](https://genro-bag.readthedocs.io/)

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Code quality
ruff check src/
mypy src/
```

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.

Copyright 2025 Softwell S.r.l. - Genropy Team
