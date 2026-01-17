# Genro Bag

A **hierarchical dictionary** for Python: a tree of named nodes with values and attributes.

## The Core Idea

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag['config.database.host'] = 'localhost'
>>> bag['config.database.port'] = 5432

>>> bag['config.database.host']
'localhost'
```

Three concepts, that's all:

1. **Paths** - Navigate with dots: `bag['a.b.c']`
2. **Values** - Each node holds a value
3. **Attributes** - Each node can have metadata: `bag['user?role']`

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag.set_item('user', 'Alice', role='admin', active=True)

>>> bag['user']
'Alice'
>>> bag['user?role']
'admin'
```

## Installation

```bash
pip install genro-bag
```

## Learn Bag in 5 Minutes

→ [Getting Started](getting-started.md)

## When You Need More

Bag is intentionally minimal at its core. As your needs grow, explore these extensions:

::::{grid} 2
:gutter: 3

:::{grid-item-card} Resolvers
:link: resolvers/index
:link-type: doc

Values that compute themselves: lazy loading, API calls, file watches.
:::

:::{grid-item-card} Subscriptions
:link: subscriptions/index
:link-type: doc

React to changes: validation, logging, computed properties.
:::

:::{grid-item-card} Builders
:link: builders/index
:link-type: doc

Domain-specific languages: HTML, Markdown, XML schemas.
:::

:::{grid-item-card} Why Bag?
:link: reference/why-bag
:link-type: doc

Comparison with omegaconf, pydantic, munch, and the typical Python toolbox.
:::

::::

## Status

**Development Status: Beta** — Core API is stable. Minor breaking changes may still occur.

---

```{toctree}
:maxdepth: 1
:caption: Start Here
:hidden:

getting-started
```

```{toctree}
:maxdepth: 2
:caption: Core Bag
:hidden:

bag/README
bag/basic-usage
bag/paths-and-access
bag/attributes
bag/serialization
bag/examples
bag/faq
```

```{toctree}
:maxdepth: 2
:caption: Resolvers
:hidden:

resolvers/README
resolvers/builtin
resolvers/custom
resolvers/examples
resolvers/faq
```

```{toctree}
:maxdepth: 2
:caption: Subscriptions
:hidden:

subscriptions/README
subscriptions/events
subscriptions/examples
subscriptions/faq
```

```{toctree}
:maxdepth: 2
:caption: Builders
:hidden:

builders/README
builders/quickstart
builders/html-builder
builders/markdown-builder
builders/xsd-builder
builders/custom-builders
builders/validation
builders/advanced
builders/examples
builders/faq
```

```{toctree}
:maxdepth: 1
:caption: Reference
:hidden:

reference/why-bag
reference/architecture
reference/benchmarks
reference/full-faq
```
