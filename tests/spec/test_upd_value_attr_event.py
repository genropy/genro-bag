"""Spec test: payload of ``upd_value_attr`` event emitted by set_item /
BagNode.set_value when ``_attributes`` is also passed.

Depends on test_basic.py (set_item) and test_subscriptions.py (subscribe).

Contract: a set_item / set_value that changes a node's value
AND also touches its attributes emits a single ``upd_value_attr``
event with composite payload:

- ``oldvalue``  = the previous scalar/Bag value (historical semantics);
- ``attrs_diff`` = diff dict of modified attributes, same form as
  ``upd_attrs`` ({"<attr>": {"old": ..., "new": ...}, ...}).

At node level the subscriber receives an ``info`` dict with both keys:
``info = {"oldvalue": <scalar>, "attrs_diff": <diff>}``.

At bag level (via _on_node_changed) the two pieces arrive as
separate kwargs: ``oldvalue=<scalar>``, ``attrs_diff=<diff>``.

If attributes don't actually change (no-op on attributes side),
``attrs_diff`` may be None but the value is still updated
as ``upd_value_attr`` (because user passed ``_attributes``
explicitly).

## Scale

1. set_item with new value + new attributes        evt + oldvalue + attrs_diff
2. set_item value change only (no _attributes)     evt='upd_value', attrs_diff=None
3. combined set_value changes both                 multi-key diff coherent
4. node subscriber with upd_value_attr             info contains both keys
5. node subscriber with pure upd_value             info has only 'oldvalue'
6. multiple attributes changed alongside value     multi-key attrs_diff
"""

from __future__ import annotations

from genro_bag import Bag

# =============================================================================
# 1. set_item with a new value plus new attributes
# =============================================================================


class TestUpdValueAttrBasic:
    def test_set_item_with_attributes_emits_upd_value_attr_with_both_payloads(self):
        """When set_item changes both value AND attributes of existing node,
        the bag-level event is upd_value_attr and carries both oldvalue (previous
        scalar) and attrs_diff."""
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
# 2. set_item without _attributes -> plain upd_value
# =============================================================================


class TestUpdValueWithoutAttributes:
    def test_set_item_value_only_emits_upd_value_with_none_attrs_diff(self):
        """set_item without attributes emits upd_value (not upd_value_attr) and
        attrs_diff is None."""
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
# 3. attributes added along with the value change
# =============================================================================


class TestUpdValueAttrAddedAttributes:
    def test_value_change_with_new_attributes_added(self):
        """If node had no attributes and set_item adds them, diff marks
        all as added (old=None)."""
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
        """Node-level subscriber receives info as dict with 'oldvalue' and
        'attrs_diff' when event is upd_value_attr."""
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
        """For pure upd_value, info contains only 'oldvalue' key."""
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
# 6. several attributes with a value change
# =============================================================================


class TestUpdValueAttrMultipleAttributes:
    def test_multiple_attributes_changed_alongside_value(self):
        """Diff includes all changed keys (added, modified or
        removed) even when value changes concurrently."""
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
        # set_item has _updattr=False by default (total replacement of
        # attributes): color is modified, weight added, size removed
        # (because not passed in new call).
        assert diff == {
            "color": {"old": "red", "new": "blue"},
            "size": {"old": 10, "new": None},
            "weight": {"old": None, "new": 3.14},
        }
