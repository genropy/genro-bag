"""Spec test: UrlResolver e OpenApiResolver.

Test end-to-end che usano un server HTTP locale (aiohttp) come finto
endpoint. Nessuna dipendenza da rete esterna: il server gira su
127.0.0.1 con porta effimera, viene avviato per ogni test e smontato
alla fine.

Filosofia:
- test spec (non test di implementazione): verifichiamo il contratto
  osservabile via API pubblica (Bag + resolver instance)
- niente mock di httpx/aiohttp: la richiesta HTTP avviene davvero,
  attraverso il loopback locale
- i resolver sono async nel core, quindi i test sono marcati
  @pytest.mark.asyncio e il risultato di bag[path] viene awaited

Scala:
1.  UrlResolver GET base + as_bag=True
2.  UrlResolver query string da costruttore, da kwargs e da Bag
3.  UrlResolver path substitution ({id} -> arg_0)
4.  UrlResolver POST con body Bag -> json
5.  UrlResolver headers da prepare_headers() (subclass hook)
6.  UrlResolver process_response override (subclass hook)
7.  UrlResolver 4xx solleva HTTPStatusError
8.  UrlResolver qs con valori None viene filtrato
9.  OpenApiResolver carica una spec minimale e la struttura per tag
10. OpenApiResolver info/servers/components
11. OpenApiResolver operation bag contiene path, method, value (UrlResolver)
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import httpx
import pytest
import pytest_asyncio
from aiohttp import web
from aiohttp.test_utils import TestServer

from genro_bag import Bag
from genro_bag.resolvers import OpenApiResolver, UrlResolver


# =============================================================================
# Fixtures
# =============================================================================


async def _drain(value):
    """Utility: await ripetuto finche' il risultato non e' piu' una coroutine."""
    while asyncio.iscoroutine(value):
        value = await value
    return value


# A minimal OpenAPI 3.0 spec used for the OpenApiResolver tests.
MINIMAL_OPENAPI_SPEC = {
    "openapi": "3.0.0",
    "info": {
        "title": "Test API",
        "version": "1.0.0",
        "description": "Spec used for spec tests",
    },
    "servers": [{"url": "http://127.0.0.1:0", "description": "local"}],
    "paths": {
        "/pets": {
            "get": {
                "tags": ["pet"],
                "operationId": "listPets",
                "summary": "List all pets",
                "parameters": [
                    {"name": "limit", "in": "query", "schema": {"type": "integer"}},
                ],
                "responses": {"200": {"description": "OK"}},
            },
            "post": {
                "tags": ["pet"],
                "operationId": "createPet",
                "summary": "Create a pet",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {"type": "object"},
                        },
                    },
                },
                "responses": {"201": {"description": "Created"}},
            },
        },
        "/pets/{id}": {
            "get": {
                "tags": ["pet"],
                "operationId": "getPet",
                "summary": "Get pet by id",
                "parameters": [
                    {"name": "id", "in": "path", "required": True,
                     "schema": {"type": "integer"}},
                ],
                "responses": {"200": {"description": "OK"}},
            },
        },
        "/users": {
            "get": {
                "tags": ["user"],
                "operationId": "listUsers",
                "summary": "List all users",
                "responses": {"200": {"description": "OK"}},
            },
        },
    },
    "components": {
        "schemas": {
            "Pet": {
                "type": "object",
                "properties": {"id": {"type": "integer"}, "name": {"type": "string"}},
            },
        },
    },
}


def _build_app() -> web.Application:
    """Create the aiohttp application with endpoints needed by the tests."""

    async def hello(request):
        return web.json_response({"hello": "world"})

    async def echo(request):
        return web.json_response({
            "method": request.method,
            "query": dict(request.query),
            "headers": dict(request.headers),
        })

    async def echo_body(request):
        try:
            body = await request.json()
        except Exception:
            body = None
        return web.json_response({"received": body})

    async def pet_by_id(request):
        pet_id = request.match_info["id"]
        return web.json_response({"id": pet_id, "name": f"pet-{pet_id}"})

    async def boom(request):
        return web.Response(status=404, text="not found")

    async def raw_bytes(request):
        return web.Response(
            body=b"plain-bytes",
            content_type="application/octet-stream",
        )

    async def openapi_spec(request):
        return web.json_response(MINIMAL_OPENAPI_SPEC)

    app = web.Application()
    app.router.add_get("/hello", hello)
    app.router.add_get("/echo", echo)
    app.router.add_post("/echo_body", echo_body)
    app.router.add_get("/pets/{id}", pet_by_id)
    app.router.add_get("/boom", boom)
    app.router.add_get("/raw", raw_bytes)
    app.router.add_get("/openapi.json", openapi_spec)
    return app


@pytest_asyncio.fixture
async def http_server() -> AsyncIterator[TestServer]:
    """Spin up a local aiohttp TestServer for the test duration.

    Exposes the following endpoints:
        GET  /hello        -> {"hello": "world"}
        GET  /echo         -> echoes method, query, headers
        POST /echo_body    -> echoes posted JSON body
        GET  /pets/{id}    -> {"id": "<id>", "name": "pet-<id>"}
        GET  /boom         -> 404
        GET  /raw          -> binary bytes
        GET  /openapi.json -> OpenAPI 3.0 spec (MINIMAL_OPENAPI_SPEC)
    """
    server = TestServer(_build_app())
    await server.start_server()
    try:
        yield server
    finally:
        await server.close()


# =============================================================================
# 1. UrlResolver: GET base + as_bag=True
# =============================================================================


class TestUrlResolverGet:
    @pytest.mark.asyncio
    async def test_get_as_bag_parses_json_response(self, http_server):
        """UrlResolver(..., as_bag=True) su un JSON endpoint produce una Bag
        navigabile per chiavi."""
        url = str(http_server.make_url("/hello"))
        bag = Bag()
        bag["data"] = UrlResolver(url, as_bag=True)
        data = await _drain(bag["data"])
        assert isinstance(data, Bag)
        assert data["hello"] == "world"

    @pytest.mark.asyncio
    async def test_get_without_as_bag_returns_raw_bytes(self, http_server):
        """Senza as_bag=True il resolver ritorna il contenuto grezzo (bytes)."""
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
        """qs={...} nel costruttore viene passato come query string."""
        url = str(http_server.make_url("/echo"))
        bag = Bag()
        bag["echo"] = UrlResolver(url, qs={"page": 1, "limit": 10}, as_bag=True)
        result = await _drain(bag["echo"])
        assert result["query.page"] == "1"
        assert result["query.limit"] == "10"

    @pytest.mark.asyncio
    async def test_query_string_from_extra_constructor_kwargs(self, http_server):
        """kwargs extra passati al costruttore (fuori da class_kwargs) vengono
        usati come query string dinamica."""
        url = str(http_server.make_url("/echo"))
        bag = Bag()
        bag["echo"] = UrlResolver(url, as_bag=True, cache_time=0, foo="bar")
        result = await _drain(bag["echo"])
        assert result["query.foo"] == "bar"

    @pytest.mark.asyncio
    async def test_query_string_from_set_attr(self, http_server):
        """set_attr su un parametro dinamico aggiorna la query string."""
        url = str(http_server.make_url("/echo"))
        bag = Bag()
        # foo dichiarato come attributo dinamico con valore iniziale None
        bag["echo"] = UrlResolver(url, as_bag=True, cache_time=0, foo=None)
        bag.set_attr("echo", foo="changed")
        result = await _drain(bag["echo"])
        assert result["query.foo"] == "changed"

    @pytest.mark.asyncio
    async def test_query_string_none_values_are_filtered(self, http_server):
        """qs con valori None viene filtrato: la chiave non compare nell'URL."""
        url = str(http_server.make_url("/echo"))
        bag = Bag()
        bag["echo"] = UrlResolver(
            url, qs={"keep": "yes", "drop": None}, as_bag=True,
        )
        result = await _drain(bag["echo"])
        assert result["query.keep"] == "yes"
        assert "drop" not in result["query"].keys()

    @pytest.mark.asyncio
    async def test_query_string_from_bag(self, http_server):
        """qs accetta anche una Bag: chiavi/valori vengono serializzati."""
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
        """URL con '{id}' viene sostituito usando arg_0 come parametro dinamico."""
        # Costruisco l'URL senza URL-encoding di '{id}' (aiohttp lo encodifica)
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
        """method='post' + body=Bag: il body viene serializzato come json."""
        url = str(http_server.make_url("/echo_body"))
        body = Bag({"name": "alice", "age": 30})
        bag = Bag()
        bag["out"] = UrlResolver(url, method="post", body=body, as_bag=True)
        result = await _drain(bag["out"])
        assert result["received.name"] == "alice"
        assert result["received.age"] == 30

    @pytest.mark.asyncio
    async def test_post_body_overridable_via_underscore_body(self, http_server):
        """_body impostato via set_attr sovrascrive il body del costruttore.

        Il parametro '_body' del UrlResolver, quando presente fra gli
        attributi del nodo, ha priorita' sul body originale del costruttore.
        """
        url = str(http_server.make_url("/echo_body"))
        bag = Bag()
        # dichiaro _body come parametro dinamico del nodo
        bag["out"] = UrlResolver(
            url, method="post", body={"orig": 1}, as_bag=True,
            cache_time=0, _body=None,
        )
        bag.set_attr("out", _body={"override": True})
        result = await _drain(bag["out"])
        assert result["received.override"] is True
        assert "orig" not in result["received"].keys()


# =============================================================================
# 5. UrlResolver: headers via subclass hook
# =============================================================================


class TestUrlResolverHeaders:
    @pytest.mark.asyncio
    async def test_static_headers_sent_on_request(self, http_server):
        """headers={} nel costruttore vengono inviati con la richiesta."""
        url = str(http_server.make_url("/echo"))
        bag = Bag()
        bag["echo"] = UrlResolver(
            url, as_bag=True, headers={"X-Test-Token": "abc123"},
        )
        result = await _drain(bag["echo"])
        assert result["headers"]["X-Test-Token"] == "abc123"

    @pytest.mark.asyncio
    async def test_prepare_headers_hook_adds_dynamic_headers(self, http_server):
        """Override di prepare_headers aggiunge headers dinamici."""

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
        """Una subclass puo' trasformare la response; il valore restituito
        dal resolver riflette la trasformazione."""

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
        """Una risposta 4xx solleva httpx.HTTPStatusError dal process_response
        di default (response.raise_for_status())."""
        url = str(http_server.make_url("/boom"))
        bag = Bag()
        bag["bad"] = UrlResolver(url)
        with pytest.raises(httpx.HTTPStatusError):
            await _drain(bag["bad"])


# =============================================================================
# 8. OpenApiResolver: carica spec e organizza per tag
# =============================================================================


class TestOpenApiResolverStructure:
    @pytest.mark.asyncio
    async def test_loads_spec_and_exposes_info_block(self, http_server):
        """result['info'] presenta description come value e title/version come attr."""
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
        """result['api'] contiene un nodo per ogni tag; ogni tag raggruppa
        le operazioni per operationId."""
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
        """L'operation bag contiene path, method e altri metadati."""
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
        """L'operation bag contiene un nodo 'value' che ha come resolver
        un UrlResolver pronto all'uso per invocare l'endpoint."""
        url = str(http_server.make_url("/openapi.json"))
        bag = Bag()
        bag["api"] = OpenApiResolver(url)
        result = await _drain(bag["api"])
        op = result.get_item("api.pet.getPet")
        assert isinstance(op, Bag)
        # il nodo 'value' dentro l'op ha un UrlResolver come resolver
        value_node = op.get_node("value")
        assert value_node is not None
        assert isinstance(value_node.resolver, UrlResolver)

    @pytest.mark.asyncio
    async def test_servers_block_exposed(self, http_server):
        """result['servers'] contiene la lista dei server definiti nella spec."""
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
        """result['components'] riporta gli schemi dalla spec."""
        url = str(http_server.make_url("/openapi.json"))
        bag = Bag()
        bag["api"] = OpenApiResolver(url)
        result = await _drain(bag["api"])
        components = result.get_item("components")
        assert isinstance(components, Bag)
