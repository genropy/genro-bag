# Genro Bag

Most software systems deal with structured things: web pages, configuration files, APIs, database schemas. We usually treat these as separate worlds, each with its own language and tools.

Yet they all share something very simple: **they are organized hierarchically**, and humans reason about them by location rather than by mechanism.

This library starts from that observation.

## A hierarchy as a first-class concept

A Bag is a **hierarchical dictionary**: a tree of named nodes.

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag['config.database.host'] = 'localhost'
>>> bag['config.database.port'] = 5432

>>> bag['config.database.host']
'localhost'
```

Instead of translating hierarchical thinking into tables, messages, or ad-hoc APIs, the hierarchy is kept explicit and central.

## Nodes with values and attributes

Each node can carry both a **value** and arbitrary **attributes**:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag.set_item('user', 'Alice', role='admin', active=True)

>>> bag['user']
'Alice'
>>> bag['user?role']
'admin'
```

## When values are not just values

Some values must be *obtained*: by calling a service, reading hardware, or computing something on demand.

In a Bag, this does not require a different mental model. You still navigate to a place in the hierarchy. Some places just know how to **resolve** a value instead of containing one.

From the outside, access looks the same. You navigate first. Resolution happens later.

Resolvers work transparently in both synchronous and asynchronous contexts — the same code, everywhere.

## Reacting to meaning, not plumbing

Change is inevitable in any non-trivial system. Usually, change is handled through events, callbacks, or polling loops that leak into application code.

A Bag takes a different approach: instead of subscribing to events, you express interest in a **place** in the hierarchy.

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> changes = []

>>> def on_change(**kw):
...     node = kw['node']
...     evt = kw['evt']
...     changes.append(f"{evt}: {node.label}")

>>> bag.subscribe('watcher', any=on_change)
>>> bag['name'] = 'Alice'
>>> bag['name'] = 'Bob'

>>> changes
['ins: name', 'upd_value: name']
```

You care about *what* changed, not *how* the change was transported.

## Writing structure the same way you read it

**Builders** allow structures to be written fluently, in a way that mirrors how they are described mentally:

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import HtmlBuilder

>>> bag = Bag(builder=HtmlBuilder())
>>> div = bag.div(id='main')
>>> div.h1(value='Welcome')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> div.p(value='Hello!')  # doctest: +ELLIPSIS
BagNode : ... at ...

>>> bag['div_0.h1_0']
'Welcome'
```

Builders can also enforce rules about what is allowed, so structures are **valid as they are built**, not validated afterwards.

## One way of thinking, many domains

Once this model is in place, the same way of reasoning can be applied to:

- web pages
- XML documents
- API descriptions
- database structures
- cloud architectures
- shared real-time state

The structure stays the same. Only the vocabulary changes.

## A structural IR, not a framework

This project is best understood as a **structural intermediate representation**.

It sits between how humans reason about structured systems and how specific technologies require them to be expressed.

It does not replace HTML, Terraform, APIs, or databases. It can compile into them, connect them, or synchronize them — and then disappear.

## Why Bag instead of the usual toolbox?

Instead of combining `omegaconf` + `pydantic` + `munch` + `rxpy` + `lxml` + custom glue code, Bag offers **one coherent model** for hierarchical data with attributes, lazy loading, reactivity, and multi-format serialization.

*Less glue. More domain logic. Higher velocity.*

See [Why Bag?](why-bag.md) for a detailed comparison with the typical Python toolbox.

## Installation

```bash
pip install genro-bag
```

## Status

**Development Status: Beta**

The core API is stable. Minor breaking changes may still occur.

```{toctree}
:maxdepth: 2
:caption: Getting Started
:hidden:

installation
quickstart
basic-usage
why-bag
```

```{toctree}
:maxdepth: 2
:caption: User Guide
:hidden:

query-syntax
serialization
resolvers
subscriptions
benchmarks
examples
faq
```

```{toctree}
:maxdepth: 2
:caption: Builders System
:hidden:

builders/index
builders/quickstart
builders/custom-builders
builders/html-builder
builders/validation
builders/advanced
```

```{toctree}
:maxdepth: 2
:caption: Appendix
:hidden:

architecture
```
