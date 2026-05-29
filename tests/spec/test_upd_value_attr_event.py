"""Spec test: payload dell'evento ``upd_value_attr`` emesso da set_item /
BagNode.set_value quando vengono passati anche ``_attributes``.

Dipende da test_basic.py (set_item) e test_subscriptions.py (subscribe).

Contratto: una set_item / set_value che cambia il valore di un nodo
esistente E ne tocca anche gli attributi emette un singolo evento
``upd_value_attr`` con payload composto:

- ``oldvalue``  = il valore scalare/Bag precedente (semantica storica);
- ``attrs_diff`` = diff dict degli attributi modificati, stessa forma
  di ``upd_attrs`` ({"<attr>": {"old": ..., "new": ...}, ...}).

A livello node il subscriber riceve un dict ``info`` con le due chiavi:
``info = {"oldvalue": <scalar>, "attrs_diff": <diff>}``.

A livello bag (via _on_node_changed) le due informazioni arrivano come
kwarg separati: ``oldvalue=<scalar>``, ``attrs_diff=<diff>``.

Se gli attributi non cambiano effettivamente (no-op sul lato attributi),
``attrs_diff`` puo' essere None ma il valore viene comunque aggiornato
come ``upd_value_attr`` (perche' l'utente ha passato ``_attributes``
esplicitamente).

## Scala

1. set_item con valore nuovo + attributi nuovi   evt + oldvalue + attrs_diff
2. set_item solo cambio valore (no _attributes)  evt='upd_value', attrs_diff=None
3. set_value combinato cambia entrambi           diff multi-key coerente
4. node subscriber con upd_value_attr            info contiene entrambe le chiavi
5. node subscriber con upd_value puro            info ha solo 'oldvalue'
6. piu' attributi cambiati insieme al valore     attrs_diff multi-key
"""

from __future__ import annotations

from genro_bag import Bag

# =============================================================================
# 1. set_item con valore nuovo + attributi nuovi
# =============================================================================


class TestUpdValueAttrBasic:
    def test_set_item_with_attributes_emits_upd_value_attr_with_both_payloads(self):
        """Quando set_item cambia valore E attributi di un nodo esistente,
        l'evento bag-level e' upd_value_attr e porta sia oldvalue (scalare
        precedente) sia attrs_diff."""
        events = []
        bag = Bag()
        bag.set_item("x", "v0", color="red")
        bag.subscribe(
            "s1",
            update=lambda **kw: events.append({
                "evt": kw["evt"],
                "oldvalue": kw["oldvalue"],
                "attrs_diff": kw["attrs_diff"],
            }),
        )
        bag.set_item("x", "v1", color="blue")
        assert events == [{
            "evt": "upd_value_attr",
            "oldvalue": "v0",
            "attrs_diff": {"color": {"old": "red", "new": "blue"}},
        }]


# =============================================================================
# 2. set_item senza _attributes -> upd_value puro
# =============================================================================


class TestUpdValueWithoutAttributes:
    def test_set_item_value_only_emits_upd_value_with_none_attrs_diff(self):
        """set_item senza attributi emette upd_value (non upd_value_attr) e
        attrs_diff e' None."""
        events = []
        bag = Bag()
        bag.set_item("x", "v0")
        bag.subscribe(
            "s1",
            update=lambda **kw: events.append({
                "evt": kw["evt"],
                "oldvalue": kw["oldvalue"],
                "attrs_diff": kw["attrs_diff"],
            }),
        )
        bag.set_item("x", "v1")
        assert events == [{
            "evt": "upd_value",
            "oldvalue": "v0",
            "attrs_diff": None,
        }]


# =============================================================================
# 3. attributi aggiunti insieme al cambio valore
# =============================================================================


class TestUpdValueAttrAddedAttributes:
    def test_value_change_with_new_attributes_added(self):
        """Se il nodo non aveva attributi e set_item ne aggiunge, il diff li
        marca tutti come added (old=None)."""
        events = []
        bag = Bag()
        bag.set_item("x", "v0")
        bag.subscribe(
            "s1",
            update=lambda **kw: events.append((kw["evt"], kw["oldvalue"], kw["attrs_diff"])),
        )
        bag.set_item("x", "v1", color="red", size=42)
        assert events == [(
            "upd_value_attr",
            "v0",
            {
                "color": {"old": None, "new": "red"},
                "size": {"old": None, "new": 42},
            },
        )]


# =============================================================================
# 4. node subscriber - upd_value_attr
# =============================================================================


class TestUpdValueAttrNodeSubscriber:
    def test_node_subscriber_receives_info_with_oldvalue_and_attrs_diff(self):
        """Un subscriber node-level riceve info come dict con 'oldvalue' e
        'attrs_diff' quando l'evento e' upd_value_attr."""
        events = []
        bag = Bag()
        bag.set_item("x", "v0", color="red")
        node = bag.get_node("x")
        node.subscribe(
            "ns1",
            lambda **kw: events.append((kw["evt"], kw["info"])),
        )
        bag.set_item("x", "v1", color="blue")
        assert events == [(
            "upd_value_attr",
            {
                "oldvalue": "v0",
                "attrs_diff": {"color": {"old": "red", "new": "blue"}},
            },
        )]


# =============================================================================
# 5. node subscriber - upd_value puro
# =============================================================================


class TestUpdValueNodeSubscriberInfoShape:
    def test_node_subscriber_receives_info_with_only_oldvalue_for_pure_upd_value(self):
        """Per upd_value puro, info contiene solo la chiave 'oldvalue'."""
        events = []
        bag = Bag()
        bag.set_item("x", "v0")
        node = bag.get_node("x")
        node.subscribe(
            "ns1",
            lambda **kw: events.append((kw["evt"], kw["info"])),
        )
        bag.set_item("x", "v1")
        assert events == [("upd_value", {"oldvalue": "v0"})]


# =============================================================================
# 6. attributi multipli con cambio valore
# =============================================================================


class TestUpdValueAttrMultipleAttributes:
    def test_multiple_attributes_changed_alongside_value(self):
        """Il diff include tutte le chiavi cambiate (aggiunte, modificate o
        rimosse) anche quando il valore cambia contestualmente."""
        events = []
        bag = Bag()
        bag.set_item("x", "v0", color="red", size=10)
        bag.subscribe(
            "s1",
            update=lambda **kw: events.append((kw["evt"], kw["oldvalue"], kw["attrs_diff"])),
        )
        bag.set_item("x", "v1", color="blue", weight=3.14)
        assert len(events) == 1
        evt, oldvalue, diff = events[0]
        assert evt == "upd_value_attr"
        assert oldvalue == "v0"
        # set_item ha _updattr=False di default (sostituzione totale degli
        # attributi): color e' modificato, weight aggiunto, size rimosso
        # (perche' non passato nella nuova chiamata).
        assert diff == {
            "color": {"old": "red", "new": "blue"},
            "size": {"old": 10, "new": None},
            "weight": {"old": None, "new": 3.14},
        }
