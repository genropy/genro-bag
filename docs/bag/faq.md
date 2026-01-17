# Core Bag FAQ

Frequently asked questions about core Bag functionality.

## Basic Usage

### How do I check if a key exists?

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag({'a': 1, 'b': 2})
>>> 'a' in bag
True
>>> 'z' in bag
False
```

### What happens when I access a missing key?

Returns `None` (doesn't raise KeyError):

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag({'a': 1})
>>> bag['missing']  # Returns None
>>> bag['missing'] is None
True
```

### How do I get a default value for missing keys?

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag({'a': 1})
>>> value = bag['missing']
>>> result = value if value is not None else 'default'
>>> result
'default'
```

Or use `get_item()` with `default`:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag({'a': 1})
>>> bag.get_item('missing', default='fallback')
'fallback'
```

### How do I iterate over a Bag?

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag({'a': 1, 'b': 2})

>>> # Yields BagNode objects
>>> for node in bag:
...     print(node.label, node.value)
a 1
b 2

>>> # Dict-like methods
>>> list(bag.keys())
['a', 'b']
>>> list(bag.values())
[1, 2]
>>> list(bag.items())
[('a', 1), ('b', 2)]
```

## Paths

### Can I use slashes instead of dots?

No, only dots are supported as path separators:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag['a.b.c'] = 1  # Correct
>>> bag['a.b.c']
1
```

### What characters are allowed in labels?

Labels should be valid Python identifiers or strings. Avoid dots in labels:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag['my_label'] = 1       # OK
>>> bag['label123'] = 2       # OK
>>> bag['my-label'] = 3       # OK (but underscore preferred)
```

### How do I handle labels with dots?

If you need a literal dot in a label, use `set_item()` with a list path:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> # This creates nested structure a -> b
>>> bag['a.b'] = 1

>>> # To get a literal 'a.b' label, you'd need to avoid the path syntax
>>> bag.set_item('version_1.0', 'value')  # Label is 'version_1'
```

## Attributes

### What's the difference between value and attributes?

- **Value**: The main data (`bag['key']`)
- **Attributes**: Metadata about the node (`bag['key?attr']`)

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag.set_item('price', 99.99, currency='USD', taxable=True)

>>> bag['price']  # The value
99.99
>>> bag['price?currency']  # Metadata
'USD'
```

### Can I have attributes without a value?

Yes, use `None` as the value:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag.set_item('config', None, env='production', version='1.0')

>>> bag['config']  # No value
>>> bag['config?env']
'production'
```

### How do I get all attributes of a node?

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag.set_item('item', 'value', a=1, b=2, c=3)

>>> node = bag.get_node('item')
>>> node.attr
{'a': 1, 'b': 2, 'c': 3}
```

## Serialization

### Why do numbers become strings in XML?

XML has no native type system. Everything is text:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag({'count': 42})
>>> xml = bag.to_xml()
>>> restored = Bag.from_xml(f'<r>{xml}</r>')
>>> restored['r.count']
'42'
>>> type(restored['r.count'])
<class 'str'>
```

Use TYTX for type preservation.

### Which format should I use?

| Need | Format |
|------|--------|
| Human-readable config | XML |
| Web API exchange | JSON |
| Full Python types | TYTX JSON |
| Compact storage | TYTX MessagePack |

### How do I preserve types in round-trip?

Use TYTX:

```{doctest}
>>> from genro_bag import Bag
>>> from decimal import Decimal

>>> bag = Bag()
>>> bag['price'] = Decimal('19.99')
>>> bag['count'] = 42

>>> restored = Bag.from_tytx(bag.to_tytx())
>>> type(restored['price'])
<class 'decimal.Decimal'>
>>> type(restored['count'])
<class 'int'>
```

## Performance

### Is Bag faster than dict?

No. Bag adds overhead for features like paths, attributes, and subscriptions. For simple key-value storage, use dict.

Bag is designed for:
- Hierarchical data
- Rich metadata
- Serialization needs
- Change tracking

### How large can a Bag be?

Bag can handle thousands of nodes. For very large datasets (millions of items), consider:
- Lazy loading with resolvers
- Database backends
- Streaming serialization

### How do I copy a Bag efficiently?

```{doctest}
>>> from genro_bag import Bag

>>> original = Bag({'a': 1, 'b': 2})

>>> # Deep copy via TYTX
>>> copy = Bag.from_tytx(original.to_tytx())
>>> copy['c'] = 3

>>> 'c' in original
False
>>> 'c' in copy
True
```

## Common Mistakes

### Forgetting that nested assignment creates structure

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag['a.b.c'] = 1

>>> # 'a' and 'a.b' are now Bags, not values
>>> isinstance(bag['a'], Bag)
True
```

### Using `=` instead of `set_item()` when you need attributes

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()

>>> # This only sets value, no attributes
>>> bag['item'] = 'value'

>>> # This sets value AND attributes
>>> bag.set_item('item2', 'value', attr1='x', attr2='y')
>>> bag['item2?attr1']
'x'
```

### Expecting KeyError on missing keys

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag({'a': 1})

>>> # Returns None, doesn't raise
>>> bag['missing']
>>> bag['missing'] is None
True
```
