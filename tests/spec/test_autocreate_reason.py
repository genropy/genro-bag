"""Spec test: gli autocreate strutturali di nodi intermedi portano
``reason="autocreate"`` negli eventi emessi ai subscriber.

Dipende da test_basic.py (set_item) e test_subscriptions.py (subscribe).

Contratto:
- Quando `bag["a.b.c"] = value` autocrea i container intermedi `a` e `b`,
  i corrispondenti eventi `ins` arrivano con ``reason="autocreate"``.
- L'evento del datum finale (`c`) resta non marcato (``reason=None``).
- La promozione di un nodo scalare a container (`bag["x"] = "v"` poi
  `bag["x.y"] = 1`) viene marcata su `x` come autocreate.
- Insert/update espliciti su path semplici non sono toccati.

## Scala

1. path nuovo, container intermedi              ins di a,b -> 'autocreate', c -> None
2. primo livello esistente come Bag             ins di b -> 'autocreate', c -> None
3. promozione scalare -> container              upd_value di a -> 'autocreate', ins di b -> 'autocreate', c -> None
4. subscriber filtra autocreate                 vede solo l'evento del leaf
5. insert su path semplice                      reason resta None
"""

from __future__ import annotations

from genro_bag import Bag

# =============================================================================
# 1. path nuovo: container intermedi puri
# =============================================================================


class TestAutocreatePureIntermediates:
    def test_intermediate_containers_marked_autocreate_leaf_not_marked(self):
        """bag['a.b.c'] = 1 su bag vuota: a,b sono autocreate; c e' insert reale."""
        events = []
        bag = Bag()
        bag.subscribe(
            "w",
            any=lambda **kw: events.append(
                (kw["evt"], kw["node"].label, kw.get("reason"))
            ),
        )
        bag["a.b.c"] = 1
        assert events == [
            ("ins", "a", "autocreate"),
            ("ins", "b", "autocreate"),
            ("ins", "c", None),
        ]


# =============================================================================
# 2. primo livello gia' presente come Bag
# =============================================================================


class TestAutocreatePartialPath:
    def test_only_missing_intermediates_marked_autocreate(self):
        """Se il primo livello esiste gia' come Bag, solo i livelli sotto
        vengono autocreate. L'evento del leaf finale resta non marcato."""
        bag = Bag()
        bag["a"] = Bag()
        events = []
        bag.subscribe(
            "w",
            any=lambda **kw: events.append(
                (kw["evt"], kw["node"].label, kw.get("reason"))
            ),
        )
        bag["a.b.c"] = 1
        assert events == [
            ("ins", "b", "autocreate"),
            ("ins", "c", None),
        ]


# =============================================================================
# 3. promozione scalare -> container
# =============================================================================


class TestAutocreateScalarPromotion:
    def test_scalar_promoted_to_container_marked_autocreate(self):
        """Un nodo scalare promosso a container durante la traversata in
        write mode riceve reason='autocreate' sull'evento upd_value della
        promozione. I livelli sotto, autocreate, idem; la foglia finale no."""
        bag = Bag()
        bag["a"] = "scalar"  # ins di "a" con reason=None
        events = []
        bag.subscribe(
            "w",
            any=lambda **kw: events.append(
                (kw["evt"], kw["node"].label, kw.get("reason"))
            ),
        )
        bag["a.b"] = 1
        # a viene promosso (upd_value 'scalar' -> Bag()), poi b inserito
        assert events == [
            ("upd_value", "a", "autocreate"),
            ("ins", "b", None),
        ]


# =============================================================================
# 4. subscriber filtra autocreate (pattern downstream idiomatico)
# =============================================================================


class TestAutocreateConsumerFilters:
    def test_subscriber_can_skip_autocreate_events(self):
        """Un subscriber reattivo che vuole reagire solo ai datum reali puo'
        filtrare via reason='autocreate' e ricevere solo l'evento del leaf."""
        real_events = []
        bag = Bag()

        def filter_autocreate(**kw):
            if kw.get("reason") == "autocreate":
                return
            real_events.append((kw["evt"], kw["node"].label))

        bag.subscribe("w", any=filter_autocreate)
        bag["a.b.c"] = 1
        assert real_events == [("ins", "c")]


# =============================================================================
# 5. insert su path semplice: reason resta None
# =============================================================================


class TestAutocreateDoesNotLeak:
    def test_simple_set_item_is_not_marked_autocreate(self):
        """Un insert/update su path semplice (niente autocreate) ha reason=None.
        La marcatura non deve 'sporcare' chiamate normali."""
        events = []
        bag = Bag()
        bag.subscribe(
            "w",
            any=lambda **kw: events.append(
                (kw["evt"], kw["node"].label, kw.get("reason"))
            ),
        )
        bag["x"] = 1
        bag["x"] = 2
        assert events == [
            ("ins", "x", None),
            ("upd_value", "x", None),
        ]
