# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0

"""Tests for the atomic contract of Bag.fill_from (issue #44).

fill_from follows the pattern established by clear() in #46:
    - the new content is built offline in an orphan Bag,
    - node containers are swapped atomically,
    - when the target is attached with backref a single upd_value event is
      emitted on the parent, with oldvalue = orphan Bag carrying the
      previous content (navigable like any Bag).

Invariants covered here:
    - Exactly one event per fill_from when attached with backref.
    - No events when the target is top-level (no parent).
    - oldvalue is a full-fledged navigable Bag holding the previous nodes.
    - Atomicity on failure: if the source fails to parse, self keeps its
      previous state (no partial population).
    - Self object identity is preserved across the call.
    - Nested sub-Bags receive proper backref after the swap.
"""

import pytest

from genro_bag import Bag


class TestFillFromSingleAtomicEvent:
    """When attached with backref, fill_from emits exactly one upd_value."""

    def test_single_event_on_dict_source(self):
        """fill_from({}) -> 1 upd_value event on parent."""
        outer = Bag()
        outer.set_backref()
        outer.set_item("inner", Bag())

        events = []
        outer.subscribe("watcher", any=lambda **kw: events.append(kw))

        outer["inner"].fill_from({"a": 1, "b": 2, "c": 3})

        assert len(events) == 1
        evt = events[0]
        assert evt["evt"] == "upd_value"
        assert evt["node"].label == "inner"

    def test_no_event_when_top_level(self):
        """fill_from on a top-level Bag (no parent) emits no events."""
        bag = Bag()
        bag.set_backref()

        events = []
        bag.subscribe("watcher", any=lambda **kw: events.append(kw))

        bag.fill_from({"a": 1, "b": 2})

        # No parent → no upward bubbling → no event
        assert events == []

    def test_single_event_on_bag_source(self):
        """fill_from(Bag) also emits a single atomic event."""
        outer = Bag()
        outer.set_backref()
        outer.set_item("inner", Bag({"old": 0}))

        events = []
        outer.subscribe("watcher", any=lambda **kw: events.append(kw))

        source = Bag({"x": 10, "y": 20})
        outer["inner"].fill_from(source)

        assert len(events) == 1
        assert events[0]["evt"] == "upd_value"


class TestFillFromOldvalue:
    """The oldvalue passed to subscribers is a navigable orphan Bag."""

    def test_oldvalue_is_a_bag(self):
        """oldvalue is a Bag instance, not a list of nodes."""
        outer = Bag()
        outer.set_backref()
        outer.set_item("inner", Bag({"x": 1, "y": 2}))

        events = []
        outer.subscribe("watcher", update=lambda **kw: events.append(kw))

        outer["inner"].fill_from({"a": 10})

        assert len(events) == 1
        oldvalue = events[0]["oldvalue"]
        assert isinstance(oldvalue, Bag)

    def test_oldvalue_preserves_previous_content(self):
        """oldvalue carries the exact previous nodes, navigable."""
        outer = Bag()
        outer.set_backref()
        outer.set_item("inner", Bag({"x": 1, "y": 2}))

        events = []
        outer.subscribe("watcher", update=lambda **kw: events.append(kw))

        outer["inner"].fill_from({"a": 10})

        oldvalue = events[0]["oldvalue"]
        assert len(oldvalue) == 2
        assert oldvalue["x"] == 1
        assert oldvalue["y"] == 2

    def test_oldvalue_is_detached_from_tree(self):
        """The orphan Bag is not part of the live tree."""
        outer = Bag()
        outer.set_backref()
        outer.set_item("inner", Bag({"x": 1}))

        events = []
        outer.subscribe("watcher", update=lambda **kw: events.append(kw))

        outer["inner"].fill_from({"a": 10})

        oldvalue = events[0]["oldvalue"]
        # No parent, no backref
        assert oldvalue.parent is None
        assert oldvalue.parent_node is None


class TestFillFromAtomicity:
    """If the source fails to parse, self stays unchanged."""

    def test_atomicity_on_malformed_xml(self):
        """Invalid XML source raises without touching self."""
        from xml.sax import SAXParseException

        outer = Bag()
        outer.set_backref()
        outer.set_item("inner", Bag({"keep": "me"}))

        with pytest.raises(SAXParseException):
            outer["inner"].fill_from("<not valid xml")

        # self still has the previous content
        inner = outer["inner"]
        assert len(inner) == 1
        assert inner["keep"] == "me"

    def test_atomicity_on_invalid_source_type(self):
        """Invalid source type raises without touching self."""
        outer = Bag()
        outer.set_backref()
        outer.set_item("inner", Bag({"keep": "me"}))

        with pytest.raises(TypeError):
            outer["inner"].fill_from(42)  # int is not a supported source

        inner = outer["inner"]
        assert len(inner) == 1
        assert inner["keep"] == "me"

    def test_atomicity_no_event_on_failure(self):
        """A failed fill_from emits no event."""
        outer = Bag()
        outer.set_backref()
        outer.set_item("inner", Bag({"keep": "me"}))

        events = []
        outer.subscribe("watcher", any=lambda **kw: events.append(kw))

        with pytest.raises(TypeError):
            outer["inner"].fill_from(42)

        assert events == []


class TestFillFromIdentity:
    """fill_from preserves self's object identity."""

    def test_self_object_unchanged(self):
        """The Bag instance is the same before and after fill_from."""
        bag = Bag()
        before_id = id(bag)
        bag.fill_from({"a": 1, "b": 2})
        assert id(bag) == before_id

    def test_subscribers_still_attached(self):
        """Subscribers registered before fill_from keep working after."""
        outer = Bag()
        outer.set_backref()
        inner = Bag({"old": 0})
        outer.set_item("inner", inner)

        events = []
        outer.subscribe("watcher", any=lambda **kw: events.append(kw))

        outer["inner"].fill_from({"a": 1})
        first_count = len(events)

        outer["inner"].set_item("b", 2)
        # Subscriber still active, still receives the new insert
        assert len(events) > first_count


class TestFillFromNestedBags:
    """Nested sub-Bags get proper backref wiring after the swap."""

    def test_nested_bag_backref_active(self):
        """A nested Bag created from a nested dict has backref on after fill_from."""
        outer = Bag()
        outer.set_backref()
        outer.set_item("inner", Bag())

        outer["inner"].fill_from({"child": {"x": 1}, "z": 99})

        child = outer["inner"]["child"]
        # nested bag must have backref propagated
        assert child.backref is True

    def test_nested_mutation_bubbles_to_outer(self):
        """A mutation inside a nested sub-Bag bubbles up to the outer subscriber."""
        outer = Bag()
        outer.set_backref()
        outer.set_item("inner", Bag())

        outer["inner"].fill_from({"child": {"x": 1}})

        events = []
        outer.subscribe("watcher", any=lambda **kw: events.append(kw))

        # Mutate inside the nested child — should bubble to outer's subscriber
        outer["inner"]["child"]["y"] = 2

        assert len(events) >= 1


class TestFillFromRegression:
    """Regression: empty source, None, and repeated calls."""

    def test_fill_from_none_is_noop(self):
        """fill_from(None) changes nothing and emits nothing."""
        outer = Bag()
        outer.set_backref()
        outer.set_item("inner", Bag({"x": 1}))

        events = []
        outer.subscribe("watcher", any=lambda **kw: events.append(kw))

        outer["inner"].fill_from(None)

        assert len(outer["inner"]) == 1
        assert outer["inner"]["x"] == 1
        assert events == []

    def test_fill_from_empty_dict(self):
        """fill_from({}) clears previous content; emits one upd_value."""
        outer = Bag()
        outer.set_backref()
        outer.set_item("inner", Bag({"x": 1, "y": 2}))

        events = []
        outer.subscribe("watcher", update=lambda **kw: events.append(kw))

        outer["inner"].fill_from({})

        assert len(outer["inner"]) == 0
        assert len(events) == 1
        assert events[0]["evt"] == "upd_value"
        # oldvalue should carry the previous nodes
        assert len(events[0]["oldvalue"]) == 2

    def test_repeated_fill_from(self):
        """fill_from can be called multiple times without corruption."""
        outer = Bag()
        outer.set_backref()
        outer.set_item("inner", Bag())

        outer["inner"].fill_from({"a": 1})
        outer["inner"].fill_from({"b": 2})
        outer["inner"].fill_from({"c": 3})

        inner = outer["inner"]
        assert len(inner) == 1
        assert inner["c"] == 3
        assert "a" not in inner
        assert "b" not in inner

    def test_clear_still_works(self):
        """Regression: #46 clear() behaviour is preserved."""
        outer = Bag()
        outer.set_backref()
        outer.set_item("inner", Bag({"x": 1, "y": 2}))

        events = []
        outer.subscribe("watcher", update=lambda **kw: events.append(kw))

        outer["inner"].clear()

        assert len(outer["inner"]) == 0
        assert len(events) == 1
        assert events[0]["evt"] == "upd_value"
        assert len(events[0]["oldvalue"]) == 2
