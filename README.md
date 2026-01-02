# genro-bag

[![PyPI version](https://badge.fury.io/py/genro-bag.svg)](https://badge.fury.io/py/genro-bag)
[![Tests](https://github.com/genropy/genro-bag/actions/workflows/tests.yml/badge.svg)](https://github.com/genropy/genro-bag/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/genropy/genro-bag/branch/main/graph/badge.svg)](https://codecov.io/gh/genropy/genro-bag)
[![Documentation](https://readthedocs.org/projects/genro-bag/badge/?version=latest)](https://genro-bag.readthedocs.io/en/latest/?badge=latest)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

Modernized bag system for the Genropy framework - a hierarchical data container with XML serialization.

## Status

**Development Status: Pre-Alpha**

This project is currently in the planning and design phase. No implementation code is available yet.

## Overview

The Bag is a foundational data structure in the Genropy framework, providing:

- **Hierarchical Data Storage**: Tree-like structure for organizing nested data
- **XML Serialization**: Native support for reading and writing XML format
- **Attribute Support**: Nodes can have both values and attributes
- **Path-based Access**: Navigate and manipulate data using path expressions
- **Event System**: Subscribe to changes in the data structure

## Use Cases

- Configuration management
- Data interchange between components
- UI component state management
- Form data handling
- XML document processing

## Installation

```bash
pip install genro-bag
```

For development:

```bash
pip install genro-bag[dev]
```

For documentation:

```bash
pip install genro-bag[docs]
```

## Quick Example

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

# Load from XML
bag2 = Bag(xml_content)
```

## Documentation

Full documentation is available at [genro-bag.readthedocs.io](https://genro-bag.readthedocs.io/).

## Repository Structure

```
genro-bag/
├── src/
│   └── genro_bag/
│       ├── __init__.py
│       └── py.typed
├── tests/
│   └── __init__.py
├── docs/
│   ├── conf.py
│   ├── index.md
│   └── ...
├── .github/
│   └── workflows/
│       ├── tests.yml
│       ├── publish.yml
│       └── docs.yml
├── pyproject.toml
├── README.md
├── LICENSE
├── NOTICE
└── CLAUDE.md
```

## Development

### Running Tests

```bash
pytest
```

With coverage:

```bash
pytest --cov=genro_bag --cov-report=html
```

### Code Quality

```bash
ruff check src/
mypy src/
```

## Contributing

Contributions are welcome! Please see the [Contributing Guide](CONTRIBUTING.md) for details.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

Copyright 2025 Softwell S.r.l.

## Origin

This project was originally part of the Genropy framework and has been extracted as a standalone module with modernized tooling and type hints.
