# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Community-contributed resolvers.

Ready-to-use resolvers for specific external services and data sources.
These extend the core resolvers with domain-specific logic.

- OpenMeteoResolver: Weather data from Open-Meteo API
- SystemResolver: Local system information (platform, CPU, disk, memory)

Example:
    from genro_bag import Bag
    from genro_bag.contrib import OpenMeteoResolver, SystemResolver

    bag = Bag()
    bag['weather'] = OpenMeteoResolver(city='Milan')
    bag['system'] = SystemResolver()
"""

from .openmeteo_resolver import OpenMeteoResolver
from .system_resolver import SystemResolver

__all__ = [
    "OpenMeteoResolver",
    "SystemResolver",
]
