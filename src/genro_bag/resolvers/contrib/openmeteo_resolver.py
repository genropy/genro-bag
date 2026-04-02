# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0

"""OpenMeteoResolver - Weather data from Open-Meteo API.

Fetches current weather for a city name using Open-Meteo's free API.
The city is geocoded to coordinates using Open-Meteo's Geocoding API.

Example:
    from genro_bag import Bag
    from genro_bag.resolvers.contrib import OpenMeteoResolver

    bag = Bag()
    bag.set_item('weather', OpenMeteoResolver(city='Rome'))
    print(bag['weather.temperature_2m'])  # 18.5
    print(bag['weather.weather'])         # 'Clear sky'

    # Change city dynamically via node attributes
    bag.set_attr('weather', city='Milan')
    print(bag['weather.temperature_2m'])  # 12.3
"""

from __future__ import annotations

from typing import Any

import httpx

from genro_bag import Bag
from genro_bag.resolvers import UrlResolver

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"

# WMO Weather interpretation codes (WMO 4677)
# https://open-meteo.com/en/docs
WMO_WEATHER_CODES: dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


class OpenMeteoResolver(UrlResolver):
    """Resolver that fetches weather data from Open-Meteo API.

    Parameters (class_kwargs):
        city: Name of the city (required).
        language: Language for geocoding search. Default "en".
        country_code: ISO-3166-1 alpha2 country code. Default None.
        cache_time: Cache duration in seconds. Default 60.
    """

    class_kwargs: dict[str, Any] = {
        **UrlResolver.class_kwargs,
        "url": FORECAST_URL,
        "cache_time": 60,
        "city": None,
        "language": "en",
        "country_code": None,
    }
    internal_params = UrlResolver.internal_params | {"city", "language", "country_code"}

    def init(self) -> None:
        """Geocode city and set query string parameters."""
        city = self._kw["city"]
        if not city:
            raise ValueError("city parameter is required")

        lat, lon = self._geocode_city()
        self._kw["qs"] = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,weather_code,wind_speed_10m,relative_humidity_2m",
        }

    def _geocode_city(self) -> tuple[float, float]:
        """Get coordinates for a city name using Open-Meteo Geocoding API.

        Returns:
            Tuple of (latitude, longitude).

        Raises:
            ValueError: If city is not found.
        """
        city = self._kw["city"]
        language = self._kw["language"]
        country_code = self._kw["country_code"]

        params = {"name": city, "count": 1, "language": language, "format": "json"}
        if country_code:
            params["countryCode"] = country_code

        response = httpx.get(GEOCODING_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if "results" not in data or not data["results"]:
            raise ValueError(f"City not found: {city}")

        result = data["results"][0]
        return result["latitude"], result["longitude"]

    def process_response(self, response: httpx.Response) -> Bag:
        """Parse Open-Meteo JSON response into a Bag."""
        response.raise_for_status()
        data = response.json()

        current = data["current"]
        result = Bag()
        for key, value in current.items():
            if key == "weather_code":
                result["weather"] = WMO_WEATHER_CODES.get(value, f"Unknown ({value})")
            else:
                result[key] = value

        return result
