"""Spec test: ``set_item('path?attr', value)`` syntax must be
equivalent to ``node.set_attr(attr=value)`` — merge semantics, not
total replacement.

Depends on test_basic.py (set_item) and test_subscriptions.py (subscribe).

Contract: when label contains ``?<attr>``, ``set_item`` leaves node value
unchanged and modifies ONLY the named attribute. All other node attributes
survive (merge). Setting attribute to ``None`` removes it but leaves others
in place, exactly like ``node.set_attr(attr=None)`` with
``_remove_null_attributes=True``.

## Scale

1. ?attr on node with multiple attrs             other attributes survive
2. ?attr1&attr2 with tuple                       modifies only two, others remain
3. ?attr=None                                    removes only that, others remain
4. ?attr equivalent to direct set_attr           same result on identical node
5. node value not touched                        ?attr does not alter node.value
"""

from __future__ import annotations

from genro_bag import Bag

# =============================================================================
# 1. ?attr on a node with several attributes: the others survive
# =============================================================================


class TestQueryAttrPreservesOthers:
    def test_single_attr_change_does_not_wipe_others(self):
        """set_item('path?color', 'blue') on node with color+width must
        modify only color, leaving width unchanged."""
        b = Bag()
        b.set_item("alfa.beta", "foo", color="red", width=56)
        b.set_item("alfa.beta?color", "blue")
        assert b.get_node("alfa.beta").attr == {"color": "blue", "width": 56}


# =============================================================================
# 2. ?attr1&attr2 with a tuple: only the two named change, the rest stay
# =============================================================================


class TestQueryMultipleAttrs:
    def test_multi_attr_query_only_touches_named_keys(self):
        """set_item('path?a&b', (1, 2)) changes only a and b, leaves c."""
        b = Bag()
        b.set_item("x", "v", a=10, b=20, c=30)
        b.set_item("x?a&b", (100, 200))
        assert b.get_node("x").attr == {"a": 100, "b": 200, "c": 30}


# =============================================================================
# 3. ?attr=None: rimuove solo quello
# =============================================================================


class TestQueryAttrSetToNone:
    def test_setting_attr_to_none_removes_only_that_attr(self):
        """set_item('path?color', None) removes color (default
        _remove_null_attributes=True) but preserves others."""
        b = Bag()
        b.set_item("x", "v", color="red", width=56)
        b.set_item("x?color", None)
        assert b.get_node("x").attr == {"width": 56}


# =============================================================================
# 4. ?attr must behave exactly like a direct set_attr
# =============================================================================


class TestQueryAttrEquivalentToSetAttr:
    def test_query_syntax_matches_direct_set_attr(self):
        """Result of set_item('x?color', 'blue') must be identical to
        node.set_attr(color='blue')."""
        # via direct set_attr
        b1 = Bag()
        b1.set_item("x", "v", color="red", width=56)
        b1.get_node("x").set_attr(color="blue")

        # via query syntax
        b2 = Bag()
        b2.set_item("x", "v", color="red", width=56)
        b2.set_item("x?color", "blue")

        assert b1.get_node("x").attr == b2.get_node("x").attr


# =============================================================================
# 5. the ?attr syntax leaves the node value untouched
# =============================================================================


class TestQueryAttrDoesNotTouchValue:
    def test_node_value_untouched_by_query_syntax(self):
        """?attr modifies only attributes: node.value stays as is."""
        b = Bag()
        b.set_item("x", "original_value", color="red")
        b.set_item("x?color", "blue")
        assert b["x"] == "original_value"
        assert b.get_node("x").attr == {"color": "blue"}
