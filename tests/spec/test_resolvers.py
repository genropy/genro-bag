"""Spec test: Bag - resolver (valori calcolati lazy).

Dipende da test_basic.py (set_item, get_item, get_attr, set_attr,
set_callback_item, set_resolver, get_resolver, get_node).

I resolver sono oggetti pubblici: l'utente li istanzia e li passa alla
Bag come valore. Il test li esercita PRINCIPALMENTE attraverso la Bag
(bag['path'] triggera il load). Solo per aspetti che riguardano
esclusivamente la vita del resolver (reset, expired, serialize) il test
chiama direttamente i metodi pubblici del resolver stesso.

## Scala

1.  UuidResolver              generatore di id univoci, cache_time=False
2.  EnvResolver               env var + default
3.  BagCbResolver sync        callback sync con kwargs
4.  BagCbResolver con cache   cache_time > 0
5.  BagCbResolver async       callback coroutine (smartawait)
6.  FileResolver              filesystem, formati txt/json/csv
7.  node.attr vs resolver._kw priorita' parametri
8.  static=True               lettura senza trigger
9.  reset / expired           invalidation manuale
10. read_only                 non salva il valore nel nodo
11. cache_time < 0            errore in __init__
12. serialize roundtrip       serializzazione resolver
13. get_resolver / set_resolver  accessori del nodo
14. UrlResolver               network (marker)
"""

from __future__ import annotations

import asyncio

import pytest

from genro_bag import Bag, BagResolver
from genro_bag.resolvers import (
    BagCbResolver,
    EnvResolver,
    FileResolver,
    UrlResolver,
    UuidResolver,
)


# =============================================================================
# 1. UuidResolver
# =============================================================================


class TestUuidResolver:
    def test_generates_string(self):
        """bag['id'] con UuidResolver produce una stringa non vuota."""
        bag = Bag()
        bag["id"] = UuidResolver()
        value = bag["id"]
        assert isinstance(value, str)
        assert len(value) > 0

    def test_cached_by_default(self):
        """Con cache_time=False (default) due letture ritornano lo stesso UUID."""
        bag = Bag()
        bag["id"] = UuidResolver()
        first = bag["id"]
        second = bag["id"]
        assert first == second

    def test_version_uuid1(self):
        """UuidResolver('uuid1') genera un UUID di tipo uuid1."""
        bag = Bag()
        bag["id"] = UuidResolver("uuid1")
        value = bag["id"]
        assert isinstance(value, str)
        # UUID1 ha versione '1' nel terzo gruppo (es. xxxxxxxx-xxxx-1xxx-...)
        assert value[14] == "1"

    def test_unsupported_version_raises_on_load(self):
        """Una versione sconosciuta solleva ValueError al primo accesso."""
        bag = Bag()
        bag["id"] = UuidResolver("uuid99")
        with pytest.raises(ValueError):
            _ = bag["id"]


# =============================================================================
# 2. EnvResolver
# =============================================================================


class TestEnvResolver:
    def test_reads_env_variable(self, monkeypatch: pytest.MonkeyPatch):
        """EnvResolver legge una variabile d'ambiente esistente."""
        monkeypatch.setenv("GENRO_BAG_TEST_VAR", "hello")
        bag = Bag()
        bag["v"] = EnvResolver("GENRO_BAG_TEST_VAR")
        assert bag["v"] == "hello"

    def test_returns_default_if_unset(self, monkeypatch: pytest.MonkeyPatch):
        """Se la variabile non esiste ritorna default."""
        monkeypatch.delenv("GENRO_BAG_MISSING_VAR", raising=False)
        bag = Bag()
        bag["v"] = EnvResolver("GENRO_BAG_MISSING_VAR", default="fallback")
        assert bag["v"] == "fallback"

    def test_reflects_runtime_changes_without_cache(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """cache_time=0 (default): ogni accesso rilegge l'env."""
        monkeypatch.setenv("GENRO_BAG_VAR_B", "first")
        bag = Bag()
        bag["v"] = EnvResolver("GENRO_BAG_VAR_B")
        assert bag["v"] == "first"
        monkeypatch.setenv("GENRO_BAG_VAR_B", "second")
        assert bag["v"] == "second"


# =============================================================================
# 3. BagCbResolver (sync)
# =============================================================================


class TestBagCbResolverSync:
    def test_calls_callback_sync(self):
        """bag['calc'] triggera il callback alla prima lettura."""
        bag = Bag()
        bag["calc"] = BagCbResolver(lambda: 42)
        assert bag["calc"] == 42

    def test_callback_kwargs_passed_through(self):
        """I kwargs del resolver vengono passati al callback."""
        def add(a, b):
            return a + b

        bag = Bag()
        bag["sum"] = BagCbResolver(add, a=3, b=5)
        assert bag["sum"] == 8

    def test_set_callback_item_shortcut(self):
        """set_callback_item e' una shortcut per BagCbResolver."""
        bag = Bag()
        bag.set_callback_item("now", lambda: "fixed")
        assert bag["now"] == "fixed"


# =============================================================================
# 4. BagCbResolver con cache
# =============================================================================


class TestBagCbResolverCache:
    def test_cache_time_zero_recomputes(self):
        """cache_time=0: ogni accesso richiama il callback."""
        counter = {"n": 0}

        def cb():
            counter["n"] += 1
            return counter["n"]

        bag = Bag()
        bag["c"] = BagCbResolver(cb)  # cache_time=0 default
        assert bag["c"] == 1
        assert bag["c"] == 2
        assert bag["c"] == 3

    def test_cache_time_infinite(self):
        """cache_time=False: il valore resta stabile dopo il primo load."""
        counter = {"n": 0}

        def cb():
            counter["n"] += 1
            return counter["n"]

        bag = Bag()
        bag["c"] = BagCbResolver(cb, cache_time=False)
        assert bag["c"] == 1
        assert bag["c"] == 1
        assert bag["c"] == 1


# =============================================================================
# 5. BagCbResolver async
# =============================================================================


class TestBagCbResolverAsync:
    @pytest.mark.asyncio
    async def test_async_callback_awaited_in_async_context(self):
        """Callback async: bag[path] ritorna una coroutine in contesto async."""

        async def async_cb():
            return "async-value"

        bag = Bag()
        bag["a"] = BagCbResolver(async_cb)
        result = bag["a"]
        if asyncio.iscoroutine(result):
            result = await result
        assert result == "async-value"

    @pytest.mark.asyncio
    async def test_async_callback_with_kwargs(self):
        """Il callback async riceve i kwargs definiti."""

        async def async_add(x, y):
            return x + y

        bag = Bag()
        bag["s"] = BagCbResolver(async_add, x=10, y=32)
        result = bag["s"]
        if asyncio.iscoroutine(result):
            result = await result
        assert result == 42


# =============================================================================
# 6. FileResolver
# =============================================================================


class TestFileResolver:
    def test_loads_text_file(self, tmp_path):
        """FileResolver legge un .txt come stringa."""
        file = tmp_path / "doc.txt"
        file.write_text("hello world", encoding="utf-8")
        bag = Bag()
        bag["doc"] = FileResolver(str(file))
        assert bag["doc"] == "hello world"

    def test_loads_json_file(self, tmp_path):
        """FileResolver su .json ritorna un dict/list parsato."""
        file = tmp_path / "data.json"
        file.write_text('{"a": 1, "b": 2}', encoding="utf-8")
        bag = Bag()
        bag["data"] = FileResolver(str(file))
        result = bag["data"]
        # senza as_bag=True resta dict (read_only=True forza no-conversion)
        assert result == {"a": 1, "b": 2}

    def test_as_bag_true_converts_to_bag(self, tmp_path):
        """FileResolver con as_bag=True converte il JSON in Bag navigabile."""
        file = tmp_path / "data.json"
        file.write_text('{"a": 1, "b": 2}', encoding="utf-8")
        bag = Bag()
        bag["data"] = FileResolver(str(file), as_bag=True)
        data = bag["data"]
        assert isinstance(data, Bag)
        assert data.get_item("a") == 1

    def test_missing_file_raises(self, tmp_path):
        """Un file inesistente fa sollevare FileNotFoundError al primo accesso."""
        bag = Bag()
        bag["doc"] = FileResolver(str(tmp_path / "missing.txt"))
        with pytest.raises(FileNotFoundError):
            _ = bag["doc"]


# =============================================================================
# 7. Priorita' node.attr vs resolver._kw
# =============================================================================


class TestParameterPriority:
    def test_resolver_kw_used_by_default(self):
        """Se node.attr non e' settato, il resolver usa i suoi defaults (_kw)."""
        bag = Bag()
        bag["x"] = BagCbResolver(lambda a: a * 2, a=5)
        assert bag["x"] == 10

    def test_node_attr_overrides_resolver_kw(self):
        """set_attr sul path sovrascrive il default del resolver."""
        bag = Bag()
        bag["x"] = BagCbResolver(lambda a: a * 2, a=5, cache_time=0)
        assert bag["x"] == 10
        bag.set_attr("x", a=50)
        assert bag["x"] == 100

    def test_call_kwargs_update_node_attr(self):
        """get_item(path, **kw) scrive i kwargs in node.attr e poi invoca load."""
        bag = Bag()
        bag["x"] = BagCbResolver(lambda a: a * 3, a=1, cache_time=0)
        result = bag.get_item("x", a=7)
        assert result == 21
        # il nuovo valore resta in node.attr
        assert bag.get_attr("x", "a") == 7


# =============================================================================
# 8. static=True (no trigger del resolver)
# =============================================================================


class TestStaticAccess:
    def test_static_true_returns_cached_without_loading(self):
        """get_item(path, static=True) non triggera il resolver."""
        calls = {"n": 0}

        def cb():
            calls["n"] += 1
            return "value"

        bag = Bag()
        bag["v"] = BagCbResolver(cb, cache_time=False)
        # prima lettura lazy triggera load
        bag["v"]
        assert calls["n"] == 1
        # static=True rilegge senza richiamare cb
        cached = bag.get_item("v", static=True)
        assert cached == "value"
        assert calls["n"] == 1

    def test_static_before_any_load_returns_none(self):
        """static=True prima di qualunque load ritorna il valore cached (None)."""
        bag = Bag()
        bag["v"] = BagCbResolver(lambda: "hello", cache_time=False)
        assert bag.get_item("v", static=True) is None


# =============================================================================
# 9. reset / expired
# =============================================================================


class TestResetAndExpired:
    def test_reset_forces_reload_next_access(self):
        """reset() (refresh=False) invalida la cache: il prossimo accesso ricarica."""
        counter = {"n": 0}

        def cb():
            counter["n"] += 1
            return counter["n"]

        bag = Bag()
        bag["c"] = BagCbResolver(cb, cache_time=False)
        assert bag["c"] == 1
        assert bag["c"] == 1  # cached
        resolver = bag.get_resolver("c")
        resolver.reset()
        assert bag["c"] == 2  # ricaricato

    def test_expired_false_when_cache_infinite_and_loaded(self):
        """Con cache_time=False e gia' caricato, expired e' False."""
        bag = Bag()
        bag["c"] = BagCbResolver(lambda: 1, cache_time=False)
        bag["c"]  # trigger
        assert bag.get_resolver("c").expired is False

    def test_expired_true_when_cache_time_zero(self):
        """Con cache_time=0 expired e' sempre True (nessuna cache)."""
        bag = Bag()
        bag["c"] = BagCbResolver(lambda: 1, cache_time=0)
        assert bag.get_resolver("c").expired is True


# =============================================================================
# 10. read_only
# =============================================================================


class TestReadOnly:
    def test_read_only_does_not_store_in_node(self):
        """read_only=True: il valore NON viene salvato come static_value."""
        counter = {"n": 0}

        def cb():
            counter["n"] += 1
            return counter["n"]

        bag = Bag()
        bag["c"] = BagCbResolver(cb, read_only=True)
        assert bag["c"] == 1
        # static=True legge il valore nel nodo, che non e' stato scritto
        assert bag.get_item("c", static=True) is None
        # dato che read_only non memorizza, ogni lettura non-static richiama cb
        assert bag["c"] == 2


# =============================================================================
# 11. Errori di costruzione
# =============================================================================


class TestConstructionErrors:
    def test_negative_cache_time_rejected(self):
        """cache_time negativo non e' piu' supportato: solleva ValueError."""
        with pytest.raises(ValueError):
            BagCbResolver(lambda: 1, cache_time=-10)

    def test_read_only_with_interval_rejected(self):
        """read_only=True + interval solleva ValueError."""
        with pytest.raises(ValueError):
            BagCbResolver(lambda: 1, read_only=True, interval=5)

    def test_read_only_with_reactive_rejected(self):
        """read_only=True + reactive=True solleva ValueError."""
        with pytest.raises(ValueError):
            BagCbResolver(lambda: 1, read_only=True, reactive=True)


# =============================================================================
# 12. serialize / deserialize
# =============================================================================


class TestSerialize:
    def test_serialize_roundtrip_preserves_class_and_args(self):
        """BagResolver.deserialize(resolver.serialize()) ricostruisce il resolver."""
        original = UuidResolver("uuid4")
        data = original.serialize()
        assert isinstance(data, dict)
        rebuilt = BagResolver.deserialize(data)
        assert isinstance(rebuilt, UuidResolver)
        assert rebuilt == original


# =============================================================================
# 13. get_resolver / set_resolver
# =============================================================================


class TestResolverAccessors:
    def test_get_resolver_returns_resolver(self):
        """get_resolver(path) ritorna l'istanza resolver del nodo."""
        bag = Bag()
        r = UuidResolver()
        bag["id"] = r
        assert bag.get_resolver("id") is r

    def test_get_resolver_none_on_plain_node(self):
        """get_resolver ritorna None per un nodo senza resolver."""
        bag = Bag()
        bag["x"] = 42
        assert bag.get_resolver("x") is None

    def test_get_resolver_none_on_missing_path(self):
        """get_resolver ritorna None se il path non esiste."""
        assert Bag().get_resolver("missing") is None

    def test_set_resolver_creates_node_with_resolver(self):
        """set_resolver(path, resolver) crea un nodo con quel resolver."""
        bag = Bag()
        r = UuidResolver()
        bag.set_resolver("id", r)
        assert bag.get_resolver("id") is r


# =============================================================================
# 14. UrlResolver (network - smoke)
# =============================================================================


class TestUrlResolver:
    @pytest.mark.network
    def test_fetches_url_content(self):
        """UrlResolver su endpoint pubblico ritorna il contenuto."""
        bag = Bag()
        bag["remote"] = UrlResolver("https://httpbin.org/json")
        value = bag["remote"]
        # httpbin.org/json ritorna un oggetto; as_bag default converte a Bag se non read_only
        assert value is not None
