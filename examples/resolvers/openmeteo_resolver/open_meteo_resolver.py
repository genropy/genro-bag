# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0

"""OpenMeteoResolver - Custom resolver extending UrlResolver for weather data.

This module provides a resolver that fetches weather data from Open-Meteo API.
It demonstrates how to create a custom resolver by subclassing UrlResolver,
adding dynamic parameters that can be changed via:
1. resolver defaults (at construction)
2. node attributes (via set_attr)
3. get_item kwargs (at call time)
"""

from __future__ import annotations

from typing import Any

import httpx

from genro_bag import Bag
from genro_bag.resolvers import UrlResolver

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

    Extends UrlResolver to add city, language and country_code parameters.
    The city name is geocoded to coordinates using Open-Meteo's Geocoding API.

    Parameters (class_kwargs):
        city: Name of the city (required).
        language: Language for geocoding search. Default "en".
        country_code: ISO-3166-1 alpha2 country code. Default None (no filter).
        cache_time: Cache duration in seconds. Default 60.
        read_only: If True, value is not stored. Default False.

    Returns:
        Bag: Weather data including temperature, weather description, wind speed, humidity.

    Example:
        >>> resolver = OpenMeteoResolver(city="Milan")
        >>> weather = resolver()
        >>> print(weather['weather'])
        Clear sky

        >>> # Or attach to a Bag node and change city dynamically
        >>> bag = Bag()
        >>> bag.set_item('weather', OpenMeteoResolver(city="Rome"))
        >>> print(bag['weather.temperature_2m'])
        12.3
        >>> bag.set_attr('weather', city="Milan")
        >>> print(bag['weather.temperature_2m'])
        9.5
    """

    class_kwargs: dict[str, Any] = {
        **UrlResolver.class_kwargs,
        "url": "https://api.open-meteo.com/v1/forecast",
        "as_bag": True,
        "cache_time": 60,
        # User parameters - can be overridden via node.attr or get_item kwargs
        "city": None,
        "language": "en",
        "country_code": None,
    }
    # Mark user params as internal so they don't get passed to UrlResolver
    internal_params: set[str] = UrlResolver.internal_params | {"city", "language", "country_code"}

    def _geocode_city(self) -> tuple[float, float]:
        """Get coordinates for a city name using Open-Meteo Geocoding API.

        Uses city, language and country_code from _kw parameters.

        Returns:
            Tuple of (latitude, longitude).

        Raises:
            ValueError: If city is not found.
        """
        city = self._kw["city"]
        language = self._kw["language"]
        country_code = self._kw["country_code"]

        url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language={language}&format=json"
        if country_code:
            url += f"&countryCode={country_code}"
        response = httpx.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if "results" not in data or not data["results"]:
            raise ValueError(f"City not found: {city}")

        result = data["results"][0]
        return result["latitude"], result["longitude"]

    async def async_load(self) -> Bag:
        """Fetch current weather from Open-Meteo API.

        Geocodes the city name to coordinates, then fetches weather data.
        The weather_code is translated to a human-readable description.

        Returns:
            Bag: Current weather data (temperature, weather, wind_speed, humidity).
        """
        city = self._kw["city"]
        if not city:
            raise ValueError("city parameter is required")

        lat, lon = self._geocode_city()

        self._kw["qs"] = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,weather_code,wind_speed_10m,relative_humidity_2m",
        }
        result = await super().async_load()
        current = result["current"]

        # Translate weather_code to description
        code = current.pop("weather_code")
        current.set_item("weather", WMO_WEATHER_CODES.get(code, f"Unknown ({code})"))

        return current
