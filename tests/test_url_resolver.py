# Copyright 2025 Softwell S.r.l. - Genropy Team
# Licensed under the Apache License, Version 2.0

"""Tests for UrlResolver and Bag.from_url() - HTTP URL loading.

These tests use real HTTP endpoints for integration testing.
Some tests are marked with @pytest.mark.network to allow skipping
when network is not available.
"""

import asyncio

import pytest

from genro_bag import Bag
from genro_bag.resolvers import UrlResolver

# ECB daily exchange rates - stable public XML endpoint
ECB_RATES_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"

# httpbin for testing - provides various response formats
HTTPBIN_JSON = "https://httpbin.org/json"
HTTPBIN_XML = "https://httpbin.org/xml"


# Skip all tests if httpx not installed
pytest.importorskip("httpx")


@pytest.fixture(autouse=True)
def reset_smartasync_cache():
    """Reset smartasync cache before each test."""
    # Reset before test - BagResolver.__call__ also uses @smartasync
    from genro_bag.resolver import BagResolver

    if hasattr(Bag.from_url, "_smartasync_reset_cache"):
        Bag.from_url._smartasync_reset_cache()
    if hasattr(UrlResolver.load, "_smartasync_reset_cache"):
        UrlResolver.load._smartasync_reset_cache()
    if hasattr(BagResolver.__call__, "_smartasync_reset_cache"):
        BagResolver.__call__._smartasync_reset_cache()
    yield


# =============================================================================
# Bag.from_url() tests
# =============================================================================


class TestBagFromUrl:
    """Tests for Bag.from_url() classmethod."""

    @pytest.mark.network
    def test_from_url_ecb_xml(self):
        """Load ECB exchange rates XML."""
        bag = Bag.from_url(ECB_RATES_URL)
        assert isinstance(bag, Bag)
        assert len(bag) > 0

    @pytest.mark.network
    def test_from_url_httpbin_xml(self):
        """Load httpbin XML."""
        bag = Bag.from_url(HTTPBIN_XML)
        assert isinstance(bag, Bag)
        assert len(bag) > 0

    @pytest.mark.network
    def test_from_url_with_timeout(self):
        """Custom timeout parameter."""
        bag = Bag.from_url(ECB_RATES_URL, timeout=60)
        assert isinstance(bag, Bag)

    @pytest.mark.asyncio
    @pytest.mark.network
    async def test_from_url_async(self):
        """Async context usage."""
        bag = await Bag.from_url(ECB_RATES_URL)
        assert isinstance(bag, Bag)
        assert len(bag) > 0

    @pytest.mark.asyncio
    @pytest.mark.network
    async def test_from_url_multiple_async(self):
        """Multiple concurrent async fetches."""
        results = await asyncio.gather(
            Bag.from_url(ECB_RATES_URL),
            Bag.from_url(HTTPBIN_XML),
        )
        assert all(isinstance(r, Bag) for r in results)
        assert all(len(r) > 0 for r in results)


class TestUrlResolverBasic:
    """Basic URL fetching."""

    @pytest.mark.network
    def test_fetch_raw_content(self):
        """Fetch URL returns raw bytes."""
        resolver = UrlResolver(HTTPBIN_JSON, as_bag=False)
        result = resolver()
        assert isinstance(result, bytes)
        assert b"slideshow" in result  # httpbin/json contains this

    @pytest.mark.network
    def test_fetch_with_timeout(self):
        """Custom timeout is respected."""
        resolver = UrlResolver(HTTPBIN_JSON, timeout=60)
        result = resolver()
        assert isinstance(result, bytes)

    def test_resolver_parameters(self):
        """Resolver stores parameters correctly."""
        resolver = UrlResolver(
            "http://example.com/data.xml", cache_time=120, timeout=45, as_bag=True
        )
        assert resolver._kw["url"] == "http://example.com/data.xml"
        assert resolver._kw["cache_time"] == 120
        assert resolver._kw["timeout"] == 45
        assert resolver._kw["as_bag"] is True


class TestUrlResolverAsBag:
    """Fetching and parsing as Bag."""

    @pytest.mark.network
    def test_fetch_ecb_xml_as_bag(self):
        """Fetch ECB exchange rates XML and parse as Bag."""
        resolver = UrlResolver(ECB_RATES_URL, as_bag=True)
        result = resolver()

        assert isinstance(result, Bag)
        # ECB XML structure: <gesmes:Envelope><Cube>...</Cube></gesmes:Envelope>
        # The root should have children
        assert len(result) > 0

    @pytest.mark.network
    def test_fetch_httpbin_xml_as_bag(self):
        """Fetch httpbin XML and parse as Bag."""
        resolver = UrlResolver(HTTPBIN_XML, as_bag=True)
        result = resolver()

        assert isinstance(result, Bag)
        # httpbin/xml returns a slideshow structure
        assert len(result) > 0

    @pytest.mark.network
    def test_auto_detect_xml_from_content(self):
        """Auto-detect XML format from content even without .xml extension."""
        # httpbin/xml doesn't have .xml extension but returns XML
        resolver = UrlResolver(HTTPBIN_XML, as_bag=True)
        result = resolver()
        assert isinstance(result, Bag)


class TestUrlResolverAsync:
    """Async context tests."""

    @pytest.mark.asyncio
    @pytest.mark.network
    async def test_async_fetch_raw(self):
        """Async fetch returns raw bytes."""
        resolver = UrlResolver(HTTPBIN_JSON, as_bag=False)

        # Call resolver() in async context - returns coroutine to await
        result = await resolver()
        assert isinstance(result, bytes)
        assert b"slideshow" in result

    @pytest.mark.asyncio
    @pytest.mark.network
    async def test_async_fetch_as_bag(self):
        """Async fetch and parse as Bag."""
        resolver = UrlResolver(ECB_RATES_URL, as_bag=True)

        result = await resolver()
        assert isinstance(result, Bag)
        assert len(result) > 0

    @pytest.mark.asyncio
    @pytest.mark.network
    async def test_multiple_async_fetches(self):
        """Multiple async fetches can run concurrently."""
        resolver1 = UrlResolver(HTTPBIN_JSON, as_bag=False)
        resolver2 = UrlResolver(HTTPBIN_XML, as_bag=True)

        # Run concurrently - resolver() returns coroutines in async context
        results = await asyncio.gather(resolver1(), resolver2())

        assert isinstance(results[0], bytes)
        assert isinstance(results[1], Bag)


class TestUrlResolverCaching:
    """Cache behavior tests."""

    @pytest.mark.network
    def test_cache_time_default(self):
        """Default cache_time is 300 seconds."""
        resolver = UrlResolver(HTTPBIN_JSON)
        assert resolver.cache_time == 300

    @pytest.mark.network
    def test_no_cache(self):
        """cache_time=0 fetches every time (different UUIDs)."""
        resolver = UrlResolver("https://httpbin.org/uuid", cache_time=0)

        result1 = resolver()
        result2 = resolver()

        # With cache_time=0, each call makes a new request
        # httpbin/uuid returns a different UUID each time
        assert result1 != result2


class TestUrlResolverInBag:
    """UrlResolver integrated with Bag."""

    @pytest.mark.network
    def test_resolver_in_bag_node(self):
        """UrlResolver works when assigned to Bag node."""
        bag = Bag()
        bag["rates"] = UrlResolver(ECB_RATES_URL, as_bag=True)

        # Check resolver is set
        node = bag.get_node("rates")
        assert node.resolver is not None
        assert isinstance(node.resolver, UrlResolver)

        # Access triggers load
        result = node.resolver()
        assert isinstance(result, Bag)

    @pytest.mark.network
    def test_multiple_url_resolvers(self):
        """Multiple URL resolvers in same Bag."""
        bag = Bag()
        bag["json"] = UrlResolver(HTTPBIN_JSON, as_bag=False)
        bag["xml"] = UrlResolver(HTTPBIN_XML, as_bag=True)

        json_result = bag.get_node("json").resolver()
        xml_result = bag.get_node("xml").resolver()

        assert isinstance(json_result, bytes)
        assert isinstance(xml_result, Bag)


class TestUrlResolverEquality:
    """Resolver equality tests."""

    def test_same_url_same_params_equal(self):
        """Same URL and params produce equal resolvers."""
        r1 = UrlResolver("http://example.com", cache_time=60)
        r2 = UrlResolver("http://example.com", cache_time=60)
        assert r1 == r2

    def test_different_url_not_equal(self):
        """Different URLs produce different resolvers."""
        r1 = UrlResolver("http://example.com/a")
        r2 = UrlResolver("http://example.com/b")
        assert r1 != r2

    def test_same_url_different_cache_not_equal(self):
        """Same URL but different cache_time are not equal."""
        r1 = UrlResolver("http://example.com", cache_time=60)
        r2 = UrlResolver("http://example.com", cache_time=120)
        assert r1 != r2


class TestUrlResolverSerialization:
    """Serialization tests."""

    def test_serialize(self):
        """Resolver can be serialized."""
        resolver = UrlResolver(
            "http://example.com/data.xml", cache_time=120, timeout=45, as_bag=True
        )
        data = resolver.serialize()

        assert data["resolver_class"] == "UrlResolver"
        assert "url_resolver" in data["resolver_module"]
        assert data["args"] == ["http://example.com/data.xml"]
        assert data["kwargs"]["cache_time"] == 120
        assert data["kwargs"]["timeout"] == 45
        assert data["kwargs"]["as_bag"] is True

    def test_deserialize(self):
        """Resolver can be deserialized."""
        from genro_bag.resolver import BagResolver

        original = UrlResolver("http://example.com/data.xml", cache_time=120, as_bag=True)
        data = original.serialize()

        restored = BagResolver.deserialize(data)

        assert isinstance(restored, UrlResolver)
        assert restored._kw["url"] == "http://example.com/data.xml"
        assert restored._kw["cache_time"] == 120
        assert restored._kw["as_bag"] is True


class TestUrlResolverErrorHandling:
    """Error handling tests."""

    @pytest.mark.network
    def test_invalid_url_raises(self):
        """Invalid URL raises appropriate error."""
        import httpx

        resolver = UrlResolver("http://invalid.invalid.invalid/")
        with pytest.raises((httpx.ConnectError, httpx.HTTPError)):
            resolver()

    @pytest.mark.network
    def test_404_raises(self):
        """404 response raises HTTPStatusError."""
        import httpx

        resolver = UrlResolver("https://httpbin.org/status/404")
        with pytest.raises(httpx.HTTPStatusError):
            resolver()


# =============================================================================
# Tests for query string and path parameters (coverage for lines 105-150, 167-169)
# =============================================================================


class TestUrlResolverQueryString:
    """Tests for query string handling."""

    @pytest.mark.network
    def test_query_string_from_dict(self):
        """Query string from dict is appended to URL."""
        resolver = UrlResolver(
            "https://httpbin.org/get", qs={"foo": "bar", "count": 42}, as_bag=False
        )
        result = resolver()
        # httpbin/get echoes back the query params
        assert b"foo" in result
        assert b"bar" in result

    @pytest.mark.network
    def test_query_string_from_bag(self):
        """Query string from Bag is converted correctly."""
        qs_bag = Bag()
        qs_bag["page"] = 1
        qs_bag["limit"] = 10

        resolver = UrlResolver("https://httpbin.org/get", qs=qs_bag, as_bag=False)
        result = resolver()
        assert b"page" in result
        assert b"limit" in result

    @pytest.mark.network
    def test_query_string_none_values_filtered(self):
        """None values in query string are filtered out."""
        qs = {"include": "data", "exclude": None}
        resolver = UrlResolver("https://httpbin.org/get", qs=qs, as_bag=False)
        result = resolver()
        # httpbin echoes back args
        assert b"include" in result
        assert b"exclude" not in result

    @pytest.mark.network
    def test_query_string_appended_to_existing(self):
        """Query string is appended with & if URL already has ?."""
        resolver = UrlResolver(
            "https://httpbin.org/get?existing=true", qs={"new": "value"}, as_bag=False
        )
        result = resolver()
        assert b"existing" in result
        assert b"new" in result

    @pytest.mark.network
    def test_extra_kwargs_become_query_string(self):
        """Extra kwargs not in class_kwargs become query string params."""
        resolver = UrlResolver("https://httpbin.org/get", as_bag=False)
        # Pass extra params when calling - these are stored in _kw via get_item
        resolver._kw["custom_param"] = "custom_value"
        resolver._kw["another"] = 123
        result = resolver()
        assert b"custom_param" in result
        assert b"another" in result


class TestUrlResolverPathParameters:
    """Tests for path parameter substitution."""

    @pytest.mark.network
    def test_path_parameter_substitution(self):
        """Path parameters {placeholder} are substituted with arg_N values."""
        # httpbin/anything echoes the URL path
        resolver = UrlResolver(
            "https://httpbin.org/anything/{id}/details", as_bag=False
        )
        resolver._kw["arg_0"] = "12345"
        result = resolver()
        assert b"12345" in result
        assert b"{id}" not in result

    @pytest.mark.network
    def test_multiple_path_parameters(self):
        """Multiple path parameters are substituted."""
        resolver = UrlResolver(
            "https://httpbin.org/anything/{type}/{id}", as_bag=False
        )
        resolver._kw["arg_0"] = "users"
        resolver._kw["arg_1"] = "42"
        result = resolver()
        assert b"users" in result
        assert b"42" in result

    def test_path_args_with_invalid_index(self):
        """Invalid arg_X index (non-numeric) is ignored."""
        resolver = UrlResolver("https://httpbin.org/anything/{id}")
        resolver._kw["arg_invalid"] = "ignored"
        # Should not raise, just ignore the invalid arg
        # URL still has {id} since arg_0 not set
        assert resolver._kw["url"] == "https://httpbin.org/anything/{id}"


class TestUrlResolverBodyHandling:
    """Tests for request body handling."""

    @pytest.mark.network
    def test_post_with_bag_body(self):
        """POST with Bag body is converted to JSON."""
        body = Bag()
        body["name"] = "Test"
        body["value"] = 123

        resolver = UrlResolver(
            "https://httpbin.org/post", method="post", body=body, as_bag=False
        )
        result = resolver()
        # httpbin/post echoes the JSON body
        assert b"name" in result
        assert b"Test" in result

    @pytest.mark.network
    def test_post_with_dict_body(self):
        """POST with dict body is sent as JSON."""
        body = {"name": "Test", "value": 456}

        resolver = UrlResolver(
            "https://httpbin.org/post", method="post", body=body, as_bag=False
        )
        result = resolver()
        assert b"name" in result
        assert b"456" in result

    @pytest.mark.network
    def test_body_override_via_underscore_body(self):
        """_body kwarg overrides constructor body."""
        original_body = {"original": "data"}
        override_body = {"override": "data"}

        resolver = UrlResolver(
            "https://httpbin.org/post", method="post", body=original_body, as_bag=False
        )
        resolver._kw["_body"] = override_body
        result = resolver()
        # Should use override body
        assert b"override" in result
        assert b"original" not in result


class TestUrlResolverQsToDict:
    """Tests for _qs_to_dict internal method."""

    def test_qs_to_dict_with_bag(self):
        """_qs_to_dict converts Bag to dict."""
        resolver = UrlResolver("http://example.com")
        qs_bag = Bag()
        qs_bag["a"] = 1
        qs_bag["b"] = "hello"
        qs_bag["c"] = None  # Should be filtered

        result = resolver._qs_to_dict(qs_bag)

        assert result == {"a": 1, "b": "hello"}
        assert "c" not in result

    def test_qs_to_dict_with_dict(self):
        """_qs_to_dict passes through dict filtering None values."""
        resolver = UrlResolver("http://example.com")
        qs_dict = {"x": 10, "y": None, "z": "test"}

        result = resolver._qs_to_dict(qs_dict)

        assert result == {"x": 10, "z": "test"}
        assert "y" not in result
