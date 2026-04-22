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

## Resolver in place - API pubblica del resolver ottenuto via bag

Come il BagNode, un resolver non si istanzia da solo nei test e poi si
usa in isolamento: lo si piazza in una Bag (bag['x'] = Resolver(...))
e poi si accede via bag.get_resolver(path). Una volta in place, tutti
i metodi/property pubblici del resolver sono API testabile.

15. property cache_time / interval / reactive / read_only / is_async
16. cached_value getter/setter
17. __eq__ tra resolver             stessa classe + stessi args
18. kw pre-processed (on_loading)
19. container proxy                  resolver['x'], resolver.keys/items/values
"""

from __future__ import annotations

import asyncio

import pytest

from genro_bag import Bag, BagResolver
from genro_bag.resolvers import (
    BagCbResolver,
    DirectoryResolver,
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

    def test_loads_csv_file_as_bag_of_records(self, tmp_path):
        """FileResolver su .csv ritorna una Bag di record con colonne come attr.

        Scenario reale: tabella CSV che viene mount-ata in una sezione di una app.
        """
        file = tmp_path / "contacts.csv"
        file.write_text(
            "name,age\nalice,30\nbob,25\n",
            encoding="utf-8",
        )
        bag = Bag()
        bag["contacts"] = FileResolver(str(file))
        contacts = bag["contacts"]
        assert isinstance(contacts, Bag)
        # due record
        assert len(contacts) == 2

    def test_loads_bag_json_file(self, tmp_path):
        """FileResolver su .bag.json usa TYTX per caricare la Bag.

        Scenario: persistenza Bag-native (type-preserving).
        """
        # preparo il file usando to_tytx della Bag originale
        src = Bag({"a": 1, "b": "hello"})
        src.to_tytx(filename=str(tmp_path / "out"), transport="json")
        # il file creato e' out.bag.json
        bag = Bag()
        bag["data"] = FileResolver(str(tmp_path / "out.bag.json"))
        data = bag["data"]
        assert isinstance(data, Bag)
        assert data.get_item("a") == 1
        assert data.get_item("b") == "hello"

    def test_base_path_resolves_relative_path(self, tmp_path):
        """FileResolver(path, base_path=...) risolve path relativi rispetto a base_path.

        Scenario reale: collezione di asset relativi a una directory di progetto.
        """
        file = tmp_path / "doc.txt"
        file.write_text("content", encoding="utf-8")
        bag = Bag()
        bag["doc"] = FileResolver("doc.txt", base_path=str(tmp_path))
        assert bag["doc"] == "content"


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


# =============================================================================
# 15. Resolver in place - properties (cache_time, interval, reactive,
#     read_only, is_async)
# =============================================================================


class TestResolverInPlaceProperties:
    def test_cache_time_property(self):
        """resolver.cache_time espone il valore di cache_time."""
        bag = Bag()
        bag["c"] = BagCbResolver(lambda: 1, cache_time=60)
        resolver = bag.get_resolver("c")
        assert resolver is not None
        assert resolver.cache_time == 60

    def test_cache_time_false_means_infinite(self):
        """cache_time=False significa cache infinita."""
        bag = Bag()
        bag["c"] = BagCbResolver(lambda: 1, cache_time=False)
        resolver = bag.get_resolver("c")
        assert resolver is not None
        assert resolver.cache_time is False

    def test_interval_default_none(self):
        """Un resolver senza interval ha interval=None."""
        bag = Bag()
        bag["c"] = BagCbResolver(lambda: 1, cache_time=False)
        resolver = bag.get_resolver("c")
        assert resolver is not None
        assert resolver.interval is None

    def test_reactive_default_false(self):
        """reactive default e' False."""
        bag = Bag()
        bag["c"] = BagCbResolver(lambda: 1)
        resolver = bag.get_resolver("c")
        assert resolver is not None
        assert resolver.reactive is False

    def test_reactive_true_when_set(self):
        """reactive=True al construct e' esposta dalla property."""
        bag = Bag()
        bag["c"] = BagCbResolver(lambda: 1, cache_time=False, reactive=True)
        resolver = bag.get_resolver("c")
        assert resolver is not None
        assert resolver.reactive is True

    def test_reactive_setter_mutates(self):
        """reactive setter permette di modificare il flag a runtime."""
        bag = Bag()
        bag["c"] = BagCbResolver(lambda: 1, cache_time=False)
        resolver = bag.get_resolver("c")
        assert resolver is not None
        resolver.reactive = True
        assert resolver.reactive is True

    def test_read_only_derived_true_when_no_cache_no_trigger(self):
        """read_only non esplicito: con cache_time=0 e no interval/reactive e' True.

        Documentato: se non passato esplicito, viene derivato dai settings di
        caching e refresh. Senza cache e senza trigger il resolver e' letto
        ad ogni accesso -> read_only=True (niente scrittura nel nodo).
        """
        bag = Bag()
        bag["c"] = BagCbResolver(lambda: 1)  # cache_time=0 default, no interval
        resolver = bag.get_resolver("c")
        assert resolver is not None
        assert resolver.read_only is True

    def test_read_only_derived_false_with_cache(self):
        """Con cache_time=False (infinita), read_only non esplicito e' False."""
        bag = Bag()
        bag["c"] = BagCbResolver(lambda: 1, cache_time=False)
        resolver = bag.get_resolver("c")
        assert resolver is not None
        assert resolver.read_only is False

    def test_read_only_explicit_false_honored(self):
        """read_only=False esplicito vince sul derived."""
        bag = Bag()
        bag["c"] = BagCbResolver(lambda: 1, read_only=False)
        resolver = bag.get_resolver("c")
        assert resolver is not None
        assert resolver.read_only is False

    def test_read_only_true_when_set(self):
        """read_only=True al construct e' esposta dalla property."""
        bag = Bag()
        bag["c"] = BagCbResolver(lambda: 1, read_only=True)
        resolver = bag.get_resolver("c")
        assert resolver is not None
        assert resolver.read_only is True

    def test_is_async_false_for_sync_callback(self):
        """is_async e' False se il callback e' sync."""
        bag = Bag()
        bag["c"] = BagCbResolver(lambda: 1)
        resolver = bag.get_resolver("c")
        assert resolver is not None
        assert resolver.is_async is False

    def test_is_async_true_for_async_callback(self):
        """is_async e' True se il callback e' una coroutine function."""

        async def async_cb():
            return 1

        bag = Bag()
        bag["c"] = BagCbResolver(async_cb)
        resolver = bag.get_resolver("c")
        assert resolver is not None
        assert resolver.is_async is True


# =============================================================================
# 16. cached_value getter/setter
# =============================================================================


class TestResolverCachedValue:
    def test_cached_value_before_load_is_none(self):
        """cached_value prima di ogni lettura e' None."""
        bag = Bag()
        bag["c"] = BagCbResolver(lambda: "hello", cache_time=False)
        resolver = bag.get_resolver("c")
        assert resolver is not None
        assert resolver.cached_value is None

    def test_cached_value_after_read(self):
        """Dopo una lettura il cached_value riflette il valore."""
        bag = Bag()
        bag["c"] = BagCbResolver(lambda: "hello", cache_time=False)
        _ = bag["c"]
        resolver = bag.get_resolver("c")
        assert resolver is not None
        assert resolver.cached_value == "hello"


# =============================================================================
# 17. __eq__ tra resolver
# =============================================================================


class TestResolverEquality:
    def test_same_class_same_args_equal(self):
        """Due UuidResolver con stessi args sono uguali."""
        assert UuidResolver("uuid4") == UuidResolver("uuid4")

    def test_same_class_different_args_not_equal(self):
        """UuidResolver('uuid4') != UuidResolver('uuid1')."""
        assert UuidResolver("uuid4") != UuidResolver("uuid1")

    def test_different_classes_not_equal(self):
        """Resolver di classi diverse non sono uguali."""
        assert UuidResolver() != EnvResolver("VAR")

    def test_resolver_not_equal_to_non_resolver(self):
        """__eq__ con oggetto non-resolver ritorna False."""
        r = UuidResolver()
        assert (r == "not a resolver") is False
        assert (r == 42) is False


# =============================================================================
# 18. kw pre-processed (on_loading)
# =============================================================================


class TestResolverKw:
    def test_kw_returns_dict_of_parameters(self):
        """resolver.kw e' il dict di parametri (post on_loading)."""
        bag = Bag()
        bag["c"] = BagCbResolver(lambda a, b: a + b, a=1, b=2)
        resolver = bag.get_resolver("c")
        assert resolver is not None
        kw = resolver.kw
        assert isinstance(kw, dict)
        assert kw["a"] == 1
        assert kw["b"] == 2

    def test_on_loading_default_is_identity(self):
        """on_loading default e' identity: kw == input."""
        bag = Bag()
        bag["c"] = BagCbResolver(lambda x: x, x=42)
        resolver = bag.get_resolver("c")
        assert resolver is not None
        # on_loading(dict) ritorna il dict senza modifiche
        kw_copy = dict(resolver.kw)
        assert resolver.on_loading(kw_copy) == kw_copy


# =============================================================================
# 19. Container proxy - resolver['x'], resolver.keys/items/values, get_node
# =============================================================================


class TestResolverContainerProxy:
    def test_resolver_getitem_after_load(self):
        """Dopo load che produce una Bag, resolver['key'] naviga la Bag risultato."""

        def build():
            return {"a": 1, "b": 2}

        bag = Bag()
        # as_bag=True forza la conversione del dict in Bag
        bag["data"] = BagCbResolver(build, cache_time=False, as_bag=True)
        _ = bag["data"]  # trigger load
        resolver = bag.get_resolver("data")
        assert resolver is not None
        assert resolver["a"] == 1
        assert resolver["b"] == 2

    def test_resolver_keys_values_items(self):
        """Il resolver proxy espone keys(), values(), items() della Bag cached."""

        def build():
            return {"a": 1, "b": 2}

        bag = Bag()
        bag["data"] = BagCbResolver(build, cache_time=False, as_bag=True)
        _ = bag["data"]
        resolver = bag.get_resolver("data")
        assert resolver is not None
        assert resolver.keys() == ["a", "b"]
        assert resolver.values() == [1, 2]
        assert resolver.items() == [("a", 1), ("b", 2)]

    def test_resolver_get_node(self):
        """resolver.get_node('key') ritorna il nodo della Bag cached."""

        def build():
            return {"a": 42}

        bag = Bag()
        bag["data"] = BagCbResolver(build, cache_time=False, as_bag=True)
        _ = bag["data"]
        resolver = bag.get_resolver("data")
        assert resolver is not None
        node = resolver.get_node("a")
        # il nodo e' un BagNode valido, con label='a'
        assert node is not None
        assert node.label == "a"
        assert node.value == 42


# =============================================================================
# 20. DirectoryResolver - montaggio lazy di una directory come Bag
# =============================================================================


class TestDirectoryResolverBasics:
    def test_empty_directory_produces_empty_bag(self, tmp_path):
        """Una directory vuota -> Bag vuota."""
        bag = Bag()
        bag["docs"] = DirectoryResolver(str(tmp_path))
        result = bag["docs"]
        assert isinstance(result, Bag)
        assert len(result) == 0

    def test_nonexistent_directory_produces_empty_bag(self, tmp_path):
        """Path inesistente -> Bag vuota (OSError gestito internamente)."""
        bag = Bag()
        bag["docs"] = DirectoryResolver(str(tmp_path / "nonexistent"))
        result = bag["docs"]
        assert isinstance(result, Bag)
        assert len(result) == 0

    def test_directory_with_xml_file(self, tmp_path):
        """Un file .xml in directory produce un nodo con label label_xml."""
        (tmp_path / "config.xml").write_text(
            "<root><x>1</x></root>", encoding="utf-8"
        )
        bag = Bag()
        bag["docs"] = DirectoryResolver(str(tmp_path))
        result = bag["docs"]
        # label default: nome + '_' + ext
        assert "config_xml" in result.keys()

    def test_directory_with_multiple_extensions(self, tmp_path):
        """ext='xml,txt' processa entrambe le estensioni."""
        (tmp_path / "config.xml").write_text("<a>1</a>", encoding="utf-8")
        (tmp_path / "notes.txt").write_text("hello", encoding="utf-8")
        bag = Bag()
        bag["docs"] = DirectoryResolver(str(tmp_path), ext="xml,txt")
        result = bag["docs"]
        assert "config_xml" in result.keys()
        assert "notes_txt" in result.keys()

    def test_subdirectory_becomes_nested_directory_resolver(self, tmp_path):
        """Una sottodir produce un nodo con resolver DirectoryResolver."""
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "inner.xml").write_text("<a/>", encoding="utf-8")
        bag = Bag()
        bag["docs"] = DirectoryResolver(str(tmp_path))
        result = bag["docs"]
        # 'sub' e' presente come nodo
        assert "sub" in result.keys()
        # accedendoci si scatena il resolver e si ottiene la Bag del sub
        sub_bag = result["sub"]
        assert isinstance(sub_bag, Bag)
        assert "inner_xml" in sub_bag.keys()


class TestDirectoryResolverAttributes:
    def test_node_has_standard_attributes(self, tmp_path):
        """Ogni nodo ha file_name, file_ext, rel_path, abs_path, mtime, size."""
        f = tmp_path / "doc.xml"
        f.write_text("<a/>", encoding="utf-8")
        bag = Bag()
        bag["docs"] = DirectoryResolver(str(tmp_path))
        result = bag["docs"]
        attrs = result.get_attr("doc_xml")
        assert attrs["file_name"] == "doc"
        assert attrs["file_ext"] == "xml"
        assert attrs["abs_path"] == str(f)
        assert attrs["size"] > 0

    def test_relocate_builds_rel_path(self, tmp_path):
        """relocate='virtual' prefixa rel_path del nodo."""
        (tmp_path / "doc.xml").write_text("<a/>", encoding="utf-8")
        bag = Bag()
        bag["docs"] = DirectoryResolver(str(tmp_path), "virtual")
        result = bag["docs"]
        assert result.get_attr("doc_xml", "rel_path") == "virtual/doc.xml"

    def test_relocate_propagates_to_subdirectories(self, tmp_path):
        """Il prefix relocate viene propagato alle sottodirectory."""
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "inner.xml").write_text("<a/>", encoding="utf-8")
        bag = Bag()
        bag["docs"] = DirectoryResolver(str(tmp_path), "virtual")
        result = bag["docs"]
        sub_bag = result["sub"]
        # il nodo 'inner_xml' dentro sub ha rel_path 'virtual/sub/inner.xml'
        assert sub_bag.get_attr("inner_xml", "rel_path") == "virtual/sub/inner.xml"


class TestDirectoryResolverVisibility:
    def test_hidden_files_excluded_by_default(self, tmp_path):
        """File con '.' iniziale sono esclusi (invisible=False default)."""
        (tmp_path / ".secret").write_text("x", encoding="utf-8")
        (tmp_path / "visible.xml").write_text("<a/>", encoding="utf-8")
        bag = Bag()
        bag["docs"] = DirectoryResolver(str(tmp_path))
        result = bag["docs"]
        keys = result.keys()
        assert "visible_xml" in keys
        assert ".secret" not in keys
        assert "secret_" not in " ".join(keys)

    def test_invisible_true_includes_hidden_files(self, tmp_path):
        """invisible=True include anche i file '.hidden'."""
        (tmp_path / ".hidden").write_text("x", encoding="utf-8")
        bag = Bag()
        bag["docs"] = DirectoryResolver(str(tmp_path), invisible=True, ext="")
        result = bag["docs"]
        # il file compare tra le key (il label ha forma '.hidden_')
        keys = result.keys()
        # qualcosa con 'hidden' nel nome
        assert any("hidden" in k for k in keys)

    def test_reserved_names_skipped(self, tmp_path):
        """File che iniziano/finiscono con '#' o terminano con '~' vengono saltati."""
        (tmp_path / "#journal").write_text("x", encoding="utf-8")
        (tmp_path / "trailing~").write_text("x", encoding="utf-8")
        (tmp_path / "normal.xml").write_text("<a/>", encoding="utf-8")
        bag = Bag()
        bag["docs"] = DirectoryResolver(str(tmp_path))
        keys = bag["docs"].keys()
        assert keys == ["normal_xml"]


class TestDirectoryResolverFilters:
    def test_include_glob_pattern(self, tmp_path):
        """include='*.xml' filtra solo quelli matchanti."""
        (tmp_path / "a.xml").write_text("<a/>", encoding="utf-8")
        (tmp_path / "b.txt").write_text("x", encoding="utf-8")
        (tmp_path / "c.xml").write_text("<c/>", encoding="utf-8")
        bag = Bag()
        bag["docs"] = DirectoryResolver(
            str(tmp_path), ext="xml,txt", include="*.xml"
        )
        keys = bag["docs"].keys()
        assert "a_xml" in keys
        assert "c_xml" in keys
        assert "b_txt" not in keys

    def test_exclude_glob_pattern(self, tmp_path):
        """exclude='*.bak' esclude i file matchanti."""
        (tmp_path / "a.xml").write_text("<a/>", encoding="utf-8")
        (tmp_path / "old.bak").write_text("old", encoding="utf-8")
        bag = Bag()
        bag["docs"] = DirectoryResolver(
            str(tmp_path), ext="xml,bak", exclude="*.bak"
        )
        keys = bag["docs"].keys()
        assert "a_xml" in keys
        assert "old_bak" not in keys

    def test_callback_filter(self, tmp_path):
        """callback ritorna False per scartare il nodo."""
        (tmp_path / "big.xml").write_text("<a>" + "x" * 500 + "</a>", encoding="utf-8")
        (tmp_path / "small.xml").write_text("<a/>", encoding="utf-8")

        def only_big(nodeattr):
            return nodeattr["size"] > 100

        bag = Bag()
        bag["docs"] = DirectoryResolver(str(tmp_path), callback=only_big)
        keys = bag["docs"].keys()
        assert "big_xml" in keys
        assert "small_xml" not in keys


class TestDirectoryResolverCaption:
    def test_caption_true_auto_generates(self, tmp_path):
        """caption=True genera caption con underscore -> spazi e capitalize."""
        (tmp_path / "my_doc.xml").write_text("<a/>", encoding="utf-8")
        bag = Bag()
        bag["docs"] = DirectoryResolver(str(tmp_path), caption=True)
        result = bag["docs"]
        assert result.get_attr("my_doc_xml", "caption") == "My doc"

    def test_caption_callable_custom(self, tmp_path):
        """caption=callable: il callable riceve il filename e ritorna la caption."""
        (tmp_path / "file.xml").write_text("<a/>", encoding="utf-8")
        bag = Bag()
        bag["docs"] = DirectoryResolver(
            str(tmp_path), caption=lambda name: f"Caption[{name}]"
        )
        result = bag["docs"]
        assert result.get_attr("file_xml", "caption") == "Caption[file]"

    def test_caption_none_omits_attribute(self, tmp_path):
        """caption non impostato: l'attributo 'caption' non c'e'."""
        (tmp_path / "doc.xml").write_text("<a/>", encoding="utf-8")
        bag = Bag()
        bag["docs"] = DirectoryResolver(str(tmp_path))
        result = bag["docs"]
        node = result.get_node("doc_xml")
        assert node is not None
        assert not node.has_attr("caption")


class TestDirectoryResolverDropExt:
    def test_dropext_true_removes_extension_from_label(self, tmp_path):
        """dropext=True: label senza '_ext' suffix."""
        (tmp_path / "doc.xml").write_text("<a/>", encoding="utf-8")
        bag = Bag()
        bag["docs"] = DirectoryResolver(str(tmp_path), dropext=True)
        keys = bag["docs"].keys()
        # label senza _xml
        assert "doc" in keys


class TestDirectoryResolverProcessors:
    def test_custom_processor(self, tmp_path):
        """processors={'ext': fn}: callable personalizzato ritorna il valore."""
        (tmp_path / "data.csv").write_text("a,b,c\n1,2,3", encoding="utf-8")

        def csv_processor(path):
            with open(path) as f:
                return f.read().upper()

        bag = Bag()
        bag["docs"] = DirectoryResolver(
            str(tmp_path), ext="csv", processors={"csv": csv_processor}
        )
        result = bag["docs"]
        # il valore del nodo e' il ritorno del processor
        assert result.get_item("data_csv") == "A,B,C\n1,2,3"

    def test_processor_false_disables_handler(self, tmp_path):
        """processors={'xml': False}: il processor e' disabilitato, usa default."""
        (tmp_path / "doc.xml").write_text("<a/>", encoding="utf-8")
        bag = Bag()
        bag["docs"] = DirectoryResolver(
            str(tmp_path), ext="xml", processors={"xml": False}
        )
        result = bag["docs"]
        # il nodo c'e', ma il valore viene dal processor_default
        assert "doc_xml" in result.keys()


class TestDirectoryResolverExtMapping:
    def test_ext_mapping_colon_syntax(self, tmp_path):
        """ext='dat:xml' mappa l'estensione .dat al processor di xml."""
        (tmp_path / "data.dat").write_text("<a/>", encoding="utf-8")
        bag = Bag()
        bag["docs"] = DirectoryResolver(str(tmp_path), ext="dat:xml")
        result = bag["docs"]
        assert "data_dat" in result.keys()


class TestDirectoryResolverContent:
    def test_xml_file_value_is_lazy_parsed_bag(self, tmp_path):
        """Accedere a un nodo file .xml triggera il parsing e ritorna una Bag."""
        (tmp_path / "doc.xml").write_text("<root><x>42</x></root>", encoding="utf-8")
        bag = Bag()
        bag["docs"] = DirectoryResolver(str(tmp_path))
        result = bag["docs"]
        parsed = result["doc_xml"]
        assert isinstance(parsed, Bag)
        assert parsed.get_item("root.x") == "42"

    def test_txt_file_value_is_lazy_bytes(self, tmp_path):
        """File .txt con ext='txt' produce un nodo con value bytes."""
        (tmp_path / "note.txt").write_text("hello", encoding="utf-8")
        bag = Bag()
        bag["docs"] = DirectoryResolver(str(tmp_path), ext="txt")
        result = bag["docs"]
        content = result["note_txt"]
        assert content == b"hello"


class TestDirectoryResolverLabelSanitization:
    def test_dots_in_filename_replaced_by_underscore(self, tmp_path):
        """Un filename con punti aggiuntivi ha i punti sostituiti da '_' nel label."""
        (tmp_path / "my.v1.xml").write_text("<a/>", encoding="utf-8")
        bag = Bag()
        bag["docs"] = DirectoryResolver(str(tmp_path))
        keys = bag["docs"].keys()
        # il label sostituisce i '.' con '_': "my_v1_xml"
        assert "my_v1_xml" in keys
