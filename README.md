# genro-bag

[![PyPI version](https://img.shields.io/pypi/v/genro-bag?v=0.7.0)](https://pypi.org/project/genro-bag/)
[![Tests](https://github.com/genropy/genro-bag/actions/workflows/tests.yml/badge.svg)](https://github.com/genropy/genro-bag/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/genropy/genro-bag/branch/main/graph/badge.svg)](https://codecov.io/gh/genropy/genro-bag)
[![Documentation](https://readthedocs.org/projects/genro-bag/badge/?version=latest)](https://genro-bag.readthedocs.io/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

## Introduction

Most software systems deal with structured things: web pages, configuration files, APIs, database schemas, cloud infrastructures, documents. We usually treat these as separate worlds, each with its own language, tools, and conventions.

Yet they all share something very simple: **they are organized hierarchically**, and humans reason about them by location rather than by mechanism. We say "the third book on the first shelf in the bedroom", not "object #42".

This project starts from that observation.

## A hierarchy as a first-class concept

A Bag is a **hierarchical dictionary**: a tree of named nodes. Instead of translating hierarchical thinking into tables, messages, callbacks, or ad-hoc APIs, the hierarchy is kept explicit and central.

```python
from genro_bag import Bag

bag = Bag()
bag['config.database.host'] = 'localhost'
bag['config.database.port'] = 5432

print(bag['config.database.host'])  # localhost
```

Each node can carry both a value and arbitrary attributes. This mirrors how we naturally think about things: a product has a name (its value) but also a price, a category, a status (its attributes).

```python
bag.set_item('product', 'Laptop', price=999, category='electronics')

bag['product']           # 'Laptop'
bag['product?price']     # 999
bag['product?category']  # 'electronics'
```

Related things live together, names are stable, navigation is uniform, and structure is visible. Nothing clever is required to get started.

## When values are not just values

In real systems, not everything can be stored. Some values must be *obtained*: by calling a service, reading hardware, querying a database, or computing something on demand.

In a Bag, this does not require a different mental model. You still navigate to a place in the hierarchy. The only difference is that some places know how to **resolve** a value instead of containing one.

```python
from datetime import datetime
from genro_bag.resolvers import BagCbResolver, UrlResolver

# A value computed on demand
bag['now'] = BagCbResolver(lambda: datetime.now().isoformat())

# A value fetched from the network
bag['weather'] = UrlResolver('https://api.weather.com/current', cache_time=300)
```

From the outside, access looks the same: `bag['now']` or `bag['weather']`. You don't switch from "data mode" to "API mode". You navigate first; resolution happens later. And it works the same whether you're in a synchronous or asynchronous context.

> **Async note**: In sync code, no special handling is needed. In async code with `static=False`, use `await smartawait(bag.get_item("path", static=False))` since the result may be a coroutine when the resolver needs to load fresh data.

## Reacting to meaning, not plumbing

Change is inevitable in any non-trivial system. Usually, change is handled through events, callbacks, queues, or polling loops. These mechanisms tend to leak into application code and force developers to think about infrastructure details.

A Bag takes a different approach. Instead of subscribing to events, you express interest in a **place** in the hierarchy.

```python
def on_price_change(**kw):
    node = kw['node']
    if node.label == 'price':
        print(f"Price changed to {node.value}")

bag.subscribe('price_watcher', update=on_price_change)

bag['product?price'] = 1099  # triggers: "Price changed to 1099"
```

You care about *what* changed, not *how* the change was transported. This keeps reactivity tied to meaning rather than to implementation details.

## Writing structure the same way you read it

The same hierarchy that can be navigated and observed can also be built. **Builders** allow structures to be written fluently, in a way that mirrors how they are described mentally.

```python
from genro_bag.builders import HtmlBuilder

bag = Bag(builder=HtmlBuilder)

page = bag.html()
head = page.head()
head.title(value='My Page')

body = page.body()
div = body.div(class_='container')
div.h1(value='Welcome')
div.p(value='This is a paragraph.')
```

This is not about inventing a new language. It is about making construction consistent with navigation. Builders can also enforce rules about what is allowed or required, so structures are **valid as they are built**, not validated afterwards.

You can create domain-specific builders for any structured vocabulary: HTML, XML schemas, configuration formats, API specifications, or business documents like invoices.

## One way of thinking, many domains

Once this model is in place, something interesting happens. The same way of reasoning can be applied to web pages, XML documents, API descriptions, database structures, cloud architectures, and shared real-time state. The structure stays the same. Only the vocabulary changes.

```python
from genro_bag.resolvers import OpenApiResolver

# Same mental model, different domains
apis = Bag()
apis['petstore'] = OpenApiResolver('https://petstore3.swagger.io/api/v3/openapi.json')

# Navigate APIs like local data - operations organized by tags
api = apis['petstore']           # Loads and parses the OpenAPI spec
api['api']['pet'].keys()         # ['addPet', 'updatePet', 'findPetsByStatus', ...]
api['api']['pet']['addPet']['summary']  # 'Add a new pet to the store'
```

Developers do not have to relearn how to think for each domain — only what names and constraints apply.

## A structural IR, not a framework

This project is best understood as a **structural intermediate representation**. It sits between how humans reason about structured systems and how specific technologies require them to be expressed.

It does not replace HTML, Terraform, APIs, or databases. It can compile into them, connect them, or synchronize them — and then disappear. Nothing depends on it at runtime unless you choose so.

That is why it is more accurate to see this as a **mental model made concrete**, rather than as a framework to adopt wholesale.

## Why Bag instead of the usual toolbox?

A typical Python project dealing with hierarchical data ends up combining `omegaconf` + `pydantic` + `munch` + `rxpy` + `lxml` + custom glue code. The result: 10+ dependencies, 5-6 different access styles, and low real productivity.

Bag offers **one coherent model** covering hierarchical data, attributes, lazy loading, reactivity, and multi-format serialization.

| Need | Typical solution(s) | With Bag |
|------|---------------------|----------|
| Hierarchical data | dict + manual nesting | Native path-based access |
| Configuration | omegaconf, hydra | Bag + builders |
| Lazy/computed values | @property, decorators | Transparent resolvers |
| Reactivity | rxpy, signals, events | Location-based subscriptions |
| XML/JSON handling | lxml, xmltodict | Unified serialization |
| Glue code | Many custom utils | Almost none |

*One coherent model. Less glue. More domain logic. Higher velocity.*

See the full comparison in [Why Bag?](https://genro-bag.readthedocs.io/why-bag/)

## Why this exists

Over time, we noticed that much of the accidental complexity in software comes from constantly translating the same hierarchical ideas into different forms.

This project exists to stop doing that. Not by simplifying domains, but by **unifying how they are described**.

## Install

```bash
pip install genro-bag
```

## Documentation

Full documentation: [genro-bag.readthedocs.io](https://genro-bag.readthedocs.io/)

## Development

```bash
pip install -e ".[dev]"
pytest
```

The project has over 1500 tests with 88%+ coverage.

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.

Copyright 2025 Softwell S.r.l. - Genropy Team
