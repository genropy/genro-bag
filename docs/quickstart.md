# Quick Start

This guide will help you get started with Genro Bag.

## Basic Usage

### Creating a Bag

```python
from genro_bag import Bag

# Create an empty bag
bag = Bag()
```

### Adding Data

```python
# Simple key-value
bag['name'] = 'John'

# Nested paths
bag['config.database.host'] = 'localhost'
bag['config.database.port'] = 5432
```

### Accessing Data

```python
# Direct access
name = bag['name']

# Nested access
host = bag['config.database.host']
```

### XML Serialization

```python
# Convert to XML
xml_string = bag.toXml()

# Create bag from XML
bag2 = Bag(xml_string)
```

## Next Steps

- Explore the API reference for detailed documentation
- Check out examples in the repository
