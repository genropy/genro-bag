# Basic Usage

This guide covers fundamental operations: creating, storing, accessing, and manipulating data.

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

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag['user'] = 'Alice'
>>> bag['config.debug'] = True
>>> bag['config.database.host'] = 'localhost'
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

## Iteration

### Iterating Over Nodes

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag({'a': 1, 'b': 2, 'c': 3})

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
```

Position syntax:

| Syntax | Meaning |
|--------|---------|
| `<` | Prepend (beginning) |
| `>` | Append (end, default) |
| `<label` | Before node with label |
| `>label` | After node with label |
| `#n` | At numeric index |

## Nested Bags

Values can be Bags themselves:

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
