"""Spec test: ``Bag.__contains__`` (operatore ``in``) deve essere
una pura check di esistenza, statica e con supporto della sintassi
``?attr`` come gli altri metodi di lettura.

Dipende da test_basic.py (set_item) e test_resolvers.py (resolver).

Contratto:
- ``"a.b" in bag`` ritorna True se il path esiste, False altrimenti.
- ``"a.b?color" in bag`` ritorna True se il nodo a.b esiste E ha
  l'attributo ``color``. False se manca il path o l'attributo.
- ``"a.b?a1&a2" in bag`` ritorna True solo se TUTTI gli attributi
  esistono sul nodo. (Convenzione uniforme con get.)
- ``in`` e' statico: non triggera resolver lungo il path.

## Scala

1. path esistente                       True
2. path inesistente                     False
3. ?attr esistente                      True
4. ?attr inesistente                    False
5. ?a&b: tutti esistenti                True
6. ?a&b: uno manca                      False
7. ?attr su path inesistente            False
8. in NON triggera resolver             load non chiamato
"""

from __future__ import annotations

from genro_bag import Bag
from genro_bag.resolver import BagSyncResolver

# =============================================================================
# 1-2. esistenza di un path
# =============================================================================


class TestContainsPath:
    def test_existing_path_returns_true(self):
        b = Bag()
        b["aa.bb"] = "foo"
        assert "aa.bb" in b
        assert "aa" in b

    def test_missing_path_returns_false(self):
        b = Bag()
        b["aa.bb"] = "foo"
        assert "aa.cc" not in b
        assert "zz" not in b


# =============================================================================
# 3-4. ?attr singolo
# =============================================================================


class TestContainsQueryAttr:
    def test_existing_attribute_returns_true(self):
        b = Bag()
        b.set_item("aa.bb", "foo", color="red", width=56)
        assert "aa.bb?color" in b
        assert "aa.bb?width" in b

    def test_missing_attribute_returns_false(self):
        b = Bag()
        b.set_item("aa.bb", "foo", color="red")
        assert "aa.bb?missing" not in b


# =============================================================================
# 5-6. ?a&b: tutti gli attributi devono esistere
# =============================================================================


class TestContainsQueryMultipleAttrs:
    def test_all_attributes_present_returns_true(self):
        b = Bag()
        b.set_item("x", "v", a=1, b=2, c=3)
        assert "x?a&b" in b
        assert "x?a&b&c" in b

    def test_one_missing_attribute_returns_false(self):
        b = Bag()
        b.set_item("x", "v", a=1, b=2)
        assert "x?a&missing" not in b


# =============================================================================
# 7. ?attr su path inesistente
# =============================================================================


class TestContainsQueryAttrOnMissingPath:
    def test_query_attr_on_missing_path_returns_false(self):
        b = Bag()
        b["aa.bb"] = "foo"
        assert "aa.cc?color" not in b
        assert "zz?anything" not in b


# =============================================================================
# 8-9. in NON triggera resolver (semantica statica)
# =============================================================================


class TestContainsIsStatic:
    def test_in_does_not_trigger_resolver(self):
        """L'operatore ``in`` deve essere puramente statico: nessun resolver
        viene eseguito durante un containment check. Conseguenza diretta:
        un resolver NON ancora triggerato e' opaco per ``in``, il path
        sotto di esso non risulta presente finche' il resolver non viene
        caricato esplicitamente."""
        calls = []

        class CountingResolver(BagSyncResolver):
            def load(self):
                calls.append("load")
                inner = Bag()
                inner["bb"] = "computed"
                return inner

        b = Bag()
        b.set_item("aa", CountingResolver())

        # Il path sotto il resolver e' opaco a `in` finche' il resolver
        # non e' stato caricato. Nessun side-effect.
        assert ("aa.bb" in b) is False
        assert calls == []

        # Il nodo `aa` (livello del resolver) e' visibile staticamente.
        assert "aa" in b
        assert calls == []

    def test_in_remains_opaque_to_resolver_content(self):
        """Anche dopo che il resolver e' stato caricato esplicitamente, il
        contenuto generato non viene materializzato sul nodo (resta nel
        resolver). ``in`` continua a non vederlo: e' coerente con la sua
        semantica statica, e l'utente che vuole sapere se ``aa.bb`` esiste
        davvero deve usare ``bag.get_node('aa.bb')`` (non statico)."""
        calls = []

        class CountingResolver(BagSyncResolver):
            def load(self):
                calls.append("load")
                inner = Bag()
                inner["bb"] = "computed"
                return inner

        b = Bag()
        b.set_item("aa", CountingResolver())

        # Trigger esplicito del resolver
        _ = b["aa"]
        assert calls == ["load"]

        # `in` resta statico: opaco anche dopo il trigger
        assert ("aa.bb" in b) is False
        # E non ha aggiunto chiamate (non ri-triggera)
        assert calls == ["load"]

        # Per testare la presenza "vera" del path serve l'API non statica
        assert b.get_node("aa.bb") is not None
