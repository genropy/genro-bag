# Copyright 2025 Softwell S.r.l. - Genropy Team
# Licensed under the Apache License, Version 2.0

"""Tests for OpenApiResolver - OpenAPI spec loading organized by tags."""

import pytest

from genro_bag import Bag
from genro_bag.resolvers import OpenApiResolver

# Petstore OpenAPI spec URL
PETSTORE_URL = "https://petstore3.swagger.io/api/v3/openapi.json"

# Skip all tests if httpx not installed
pytest.importorskip("httpx")


@pytest.fixture(autouse=True)
def reset_smartasync_cache():
    """Reset smartasync cache before each test."""
    # Reset before test - BagResolver.__call__ also uses @smartasync
    from genro_bag.resolver import BagResolver

    if hasattr(OpenApiResolver.load, "_smartasync_reset_cache"):
        OpenApiResolver.load._smartasync_reset_cache()
    if hasattr(BagResolver.__call__, "_smartasync_reset_cache"):
        BagResolver.__call__._smartasync_reset_cache()
    yield


class TestOpenApiResolverBasic:
    """Basic OpenAPI loading tests."""

    @pytest.mark.network
    def test_load_petstore_spec(self):
        """Load Petstore OpenAPI spec."""
        resolver = OpenApiResolver(PETSTORE_URL)
        api = resolver()

        assert isinstance(api, Bag)
        assert len(api) > 0

    @pytest.mark.network
    def test_has_info(self):
        """Loaded spec has info section with title as attribute."""
        resolver = OpenApiResolver(PETSTORE_URL)
        api = resolver()

        assert "info" in api.keys()
        # info value is the description string
        info = api["info"]
        assert isinstance(info, str)
        # title is in node attributes
        info_node = api.get_node("info")
        assert info_node.attr.get("title") is not None

    @pytest.mark.network
    def test_has_tags_as_children(self):
        """Tags from spec become child Bags under 'api'."""
        resolver = OpenApiResolver(PETSTORE_URL)
        api = resolver()

        # Tags are under api['api']
        assert "api" in api.keys()
        api_bag = api["api"]
        # Petstore has pet, store, user tags
        assert "pet" in api_bag.keys()
        assert "store" in api_bag.keys()
        assert "user" in api_bag.keys()

    @pytest.mark.network
    def test_tag_bag_has_endpoints(self):
        """Each tag Bag contains endpoints."""
        resolver = OpenApiResolver(PETSTORE_URL)
        api = resolver()

        pet_bag = api["api.pet"]
        assert isinstance(pet_bag, Bag)
        assert len(pet_bag) > 0

    @pytest.mark.network
    def test_endpoint_has_operation_info(self):
        """Endpoints contain operation details."""
        resolver = OpenApiResolver(PETSTORE_URL)
        api = resolver()

        # Get first endpoint from pet tag
        pet_bag = api["api.pet"]
        first_key = list(pet_bag.keys())[0]
        endpoint = pet_bag[first_key]

        # Should have at least summary or operationId
        keys = endpoint.keys()
        assert "summary" in keys or "operationId" in keys


class TestOpenApiResolverStructure:
    """Tests for Bag structure from OpenAPI."""

    @pytest.mark.network
    def test_components_included(self):
        """Components section is included."""
        resolver = OpenApiResolver(PETSTORE_URL)
        api = resolver()

        assert "components" in api.keys()
        components = api["components"]
        assert isinstance(components, Bag)

    @pytest.mark.network
    def test_schemas_in_components(self):
        """Schemas are accessible in components."""
        resolver = OpenApiResolver(PETSTORE_URL)
        api = resolver()

        components = api["components"]
        assert "schemas" in components.keys()

        schemas = components["schemas"]
        # Petstore has Pet schema
        assert "Pet" in schemas.keys()

    @pytest.mark.network
    def test_endpoint_has_method_key(self):
        """Endpoint Bag has method as a key."""
        resolver = OpenApiResolver(PETSTORE_URL)
        api = resolver()

        pet_bag = api["api.pet"]
        first_key = list(pet_bag.keys())[0]
        endpoint = pet_bag[first_key]

        # Method should be a key in endpoint Bag
        assert "method" in endpoint.keys()

    @pytest.mark.network
    def test_endpoint_has_nested_url_resolver(self):
        """Endpoint has nested UrlResolver accessible via Bag path."""
        from genro_bag.resolvers import UrlResolver

        # Create a Bag and put OpenApiResolver inside
        apibag = Bag()
        apibag["openapi.petstore"] = OpenApiResolver(PETSTORE_URL)

        # Access nested UrlResolver via full path (static=False to trigger resolvers)
        value_node = apibag.get_node("openapi.petstore.api.store.getInventory.value", static=False)
        assert value_node is not None
        assert value_node.resolver is not None
        assert isinstance(value_node.resolver, UrlResolver)

        # Check resolver has correct method
        assert value_node.resolver._kw["method"] == "get"


class TestOpenApiResolverCaching:
    """Cache behavior tests."""

    def test_cache_time_default(self):
        """Default cache_time is -1 (infinite cache)."""
        resolver = OpenApiResolver(PETSTORE_URL)
        assert resolver.cache_time == -1

    def test_custom_cache_time(self):
        """Custom cache_time is respected."""
        resolver = OpenApiResolver(PETSTORE_URL, cache_time=600)
        assert resolver.cache_time == 600


class TestOpenApiResolverInBag:
    """Integration with Bag."""

    @pytest.mark.network
    def test_resolver_in_bag_node(self):
        """OpenApiResolver works when assigned to Bag node."""
        bag = Bag()
        bag["petstore"] = OpenApiResolver(PETSTORE_URL)

        node = bag.get_node("petstore")
        assert node.resolver is not None
        assert isinstance(node.resolver, OpenApiResolver)

        # Trigger resolver
        api = node.resolver()
        assert isinstance(api, Bag)
        assert "pet" in api["api"].keys()


class TestOpenApiResolverEquality:
    """Resolver equality tests."""

    def test_same_url_equal(self):
        """Same URL produces equal resolvers."""
        r1 = OpenApiResolver(PETSTORE_URL)
        r2 = OpenApiResolver(PETSTORE_URL)
        assert r1 == r2

    def test_different_url_not_equal(self):
        """Different URLs produce different resolvers."""
        r1 = OpenApiResolver(PETSTORE_URL)
        r2 = OpenApiResolver("https://example.com/api.json")
        assert r1 != r2

    def test_same_url_different_cache_not_equal(self):
        """Same URL but different cache_time are not equal."""
        r1 = OpenApiResolver(PETSTORE_URL, cache_time=60)
        r2 = OpenApiResolver(PETSTORE_URL, cache_time=120)
        assert r1 != r2


class TestOpenApiResolverSerialization:
    """Serialization tests."""

    def test_serialize(self):
        """Resolver can be serialized."""
        resolver = OpenApiResolver(PETSTORE_URL, cache_time=120, timeout=45)
        data = resolver.serialize()

        assert data["resolver_class"] == "OpenApiResolver"
        assert "openapi_resolver" in data["resolver_module"]
        assert data["args"] == [PETSTORE_URL]
        assert data["kwargs"]["cache_time"] == 120
        assert data["kwargs"]["timeout"] == 45

    def test_deserialize(self):
        """Resolver can be deserialized."""
        from genro_bag.resolver import BagResolver

        original = OpenApiResolver(PETSTORE_URL, cache_time=120)
        data = original.serialize()

        restored = BagResolver.deserialize(data)

        assert isinstance(restored, OpenApiResolver)
        assert restored._kw["url"] == PETSTORE_URL
        assert restored._kw["cache_time"] == 120
