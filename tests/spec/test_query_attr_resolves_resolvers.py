"""Spec test: la sintassi ``?attr`` risolve i BagResolver tenuti come
attributi (issue #60), e il bare ``?`` ritorna tutti gli attributi come
dict con i resolver risolti (issue #61).

Dipende da test_basic.py (set_item) e test_resolvers.py (EnvResolver).

Contratto:
- ``bag['n?key']``: se ``key`` e' un BagResolver e ``static=False``,
  restituisce il valore risolto. Altrimenti l'attributo grezzo.
- ``bag['n?a&b']``: tupla di valori (risolti per i resolver, grezzi per
  gli altri).
- ``bag['n?']`` (bare): dict ``{name: value}`` con TUTTI gli attributi;
  i resolver vengono risolti.
- ``static=True``: non triggera alcun resolver in nessuna delle forme;
  restituisce l'oggetto ``BagResolver`` grezzo.

## Scala

### #60 (named form risolve i resolver)
1. ?attr singolo con resolver           valore risolto
2. ?attr singolo con valore piano       invariato
3. ?a&b misto                           tupla mista risolto/piano
4. ?a&b due resolver                    tupla con entrambi risolti
5. ?attr inesistente                    None (invariato)

### #61 (bare ? dict)
6. bag['n?'] misti                      dict con resolver risolti
7. bag['n?'] senza attributi            {}
8. bag['n?'] solo resolver              dict di valori risolti
9. bag['n?'] preserva insertion order   sanity check dict

### static=True
10. static=True su ?key                 oggetto BagResolver, non chiamato
11. static=True su ? bare               dict con resolver grezzi
"""

from __future__ import annotations

from genro_bag import Bag
from genro_bag.resolvers import EnvResolver

# =============================================================================
# 1-5. #60: named form risolve i resolver
# =============================================================================


class TestQueryAttrResolvesSingleResolver:
    def test_single_attr_resolver_returns_resolved_value(self, monkeypatch):
        monkeypatch.setenv("X_SECRET", "secret")
        b = Bag()
        b.set_item("n", "v", key=EnvResolver("X_SECRET"))
        assert b["n?key"] == "secret"


class TestQueryAttrPlainValueUnchanged:
    def test_single_attr_plain_value_returns_as_is(self):
        b = Bag()
        b.set_item("n", "v", plain="hello")
        assert b["n?plain"] == "hello"


class TestQueryAttrMixedResolverAndPlain:
    def test_a_and_b_returns_tuple_with_resolved_and_plain(self, monkeypatch):
        monkeypatch.setenv("X_SECRET", "secret")
        b = Bag()
        b.set_item("n", "v", key=EnvResolver("X_SECRET"), plain="x")
        assert b["n?key&plain"] == ("secret", "x")


class TestQueryAttrBothResolvers:
    def test_a_and_b_returns_tuple_with_both_resolved(self, monkeypatch):
        monkeypatch.setenv("X_A", "alpha")
        monkeypatch.setenv("X_B", "beta")
        b = Bag()
        b.set_item("n", "v", a=EnvResolver("X_A"), b=EnvResolver("X_B"))
        assert b["n?a&b"] == ("alpha", "beta")


class TestQueryAttrMissing:
    def test_missing_attr_returns_none(self):
        b = Bag()
        b.set_item("n", "v", present="p")
        assert b["n?missing"] is None


# =============================================================================
# 6-9. #61: bare ? ritorna dict con resolver risolti
# =============================================================================


class TestBareQueryReturnsDictWithMixedAttrs:
    def test_bare_query_returns_dict_resolving_resolvers(self, monkeypatch):
        monkeypatch.setenv("X_SECRET", "secret")
        b = Bag()
        b.set_item("n", "v", key=EnvResolver("X_SECRET"), plain="x")
        assert b["n?"] == {"key": "secret", "plain": "x"}


class TestBareQueryEmptyAttrs:
    def test_bare_query_on_node_without_attrs_returns_empty_dict(self):
        b = Bag()
        b.set_item("n", "v")
        assert b["n?"] == {}


class TestBareQueryOnlyResolvers:
    def test_bare_query_all_resolvers_returns_all_resolved(self, monkeypatch):
        monkeypatch.setenv("X_A", "alpha")
        monkeypatch.setenv("X_B", "beta")
        b = Bag()
        b.set_item("n", "v", a=EnvResolver("X_A"), b=EnvResolver("X_B"))
        assert b["n?"] == {"a": "alpha", "b": "beta"}


class TestBareQueryPreservesInsertionOrder:
    def test_bare_query_dict_preserves_insertion_order(self):
        b = Bag()
        b.set_item("n", "v", first=1, second=2, third=3)
        result = b["n?"]
        assert list(result.keys()) == ["first", "second", "third"]


# =============================================================================
# 10-11. static=True non triggera i resolver
# =============================================================================


class TestStaticNamedForm:
    def test_static_true_returns_raw_resolver_object_for_named(self, monkeypatch):
        monkeypatch.setenv("X_SECRET", "secret")
        b = Bag()
        b.set_item("n", "v", key=EnvResolver("X_SECRET"))
        node = b.get_node("n")
        result = node.get_value(static=True, _query_string="key")
        # con static=True l'oggetto resolver non viene chiamato
        assert isinstance(result, EnvResolver)


class TestStaticBareForm:
    def test_static_true_returns_dict_with_raw_resolvers_for_bare(self, monkeypatch):
        monkeypatch.setenv("X_SECRET", "secret")
        b = Bag()
        b.set_item("n", "v", key=EnvResolver("X_SECRET"), plain="x")
        node = b.get_node("n")
        result = node.get_value(static=True, _query_string="")
        assert isinstance(result, dict)
        assert set(result.keys()) == {"key", "plain"}
        assert isinstance(result["key"], EnvResolver)
        assert result["plain"] == "x"


