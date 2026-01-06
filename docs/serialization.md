# Serialization

Bag supports multiple serialization formats for saving and loading data:

- **XML**: Human-readable, widely compatible
- **JSON**: Web-friendly, simple structure
- **TYTX**: Type-preserving format (JSON or MessagePack transport)

## XML Serialization

### To XML

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag['name'] = 'Alice'
>>> bag['age'] = 30

>>> bag.to_xml()
'<name>Alice</name><age>30</age>'
```

### With Pretty Print

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag['config.debug'] = True
>>> bag['config.port'] = 8080

>>> print(bag.to_xml(pretty=True))  # doctest: +SKIP
<config>
  <debug>True</debug>
  <port>8080</port>
</config>
```

### With XML Declaration

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag({'test': 'value'})
>>> bag.to_xml(doc_header=True)  # doctest: +ELLIPSIS
"<?xml version='1.0' encoding='UTF-8'?>..."
```

### Save to File

```python
bag.to_xml('/path/to/file.xml')
```

### From XML

```{doctest}
>>> from genro_bag import Bag

>>> xml = '<root><name>Test</name><count>42</count></root>'
>>> bag = Bag.from_xml(xml)
>>> bag['root.name']
'Test'
>>> bag['root.count']
'42'
```

Note: XML doesn't preserve types - numbers become strings.

### With Attributes

XML attributes are preserved:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag.set_item('user', 'Alice', role='admin', active='true')

>>> bag.to_xml()
'<user role="admin" active="true">Alice</user>'
```

## JSON Serialization

JSON serialization preserves the Bag structure with labels, values and attributes.

### To JSON

```python
>>> from genro_bag import Bag

>>> bag = Bag({'name': 'Alice', 'age': 30})
>>> bag.to_json()  # Returns JSON with label/value/attr structure
'[{"label":"name","value":"Alice","attr":{}},{"label":"age","value":30,"attr":{}}]'
```

### From JSON

```{doctest}
>>> from genro_bag import Bag

>>> json_str = '{"name": "Test", "value": 42}'
>>> bag = Bag.from_json(json_str)
>>> bag['name']
'Test'
>>> bag['value']
42
```

### Limitations

Standard JSON doesn't support:
- Node attributes (they're lost)
- Complex types (datetime, Decimal, bytes)

For type preservation, use TYTX.

## TYTX Serialization

TYTX (Typed Text eXchange) preserves Python types exactly.

### To TYTX

```{doctest}
>>> from genro_bag import Bag
>>> from datetime import datetime, date
>>> from decimal import Decimal

>>> bag = Bag()
>>> bag['count'] = 42
>>> bag['price'] = Decimal('19.99')
>>> bag['active'] = True

>>> tytx = bag.to_tytx()
>>> # Types are encoded with prefixes like 'i:42', 'd:19.99', 'b:true'
```

### From TYTX

```{doctest}
>>> from genro_bag import Bag
>>> from decimal import Decimal

>>> bag = Bag()
>>> bag['price'] = Decimal('19.99')
>>> tytx = bag.to_tytx()

>>> restored = Bag.from_tytx(tytx)
>>> restored['price']
Decimal('19.99')
>>> type(restored['price'])
<class 'decimal.Decimal'>
```

### Transport Formats

TYTX supports two transports:

**JSON** (default, human-readable):
```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag({'x': 1})
>>> bag.to_tytx(transport='json')  # doctest: +ELLIPSIS
'...'
```

**MessagePack** (compact binary):
```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag({'x': 1})
>>> data = bag.to_tytx(transport='msgpack')
>>> type(data)
<class 'bytes'>
```

### With Attributes

TYTX preserves node attributes:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag.set_item('user', 'Alice', role='admin')

>>> restored = Bag.from_tytx(bag.to_tytx())
>>> restored['user?role']
'admin'
```

### Save to File

```python
# JSON format
bag.to_tytx('/path/to/data.bag.json')

# MessagePack format
bag.to_tytx('/path/to/data.bag.mp', transport='msgpack')
```

### Load from File

```python
# Auto-detected from extension
bag = Bag()
bag.fill_from('/path/to/data.bag.json')
bag.fill_from('/path/to/data.bag.mp')
```

## Supported Types

### XML
- Strings (all values converted to string)
- Nested structure via tags
- Attributes preserved

### JSON
- Strings, numbers, booleans, null
- Nested dicts/lists
- No attributes, no complex types

### TYTX
Full type preservation:
- `int`, `float`, `Decimal`
- `bool`, `None`
- `str`, `bytes`
- `datetime`, `date`, `time`
- `list`, `tuple`
- Nested Bag with attributes

## Round-Trip Safety

### XML (lossy)

```{doctest}
>>> from genro_bag import Bag

>>> original = Bag({'count': 42, 'active': True})
>>> xml = original.to_xml()
>>> restored = Bag.from_xml(f'<root>{xml}</root>')

>>> # Types are lost - everything becomes string
>>> restored['root.count']
'42'
>>> type(restored['root.count'])
<class 'str'>
```

### TYTX (lossless)

```{doctest}
>>> from genro_bag import Bag
>>> from decimal import Decimal

>>> original = Bag()
>>> original['count'] = 42
>>> original['price'] = Decimal('19.99')
>>> original.set_item('user', 'Alice', role='admin')

>>> restored = Bag.from_tytx(original.to_tytx())

>>> restored['count']
42
>>> type(restored['count'])
<class 'int'>
>>> restored['price']
Decimal('19.99')
>>> restored['user?role']
'admin'
```

## Format Comparison

| Feature | XML | JSON | TYTX |
|---------|-----|------|------|
| Human readable | Yes | Yes | JSON: Yes, MP: No |
| Type preservation | No | Partial | Full |
| Attributes | Yes | No | Yes |
| Binary data | No | No | Yes |
| File size | Large | Medium | Small (MP) |

## Best Practices

1. **For configuration files**: Use XML or JSON for readability
2. **For data exchange**: Use TYTX JSON for type safety
3. **For storage/cache**: Use TYTX MessagePack for efficiency
4. **For web APIs**: Use JSON for compatibility

## Next Steps

- Learn about [Resolvers](resolvers.md) for lazy loading
- Understand [Subscriptions](subscriptions.md) for reactivity
- Explore [Builders](builders/index.md) for domain-specific structures
