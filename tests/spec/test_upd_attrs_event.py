"""Spec test: payload dell'evento ``upd_attrs`` emesso da BagNode.set_attr.

Dipende da test_basic.py (set_item) e test_subscriptions.py (subscribe).

Contratto: ogni chiamata a ``set_attr`` che modifica almeno un attributo
emette ``upd_attrs`` con payload **diff dict** auto-contenuto:

    {"<attr>": {"old": <prev_value>, "new": <curr_value>}, ...}

Regole:
- chiavi nel diff: solo quelle effettivamente cambiate;
- attributo aggiunto:   ``{"old": None, "new": <value>}``;
- attributo rimosso:    ``{"old": <value>, "new": None}``;
- attributo modificato: ``{"old": <prev>, "new": <curr>}``;
- nessuna modifica reale -> nessun evento emesso (no-op silenzioso);
- ``trigger=False`` -> nessun evento.

Il payload arriva:
- ai subscriber node-level come ``info={"attrs_diff": <diff>}``;
- ai subscriber bag-level (via _on_node_changed) come kwarg
  ``attrs_diff=<diff>``; ``oldvalue`` resta None (e' riservato al valore
  vecchio scalare di upd_value / upd_value_attr).

## Scala

1. attributo aggiunto                       diff con old=None, new=value
2. attributo modificato                     diff con old=prev, new=curr
3. attributo rimosso (None + remove_null)   diff con new=None
4. piu' attributi in una sola chiamata      diff multi-key coerente
5. no-op                                    nessun evento
6. trigger=False                            nessun evento
7. _updattr=False (replace totale)          attributi non passati = removed
8. node subscriber                          riceve info={"attrs_diff": <diff>}
9. bag subscriber                           riceve attrs_diff=<diff>, oldvalue=None
"""

from __future__ import annotations

from genro_bag import Bag

# =============================================================================
# 1. attributo aggiunto
# =============================================================================


class TestUpdAttrsAdded:
    def test_added_attribute_emits_diff_with_old_none(self):
        """Un attributo nuovo appare nel diff come {"old": None, "new": <value>}."""
        events = []
        bag = Bag()
        bag.set_item("x", "value")
        bag.subscribe(
            "s1",
            update=lambda **kw: events.append((kw["evt"], kw["attrs_diff"])),
        )
        bag.get_node("x").set_attr(color="red")
        assert events == [("upd_attrs", {"color": {"old": None, "new": "red"}})]


# =============================================================================
# 2. attributo modificato
# =============================================================================


class TestUpdAttrsModified:
    def test_modified_attribute_emits_diff_with_old_and_new(self):
        """Un attributo modificato appare nel diff con old e new entrambi valorizzati."""
        events = []
        bag = Bag()
        bag.set_item("x", "value", color="red")
        bag.subscribe(
            "s1",
            update=lambda **kw: events.append((kw["evt"], kw["attrs_diff"])),
        )
        bag.get_node("x").set_attr(color="blue")
        assert events == [("upd_attrs", {"color": {"old": "red", "new": "blue"}})]


# =============================================================================
# 3. attributo rimosso (None + _remove_null_attributes default)
# =============================================================================


class TestUpdAttrsRemoved:
    def test_attribute_set_to_none_appears_as_removed(self):
        """Settare un attributo a None con _remove_null_attributes=True (default)
        produce un diff con new=None (l'attributo viene rimosso)."""
        events = []
        bag = Bag()
        bag.set_item("x", "value", color="red")
        bag.subscribe(
            "s1",
            update=lambda **kw: events.append((kw["evt"], kw["attrs_diff"])),
        )
        bag.get_node("x").set_attr(color=None)
        assert events == [("upd_attrs", {"color": {"old": "red", "new": None}})]


# =============================================================================
# 4. piu' attributi in una sola chiamata
# =============================================================================


class TestUpdAttrsMultiple:
    def test_multiple_changes_in_one_call_produce_single_event_with_all_keys(self):
        """Una sola set_attr che tocca piu' chiavi emette un solo evento con
        tutte le chiavi nel diff."""
        events = []
        bag = Bag()
        bag.set_item("x", "value", color="red")
        bag.subscribe(
            "s1",
            update=lambda **kw: events.append((kw["evt"], kw["attrs_diff"])),
        )
        bag.get_node("x").set_attr(color="blue", size=42)
        assert len(events) == 1
        evt, diff = events[0]
        assert evt == "upd_attrs"
        assert diff == {
            "color": {"old": "red", "new": "blue"},
            "size": {"old": None, "new": 42},
        }


# =============================================================================
# 5. no-op (nessun cambio reale)
# =============================================================================


class TestUpdAttrsNoOp:
    def test_setting_same_value_emits_no_event(self):
        """Settare un attributo allo stesso valore non emette eventi."""
        events = []
        bag = Bag()
        bag.set_item("x", "value", color="red")
        bag.subscribe("s1", update=lambda **kw: events.append(kw["evt"]))
        bag.get_node("x").set_attr(color="red")
        assert events == []


# =============================================================================
# 6. trigger=False
# =============================================================================


class TestUpdAttrsTriggerFalse:
    def test_trigger_false_emits_no_event(self):
        """trigger=False sopprime l'evento anche se ci sono cambi reali."""
        events = []
        bag = Bag()
        bag.set_item("x", "value", color="red")
        bag.subscribe("s1", update=lambda **kw: events.append(kw["evt"]))
        bag.get_node("x").set_attr(color="blue", trigger=False)
        assert events == []
        assert bag.get_node("x").attr["color"] == "blue"  # la modifica e' avvenuta


# =============================================================================
# 7. _updattr=False (sostituzione totale)
# =============================================================================


class TestUpdAttrsReplaceMode:
    def test_replace_mode_marks_dropped_attributes_as_removed(self):
        """Con _updattr=False gli attributi precedenti non passati nella nuova
        chiamata appaiono nel diff come removed (new=None)."""
        events = []
        bag = Bag()
        bag.set_item("x", "value", color="red", size=10)
        bag.subscribe(
            "s1",
            update=lambda **kw: events.append((kw["evt"], kw["attrs_diff"])),
        )
        bag.get_node("x").set_attr(attr={"shape": "circle"}, _updattr=False)
        assert len(events) == 1
        evt, diff = events[0]
        assert evt == "upd_attrs"
        assert diff == {
            "color": {"old": "red", "new": None},
            "size": {"old": 10, "new": None},
            "shape": {"old": None, "new": "circle"},
        }


# =============================================================================
# 8. node subscriber
# =============================================================================


class TestUpdAttrsNodeSubscriber:
    def test_node_level_subscriber_receives_diff_as_info_attrs_diff(self):
        """Un subscriber registrato direttamente sul nodo riceve il diff dict
        come argomento ``info["attrs_diff"]``."""
        events = []
        bag = Bag()
        bag.set_item("x", "value", color="red")
        node = bag.get_node("x")
        node.subscribe(
            "ns1",
            lambda **kw: events.append((kw["evt"], kw["info"])),
        )
        node.set_attr(color="blue")
        assert events == [
            (
                "upd_attrs",
                {"attrs_diff": {"color": {"old": "red", "new": "blue"}}},
            )
        ]


# =============================================================================
# 9. bag subscriber (propagazione via _on_node_changed)
# =============================================================================


class TestUpdAttrsBagSubscriber:
    def test_bag_level_subscriber_receives_diff_as_attrs_diff_kwarg(self):
        """Un subscriber registrato sul parent bag riceve il diff dict come
        kwarg ``attrs_diff`` (propagato via _on_node_changed). ``oldvalue``
        resta None per gli eventi puramente di attributi."""
        events = []
        bag = Bag()
        bag.set_item("x", "value", color="red")
        bag.subscribe(
            "s1",
            update=lambda **kw: events.append({
                "evt": kw["evt"],
                "oldvalue": kw["oldvalue"],
                "attrs_diff": kw["attrs_diff"],
                "pathlist": kw["pathlist"],
            }),
        )
        bag.get_node("x").set_attr(color="blue")
        assert events == [{
            "evt": "upd_attrs",
            "oldvalue": None,
            "attrs_diff": {"color": {"old": "red", "new": "blue"}},
            "pathlist": ["x"],
        }]
