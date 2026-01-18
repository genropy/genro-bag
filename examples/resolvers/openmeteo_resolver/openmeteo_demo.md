# OpenMeteoResolver Demo

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
