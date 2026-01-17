# Core Bag Examples

Practical examples using only core Bag features (no resolvers, subscriptions, or builders).

## Configuration Management

### Application Config

```{doctest}
>>> from genro_bag import Bag

>>> config = Bag()
>>> config['app.name'] = 'MyApp'
>>> config['app.version'] = '1.0.0'
>>> config['database.host'] = 'localhost'
>>> config['database.port'] = 5432
>>> config['database.name'] = 'mydb'
>>> config['logging.level'] = 'INFO'
>>> config['logging.format'] = '%(asctime)s - %(message)s'

>>> # Access nested config
>>> config['database.host']
'localhost'

>>> # Get entire section
>>> db = config['database']
>>> list(db.keys())
['host', 'port', 'name']
```

### Environment-Specific Config

```{doctest}
>>> from genro_bag import Bag

>>> config = Bag()
>>> config.set_item('api_url', 'https://api.example.com', env='production')
>>> config.set_item('api_url_dev', 'http://localhost:8000', env='development')
>>> config.set_item('debug', False, env='production')
>>> config.set_item('debug_dev', True, env='development')

>>> # Find production settings
>>> config.query('#k,#v', condition=lambda n: n.get_attr('env') == 'production')
[('api_url', 'https://api.example.com'), ('debug', False)]
```

## Data Organization

### User Directory

```{doctest}
>>> from genro_bag import Bag

>>> users = Bag()
>>> users.set_item('alice', 'Alice Smith',
...     email='alice@example.com', role='admin', active=True)
>>> users.set_item('bob', 'Bob Jones',
...     email='bob@example.com', role='user', active=True)
>>> users.set_item('carol', 'Carol White',
...     email='carol@example.com', role='user', active=False)

>>> # Find admins
>>> users.query('#v', condition=lambda n: n.get_attr('role') == 'admin')
['Alice Smith']

>>> # Find active users
>>> users.query('#k,#a.email', condition=lambda n: n.get_attr('active'))
[('alice', 'alice@example.com'), ('bob', 'bob@example.com')]
```

### Hierarchical Categories

```{doctest}
>>> from genro_bag import Bag

>>> catalog = Bag()
>>> catalog['electronics.computers.laptops'] = 'MacBook Pro'
>>> catalog['electronics.computers.desktops'] = 'iMac'
>>> catalog['electronics.phones.smartphones'] = 'iPhone'
>>> catalog['clothing.mens.shirts'] = 'Oxford Shirt'
>>> catalog['clothing.womens.dresses'] = 'Summer Dress'

>>> # Get all electronics
>>> electronics = catalog['electronics']
>>> [path for path, node in electronics.walk() if not isinstance(node.value, Bag)]
['computers.laptops', 'computers.desktops', 'phones.smartphones']
```

## Data Transformation

### Flattening Nested Data

```{doctest}
>>> from genro_bag import Bag

>>> nested = Bag()
>>> nested['a.b.c'] = 1
>>> nested['a.b.d'] = 2
>>> nested['a.e'] = 3

>>> # Flatten to dict
>>> flat = {path: node.value for path, node in nested.walk()
...         if not isinstance(node.value, Bag)}
>>> flat
{'a.b.c': 1, 'a.b.d': 2, 'a.e': 3}
```

### Building from Flat Data

```{doctest}
>>> from genro_bag import Bag

>>> flat_data = {
...     'user.name': 'Alice',
...     'user.email': 'alice@example.com',
...     'settings.theme': 'dark',
...     'settings.notifications': True
... }

>>> bag = Bag()
>>> for path, value in flat_data.items():
...     bag[path] = value

>>> bag['user.name']
'Alice'
>>> bag['settings.theme']
'dark'
```

## Order and Positioning

### Priority Queue

```{doctest}
>>> from genro_bag import Bag

>>> tasks = Bag()
>>> tasks.set_item('task1', 'Low priority task', priority=3)
>>> tasks.set_item('task2', 'High priority task', priority=1)
>>> tasks.set_item('task3', 'Medium priority task', priority=2)

>>> # Get tasks sorted by priority
>>> sorted_tasks = sorted(
...     [(n.get_attr('priority'), n.value) for n in tasks],
...     key=lambda x: x[0]
... )
>>> [t[1] for t in sorted_tasks]
['High priority task', 'Medium priority task', 'Low priority task']
```

### Ordered Insertion

```{doctest}
>>> from genro_bag import Bag

>>> menu = Bag()
>>> menu['main'] = 'Main Course'
>>> menu.set_item('appetizer', 'Appetizer', node_position='<')  # Before all
>>> menu.set_item('dessert', 'Dessert', node_position='>')  # After all
>>> menu.set_item('soup', 'Soup', node_position='>appetizer')  # After appetizer

>>> list(menu.keys())
['appetizer', 'soup', 'main', 'dessert']
```

## XML Round-Trip

### Configuration File

```{doctest}
>>> from genro_bag import Bag

>>> # Create config
>>> config = Bag()
>>> config.set_item('server', None, host='localhost', port='8080')
>>> config.set_item('database', None, driver='postgresql', name='mydb')

>>> # Save to XML string
>>> xml = config.to_xml()
>>> 'host="localhost"' in xml
True

>>> # Parse back
>>> restored = Bag.from_xml(f'<config>{xml}</config>')
>>> restored['config.server?host']
'localhost'
```

## Aggregation

### Shopping Cart

```{doctest}
>>> from genro_bag import Bag

>>> cart = Bag()
>>> cart.set_item('item1', 'Widget A', price=10, qty=2)
>>> cart.set_item('item2', 'Widget B', price=25, qty=1)
>>> cart.set_item('item3', 'Widget C', price=5, qty=4)

>>> # Calculate totals
>>> total = sum(n.get_attr('price') * n.get_attr('qty') for n in cart)
>>> total
65

>>> # Item count
>>> item_count = sum(n.get_attr('qty') for n in cart)
>>> item_count
7
```

### Statistics

```{doctest}
>>> from genro_bag import Bag

>>> scores = Bag({'alice': 85, 'bob': 92, 'carol': 78, 'dave': 95})

>>> values = list(scores.values())
>>> avg = sum(values) / len(values)
>>> avg
87.5

>>> max_score = max(values)
>>> max_score
95

>>> # Who has max score?
>>> scores.query('#k', condition=lambda n: n.value == max_score)
['dave']
```

## Pattern: Merge Bags

```{doctest}
>>> from genro_bag import Bag

>>> defaults = Bag({'timeout': 30, 'retries': 3, 'debug': False})
>>> overrides = Bag({'timeout': 60, 'debug': True})

>>> # Merge overrides into defaults
>>> merged = Bag()
>>> for node in defaults:
...     merged[node.label] = node.value
>>> for node in overrides:
...     merged[node.label] = node.value

>>> merged['timeout']
60
>>> merged['retries']
3
>>> merged['debug']
True
```

## Pattern: Clone and Modify

```{doctest}
>>> from genro_bag import Bag

>>> template = Bag()
>>> template['type'] = 'user'
>>> template['status'] = 'active'
>>> template['permissions'] = 'read'

>>> # Clone via TYTX round-trip
>>> user1 = Bag.from_tytx(template.to_tytx())
>>> user1['name'] = 'Alice'
>>> user1['permissions'] = 'admin'

>>> user2 = Bag.from_tytx(template.to_tytx())
>>> user2['name'] = 'Bob'

>>> user1['permissions']
'admin'
>>> user2['permissions']
'read'
```
