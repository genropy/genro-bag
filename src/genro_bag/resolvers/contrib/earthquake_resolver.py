# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0

"""EarthquakeResolver - USGS earthquake feed with conditional requests.

Fetches recent earthquakes from the USGS GeoJSON feed. Uses If-Modified-Since
to skip redownloading when data hasn't changed. Returns raw GeoJSON features
as a Bag.

The resolver is intentionally simple — it only fetches data. Business logic
(versioning, deduplication, notifications) belongs in subscriptions.

Example (async only — active cache requires an event loop):
    import asyncio
    from genro_bag import Bag
    from genro_bag.resolvers.contrib import EarthquakeResolver

    async def main():
        bag = Bag()
        bag['feed'] = EarthquakeResolver(cache_time=-60)
        print(bag['feed.count'])

    asyncio.run(main())
"""

from __future__ import annotations

from typing import Any

import httpx

from genro_bag import Bag
from genro_bag.resolvers import UrlResolver

USGS_FEED = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson"


class EarthquakeResolver(UrlResolver):
    """Resolver that fetches recent earthquakes from USGS.

    Uses If-Modified-Since to avoid redownloading unchanged data.
    Returns a Bag with count, title, and features (raw GeoJSON data).
    """

    class_kwargs: dict[str, Any] = {
        **UrlResolver.class_kwargs,
        "url": USGS_FEED,
    }
    class_args: list[str] = ["url"]

    def init(self) -> None:
        """Initialize last-modified tracking."""
        self._last_modified: str | None = None

    def prepare_headers(self) -> dict[str, str]:
        """Add If-Modified-Since header when available."""
        if self._last_modified:
            return {"If-Modified-Since": self._last_modified}
        return {}

    def process_response(self, response: httpx.Response) -> Bag:
        """Parse USGS GeoJSON response into a Bag."""
        if response.status_code == 304:
            return self.cached_value

        response.raise_for_status()
        self._last_modified = response.headers.get("Last-Modified")

        data = response.json()
        result = Bag()
        result["count"] = len(data["features"])
        result["title"] = data["metadata"]["title"]

        features = Bag()
        for feature in data["features"]:
            props = feature["properties"]
            fid = feature["id"]
            features.set_item(
                fid,
                None,
                place=props.get("place", "Unknown"),
                mag=props.get("mag", 0),
                time=props.get("time", 0),
                updated=props.get("updated", 0),
            )

        result["features"] = features
        return result
