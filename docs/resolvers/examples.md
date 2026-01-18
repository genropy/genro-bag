# Resolver Examples

Practical examples of resolver usage patterns.

Source code: [`examples/resolvers/`](../../examples/resolvers/)

---

## Resolver Parameters

Shows how parameters flow through the resolver system with three priority levels.

Source: [`examples/resolvers/resolver_parameters/`](../../examples/resolvers/resolver_parameters/)

### Parameter Priority

When a resolver is called, parameters come from three sources (highest priority first):

1. **call_kwargs**: Passed to `get_item()` or `get_value()` at call time
2. **node.attr**: Attributes set on the parent BagNode
3. **resolver._kw**: Default parameters set at resolver construction

### Basic Example with BagCbResolver

```python
>>> from genro_bag import Bag
>>> from genro_bag.resolver import BagCbResolver
>>>
>>> def multiply(base, multiplier):
...     return base * multiplier
>>>
>>> bag = Bag()
>>> bag['calc'] = BagCbResolver(multiply, base=10, multiplier=2)
>>>
>>> # Level 3: Uses resolver defaults (base=10, multiplier=2)
>>> bag['calc']
20
>>>
>>> # Level 2: Override via node attributes
>>> bag.set_attr('calc', multiplier=5)
>>> bag['calc']
50
>>>
>>> # Level 1: Override via call_kwargs (highest priority)
>>> bag.get_item('calc', multiplier=10)
100
>>>
>>> # Node attr is still there, used when no call_kwargs
>>> bag['calc']
50
```

### Cache Invalidation

Cache is automatically invalidated when effective parameters change:

```python
>>> bag = Bag()
>>> bag['data'] = BagCbResolver(counter, x=5, cache_time=-1)  # infinite cache
>>>
>>> bag['data']  # First call -> computed
10
>>> bag['data']  # From cache (same params)
10
>>> bag.set_attr('data', x=7)  # Change param -> invalidates cache
>>> bag['data']  # Recomputed
14
```

### Parameter Flow Diagram

```text
bag.get_item('path', **call_kwargs)
    |
    v
node.get_value(**call_kwargs)
    |
    v
resolver(static=False, **call_kwargs)
    |
    v
+------------------------------------------+
| effective_kw = {}                         |
| effective_kw.update(resolver._kw)     # 3 |
| effective_kw.update(node.attr)        # 2 |
| effective_kw.update(call_kwargs)      # 1 |
+------------------------------------------+
    |
    v
resolver.load()  # uses self._kw = effective_kw
    |
    v
result (cached if cache_time != 0)
```

---

## UrlResolver Examples

Source: [`examples/resolvers/url_resolver/`](../../examples/resolvers/url_resolver/)

### httpbin Test API

```python
>>> from genro_bag import Bag
>>> from genro_bag.resolvers import UrlResolver
>>>
>>> api = Bag()
>>> api['json'] = UrlResolver('https://httpbin.org/json', as_bag=True)
>>> api['ip'] = UrlResolver('https://httpbin.org/ip', as_bag=True)
>>> api['headers'] = UrlResolver('https://httpbin.org/headers', as_bag=True)
>>>
>>> api['json.slideshow.title']
'Sample Slide Show'
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
│           └── ...
├── ip
│   └── origin: '203.0.113.42'
└── headers
    └── headers
        ├── Accept: '*/*'
        ├── Host: 'httpbin.org'
        └── User-Agent: 'python-httpx/0.27.0'
```

### ECB Exchange Rates (XML)

Fetching XML data from the European Central Bank:

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
>>> print(rates.to_string())
└── Envelope
    ├── subject: 'Reference rates'
    ├── Sender
    │   └── name: 'European Central Bank'
    └── Cube
        └── Cube
            └── ...
```

### Petstore API

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
>>> petstore['pets.0.name']
'doggie'
>>>
>>> petstore['store.available']
234
```

---

## OpenApiResolver

Loads an OpenAPI spec and organizes endpoints by tags with ready-to-use UrlResolvers.

Source: [`examples/resolvers/openapi_resolver/`](../../examples/resolvers/openapi_resolver/)

```python
>>> from genro_bag import Bag
>>> from genro_bag.resolvers import OpenApiResolver
>>>
>>> bag = Bag()
>>> bag['petstore'] = OpenApiResolver('https://petstore3.swagger.io/api/v3/openapi.json')
>>>
>>> api = bag['petstore']
>>> list(api.keys())
['info', 'externalDocs', 'servers', 'api', 'components']
>>>
>>> api['info']
'This is a sample Pet Store Server based on the OpenAPI 3.0 specification.'
>>>
>>> list(api['api'].keys())
['pet', 'store', 'user']
>>>
>>> list(api['api.pet'].keys())
['updatePet', 'addPet', 'findPetsByStatus', 'findPetsByTags', 'getPetById', ...]
>>>
>>> op = api['api.pet.findPetsByStatus']
>>> op['summary']
'Finds Pets by status'
>>>
>>> op['method']
'get'
>>>
>>> # Set query parameters and invoke
>>> op['qs.status'] = 'available'
>>> result = op['value']  # triggers the API call
>>> result['0.name']
'doggie'
>>>
>>> print(api.to_string())
├── info: 'This is a sample Pet Store Server...'
├── externalDocs
│   ├── description: 'Find out more about Swagger'
│   └── url: 'https://swagger.io'
├── servers
│   └── 0
│       └── url: '/api/v3'
├── api
│   ├── pet [name='pet', description='Everything about your Pets']
│   │   ├── updatePet
│   │   │   ├── summary: 'Update an existing pet'
│   │   │   ├── method: 'put'
│   │   │   └── ...
│   │   ├── findPetsByStatus
│   │   │   ├── summary: 'Finds Pets by status'
│   │   │   ├── method: 'get'
│   │   │   ├── qs
│   │   │   │   └── status: None
│   │   │   └── value: <UrlResolver>
│   │   └── ...
│   ├── store [name='store', description='Access to Petstore orders']
│   └── user [name='user', description='Operations about user']
└── components
    ├── schemas
    └── securitySchemes
```

---

## DirectoryResolver

Maps filesystem directories to Bag with lazy loading.

Source: [`examples/resolvers/directory_resolver/`](../../examples/resolvers/directory_resolver/)

### Basic Directory Scanning

```python
from genro_bag import Bag
from genro_bag.resolvers import DirectoryResolver

# Create resolver
resolver = DirectoryResolver('/path/to/directory')
bag = Bag()
bag['files'] = resolver

# Access triggers scan
files = bag['files']

for path, node in files.walk():
    indent = "  " * path.count(".")
    is_dir = node.is_branch
    print(f"{indent}{node.label}{'/' if is_dir else ''}")
```

### Filtered Directory Scanning

```python
# Include only .xml and .json files
resolver = DirectoryResolver(
    '/path/to/directory',
    include="*.xml,*.json",
    ext="xml,json",
)
bag = Bag()
bag['config_files'] = resolver

files = bag['config_files']
for path, node in files.walk():
    print(node.label)
```

---

## Custom Resolvers

### SystemResolver

Collects system information from multiple sources (platform, psutil, etc.).

Source: [`examples/resolvers/system_resolver/`](../../examples/resolvers/system_resolver/)

```python
>>> from genro_bag import Bag
>>> from genro_bag.resolvers import DirectoryResolver
>>> from system_resolver import SystemResolver
>>>
>>> computer = Bag()
>>> computer['sys'] = SystemResolver()
>>> computer['home'] = DirectoryResolver('~')
>>>
>>> list(computer['sys'].keys())
['platform', 'python', 'user', 'cpu', 'disk', 'network', 'memory']
>>>
>>> computer['sys.platform.system']
'Darwin'
>>>
>>> computer['sys.cpu.count']
10
>>>
>>> computer['sys.disk.free_gb']
182.45
>>>
>>> computer['sys.memory.percent']
49.4
>>>
>>> print(computer.to_string(static=False))
├── sys
│   ├── platform
│   │   ├── system: 'Darwin'
│   │   ├── release: '25.1.0'
│   │   ├── machine: 'arm64'
│   │   └── ...
│   ├── python
│   │   ├── version: '3.12.8'
│   │   └── ...
│   ├── cpu
│   │   ├── count: 10
│   │   ├── percent: 12.5
│   │   └── freq_mhz: 3228
│   ├── disk
│   │   ├── total_gb: 460.43
│   │   ├── free_gb: 182.45
│   │   └── percent: 60.4
│   ├── memory
│   │   ├── total_gb: 36.0
│   │   ├── available_gb: 18.23
│   │   └── percent: 49.4
│   └── ...
└── home
    ├── Desktop
    ├── Documents
    └── ...
```

### OpenMeteoResolver

Fetches weather data from Open-Meteo API.

Source: [`examples/resolvers/openmeteo_resolver/`](../../examples/resolvers/openmeteo_resolver/)

```python
>>> from genro_bag import Bag
>>> from open_meteo_resolver import OpenMeteoResolver
>>>
>>> meteo = Bag()
>>> cities = ["london", "paris", "rome", "berlin", "madrid"]
>>> for city in cities:
...     meteo.set_item(city, OpenMeteoResolver(), city=city)
>>>
>>> print(meteo.to_string(static=False))
├── london [city='london']
│   ├── temperature_2m: 7.4
│   ├── wind_speed_10m: 14.9
│   ├── relative_humidity_2m: 80
│   └── weather: 'Overcast'
├── paris [city='paris']
│   ├── temperature_2m: 5.2
│   ├── wind_speed_10m: 11.2
│   ├── relative_humidity_2m: 92
│   └── weather: 'Overcast'
├── rome [city='rome']
│   ├── temperature_2m: 10.1
│   ├── wind_speed_10m: 5.4
│   ├── relative_humidity_2m: 71
│   └── weather: 'Clear sky'
└── ...
```

---

## Common Patterns

### Configuration with Fallbacks

```python
from genro_bag import Bag
from genro_bag.resolver import BagCbResolver
import os

def load_config():
    # Try environment first
    if os.getenv('APP_CONFIG'):
        return Bag.from_json(os.getenv('APP_CONFIG'))

    # Then config file
    config_path = os.getenv('CONFIG_PATH', '/etc/myapp/config.json')
    if os.path.exists(config_path):
        return Bag.from_json(open(config_path).read())

    # Defaults
    return Bag({'debug': False, 'port': 8080})

app = Bag()
app['config'] = BagCbResolver(load_config, cache_time=-1)
```

### Computed Properties

```python
from genro_bag import Bag
from genro_bag.resolver import BagCbResolver

def create_order():
    order = Bag()
    order['items'] = Bag()

    def compute_total():
        total = 0
        for node in order['items']:
            price = node.get_attr('price', 0)
            qty = node.get_attr('qty', 1)
            total += price * qty
        return total

    order['subtotal'] = BagCbResolver(compute_total, cache_time=0)
    return order

order = create_order()
order['items'].set_item('widget', 'Widget', price=10, qty=2)
order['items'].set_item('gadget', 'Gadget', price=25, qty=1)

print(order['subtotal'])  # 45
```

### API Client with Caching

```python
from genro_bag import Bag
from genro_bag.resolvers import UrlResolver

class ApiClient:
    def __init__(self, base_url):
        self.bag = Bag()
        self.base_url = base_url

    def _resolver(self, endpoint, cache_time=300):
        return UrlResolver(
            f'{self.base_url}{endpoint}',
            as_bag=True,
            cache_time=cache_time
        )

    def setup(self):
        self.bag['users'] = self._resolver('/users', cache_time=600)
        self.bag['stats'] = self._resolver('/stats', cache_time=30)
        self.bag['countries'] = self._resolver('/countries', cache_time=-1)

api = ApiClient('https://api.example.com')
api.setup()
users = api.bag['users']
```
