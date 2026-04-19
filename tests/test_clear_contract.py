# Copyright 2025 Softwell S.r.l. - Genropy Team
# Licensed under the Apache License, Version 2.0

"""Tests for the semantic contract of Bag.clear().

clear() is an atomic replacement of the container content, not a sequence of
deletes. It emits one 'upd' event on the parent_node (if any) carrying an
orphan Bag with the old nodes as oldvalue.
"""

from genro_bag.bag import Bag


class TestClearContract:
    """Contract: clear() = update on parent_node with orphan Bag as oldvalue."""

    def test_clear_on_nested_bag_emits_update_on_parent(self):
        """clear() on a nested bag emits one upd event on the parent_node."""
        root = Bag()
        root.set_backref()
        root["sub.a"] = 1
        root["sub.b"] = 2

        events = []
        root.subscribe(
            "watch",
            update=lambda **kw: events.append(
                {"node": kw["node"], "oldvalue": kw["oldvalue"], "evt": kw["evt"]}
            ),
        )

        sub = root["sub"]
        sub.clear()

        assert len(events) == 1
        event = events[0]
        assert event["node"].label == "sub"
        assert event["evt"] == "upd_value"

    def test_clear_oldvalue_is_navigable_bag_with_old_nodes(self):
        """oldvalue passed to update subscriber is a Bag with the old nodes."""
        root = Bag()
        root.set_backref()
        root["sub.a"] = 1
        root["sub.b"] = 2

        captured = []
        root.subscribe("watch", update=lambda **kw: captured.append(kw["oldvalue"]))

        root["sub"].clear()

        assert len(captured) == 1
        orphans = captured[0]
        assert isinstance(orphans, Bag)
        labels = [n.label for n in orphans]
        assert "a" in labels
        assert "b" in labels
        assert orphans["a"] == 1
        assert orphans["b"] == 2

    def test_clear_top_level_bag_emits_no_event(self):
        """clear() on a top-level bag (no parent_node) emits no event."""
        bag = Bag()
        bag.set_backref()
        bag["a"] = 1
        bag["b"] = 2

        events = []
        bag.subscribe("watch", update=lambda **kw: events.append(kw))
        bag.subscribe("watch_del", delete=lambda **kw: events.append(kw))
        bag.subscribe("watch_ins", insert=lambda **kw: events.append(kw))

        bag.clear()

        assert events == []

    def test_clear_emits_no_delete_events(self):
        """clear() does NOT emit delete events anymore."""
        root = Bag()
        root.set_backref()
        root["sub.a"] = 1
        root["sub.b"] = 2

        deletes = []
        root.subscribe("watch", delete=lambda **kw: deletes.append(kw))

        root["sub"].clear()

        assert deletes == []

    def test_clear_leaves_self_connected_to_parent(self):
        """After clear(), self remains at its place in the tree."""
        root = Bag()
        root.set_backref()
        root["sub.a"] = 1

        sub = root["sub"]
        parent_node_before = sub.parent_node
        parent_before = sub.parent

        sub.clear()

        assert sub.parent_node is parent_node_before
        assert sub.parent is parent_before
        assert len(sub) == 0
        # the sub-bag is still the same instance reachable from root
        assert root["sub"] is sub

    def test_clear_orphans_have_parent_bag_pointing_to_orphan_bag(self):
        """Old nodes have _parent_bag pointing to the orphan Bag, not self."""
        root = Bag()
        root.set_backref()
        root["sub.a"] = 1
        root["sub.b"] = 2

        sub = root["sub"]
        captured = []
        root.subscribe("watch", update=lambda **kw: captured.append(kw["oldvalue"]))

        sub.clear()

        orphans = captured[0]
        for node in orphans:
            assert node.parent_bag is orphans
            assert node.parent_bag is not sub

    def test_clear_orphan_bag_is_detached_from_tree(self):
        """The orphan Bag has no parent/parent_node, it's outside the tree."""
        root = Bag()
        root.set_backref()
        root["sub.a"] = 1

        captured = []
        root.subscribe("watch", update=lambda **kw: captured.append(kw["oldvalue"]))

        root["sub"].clear()

        orphans = captured[0]
        assert orphans.parent is None
        assert orphans.parent_node is None

    def test_clear_without_backref_emits_no_event(self):
        """clear() on a bag without backref emits no event (as before)."""
        root = Bag()
        root["sub.a"] = 1
        sub = root["sub"]
        # backref not enabled

        events = []
        # Subscribe would work only with backref; verify clear is silent anyway.
        sub.subscribe("watch", update=lambda **kw: events.append(kw))

        sub.clear()
        assert events == []

    def test_clear_empty_bag_is_noop(self):
        """Clearing an already empty bag does not crash and emits no event."""
        root = Bag()
        root.set_backref()
        root["sub"] = Bag()

        events = []
        root.subscribe("watch", update=lambda **kw: events.append(kw))

        root["sub"].clear()

        assert events == []
        assert len(root["sub"]) == 0
