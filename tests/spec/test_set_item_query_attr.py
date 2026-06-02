"""Spec test: la sintassi ``set_item('path?attr', value)`` deve essere
equivalente a ``node.set_attr(attr=value)`` — semantica di merge, non di
sostituzione totale.

Dipende da test_basic.py (set_item) e test_subscriptions.py (subscribe).

Contratto: quando il label contiene ``?<attr>``, ``set_item`` lascia il
valore del nodo invariato e modifica SOLO l'attributo nominato. Tutti gli
altri attributi del nodo sopravvivono (merge). Settare l'attributo a
``None`` lo rimuove ma lascia gli altri al loro posto, esattamente come
``node.set_attr(attr=None)`` con ``_remove_null_attributes=True``.

## Scala

1. ?attr su nodo con piu' attributi              gli altri attributi sopravvivono
2. ?attr1&attr2 con tuple                        modifica solo i due, gli altri restano
3. ?attr=None                                    rimuove solo quello, gli altri restano
4. ?attr equivalente a set_attr diretto          stesso risultato su un nodo identico
5. valore del nodo non viene toccato             ?attr non altera node.value
"""

from __future__ import annotations

from genro_bag import Bag

# =============================================================================
# 1. ?attr su nodo con piu' attributi: gli altri sopravvivono
# =============================================================================


class TestQueryAttrPreservesOthers:
    def test_single_attr_change_does_not_wipe_others(self):
        """set_item('path?color', 'blue') su nodo con color+width deve
        modificare solo color, lasciando width intatto."""
        b = Bag()
        b.set_item("alfa.beta", "foo", color="red", width=56)
        b.set_item("alfa.beta?color", "blue")
        assert b.get_node("alfa.beta").attr == {"color": "blue", "width": 56}


# =============================================================================
# 2. ?attr1&attr2 con tuple: solo i due nominati, gli altri restano
# =============================================================================


class TestQueryMultipleAttrs:
    def test_multi_attr_query_only_touches_named_keys(self):
        """set_item('path?a&b', (1, 2)) cambia solo a e b, lascia c."""
        b = Bag()
        b.set_item("x", "v", a=10, b=20, c=30)
        b.set_item("x?a&b", (100, 200))
        assert b.get_node("x").attr == {"a": 100, "b": 200, "c": 30}


# =============================================================================
# 3. ?attr=None: rimuove solo quello
# =============================================================================


class TestQueryAttrSetToNone:
    def test_setting_attr_to_none_removes_only_that_attr(self):
        """set_item('path?color', None) rimuove color (default
        _remove_null_attributes=True) ma preserva gli altri."""
        b = Bag()
        b.set_item("x", "v", color="red", width=56)
        b.set_item("x?color", None)
        assert b.get_node("x").attr == {"width": 56}


# =============================================================================
# 4. ?attr deve essere equivalente a set_attr diretta
# =============================================================================


class TestQueryAttrEquivalentToSetAttr:
    def test_query_syntax_matches_direct_set_attr(self):
        """Il risultato di set_item('x?color', 'blue') deve essere identico
        a node.set_attr(color='blue')."""
        # via set_attr diretta
        b1 = Bag()
        b1.set_item("x", "v", color="red", width=56)
        b1.get_node("x").set_attr(color="blue")

        # via query syntax
        b2 = Bag()
        b2.set_item("x", "v", color="red", width=56)
        b2.set_item("x?color", "blue")

        assert b1.get_node("x").attr == b2.get_node("x").attr


# =============================================================================
# 5. il valore del nodo non viene alterato dalla sintassi ?attr
# =============================================================================


class TestQueryAttrDoesNotTouchValue:
    def test_node_value_untouched_by_query_syntax(self):
        """?attr modifica solo gli attributi: node.value resta com'era."""
        b = Bag()
        b.set_item("x", "original_value", color="red")
        b.set_item("x?color", "blue")
        assert b["x"] == "original_value"
        assert b.get_node("x").attr == {"color": "blue"}
