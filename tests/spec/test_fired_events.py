"""Spec test: change events of a fired write carry ``fired=True``.

Depends on test_basic.py (set_item with _fired) and test_subscriptions.py
(subscribe, transaction).

Contract:
- `set_item(path, value, _fired=True)` writes the value, notifies the
  subscribers, then resets the value to None without a second event.
- The `upd` or `ins` event of the fired write carries ``fired=True``.
- Every other `upd` and `ins` event carries ``fired=False``: ordinary writes,
  attribute changes, and the autocreated intermediates of a fired write.
- The flag propagates to the subscribers of the parent Bags.
- Inside `transaction()` the flag is the last element of the `upd` and `ins`
  mutation tuples.

## Scale

1. fired write on an existing node          upd_value with fired=True
2. fired write on a missing path            ins of the leaf with fired=True,
                                            autocreated intermediates fired=False
3. ordinary writes                          ins / upd_value / upd_attrs with fired=False
4. propagation to the parent Bag            root subscriber receives fired=True
5. reset after the fired write              no second event
6. fired write inside transaction()         fired recorded in the mutation tuple
"""

from __future__ import annotations

from genro_bag import Bag

# =============================================================================
# 1. fired write on an existing node
# =============================================================================


class TestFiredWriteExistingNode:
    def test_update_event_carries_fired_true(self):
        """A fired write on an existing node emits upd_value with fired=True."""
        events = []
        bag = Bag()
        bag["click"] = None
        bag.subscribe(
            "w",
            update=lambda **kw: events.append((kw["evt"], kw["node"].value, kw["fired"])),
        )
        bag.set_item("click", "button_ok", _fired=True)
        assert events == [("upd_value", "button_ok", True)]
        assert bag["click"] is None


# =============================================================================
# 2. fired write on a missing path
# =============================================================================


class TestFiredWriteMissingPath:
    def test_insert_event_carries_fired_true(self):
        """A fired write on a missing label emits ins with fired=True."""
        events = []
        bag = Bag()
        bag.subscribe(
            "w",
            insert=lambda **kw: events.append((kw["node"].label, kw["node"].value, kw["fired"])),
        )
        bag.set_item("click", "button_ok", _fired=True)
        assert events == [("click", "button_ok", True)]
        assert bag["click"] is None

    def test_autocreated_intermediates_carry_fired_false(self):
        """Only the leaf of a fired write on 'a.b.c' is fired; a and b are not."""
        events = []
        bag = Bag()
        bag.subscribe(
            "w",
            insert=lambda **kw: events.append((kw["node"].label, kw["reason"], kw["fired"])),
        )
        bag.set_item("a.b.c", "go", _fired=True)
        assert events == [
            ("a", "autocreate", False),
            ("b", "autocreate", False),
            ("c", None, True),
        ]


# =============================================================================
# 3. ordinary writes
# =============================================================================


class TestOrdinaryWrites:
    def test_insert_and_update_carry_fired_false(self):
        """Ordinary insert and update events carry fired=False."""
        events = []
        bag = Bag()
        bag.subscribe("w", any=lambda **kw: events.append((kw["evt"], kw["fired"])))
        bag["a"] = 1
        bag["a"] = 2
        assert events == [("ins", False), ("upd_value", False)]

    def test_attribute_update_carries_fired_false(self):
        """An upd_attrs event from set_attr carries fired=False."""
        events = []
        bag = Bag()
        bag.set_item("x", 1, color="red")
        bag.subscribe("w", update=lambda **kw: events.append((kw["evt"], kw["fired"])))
        bag.get_node("x").set_attr(color="blue")
        assert events == [("upd_attrs", False)]


# =============================================================================
# 4. propagation to the parent Bag
# =============================================================================


class TestFiredPropagation:
    def test_root_receives_fired_update_from_child(self):
        """A fired write in a sub-Bag reaches the root with fired=True."""
        events = []
        root = Bag()
        root["section.click"] = None
        root.subscribe(
            "w",
            update=lambda **kw: events.append((kw["pathlist"], kw["fired"])),
        )
        root.set_item("section.click", "go", _fired=True)
        assert events == [(["section", "click"], True)]

    def test_root_receives_fired_insert_from_child(self):
        """A fired insert in an existing sub-Bag reaches the root with fired=True."""
        events = []
        root = Bag()
        root["section.x"] = 0
        root.subscribe(
            "w",
            insert=lambda **kw: events.append((kw["node"].label, kw["fired"])),
        )
        root.set_item("section.click", "go", _fired=True)
        assert events == [("click", True)]


# =============================================================================
# 5. reset after the fired write
# =============================================================================


class TestFiredResetIsSilent:
    def test_existing_node_emits_one_event(self):
        """The reset to None after a fired update emits no event."""
        events = []
        bag = Bag()
        bag["click"] = None
        bag.subscribe("w", any=lambda **kw: events.append(kw["evt"]))
        bag.set_item("click", "button_ok", _fired=True)
        assert events == ["upd_value"]

    def test_missing_path_emits_one_event(self):
        """The reset to None after a fired insert emits no event."""
        events = []
        bag = Bag()
        bag.subscribe("w", any=lambda **kw: events.append(kw["evt"]))
        bag.set_item("click", "button_ok", _fired=True)
        assert events == ["ins"]


# =============================================================================
# 6. fired write inside transaction()
# =============================================================================


class TestFiredInTransaction:
    def test_mutation_tuples_record_fired(self):
        """upd and ins mutation tuples end with the fired flag."""
        received = []
        bag = Bag()
        bag["existing"] = None
        bag.subscribe("s1", transaction=lambda **kw: received.append(kw["mutations"]))
        with bag.transaction():
            bag.set_item("existing", "go", _fired=True)
            bag.set_item("new", "go", _fired=True)
            bag["plain"] = 1
        assert [(m[0], m[-1]) for m in received[0]] == [
            ("upd", True),
            ("ins", True),
            ("ins", False),
        ]
