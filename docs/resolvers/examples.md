# Resolver Examples

Practical examples of resolver usage patterns.

Source code: [`examples/resolvers/`](../../examples/resolvers/)

---

## Resolver Parameters

Shows how parameters flow through the resolver system with three priority levels.

Source: [`examples/resolvers/resolver_parameters/`](../../examples/resolvers/resolver_parameters/)

### Parameter Priority

When a resolver is called, parameters come from two sources (highest priority first):

1. **node.attr**: Attributes set on the parent BagNode (mutable)
2. **resolver._kw**: Default parameters set at resolver construction

Passing kwargs at call time (`bag.get_item('path', x=10)`) is syntactic sugar
for `set_attr(x=10)` followed by the read — the call updates node.attr so the
cached value stays coherent with it. "Changing arguments = updating resolver
state" (no transient overrides).

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
>>> # Defaults: base=10, multiplier=2
>>> bag['calc']
20
>>>
>>> # Update via node attributes
>>> bag.set_attr('calc', multiplier=5)
>>> bag['calc']
50
>>>
>>> # Pass kwargs at call time: updates node.attr and loads
>>> bag.get_item('calc', multiplier=10)
100
>>>
>>> # The update persists: node.attr now has multiplier=10
>>> bag['calc']
100
```

### Query String Syntax in Path

Parameters can also be passed directly in the path using query string syntax:

```python
>>> from genro_bag import Bag
>>> from genro_bag.resolver import BagCbResolver
>>>
>>> bag = Bag()
>>> bag['calc'] = BagCbResolver(lambda x: x * 2, x=5)
>>>
>>> # These two are equivalent:
>>> bag.get_item('calc', x=10)
20
>>> bag.get_item('calc?x=10')
20
>>>
>>> # Multiple parameters:
>>> def add(a, b):
...     return a + b
>>>
>>> bag['sum'] = BagCbResolver(add, a=1, b=2)
>>> bag.get_item('sum?a=10&b=20')
30
```

### Cache Invalidation

Cache is automatically invalidated when effective parameters change:

```python
>>> bag = Bag()
>>> bag['data'] = BagCbResolver(counter, x=5, cache_time=False)  # infinite cache
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
    +--- if call_kwargs:
    |       node.set_attr(**call_kwargs)   # write into node.attr
    |
    v
+------------------------------------------+
| effective_kw = {}                         |
| effective_kw.update(resolver._kw)     # 2 |
| effective_kw.update(node.attr)        # 1 |  (node.attr now has the call_kwargs)
+------------------------------------------+
    |
    v
resolver.load()  # reads from self.kw (on_loading applied to merged self._kw)
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
```

### POST with Body

The resolver also supports POST/PUT/PATCH operations with body parameters:

```python
>>> # Get the addPet operation
>>> add_pet = api['api.pet.addPet']
>>> add_pet['summary']
'Add a new pet to the store'
>>>
>>> add_pet['method']
'post'
>>>
>>> # View expected body structure
>>> print(add_pet['body'].to_string())
├── id: None
├── name: None
├── category
│   ├── id: None
│   └── name: None
├── photoUrls: []
├── tags: []
└── status: None
>>>
>>> # Set body values and invoke
>>> add_pet['body.name'] = 'Fluffy'
>>> add_pet['body.status'] = 'available'
>>> add_pet['body.category.name'] = 'Cats'
>>>
>>> # Or pass body via _body parameter at call time
>>> from genro_bag import Bag
>>> new_pet = Bag()
>>> new_pet['name'] = 'Buddy'
>>> new_pet['status'] = 'available'
>>> new_pet['category.name'] = 'Dogs'
>>>
>>> result = api.get_item('api.pet.addPet.value', _body=new_pet)
>>> result['name']
'Buddy'
```

### API Structure

```python
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

#### Single resolver with query string syntax

```python
>>> from genro_bag import Bag
>>> from open_meteo_resolver import OpenMeteoResolver
>>>
>>> bag = Bag()
>>> bag['meteo'] = OpenMeteoResolver()
>>>
>>> # Pass city via query string in path
>>> bag['meteo?city=London']
<Bag with weather data>
>>>
>>> bag['meteo?city=London'].keys()
['temperature_2m', 'wind_speed_10m', 'relative_humidity_2m', 'weather']
>>>
>>> bag['meteo?city=London.temperature_2m']
7.4
>>>
>>> bag['meteo?city=London.weather']
'Overcast'
>>>
>>> # Different city, same resolver
>>> bag['meteo?city=Rome.weather']
'Clear sky'
```

#### Multiple cities via node attributes

```python
>>> from genro_bag import Bag
>>> from open_meteo_resolver import OpenMeteoResolver
>>>
>>> meteo = Bag()
>>> cities = ["london", "paris", "rome", "berlin", "madrid"]
>>> for city in cities:
...     # city=city is passed as node attribute, read by resolver at call time
...     meteo.set_item(city, OpenMeteoResolver(), city=city)
>>>
>>> # Change city dynamically via node attribute
>>> meteo.set_attr('london', city='manchester')
>>> meteo['london']  # Now fetches Manchester weather
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
app['config'] = BagCbResolver(load_config, cache_time=False)
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
        self.bag['countries'] = self._resolver('/countries', cache_time=False)

api = ApiClient('https://api.example.com')
api.setup()
users = api.bag['users']
```

### Async Usage

Resolvers work seamlessly in async contexts. Use `smartawait` to await results:

```python
from genro_bag import Bag
from genro_bag.resolvers import UrlResolver
from genro_toolbox import smartawait

async def fetch_weather():
    bag = Bag()
    bag['weather'] = UrlResolver(
        'https://api.open-meteo.com/v1/forecast',
        qs={'latitude': 51.5, 'longitude': -0.1, 'current_weather': True},
        as_bag=True
    )

    # Await the resolver result
    result = await smartawait(bag['weather'])
    return result['current_weather.temperature']

async def fetch_multiple():
    bag = Bag()
    bag['users'] = UrlResolver('https://api.example.com/users', as_bag=True)
    bag['posts'] = UrlResolver('https://api.example.com/posts', as_bag=True)

    # Fetch both in parallel
    import asyncio
    users, posts = await asyncio.gather(
        smartawait(bag['users']),
        smartawait(bag['posts'])
    )
    return users, posts
```

With query string parameters:

```python
from genro_bag import Bag
from genro_bag.resolver import BagCbResolver
from genro_toolbox import smartawait

async def calculate():
    bag = Bag()
    bag['calc'] = BagCbResolver(lambda x, y: x * y, x=1, y=1)

    # Pass parameters via query string, await result
    result = await smartawait(bag.get_item('calc?x=10&y=5'))
    return result  # 50
```

With OpenMeteoResolver:

```python
from genro_bag import Bag
from open_meteo_resolver import OpenMeteoResolver
from genro_toolbox import smartawait

async def get_weather_async(city: str):
    bag = Bag()
    bag['meteo'] = OpenMeteoResolver()

    # Query string syntax with await
    weather = await smartawait(bag[f'meteo?city={city}'])
    return weather

async def compare_cities():
    bag = Bag()
    bag['meteo'] = OpenMeteoResolver()

    import asyncio
    london, paris = await asyncio.gather(
        smartawait(bag['meteo?city=London']),
        smartawait(bag['meteo?city=Paris'])
    )

    print(f"London: {london['temperature_2m']}°C")
    print(f"Paris: {paris['temperature_2m']}°C")
```
