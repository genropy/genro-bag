# UrlResolver Demo - httpbin

Example using UrlResolver with httpbin.org test API.

```python
>>> from genro_bag import Bag
>>> from genro_bag.resolvers import UrlResolver
>>>
>>> api = Bag()
>>> api['json'] = UrlResolver('https://httpbin.org/json', as_bag=True)
>>> api['ip'] = UrlResolver('https://httpbin.org/ip', as_bag=True)
>>> api['headers'] = UrlResolver('https://httpbin.org/headers', as_bag=True)
>>>
>>> list(api.keys())
['json', 'ip', 'headers']
>>>
>>> api['json.slideshow.title']
'Sample Slide Show'
>>>
>>> api['json.slideshow.author']
'Yours Truly'
>>>
>>> api['ip.origin']
'203.0.113.42'
>>>
>>> print(api.to_string(static=False))
├── json
│   └── slideshow
│       ├── author: 'Yours Truly'
│       ├── date: 'date of publication'
│       ├── title: 'Sample Slide Show'
│       └── slides
│           ├── 0
│           │   ├── title: 'Wake up to WonderWidgets!'
│           │   └── type: 'all'
│           └── 1
│               ├── title: 'Overview'
│               ├── type: 'all'
│               └── items
│                   ├── 0: 'Why WonderWidgets are great'
│                   ├── 1: 'Who buys WonderWidgets'
│                   └── 2: ...
├── ip
│   └── origin: '203.0.113.42'
└── headers
    └── headers
        ├── Accept: '*/*'
        ├── Host: 'httpbin.org'
        └── User-Agent: 'python-httpx/0.27.0'
```
