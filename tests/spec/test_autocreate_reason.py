"""Spec test: structural autocreate of intermediate nodes carry
``reason="autocreate"`` in the events sent to subscribers.

Depends on test_basic.py (set_item) and test_subscriptions.py (subscribe).

Contract:
- When `bag["a.b.c"] = value` autocreates intermediate containers `a` and `b`,
  the corresponding `ins` events arrive with ``reason="autocreate"``.
- The event of the final datum (`c`) remains unmarked (``reason=None``).
- The promotion of a scalar node to container (`bag["x"] = "v"` then
  `bag["x.y"] = 1`) is marked on `x` as autocreate.
- Explicit insert/update on simple paths are untouched.

## Scale

1. new path, intermediate containers           ins of a,b -> 'autocreate', c -> None
2. first level already exists as Bag           ins of b -> 'autocreate', c -> None
3. scalar -> container promotion               upd_value of a -> 'autocreate', ins of b -> 'autocreate', c -> None
4. subscriber filters autocreate               sees only the leaf event
5. insert on simple path                       reason remains None
"""

from __future__ import annotations

from genro_bag import Bag

# =============================================================================
# 1. path nuovo: container intermedi puri
# =============================================================================


class TestAutocreatePureIntermediates:
    def test_intermediate_containers_marked_autocreate_leaf_not_marked(self):
        """bag['a.b.c'] = 1 on empty bag: a,b are autocreate; c is real insert."""
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
# 2. first level already present as a Bag
# =============================================================================


class TestAutocreatePartialPath:
    def test_only_missing_intermediates_marked_autocreate(self):
        """If the first level already exists as a Bag, only the levels below
        are autocreated. The final leaf event remains unmarked."""
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
        """A scalar node promoted to container during traversal in
        write mode receives reason='autocreate' on the upd_value event of the
        promotion. Levels below, autocreated, same; the final leaf no."""
        bag = Bag()
        bag["a"] = "scalar"  # ins of "a" with reason=None
        events = []
        bag.subscribe(
            "w",
            any=lambda **kw: events.append(
                (kw["evt"], kw["node"].label, kw.get("reason"))
            ),
        )
        bag["a.b"] = 1
        # a is promoted (upd_value 'scalar' -> Bag()), then b inserted
        assert events == [
            ("upd_value", "a", "autocreate"),
            ("ins", "b", None),
        ]


# =============================================================================
# 4. subscriber filtra autocreate (pattern downstream idiomatico)
# =============================================================================


class TestAutocreateConsumerFilters:
    def test_subscriber_can_skip_autocreate_events(self):
        """A reactive subscriber that wants to react only to real data can
        filter out reason='autocreate' and receive only the leaf event."""
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
        """An insert/update on a simple path (no autocreate) has reason=None.
        The marking must not 'pollute' normal calls."""
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
