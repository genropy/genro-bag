# Query Syntax

Bag provides powerful query capabilities to extract, filter, and traverse hierarchical data.

## The query() Method

The main query method is `query()`. It extracts data using a concise syntax:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag.set_item('alice', 'Alice Smith', role='admin', age=30)
>>> bag.set_item('bob', 'Bob Jones', role='user', age=25)

>>> # Get all labels and values
>>> bag.query('#k,#v')
[('alice', 'Alice Smith'), ('bob', 'Bob Jones')]

>>> # Get labels and specific attribute
>>> bag.query('#k,#a.role')
[('alice', 'admin'), ('bob', 'user')]
```

## Query Specifiers

| Syntax | Description |
|--------|-------------|
| `#k` | Node label (key) |
| `#v` | Node value |
| `#a` | All attributes as dict |
| `#a.name` | Specific attribute |
| `#p` | Full path (useful with `deep=True`) |
| `#n` | The BagNode object itself |
| `#__v` | Static value (bypasses resolvers) |

## Basic Queries

### Single Specifier

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag({'x': 10, 'y': 20, 'z': 30})

>>> # All labels
>>> bag.query('#k')
['x', 'y', 'z']

>>> # All values
>>> bag.query('#v')
[10, 20, 30]
```

### Multiple Specifiers

Combine specifiers with commas:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag.set_item('item1', 100, category='A')
>>> bag.set_item('item2', 200, category='B')

>>> bag.query('#k,#v,#a.category')
[('item1', 100, 'A'), ('item2', 200, 'B')]
```

## Filtering

### By Condition

Pass a callable that receives a BagNode and returns boolean:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag.set_item('alice', 100, active=True)
>>> bag.set_item('bob', 50, active=False)
>>> bag.set_item('carol', 75, active=True)

>>> # Only active users
>>> bag.query('#k,#v', condition=lambda n: n.get_attr('active'))
[('alice', 100), ('carol', 75)]

>>> # Values greater than 60
>>> bag.query('#k', condition=lambda n: n.value > 60)
['alice', 'carol']
```

## Deep Traversal

Use the `walk()` method for recursive traversal of nested Bags:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag['config.database.host'] = 'localhost'
>>> bag['config.database.port'] = 5432
>>> bag['config.debug'] = True

>>> # Get all paths using walk()
>>> [path for path, node in bag.walk()]
['config', 'config.database', 'config.database.host', 'config.database.port', 'config.debug']
```

## Path-Based Access

Query a specific subtree using `path:what` syntax:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag['users.alice'] = 'Alice'
>>> bag['users.bob'] = 'Bob'
>>> bag['config.debug'] = True

>>> # Query only the users subtree
>>> bag.query('users:#k')
['alice', 'bob']
```

## The walk() Method

For full tree traversal, use `walk()`:

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

## Finding Nodes

### By Attribute

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag.set_item('user1', 'Alice', id='u001')
>>> bag.set_item('user2', 'Bob', id='u002')

>>> node = bag.get_node_by_attr('id', 'u002')
>>> node.value
'Bob'
```

### By Value Content

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

### Sum Values

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag({'a': 10, 'b': 20, 'c': 30})
>>> bag.sum()
60
```

### Sum Attributes

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag.set_item('item1', 100, price=100)
>>> bag.set_item('item2', 200, price=200)

>>> bag.sum('#a.price')
300
```

## Access Syntax Shortcuts

In addition to `query()`, you can use path syntax for quick queries:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag.set_item('user', 'Alice', role='admin')

>>> # Value access
>>> bag['user']
'Alice'

>>> # Attribute access
>>> bag['user?role']
'admin'
```

## Summary

| Method | Purpose |
|--------|---------|
| `query(what)` | Extract data with query syntax |
| `walk()` | Generator for tree traversal |
| `get_node_by_attr(attr, val)` | Find node by attribute |
| `get_node_by_value(key, val)` | Find node by value content |
| `sum(attr)` | Sum values or attributes |
| `keys()`, `values()`, `items()` | Dict-like iteration |

## Next Steps

- Learn about [Serialization](serialization.md) for saving/loading
- Explore [Resolvers](resolvers.md) for lazy loading
- Understand [Subscriptions](subscriptions.md) for reactivity
