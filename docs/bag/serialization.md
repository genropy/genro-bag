# Serialization

Bag supports multiple formats for saving and loading data:

| Format | Best For |
|--------|----------|
| **XML** | Human-readable configs, interop |
| **JSON** | Web APIs, simple data |
| **TYTX** | Full type preservation |

## XML

### Writing

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag['name'] = 'Alice'
>>> bag['age'] = 30

>>> bag.to_xml()
'<name>Alice</name><age>30</age>'
```

With formatting:

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

With XML declaration:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag({'test': 'value'})
>>> bag.to_xml(doc_header=True)  # doctest: +ELLIPSIS
"<?xml version='1.0' encoding='UTF-8'?>..."
```

### Reading

```{doctest}
>>> from genro_bag import Bag

>>> xml = '<root><name>Test</name><count>42</count></root>'
>>> bag = Bag.from_xml(xml)
>>> bag['root.name']
'Test'
```

### Attributes in XML

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag()
>>> bag.set_item('user', 'Alice', role='admin', active='true')

>>> bag.to_xml()
'<user role="admin" active="true">Alice</user>'
```

### Limitations

XML doesn't preserve Python types — everything becomes a string:

```{doctest}
>>> from genro_bag import Bag

>>> bag = Bag({'count': 42, 'active': True})
>>> restored = Bag.from_xml(f'<root>{bag.to_xml()}</root>')
>>> restored['root.count']
'42'
>>> type(restored['root.count'])
<class 'str'>
```

## JSON

### Writing

```python
>>> from genro_bag import Bag

>>> bag = Bag({'name': 'Alice', 'age': 30})
>>> bag.to_json()
'[{"label":"name","value":"Alice","attr":{}},{"label":"age","value":30,"attr":{}}]'
```

### Reading

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

`to_json` writes node attributes, resolvers and tags — a Bag round-trips
through it. With the default `typed=True` the complex types (datetime,
Decimal) go through TYTX encoding and survive; `typed=False` produces
plain JSON and raises on a value it cannot represent.

Reading arbitrary JSON from elsewhere is a different matter: without the
`label`/`value`/`attr` shape there are no attributes to restore.

## TYTX (Typed Exchange)

TYTX preserves Python types exactly. Two transports available:

- **JSON** (default): Human-readable
- **MessagePack**: Compact binary

### Writing

```{doctest}
>>> from genro_bag import Bag
>>> from decimal import Decimal

>>> bag = Bag()
>>> bag['count'] = 42
>>> bag['price'] = Decimal('19.99')
>>> bag['active'] = True

>>> tytx = bag.to_tytx()  # JSON transport
>>> mp = bag.to_tytx(transport='msgpack')  # Binary
>>> type(mp)
<class 'bytes'>
```

### Reading

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

### Full Type Preservation

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

### Supported Types

| Type | Example |
|------|---------|
| `int` | `42` |
| `float` | `3.14` |
| `Decimal` | `Decimal('19.99')` |
| `bool` | `True` |
| `None` | `None` |
| `str` | `'hello'` |
| `bytes` | `b'\x00\x01'` |
| `datetime` | `datetime(2025, 1, 1)` |
| `date` | `date(2025, 1, 1)` |
| `time` | `time(12, 30)` |
| `list/tuple` | `[1, 2, 3]` |

### Bags nested in plain values

`Bag` is registered with genro-tytx as a custom type under the suffix `X`,
so a Bag sitting **inside** a plain dict or list value survives `to_tytx` /
`from_tytx` round-trips like any other supported type.

Two boundaries apply on that path, because the type registry matches the
exact class and its hooks take no arguments:

- **Subclasses need registration.** A subclass inside a plain value must
  declare its own `__tytx_suffix__` and use `genro_tytx.register_class`.
  Unregistered subclasses inside plain values raise `TypeError` at encode.
- **Signing does not reach it.** The registry hooks cannot carry
  `sign_key`, so a resolver inside such a nested Bag could be neither
  signed nor verified. Both sides refuse instead, on every slot the
  registry serves — node values and attribute values, on `to_tytx` and
  `to_json` alike: the writers raise `BagSerializationError`, the readers
  (`from_tytx`, `from_json`) raise `SignatureError`. Keep resolvers on
  Bag-valued nodes, where signing works, or serialize without a key.

## Resolvers

A `BagResolver` survives every format, whether it is the node's value or
sits in an attribute. It travels as a `::RSLV:` marked string carrying its
class and parameters — an XML `_resolver` attribute, a JSON `resolver`
key, the TYTX value slot:

```python
bag['api'] = UrlResolver('https://api.example.com/data')
bag.set_item('doc', 'text', author=EnvResolver('USER'))

restored = Bag.from_json(bag.to_json())
restored.get_resolver('api')   # rebuilt, an equivalent instance
restored['doc?author']         # resolves as before
```

Nothing is ever called during serialization or parsing: the resolver is
written from its definition and rebuilt inert, and the effect happens when
your code reads the value. A resolver whose parameters do not fit JSON —
a callback, most often — raises `BagSerializationError` naming the node
and the attribute.

### Signing

When the Bag leaves the process and may come back — handed to a browser,
carried in a URL, put on a queue — sign it. A resolver's arguments say
what it will act on, so an unsigned payload lets whoever holds it rewrite
a path or a URL before returning it:

```python
payload = bag.to_json(sign_key=SECRET, expires_in=300)   # on the way out
bag = Bag.from_json(payload, sign_key=SECRET)            # on the way in
```

The key never leaves the server. Reading with `sign_key` demands a valid
signature, so a substituted or unsigned payload raises `SignatureError`,
and an expired one `SignatureExpired`. All three writers take `sign_key`
and `expires_in`, all three readers take `sign_key`.

### Signing hides nothing

A signature proves a payload was not altered. It does not conceal it: the
encoding is base64, not encryption, and whoever holds the payload reads
every parameter — a path, a URL, an API key.

So keep secrets out of the parameters in the first place. Where a resolver
needs a credential at request time, compute it in a hook rather than store
it: `UrlResolver.prepare_headers()` runs when the request is made and is
never serialized.

```python
class ApiResolver(UrlResolver):
    def prepare_headers(self):
        return {'Authorization': f'Bearer {os.environ["API_TOKEN"]}'}

bag['api'] = ApiResolver('https://api.example.com/data')
bag.to_json()   # no token in the payload
```

Written the obvious way instead — `UrlResolver(url, headers={'Authorization': ...})`
— the token is a plain parameter, and it travels.

## File Operations

### Save to File

```python
# XML
bag.to_xml('/path/to/file.xml')

# TYTX JSON
bag.to_tytx('/path/to/data.bag.json')

# TYTX MessagePack
bag.to_tytx('/path/to/data.bag.mp', transport='msgpack')
```

### Load from File

```python
# Auto-detected from extension
bag = Bag()
bag.replace(Bag('/path/to/data.bag.json'))
bag.replace(Bag('/path/to/data.bag.mp'))
```

## Format Comparison

| Feature | XML | JSON | TYTX |
|---------|-----|------|------|
| Human readable | ✓ | ✓ | JSON: ✓ |
| Type preservation | ✗ | Partial | ✓ |
| Attributes | ✓ | ✓ | ✓ |
| Attribute types | ✗ | Partial | ✓ |
| Resolvers | ✓ | ✓ | ✓ |
| Binary data | ✗ | ✗ | ✓ |
| File size | Large | Medium | Small (MP) |

## Best Practices

| Use Case | Format |
|----------|--------|
| Configuration files | XML or JSON |
| Data exchange with types | TYTX JSON |
| Storage/cache | TYTX MessagePack |
| Web APIs | JSON |

### Mixed branch types and legacy subclasses

Each registered Bag branch travels with its own suffix, including empty
branches. A registered subclass with its own suffix can contain ordinary
`Bag` data branches (`X`) and other registered subclasses without changing
their types during JSON or MessagePack round-trips, with compact paths on
or off. The same rule applies inside a typed dict/list envelope.

Subclasses that still inherit `X` keep the historical behavior:
`LegacyBag.from_tytx(...)` reconstructs `X` branches as `LegacyBag`.
To distinguish ordinary data Bags from specialized branches, declare a
unique suffix and register the specialized class. Existing serialized `X`
branches contain no information identifying a specialized class; serialize
again from the original typed tree when migrating.

Unknown parent references and missing or undecodable parent branches raise
`BagSerializationError`; descendants are never moved to the root. Parent
rows must precede their children. MessagePack text such as `::RAW` and `::D`
remains text. Only exact empty markers for registered Bag types are treated
as structural branch markers by the Bag decoder.
