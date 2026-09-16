# Getting Started

Learn Bag in 5 minutes. No resolvers, no subscriptions — just the core.

## Install

```bash
pip install genro-bag
```

## Create a Bag

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
```

### Create named nodes with tuples

A tuple describes one node: `(label, value)` or `(label, value, attributes)`.
A list or tuple of these node tuples creates multiple named nodes in order.
This syntax is available directly, without enabling legacy mode.

```python
project = Bag(('project', None, {'name': 'demo', 'language': 'en'}))
rows = Bag([
    ('first', 10, {'caption': 'First'}),
    ('second', 20),
])
```

Labels must be strings. Attributes must be a mapping or `None`; the mapping
is copied. Values, including resolvers, are passed to normal `set_item`
semantics. Paths and repeated labels behave as repeated `set_item` calls.

Other lists remain positional: `Bag(['first', 10])` has labels `"0"` and
`"1"`. Lists of lists also remain positional. A list of named node tuples is
now interpreted as node specifications; use an explicit mapping such as
`Bag({'0': ('first', 10)})` to store such a tuple as a value instead.
To replace existing contents, use `bag.replace(Bag(source))`. Parsing completes before replacement.

### Mount a directory

```python
bag = Bag('/srv/config')
# The directory node is named after the directory, and remains lazy.
value = bag['config.environment_xml.setting']
```

An existing directory path, supplied as a string or `pathlib.Path`, mounts a
`DirectoryResolver` under its basename. Subdirectories and supported files are
loaded synchronously on demand. `bag.replace(Bag(directory))` supports the same input.
Node labels follow normal Bag path semantics, as in the historical constructor.

For compatibility, `_template_kargs` passed alongside a source is ignored,
matching the historical constructor's treatment of that misspelled option.
It does not perform environment substitution.

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

::::
