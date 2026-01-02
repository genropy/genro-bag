# Genro Bag

Welcome to the Genro Bag documentation.

Genro Bag is a modernized bag system for the Genropy framework - a hierarchical data container with XML serialization.

## Status

**Development Status: Pre-Alpha**

This project is currently in the planning and design phase.

## Features

- **Hierarchical Data Storage**: Tree-like structure for organizing nested data
- **XML Serialization**: Native support for reading and writing XML format
- **Attribute Support**: Nodes can have both values and attributes
- **Path-based Access**: Navigate and manipulate data using path expressions
- **Event System**: Subscribe to changes in the data structure

## Quick Start

```python
from genro_bag import Bag

# Create a new bag
bag = Bag()

# Add nested data
bag['config.database.host'] = 'localhost'
bag['config.database.port'] = 5432

# Access data
host = bag['config.database.host']

# Serialize to XML
xml_content = bag.toXml()
```

## Contents

```{toctree}
:maxdepth: 2
:caption: Contents

installation
quickstart
```

## Indices and tables

- {ref}`genindex`
- {ref}`modindex`
- {ref}`search`
