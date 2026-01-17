# Node Attributes

Every node in a Bag can carry **attributes** (metadata) separate from its value.

## Why Attributes?

Values represent *what* the data is. Attributes represent *how* to interpret or handle it.

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag.set_item('api_key', 'sk-xxx', env='production', expires=2025, encrypted=True)

>>> bag['api_key']  # The value
'sk-xxx'

>>> bag['api_key?env']  # Metadata about the value
'production'
```

## Setting Attributes

### With set_item()

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag.set_item('user', 'Alice', role='admin', active=True, level=5)

>>> bag['user']
'Alice'
>>> bag['user?role']
'admin'
```

### With _attributes Parameter

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> attrs = {'region': 'eu', 'tier': 1, 'tags': ['web', 'api']}
>>> bag.set_item('server', 'prod-01', _attributes=attrs)

>>> bag['server?region']
'eu'
>>> bag['server?tags']
['web', 'api']
```

### After Creation

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag['user'] = 'Alice'

>>> # Set attribute using ? syntax
>>> bag['user?role'] = 'admin'
>>> bag['user?role']
'admin'
```

## Reading Attributes

### Single Attribute

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag.set_item('item', 100, category='A', priority=1)

>>> bag['item?category']
'A'
>>> bag['item?priority']
1
>>> bag['item?missing']  # Missing attribute returns None
```

### All Attributes

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag.set_item('item', 100, category='A', priority=1)

>>> node = bag.get_node('item')
>>> node.attr
{'category': 'A', 'priority': 1}
```

### Using get_attr()

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag.set_item('item', 100, category='A')

>>> node = bag.get_node('item')
>>> node.get_attr('category')
'A'
>>> node.get_attr('missing', default='N/A')
'N/A'
```

## Attribute Types

Attributes can be any Python value:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag.set_item('config', None,
...     enabled=True,              # bool
...     count=42,                  # int
...     ratio=3.14,               # float
...     name='test',              # str
...     tags=['a', 'b'],          # list
...     meta={'x': 1, 'y': 2}     # dict
... )

>>> bag['config?enabled']
True
>>> bag['config?tags']
['a', 'b']
>>> bag['config?meta']
{'x': 1, 'y': 2}
```

## Querying by Attribute

### Filter by Attribute Value

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag.set_item('alice', 'Alice', role='admin')
>>> bag.set_item('bob', 'Bob', role='user')
>>> bag.set_item('carol', 'Carol', role='admin')

>>> bag.query('#k', condition=lambda n: n.get_attr('role') == 'admin')
['alice', 'carol']
```

### Extract Attributes

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag.set_item('p1', 'Product 1', price=100)
>>> bag.set_item('p2', 'Product 2', price=200)

>>> bag.query('#k,#a.price')
[('p1', 100), ('p2', 200)]

>>> bag.sum('#a.price')
300
```

### Find by Attribute

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag.set_item('user1', 'Alice', id='u001')
>>> bag.set_item('user2', 'Bob', id='u002')

>>> node = bag.get_node_by_attr('id', 'u002')
>>> node.value
'Bob'
```

## Serialization

Attributes are preserved in all serialization formats:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag.set_item('item', 'value', meta='data')

>>> # XML preserves attributes
>>> xml = bag.to_xml()
>>> 'meta="data"' in xml
True

>>> # Round-trip preserves attributes
>>> bag2 = Bag.from_xml(xml)
>>> bag2['item?meta']
'data'
```

## Common Patterns

### Configuration with Defaults

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag.set_item('timeout', 30, unit='seconds', default=True)
>>> bag.set_item('retries', 3, default=True)
>>> bag.set_item('host', 'custom.example.com', default=False)

>>> # Find custom (non-default) settings
>>> bag.query('#k', condition=lambda n: not n.get_attr('default', True))
['host']
```

### Type Hints

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag.set_item('age', '25', type='int')
>>> bag.set_item('active', 'true', type='bool')
>>> bag.set_item('score', '3.14', type='float')

>>> # Use type hints to convert
>>> def convert(node):
...     t = node.get_attr('type')
...     v = node.value
...     if t == 'int': return int(v)
...     if t == 'bool': return v.lower() == 'true'
...     if t == 'float': return float(v)
...     return v

>>> node = bag.get_node('age')
>>> convert(node)
25
```

### Validation State

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag.set_item('email', 'test@example.com', validated=True)
>>> bag.set_item('phone', 'invalid', validated=False, error='Invalid format')

>>> # Find invalid fields
>>> bag.query('#k,#a.error', condition=lambda n: not n.get_attr('validated', True))
[('phone', 'Invalid format')]
```
