# Genro Bag

**Genro Bag** is a hierarchical data container for the Genropy framework, providing:

- **Tree-like Structure**: Organize nested data with nodes, values, and attributes
- **Builders System**: Domain-specific fluent APIs for constructing validated structures
- **Serialization**: XML, JSON, and MessagePack support via TyTx format

## Quick Example

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import HtmlBuilder

>>> # Create a Bag with HTML builder
>>> bag = Bag(builder=HtmlBuilder())

>>> # Build structure with fluent API
>>> div = bag.div(id='main', class_='container')
>>> div.h1(value='Welcome')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> div.p(value='Hello, World!')  # doctest: +ELLIPSIS
BagNode : ... at ...

>>> # Access the structure
>>> bag['div_0.h1_0']
'Welcome'
>>> len(list(div))  # 2 children: h1 and p
2
```

## Features

### Hierarchical Data Storage

Organize data in a tree structure with path-based access:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag.set_item('config.database.host', 'localhost')
>>> bag.set_item('config.database.port', 5432)

>>> bag['config.database.host']
'localhost'
>>> bag['config.database.port']
5432
```

### Builders System

Create domain-specific APIs with validation:

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element

>>> class MenuBuilder(BagBuilderBase):
...     @element(children='item')
...     def menu(self, target, tag, **attr):
...         return self.child(target, tag, **attr)
...
...     @element()
...     def item(self, target, tag, value=None, **attr):
...         return self.child(target, tag, value=value or '', **attr)

>>> bag = Bag(builder=MenuBuilder())
>>> menu = bag.menu(id='nav')
>>> menu.item(value='Home', href='/')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> menu.item(value='About', href='/about')  # doctest: +ELLIPSIS
BagNode : ... at ...
```

### HTML Generation

Build complete HTML pages with `HtmlPage`:

```{doctest}
>>> from genro_bag.builders import HtmlPage

>>> page = HtmlPage()
>>> page.head.title(value='My Site')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> page.body.div().p(value='Welcome!')  # doctest: +ELLIPSIS
BagNode : ... at ...

>>> html = page.to_html()
>>> '<!DOCTYPE html>' in html
True
>>> '<title>My Site</title>' in html
True
```

### Attributes on Nodes

Nodes can have both values and arbitrary attributes:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag.set_item('user', 'Alice', role='admin', active=True)
>>> bag['user']
'Alice'
>>> bag['user?role']
'admin'
>>> bag['user?active']
True
```

## Installation

```bash
pip install genro-bag
```

## Documentation

```{toctree}
:maxdepth: 2
:caption: Getting Started

installation
quickstart
basic-usage
```

```{toctree}
:maxdepth: 2
:caption: User Guide

query-syntax
serialization
resolvers
subscriptions
```

```{toctree}
:maxdepth: 2
:caption: Builders System

builders/index
builders/quickstart
builders/custom-builders
builders/html-builder
builders/validation
builders/advanced
```

## Status

**Development Status: Alpha**

The core API is stabilizing. Breaking changes may still occur.

## Indices and tables

- {ref}`genindex`
- {ref}`modindex`
- {ref}`search`
