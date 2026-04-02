# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Community-contributed resolvers for genro-bag.

Ready-to-use resolvers for specific external services and data sources.

- EarthquakeResolver: USGS earthquake feed with conditional requests and versioning
- OpenMeteoResolver: Weather data from Open-Meteo API
- SystemResolver: Local system information (platform, CPU, disk, memory)

Example:
    from genro_bag import Bag
    from genro_bag.resolvers.contrib import EarthquakeResolver, OpenMeteoResolver, SystemResolver

    bag = Bag()
    bag['quakes'] = EarthquakeResolver(cache_time=-60)
    bag['weather'] = OpenMeteoResolver(city='Milan')
    bag['system'] = SystemResolver()
"""

from .earthquake_resolver import EarthquakeResolver
from .openmeteo_resolver import OpenMeteoResolver
from .system_resolver import SystemResolver

__all__ = [
    "EarthquakeResolver",
    "OpenMeteoResolver",
    "SystemResolver",
]
