# Quick Start

Get up and running with Genro Bag in 5 minutes.

## Installation

```bash
pip install genro-bag
```

## Basic Usage

### Creating a Bag

```python
from genro_bag import Bag

# Create an empty bag
bag = Bag()

# Or from a dictionary
bag = Bag({'name': 'Alice', 'age': 30})
```

### Adding Data

Use dot-separated paths for nested structures:

```python
from genro_bag import Bag

bag = Bag()

# Simple key-value
bag['name'] = 'John'

# Nested paths (intermediate Bags are created automatically)
bag['config.database.host'] = 'localhost'
bag['config.database.port'] = 5432
```

### Accessing Data

```python
# Direct access
name = bag['name']  # 'John'

# Nested access
host = bag['config.database.host']  # 'localhost'

# Get intermediate Bag
db_config = bag['config.database']
```

## Node Attributes

Every node can carry attributes (metadata) separate from its value:

```python
from genro_bag import Bag

bag = Bag()

# Create node with value AND attributes
bag.set_item('user', 'Alice', role='admin', active=True)

# Value
bag['user']  # 'Alice'

# Attributes (use ? syntax)
bag['user?role']    # 'admin'
bag['user?active']  # True
```

## XML Serialization

```python
from genro_bag import Bag

bag = Bag()
bag['name'] = 'Test'
bag['count'] = 42

# Convert to XML
xml_string = bag.to_xml()
# '<name>Test</name><count>42</count>'

# Create bag from XML
xml = '<root><name>Test</name></root>'
bag2 = Bag.from_xml(xml)
bag2['root.name']  # 'Test'
```

## Lazy Loading with Resolvers

Values can be computed or fetched on demand:

```python
from genro_bag import Bag
from genro_bag.resolvers import BagCbResolver
from datetime import datetime

bag = Bag()

# Value computed each time it's accessed
bag['now'] = BagCbResolver(lambda: datetime.now().isoformat())

# Access triggers the callback
print(bag['now'])  # '2025-01-13T10:30:45.123456'
```

## Next Steps

- [Basic Usage](basic-usage.md) - Complete guide to Bag operations
- [Serialization](serialization.md) - XML, JSON, and TYTX formats
- [Resolvers](resolvers.md) - Lazy loading and async values
- [Builders Quick Start](builders/quickstart.md) - Domain-specific builders
