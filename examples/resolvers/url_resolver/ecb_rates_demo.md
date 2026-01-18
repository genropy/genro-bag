# UrlResolver Demo - ECB Exchange Rates

Example fetching XML data from the European Central Bank.

```python
>>> from genro_bag import Bag
>>> from genro_bag.resolvers import UrlResolver
>>>
>>> ecb = Bag()
>>> ecb['rates'] = UrlResolver(
...     'https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml',
...     as_bag=True
... )
>>>
>>> ecb['rates.Envelope.Cube.Cube']
<Bag with currency rates>
>>>
>>> # Or use Bag.from_url for immediate fetch
>>> rates = Bag.from_url('https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml')
>>> list(rates.keys())
['Envelope']
>>>
>>> print(rates.to_string())
└── Envelope
    ├── subject: 'Reference rates'
    ├── Sender
    │   └── name: 'European Central Bank'
    └── Cube
        └── Cube
            ├── Cube
            │   └── ...
            └── ...
```
