# genro-bag

[![PyPI version](https://img.shields.io/pypi/v/genro-bag?v=0.7.1)](https://pypi.org/project/genro-bag/)
[![Tests](https://github.com/genropy/genro-bag/actions/workflows/tests.yml/badge.svg)](https://github.com/genropy/genro-bag/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/genropy/genro-bag/branch/main/graph/badge.svg)](https://codecov.io/gh/genropy/genro-bag)
[![Documentation](https://readthedocs.org/projects/genro-bag/badge/?version=latest)](https://genro-bag.readthedocs.io/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

An **intermediate representation** for structured data in Python.

## What is Bag?

A Bag is an abstraction that bridges the gap between how humans think about structured data and how software implements it.

When you work with configuration files, API responses, form data, or document structures, they all share the same fundamental shape: **named things containing values, organized in a hierarchy, with additional properties attached**.

Yet in code, we scatter this across dictionaries, classes, JSON, XML, database rows—each with its own access patterns and limitations.

A Bag unifies these patterns into a single, consistent model:

- **Nodes** — Named containers that hold a value
- **Hierarchy** — Nodes can contain other nodes, forming a tree
- **Attributes** — Each node carries metadata alongside its value
- **Paths** — Navigate the tree with familiar dot notation

## The Layered Design

Bag provides progressive capability. Start simple, add layers when needed:

| Layer | Purpose |
|-------|---------|
| **Core Bag** | The fundamental container: paths, values, attributes |
| **Resolvers** | Values that compute themselves: lazy loading, API calls |
| **Subscriptions** | React to changes: validation, logging, computed properties |
| **Builders** | Domain-specific languages: HTML, Markdown, XML schemas |

## Install

```bash
pip install genro-bag
```

## Documentation

Full documentation with examples: [genro-bag.readthedocs.io](https://genro-bag.readthedocs.io/)

| Section | Description |
|---------|-------------|
| **[Getting Started](https://genro-bag.readthedocs.io/en/latest/getting-started.html)** | Learn the three core concepts |
| **[Core Bag](https://genro-bag.readthedocs.io/en/latest/bag/)** | Basic usage, paths, attributes, serialization |
| **[Resolvers](https://genro-bag.readthedocs.io/en/latest/resolvers/)** | Lazy loading, API calls, computed values |
| **[Subscriptions](https://genro-bag.readthedocs.io/en/latest/subscriptions/)** | React to changes, validation, logging |
| **[Builders](https://genro-bag.readthedocs.io/en/latest/builders/)** | Domain-specific languages (HTML, Markdown, XSD) |

## Development

```bash
pip install -e ".[dev]"
pytest
```

1500+ tests, 88%+ coverage.

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.

Copyright 2025 Softwell S.r.l. - Genropy Team
