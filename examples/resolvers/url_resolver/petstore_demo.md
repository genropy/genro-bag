# UrlResolver Demo

Example using UrlResolver with the Swagger Petstore API.

```python
>>> from genro_bag import Bag
>>> from genro_bag.resolvers import UrlResolver
>>>
>>> petstore = Bag()
>>> petstore['pets'] = UrlResolver(
...     'https://petstore.swagger.io/v2/pet/findByStatus',
...     qs={'status': 'available'},
...     as_bag=True
... )
>>> petstore['store'] = UrlResolver(
...     'https://petstore.swagger.io/v2/store/inventory',
...     as_bag=True
... )
>>>
>>> list(petstore.keys())
['pets', 'store']
>>>
>>> petstore['pets.0.name']
'doggie'
>>>
>>> petstore['pets.0.status']
'available'
>>>
>>> petstore['pets.0.category.name']
'Dogs'
>>>
>>> petstore['store.available']
234
>>>
>>> print(petstore.to_string(static=False))
├── pets
│   ├── 0
│   │   ├── id: 9223372036854775807
│   │   ├── name: 'doggie'
│   │   ├── status: 'available'
│   │   ├── category
│   │   │   ├── id: 0
│   │   │   └── name: 'Dogs'
│   │   ├── photoUrls
│   │   │   └── 0: 'string'
│   │   └── tags
│   │       └── 0
│   │           ├── id: 0
│   │           └── name: 'string'
│   ├── 1
│   │   └── ...
│   └── ...
└── store
    ├── available: 234
    ├── pending: 12
    └── sold: 45
```
