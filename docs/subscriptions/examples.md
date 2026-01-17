# Subscription Examples

Practical examples of reactivity patterns.

## Validation

### Email Validation

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()

>>> def validate_email(**kw):
...     node = kw['node']
...     evt = kw['evt']
...     if evt == 'upd_value' and node.label == 'email':
...         if '@' not in str(node.value):
...             raise ValueError('Invalid email')

>>> bag.subscribe('validator', update=validate_email)

>>> bag['email'] = 'test@example.com'  # OK

>>> try:
...     bag['email'] = 'invalid'
... except ValueError as e:
...     print(e)
Invalid email
```

### Range Validation

```{doctest}
>>> from genro_bag import Bag

>>> form = Bag()

>>> def validate_range(**kw):
...     node = kw['node']
...     if node.label == 'age':
...         age = node.value
...         if not (0 <= age <= 150):
...             raise ValueError(f'Age must be 0-150, got {age}')

>>> form.subscribe('validator', any=validate_range)

>>> form['age'] = 25  # OK

>>> try:
...     form['age'] = 200
... except ValueError as e:
...     'Age must be' in str(e)
True
```

## Change Logging

### Simple Audit Log

```python
import logging
from genro_bag import Bag

def audit_log(**kw):
    node = kw['node']
    pathlist = kw['pathlist']
    evt = kw['evt']
    path = '.'.join(pathlist)

    if evt == 'ins':
        logging.info(f"Created {path} = {node.value}")
    elif evt == 'upd_value':
        logging.info(f"Updated {path} = {node.value}")
    elif evt == 'del':
        logging.info(f"Deleted {path}")

config = Bag()
config.subscribe('audit', any=audit_log)

config['database.host'] = 'localhost'
# Log: Created database
# Log: Created database.host = localhost
```

### Change History

```{doctest}
>>> from genro_bag import Bag
>>> from datetime import datetime

>>> bag = Bag()
>>> history = []

>>> def track_history(**kw):
...     node = kw['node']
...     evt = kw['evt']
...     history.append({
...         'label': node.label,
...         'value': node.value,
...         'event': evt
...     })

>>> bag.subscribe('history', any=track_history)

>>> bag['count'] = 0
>>> bag['count'] = 1
>>> bag['count'] = 2

>>> [h['value'] for h in history if h['label'] == 'count']
[0, 1, 2]
```

## Computed Properties

### Auto-Calculate Total

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag['price'] = 100
>>> bag['quantity'] = 5
>>> bag['total'] = 500

>>> def update_total(**kw):
...     node = kw['node']
...     if node.label in ('price', 'quantity'):
...         parent = node.parent_bag
...         parent['total'] = parent['price'] * parent['quantity']

>>> bag.subscribe('calculator', update=update_total)

>>> bag['price'] = 150
>>> bag['total']
750

>>> bag['quantity'] = 3
>>> bag['total']
450
```

### Derived Status

```{doctest}
>>> from genro_bag import Bag

>>> order = Bag()
>>> order['items_count'] = 0
>>> order['status'] = 'empty'

>>> def update_status(**kw):
...     node = kw['node']
...     if node.label == 'items_count':
...         parent = node.parent_bag
...         count = node.value
...         if count == 0:
...             parent['status'] = 'empty'
...         elif count < 5:
...             parent['status'] = 'partial'
...         else:
...             parent['status'] = 'full'

>>> order.subscribe('status', update=update_status)

>>> order['items_count'] = 3
>>> order['status']
'partial'

>>> order['items_count'] = 10
>>> order['status']
'full'
```

## Synchronization

### Mirror to Another Bag

```{doctest}
>>> from genro_bag import Bag

>>> source = Bag()
>>> mirror = Bag()

>>> def sync_to_mirror(**kw):
...     node = kw['node']
...     evt = kw['evt']
...     label = node.label
...     if evt == 'ins':
...         mirror[label] = node.value
...     elif evt == 'upd_value':
...         mirror[label] = node.value
...     elif evt == 'del':
...         if label in mirror:
...             del mirror[label]

>>> source.subscribe('sync', any=sync_to_mirror)

>>> source['a'] = 1
>>> source['b'] = 2

>>> mirror['a']
1
>>> mirror['b']
2
```

### Selective Sync

```python
from genro_bag import Bag

source = Bag()
public = Bag()

def sync_public(**kw):
    node = kw['node']
    # Only sync non-private fields
    if not node.label.startswith('_'):
        path = '.'.join(kw['pathlist'])
        if kw['evt'] in ('ins', 'upd_value'):
            public[path] = node.value

source.subscribe('public_sync', any=sync_public)

source['name'] = 'Alice'      # Synced
source['_password'] = 'xxx'   # Not synced

public['name']      # 'Alice'
public['_password'] # None (not synced)
```

## UI Patterns

### Form Dirty Tracking

```{doctest}
>>> from genro_bag import Bag

>>> form = Bag()
>>> form['_dirty'] = False
>>> form['_original'] = {}

>>> def mark_dirty(**kw):
...     evt = kw['evt']
...     node = kw['node']
...     if evt == 'upd_value' and not node.label.startswith('_'):
...         node.parent_bag['_dirty'] = True

>>> form.subscribe('dirty', update=mark_dirty)

>>> form['name'] = 'Alice'  # Insert, not update
>>> form['_dirty']
False

>>> form['name'] = 'Bob'  # Update
>>> form['_dirty']
True
```

### Change Counter

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag['_change_count'] = 0

>>> def count_changes(**kw):
...     if not kw['node'].label.startswith('_'):
...         bag['_change_count'] = bag['_change_count'] + 1

>>> bag.subscribe('counter', any=count_changes)

>>> bag['a'] = 1
>>> bag['b'] = 2
>>> bag['a'] = 10

>>> bag['_change_count']
3
```

## Error Handling

### Safe Callbacks

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> errors = []

>>> def safe_callback(**kw):
...     try:
...         # Your logic here
...         value = kw['node'].value
...         if value < 0:
...             raise ValueError("Negative not allowed")
...     except Exception as e:
...         errors.append(str(e))
...         # Don't re-raise to allow other subscribers to run

>>> bag.subscribe('safe', any=safe_callback)

>>> bag['x'] = -1
>>> errors
['Negative not allowed']
```

## Multiple Subscribers

### Layered Processing

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> processing_order = []

>>> bag.subscribe('layer1', any=lambda **kw: processing_order.append('validate'))
>>> bag.subscribe('layer2', any=lambda **kw: processing_order.append('transform'))
>>> bag.subscribe('layer3', any=lambda **kw: processing_order.append('notify'))

>>> bag['x'] = 1

>>> processing_order
['validate', 'transform', 'notify']
```
