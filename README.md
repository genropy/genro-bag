# genro-bag

[![PyPI version](https://badge.fury.io/py/genro-bag.svg)](https://badge.fury.io/py/genro-bag)
[![Tests](https://github.com/genropy/genro-bag/actions/workflows/tests.yml/badge.svg)](https://github.com/genropy/genro-bag/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/genropy/genro-bag/branch/main/graph/badge.svg)](https://codecov.io/gh/genropy/genro-bag)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

**Hierarchical data container for Python.**

## Why?

Most software systems deal with structured things: configurations, API responses,
XML documents, UI components. We usually treat these as separate worlds, each
with its own language, tools, and conventions.

Yet they all share something simple: **they are organized hierarchically**.

We say "the third book on the first shelf in the bedroom", not "object #42".
We think by *location*, not by mechanism.

`genro-bag` makes hierarchy a first-class concept. Instead of translating
hierarchical thinking into tables, callbacks, or ad-hoc APIs, the hierarchy
stays explicit and central.

## Install

```bash
pip install genro-bag
```

## Quick Start

```python
from genro_bag import Bag

# Hierarchical dict with dot notation
config = Bag()
config["database.host"] = "localhost"
config["database.port"] = 5432
config["database.credentials.user"] = "admin"

# Access nested values directly
print(config["database.host"])  # "localhost"

# Node attributes - metadata separate from values
config.set_item("api_key", "sk-xxx", _attributes={"env": "production", "expires": 2025})

node = config.get_node("api_key")
print(node.value)           # "sk-xxx"
print(node.attr["env"])     # "production"

# Serialize to multiple formats
print(config.to_xml())
print(config.to_json())
```

## Features

### Hierarchical Navigation

Navigate deep structures without defensive chains of `.get()`:

```python
# Traditional Python - fragile and verbose
email = data.get("user", {}).get("profile", {}).get("settings", {}).get("email")

# With Bag - one path, clear intent
email = bag["user.profile.settings.email"]
```

### Node Attributes

Every node has both a value and attributes. Metadata stays separate from data:

```python
bag.set_item("user", "Mario", _attributes={"role": "admin", "active": True})

# Value and attributes are separate concerns
node = bag.get_node("user")
node.value        # "Mario"
node.attr["role"] # "admin"
```

### Query Syntax

Extract data with a concise query language:

```python
# All values from users
bag.digest("users.*#v")

# All active users (filter by attribute)
bag.digest("users.*?active=true")

# Specific attribute from all users
bag.digest("users.*#a.role")
```

| Syntax | Meaning |
|--------|---------|
| `#v` | Node value |
| `#a` | All attributes |
| `#a.name` | Specific attribute |
| `?attr` | Filter: has attribute |
| `?attr=val` | Filter: attribute equals value |
| `*` | All children |

### Lazy Resolution

Not everything can be stored. Some values must be *obtained*: from APIs,
databases, files. With resolvers, access looks the same - resolution happens
transparently:

```python
from genro_bag import Bag
from genro_bag.resolvers import UrlResolver, OpenApiResolver

bag = Bag()

# URL resolver - fetches on access
bag["weather"] = UrlResolver("https://api.weather.com/today")

# OpenAPI resolver - loads spec and provides typed access
bag["petstore"] = OpenApiResolver("https://petstore.swagger.io/v3/openapi.json")

# Access triggers resolution (with optional caching)
print(bag["weather"])           # GET request happens here
print(bag["petstore.api.pet"])  # Structured API access
```

### Reactivity

Subscribe to changes by *location*, not by mechanism:

```python
def on_change(node, event, old_value):
    print(f"Changed: {node.fullpath} = {node.value}")

bag.subscribe("watcher", update=on_change, path="config.*")

bag["config.debug"] = True  # Triggers: "Changed: config.debug = True"
```

### Serialization

Multiple formats, round-trip safe:

```python
# XML with type preservation
xml = bag.to_xml()
restored = Bag.from_xml(xml)

# JSON
json_str = bag.to_json()
restored = Bag.from_json(json_str)

# TYTX - typed transport (preserves Python types exactly)
tytx = bag.to_tytx()
restored = Bag.from_tytx(tytx)
```

### Builders (coming soon)

Write structures the same way you think about them:

```python
from genro_bag import Bag
from genro_bag.builders import HtmlBuilder

bag = Bag(builder=HtmlBuilder())
body = bag.body()
div = body.div(id='main')
div.h1(value='Welcome')
div.p(value='Hello, World!')

print(bag.to_xml(html=True))
```

## One Way of Thinking, Many Domains

The same hierarchical model applies to:

- Web pages and HTML documents
- Configuration files
- API responses and OpenAPI specs
- Database schemas
- Cloud infrastructure definitions
- Shared real-time state

The structure stays the same. Only the vocabulary changes.

## Documentation

Full documentation: [genro-bag.readthedocs.io](https://genro-bag.readthedocs.io/)

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=genro_bag --cov-report=html

# Code quality
ruff check src/
mypy src/
```

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.

Copyright 2025 Softwell S.r.l. - Genropy Team
