# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0

"""Earthquake logger example — active cache + subscriptions.

Demonstrates:
- EarthquakeResolver (contrib): fetches USGS feed with If-Modified-Since
- Active cache (cache_time < 0): background refresh
- Timer subscription: periodically processes feed into versioned quakes
- Insert subscription: reacts to each new earthquake event

Structure of self.bag['quakes']:
    quakes/
    ├── us/
    │   └── 7000n1b2/
    │       ├── 00 = None  {place: "...", mag: 2.1, updated: ...}
    │       └── 01 = None  {place: "...", mag: 2.3, updated: ...}
    └── nc/
        └── 74053451/
            └── 00 = None  {place: "...", mag: 1.8, updated: ...}

Usage:
    pip install genro-bag-contrib-resolvers
    python earthquake_resolver_example.py
"""

import time

from genro_bag import Bag
from genro_bag_contrib_resolvers import EarthquakeResolver

LOG_TEMPLATE = "  [{tag}] {where}/{event_id}.{version} M{mag} -- {place}"


class EarthquakeLogger:
    """Monitors USGS earthquake feed with versioning and logging.

    Args:
        interval: Seconds between feed checks.
    """

    def __init__(self, interval: int = 60):
        self.bag = Bag()

        # Quakes bag + subscription
        self.bag["quakes"] = Bag()
        self.bag["quakes"].subscribe("logger", insert=self.log_event)

        # Feed resolver + timer subscription
        self.bag["feed"] = EarthquakeResolver(cache_time=-interval)
        self.bag.subscribe("poll_feed", timer=self.process_feed, interval=interval)

        # First load + process
        self.process_feed()

    def process_feed(self, **kw):
        """Process raw feed into versioned quakes."""
        features = self.bag["feed.features"]
        quakes = self.bag["quakes"]

        for fid, attrs, updated in features.query("#k,#a,#a.updated"):
            key = f"{fid[:2]}.{fid[2:]}"
            if key not in quakes:
                quakes[key] = Bag()
            elif quakes[key].nodes[-1].attr['updated'] == updated:
                continue
            event_bag = quakes[key]
            version = f"{len(event_bag):02d}"
            event_bag.set_item(version, None, **attrs)

    def log_event(self, node=None, pathlist=None, **_kw):
        """Log new or updated earthquake events."""
        if not node.attr:
            return
        record = dict(node.attr)
        record.setdefault("place", "?")
        record.setdefault("mag", "?")
        record["where"] = pathlist[0]
        record["event_id"] = pathlist[1]
        record["version"] = node.label
        record["tag"] = "New Quake" if node.label == "00" else "Update Quake"
        print(LOG_TEMPLATE.format(**record))


if __name__ == "__main__":
    logger = EarthquakeLogger(interval=60)

    count = len(list(logger.bag["quakes"].query("#k", deep=True, branch=False)))
    print(f"\nQuakes loaded: {count}")
    print("Listening for new earthquakes (refresh every 60s)...")
    print("Press Ctrl+C to stop.\n")

    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print("\nStopped.")
