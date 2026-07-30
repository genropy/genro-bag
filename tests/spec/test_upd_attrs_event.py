"""Spec test: payload of ``upd_attrs`` event emitted by BagNode.set_attr.

Depends on test_basic.py (set_item) and test_subscriptions.py (subscribe).

Contract: every call to ``set_attr`` that modifies at least one attribute
emits ``upd_attrs`` with self-contained **diff dict** payload:

    {"<attr>": {"old": <prev_value>, "new": <curr_value>}, ...}

Rules:
- keys in diff: only those actually changed;
- attribute added:    ``{"old": None, "new": <value>}``;
- attribute removed:  ``{"old": <value>, "new": None}``;
- attribute modified: ``{"old": <prev>, "new": <curr>}``;
- no actual change -> no event emitted (silent no-op);
- ``trigger=False`` -> no event.

The payload arrives:
- to node-level subscribers as ``info={"attrs_diff": <diff>}``;
- to bag-level subscribers (via _on_node_changed) as kwarg
  ``attrs_diff=<diff>``; ``oldvalue`` stays None (it's reserved for
  the old scalar value of upd_value / upd_value_attr).

## Scale

1. attribute added                          diff with old=None, new=value
2. attribute modified                       diff with old=prev, new=curr
3. attribute removed (None + remove_null)   diff with new=None
4. multiple attributes in one call          multi-key diff coherent
5. no-op                                    no event
6. trigger=False                            no event
7. _updattr=False (total replacement)       unpasssed attributes = removed
8. node subscriber                          receives info={"attrs_diff": <diff>}
9. bag subscriber                           receives attrs_diff=<diff>, oldvalue=None
"""

from __future__ import annotations

from genro_bag import Bag

# =============================================================================
# 1. attributo aggiunto
# =============================================================================


class TestUpdAttrsAdded:
    def test_added_attribute_emits_diff_with_old_none(self):
        """New attribute appears in diff as {"old": None, "new": <value>}."""
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
        """Modified attribute appears in diff with both old and new populated."""
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
        """Setting attribute to None with _remove_null_attributes=True (default)
        produces diff with new=None (attribute is removed)."""
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
# 4. several attributes in a single call
# =============================================================================


class TestUpdAttrsMultiple:
    def test_multiple_changes_in_one_call_produce_single_event_with_all_keys(self):
        """Single set_attr touching multiple keys emits one event with
        all keys in diff."""
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
# 5. no-op (nothing actually changes)
# =============================================================================


class TestUpdAttrsNoOp:
    def test_setting_same_value_emits_no_event(self):
        """Setting attribute to same value emits no event."""
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
        """trigger=False suppresses event even if there are real changes."""
        events = []
        bag = Bag()
        bag.set_item("x", "value", color="red")
        bag.subscribe("s1", update=lambda **kw: events.append(kw["evt"]))
        bag.get_node("x").set_attr(color="blue", trigger=False)
        assert events == []
        assert bag.get_node("x").attr["color"] == "blue"  # change did happen


# =============================================================================
# 7. _updattr=False (sostituzione totale)
# =============================================================================


class TestUpdAttrsReplaceMode:
    def test_replace_mode_marks_dropped_attributes_as_removed(self):
        """With _updattr=False previous attributes not passed in new
        call appear in diff as removed (new=None)."""
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
        """Subscriber registered directly on node receives diff dict
        as argument ``info["attrs_diff"]``."""
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
        """Subscriber registered on parent bag receives diff dict as
        kwarg ``attrs_diff`` (propagated via _on_node_changed). ``oldvalue``
        stays None for purely attribute events."""
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
