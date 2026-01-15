# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0

"""URL Resolver examples.

Demonstrates fetching remote content into Bag:
- Fetching XML from URLs
- Fetching JSON from APIs
- Lazy loading with resolvers
"""

from __future__ import annotations

from genro_bag import Bag
from genro_bag.resolvers import UrlResolver


def demo_fetch_xml():
    """Fetch XML from URL into Bag."""
    print("=" * 60)
    print("Fetch XML from URL")
    print("=" * 60)

    # ECB exchange rates (public XML feed)
    url = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"

    print(f"Fetching: {url}")
    bag = Bag.from_url(url)

    print("\nParsed structure (first 10 paths):")
    for i, (path, node) in enumerate(bag.walk()):
        if i >= 10:
            print("  ...")
            break
        indent = "  " * path.count(".")
        if node.is_branch:
            print(f"{indent}{node.label}")
        else:
            # Use get_value(static=True) to show cached value without triggering resolvers
            print(f"{indent}{node.label}: {node.get_value(static=True)}")


def demo_fetch_json():
    """Fetch JSON from API into Bag."""
    print("\n" + "=" * 60)
    print("Fetch JSON from API")
    print("=" * 60)

    # httpbin.org test API
    url = "https://httpbin.org/json"

    print(f"Fetching: {url}")
    bag = Bag.from_url(url)

    print("\nParsed JSON structure:")
    for path, node in bag.walk():
        indent = "  " * path.count(".")
        if node.is_branch:
            print(f"{indent}{node.label}")
        else:
            # Use get_value(static=True) to show cached value without triggering resolvers
            value = node.get_value(static=True)
            value_str = str(value)[:50] + "..." if len(str(value)) > 50 else value
            print(f"{indent}{node.label}: {value_str}")


def demo_lazy_resolver():
    """Use UrlResolver for lazy loading."""
    print("\n" + "=" * 60)
    print("Lazy Loading with UrlResolver")
    print("=" * 60)

    # Create Bag with resolver (doesn't fetch yet)
    bag = Bag()
    resolver = UrlResolver("https://httpbin.org/json", as_bag=True)
    bag.set_item("api_data", None, resolver=resolver)

    print("Resolver attached but not fetched yet")
    print(f"Node has resolver: {bag.get_node('api_data').resolver is not None}")

    # Access triggers fetch - use get_value() to explicitly trigger resolver
    print("\nAccessing data (triggers fetch)...")
    node = bag.get_node("api_data")
    value = node.get_value()  # This triggers the resolver

    print(f"Data loaded: {type(value)}")
    if isinstance(value, Bag):
        print(f"Keys: {[n.label for n in value]}")


def demo():
    """Run all demos."""
    demo_fetch_xml()
    demo_fetch_json()
    demo_lazy_resolver()


if __name__ == "__main__":
    demo()
