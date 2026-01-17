# Resolver Examples

Practical examples of resolver usage patterns.

## Configuration with Fallbacks

Load config from environment, then file, then defaults:

```python
from genro_bag import Bag
from genro_bag.resolvers import BagCbResolver
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
    return Bag({
        'debug': False,
        'port': 8080,
        'host': 'localhost'
    })

app = Bag()
app['config'] = BagCbResolver(load_config, cache_time=-1)

# Access config
debug = app['config']['debug']
```

## API Client with Caching

```python
from genro_bag import Bag
from genro_bag.resolvers import UrlResolver

class ApiClient:
    def __init__(self, base_url, api_key):
        self.bag = Bag()
        self.base_url = base_url
        self.api_key = api_key

    def _resolver(self, endpoint, cache_time=300):
        return UrlResolver(
            f'{self.base_url}{endpoint}',
            headers={'Authorization': f'Bearer {self.api_key}'},
            as_bag=True,
            cache_time=cache_time
        )

    def setup(self):
        # Frequently accessed, long cache
        self.bag['users'] = self._resolver('/users', cache_time=600)

        # Frequently changing, short cache
        self.bag['stats'] = self._resolver('/stats', cache_time=30)

        # Static reference data, infinite cache
        self.bag['countries'] = self._resolver('/countries', cache_time=-1)

# Usage
api = ApiClient('https://api.example.com', 'my-key')
api.setup()

users = api.bag['users']
stats = api.bag['stats']
```

## Lazy Configuration Tree

```python
from genro_bag import Bag
from genro_bag.resolvers import DirectoryResolver

def create_config_tree(base_path):
    """Create a lazy-loading config tree from directory structure."""
    config = Bag()

    # Each environment loads on demand
    config['production'] = DirectoryResolver(f'{base_path}/production/')
    config['staging'] = DirectoryResolver(f'{base_path}/staging/')
    config['development'] = DirectoryResolver(f'{base_path}/development/')

    return config

# Directory structure:
# /config/
#   production/
#     database.xml
#     cache.xml
#   staging/
#     database.xml
#   development/
#     database.xml

config = create_config_tree('/config')

# Only loads production/database.xml when accessed
db_config = config['production']['database']
```

## Dynamic Form with Validation Rules

```python
from genro_bag import Bag
from genro_bag.resolvers import BagCbResolver

def load_validation_rules():
    """Load validation rules from database."""
    rules = Bag()
    rules.set_item('email', r'^[\w.-]+@[\w.-]+\.\w+$', required=True)
    rules.set_item('phone', r'^\+?[\d\s-]+$', required=False)
    rules.set_item('age', r'^\d+$', min=0, max=150)
    return rules

form = Bag()
form['data'] = Bag()  # User input
form['rules'] = BagCbResolver(load_validation_rules, cache_time=-1)

def validate(form):
    errors = []
    rules = form['rules']

    for node in rules:
        field = node.label
        pattern = node.value
        required = node.get_attr('required', False)

        value = form['data'][field]

        if required and not value:
            errors.append(f'{field}: required')
        elif value and not re.match(pattern, str(value)):
            errors.append(f'{field}: invalid format')

    return errors
```

## Computed Properties

```python
from genro_bag import Bag
from genro_bag.resolvers import BagCbResolver

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

    def compute_tax():
        return order['subtotal'] * 0.1

    # Computed fields
    order['subtotal'] = BagCbResolver(compute_total, cache_time=0)
    order['tax'] = BagCbResolver(compute_tax, cache_time=0)

    return order

order = create_order()
order['items'].set_item('widget', 'Widget', price=10, qty=2)
order['items'].set_item('gadget', 'Gadget', price=25, qty=1)

print(order['subtotal'])  # 45
print(order['tax'])       # 4.5
```

## Multi-Source Data Aggregation

```python
from genro_bag import Bag
from genro_bag.resolvers import UrlResolver, BagCbResolver

def create_dashboard():
    dashboard = Bag()

    # Data from different sources
    dashboard['sales'] = UrlResolver(
        'https://sales-api.internal/summary',
        as_bag=True,
        cache_time=60
    )

    dashboard['inventory'] = UrlResolver(
        'https://inventory-api.internal/levels',
        as_bag=True,
        cache_time=120
    )

    dashboard['alerts'] = UrlResolver(
        'https://monitoring-api.internal/alerts',
        as_bag=True,
        cache_time=30
    )

    # Computed summary
    def compute_summary():
        return Bag({
            'total_sales': dashboard['sales']['total'],
            'low_stock_count': len([
                n for n in dashboard['inventory']
                if n.value < 10
            ]),
            'critical_alerts': len([
                n for n in dashboard['alerts']
                if n.get_attr('severity') == 'critical'
            ])
        })

    dashboard['summary'] = BagCbResolver(compute_summary, cache_time=30)

    return dashboard

dash = create_dashboard()
summary = dash['summary']
```

## Async Batch Loading

```python
from genro_bag import Bag
from genro_bag.resolvers import BagCbResolver
import asyncio

async def fetch_all_users(user_ids):
    """Batch fetch users from API."""
    async with aiohttp.ClientSession() as session:
        tasks = [
            session.get(f'https://api.example.com/users/{uid}')
            for uid in user_ids
        ]
        responses = await asyncio.gather(*tasks)

        bag = Bag()
        for uid, resp in zip(user_ids, responses):
            data = await resp.json()
            bag[uid] = Bag(data)
        return bag

# Setup
users = Bag()
user_ids = ['u001', 'u002', 'u003']
users['all'] = BagCbResolver(
    lambda: fetch_all_users(user_ids),
    cache_time=300
)

# In async context
from genro_toolbox import smartawait
all_users = await smartawait(users.get_item('all', static=False))
```

## Pattern: Resolver Chain

```python
from genro_bag import Bag
from genro_bag.resolvers import BagCbResolver

def create_config_chain(sources):
    """Create config that chains through multiple sources."""

    def load_merged():
        result = Bag()
        for source in sources:
            source_bag = source()  # Each source is a callable
            for node in source_bag:
                if node.label not in result:
                    result[node.label] = node.value
        return result

    return BagCbResolver(load_merged, cache_time=-1)

# Usage
config = Bag()
config['settings'] = create_config_chain([
    lambda: Bag.from_json(os.getenv('CONFIG', '{}')),  # Env first
    lambda: Bag.from_xml(open('config.xml').read()),   # Then file
    lambda: Bag({'debug': False, 'port': 8080})        # Then defaults
])
```
