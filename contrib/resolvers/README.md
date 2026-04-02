# genro-bag-contrib-resolvers

Community-contributed resolvers for genro-bag.

## Installation

```bash
pip install genro-bag-contrib-resolvers
```

For system memory/CPU usage monitoring:

```bash
pip install genro-bag-contrib-resolvers[system]
```

## Resolvers

### EarthquakeResolver

Fetches recent earthquakes from the USGS GeoJSON feed. Uses `If-Modified-Since` to skip redownloading when data hasn't changed.

```python
from genro_bag import Bag
from genro_bag_contrib_resolvers import EarthquakeResolver

bag = Bag()
bag['quakes'] = EarthquakeResolver(cache_time=-60)
```

### OpenMeteoResolver

Weather data from Open-Meteo API. Geocodes city name to coordinates automatically.

```python
from genro_bag import Bag
from genro_bag_contrib_resolvers import OpenMeteoResolver

bag = Bag()
bag['weather'] = OpenMeteoResolver(city='Rome')
print(bag['weather.temperature_2m'])  # 18.5
print(bag['weather.weather'])         # 'Clear sky'
```

### SystemResolver

Local system information (platform, CPU, disk, network). Optionally adds memory/CPU usage if `psutil` is installed.

```python
from genro_bag import Bag
from genro_bag_contrib_resolvers import SystemResolver

bag = Bag()
bag['system'] = SystemResolver()
print(bag['system.platform.system'])  # 'Darwin'
print(bag['system.cpu.count'])        # 8
```

## Examples

See the [examples/](examples/) directory for complete working examples.

## License

Apache-2.0 - Copyright 2025 Softwell S.r.l.
