"""Spec test: the ``?attr`` syntax resolves BagResolvers held as
attributes (issue #60), and bare ``?`` returns all attributes as
a dict with resolvers resolved (issue #61).

Depends on test_basic.py (set_item) and test_resolvers.py (EnvResolver).

Contract:
- ``bag['n?key']``: if ``key`` is a BagResolver and ``static=False``,
  returns the resolved value. Otherwise the raw attribute.
- ``bag['n?a&b']``: tuple of values (resolved for resolvers, raw for
  others).
- ``bag['n?']`` (bare): dict ``{name: value}`` with ALL attributes;
  resolvers are resolved.
- ``static=True``: does not trigger any resolver in any form;
  returns the raw ``BagResolver`` object.

## Scale

### #60 (named form resolves resolvers)
1. ?attr single with resolver           resolved value
2. ?attr single with plain value        unchanged
3. ?a&b mixed                           mixed tuple resolved/plain
4. ?a&b two resolvers                   tuple with both resolved
5. ?attr non-existent                   None (unchanged)

### #61 (bare ? dict)
6. bag['n?'] mixed                      dict with resolvers resolved
7. bag['n?'] no attributes              {}
8. bag['n?'] only resolvers             dict of resolved values
9. bag['n?'] preserves insertion order  dict sanity check

### static=True
10. static=True on ?key                 BagResolver object, not called
11. static=True on ? bare               dict with raw resolvers
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
# 6-9. #61: bare ? returns a dict with the resolvers resolved
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
# 10-11. static=True does not trigger the resolvers
# =============================================================================


class TestStaticNamedForm:
    def test_static_true_returns_raw_resolver_object_for_named(self, monkeypatch):
        monkeypatch.setenv("X_SECRET", "secret")
        b = Bag()
        b.set_item("n", "v", key=EnvResolver("X_SECRET"))
        node = b.get_node("n")
        result = node.get_value(static=True, _query_string="key")
        # with static=True the resolver object is not called
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


