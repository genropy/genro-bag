# Basic Usage

This guide covers the fundamental operations for working with Bag: creating, storing, accessing, and manipulating hierarchical data.

## Creating a Bag

```{doctest}
>>> from genro_bag import Bag

>>> # Empty bag
>>> bag = Bag()

>>> # From a dictionary
>>> bag = Bag({'name': 'Alice', 'age': 30})
>>> bag['name']
'Alice'
```

## Storing Values

### Simple Assignment

Use bracket notation with dot-separated paths:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag['user'] = 'Alice'
>>> bag['config.debug'] = True
>>> bag['config.database.host'] = 'localhost'
>>> bag['config.database.port'] = 5432
```

Intermediate Bags are created automatically when you assign to nested paths.

### Using set_item()

For more control, use `set_item()` which accepts attributes and positioning:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag.set_item('user', 'Alice', role='admin', active=True)
>>> bag['user']
'Alice'
>>> bag['user?role']
'admin'
```

## Accessing Values

### By Label

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag({'a': 1, 'b': 2, 'c': 3})
>>> bag['a']
1
>>> bag['missing']  # Returns None for missing keys
```

### By Path

Access nested values with dot-separated paths:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag['config.database.host'] = 'localhost'
>>> bag['config.database.port'] = 5432

>>> bag['config.database.host']
'localhost'

>>> # Get intermediate Bag
>>> db = bag['config.database']
>>> db['host']
'localhost'
```

### By Index

Access by position using `#n` syntax:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag['first'] = 1
>>> bag['second'] = 2
>>> bag['third'] = 3

>>> bag['#0']  # First element
1
>>> bag['#2']  # Third element (0-indexed)
3
```

## Node Attributes

Every node can have attributes separate from its value:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag.set_item('api_key', 'sk-xxx', env='production', expires=2025)

>>> # Get value
>>> bag['api_key']
'sk-xxx'

>>> # Get attribute with ?attr syntax
>>> bag['api_key?env']
'production'
>>> bag['api_key?expires']
2025

>>> # Get all attributes
>>> node = bag.get_node('api_key')
>>> node.attr
{'env': 'production', 'expires': 2025}
```

### Setting Attributes

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag['user'] = 'Alice'

>>> # Set attribute after creation
>>> bag['user?role'] = 'admin'
>>> bag['user?role']
'admin'

>>> # Or via set_item with _attributes
>>> bag.set_item('server', 'prod-01', _attributes={'region': 'eu', 'tier': 1})
>>> bag['server?region']
'eu'
```

## Iteration

### Iterating Over Nodes

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag({'a': 1, 'b': 2, 'c': 3})

>>> # Iterate yields BagNode objects
>>> for node in bag:
...     print(f"{node.label}: {node.value}")
a: 1
b: 2
c: 3
```

### Keys, Values, Items

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag({'x': 10, 'y': 20})

>>> list(bag.keys())
['x', 'y']

>>> list(bag.values())
[10, 20]

>>> list(bag.items())
[('x', 10), ('y', 20)]
```

## Modifying

### Deleting

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag({'a': 1, 'b': 2, 'c': 3})
>>> del bag['b']
>>> list(bag.keys())
['a', 'c']

>>> # Pop returns the value
>>> bag.pop('a')
1
>>> list(bag.keys())
['c']
```

### Clearing

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag({'a': 1, 'b': 2})
>>> bag.clear()
>>> len(bag)
0
```

## Positioning

Control where new items are inserted:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag['middle'] = 2

>>> # Insert at beginning
>>> bag.set_item('first', 1, node_position='<')
>>> list(bag.keys())
['first', 'middle']

>>> # Insert at end (default)
>>> bag.set_item('last', 3, node_position='>')
>>> list(bag.keys())
['first', 'middle', 'last']

>>> # Insert before a label
>>> bag.set_item('before_last', 2.5, node_position='<last')
>>> list(bag.keys())
['first', 'middle', 'before_last', 'last']

>>> # Insert after a label
>>> bag.set_item('after_first', 1.5, node_position='>first')
>>> list(bag.keys())
['first', 'after_first', 'middle', 'before_last', 'last']
```

Position syntax:

- `<` - Prepend (insert at beginning)
- `>` - Append (insert at end, default)
- `<label` - Insert before the node with given label
- `>label` - Insert after the node with given label
- `#n` - Insert at numeric index

## Nested Bags

Values can be Bags themselves, creating hierarchies:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag['config'] = Bag({'debug': True, 'version': '1.0'})
>>> bag['config.debug']
True

>>> # Or let auto-creation handle it
>>> bag2 = Bag()
>>> bag2['a.b.c'] = 'deep'
>>> bag2['a.b.d'] = 'also deep'
>>> bag2['a.b.c']
'deep'
```

## Checking Contents

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag({'x': 1, 'y': 2})

>>> 'x' in bag
True
>>> 'z' in bag
False

>>> len(bag)
2

>>> bool(Bag())  # Empty bag is falsy
False
>>> bool(bag)  # Non-empty bag is truthy
True
```

## Getting Nodes

To access the BagNode object (not just the value):

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag.set_item('user', 'Alice', role='admin')

>>> node = bag.get_node('user')
>>> node.label
'user'
>>> node.value
'Alice'
>>> node.attr
{'role': 'admin'}
```

## Next Steps

- Learn about [Query Syntax](query-syntax.md) for extracting data
- Explore [Serialization](serialization.md) for saving/loading
- Understand [Resolvers](resolvers.md) for lazy loading
- Master [Subscriptions](subscriptions.md) for reactivity
