# OpenMeteoResolver Demo

## Single resolver with query string syntax

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

## Multiple cities via node attributes

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
├── berlin [city='berlin']
│   ├── temperature_2m: 3.8
│   ├── wind_speed_10m: 9.7
│   ├── relative_humidity_2m: 88
│   └── weather: 'Fog'
└── madrid [city='madrid']
    ├── temperature_2m: 8.6
    ├── wind_speed_10m: 3.2
    ├── relative_humidity_2m: 65
    └── weather: 'Mainly clear'
```

## Async usage with smartawait

```python
>>> from genro_bag import Bag
>>> from open_meteo_resolver import OpenMeteoResolver
>>> from genro_toolbox import smartawait
>>> import asyncio
>>>
>>> async def get_weather(city):
...     bag = Bag()
...     bag['meteo'] = OpenMeteoResolver()
...     return await smartawait(bag[f'meteo?city={city}'])
>>>
>>> # Single city
>>> weather = asyncio.run(get_weather('London'))
>>> weather['temperature_2m']
7.4
>>>
>>> # Compare multiple cities in parallel
>>> async def compare_cities():
...     bag = Bag()
...     bag['meteo'] = OpenMeteoResolver()
...     london, paris, rome = await asyncio.gather(
...         smartawait(bag['meteo?city=London']),
...         smartawait(bag['meteo?city=Paris']),
...         smartawait(bag['meteo?city=Rome'])
...     )
...     return {
...         'London': london['temperature_2m'],
...         'Paris': paris['temperature_2m'],
...         'Rome': rome['temperature_2m']
...     }
>>>
>>> temps = asyncio.run(compare_cities())
>>> temps
{'London': 7.4, 'Paris': 5.2, 'Rome': 10.1}
```
