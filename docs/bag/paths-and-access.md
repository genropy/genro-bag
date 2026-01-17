# Paths and Access

Complete guide to navigating and querying Bag hierarchies.

## Path Syntax

### Dot-Separated Paths

The fundamental access pattern:

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

### Index Access

Use `#n` for positional access:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag({'a': 1, 'b': 2, 'c': 3})

>>> bag['#0']  # First element
1
>>> bag['#2']  # Third element
3
>>> bag['#-1']  # Last element
3
```

### Attribute Access

Use `?attr` to access node attributes:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag.set_item('user', 'Alice', role='admin', active=True)

>>> bag['user']  # Value
'Alice'
>>> bag['user?role']  # Attribute
'admin'
>>> bag['user?active']
True
```

## Query Syntax

The `query()` method extracts structured data:

### Query Specifiers

| Syntax | Description |
|--------|-------------|
| `#k` | Node label (key) |
| `#v` | Node value |
| `#a` | All attributes as dict |
| `#a.name` | Specific attribute |
| `#p` | Full path |
| `#n` | The BagNode object itself |

### Basic Queries

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag({'x': 10, 'y': 20, 'z': 30})

>>> bag.query('#k')
['x', 'y', 'z']

>>> bag.query('#v')
[10, 20, 30]

>>> bag.query('#k,#v')
[('x', 10), ('y', 20), ('z', 30)]
```

### With Attributes

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag.set_item('alice', 'Alice Smith', role='admin', age=30)
>>> bag.set_item('bob', 'Bob Jones', role='user', age=25)

>>> bag.query('#k,#a.role')
[('alice', 'admin'), ('bob', 'user')]
```

### Filtering

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag.set_item('alice', 100, active=True)
>>> bag.set_item('bob', 50, active=False)
>>> bag.set_item('carol', 75, active=True)

>>> bag.query('#k,#v', condition=lambda n: n.get_attr('active'))
[('alice', 100), ('carol', 75)]
```

### Path-Based Query

Query a specific subtree:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag['users.alice'] = 'Alice'
>>> bag['users.bob'] = 'Bob'
>>> bag['config.debug'] = True

>>> bag.query('users:#k')
['alice', 'bob']
```

## Tree Traversal

### The walk() Method

Recursive traversal of all nodes:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag['a.b'] = 1
>>> bag['a.c'] = 2

>>> for path, node in bag.walk():
...     print(f"{path}: {node.value}")
a: ...
a.b: 1
a.c: 2
```

### Finding Nodes

By attribute:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag.set_item('user1', 'Alice', id='u001')
>>> bag.set_item('user2', 'Bob', id='u002')

>>> node = bag.get_node_by_attr('id', 'u002')
>>> node.value
'Bob'
```

By value content:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag['users'] = Bag({'name': 'Alice', 'age': 30})
>>> bag['admins'] = Bag({'name': 'Bob', 'age': 25})

>>> node = bag.get_node_by_value('name', 'Bob')
>>> node.label
'admins'
```

## Aggregation

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag({'a': 10, 'b': 20, 'c': 30})
>>> bag.sum()
60

>>> bag2 = Bag()
>>> bag2.set_item('item1', None, price=100)
>>> bag2.set_item('item2', None, price=200)
>>> bag2.sum('#a.price')
300
```

## Quick Reference

| Operation | Syntax |
|-----------|--------|
| Get by path | `bag['a.b.c']` |
| Get by index | `bag['#0']` |
| Get attribute | `bag['key?attr']` |
| Query labels | `bag.query('#k')` |
| Query values | `bag.query('#v')` |
| Query combo | `bag.query('#k,#v,#a.attr')` |
| Filter | `bag.query('#k', condition=fn)` |
| Subtree query | `bag.query('path:#k')` |
| Walk tree | `for path, node in bag.walk()` |
| Find by attr | `bag.get_node_by_attr(attr, val)` |
| Find by value | `bag.get_node_by_value(key, val)` |
