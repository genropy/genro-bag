# genro-bag

[![PyPI version](https://img.shields.io/pypi/v/genro-bag?v=0.7.1)](https://pypi.org/project/genro-bag/)
[![Tests](https://github.com/genropy/genro-bag/actions/workflows/tests.yml/badge.svg)](https://github.com/genropy/genro-bag/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/genropy/genro-bag/branch/main/graph/badge.svg)](https://codecov.io/gh/genropy/genro-bag)
[![Documentation](https://readthedocs.org/projects/genro-bag/badge/?version=latest)](https://genro-bag.readthedocs.io/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

A **hierarchical dictionary** for Python: a tree of named nodes with values and attributes.

## The Core Idea

```python
from genro_bag import Bag

bag = Bag()
bag['config.database.host'] = 'localhost'
bag['config.database.port'] = 5432

bag['config.database.host']  # 'localhost'
```

Three concepts, that's all:

| Concept | Syntax | Example |
|---------|--------|---------|
| **Path** | `bag['a.b.c']` | Navigate hierarchy with dots |
| **Value** | `bag['key'] = value` | Each node holds a value |
| **Attribute** | `bag['key?attr']` | Each node can have metadata |

```python
bag.set_item('user', 'Alice', role='admin', active=True)

bag['user']        # 'Alice'
bag['user?role']   # 'admin'
```

## Install

```bash
pip install genro-bag
```

## Learn More

| Section | Description |
|---------|-------------|
| **[Core Bag](docs/bag/)** | Basic usage, paths, attributes, serialization |
| **[Resolvers](docs/resolvers/)** | Lazy loading, API calls, computed values |
| **[Subscriptions](docs/subscriptions/)** | React to changes, validation, logging |
| **[Builders](docs/builders/)** | Domain-specific languages (HTML, Markdown, XSD) |

## When You Need More

Bag is intentionally minimal at its core. As your needs grow:

### Resolvers — Values that compute themselves

```python
from genro_bag.resolvers import BagCbResolver, UrlResolver

bag['now'] = BagCbResolver(lambda: datetime.now().isoformat())
bag['api'] = UrlResolver('https://api.example.com/data', cache_time=300)

bag['now']  # Computed on access
bag['api']  # Fetched from network, cached 5 minutes
```

### Subscriptions — React to changes

```python
def on_change(**kw):
    print(f"Changed: {kw['node'].label} = {kw['node'].value}")

bag.subscribe('watcher', any=on_change)
bag['count'] = 1  # Prints: "Changed: count = 1"
```

### Builders — Domain-specific structure

```python
from genro_bag.builders import HtmlBuilder

page = Bag(builder=HtmlBuilder)
div = page.div(class_='container')
div.h1(value='Welcome')
div.p(value='Hello, World!')

page.to_xml(pretty=True)
```

## Why Bag?

Instead of combining `omegaconf` + `pydantic` + `munch` + `rxpy` + `lxml` + custom glue:

| Need | Typical solution | With Bag |
|------|------------------|----------|
| Hierarchical data | dict + manual nesting | Native path access |
| Configuration | omegaconf, hydra | Bag + builders |
| Lazy values | @property, decorators | Transparent resolvers |
| Reactivity | rxpy, signals | Location-based subscriptions |
| XML/JSON | lxml, xmltodict | Unified serialization |

*One coherent model. Less glue. More domain logic.*

## Documentation

Full documentation: [genro-bag.readthedocs.io](https://genro-bag.readthedocs.io/)

## Development

```bash
pip install -e ".[dev]"
pytest
```

1500+ tests, 88%+ coverage.

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.

Copyright 2025 Softwell S.r.l. - Genropy Team
