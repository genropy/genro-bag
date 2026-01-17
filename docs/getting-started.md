# Getting Started

Learn Bag in 5 minutes. No resolvers, no subscriptions, no builders — just the core.

## Install

```bash
pip install genro-bag
```

## Create a Bag

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
```

## Store Values with Paths

Use dot-separated paths. Intermediate nodes are created automatically.

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag['name'] = 'Alice'
>>> bag['config.database.host'] = 'localhost'
>>> bag['config.database.port'] = 5432
```

## Read Values

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag['config.database.host'] = 'localhost'
>>> bag['config.database.port'] = 5432

>>> bag['config.database.host']
'localhost'

>>> # Get intermediate Bag
>>> db = bag['config.database']
>>> db['port']
5432
```

## Add Attributes (Metadata)

Every node can carry attributes separate from its value.

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag.set_item('api_key', 'sk-xxx', env='production', expires=2025)

>>> bag['api_key']
'sk-xxx'

>>> bag['api_key?env']
'production'
```

## Iterate

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag({'a': 1, 'b': 2, 'c': 3})

>>> for node in bag:
...     print(f"{node.label}: {node.value}")
a: 1
b: 2
c: 3

>>> list(bag.keys())
['a', 'b', 'c']
```

## Serialize

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag['name'] = 'Test'
>>> bag['count'] = 42

>>> xml = bag.to_xml()
>>> '<name>Test</name>' in xml
True

>>> # Round-trip
>>> bag2 = Bag.from_xml('<root><x>1</x></root>')
>>> bag2['root.x']
'1'
```

## That's It

You now know Bag. Three concepts:

| Concept | Syntax | Example |
|---------|--------|---------|
| Path | `bag['a.b.c']` | Navigate hierarchy |
| Value | `bag['key'] = value` | Store data |
| Attribute | `bag['key?attr']` | Add metadata |

## What's Next?

::::{grid} 2
:gutter: 3

:::{grid-item-card} Deep Dive: Core Bag
:link: bag/basic-usage
:link-type: doc

Positioning, deletion, nested Bags, and more.
:::

:::{grid-item-card} When values need to compute themselves
:link: resolvers/index
:link-type: doc

Lazy loading, API calls, file watches.
:::

:::{grid-item-card} When you need to react to changes
:link: subscriptions/index
:link-type: doc

Validation, logging, computed properties.
:::

:::{grid-item-card} When you need domain-specific structure
:link: builders/index
:link-type: doc

HTML, Markdown, XML schemas — validated as you build.
:::

::::
