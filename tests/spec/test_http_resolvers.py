"""Spec test: UrlResolver and OpenApiResolver.

End-to-end tests against a local HTTP server standing in for a real
endpoint. Nothing reaches the outside world: the server listens on
127.0.0.1 on an ephemeral port, started per test and torn down after.

Approach:
- spec tests, not implementation tests: the observable contract through
  the public API (Bag plus the resolver instance)
- httpx is not mocked — the request really happens, over loopback
- the server is stdlib only (http.server on a thread): one less test
  dependency to declare, and one less to forget
- the resolvers are async at the core, so the tests carry
  @pytest.mark.asyncio and the result of bag[path] is awaited

Scale:
1.  UrlResolver GET plus as_bag=True
2.  UrlResolver query string from constructor, kwargs and Bag
3.  UrlResolver path substitution ({id} -> arg_0)
4.  UrlResolver POST with a Bag body -> json
5.  UrlResolver headers from prepare_headers() (subclass hook)
6.  UrlResolver process_response override (subclass hook)
7.  UrlResolver 4xx raises HTTPStatusError
8.  UrlResolver qs drops None values
9.  OpenApiResolver loads a minimal spec and groups it by tag
10. OpenApiResolver info/servers/components
11. OpenApiResolver operation bag holds path, method, value (UrlResolver)
"""

from __future__ import annotations

import asyncio

import httpx
import pytest

from genro_bag import Bag
from genro_bag.resolvers import OpenApiResolver, UrlResolver

# =============================================================================
# Fixtures
# =============================================================================


async def _drain(value):
    """Await repeatedly until the result is no longer a coroutine."""
    while asyncio.iscoroutine(value):
        value = await value
    return value


# =============================================================================
# 1. UrlResolver: GET base + as_bag=True
# =============================================================================


class TestUrlResolverGet:
    @pytest.mark.asyncio
    async def test_get_as_bag_parses_json_response(self, http_server):
        """UrlResolver(..., as_bag=True) on a JSON endpoint yields a Bag
        navigable by key."""
        url = str(http_server.make_url("/hello"))
        bag = Bag()
        bag["data"] = UrlResolver(url, as_bag=True)
        data = await _drain(bag["data"])
        assert isinstance(data, Bag)
        assert data["hello"] == "world"

    @pytest.mark.asyncio
    async def test_get_without_as_bag_returns_raw_bytes(self, http_server):
        """Without as_bag=True the resolver returns the raw content (bytes)."""
        url = str(http_server.make_url("/raw"))
        bag = Bag()
        bag["data"] = UrlResolver(url)
        data = await _drain(bag["data"])
        assert data == b"plain-bytes"


# =============================================================================
# 2. UrlResolver: query string (costruttore, kwargs, Bag)
# =============================================================================


class TestUrlResolverQueryString:
    @pytest.mark.asyncio
    async def test_query_string_from_constructor(self, http_server):
        """qs={...} on the constructor is sent as the query string."""
        url = str(http_server.make_url("/echo"))
        bag = Bag()
        bag["echo"] = UrlResolver(url, qs={"page": 1, "limit": 10}, as_bag=True)
        result = await _drain(bag["echo"])
        assert result["query.page"] == "1"
        assert result["query.limit"] == "10"

    @pytest.mark.asyncio
    async def test_query_string_from_extra_constructor_kwargs(self, http_server):
        """Extra kwargs on the constructor (outside class_kwargs) become the
        dynamic query string."""
        url = str(http_server.make_url("/echo"))
        bag = Bag()
        bag["echo"] = UrlResolver(url, as_bag=True, cache_time=0, foo="bar")
        result = await _drain(bag["echo"])
        assert result["query.foo"] == "bar"

    @pytest.mark.asyncio
    async def test_query_string_from_set_attr(self, http_server):
        """set_attr on a dynamic parameter updates the query string."""
        url = str(http_server.make_url("/echo"))
        bag = Bag()
        # foo declared as a dynamic attribute, initially None
        bag["echo"] = UrlResolver(url, as_bag=True, cache_time=0, foo=None)
        bag.set_attr("echo", foo="changed")
        result = await _drain(bag["echo"])
        assert result["query.foo"] == "changed"

    @pytest.mark.asyncio
    async def test_query_string_none_values_are_filtered(self, http_server):
        """None values in qs are dropped: the key never reaches the URL."""
        url = str(http_server.make_url("/echo"))
        bag = Bag()
        bag["echo"] = UrlResolver(
            url, qs={"keep": "yes", "drop": None}, as_bag=True,
        )
        result = await _drain(bag["echo"])
        assert result["query.keep"] == "yes"
        assert "drop" not in result["query"]

    @pytest.mark.asyncio
    async def test_query_string_from_bag(self, http_server):
        """qs also takes a Bag: keys and values are serialized."""
        url = str(http_server.make_url("/echo"))
        qs_bag = Bag({"a": "1", "b": "2"})
        bag = Bag()
        bag["echo"] = UrlResolver(url, qs=qs_bag, as_bag=True)
        result = await _drain(bag["echo"])
        assert result["query.a"] == "1"
        assert result["query.b"] == "2"


# =============================================================================
# 3. UrlResolver: path substitution
# =============================================================================


class TestUrlResolverPathSubstitution:
    @pytest.mark.asyncio
    async def test_path_placeholder_substituted_via_arg_0(self, http_server):
        """A URL holding '{id}' is filled from arg_0 as a dynamic parameter."""
        # Build the URL without URL-encoding '{id}' — the resolver fills it in
        url = f"http://{http_server.host}:{http_server.port}/pets/{{id}}"
        bag = Bag()
        bag["pet"] = UrlResolver(url, as_bag=True, cache_time=0, arg_0=42)
        result = await _drain(bag["pet"])
        assert result["id"] == "42"
        assert result["name"] == "pet-42"


# =============================================================================
# 4. UrlResolver: POST con body Bag -> json
# =============================================================================


class TestUrlResolverPost:
    @pytest.mark.asyncio
    async def test_post_with_bag_body(self, http_server):
        """method='post' with body=Bag: the body is serialized as json."""
        url = str(http_server.make_url("/echo_body"))
        body = Bag({"name": "alice", "age": 30})
        bag = Bag()
        bag["out"] = UrlResolver(url, method="post", body=body, as_bag=True)
        result = await _drain(bag["out"])
        assert result["received.name"] == "alice"
        assert result["received.age"] == 30

    @pytest.mark.asyncio
    async def test_post_body_overridable_via_underscore_body(self, http_server):
        """_body set via set_attr overrides the constructor body.

        UrlResolver's '_body' parameter, when present among the node
        attributes, wins over the body given to the constructor.
        """
        url = str(http_server.make_url("/echo_body"))
        bag = Bag()
        # declare _body as a dynamic parameter of the node
        bag["out"] = UrlResolver(
            url, method="post", body={"orig": 1}, as_bag=True,
            cache_time=0, _body=None,
        )
        bag.set_attr("out", _body={"override": True})
        result = await _drain(bag["out"])
        assert result["received.override"] is True
        assert "orig" not in result["received"]


# =============================================================================
# 5. UrlResolver: headers via subclass hook
# =============================================================================


class TestUrlResolverHeaders:
    @pytest.mark.asyncio
    async def test_static_headers_sent_on_request(self, http_server):
        """headers={} on the constructor travel with the request."""
        url = str(http_server.make_url("/echo"))
        bag = Bag()
        bag["echo"] = UrlResolver(
            url, as_bag=True, headers={"X-Test-Token": "abc123"},
        )
        result = await _drain(bag["echo"])
        assert result["headers"]["X-Test-Token"] == "abc123"

    @pytest.mark.asyncio
    async def test_prepare_headers_hook_adds_dynamic_headers(self, http_server):
        """Overriding prepare_headers adds dynamic headers."""

        class AuthUrlResolver(UrlResolver):
            def prepare_headers(self) -> dict[str, str]:
                return {"Authorization": "Bearer dynamic-token"}

        url = str(http_server.make_url("/echo"))
        bag = Bag()
        bag["echo"] = AuthUrlResolver(url, as_bag=True)
        result = await _drain(bag["echo"])
        assert result["headers"]["Authorization"] == "Bearer dynamic-token"


# =============================================================================
# 6. UrlResolver: process_response override
# =============================================================================


class TestUrlResolverProcessResponse:
    @pytest.mark.asyncio
    async def test_process_response_override_transforms_output(self, http_server):
        """A subclass can transform the response; the resolver returns the
        transformed value."""

        class CountResolver(UrlResolver):
            def process_response(self, response: httpx.Response):
                response.raise_for_status()
                data = response.json()
                return {"echoed_keys": sorted(data.keys())}

        url = str(http_server.make_url("/hello"))
        bag = Bag()
        bag["custom"] = CountResolver(url)
        data = await _drain(bag["custom"])
        assert data == {"echoed_keys": ["hello"]}


# =============================================================================
# 7. UrlResolver: errori HTTP
# =============================================================================


class TestUrlResolverHttpErrors:
    @pytest.mark.asyncio
    async def test_404_raises_http_status_error(self, http_server):
        """A 4xx response raises httpx.HTTPStatusError from the default
        process_response (response.raise_for_status())."""
        url = str(http_server.make_url("/boom"))
        bag = Bag()
        bag["bad"] = UrlResolver(url)
        with pytest.raises(httpx.HTTPStatusError):
            await _drain(bag["bad"])


# =============================================================================
# 8. OpenApiResolver: loads the spec and organizes it by tag
# =============================================================================


class TestOpenApiResolverStructure:
    @pytest.mark.asyncio
    async def test_loads_spec_and_exposes_info_block(self, http_server):
        """result['info'] holds description as value, title/version as attrs."""
        url = str(http_server.make_url("/openapi.json"))
        bag = Bag()
        bag["api"] = OpenApiResolver(url)
        result = await _drain(bag["api"])
        assert isinstance(result, Bag)
        info_node = result.get_node("info")
        assert info_node is not None
        assert info_node.attr.get("title") == "Test API"
        assert info_node.attr.get("version") == "1.0.0"

    @pytest.mark.asyncio
    async def test_paths_grouped_by_tag(self, http_server):
        """result['api'] holds one node per tag; each tag groups its
        operations by operationId."""
        url = str(http_server.make_url("/openapi.json"))
        bag = Bag()
        bag["api"] = OpenApiResolver(url)
        result = await _drain(bag["api"])
        pet_tag = result.get_item("api.pet")
        assert isinstance(pet_tag, Bag)
        op_labels = list(pet_tag.keys())
        assert "listPets" in op_labels
        assert "createPet" in op_labels
        assert "getPet" in op_labels

    @pytest.mark.asyncio
    async def test_operation_bag_has_expected_fields(self, http_server):
        """The operation bag holds path, method and the other metadata."""
        url = str(http_server.make_url("/openapi.json"))
        bag = Bag()
        bag["api"] = OpenApiResolver(url)
        result = await _drain(bag["api"])
        op = result.get_item("api.pet.getPet")
        assert isinstance(op, Bag)
        assert op["path"] == "/pets/{id}"
        assert op["method"] == "get"

    @pytest.mark.asyncio
    async def test_operation_value_is_invocable_url_resolver(self, http_server):
        """The operation bag holds a 'value' node whose resolver is a
        ready-to-call UrlResolver for that endpoint."""
        url = str(http_server.make_url("/openapi.json"))
        bag = Bag()
        bag["api"] = OpenApiResolver(url)
        result = await _drain(bag["api"])
        op = result.get_item("api.pet.getPet")
        assert isinstance(op, Bag)
        # the 'value' node inside the op carries a UrlResolver
        value_node = op.get_node("value")
        assert value_node is not None
        assert isinstance(value_node.resolver, UrlResolver)

    @pytest.mark.asyncio
    async def test_servers_block_exposed(self, http_server):
        """result['servers'] lists the servers declared in the spec."""
        url = str(http_server.make_url("/openapi.json"))
        bag = Bag()
        bag["api"] = OpenApiResolver(url)
        result = await _drain(bag["api"])
        servers = result.get_item("servers")
        assert isinstance(servers, Bag)
        # almeno un server
        assert len(servers) >= 1

    @pytest.mark.asyncio
    async def test_components_block_exposed(self, http_server):
        """result['components'] carries the schemas from the spec."""
        url = str(http_server.make_url("/openapi.json"))
        bag = Bag()
        bag["api"] = OpenApiResolver(url)
        result = await _drain(bag["api"])
        components = result.get_item("components")
        assert isinstance(components, Bag)
