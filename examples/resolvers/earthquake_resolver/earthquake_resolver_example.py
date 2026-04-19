# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0

"""Earthquake logger example — pure dataflow via interval + subscribe.

Pattern:
    interval -> feed update event -> process_feed -> quakes insert event
        -> log_event

A single timer lives inside the resolver. The refresh writes the new
feed value via the node mutation channel (emitting an update event), so
a subscriber on 'feed' is the natural trigger for parsing — no external
timer-subscribe is needed.

Usage:
    pip install genro-bag[contrib-resolvers]
    python earthquake_resolver_example.py
"""

import asyncio

from genro_bag import Bag
from genro_bag.resolvers.contrib import EarthquakeResolver

LOG_TEMPLATE = "  [{tag}] {where}/{event_id}.{version} M{mag} -- {place}"


class EarthquakeLogger:
    """Monitors USGS earthquake feed with versioning and logging.

    Args:
        interval: Seconds between feed checks.
    """

    def __init__(self):
        # Sync phase: build the bag structure. No resolvers with timers,
        # no event loop needed. Safe to run anywhere.
        self.bag = Bag()
        self.bag.set_backref()
        self.bag["quakes"] = Bag()
        self.bag["quakes"].subscribe("logger", insert=self.log_event)

    async def start(self, interval: int = 60):
        # Async phase: attach the resolver, subscribe to its node, turn
        # on the interval. The last line is the explicit "power on".
        self.bag["feed"] = EarthquakeResolver()
        feed_node = self.bag.get_node("feed")
        feed_node.subscribe("parser", self.process_feed)
        feed_node.resolver.interval = interval

    def process_feed(self, **_kw):
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


async def main():
    logger = EarthquakeLogger()         # sync: structure only
    await logger.start(interval=10)     # async: attach + power on
    print("Listening for new earthquakes (refresh every 10s)...")
    print("Press Ctrl+C to stop.\n")
    await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped.")
